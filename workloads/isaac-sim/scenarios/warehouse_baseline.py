# This project was developed with assistance from AI tools.
"""Phase-1 warehouse scenario — Nucleus scene-pack + Kafka twin-update.

Opens the scene-pack overlay from Nucleus (warehouse + forklift + markers
composed via sublayer). Subscribes to fleet.telemetry and fleet.safety.alerts
on background threads; prim updates are queued and applied on Kit's main-thread
update tick.

Chains viewport_mjpeg.py for the MJPEG viewport broadcaster and installs a
camera-orbit tick for guaranteed viewport motion.

Env contract:
    SCENE_PACK_URL          — omniverse:// URL of the scene-pack overlay on Nucleus
    NUCLEUS_USER            — Nucleus auth user (default "omniverse")
    NUCLEUS_PASS            — Nucleus auth password
    KAFKA_BOOTSTRAP_SERVERS — Kafka bootstrap (default fleet-kafka-bootstrap.fleet-ops.svc:9092)
    KAFKA_SECURITY_PROTOCOL — PLAINTEXT (default) or SSL
    PALLET_ASSET_URL        — omniverse:// URL for the pallet USD asset (optional;
                              falls back to a red-cube marker if unset)
    SCENE_CAMERA_ORBIT      — "1" (default) to orbit, "0" to disable
"""

import asyncio
import json
import math
import os
import queue
import threading
import time
import traceback

import carb
import omni.kit.app
import omni.timeline
import omni.usd

SCENE_PACK_URL = os.environ.get("SCENE_PACK_URL", "")
NUCLEUS_USER = os.environ.get("NUCLEUS_USER", "omniverse")
NUCLEUS_PASS = os.environ.get("NUCLEUS_PASS", "")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "fleet-kafka-bootstrap.fleet-ops.svc:9092")
KAFKA_SECURITY_PROTOCOL = os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")

FORKLIFT_PRIM = "/World/Robots/fl_07"
PALLET_PRIM = "/World/Obstructions/aisle_3_pallet"
PALLET_ASSET_URL = os.environ.get("PALLET_ASSET_URL", "")
PALLET_POS = (1.0, 0.0, 0.0)

_CMD_QUEUE: "queue.Queue[tuple]" = queue.Queue(maxsize=64)

_AUTH_SUB = None
_UPDATE_SUB = None
_ORBIT_SUB = None


# ---------------------------------------------------------------------------
# Nucleus auth
# ---------------------------------------------------------------------------

def _register_nucleus_auth() -> None:
    """Register auth callback before Kit attempts any Nucleus connections."""
    import omni.client

    def _cb(url: str):
        return (NUCLEUS_USER, NUCLEUS_PASS)

    global _AUTH_SUB
    _AUTH_SUB = omni.client.register_authentication_callback(_cb)
    carb.log_info(f"warehouse_baseline: nucleus auth registered (user={NUCLEUS_USER})")


# ---------------------------------------------------------------------------
# Scene loading
# ---------------------------------------------------------------------------

CDN_WAREHOUSE_REL = "/Isaac/Samples/Replicator/Stage/full_warehouse_worker_and_anim_cameras.usd"


async def _open_scene() -> None:
    ctx = omni.usd.get_context()

    if SCENE_PACK_URL:
        carb.log_info(f"warehouse_baseline: opening scene-pack {SCENE_PACK_URL}")
        result, err = await ctx.open_stage_async(SCENE_PACK_URL)
        if not result:
            raise RuntimeError(f"failed to open scene-pack: {err}")
        carb.log_info("warehouse_baseline: scene-pack opened")
        return

    # Fallback: CDN warehouse (for KAS sessions without Nucleus env vars).
    from isaacsim.storage.native import get_assets_root_path_async
    asset_root = await get_assets_root_path_async()
    if not asset_root:
        raise RuntimeError("no Isaac asset root resolved and SCENE_PACK_URL not set")
    url = f"{asset_root}{CDN_WAREHOUSE_REL}"
    carb.log_info(f"warehouse_baseline: SCENE_PACK_URL not set — falling back to CDN: {url}")
    result, err = await ctx.open_stage_async(url)
    if not result:
        raise RuntimeError(f"failed to open CDN stage: {err}")
    carb.log_info("warehouse_baseline: CDN warehouse opened (fallback)")


# ---------------------------------------------------------------------------
# Kafka consumers (daemon threads)
# ---------------------------------------------------------------------------

def _make_consumer_conf(group_id: str) -> dict:
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": group_id,
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    }
    if KAFKA_SECURITY_PROTOCOL != "PLAINTEXT":
        conf["security.protocol"] = KAFKA_SECURITY_PROTOCOL
        conf["ssl.endpoint.identification.algorithm"] = "none"
        conf["enable.ssl.certificate.verification"] = False
    return conf


def _telemetry_consumer() -> None:
    """Consume fleet.telemetry → queue forklift pose updates."""
    try:
        from confluent_kafka import Consumer
    except ImportError:
        carb.log_warn("warehouse_baseline: confluent_kafka unavailable — telemetry subscriber disabled")
        return

    c = Consumer(_make_consumer_conf("isaac-sim-twin"))
    c.subscribe(["fleet.telemetry"])
    carb.log_info("warehouse_baseline: telemetry consumer started")

    while True:
        msg = c.poll(1.0)
        if msg is None or msg.error():
            continue
        try:
            data = json.loads(msg.value())
            pose = data.get("pose")
            if pose:
                try:
                    _CMD_QUEUE.put_nowait(("move", FORKLIFT_PRIM, pose))
                except queue.Full:
                    pass
        except (json.JSONDecodeError, ValueError):
            pass


