# This project was developed with assistance from AI tools.
"""Generate the Phase-1 scene-pack overlay USD from warehouse-topology.yaml.

Per ADR-027 step 5. Produces `warehouse_scene_pack.usda`: a USD composition
that **sublayers** the NVIDIA Digital_Twin_Warehouse scene and adds the
Phase-1-specific placements on top — forklift at its dock-a home, camera
prims at ceiling vantage points, approach-point + dock markers where the
topology yaml declares them.

The overlay is the file Isaac Sim actually opens at demo time. Everything
is driven off `warehouse-topology.yaml` so a coordinate change in the yaml
regenerates a consistent overlay.

Runtime: `/isaac-sim/python.sh` with an `isaacsim.SimulationApp` bootstrap
so `pxr.Usd` is importable and `omni.client` can push the result to Nucleus.

Env contract:
    TOPOLOGY_YAML   — path to warehouse-topology.yaml (default /scripts/warehouse-topology.yaml)
    OUTPUT_USDA     — local path to write the overlay (default /tmp/warehouse_scene_pack.usda)
    NUCLEUS_ROOT    — omniverse:// URL prefix where Phase-1 assets were seeded by
                      apps/platform/nucleus-seeder
    NUCLEUS_UPLOAD  — "1" to also push the output to Nucleus (default 1)
    NUCLEUS_USER / NUCLEUS_PASS — auth for the upload step (omniverse / master-password)
"""

from __future__ import annotations

# Bootstrap Kit before importing pxr / omni.client — same reason as
# apps/platform/nucleus-seeder/seed.py.
from isaacsim import SimulationApp  # noqa: E402
_app = SimulationApp({"headless": True})

import asyncio  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

import yaml  # noqa: E402
from pxr import Gf, Sdf, Usd, UsdGeom  # noqa: E402


TOPOLOGY = pathlib.Path(os.environ.get("TOPOLOGY_YAML", "/scripts/warehouse-topology.yaml"))
OUTPUT = pathlib.Path(os.environ.get("OUTPUT_USDA", "/tmp/warehouse_scene_pack.usda"))
NUCLEUS_ROOT = os.environ["NUCLEUS_ROOT"]  # e.g. omniverse://nucleus.apps.<cluster>/Projects/showcase/assets/Isaac/6.0
UPLOAD = os.environ.get("NUCLEUS_UPLOAD", "1") == "1"
NUCLEUS_USER = os.environ.get("NUCLEUS_USER", "omniverse")
NUCLEUS_PASS = os.environ.get("NUCLEUS_PASS", "")
SCENE_PACK_TARGET = os.environ.get(
    "NUCLEUS_TARGET",
    f"{NUCLEUS_ROOT}/ScenePacks/warehouse_scene_pack.usda",
)

WAREHOUSE_USD = f"{NUCLEUS_ROOT}/Isaac/Environments/Digital_Twin_Warehouse/small_warehouse_digital_twin.usd"

# Logical asset id → Nucleus URL. Kept here rather than in the topology yaml
# so the yaml stays portable across Nucleus deployments.
ASSET_REFS = {
    "nvidia/Forklift_A01": (
        f"{NUCLEUS_ROOT}/NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Equipment/Forklifts/"
        "Forklift_A/Standard_A/Forklift_A01_PR_V_NVD_01.usd"
    ),
    "nvidia/Cardboard_Boxes_on_Pallet/Standard_A/Default": (
        f"{NUCLEUS_ROOT}/NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/"
        "Cardboard_Boxes_on_Pallet/Standard_A/CbrdBoxesOnPlt_A01_106x106x80cm_PR_NVD_01.usd"
    ),
}


def _safe(name: str) -> str:
    return name.replace("-", "_").replace("/", "_")


