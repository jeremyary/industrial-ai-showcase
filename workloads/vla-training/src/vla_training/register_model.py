# This project was developed with assistance from AI tools.
"""Register fine-tuned VLA ONNX model with RHOAI Model Registry."""

from __future__ import annotations

import argparse
import os

from vla_training.constants import MODEL_REGISTRY_ADDRESS as _DEFAULT_REGISTRY_ADDRESS


def _read_sa_token() -> str | None:
    token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(token_path):
        with open(token_path) as f:
            return f.read().strip()
    return None


def register_model(
    name: str,
    uri: str,
    version: str,
    model_format_name: str = "onnx",
    model_format_version: str = "1",
    description: str | None = None,
    author: str = "vla-training-pipeline",
    metadata: dict | None = None,
    onnx_files: list[str] | None = None,
) -> str:
    """Register a model with the RHOAI Model Registry. Returns the model version ID."""
    from model_registry import ModelRegistry

    server_address = os.environ.get("MODEL_REGISTRY_ADDRESS", _DEFAULT_REGISTRY_ADDRESS)
    is_secure = server_address.startswith("https")
    token = _read_sa_token() if is_secure else None

    registry = ModelRegistry(
        server_address=server_address,
        author=author,
        is_secure=is_secure,
        user_token=token,
    )

    print(f"Registering model: {name} v{version}")
    print(f"  URI: {uri}")
    print(f"  Format: {model_format_name} v{model_format_version}")

    combined_metadata = dict(metadata or {})
    if onnx_files:
        combined_metadata["onnx_files"] = ",".join(onnx_files)

    registered_model = registry.register_model(
        name=name,
        uri=uri,
        version=version,
        model_format_name=model_format_name,
        model_format_version=model_format_version,
        version_description=description,
        metadata=combined_metadata,
    )

    print(f"  Registered: {registered_model.name} (id={registered_model.id})")
    return registered_model.id


def _lineage_metadata() -> dict:
    """Collect lineage metadata from environment (set by pipeline steps)."""
    meta = {}
    env_map = {
        "DSPA_RUN_ID": "pipeline_run_id",
        "VLA_DATASET_REPO": "dataset_repo",
        "VLA_BASE_MODEL_REPO": "base_model_repo",
        "VLA_MAX_STEPS": "training_steps",
        "VLA_EMBODIMENT_TAG": "embodiment_tag",
    }
    for env_key, meta_key in env_map.items():
        val = os.environ.get(env_key, "")
        if val:
            meta[meta_key] = val
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a model with RHOAI Model Registry")
    parser.add_argument("--name", required=True)
    parser.add_argument("--uri", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--format-name", default="onnx")
    parser.add_argument("--format-version", default="1")
    parser.add_argument("--description", default=None)
    args = parser.parse_args()

    register_model(
        name=args.name,
        uri=args.uri,
        version=args.version,
        model_format_name=args.format_name,
        model_format_version=args.format_version,
        description=args.description,
        metadata=_lineage_metadata(),
    )


if __name__ == "__main__":
    main()
