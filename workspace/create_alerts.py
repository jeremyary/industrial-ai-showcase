"""Create alert prims in the warehouse scene for safety status visualization.
Run this in Isaac Sim's Script Editor before starting the MQTT bridge.

Creates:
- Alert marker spheres at each camera position (green/yellow/red status indicators)
- Zone highlight planes on the floor (semi-transparent danger overlays)
- A status text prim (optional, for viewport display)
"""

import omni.usd
from pxr import UsdGeom, UsdShade, Gf, Sdf

stage = omni.usd.get_context().get_stage()

# Create parent Xform for alerts
alerts_path = "/World/Alerts"
if not stage.GetPrimAtPath(alerts_path):
    UsdGeom.Xform.Define(stage, alerts_path)

# ---- Helper: create a colored material ----
def create_material(name, color, opacity=1.0):
    mat_path = f"/World/Alerts/Materials/{name}"
    mat = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(color)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    if opacity < 1.0:
        shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


# ---- Create materials ----
mat_safe = create_material("SafeGreen", Gf.Vec3f(0.0, 0.8, 0.0))
mat_caution = create_material("CautionYellow", Gf.Vec3f(1.0, 0.8, 0.0))
mat_danger = create_material("DangerRed", Gf.Vec3f(1.0, 0.0, 0.0))
mat_zone_danger = create_material("ZoneDangerRed", Gf.Vec3f(1.0, 0.0, 0.0), opacity=0.3)
mat_zone_caution = create_material("ZoneCautionYellow", Gf.Vec3f(1.0, 0.8, 0.0), opacity=0.3)

# ---- Alert marker spheres (at ground level near zone centers) ----
# Placed on the floor so they don't block camera views
alert_positions = {
    "overhead": Gf.Vec3d(-23, -70, 0.5),       # center of warehouse, ground level
    "forklift": Gf.Vec3d(-45, -80, 0.5),       # forklift zone corner
    "loading_dock": Gf.Vec3d(-20, -50, 0.5),   # loading dock area
}

for cam_id, pos in alert_positions.items():
    sphere_path = f"/World/Alerts/{cam_id}_Alert"
    sphere = UsdGeom.Sphere.Define(stage, sphere_path)
    sphere.GetRadiusAttr().Set(0.5)

    xform = UsdGeom.Xformable(sphere.GetPrim())
    xform.ClearXformOpOrder()
    translate_op = xform.AddTranslateOp()
    translate_op.Set(pos)

    # Bind green material (safe by default)
    UsdShade.MaterialBindingAPI.Apply(sphere.GetPrim()).Bind(mat_safe)

    print(f"Created alert sphere: {sphere_path}")

# ---- Zone highlight planes (on the floor) ----
# Zones roughly correspond to camera coverage areas
zones = {
    "overhead_zone": {
        "pos": Gf.Vec3d(-23, -70, 0.05),  # just above floor
        "scale": Gf.Vec3f(15, 15, 1),      # 30m x 30m coverage
    },
    "forklift_zone": {
        "pos": Gf.Vec3d(-45, -80, 0.05),
        "scale": Gf.Vec3f(10, 10, 1),      # 20m x 20m
    },
    "loading_dock_zone": {
        "pos": Gf.Vec3d(-20, -50, 0.05),
        "scale": Gf.Vec3f(10, 8, 1),       # 20m x 16m
    },
}

for zone_id, props in zones.items():
    plane_path = f"/World/Alerts/{zone_id}"
    plane = UsdGeom.Mesh.Define(stage, plane_path)

    # Simple quad
    plane.GetPointsAttr().Set([
        Gf.Vec3f(-1, -1, 0), Gf.Vec3f(1, -1, 0),
        Gf.Vec3f(1, 1, 0), Gf.Vec3f(-1, 1, 0),
    ])
    plane.GetFaceVertexCountsAttr().Set([4])
    plane.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
    plane.GetNormalsAttr().Set([Gf.Vec3f(0, 0, 1)] * 4)

    xform = UsdGeom.Xformable(plane.GetPrim())
    xform.ClearXformOpOrder()
    translate_op = xform.AddTranslateOp()
    translate_op.Set(props["pos"])
    scale_op = xform.AddScaleOp()
    scale_op.Set(props["scale"])

    # Start invisible
    UsdGeom.Imageable(plane.GetPrim()).MakeInvisible()

    # Bind zone danger material
    UsdShade.MaterialBindingAPI.Apply(plane.GetPrim()).Bind(mat_zone_danger)

    print(f"Created zone plane: {plane_path} (hidden)")

print("\nAlert prims created! Save the scene, then run mqtt_bridge.py")
