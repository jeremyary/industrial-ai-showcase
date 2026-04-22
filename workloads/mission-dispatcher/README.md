# mission-dispatcher

**Role**: companion-side mission executor. Consumes missions from the hub, calls the local VLA serving endpoint, emits execution events and telemetry.

**Phase**: 1 (5-min Warehouse Baseline — plan item 8).

## Interfaces

- **Consumes**: Kafka topic `fleet.missions` (replicated to companion via MirrorMaker in Phase 2; direct hub↔companion bridge in Phase 1).
- **Produces**: Kafka topic `fleet.ops.events` (execution transitions), Kafka topic `fleet.telemetry` (robot state back to hub).
- **HTTP client**: POSTs observations to the **host-local VLA endpoint** on the companion Fedora node's bridge network per ADR-026. Endpoint URL configured via `VLA_ENDPOINT_URL` env var (default: `http://host.containers.internal:8000/act`). Not a KServe InferenceService in Phase 1.
- **HTTP server**: `GET /healthz`, `GET /metrics`.

## Why host-HTTP and not KServe in Phase 1

Per ADR-026: the companion's Radeon 8060S iGPU is reachable only from the Fedora host (kernel 6.19.8), not from inside the SNO VM (kernel 5.14). VLA serving runs on the host; Mission Dispatcher crosses the bridge network to reach it. Honest narration in the demo scripts. KServe custom-predictor pattern returns in Phase 3 when Jetson Thor arrives as a second edge target (see `workloads/vla-serving-pod/`).

## Deployment

- Cluster: companion SNO, namespace `robot-edge`.
- Chart: `chart/`, Argo-managed from `infrastructure/gitops/apps/workloads/mission-dispatcher/` via ACM.
- GPU: none (inference is off-cluster on the host).
- Service Mesh member; NetworkPolicy permits egress to Kafka + the host bridge IP + Postgres-read-only.

## Local development

```
cd workloads/mission-dispatcher
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
uvicorn mission_dispatcher.main:app --reload --port 8081
```

## Status

Phase 1 scaffolding only. Implementation blocked on (a) Kafka topics live, (b) host-VLA endpoint reachable, (c) bridge-network wiring from SNO CNI range to host bridge IP (plan item 12).
