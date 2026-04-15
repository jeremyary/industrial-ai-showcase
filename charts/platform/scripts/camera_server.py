"""In-process HTTP camera server for Isaac Sim.
Run this in Isaac Sim's Script Editor AFTER opening the warehouse scene.

Serves JPEG snapshots from camera annotators via HTTP. No disk I/O.
Uses viewport_manager.get_render_product() + app.next_update_async()
following NVIDIA's IsaacSimZMQ reference implementation.

Endpoints:
  GET /cameras/{name}/latest.jpg  — single JPEG snapshot
  GET /cameras/status             — JSON health check
"""

import importlib
importlib.invalidate_caches()

import asyncio
import io
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import numpy as np
from PIL import Image

import carb.settings
import omni.kit.app
import omni.usd
import omni.replicator.core as rep
from omni.replicator.core.scripts.utils import viewport_manager

# ---------------------------------------------------------------------------
# Cleanup previous instance
# ---------------------------------------------------------------------------
try:
    _prev_camera_server.shutdown()
    _prev_camera_server.server_close()
    time.sleep(0.5)
    print("[camera_server] Stopped previous HTTP server")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Disable Fabric Scene Delegate (causes empty annotator data)
# Reference: https://forums.developer.nvidia.com/t/294366
# ---------------------------------------------------------------------------
fsd = carb.settings.get_settings().get("/app/useFabricSceneDelegate")
if fsd:
    carb.settings.get_settings().set_bool("/app/useFabricSceneDelegate", False)
    print("[camera_server] Disabled Fabric Scene Delegate")

# Reduce temporal denoiser ghosting (lower = less ghosting, more noise)
carb.settings.get_settings().set_float("/rtx/post/temporalAntiAliasing/blendFactor", 0.01)
print("[camera_server] Reduced TAA blend factor for less ghosting")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVER_PORT = 8211
CAPTURE_INTERVAL = 0.25
JPEG_QUALITY = 80
RENDER_SIZE = (640, 480)

CAMERAS = {
    "overhead": "/World/SecurityCameras/Camera_Overhead",
    "forklift": "/World/SecurityCameras/Camera_ForkLift",
    "loading_dock": "/World/SecurityCameras/Camera_LoadingDock",
}

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
_frame_lock = threading.Lock()
_frames = {}       # {camera_name: jpeg_bytes}
_frame_times = {}  # {camera_name: timestamp}

# ---------------------------------------------------------------------------
# Render products + annotators (using viewport_manager, not rep.create)
# Reference: github.com/isaac-sim/IsaacSimZMQ annotators.py
# ---------------------------------------------------------------------------
_annotators = {}

stage = omni.usd.get_context().get_stage()

for name, cam_path in CAMERAS.items():
    prim = stage.GetPrimAtPath(cam_path)
    if not prim.IsValid():
        print(f"[camera_server] WARNING: Camera prim not found: {cam_path}")
        continue

    rp = viewport_manager.get_render_product(cam_path, RENDER_SIZE, False, f"{name}_cam_rp")
    rp_path = rp.hydra_texture.get_render_product_path()

    annot = rep.AnnotatorRegistry.get_annotator("rgb", device="cpu")
    annot.attach(rp_path)
    _annotators[name] = annot
    print(f"[camera_server] Attached annotator to {name} ({cam_path})")


def _encode_jpeg(rgba_array):
    """Encode an RGBA numpy array to JPEG bytes."""
    rgb = rgba_array[:, :, :3] if rgba_array.ndim == 3 and rgba_array.shape[2] == 4 else rgba_array
    if rgb.dtype != np.uint8:
        rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Async capture loop — uses app.next_update_async(), NOT rep.orchestrator
# ---------------------------------------------------------------------------
async def _capture_loop():
    """Periodically render and read annotator data."""
    app = omni.kit.app.get_app()

    # Warmup
    print("[camera_server] Warming up (10 frames)...")
    for i in range(10):
        await app.next_update_async()
        await asyncio.sleep(0.05)

    print("[camera_server] Capture loop started")
    while True:
        try:
            await app.next_update_async()

            for name, annot in _annotators.items():
                data = annot.get_data()
                if data is None:
                    continue
                arr = np.array(data)
                if arr.size == 0 or arr.ndim < 2:
                    continue

                jpeg_bytes = _encode_jpeg(arr)
                with _frame_lock:
                    _frames[name] = jpeg_bytes
                    _frame_times[name] = time.time()

        except Exception as e:
            print(f"[camera_server] Capture error: {e}")

        await asyncio.sleep(CAPTURE_INTERVAL)


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class CameraHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/cameras/status":
            self._serve_status()
            return

        parts = path.split("/")
        if len(parts) == 4 and parts[1] == "cameras":
            cam_name = parts[2]
            action = parts[3]

            if cam_name not in CAMERAS:
                self.send_error(404, f"Unknown camera: {cam_name}")
                return

            if action == "latest.jpg":
                self._serve_snapshot(cam_name)
            elif action == "stream":
                self._serve_mjpeg(cam_name)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def _serve_status(self):
        with _frame_lock:
            status = {
                "cameras": {},
                "server_time": time.time(),
            }
            for name in CAMERAS:
                has_frame = name in _frames
                status["cameras"][name] = {
                    "has_frame": has_frame,
                    "last_capture": _frame_times.get(name, 0),
                    "age_seconds": round(time.time() - _frame_times[name], 1) if has_frame else None,
                }

        body = json.dumps(status, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_snapshot(self, cam_name):
        with _frame_lock:
            jpeg = _frames.get(cam_name)

        if jpeg is None:
            self.send_error(503, "No frame available yet")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(jpeg)

    def _serve_mjpeg(self, cam_name):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_served = 0
        try:
            while True:
                with _frame_lock:
                    jpeg = _frames.get(cam_name)
                    ft = _frame_times.get(cam_name, 0)

                if jpeg is not None and ft > last_served:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n".encode())
                    self.wfile.write(b"\r\n")
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    last_served = ft

                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass


# ---------------------------------------------------------------------------
# Start HTTP server in a daemon thread
# ---------------------------------------------------------------------------
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

_server = ThreadedHTTPServer(("0.0.0.0", SERVER_PORT), CameraHandler)
_server.timeout = 0.5

def _run_server():
    print(f"[camera_server] HTTP server listening on port {SERVER_PORT}")
    _server.serve_forever()

_server_thread = threading.Thread(target=_run_server, daemon=True)
_server_thread.start()

_prev_camera_server = _server

# ---------------------------------------------------------------------------
# Start capture loop
# ---------------------------------------------------------------------------
asyncio.ensure_future(_capture_loop())

print(f"[camera_server] Ready!")
print(f"  Snapshot: http://localhost:{SERVER_PORT}/cameras/forklift/latest.jpg")
print(f"  Status:   http://localhost:{SERVER_PORT}/cameras/status")
