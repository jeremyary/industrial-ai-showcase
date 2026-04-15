# This project was developed with assistance from AI tools.
"""
Run Cosmos Transfer2.5 augmentation on prepared control map clips.

Reads video clips from the prepare step, calls the Cosmos Transfer NIM API
with configurable prompt and control weights, extracts augmented frames,
and copies original KITTI labels to the augmented output directory.

Usage:
    python run_cosmos_augmentation.py \
        --clips-dir /output/cosmos_clips \
        --output-dir /output/cosmos_augmented/Camera \
        --labels-dir /output/palletjack_data/warehouse/Camera/object_detection \
        --endpoint http://cosmos-transfer-nim:8000 \
        --prompt "Industrial warehouse, bright fluorescent lighting"
"""
import argparse
import base64
import json
import os
import shutil
import subprocess

import requests


def encode_video(path):
    """Base64-encode a video file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_cosmos_transfer(endpoint, clip_dir, prompt, edge_weight, depth_weight, seg_weight):
    """Call Cosmos Transfer2.5 API with control maps from a clip directory."""
    payload = {
        "prompt": prompt,
        "video": encode_video(os.path.join(clip_dir, "rgb.mp4")),
    }

    edges_path = os.path.join(clip_dir, "edges.mp4")
    if os.path.exists(edges_path):
        payload["edge"] = {
            "control_weight": edge_weight,
            "control": encode_video(edges_path),
        }

    depth_path = os.path.join(clip_dir, "depth.mp4")
    if os.path.exists(depth_path):
        payload["depth"] = {
            "control_weight": depth_weight,
            "input_control": encode_video(depth_path),
        }

    seg_path = os.path.join(clip_dir, "segmentation.mp4")
    if os.path.exists(seg_path):
        payload["seg"] = {
            "control_weight": seg_weight,
            "control": encode_video(seg_path),
        }

    url = f"{endpoint}/cosmos/transfer"
    print(f"  POST {url} (payload ~{len(json.dumps(payload)) // 1024}KB)")

    resp = requests.post(url, json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()


def extract_frames_from_video(video_data_b64, output_dir, prefix="aug"):
    """Decode base64 video and extract frames as PNGs using ffmpeg."""
    os.makedirs(output_dir, exist_ok=True)

    # Write video to temp file
    tmp_video = os.path.join(output_dir, "_tmp_augmented.mp4")
    with open(tmp_video, "wb") as f:
        f.write(base64.b64decode(video_data_b64))

    # Extract frames
    cmd = [
        "ffmpeg", "-y", "-i", tmp_video,
        "-vsync", "0",
        os.path.join(output_dir, f"{prefix}_%04d.png"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(tmp_video)

    frames = sorted(f for f in os.listdir(output_dir) if f.startswith(prefix) and f.endswith(".png"))
    return frames


def main():
    parser = argparse.ArgumentParser(description="Run Cosmos Transfer augmentation")
    parser.add_argument("--clips-dir", required=True, help="Directory containing prepared clips")
    parser.add_argument("--output-dir", required=True, help="Output directory for augmented Camera data")
    parser.add_argument("--labels-dir", required=True, help="Original KITTI labels directory")
    parser.add_argument("--endpoint", required=True, help="Cosmos Transfer NIM endpoint URL")
    parser.add_argument("--prompt", default="Industrial warehouse, bright overhead fluorescent lighting, concrete floor")
    parser.add_argument("--edge-weight", type=float, default=1.0)
    parser.add_argument("--depth-weight", type=float, default=0.25)
    parser.add_argument("--seg-weight", type=float, default=0.25)
    args = parser.parse_args()

    rgb_out = os.path.join(args.output_dir, "rgb")
    labels_out = os.path.join(args.output_dir, "object_detection")
    os.makedirs(rgb_out, exist_ok=True)
    os.makedirs(labels_out, exist_ok=True)

    clips = sorted(d for d in os.listdir(args.clips_dir)
                   if os.path.isdir(os.path.join(args.clips_dir, d)) and d.startswith("clip_"))

    print(f"Found {len(clips)} clips to augment")
    total_frames = 0

    for clip_name in clips:
        clip_dir = os.path.join(args.clips_dir, clip_name)
        manifest_path = os.path.join(clip_dir, "frame_manifest.json")

        with open(manifest_path) as f:
            manifest = json.load(f)

        print(f"\nProcessing {clip_name} ({len(manifest)} frames)...")

        result = call_cosmos_transfer(
            args.endpoint, clip_dir, args.prompt,
            args.edge_weight, args.depth_weight, args.seg_weight,
        )

        if "video" in result:
            video_b64 = result["video"]
        elif "output" in result:
            video_b64 = result["output"]
        else:
            print(f"  WARNING: unexpected response format: {list(result.keys())}")
            continue

        tmp_extract = os.path.join(clip_dir, "_tmp_extract")
        extracted = extract_frames_from_video(video_b64, tmp_extract, prefix="aug")

        for i, entry in enumerate(manifest):
            if i >= len(extracted):
                print(f"  WARNING: fewer augmented frames ({len(extracted)}) than manifest ({len(manifest)})")
                break

            src_frame = os.path.join(tmp_extract, extracted[i])
            aug_fname = f"aug_{entry['frame_id']}.png"
            dst_frame = os.path.join(rgb_out, aug_fname)
            shutil.move(src_frame, dst_frame)

            orig_label = os.path.join(args.labels_dir, f"{entry['frame_id']}.txt")
            aug_label = os.path.join(labels_out, f"aug_{entry['frame_id']}.txt")
            if os.path.exists(orig_label):
                shutil.copy2(orig_label, aug_label)

            total_frames += 1

        shutil.rmtree(tmp_extract, ignore_errors=True)
        print(f"  Augmented {min(len(extracted), len(manifest))} frames")

    print(f"\nDone: {total_frames} augmented frames written to {args.output_dir}")


if __name__ == "__main__":
    main()
