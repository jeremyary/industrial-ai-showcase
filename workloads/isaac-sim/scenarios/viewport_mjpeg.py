# This project was developed with assistance from AI tools.
"""HLS viewport streamer for Isaac Sim.

Creates a render product (HydraTexture) attached to the scene camera,
reads RGBA frames via the replicator "rgb" annotator on every Nth Kit
update tick, and pipes them to an ffmpeg subprocess that encodes H.264
with NVENC and outputs HLS segments.  The built-in HTTP server serves
the .m3u8 playlist and .ts segments so the Showcase Console can embed
the stream in a standard <video> element via hls.js.

Render products are independent of the viewport window — they create
their own GPU render target and produce frames on every Kit update
regardless of whether a display or WebRTC client is connected.  This
is the same pipeline Isaac Sim uses for synthetic data generation.
"""

import os
import queue
import subprocess
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import carb


FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
FFMPEG_PATH = "/tmp/ffmpeg"
HLS_DIR = "/tmp/hls"
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8090

CAMERA_PRIM = "/OmniverseKit_Persp"
RESOLUTION = (1920, 1080)
CAPTURE_EVERY_N_TICKS = 1
TARGET_FPS = 60

_ffmpeg_proc = None
_ffmpeg_lock = threading.Lock()
_rgb_annotator = None
_update_sub = None
_tick = 0
_frame_count = 0
_setup_done = False
_frame_queue: queue.Queue = queue.Queue(maxsize=4)


# ---- ffmpeg management -------------------------------------------------------


def _download_ffmpeg() -> bool:
    if os.path.isfile(FFMPEG_PATH):
        return True
    print("[viewport_stream] downloading ffmpeg...", flush=True)
    try:
        import lzma
        import tarfile
        import urllib.request
        resp = urllib.request.urlopen(FFMPEG_URL, timeout=120)
        with lzma.open(resp) as xz:
            with tarfile.open(fileobj=xz, mode="r|") as tar:
                for m in tar:
                    if m.name.endswith("/bin/ffmpeg") and m.isfile():
                        f = tar.extractfile(m)
                        if f:
                            with open(FFMPEG_PATH, "wb") as out:
                                out.write(f.read())
                            os.chmod(FFMPEG_PATH, 0o755)
                            print("[viewport_stream] ffmpeg downloaded", flush=True)
                            return True
    except Exception:
        print(f"[viewport_stream] ffmpeg download failed: {traceback.format_exc()}", flush=True)
    return False


def _start_ffmpeg() -> None:
    global _ffmpeg_proc
    os.makedirs(HLS_DIR, exist_ok=True)
    for f in os.listdir(HLS_DIR):
        os.remove(os.path.join(HLS_DIR, f))
    w, h = RESOLUTION
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "rawvideo",
        "-pixel_format", "rgba",
        "-video_size", f"{w}x{h}",
        "-framerate", str(TARGET_FPS),
        "-i", "pipe:0",
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-tune", "ll",
        "-b:v", "8M",
        "-maxrate", "12M",
        "-bufsize", "16M",
        "-g", str(TARGET_FPS),
        "-keyint_min", str(TARGET_FPS),
        "-f", "hls",
        "-hls_time", "0.5",
        "-hls_list_size", "6",
        "-hls_flags", "delete_segments+append_list+omit_endlist",
        "-hls_segment_type", "mpegts",
        os.path.join(HLS_DIR, "stream.m3u8"),
    ]
    _ffmpeg_proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    print(f"[viewport_stream] ffmpeg started ({w}x{h} -> HLS/NVENC)", flush=True)


# ---- Render product setup (deferred until scene is loaded) -------------------


def _scene_is_loaded() -> bool:
    """Return True once the USD stage has a loaded scene (not just Kit defaults)."""
    try:
        import omni.usd
        ctx = omni.usd.get_context()
        if ctx is None:
            return False
        stage = ctx.get_stage()
        if stage is None:
            return False
        return stage.GetPrimAtPath(CAMERA_PRIM).IsValid()
    except Exception:
        return False


