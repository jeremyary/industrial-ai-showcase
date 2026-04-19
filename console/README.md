# console

Showcase Console — the single seller-facing surface that drives the three scripted demos (`demos/warehouse-baseline/`, `demos/20-min-architecture/`, `demos/60-min-deep-dive/`).

## Phase 1 skeletal (what's here today)

- `backend/` — Fastify + kafkajs; consumes the four `fleet.*` Kafka topics, exposes SSE to the frontend, proxies scenario-run triggers to WMS-Stub, describes the hub + companion topology.
- `frontend/` — React 19 + Vite + PatternFly 6; three-panel layout (Topology ← Stage → Events), audience-mode selector (novice / evaluator / expert), "Fire scenario" action that drives the 5-min demo's aisle-3 obstruction loop end-to-end.
- `assets/` — placeholders for the Phase-1-tail offline-fallback recording once Kit App Streaming is integrated.
- `scenarios/` — scenario metadata (beats, audience applicability). Currently only `warehouse-baseline` is wired.

## Phase 2 / 3 growth

Per `demos/20-min-architecture/script.md` and `demos/60-min-deep-dive/script.md`, the Console adds:
- Fleet view (per-site version pills, anomaly sparklines).
- Architecture view with Purdue-model overlay.
- Lineage view (MLflow-backed).
- Agent panel with the 6-pane HIL approval drawer (per Phase-2 ADR design spec).
- Compliance evidence panel pulling live Compliance Operator results.
- Live VLA swap visualization (ServingRuntime before/after).

## Deployment

Backend + frontend run as separate Deployments in `fleet-ops`; front exposes a passthrough Route. In-cluster BuildConfigs drive image builds.

## Local dev

```
# backend
cd console/backend && npm install && KAFKA_BOOTSTRAP_SERVERS=localhost:9092 npm run dev

# frontend (proxies to the local backend via vite dev server)
cd console/frontend && npm install && npm run dev
```
