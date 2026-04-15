"""MQTT-to-USD bridge: subscribes to safety topics and updates alert prims.
Run this in Isaac Sim's Script Editor AFTER running create_alerts.py.

Connects to MQTT broker on localhost:1883, subscribes to warehouse/safety/#,
and updates alert sphere colors + zone plane visibility based on safety status.
"""

import importlib
importlib.invalidate_caches()

import json
import threading
import uuid
import omni.usd
from pxr import UsdGeom, UsdShade, Gf, Sdf
import paho.mqtt.client as mqtt

# Stop any previous instance of this script
try:
    _prev_bridge_mqtt.loop_stop()
    _prev_bridge_mqtt.disconnect()
    print("Stopped previous bridge MQTT client")
except Exception:
    pass

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "warehouse/safety/#"

# Map camera_id from MQTT messages to alert prim paths
ALERT_SPHERES = {
    "overhead": "/World/Alerts/overhead_Alert",
    "forklift": "/World/Alerts/forklift_Alert",
    "loading_dock": "/World/Alerts/loading_dock_Alert",
}

ZONE_PLANES = {
    "overhead": "/World/Alerts/overhead_zone",
    "forklift": "/World/Alerts/forklift_zone",
    "loading_dock": "/World/Alerts/loading_dock_zone",
}

# Material paths created by create_alerts.py
MATERIAL_PATHS = {
    "SAFE": "/World/Alerts/Materials/SafeGreen",
    "CAUTION": "/World/Alerts/Materials/CautionYellow",
    "DANGER": "/World/Alerts/Materials/DangerRed",
}

ZONE_MATERIAL_PATHS = {
    "CAUTION": "/World/Alerts/Materials/ZoneCautionYellow",
    "DANGER": "/World/Alerts/Materials/ZoneDangerRed",
}

# Queue for thread-safe USD updates (MQTT callback runs on a background thread)
_pending_updates = []
_lock = threading.Lock()


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"MQTT bridge connected (rc={reason_code})")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to {MQTT_TOPIC}")


def on_message(client, userdata, msg):
    """Queue MQTT message for processing on the main thread."""
    try:
        data = json.loads(msg.payload.decode())
        camera_id = data.get("camera_id", "unknown")
        status = data.get("overall_status", "SAFE")
        hazards = data.get("hazards", [])
        summary = data.get("summary", "")

        with _lock:
            _pending_updates.append({
                "camera_id": camera_id,
                "status": status,
                "hazards": hazards,
                "summary": summary,
            })

        print(f"[MQTT] {camera_id}: {status} - {summary}")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"[MQTT] Parse error: {e}")


def process_updates():
    """Process queued updates on the main thread (safe for USD stage access)."""
    with _lock:
        updates = list(_pending_updates)
        _pending_updates.clear()

    if not updates:
        return

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return

    for update in updates:
        camera_id = update["camera_id"]
        status = update["status"]

        # Update alert sphere color
        sphere_path = ALERT_SPHERES.get(camera_id)
        mat_path = MATERIAL_PATHS.get(status)
        if sphere_path and mat_path:
            sphere_prim = stage.GetPrimAtPath(sphere_path)
            mat_prim = stage.GetPrimAtPath(mat_path)
            if sphere_prim.IsValid() and mat_prim.IsValid():
                mat = UsdShade.Material(mat_prim)
                UsdShade.MaterialBindingAPI.Apply(sphere_prim).Bind(mat)

        # Update zone plane visibility
        zone_path = ZONE_PLANES.get(camera_id)
        if zone_path:
            zone_prim = stage.GetPrimAtPath(zone_path)
            if zone_prim.IsValid():
                imageable = UsdGeom.Imageable(zone_prim)
                if status in ("CAUTION", "DANGER"):
                    imageable.MakeVisible()
                    # Bind appropriate zone material
                    zone_mat_path = ZONE_MATERIAL_PATHS.get(status)
                    if zone_mat_path:
                        zone_mat_prim = stage.GetPrimAtPath(zone_mat_path)
                        if zone_mat_prim.IsValid():
                            mat = UsdShade.Material(zone_mat_prim)
                            UsdShade.MaterialBindingAPI.Apply(zone_prim).Bind(mat)
                else:
                    imageable.MakeInvisible()

        # Log hazards
        for hazard in update["hazards"]:
            sev = hazard.get("severity", "?")
            desc = hazard.get("description", "")
            print(f"  HAZARD [{sev}] {hazard.get('type', '?')}: {desc}")


# ---- Start MQTT client in background thread ----
_bridge_id = f"usd-bridge-{uuid.uuid4().hex[:8]}"
_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=_bridge_id)
_mqtt_client.on_connect = on_connect
_mqtt_client.on_message = on_message
_mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
_mqtt_client.loop_start()
_prev_bridge_mqtt = _mqtt_client

# ---- Register a periodic update on Kit's event loop ----
import omni.kit.app
import asyncio


async def _bridge_loop():
    """Periodically process MQTT updates on the main thread."""
    print("MQTT-to-USD bridge loop started (processing every 1s)")
    while True:
        process_updates()
        await asyncio.sleep(1.0)


asyncio.ensure_future(_bridge_loop())
print("MQTT-to-USD bridge is running!")
print("  Listening on: warehouse/safety/#")
print("  Alert spheres will change color based on status")
print("  Zone planes will appear on CAUTION/DANGER")
