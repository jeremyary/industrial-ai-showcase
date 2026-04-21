# This project was developed with assistance from AI tools.
"""Warehouse-baseline startup script for the Isaac Sim 5.0 Streaming app.

Passed via `--exec` to `isaac-sim.streaming.sh` (see the Deployment spec in
`infrastructure/gitops/apps/isaac-sim/deployment.yaml`). Runs inside the Kit
process; uses `omni.isaac.core` / `omni.usd` APIs that are only safe to call
after Kit's app_ready phase.

Scene selection per `assets/README.md`:
- `/Isaac/Samples/Replicator/Stage/full_warehouse_worker_and_anim_cameras.usd`
  — bundled NVIDIA warehouse with animated worker + overhead cameras. Loaded
  from Isaac asset root (resolves to NVIDIA S3 CDN by default).
- `/Isaac/Samples/Replicator/OmniGraph/nova_carter_nav_only.usd` — Nova Carter
  AMR with nav stack wired, no perception. Perfect for the 5-min AMR beat.
"""

import asyncio
import traceback

import carb
import omni.kit.app
import omni.usd
from isaacsim.storage.native import get_assets_root_path_async

# Relative paths — the resolver prepends the active asset-root URL.
STAGE_URL_REL = "/Isaac/Samples/Replicator/Stage/full_warehouse_worker_and_anim_cameras.usd"
CARTER_URL_REL = "/Isaac/Samples/Replicator/OmniGraph/nova_carter_nav_only.usd"
CARTER_STAGE_PATH = "/World/nova_carter"
CARTER_POSITION = (-6.0, 4.0, 0.0)


async def _open_stage(url: str) -> None:
    ctx = omni.usd.get_context()
    carb.log_info(f"warehouse_baseline: opening {url}")
    result, err = await ctx.open_stage_async(url)
    if not result:
        raise RuntimeError(f"failed to open {url}: {err}")
    carb.log_info(f"warehouse_baseline: stage opened")


async def _add_carter(stage_url: str) -> None:
    from pxr import Gf, Sdf, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("no stage after open_stage_async")
    xform = UsdGeom.Xform.Define(stage, Sdf.Path(CARTER_STAGE_PATH))
    xform.GetPrim().GetReferences().AddReference(stage_url)
    UsdGeom.XformCommonAPI(xform).SetTranslate(Gf.Vec3d(*CARTER_POSITION))
    carb.log_info(f"warehouse_baseline: referenced Carter at {CARTER_STAGE_PATH}")


async def _run() -> None:
    try:
        asset_root = await get_assets_root_path_async()
        if not asset_root:
            raise RuntimeError("no Isaac asset root resolved — NVIDIA CDN unreachable?")
        carb.log_info(f"warehouse_baseline: asset_root={asset_root}")
        stage_url = f"{asset_root}{STAGE_URL_REL}"
        carter_url = f"{asset_root}{CARTER_URL_REL}"
        await _open_stage(stage_url)
        await _add_carter(carter_url)
        # Start the timeline so the animated worker + camera motion give the
        # MJPEG encoder something interesting to send. The Kit WebRTC stream
        # stalls at ~20s when timeline plays against the warehouse scene, but
        # the MJPEG path (viewport_mjpeg.py) doesn't depend on Kit's encoder
        # — it reads frames directly from the viewport and serves them over
        # HTTP, so this is safe.
        import omni.timeline
        omni.timeline.get_timeline_interface().play()
        carb.log_info("warehouse_baseline: scene ready, timeline playing")
    except Exception:
        carb.log_error("warehouse_baseline: " + traceback.format_exc())


# Kit runs this script in the main thread during extension load. Schedule the
# async work on Kit's message-pump loop.
omni.kit.app.get_app().get_post_update_event_stream()
asyncio.ensure_future(_run())

# Kit only processes one `--exec` script per invocation — chain the MJPEG
# viewport broadcaster here so it boots in the same Kit process. import has
# module-level side effects (starts http + encoder threads, subscribes to
# Kit's update stream), which is exactly what we want.
import sys as _sys  # noqa: E402
_sys.path.insert(0, "/scenarios")
import viewport_mjpeg  # noqa: E402,F401


# Smoke-test camera orbit. Until the scenario→Isaac-Sim closed loop is wired
# (real Carter driving in response to events), this gives the MJPEG stream
# guaranteed continuous motion so the Console pipeline is exercised under
# real frame-to-frame delta. Disable by setting SCENE_CAMERA_ORBIT=0.
import math as _math  # noqa: E402
import time as _time  # noqa: E402
import os as _os  # noqa: E402


def _install_camera_orbit() -> None:
    if _os.environ.get("SCENE_CAMERA_ORBIT", "1") == "0":
        return
    try:
        from pxr import Gf, UsdGeom
    except Exception:
        carb.log_warn("camera_orbit: pxr imports unavailable")
        return

    camera_path = "/OmniverseKit_Persp"
    orbit_radius = 12.0
    orbit_period_s = 20.0
    height = 4.0
    t0 = _time.time()

    def _tick(_event) -> None:  # noqa: ANN001 — Kit event type
        try:
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return
            cam = stage.GetPrimAtPath(camera_path)
            if not cam or not cam.IsValid():
                return
            t = _time.time() - t0
            angle = (t / orbit_period_s) * 2.0 * _math.pi
            x = orbit_radius * _math.cos(angle)
            y = orbit_radius * _math.sin(angle)
            # Yaw so the camera faces the origin — pitch is constant.
            yaw_deg = _math.degrees(_math.atan2(-y, -x)) - 90.0
            xf = UsdGeom.XformCommonAPI(cam)
            xf.SetTranslate(Gf.Vec3d(x, y, height))
            xf.SetRotate(Gf.Vec3f(80.0, 0.0, yaw_deg))
        except Exception:
            pass  # silent — per-frame tick; don't spam logs

    # Stash the subscription on a module attribute so it isn't GC'd.
    global _ORBIT_SUB  # noqa: PLW0603
    _ORBIT_SUB = (
        omni.kit.app.get_app()
        .get_update_event_stream()
        .create_subscription_to_pop(_tick, name="camera_orbit-smoketest")
    )
    carb.log_info("camera_orbit: subscribed (radius=12, period=20s)")


_install_camera_orbit()
