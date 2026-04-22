# apps/cosmos

Cosmos family deployments — Phase 1 lands **Cosmos-Reason2-8B** (Qwen3-VL-derivative) on L40S for perception / obstruction detection via vLLM's OpenAI-compatible API (per ADR-027; supersedes the earlier Cosmos-Reason1-7B on L4 deployment).

Trial history (2026-04-20): 2B on L4 was trialed first (cheaper class, simpler schedule) but missed pallet detection in photorealistic warehouse-aisle images — 0.97 "no obstruction" confidence on both empty and pallet-blocked frames. 8B on L40S got it right: 0.98 clear for the empty frame, 0.99 "large box on the floor, partially blocking the pathway" for the pallet frame. ~3-6 s per-frame latency.

## Phase 1 — cosmos-reason (8B on L40S, validated)

- Runtime: `vllm/vllm-openai:v0.11.0` — Qwen3-VL support landed in 0.11.0 (0.8.x won't load these models).
- Model: `nvidia/Cosmos-Reason2-8B` pulled from HuggingFace on first start. HF token required (gated repo); mounted from Vault-backed Secret `hf-token` via VaultStaticSecret (`kv/hf/token`).
- Served-model-name: `cosmos-reason-2` (stable across 2B/8B variants so downstream clients don't flip).
- GPU: 1 × L40S via `nvidia.com/gpu.product=NVIDIA-L40S` nodeSelector. NVIDIA specs 32 GB minimum; doesn't fit L4's 24 GB.
- Memory: bfloat16, `--gpu-memory-utilization=0.9`, `--max-model-len=8192` (image tokens exceed the 4096 default for warehouse-resolution frames), `--limit-mm-per-prompt '{"image":1}'` (JSON syntax required by vLLM 0.11).
- Reasoning parser: `--reasoning-parser qwen3` per NVIDIA's documented invocation.
- Cache: 60 GiB PVC at `/cache/hf`.

## Trial harness

`workloads/obstruction-detector/trial.py` sends each image under `test-images/` to the endpoint (via `oc port-forward -n cosmos svc/cosmos-reason 8000:8000`) and prints the parsed JSON verdict. Used to re-validate the quality bar if the model ever changes.

Invoked by the hub-side **obstruction-detector** service (consumes `warehouse.cameras.aisle3`, calls `POST /v1/chat/completions` with image + prompt, parses the fenced JSON response, publishes `fleet.safety.alerts`). The Phase-1-transitional `workloads/camera-adapter/` still speaks to the same endpoint and will be retired once obstruction-detector + companion fake-camera are wired end-to-end.

### Why vLLM + HF instead of NGC NIM

The NIM packaging for Cosmos-Reason lives behind an NGC enterprise entitlement tier we don't have. vLLM + HuggingFace gets us the same weights via the same underlying model with an OpenAI-compatible surface that camera-adapter already speaks. No customer unavailability vs. the NIM path — customers can swap the runtime for NIM themselves if they have the entitlement.

## Phase 3 adds

- `deployment-predict.yaml` — Cosmos Predict 2.5 as a pre-dispatch admission check (per `demos/60-min-deep-dive/script.md` Segment 1, Beat 1).
- `deployment-transfer.yaml` — Cosmos Transfer 2.5 for synthetic-data scene variation.

Both are larger models (L40S-class) and not Phase-1 scope.
