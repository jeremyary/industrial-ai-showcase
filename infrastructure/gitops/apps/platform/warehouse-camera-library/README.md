# warehouse-camera-library

Phase-1 image library backing the companion-side fake-camera service. Per ADR-027 step 6.

## What it is

A minimal MinIO instance in its own namespace (`warehouse-data`), with one bucket (`warehouse-camera-library`) holding the AI-generated photorealistic warehouse frames the fake-camera service rotates between.

- `aisle3_empty.jpg` — clean baseline (camera sees no obstruction).
- `aisle3_pallet.jpg` — obstructed state (Drop Pallet button target).

## Why a new MinIO rather than reuse an existing one

Existing in-cluster MinIOs (mlflow, obs-storage, mortgage-*) are owned by other workloads and scoped to their function. A dedicated library for demo-data avoids cross-contamination and keeps the camera images' lifecycle (update → re-upload → restart fake-camera) independent of observability storage or MLflow artifact management.

## Contents

- `minio-deployment.yaml` + `minio-service.yaml` — single-replica MinIO on a 5 GB RWO PVC. Plain image, `:latest` tag, matching the mlflow + observability pattern.
- `minio-credentials.yaml` — Phase-1 placeholder creds. Upgrade to Vault-backed `VaultStaticSecret` once any cross-namespace consumer needs them.
- `bucket-init-job.yaml` — ArgoCD `PostSync` Job. Waits for MinIO readiness, creates the bucket idempotently, and `mc cp`s every frame from the generated `warehouse-camera-frames` ConfigMap into the bucket.

## Adding / changing frames

Update or add JPEGs under `workloads/obstruction-detector/test-images/` (the canonical frame source), update `kustomization.yaml`'s `configMapGenerator` to include the new file, re-sync. The `bucket-init-job` re-runs and overwrites.

## Build notes

`kustomize build --load-restrictor=LoadRestrictionsNone …/warehouse-camera-library/` — same reason as `scene-pack-builder`: lets kustomize read the JPEG sources from their canonical location outside this kustomization root.

## Consumer contract

The fake-camera service (Session-18 step 7) reads frames from `http://minio.warehouse-data.svc.cluster.local:9000/warehouse-camera-library/<name>` using the `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` from `minio-credentials` (or from Vault, once that lands). Frame names come from `warehouse-topology.yaml`'s `cameras.*.frame_library` — the topology yaml is the only place that maps a scenario state → a specific filename.
