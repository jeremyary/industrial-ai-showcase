"""Demo scenario: worker walks into forklift zone near a parked forklift.
Run this in Isaac Sim's Script Editor AFTER mqtt_bridge.py and camera_server.py are running.

Only the forklift zone is monitored. Overhead and loading dock stay SAFE.
A static forklift prim is placed in the zone to show why it's dangerous.
"""

import importlib
importlib.invalidate_caches()

import asyncio
import json
import time
import uuid
import omni.usd
from pxr import UsdGeom, UsdShade, Gf, Sdf
import paho.mqtt.client as mqtt

# Stop any previous instance of this script
try:
    _prev_mqtt.loop_stop()
    _prev_mqtt.disconnect()
    print("Stopped previous MQTT client")
except Exception:
    pass

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# Forklift zone center from create_alerts.py: (-45, -80)
FORKLIFT_POS = Gf.Vec3d(-52, -80, 0)   # where the static forklift sits
FORKLIFT_PATH = "/World/DemoForklift"

SCENARIO_PATH = [
    # Worker starts north of zone, in open aisle (avoids equipment cluster at -35,-80)
    (Gf.Vec3d(-39, -73, 0), 2, "SAFE", 0),
    (Gf.Vec3d(-40, -73.5, 0), 1, "SAFE", 0),
    (Gf.Vec3d(-41, -74, 0), 1, "SAFE", 1),
    (Gf.Vec3d(-42, -74.5, 0), 1, "SAFE", 1),
    (Gf.Vec3d(-43, -75, 0), 1, "SAFE", 1),
    (Gf.Vec3d(-43.5, -75.5, 0), 1, "SAFE", 1),
    # Entering caution perimeter — approaching from north
    (Gf.Vec3d(-44, -76, 0), 1, "CAUTION", 2),
    (Gf.Vec3d(-44.5, -76.5, 0), 1, "CAUTION", 2),
    (Gf.Vec3d(-45, -77, 0), 1, "CAUTION", 2),
    (Gf.Vec3d(-45.5, -77.5, 0), 1, "CAUTION", 2),
    # Into forklift danger zone — walking toward parked forklift
    (Gf.Vec3d(-46, -78, 0), 1, "DANGER", 3),
    (Gf.Vec3d(-46, -78.5, 0), 1, "DANGER", 3),
    (Gf.Vec3d(-46.5, -79, 0), 1, "DANGER", 3),
    (Gf.Vec3d(-46.5, -79.5, 0), 2, "DANGER", 3),
    (Gf.Vec3d(-47, -79.5, 0), 3, "DANGER", 3),   # right next to forklift
    # Backing away north
    (Gf.Vec3d(-46.5, -79, 0), 1, "DANGER", 3),
    (Gf.Vec3d(-46, -78.5, 0), 1, "DANGER", 3),
    (Gf.Vec3d(-45.5, -78, 0), 1, "CAUTION", 2),
    (Gf.Vec3d(-45, -77, 0), 1, "CAUTION", 2),
    # Walking out to safe — heading north-east
    (Gf.Vec3d(-44.5, -76.5, 0), 1, "SAFE", 4),
    (Gf.Vec3d(-44, -76, 0), 1, "SAFE", 4),
    (Gf.Vec3d(-43.5, -75.5, 0), 1, "SAFE", 4),
    (Gf.Vec3d(-43, -75, 0), 1, "SAFE", 4),
    (Gf.Vec3d(-42, -74, 0), 1, "SAFE", 4),
    (Gf.Vec3d(-41, -73.5, 0), 1, "SAFE", 4),
    (Gf.Vec3d(-39, -73, 0), 1, "SAFE", 4),
]

WORKER_PATH = "/World/DemoWorker"
WORKER_HEIGHT = 1.8
MARKER_HEIGHT = 4.0

_mqtt_client = None
_scenario_running = False
_trigger_pending = False