def _setup_render_product() -> bool:
    """Create a render product + RGB annotator. Returns True on success."""
    global _rgb_annotator, _setup_done

    if not _scene_is_loaded():
        return False

    try:
        import omni.replicator.core as rep
    except Exception:
        print(f"[viewport_stream] omni.replicator.core not available: {traceback.format_exc()}", flush=True)
        return False

    try:
        rp = rep.create.render_product(CAMERA_PRIM, resolution=RESOLUTION)
        _rgb_annotator = rep.AnnotatorRegistry.get_annotator("rgb")
        _rgb_annotator.attach([rp.path])
        _setup_done = True
        print(f"[viewport_stream] render product created at {rp.path}", flush=True)
        return True
    except Exception:
        print(f"[viewport_stream] render product setup failed: {traceback.format_exc()}", flush=True)
        return False


# ---- Capture tick: reads annotator data and writes to ffmpeg -----------------


def _on_update(event) -> None:
    """Grab annotator frame and enqueue for the writer thread (non-blocking)."""
    global _tick, _setup_done

    _tick += 1
    if _tick % CAPTURE_EVERY_N_TICKS != 0:
        return

    if not _setup_done:
        if _tick % (CAPTURE_EVERY_N_TICKS * 15) == 0:
            _setup_render_product()
        return

    if _rgb_annotator is None:
        return

    try:
        data = _rgb_annotator.get_data()
    except Exception:
        _setup_done = False
        return

    if data is None:
        return

    if isinstance(data, dict):
        data = data.get("data", None)
        if data is None:
            return

    if hasattr(data, "ndim"):
        if data.ndim != 3 or data.shape[0] == 0:
            return
        raw = data.tobytes()
    else:
        raw = bytes(data)

    if not raw:
        return

    try:
        _frame_queue.put_nowait(raw)
    except queue.Full:
        pass


def _writer_loop() -> None:
    """Drain the frame queue and write to ffmpeg stdin (runs in its own thread)."""
    global _ffmpeg_proc, _frame_count

    while True:
        raw = _frame_queue.get()

        if _ffmpeg_proc is None:
            if not os.path.isfile(FFMPEG_PATH):
                continue
            _start_ffmpeg()

        try:
            _ffmpeg_proc.stdin.write(raw)
            _ffmpeg_proc.stdin.flush()
            _frame_count += 1
            if _frame_count == 1:
                print("[viewport_stream] first frame written to ffmpeg", flush=True)
            elif _frame_count % 1800 == 0:
                print(f"[viewport_stream] {_frame_count} frames written", flush=True)
        except (BrokenPipeError, OSError):
            print("[viewport_stream] ffmpeg pipe broken, restarting", flush=True)
            with _ffmpeg_lock:
                try:
                    _ffmpeg_proc.kill()
                except Exception:
                    pass
                _ffmpeg_proc = None


# ---- HTTP server: serves HLS + health endpoints -----------------------------


class _HlsHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path in ("/healthz", "/health"):
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        if self.path.startswith("/hls/"):
            filename = self.path[5:].split("?")[0]
            if "/" in filename or ".." in filename:
                self.send_response(403)
                self.end_headers()
                return
            filepath = os.path.join(HLS_DIR, filename)
            if not os.path.isfile(filepath):
                self.send_response(404)
                self._send_cors()
                self.end_headers()
                return
            with open(filepath, "rb") as f:
                file_data = f.read()
            self.send_response(200)
            self._send_cors()
            if filename.endswith(".m3u8"):
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            elif filename.endswith(".ts"):
                self.send_header("Content-Type", "video/mp2t")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(file_data)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            try:
                self.wfile.write(file_data)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_response(404)
        self._send_cors()
        self.end_headers()


def _serve_forever() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), _HlsHandler)
    server.daemon_threads = True
    server.allow_reuse_address = True
    print(f"[viewport_stream] HLS server on http://{LISTEN_HOST}:{LISTEN_PORT}/hls/stream.m3u8", flush=True)
    server.serve_forever()


# ---- Bootstrap ---------------------------------------------------------------


def start() -> None:
    global _update_sub

    threading.Thread(target=_download_ffmpeg, daemon=True, name="ffmpeg-dl").start()

    threading.Thread(target=_serve_forever, daemon=True, name="hls-http").start()

    threading.Thread(target=_writer_loop, daemon=True, name="ffmpeg-writer").start()

    try:
        import omni.kit.app
        _update_sub = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(_on_update, name="viewport_stream-capture")
        )
        print("[viewport_stream] subscribed to update stream, will set up render product on first scene tick", flush=True)
    except Exception:
        print(f"[viewport_stream] failed to subscribe: {traceback.format_exc()}", flush=True)


start()
