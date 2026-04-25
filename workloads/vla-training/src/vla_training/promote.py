# This project was developed with assistance from AI tools.
"""Promote a registered model to a factory's GitOps overlay.

Reads a model version from the RHOAI Model Registry, generates a Kustomize
patch updating the VLA InferenceService image/URI, and commits it as a PR
to the GitOps repo. Merging the PR triggers Argo CD sync.

Usage:
    python -m vla_training.promote --model-name g1-vla-finetune --model-version v2 --factory factory-a
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from vla_training.constants import MODEL_REGISTRY_ADDRESS as _DEFAULT_REGISTRY_ADDRESS


def _read_sa_token() -> str | None:
    token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(token_path):
        with open(token_path) as f:
            return f.read().strip()
    return None


def _get_model_uri(name: str, version: str) -> str:
    from model_registry import ModelRegistry

    server_address = os.environ.get("MODEL_REGISTRY_ADDRESS", _DEFAULT_REGISTRY_ADDRESS)
    is_secure = server_address.startswith("https")
    token = _read_sa_token() if is_secure else None

    registry = ModelRegistry(
        server_address=server_address,
        author="vla-training-pipeline",
        is_secure=is_secure,
        user_token=token,
    )

    model = registry.get_registered_model(name)
    model_version = registry.get_model_version(name, version)
    art = registry.get_model_artifact(name, version)

    print(f"Model: {model.name} v{model_version.name}")
    print(f"URI: {art.uri}")
    return art.uri


def _write_overlay_patch(factory: str, model_uri: str, version: str, gitops_root: Path) -> Path:
    overlay_dir = gitops_root / "apps" / "workloads" / factory / "overlays" / "policy"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    patch = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"mission-dispatcher-{factory.replace('factory-', '')}",
        },
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "showcase.redhat.com/vla-model-uri": model_uri,
                        "showcase.redhat.com/vla-policy-version": version,
                    },
                },
                "spec": {
                    "containers": [
                        {
                            "name": "mission-dispatcher",
                            "env": [
                                {"name": "VLA_MODEL_URI", "value": model_uri},
                                {"name": "VLA_POLICY_VERSION", "value": version},
                            ],
                        }
                    ],
                },
            },
        },
    }

    patch_path = overlay_dir / "policy-version-patch.yaml"
    patch_path.write_text(json.dumps(patch, indent=2) + "\n")
    print(f"Wrote overlay patch: {patch_path}")
    return patch_path


def _create_pr(factory: str, version: str, patch_path: Path) -> None:
    branch = f"policy/{factory}-{version}"
    title = f"feat({factory}): promote VLA policy to {version}"
    body = (
        f"Promotes VLA policy to `{version}` on `{factory}`.\n\n"
        f"Patch: `{patch_path}`\n\n"
        "Co-Authored-by: Claude"
    )

    subprocess.run(["git", "checkout", "-b", branch], check=True)
    subprocess.run(["git", "add", str(patch_path)], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"{title}\n\nCo-Authored-by: Claude"],
        check=True,
    )
    subprocess.run(["git", "push", "-u", "origin", branch], check=True)

    result = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"PR created: {result.stdout.strip()}")
    else:
        print(f"PR creation failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


def promote(
    model_name: str,
    model_version: str,
    factory: str,
    gitops_root: str | None = None,
    create_pr: bool = True,
) -> Path:
    """Promote a model version to a factory overlay. Returns the patch path."""
    root = Path(gitops_root) if gitops_root else Path("infrastructure/gitops")

    print(f"\n=== Policy Promotion: {model_name} {model_version} → {factory} ===")
    model_uri = _get_model_uri(model_name, model_version)
    patch_path = _write_overlay_patch(factory, model_uri, model_version, root)

    if create_pr:
        _create_pr(factory, model_version, patch_path)

    print(f"\n=== Policy Promotion: COMPLETE ===")
    return patch_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a model to a factory's GitOps overlay")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--factory", required=True, choices=["factory-a", "factory-b"])
    parser.add_argument("--gitops-root", default=None)
    parser.add_argument("--no-pr", action="store_true", help="Write patch only, skip PR creation")
    args = parser.parse_args()

    promote(
        model_name=args.model_name,
        model_version=args.model_version,
        factory=args.factory,
        gitops_root=args.gitops_root,
        create_pr=not args.no_pr,
    )


if __name__ == "__main__":
    main()