def create_forklift_prim():
    """Place a forklift in the zone using the same USD asset as existing scene forklifts."""
    stage = omni.usd.get_context().get_stage()

    if stage.GetPrimAtPath(FORKLIFT_PATH):
        return  # already exists

    # Same asset the scene's SM_Forklift_B01_Red forklifts use
    FORKLIFT_ASSET = "/simready-warehouse/Props/general/SM_Forklift_B01_Red_01/SM_Forklift_B01_Red_01_physics.usd"

    prim = stage.DefinePrim(FORKLIFT_PATH, "Xform")
    prim.GetReferences().AddReference(FORKLIFT_ASSET)

    # Position, orient, and scale the forklift in the zone
    # Asset is in centimeters, scene is in meters — need 0.01 scale
    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(FORKLIFT_POS)
    xform.AddRotateZOp().Set(90.0)
    xform.AddScaleOp().Set(Gf.Vec3f(0.01, 0.01, 0.01))

    print(f"Created forklift prim at {FORKLIFT_PATH} (payload from scene asset)")


def create_worker_prim():
    """Create a visible worker figure with a tall marker pole."""
    stage = omni.usd.get_context().get_stage()

    if not stage.GetPrimAtPath(WORKER_PATH):
        UsdGeom.Xform.Define(stage, WORKER_PATH)

    body_path = f"{WORKER_PATH}/Body"
    body = UsdGeom.Capsule.Define(stage, body_path)
    body.GetRadiusAttr().Set(0.35)
    body.GetHeightAttr().Set(1.4)
    body.GetAxisAttr().Set("Z")

    head_path = f"{WORKER_PATH}/Head"
    head = UsdGeom.Sphere.Define(stage, head_path)
    head.GetRadiusAttr().Set(0.25)
    head_xform = UsdGeom.Xformable(head.GetPrim())
    head_xform.ClearXformOpOrder()
    head_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, 1.0))

    pole_path = f"{WORKER_PATH}/MarkerPole"
    pole = UsdGeom.Cylinder.Define(stage, pole_path)
    pole.GetRadiusAttr().Set(0.05)
    pole.GetHeightAttr().Set(MARKER_HEIGHT)
    pole.GetAxisAttr().Set("Z")
    pole_xform = UsdGeom.Xformable(pole.GetPrim())
    pole_xform.ClearXformOpOrder()
    pole_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, MARKER_HEIGHT / 2 + 1.2))

    diamond_path = f"{WORKER_PATH}/MarkerDiamond"
    diamond = UsdGeom.Sphere.Define(stage, diamond_path)
    diamond.GetRadiusAttr().Set(0.4)
    diamond_xform = UsdGeom.Xformable(diamond.GetPrim())
    diamond_xform.ClearXformOpOrder()
    diamond_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, MARKER_HEIGHT + 1.6))

    mat_path = f"{WORKER_PATH}/HiVisMat"
    mat = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(1.0, 0.4, 0.0)
    )
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(1.0, 0.3, 0.0)
    )
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    marker_mat_path = f"{WORKER_PATH}/MarkerMat"
    marker_mat = UsdShade.Material.Define(stage, marker_mat_path)
    marker_shader = UsdShade.Shader.Define(stage, f"{marker_mat_path}/Shader")
    marker_shader.CreateIdAttr("UsdPreviewSurface")
    marker_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(1.0, 0.0, 0.0)
    )
    marker_shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(2.0, 0.0, 0.0)
    )
    marker_mat.CreateSurfaceOutput().ConnectToSource(
        marker_shader.ConnectableAPI(), "surface"
    )

    for p in [body_path, head_path]:
        UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath(p)).Bind(mat)
    for p in [pole_path, diamond_path]:
        UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath(p)).Bind(marker_mat)

    print(f"Created worker prim at {WORKER_PATH} (with {MARKER_HEIGHT}m marker pole)")
    return True


def move_worker(position):
    """Move the worker prim to a new position."""
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(WORKER_PATH)
    if not prim.IsValid():
        return
    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    translate_op = xform.AddTranslateOp()
    translate_op.Set(position + Gf.Vec3d(0, 0, WORKER_HEIGHT / 2))


def remove_worker():
    """Remove the worker prim from the scene."""
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(WORKER_PATH)
    if prim.IsValid():
        stage.RemovePrim(WORKER_PATH)
        print("Removed worker prim")


