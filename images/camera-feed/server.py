"""Camera feed replay server.

Serves frames via HTTP, simulating IP cameras.
Supports two input modes:
  1. Pre-extracted JPEGs in /data/frames/{camera_name}/*.jpg
  2. MP4 video files in /data/videos/{camera_name}.mp4

When MP4 files are found, frames are extracted at startup using OpenCV.
Frames cycle based on wall-clock time and configured frame rate.

Endpoints:
  GET /cameras/{name}/latest.jpg  — current frame (cycles through sequence)
  GET /cameras/list               — JSON list of camera names
  GET /cameras/status             — JSON listing cameras and frame counts
  GET /healthz                    — liveness probe
"""

import os
import time
from pathlib import Path

from flask import Flask, Response, jsonify

app = Flask(__name__)

FRAME_DIR = Path(os.environ.get("FRAME_DIR", "/data/frames"))
VIDEO_DIR = Path(os.environ.get("VIDEO_DIR", "/data/videos"))
FRAME_RATE = float(os.environ.get("FRAME_RATE", "2"))
EXTRACT_FPS = float(os.environ.get("EXTRACT_FPS", "2"))

# In-memory cache: camera_name -> list of JPEG bytes
_frame_cache: dict[str, list[bytes]] = {}


def extract_frames_from_video(video_path: Path, fps: float = 2.0) -> list[bytes]:
    """Extract JPEG frames from an MP4 file using OpenCV."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  WARNING: Cannot open video {video_path}")
        return []

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(video_fps / fps))
    duration = total_frames / video_fps if video_fps > 0 else 0

    print(f"  Video: {video_path.name} ({total_frames} frames, {video_fps:.1f}fps, {duration:.1f}s)")
    print(f"  Extracting every {frame_interval} frames ({fps} fps target)...")

    frames = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append(buf.tobytes())
        frame_idx += 1

    cap.release()
    print(f"  Extracted {len(frames)} frames")
    return frames


def load_jpeg_directory(camera_dir: Path) -> list[bytes]:
    """Load pre-extracted JPEG files from a directory."""
    jpg_files = sorted(camera_dir.glob("*.jpg"))
    if not jpg_files:
        return []
    frames = [f.read_bytes() for f in jpg_files]
    print(f"  Directory: {camera_dir.name} ({len(frames)} JPEGs)")
    return frames


def init_cameras():
    """Load frames from all available sources into memory cache."""
    print("Initializing camera feeds...")

    # Load from MP4 videos first
    if VIDEO_DIR.exists():
        for video_file in sorted(VIDEO_DIR.glob("*.mp4")):
            camera_name = video_file.stem
            frames = extract_frames_from_video(video_file, EXTRACT_FPS)
            if frames:
                _frame_cache[camera_name] = frames

    # Load from JPEG directories (won't overwrite video-sourced cameras)
    if FRAME_DIR.exists():
        for camera_dir in sorted(FRAME_DIR.iterdir()):
            if camera_dir.is_dir() and camera_dir.name not in _frame_cache:
                frames = load_jpeg_directory(camera_dir)
                if frames:
                    _frame_cache[camera_dir.name] = frames

    if _frame_cache:
        print(f"Loaded {len(_frame_cache)} cameras: {', '.join(_frame_cache.keys())}")
        for name, frames in _frame_cache.items():
            print(f"  {name}: {len(frames)} frames ({len(frames)/FRAME_RATE:.0f}s loop)")
    else:
        print("WARNING: No camera feeds found!")
        print(f"  Looked in VIDEO_DIR={VIDEO_DIR} for *.mp4")
        print(f"  Looked in FRAME_DIR={FRAME_DIR} for */*.jpg")


@app.route("/cameras/<camera_name>/latest.jpg")
def latest_frame(camera_name):
    if camera_name not in _frame_cache or not _frame_cache[camera_name]:
        return Response(f"Unknown camera: {camera_name}", status=404)

    frames = _frame_cache[camera_name]
    idx = int(time.time() * FRAME_RATE) % len(frames)

    return Response(
        frames[idx],
        mimetype="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.route("/cameras/list")
def camera_list():
    return jsonify(list(_frame_cache.keys()))


@app.route("/cameras/status")
def status():
    return jsonify(
        {
            "cameras": {
                name: {
                    "frame_count": len(frames),
                    "loop_duration_s": round(len(frames) / FRAME_RATE, 1),
                }
                for name, frames in _frame_cache.items()
            },
            "frame_rate": FRAME_RATE,
            "server_time": time.time(),
        }
    )


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8211"))
    init_cameras()
    print(f"\nCamera feed server starting on port {port}")
    print(f"  Frame rate: {FRAME_RATE} fps")
    app.run(host="0.0.0.0", port=port)
