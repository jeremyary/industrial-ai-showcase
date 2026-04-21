# cosmos/reason-2

**Role**: NVIDIA Cosmos Reason 2-8B (Qwen3-VL-derivative) served via vLLM's OpenAI-compatible API. Perception VLM called by the hub-side `obstruction-detector` pod on camera frames federated from the companion cluster.

**Phase**: 1 (per ADR-027). Replaces the cut Metropolis VSS pipeline.

## Interfaces

- **Input**: image + prompt via OpenAI-compatible `/v1/chat/completions` with `image_url` content blocks (base64 data URI works).
- **Output**: structured JSON inside fenced ` ```json ` block — obstruction verdict, label, confidence, detail.
- **Called by**: `workloads/obstruction-detector/` (Phase 1); legacy `workloads/camera-adapter/` still speaks the same endpoint and is retired once obstruction-detector + companion fake-camera are wired end-to-end.

## GPU

Per `docs/08-gpu-resource-planning.md`: single **L40S** (48 GB) via `nodeSelector: nvidia.com/gpu.product: NVIDIA-L40S`, `nvidia.com/gpu: 1`. NVIDIA specs 32 GB minimum for 8B; does not fit L4's 24 GB. A trial of the 2B variant on L4 (2026-04-20) failed the quality bar for warehouse-aisle obstruction detection.

## Runtime

Deployed as a plain `Deployment` + `Service` in `infrastructure/gitops/apps/cosmos/` (not KServe — the OpenAI-compatible path via vLLM is what downstream clients already speak, and KServe adds no value here). Weights pulled from HuggingFace on first start; HF token mounted from Vault-backed Secret `hf-token`.

## Why only Reason 2 in Phase 1

Cosmos Predict 2.5 and Cosmos Transfer 2.5 are Phase 3 scope. Predict arrives as a pre-dispatch admission-check beat (60-min Segment 1, Beat 1, per `demos/60-min-deep-dive/script.md` revision); Transfer arrives as the synthetic-data factory. See `workloads/cosmos/` parent directory for sibling subdirectories that will be created when those phases start.

## Status

Validated on-cluster 2026-04-20 against the trial image pair in `workloads/obstruction-detector/test-images/`. 8B on L40S detects the pallet obstruction reliably (0.99 confidence) and returns 0.98 "clear" for the empty baseline.
