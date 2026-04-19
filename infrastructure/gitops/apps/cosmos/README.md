# apps/cosmos

Cosmos family deployments — Phase 1 lands **Cosmos-Reason1-7B** for scene reasoning via vLLM's OpenAI-compatible API.

## Phase 1 — cosmos-reason

- Runtime: `vllm/vllm-openai:v0.8.5` (Qwen2-VL-class multimodal decoder support).
- Model: `nvidia/Cosmos-Reason1-7B` pulled from HuggingFace on first start (~14 GiB weights). HF token is mounted from Vault-backed Secret `hf-token` if set.
- GPU: 1 × L4 via `nvidia.com/gpu.product=NVIDIA-L4` nodeSelector + toleration for the L4 taint.
- Memory: bfloat16, `--gpu-memory-utilization=0.9`, `--max-model-len=4096`, one image per prompt.
- Cache: 60 GiB PVC at `/cache/hf`.

Invoked by `workloads/camera-adapter/` — POSTs base64-encoded camera frames to `POST /v1/chat/completions` with a scene-reasoning prompt; parses the response into a `FleetEvent` on `fleet.events`.

### Why vLLM + HF instead of NGC NIM

The NIM packaging for Cosmos-Reason lives behind an NGC enterprise entitlement tier we don't have. vLLM + HuggingFace gets us the same weights via the same underlying model with an OpenAI-compatible surface that camera-adapter already speaks. No customer unavailability vs. the NIM path — customers can swap the runtime for NIM themselves if they have the entitlement.

## Phase 3 adds

- `deployment-predict.yaml` — Cosmos Predict 2.5 as a pre-dispatch admission check (per `demos/60-min-deep-dive/script.md` Segment 1, Beat 1).
- `deployment-transfer.yaml` — Cosmos Transfer 2.5 for synthetic-data scene variation.

Both are larger models (L40S-class) and not Phase-1 scope.
