# isaac-sim

**Role**: NVIDIA Isaac Sim 6.0 headless runner. Renders the SimReady Warehouse scene with Nova Carter AMR + Unitree G1, publishes simulated cameras as RTSP streams, executes scripted deterministic scenarios for the 5-min demo.

**Phase**: 1 (plan item 3).

## Interfaces

- **Loads**: USD scene from Nucleus (`nucleus/` workload) — SimReady Warehouse (specific layout TBD during implementation, documented in `scenarios/`).
- **Emits**: simulated ceiling-camera RTSP streams, consumed by `camera-adapter/`.
- **Accepts**: scenario commands via gRPC (for WMS-Stub-driven deterministic runs).
- **Streams**: viewport to `kit-app-streaming/` Factory Viewer Kit app for the Console.

## GPU

`nvidia.com/gpu: 1` with `nodeSelector: nvidia.com/gpu.product: NVIDIA-L40S` per ADR-018. L40S class for ray-traced rendering + physics.

## Packaging

- `container/` — image built on `nvcr.io/nvidia/isaac-sim` with custom startup scripts and the SimReady Warehouse scenario pack baked in. Cosign-signed; SBOM generated.
- `chart/` — Deployment (not Job) with persistent viewport.
- `scenarios/` — scenario configs referenced by WMS-Stub runs.

## Status

Phase 1 scaffolding only. Implementation depends on: Nucleus chart codified, Kit App Streaming deployment path confirmed, NGC entitlement verified for Isaac Sim image pulls.

## References

- `assets/README.md` for scene + robot selections.
- `demos/warehouse-baseline/script.md` for scripted-scenario requirements.
