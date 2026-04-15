# Industrial AI Showcase

Field demo for sales specialists showing the NVIDIA Omniverse and Physical AI stack running on Red Hat OpenShift. Covers the breadth of what Omniverse enables — 3D simulation, synthetic data generation, vision-language AI, perception model training, and continuous model improvement. Digital twin is one use case within the stack, not the entire story.

See PLAN.md for the full demo narrative, audience adaptation matrix, chapter details, and build phases.

## What This Project Is

A single OpenShift cluster running every layer of the industrial AI stack:
- **Platform chart** (`charts/platform/`) — Isaac Sim (3D simulation + rendering), central MQTT broker, NOC dashboard
- **Factory chart** (`charts/factory/`) — Per-site edge inference (Cosmos-Reason2 via vLLM), camera feeds, edge MQTT broker
- **MLOps chart** (`charts/mlops/`) — RHOAI components (MLflow, Data Science Pipelines, MinIO, KServe, Model Registry)
- **Pipelines** (`pipelines/`) — KFP v2 definitions for synthetic data generation, model training, Cosmos Transfer augmentation
- **Workspace** (`workspace/`) — Python scripts that run inside Isaac Sim's Script Editor (cameras, alerts, MQTT bridge, demo scenario)

## Architecture

Three Helm charts deployed to separate namespaces:

```
charts/platform/  → namespace: ai-showcase-central   (Isaac Sim on L40S, MQTT, dashboard)
charts/factory/   → namespace: ai-showcase-factory-a  (edge inference on L4, cameras, edge MQTT)
charts/mlops/     → namespace: ai-showcase-mlops      (MLflow, DSPA, MinIO, KServe, Model Registry)
```

## Demo Chapters (Narrative Flow)

1. **"This is NVIDIA Omniverse"** — Isaac Sim, SimReady assets, OpenUSD, WebRTC streaming
2. **"The twin sees and understands"** — Camera feeds → Cosmos-Reason2 → MQTT → NOC dashboard
3. **"Where do the models come from?"** — Synthetic data (Replicator) → training (TAO) → serving (KServe), tracked in MLflow
4. **"Test it before you deploy it"** — Mission planner (Nemotron + Cosmos-Reason2) → SIL validation in Isaac Sim
5. **"It gets better on its own"** — Feedback loop: low-confidence detections → Cosmos verifies → retrain
6. **"Now multiply by 15 factories"** — Multi-site Helm deployment, MQTT bridging, central NOC

## NVIDIA Components Showcased

Simulation: Isaac Sim 5.1, Omniverse Kit, SimReady Assets, OpenUSD, Replicator
AI Models: Cosmos-Reason2-2B, Nemotron 3 Nano 4B, TAO Toolkit 5.0 (DetectNet_v2)
Robotics: Mission Planner (FastAPI), SIL Validation
Serving: vLLM, KServe

## Container Images

- Registry: quay.io/jary/
- Runtime: Podman with CDI for GPU (`--device nvidia.com/gpu=all`)
- Isaac Sim base: nvcr.io/nvidia/isaac-sim:5.1.0

## Conventions

- Helm charts use `_helpers.tpl` for common labels and selectors
- GPU node selection via `nodeSelector` with NFD labels (e.g., `NVIDIA-L40S`)
- MQTT topics follow `{site}/safety/{camera}` pattern
- Isaac Sim workspace scripts are mounted via ConfigMap in the platform chart
- All secrets (NGC API key, HuggingFace token) stored as Kubernetes Secrets, never in values.yaml

## Testing

- Bind mock/test servers to `127.0.0.1`, not `0.0.0.0`.
- Use `respx` for mocking `httpx` in async tests.
