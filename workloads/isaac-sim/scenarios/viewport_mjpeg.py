# This project was developed with assistance from AI tools.
"""MJPEG viewport broadcaster for Isaac Sim sessions.

Runs inside Kit (via `--exec`) alongside the warehouse scenario. Captures the
active viewport each frame via `omni.kit.viewport.utility.capture_viewport_to_buffer`,
JPEG-encodes on a worker thread, and serves `multipart/x-mixed-replace` on
port 8090. The Showcase Console embeds this as a plain `<img>` tag so the
demo gets a reliable, low-fuss view of just the scene — not the whole Kit
application UI.

Threading model:
  - Main Kit thread: subscribes to the app update-event stream. Every N
    ticks it schedules a viewport capture. Must run here because
    `capture_viewport_to_buffer` creates an `asyncio.Future` internally
    and that requires an event loop on the current thread — Kit's main
    thread is the only one that has one.
  - Kit render thread (callback): pushes the raw RGBA pixel bytes onto a
    bounded queue. No JPEG encoding here — encoding is CPU-heavy and we
    don't want to stall Kit's render thread.
  - Worker thread: pops raw bytes, JPEG-encodes with Pillow, publishes to
    the frame broker.
  - HTTP thread: serves MJPEG over multipart/x-mixed-replace from the
    broker to any number of browser clients.
"""

import ctypes
import io
import queue
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import carb


_PyCapsule_GetPointer = ctypes.pythonapi.PyCapsule_GetPointer
_PyCapsule_GetPointer.restype = ctypes.c_void_p
_PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]

try:
    from PIL import Image
except ImportError:  # pragma: no cover — Kit's python ships PIL
    Image = None


JPEG_QUALITY = 70
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8090
# Every Nth Kit app-update event triggers a capture. Kit runs the app
# update loop near the render rate (60 Hz target). Capture allocates a
# Vulkan fence + staging buffer per call; if we over-schedule (or if
# previous captures fail), the driver leaks those and Kit eventually
# OOMs. 10 Hz is plenty for a <img> tag and leaves headroom for Kit.
CAPTURE_EVERY_N_TICKS = 6
# Bounded raw-frame queue: if the encoder can't keep up we drop frames
# rather than grow unbounded memory. One slot is enough for MJPEG — we
# always want the freshest frame.
RAW_QUEUE_MAX = 1


# ---- Frame broker (latest-wins) ---------------------------------------------


class _FrameBroker:
    def __init__(self) -> None:
        self._frame: bytes | None = None
        self._seq: int = 0
        self._cv = threading.Condition()

    def publish(self, frame: bytes) -> None:
        with self._cv:
            self._frame = frame
            self._seq += 1
            self._cv.notify_all()

    def wait_newer_than(self, last_seq: int, timeout: float = 5.0):
        with self._cv:
            if self._seq > last_seq:
                return self._frame, self._seq
            self._cv.wait(timeout=timeout)
            if self._seq > last_seq:
                return self._frame, self._seq
        return None, last_seq


_BROKER = _FrameBroker()
_RAW_QUEUE: "queue.Queue[tuple[int, int, bytes]]" = queue.Queue(maxsize=RAW_QUEUE_MAX)
_capture_err_count = 0


# ---- Capture callback: runs on Kit's render thread --------------------------


def _on_capture(*args) -> None:
    # Kit 110's ByteCapture callback signature is
    #   on_capture(buffer_capsule, buffer_size, width, height, format_str)
    # where buffer_capsule is a PyCapsule wrapping a void* to driver-owned
    # RGBA memory. We copy it out immediately (before the callback returns)
    # since Kit may reuse or free the buffer afterwards.
    try:
        if len(args) >= 5:
            buffer_capsule = args[0]
            buffer_size = int(args[1])
            width = int(args[2])
            height = int(args[3])
            if buffer_size <= 0 or width <= 0 or height <= 0:
                return
            ptr = _PyCapsule_GetPointer(buffer_capsule, None)
            if not ptr:
                return
            pixels = bytes((ctypes.c_ubyte * buffer_size).from_address(ptr))
        else:
            wrapper = args[0]
            if hasattr(wrapper, "get_buffer"):
                width = wrapper.get_width()
                height = wrapper.get_height()
                pixels = bytes(wrapper.get_buffer())
            else:
                width, height, _fmt, buf = wrapper
                pixels = bytes(buf)
    except Exception:
        # Rate-limit — logging on every frame would itself impact Kit.
        global _capture_err_count
        _capture_err_count += 1
        if _capture_err_count <= 3 or _capture_err_count % 200 == 0:
            carb.log_warn(
                f"viewport_mjpeg: capture extract failed (#{_capture_err_count}): "
                + traceback.format_exc()
            )
        return
    if not pixels or width <= 0 or height <= 0:
        return
    # Drop oldest if queue is full — browser should see the newest frame.
    try:
        _RAW_QUEUE.put_nowait((width, height, pixels))
    except queue.Full:
        try:
            _RAW_QUEUE.get_nowait()
        except queue.Empty:
            pass
        try:
            _RAW_QUEUE.put_nowait((width, height, pixels))
        except queue.Full:
            pass


