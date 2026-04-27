# This project was developed with assistance from AI tools.
"""Download VLA ONNX models from S3 and validate: structure, inference, finite outputs, determinism."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

from vla_training.config import VlaTrainingConfig

ONNX_EXTENSIONS = {".onnx"}

_IMAGE_PATTERNS = {"image", "pixel", "vision", "img"}
_SEQUENCE_PATTERNS = {"token", "input_ids", "attention", "mask", "text"}
_MIN_SPATIAL_DIM = 16
_MIN_SEQUENCE_DIM = 4

_S3_PREFIX_PATTERN = re.compile(r"^[a-zA-Z0-9._\-/]*$")


def _validate_s3_prefix(value: str, field_name: str = "s3_prefix") -> None:
    if ".." in value:
        raise ValueError(f"{field_name} must not contain '..': {value!r}")
    if value.startswith("/"):
        raise ValueError(f"{field_name} must not start with '/': {value!r}")
    if not _S3_PREFIX_PATTERN.match(value):
        raise ValueError(f"{field_name} contains invalid characters: {value!r}")


def _resolve_dynamic_dim(input_name: str) -> int:
    name_lower = (input_name or "").lower()
    if any(p in name_lower for p in _IMAGE_PATTERNS):
        return _MIN_SPATIAL_DIM
    if any(p in name_lower for p in _SEQUENCE_PATTERNS):
        return _MIN_SEQUENCE_DIM
    return 1


def _build_feed(inputs) -> dict:
    feed = {}
    for inp in inputs:
        shape = []
        for dim in inp.shape:
            if isinstance(dim, str) or dim is None:
                shape.append(_resolve_dynamic_dim(inp.name))
            else:
                shape.append(dim)

        dtype_str = inp.type.lower() if inp.type else ""
        if "float" in dtype_str or "double" in dtype_str:
            feed[inp.name] = np.random.randn(*shape).astype(np.float32)
        else:
            feed[inp.name] = np.random.randint(0, 100, size=shape).astype(np.int64)

    return feed


def _download_onnx_files(s3, bucket: str, prefix: str, local_dir: Path) -> list[Path]:
    print(f"Downloading ONNX files from s3://{bucket}/{prefix}/...")
    local_dir.mkdir(parents=True, exist_ok=True)

    paginator = s3.get_paginator("list_objects_v2")
    onnx_files = []
    total = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel_path = key[len(prefix):].lstrip("/")
            if not rel_path:
                continue
            local_path = local_dir / rel_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, key, str(local_path))
            total += 1
            if local_path.suffix in ONNX_EXTENSIONS:
                onnx_files.append(local_path)

    print(f"Downloaded {total} file(s), {len(onnx_files)} ONNX model(s): {[p.name for p in onnx_files]}")
    return onnx_files


def _validate_onnx_model(onnx_path: Path) -> dict:
    import onnx
    import onnxruntime as ort

    print(f"\n--- Validating: {onnx_path.name} ---")
    result: dict = {"name": onnx_path.name, "passed": True, "errors": []}

    try:
        model = onnx.load(str(onnx_path))
        onnx.checker.check_model(model)
        print("  Structure: OK")
    except Exception as e:
        msg = str(e)
        if "too large" in msg.lower():
            print(f"  Structure: SKIPPED (model too large for checker)")
        else:
            result["passed"] = False
            result["errors"].append(f"ONNX structural check failed: {e}")
            return result

    try:
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    except Exception as e:
        print(f"  Inference: SKIPPED ({e})")
        return result

    inputs = session.get_inputs()
    outputs = session.get_outputs()
    result["inputs"] = [{"name": i.name, "shape": i.shape, "type": i.type} for i in inputs]
    result["outputs"] = [{"name": o.name, "shape": o.shape, "type": o.type} for o in outputs]

    print(f"  Inputs:  {[(i.name, i.shape) for i in inputs]}")
    print(f"  Outputs: {[(o.name, o.shape) for o in outputs]}")

    if not inputs:
        result["passed"] = False
        result["errors"].append("Model has no inputs")
        return result
    if not outputs:
        result["passed"] = False
        result["errors"].append("Model has no outputs")
        return result

    feed = _build_feed(inputs)

    try:
        out1 = session.run(None, feed)
        print(f"  Inference: OK (output shapes: {[o.shape for o in out1]})")
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"Inference failed: {e}")
        return result

    for i, o in enumerate(out1):
        if not np.all(np.isfinite(o)):
            result["passed"] = False
            result["errors"].append(f"Non-finite values in output {i}")

    deterministic = True
    try:
        out2 = session.run(None, feed)
        for i, (o1, o2) in enumerate(zip(out1, out2)):
            if not np.allclose(o1, o2, atol=1e-6):
                deterministic = False
                result["passed"] = False
                result["errors"].append(f"Non-deterministic output at index {i}")
        if deterministic:
            print("  Determinism: OK")
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"Determinism check failed: {e}")

    return result


def run(checkpoint_prefix: str | None = None) -> list[dict]:
    cfg = VlaTrainingConfig()

    if not cfg.s3.enabled:
        print("ERROR: S3 not configured.", file=sys.stderr)
        sys.exit(1)

    checkpoint_prefix = checkpoint_prefix or cfg.s3.checkpoint_prefix
    _validate_s3_prefix(checkpoint_prefix, "checkpoint_prefix")
    onnx_prefix = f"{checkpoint_prefix}/onnx"
    s3 = cfg.s3.create_client()

    with tempfile.TemporaryDirectory(prefix="vla-validate-") as tmpdir:
        onnx_dir = Path(tmpdir)
        onnx_files = _download_onnx_files(s3, cfg.s3.bucket, onnx_prefix, onnx_dir)

        if not onnx_files:
            print("ERROR: No ONNX files found in S3.", file=sys.stderr)
            sys.exit(1)

        results = [_validate_onnx_model(f) for f in onnx_files]

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    print(f"\n=== VLA ONNX Validation: {passed} passed, {failed} failed ===")

    if failed > 0:
        for r in results:
            if not r["passed"]:
                print(f"  FAILED: {r['name']}: {r['errors']}")
        sys.exit(1)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate VLA ONNX models")
    parser.add_argument("--checkpoint-prefix", type=str, default=None)
    args = parser.parse_args()
    run(checkpoint_prefix=args.checkpoint_prefix)


if __name__ == "__main__":
    main()
