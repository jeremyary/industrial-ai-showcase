# kit-app-streaming

**Role**: NVIDIA Omniverse Kit App Streaming — streams a minimal custom Kit app ("Factory Viewer") loading the warehouse USD scene from Nucleus, exposed as a WebRTC-streamed viewport embedded in the Showcase Console.

**Phase**: 1 (plan item 4).

## Interfaces

- **Input**: scene URI from Nucleus (via Factory Viewer Kit app configuration).
- **Output**: WebRTC-streamed viewport reachable from the Console front-end.
- **Ingress**: OpenShift Route for WebRTC signaling + streaming.

## Structure

- `factory-viewer/` — the custom Kit app: minimal scene-load + camera-control + overlay rendering. Written against the Kit SDK.
- `chart-overrides/` — values for the upstream NVIDIA Kit App Streaming Helm chart (version pinned in `chart-overrides/values.yaml`).

## GPU

Kit App Streaming requires L40S-class rendering. Per ADR-018: `nodeSelector: nvidia.com/gpu.product: NVIDIA-L40S`, `nvidia.com/gpu: 1`.

## Offline fallback

Per the 5-min script's hard-constraint on offline fallback: the Console caches a pre-recorded viewport loop and plays it seamlessly when the live cluster is unreachable. Recording cadence + format lives in `console/assets/recordings/`.

## Status

Phase 1 scaffolding only. Depends on: NVIDIA Kit App Streaming Helm chart version currently available (verify during implementation), Nucleus scene URI reachable from the Kit app pod, Route TLS configured.
