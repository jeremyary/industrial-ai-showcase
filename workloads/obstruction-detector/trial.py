# This project was developed with assistance from AI tools.
"""Trial the Cosmos-Reason2-2B perception quality on the aisle-3 empty/obstructed pair.

Run:
    oc port-forward -n cosmos svc/cosmos-reason 8000:8000 &
    python trial.py

Sends each `test-images/*.png` as a base64 data URI to the vLLM OpenAI-compatible
endpoint and prints the model's JSON verdict. Used before we commit to 2B on L4
vs. promoting to 8B on L40S.
"""

from __future__ import annotations

import base64
import json
import pathlib
import re
import sys
import time
from typing import Any

import requests


ENDPOINT = "http://localhost:8000/v1/chat/completions"
MODEL = "cosmos-reason-2"
IMAGE_DIR = pathlib.Path(__file__).parent / "test-images"

PROMPT = (
    "Is this aisle obstructed? Respond ONLY with a single JSON object of the form:\n"
    '{"obstruction": true|false, "label": "<short noun phrase>", '
    '"confidence": <0..1>, "detail": "<one short sentence>"}'
)


def encode_image(path: pathlib.Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def call_model(image_path: pathlib.Path) -> tuple[dict[str, Any] | None, str, float]:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": encode_image(image_path)}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
        "max_tokens": 512,
        "temperature": 0.0,
    }
    t0 = time.perf_counter()
    resp = requests.post(ENDPOINT, json=payload, timeout=120)
    elapsed = time.perf_counter() - t0
    if not resp.ok:
        raise requests.HTTPError(f"HTTP {resp.status_code}: {resp.text[:500]}")
    body = resp.json()
    msg = body["choices"][0]["message"]
    reasoning = msg.get("reasoning") or ""
    content = msg.get("content") or ""
    raw = content or reasoning
    if reasoning:
        print(f"  reasoning: {reasoning[:600]}")
    match = re.search(r"\{[\s\S]*\}", raw)
    parsed: dict[str, Any] | None = None
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            parsed = None
    return parsed, raw, elapsed


def main() -> int:
    images = sorted(IMAGE_DIR.glob("*.png")) + sorted(IMAGE_DIR.glob("*.jpg"))
    if not images:
        print(f"no images found in {IMAGE_DIR}", file=sys.stderr)
        return 1
    print(f"endpoint: {ENDPOINT}")
    print(f"model:    {MODEL}")
    print(f"images:   {len(images)}\n")
    for path in images:
        print(f"=== {path.name} ({path.stat().st_size // 1024} KB) ===")
        try:
            parsed, raw, elapsed = call_model(path)
        except requests.RequestException as e:
            print(f"  REQUEST FAILED: {e}\n")
            continue
        print(f"  elapsed: {elapsed:.2f}s")
        if parsed is not None:
            print(f"  parsed:  {json.dumps(parsed, indent=2)}")
        else:
            print(f"  raw:     {raw[:800]}")
        print(f"  full:    {raw[:1200]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