def publish_safety(camera_id, status, hazards, summary):
    """Publish a safety status message to MQTT (retained for dashboard state on load)."""
    msg = {
        "camera_id": camera_id,
        "overall_status": status,
        "hazards": hazards,
        "summary": summary,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _mqtt_client.publish(
        f"warehouse/safety/{camera_id}",
        json.dumps(msg),
        qos=1,
        retain=True,
    )


def publish_scenario_status(phase=None, step=None):
    """Publish scenario progress for the dashboard."""
    msg = {}
    if phase:
        msg["phase"] = phase
    if step is not None:
        msg["step"] = step
    _mqtt_client.publish(
        "warehouse/control/scenario_status",
        json.dumps(msg),
        qos=1,
    )


async def run_scenario():
    """Execute the demo scenario."""
    global _scenario_running

    if _scenario_running:
        print("Scenario already running")
        return

    _scenario_running = True
    print("\n=== DEMO SCENARIO STARTED ===")
    publish_scenario_status(phase="start")

    create_forklift_prim()
    create_worker_prim()

    for pos, dwell, status, step_idx in SCENARIO_PATH:
        if not _scenario_running:
            break

        move_worker(pos)
        publish_scenario_status(step=step_idx)

        step_labels = [
            "Baseline scan - all clear",
            "Worker approaching forklift zone",
            "Worker near forklift perimeter",
            "Worker in forklift operating area - DANGER",
            "Worker has exited the forklift zone",
        ]
        print(f"  Step {step_idx}: {step_labels[step_idx]} ({status})")

        hazards = []
        if status == "CAUTION":
            hazards = [{
                "type": "worker_near_zone",
                "severity": "medium",
                "description": "Worker detected near forklift operating path",
            }]
        elif status == "DANGER":
            hazards = [{
                "type": "worker_in_path",
                "severity": "high",
                "description": "Worker standing in active forklift lane",
            }]

        # Only forklift zone changes status; other cameras stay SAFE
        publish_safety("forklift", status, hazards,
                       step_labels[step_idx])
        publish_safety("overhead", "SAFE", [],
                       "Overhead view nominal")
        publish_safety("loading_dock", "SAFE", [],
                       "Loading dock area clear")

        # Wait at this position (camera_server.py captures independently)
        await asyncio.sleep(dwell)

    # Cleanup
    remove_worker()
    for cam in ["overhead", "forklift", "loading_dock"]:
        publish_safety(cam, "SAFE", [], "All clear - no hazards detected")
    await asyncio.sleep(2)

    publish_scenario_status(phase="end")
    _scenario_running = False
    print("=== DEMO SCENARIO COMPLETE ===\n")


def on_control_message(client, userdata, msg):
    """Handle control messages from the dashboard (runs on MQTT thread)."""
    global _trigger_pending
    try:
        if msg.topic == "warehouse/control/trigger_demo":
            data = json.loads(msg.payload.decode())
            if data.get("action") == "start":
                print("Demo trigger received from dashboard")
                _trigger_pending = True
    except Exception as e:
        print(f"Control message error: {e}")


# Connect to MQTT
_client_id = f"demo-scenario-{uuid.uuid4().hex[:8]}"
_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=_client_id)
_mqtt_client.on_message = on_control_message
_mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
_mqtt_client.subscribe("warehouse/control/trigger_demo")
_mqtt_client.loop_start()
_prev_mqtt = _mqtt_client


async def _trigger_loop():
    """Poll for trigger requests on Kit's main event loop."""
    global _trigger_pending
    while True:
        if _trigger_pending and not _scenario_running:
            _trigger_pending = False
            await run_scenario()
        await asyncio.sleep(0.5)


async def _startup():
    """Hide zone planes, capture initial frames, publish SAFE state."""
    stage = omni.usd.get_context().get_stage()
    for zone_name in ["overhead_zone", "forklift_zone", "loading_dock_zone"]:
        zone_prim = stage.GetPrimAtPath(f"/World/Alerts/{zone_name}")
        if zone_prim.IsValid():
            UsdGeom.Imageable(zone_prim).MakeInvisible()

    remove_worker()

    # Publish initial SAFE state
    for cam in ["overhead", "forklift", "loading_dock"]:
        publish_safety(cam, "SAFE", [], "All clear - no hazards detected")
    print("Published initial SAFE state for all cameras")


asyncio.ensure_future(_trigger_loop())
asyncio.ensure_future(_startup())

print("Demo scenario handler ready!")
print("  Trigger via dashboard button or:")
print("  mosquitto_pub -h localhost -t warehouse/control/trigger_demo -m '{\"action\":\"start\"}'")
