#!/usr/bin/env python3
"""Edge inference service: watches camera frames, analyzes with Cosmos, publishes to MQTT."""

import json
import time
import glob
import os
import re
import requests
import paho.mqtt.client as mqtt

VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "/models/cosmos-reason2-2b-w4a16"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "warehouse/safety"
CAMERA_DIR = os.environ.get("CAMERA_DIR", "./workspace/camera_feeds")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "5.0"))

SAFETY_PROMPT = """You are a warehouse safety monitoring AI analyzing security camera footage.

Analyze this image and report:
1. All people visible and their locations
2. All vehicles/forklifts and whether they are moving or stationary
3. Any safety hazards:
   - Workers in forklift operating paths
   - Fallen or unstable pallets/objects
   - Blocked emergency exits or aisles
   - Missing safety equipment
4. Overall safety status: SAFE, CAUTION, or DANGER

Respond ONLY in JSON format:
{
  "people": [{"description": "...", "in_danger": true/false}],
  "vehicles": [{"type": "forklift", "status": "moving/stationary"}],
  "hazards": [{"type": "...", "severity": "low/medium/high", "description": "..."}],
  "overall_status": "SAFE",
  "summary": "One-sentence summary"
}"""


def analyze_frame(image_path: str, camera_id: str) -> dict | None:
    """Send a frame to Cosmos-Reason2 for analysis."""
    try:
        # Convert host path to container path for vLLM
        filename = os.path.basename(image_path)
        container_path = f"/camera_feeds/{filename}"

        response = requests.post(
            VLLM_URL,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"file://{container_path}"},
                            },
                            {"type": "text", "text": SAFETY_PROMPT},
                        ],
                    }
                ],
                "max_tokens": 512,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()

        # Cosmos-Reason2 puts output in reasoning field via qwen3 parser
        message = result["choices"][0]["message"]
        content = message.get("reasoning") or message.get("content") or ""

        # Extract JSON from the response (may be wrapped in ```json blocks)
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())

        print(f"  No JSON found in response for {camera_id}")
        return None

    except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Analysis failed for {camera_id}: {e}")
        return None


def main():
    # Connect to MQTT broker
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-inference")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()

    print(f"Edge inference service started")
    print(f"  Watching: {CAMERA_DIR} for *_latest.png files")
    print(f"  vLLM: {VLLM_URL}")
    print(f"  MQTT: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Poll interval: {POLL_INTERVAL}s")

    last_processed = {}

    while True:
        for frame_path in glob.glob(os.path.join(CAMERA_DIR, "*_latest.png")):
            mtime = os.path.getmtime(frame_path)
            if last_processed.get(frame_path) == mtime:
                continue

            camera_id = os.path.basename(frame_path).replace("_latest.png", "")
            print(f"\nAnalyzing {camera_id}...")

            result = analyze_frame(frame_path, camera_id)
            if result:
                result["camera_id"] = camera_id
                result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                topic = f"{MQTT_TOPIC_PREFIX}/{camera_id}"
                payload = json.dumps(result, indent=2)
                mqtt_client.publish(topic, payload, qos=1)
                print(f"  Status: {result.get('overall_status', 'UNKNOWN')}")
                print(f"  Published to: {topic}")

            last_processed[frame_path] = mtime

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
