# This project was developed with assistance from AI tools.
"""
Prepare Cosmos Transfer control maps from Isaac Sim Replicator output.

Reads RGB, depth, and semantic segmentation PNGs from the Replicator output
directory, chunks them into video clips, and derives edge maps. Output clips
are ready for the Cosmos Transfer2.5 API.

Usage:
    python prepare_control_maps.py \
        --input-dir /output/palletjack_data/warehouse/Camera \
        --output-dir /output/cosmos_clips \
        --clip-length 25 \
        --height 544 --width 960
"""
import argparse
import json
import os
import subprocess

import cv2
import numpy as np


def sorted_frames(directory, ext=".png"):
    """Return frame filenames sorted numerically (0.png, 1.png, ..., 10.png)."""
    files = [f for f in os.listdir(directory) if f.endswith(ext)]
    files.sort(key=lambda fn: int(os.path.splitext(fn)[0]))
    return files


def normalize_depth(depth_16bit):
    """Normalize 16-bit linear depth to 8-bit grayscale for Cosmos Transfer."""
    depth_float = depth_16bit.astype(np.float32)
    # Clip outliers (e.g., sky/background at max depth)
    p99 = np.percentile(depth_float[depth_float > 0], 99) if np.any(depth_float > 0) else 1.0
    depth_clipped = np.clip(depth_float, 0, p99)
    # Normalize to 0-255 range
    if p99 > 0:
        depth_norm = (depth_clipped / p99 * 255).astype(np.uint8)
    else:
        depth_norm = np.zeros_like(depth_16bit, dtype=np.uint8)
    return depth_norm


def compute_edges(rgb_image):
    """Compute Canny edge detection on an RGB image."""
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
    CANNY_LOW, CANNY_HIGH = 50, 150
    edges = cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)
    return edges


def frames_to_mp4(frame_paths, output_path, height, width, fps=10):
    """Encode a list of image files to an MP4 video using ffmpeg."""
    # Write frame list to a temporary file for ffmpeg concat
    list_path = output_path + ".frames.txt"
    with open(list_path, "w") as f:
        for path in frame_paths:
            f.write(f"file '{path}'\n")
            f.write(f"duration {1.0/fps}\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-vf", f"scale={width}:{height}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "18",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(list_path)


def process_clip(clip_frames, input_dir, output_dir, clip_idx, height, width):
    """Process a single clip of frames into control map videos."""
    clip_dir = os.path.join(output_dir, f"clip_{clip_idx:04d}")
    os.makedirs(clip_dir, exist_ok=True)

    # Temporary directories for processed frames
    tmp_dirs = {}
    for kind in ["rgb", "depth", "segmentation", "edges"]:
        d = os.path.join(clip_dir, f"tmp_{kind}")
        os.makedirs(d, exist_ok=True)
        tmp_dirs[kind] = d

    frame_manifest = []

    for i, fname in enumerate(clip_frames):
        frame_id = os.path.splitext(fname)[0]
        frame_manifest.append({"index": i, "filename": fname, "frame_id": frame_id})

        rgb_path = os.path.join(input_dir, "rgb", fname)
        rgb = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
        if rgb.shape[2] == 4:
            rgb = rgb[:, :, :3]
        cv2.imwrite(os.path.join(tmp_dirs["rgb"], f"{i:04d}.png"), rgb)

        depth_path = os.path.join(input_dir, "depth", fname)
        depth_16 = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
        depth_8 = normalize_depth(depth_16)
        cv2.imwrite(os.path.join(tmp_dirs["depth"], f"{i:04d}.png"), depth_8)

        seg_path = os.path.join(input_dir, "semantic_segmentation", fname)
        seg = cv2.imread(seg_path, cv2.IMREAD_UNCHANGED)
        if seg.shape[2] == 4:
            seg = seg[:, :, :3]
        cv2.imwrite(os.path.join(tmp_dirs["segmentation"], f"{i:04d}.png"), seg)

        edges = compute_edges(rgb)
        cv2.imwrite(os.path.join(tmp_dirs["edges"], f"{i:04d}.png"), edges)

    # Encode each channel to MP4
    for kind in ["rgb", "depth", "segmentation", "edges"]:
        frames = sorted(os.listdir(tmp_dirs[kind]))
        frame_paths = [os.path.join(tmp_dirs[kind], f) for f in frames]
        mp4_path = os.path.join(clip_dir, f"{kind}.mp4")
        frames_to_mp4(frame_paths, mp4_path, height, width)
        print(f"  {kind}.mp4: {os.path.getsize(mp4_path)} bytes")

    # Write manifest
    manifest_path = os.path.join(clip_dir, "frame_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(frame_manifest, f, indent=2)

    # Cleanup temp frame directories
    for kind in tmp_dirs:
        for fname in os.listdir(tmp_dirs[kind]):
            os.remove(os.path.join(tmp_dirs[kind], fname))
        os.rmdir(tmp_dirs[kind])

    return len(clip_frames)


def main():
    parser = argparse.ArgumentParser(description="Prepare Cosmos Transfer control maps")
    parser.add_argument("--input-dir", required=True, help="Replicator Camera output directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for clips")
    parser.add_argument("--clip-length", type=int, default=25, help="Frames per clip")
    parser.add_argument("--height", type=int, default=544)
    parser.add_argument("--width", type=int, default=960)
    args = parser.parse_args()

    frames = sorted_frames(os.path.join(args.input_dir, "rgb"))
    print(f"Found {len(frames)} frames")

    os.makedirs(args.output_dir, exist_ok=True)

    total_processed = 0
    for clip_idx, start in enumerate(range(0, len(frames), args.clip_length)):
        clip_frames = frames[start:start + args.clip_length]
        print(f"Processing clip {clip_idx} ({len(clip_frames)} frames)...")
        n = process_clip(clip_frames, args.input_dir, args.output_dir, clip_idx, args.height, args.width)
        total_processed += n

    num_clips = (len(frames) + args.clip_length - 1) // args.clip_length
    print(f"\nDone: {num_clips} clips, {total_processed} frames total")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
