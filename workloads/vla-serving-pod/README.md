# vla-serving-pod

**Role**: pod-native VLA serving via KServe custom predictor on a CUDA-capable edge (Jetson Thor). Second edge pattern alongside `vla-serving-host/`.

**Phase**: 3 / 4 — **materializes when Jetson AGX Thor Developer Kit hardware arrives** (ordered 2026-04-19). Empty scaffold today; do not populate until the hardware is in hand.

## Why this directory exists now

Per ADR-026, the reference is committed to two edge patterns:
1. AMD consumer APU host-native (`vla-serving-host/`, Phase 1, live today).
2. NVIDIA Jetson pod-native via MicroShift + NVIDIA GPU Operator + KServe (this directory, Phase 3+).

The 60-min Segment-4 live-swap beat grows to *"same open VLA serving on AMD edge host, then on Jetson Thor edge pod"* once this arrives.

## Planned interfaces (when hardware lands)

- **KServe `InferenceService`** using a custom predictor image — OpenVLA reference code or vLLM-for-multimodal if OpenVLA support lands upstream by Phase 3.
- Runtime: CUDA on Thor's Blackwell GPU; unified 128 GB LPDDR5X.
- GitOps-reconciled via Argo CD.
- ACM-federated: Thor cluster registers as a third managed cluster alongside hub + companion SNO.

## Do-not-do-yet

Do not build containers, write manifests, or write InferenceService definitions here until Thor hardware arrives, is provisioned with JetPack + MicroShift, and the GPU Operator is confirmed working. Premature scaffolding risks baking assumptions that turn out wrong once the hardware is live.

## Supersedes

`workloads/groot-serving/` — renamed to this directory per ADR-026. GR00T-as-primary was never the right framing; OpenVLA is primary per `docs/licensing-gates.md`, and serving pattern (not model) is what this directory represents.
