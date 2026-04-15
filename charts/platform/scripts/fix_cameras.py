"""Restore security cameras to known good positions.
Uses full 4x4 transform matrices captured from viewport positioning.
"""

import omni.usd
from pxr import UsdGeom, Gf

stage = omni.usd.get_context().get_stage()

# Full world transforms captured from manually positioned cameras
cameras = {
    "Camera_Overhead": Gf.Matrix4d(
        0.060785, 0.998151, 0.000000, 0.000000,
        -0.539113, 0.032831, 0.841593, 0.000000,
        0.840037, -0.051156, 0.540112, 0.000000,
        -26.768102, -73.801882, 9.199617, 1.000000,
    ),
    "Camera_ForkLift": Gf.Matrix4d(
        -0.043914, -0.999035, 0.000000, 0.000000,
        0.511165, -0.022469, 0.859189, 0.000000,
        -0.858360, 0.037731, 0.511658, 0.000000,
        -59.208839, -77.994807, 8.581080, 1.000000,
    ),
    "Camera_LoadingDock": Gf.Matrix4d(
        0.451282, 0.892381, 0.000000, 0.000000,
        -0.244812, 0.123803, 0.961634, 0.000000,
        0.858144, -0.433968, 0.274335, 0.000000,
        -0.905791, -89.511685, 7.362316, 1.000000,
    ),
}

for name, matrix in cameras.items():
    cam_path = f"/World/SecurityCameras/{name}"
    prim = stage.GetPrimAtPath(cam_path)

    if not prim.IsValid():
        print(f"Camera not found: {cam_path}")
        continue

    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTransformOp().Set(matrix)

    pos = matrix.ExtractTranslation()
    print(f"Restored: {name} at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")

print("\nDone! All cameras restored to saved positions.")
