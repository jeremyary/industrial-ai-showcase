# cosmos/reason-2

**Role**: NVIDIA Cosmos Reason 2 deployment as a KServe `ServingRuntime` + `InferenceService`. Scene-reasoning VLM called by `camera-adapter/` on key-frames from Isaac Sim.

**Phase**: 1 (plan item 6). Replaces the cut Metropolis VSS pipeline.

## Interfaces

- **Input**: image + optional prompt context (structured via the KServe InferenceService API).
- **Output**: structured scene-reasoning JSON (event class, confidence, bounding-box context if applicable).
- **Called by**: `camera-adapter/` only; not directly user-facing.

## GPU

Per `docs/08-gpu-resource-planning.md`: single **L4** (24 GB) via `nodeSelector: nvidia.com/gpu.product: NVIDIA-L4`, `nvidia.com/gpu: 1`. L4 class fits Cosmos Reason 2 comfortably.

## Structure

- `chart-overrides/` — values for the upstream Cosmos Reason 2 ServingRuntime + InferenceService deployment. Pulls from NGC (entitlement required; documented in `docs/licensing-gates.md`).

## Why only Reason 2 in Phase 1

Cosmos Predict 2.5 and Cosmos Transfer 2.5 are Phase 3 scope. Predict arrives as a pre-dispatch admission-check beat (60-min Segment 1, Beat 1, per `demos/60-min-deep-dive/script.md` revision); Transfer arrives as the synthetic-data factory. See `workloads/cosmos/` parent directory for sibling subdirectories that will be created when those phases start.

## Status

Phase 1 scaffolding only. Depends on: NGC entitlement verified, NVIDIA-provided chart/manifest version selected.