def build_overlay(topo: dict) -> None:
    stage = Usd.Stage.CreateNew(str(OUTPUT))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    # Sublayer the warehouse USD — the overlay and the warehouse compose
    # into one stage at load time.
    stage.GetRootLayer().subLayerPaths.append(WAREHOUSE_USD)

    world = UsdGeom.Xform.Define(stage, Sdf.Path("/World"))
    stage.SetDefaultPrim(world.GetPrim())

    # Robots — reference the asset, place at home dock.
    for robot_id, robot in topo.get("robots", {}).items():
        ref_url = ASSET_REFS.get(robot["asset_ref"])
        if not ref_url:
            print(f"[warn] no asset_ref mapping for robot {robot_id}: {robot['asset_ref']}", flush=True)
            continue
        home = topo["docks"][robot["home"]]
        path = Sdf.Path(f"/World/Robots/{_safe(robot_id)}")
        xf = UsdGeom.Xform.Define(stage, path)
        xf.GetPrim().GetReferences().AddReference(ref_url)
        api = UsdGeom.XformCommonAPI(xf)
        api.SetTranslate(Gf.Vec3d(*home["position"]))
        api.SetRotate(Gf.Vec3f(0.0, 0.0, float(home["orientation_deg"])))

    # Approach-point markers — low green disks (visible in twin, non-physical).
    for ap_id, ap in topo.get("approach_points", {}).items():
        path = Sdf.Path(f"/World/ApproachPoints/{_safe(ap_id)}")
        cyl = UsdGeom.Cylinder.Define(stage, path)
        cyl.CreateRadiusAttr(0.35)
        cyl.CreateHeightAttr(0.05)
        cyl.CreateAxisAttr(UsdGeom.Tokens.z)
        cyl.CreateDisplayColorAttr([(0.1, 0.8, 0.2)])
        UsdGeom.XformCommonAPI(cyl).SetTranslate(Gf.Vec3d(*ap["position"]))

    # Dock markers — flat blue pads.
    for dock_id, dock in topo.get("docks", {}).items():
        path = Sdf.Path(f"/World/Docks/{_safe(dock_id)}")
        cube = UsdGeom.Cube.Define(stage, path)
        cube.CreateSizeAttr(1.0)
        cube.CreateDisplayColorAttr([(0.2, 0.5, 0.95)])
        api = UsdGeom.XformCommonAPI(cube)
        api.SetTranslate(Gf.Vec3d(*dock["position"]))
        api.SetScale(Gf.Vec3f(2.0, 2.0, 0.05))
        api.SetRotate(Gf.Vec3f(0.0, 0.0, float(dock["orientation_deg"])))

    # Cameras — UsdGeomCamera prims the twin subscribers + render viewports can bind to.
    for cam_id, cam in topo.get("cameras", {}).items():
        path = Sdf.Path(f"/World/Cameras/{_safe(cam_id)}")
        camera = UsdGeom.Camera.Define(stage, path)
        camera.CreateFocalLengthAttr(24.0)
        api = UsdGeom.XformCommonAPI(camera)
        api.SetTranslate(Gf.Vec3d(*cam["position"]))
        api.SetRotate(Gf.Vec3f(*[float(x) for x in cam["rotation_deg"]]))
        camera.GetPrim().CreateAttribute(
            "showcase:publishesTopic", Sdf.ValueTypeNames.String, custom=True
        ).Set(cam.get("publishes_topic", ""))

    stage.GetRootLayer().Save()
    print(f"[build] wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)", flush=True)


def _warmup_kit(seconds: float = 60.0) -> None:
    """Tick Kit's update loop for a wall-clock duration so `omni.kit.async_engine`
    (and therefore `omni.client`'s background connection machinery) is fully
    initialized before we make network calls.

    Short-running Kit apps (build-and-exit jobs that don't have a download
    phase to pad the startup) can otherwise reach the first `omni.client`
    call before the async engine has finished wiring up, and the auth
    callback never fires.
    """
    import time
    t0 = time.time()
    n = 0
    while time.time() - t0 < seconds:
        _app.update()
        time.sleep(0.05)
        n += 1
    print(f"[warmup] {seconds:.0f}s, {n} ticks", flush=True)


def _register_auth() -> None:
    """Register the auth callback before Kit's startup code attempts any
    Nucleus connections of its own. Kit will try to re-auth cached servers
    during startup; without our callback in place first, it falls through
    to device-flow (xdg-open) and blacklists the connection.
    """
    import omni.client

    print(f"[env] NUCLEUS_USER={NUCLEUS_USER!r} NUCLEUS_PASS len={len(NUCLEUS_PASS)}", flush=True)

    def _cb(url: str):
        print(f"[auth_cb] url={url}", flush=True)
        return (NUCLEUS_USER, NUCLEUS_PASS)

    # Hold the subscription on a module global so it outlives the function.
    global _AUTH_SUB
    _AUTH_SUB = omni.client.register_authentication_callback(_cb)  # noqa: F841


_AUTH_SUB = None


async def upload_to_nucleus() -> int:
    import omni.client
    # Ensure parent folder exists.
    parent = SCENE_PACK_TARGET.rsplit("/", 1)[0]
    r = await omni.client.create_folder_async(parent)
    if r not in (omni.client.Result.OK, omni.client.Result.ERROR_ALREADY_EXISTS):
        print(f"[upload] create_folder {parent}: {r}", flush=True)

    r = await omni.client.copy_async(
        str(OUTPUT), SCENE_PACK_TARGET, behavior=omni.client.CopyBehavior.OVERWRITE
    )
    if r != omni.client.Result.OK:
        print(f"[upload] FAIL {SCENE_PACK_TARGET}: {r}", flush=True)
        return 1
    print(f"[upload] {SCENE_PACK_TARGET} ok", flush=True)
    return 0


def main() -> int:
    # Register auth before Kit's startup does any connect attempts of its own.
    if UPLOAD:
        _register_auth()
    topo = yaml.safe_load(TOPOLOGY.read_text())
    build_overlay(topo)
    if UPLOAD:
        _warmup_kit()
        return asyncio.run(upload_to_nucleus())
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        _app.close()
    sys.exit(rc)