# ---- Capture dispatcher: runs on Kit's main thread --------------------------


_tick = 0
_update_sub = None  # noqa: N816 — Kit subscription handle must outlive this fn


def _schedule_capture(event) -> None:  # noqa: ARG001 — Kit passes an event arg
    global _tick
    _tick += 1
    if _tick % CAPTURE_EVERY_N_TICKS != 0:
        return
    try:
        from omni.kit.viewport.utility import capture_viewport_to_buffer, get_active_viewport
    except Exception:
        return
    try:
        vp = get_active_viewport()
        if vp is None:
            return
        capture_viewport_to_buffer(vp, _on_capture)
    except Exception:
        # Rate-limit noisy warnings — first time only.
        if _tick < CAPTURE_EVERY_N_TICKS * 5:
            carb.log_warn("viewport_mjpeg: capture schedule failed: " + traceback.format_exc())


# ---- Encoder worker thread --------------------------------------------------


def _encode_jpeg(pixels: bytes, width: int, height: int) -> bytes:
    if Image is None:
        raise RuntimeError("Pillow not available in Kit's Python")
    img = Image.frombuffer("RGBA", (width, height), pixels, "raw", "RGBA", 0, 1)
    img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY)
    return out.getvalue()


def _encoder_loop() -> None:
    while True:
        try:
            width, height, pixels = _RAW_QUEUE.get(timeout=30.0)
        except queue.Empty:
            continue
        try:
            jpeg = _encode_jpeg(pixels, width, height)
            _BROKER.publish(jpeg)
        except Exception:
            carb.log_error("viewport_mjpeg: encode failed: " + traceback.format_exc())


# ---- HTTP server ------------------------------------------------------------


class _MjpegHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 — stdlib signature
        return  # silence per-request access logs

    def _send_cors(self) -> None:
        # The Console serves from a different subdomain than this MJPEG
        # route, so cross-origin fetch() requires permissive CORS. A
        # plain <img> tag wouldn't need this, but the Canvas-parsing
        # consumer uses fetch() for single-connection stream control.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self) -> None:  # noqa: N802 — stdlib naming
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 — stdlib naming
        if self.path in ("/healthz", "/health"):
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path not in ("/", "/stream.mjpg", "/stream"):
            self.send_response(404)
            self._send_cors()
            self.end_headers()
            return
        self.send_response(200)
        self._send_cors()
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        last_seq = 0
        while True:
            frame, last_seq = _BROKER.wait_newer_than(last_seq, timeout=10.0)
            if frame is None:
                continue
            try:
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return


def _serve_forever() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), _MjpegHandler)
    server.daemon_threads = True
    server.allow_reuse_address = True
    carb.log_info(f"viewport_mjpeg: serving on http://{LISTEN_HOST}:{LISTEN_PORT}/stream.mjpg")
    server.serve_forever()


# ---- Bootstrap --------------------------------------------------------------


def start() -> None:
    global _update_sub
    threading.Thread(target=_serve_forever, daemon=True, name="mjpeg-http").start()
    threading.Thread(target=_encoder_loop, daemon=True, name="mjpeg-encoder").start()
    # Subscribe on Kit's main thread — needs its asyncio loop context.
    try:
        import omni.kit.app
        _update_sub = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(_schedule_capture, name="viewport_mjpeg-capture")
        )
        carb.log_info("viewport_mjpeg: subscribed to app update stream")
    except Exception:
        carb.log_error("viewport_mjpeg: failed to subscribe: " + traceback.format_exc())
    carb.log_info("viewport_mjpeg: started http + encoder threads")


start()
