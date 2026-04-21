# camera-adapter

**Role**: custom RTSP→Kafka adapter fronting Cosmos Reason 2. Pulls simulated camera frames from Isaac Sim, submits them to the Cosmos Reason 2 inference endpoint for scene reasoning, publishes structured events to Kafka.

**Phase**: 1 (5-min Warehouse Baseline — plan item 6). Replaces the cut Metropolis VSS blueprint.

## Why this replaces VSS

Per the Phase-1 story-driven audit in `docs/04-phased-plan.md`: the full Metropolis VSS 8-GPU pipeline wasn't justified by any demo beat. The narrow "event from camera" job is handled by Cosmos Reason 2-8B on a single L40S plus this lightweight adapter. Saves ~7 GPUs and simplifies the critical path. Per ADR-027, this adapter is being superseded by the `workloads/obstruction-detector/` pod (hub) plus the companion-side fake-camera service; camera-adapter stays in place as a smoke-test path until that cutover is complete.

## Interfaces

- **Consumes**: RTSP streams from Isaac Sim's simulated ceiling cameras (URL list from ConfigMap).
- **Calls**: Cosmos Reason 2 inference endpoint (see `workloads/cosmos/reason-2/`). Submits key-frames per a frame-throttling policy.
- **Produces**: Kafka topic `fleet.events` — structured scene-reasoning outputs in Avro format.
- **HTTP**: `GET /healthz`, `GET /metrics`.

## Frame sampling policy (v1)

Per-camera 1 Hz key-frame sampling for the 5-min demo. Adjustable via ConfigMap. Motion-triggered sampling lands in Phase 2+ if a demo beat earns it.

## Deployment

- Cluster: OSD hub, namespace `fleet-ops`.
- Chart: `chart/`.
- GPU: none directly (Cosmos Reason 2 carries the GPU load via its own InferenceService).

## Local development

```
cd workloads/camera-adapter
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
uvicorn camera_adapter.main:app --reload --port 8083
```

## Status

Phase 1 scaffolding only. Depends on: Cosmos Reason 2 InferenceService reachable, Isaac Sim runner emitting RTSP, Kafka topics live.