def _alerts_consumer() -> None:
    """Consume fleet.safety.alerts → queue pallet show/hide."""
    try:
        from confluent_kafka import Consumer
    except ImportError:
        carb.log_warn("warehouse_baseline: confluent_kafka unavailable — alerts subscriber disabled")
        return

    c = Consumer(_make_consumer_conf("isaac-sim-twin-alerts"))
    c.subscribe(["fleet.safety.alerts"])
    carb.log_info("warehouse_baseline: alerts consumer started")

    while True:
        msg = c.poll(1.0)
        if msg is None or msg.error():
            continue
        try:
            data = json.loads(msg.value())
            obstructed = data.get("obstructed", False)
            try:
                _CMD_QUEUE.put_nowait(("obstruction", PALLET_PRIM, obstructed))
            except queue.Full:
                pass
        except (json.JSONDecodeError, ValueError):
            pass


# ---------------------------------------------------------------------------
# Main-thread prim updater (Kit update tick)
# ---------------------------------------------------------------------------

def _apply_updates(_event) -> None:
    """Drain command queue and update USD prims on Kit's main thread."""
    try:
        from pxr import Gf, Sdf, UsdGeom
    except Exception:
        return

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return

    while not _CMD_QUEUE.empty():
        try:
            cmd = _CMD_QUEUE.get_nowait()
        except queue.Empty:
            break

        if cmd[0] == "move":
            prim_path, pose = cmd[1], cmd[2]
            prim = stage.GetPrimAtPath(prim_path)
            if prim and prim.IsValid():
                UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(
                    float(pose.get("x", 0)),
                    float(pose.get("y", 0)),
                    float(pose.get("z", 0)),
                ))

        elif cmd[0] == "obstruction":
            prim_path, obstructed = cmd[1], cmd[2]
            prim = stage.GetPrimAtPath(prim_path)

            if obstructed:
                if not prim or not prim.IsValid():
                    if PALLET_ASSET_URL:
                        xf = UsdGeom.Xform.Define(stage, Sdf.Path(prim_path))
                        xf.GetPrim().GetReferences().AddReference(PALLET_ASSET_URL)
                    else:
                        cube = UsdGeom.Cube.Define(stage, Sdf.Path(prim_path))
                        cube.CreateSizeAttr(0.8)
                        cube.CreateDisplayColorAttr([(0.9, 0.15, 0.1)])
                    UsdGeom.XformCommonAPI(
                        stage.GetPrimAtPath(prim_path)
                    ).SetTranslate(Gf.Vec3d(*PALLET_POS))
                    prim = stage.GetPrimAtPath(prim_path)
                UsdGeom.Imageable(prim).MakeVisible()
                carb.log_info(f"warehouse_baseline: pallet visible at {PALLET_POS}")

            else:
                if prim and prim.IsValid():
                    UsdGeom.Imageable(prim).MakeInvisible()
                    carb.log_info("warehouse_baseline: pallet hidden")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def _run() -> None:
    try:
        _register_nucleus_auth()
        await _open_scene()

        threading.Thread(target=_telemetry_consumer, daemon=True, name="twin-telemetry").start()
        threading.Thread(target=_alerts_consumer, daemon=True, name="twin-alerts").start()

        global _UPDATE_SUB
        _UPDATE_SUB = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(_apply_updates, name="twin-update")
        )

        omni.timeline.get_timeline_interface().play()
        carb.log_info("warehouse_baseline: scene ready, twin subscribers active")
    except Exception:
        carb.log_error("warehouse_baseline: " + traceback.format_exc())


omni.kit.app.get_app().get_post_update_event_stream()
asyncio.ensure_future(_run())


# ---------------------------------------------------------------------------
# Chain MJPEG viewport broadcaster
# ---------------------------------------------------------------------------

import sys as _sys  # noqa: E402
_sys.path.insert(0, "/scenarios")
import viewport_mjpeg  # noqa: E402,F401


# ---------------------------------------------------------------------------
# Camera orbit (guaranteed viewport motion for the MJPEG stream)
# ---------------------------------------------------------------------------

def _install_camera_orbit() -> None:
    if os.environ.get("SCENE_CAMERA_ORBIT", "1") == "0":
        return
    try:
        from pxr import Gf, UsdGeom
    except Exception:
        carb.log_warn("camera_orbit: pxr imports unavailable")
        return

    camera_path = "/OmniverseKit_Persp"
    orbit_radius = 14.0
    orbit_period_s = 30.0
    orbit_height = 6.0
    orbit_center_y = 2.0
    t0 = time.time()

    def _tick(_event) -> None:
        try:
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return
            cam = stage.GetPrimAtPath(camera_path)
            if not cam or not cam.IsValid():
                return
            t = time.time() - t0
            angle = (t / orbit_period_s) * 2.0 * math.pi
            x = orbit_radius * math.cos(angle)
            y = orbit_center_y + orbit_radius * math.sin(angle)
            yaw_deg = math.degrees(math.atan2(-(y - orbit_center_y), -x)) - 90.0
            xf = UsdGeom.XformCommonAPI(cam)
            xf.SetTranslate(Gf.Vec3d(x, y, orbit_height))
            xf.SetRotate(Gf.Vec3f(75.0, 0.0, yaw_deg))
        except Exception:
            pass

    global _ORBIT_SUB
    _ORBIT_SUB = (
        omni.kit.app.get_app()
        .get_update_event_stream()
        .create_subscription_to_pop(_tick, name="camera_orbit")
    )
    carb.log_info(f"camera_orbit: subscribed (radius={orbit_radius}, period={orbit_period_s}s)")


_install_camera_orbit()
