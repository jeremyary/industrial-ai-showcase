# console/backend

Fastify + kafkajs + TypeScript. Fronts the live Kafka event stream as SSE, proxies scenario triggers to WMS-Stub, describes the hub/companion topology.

**Phase**: 1 skeletal per plan item 11.

## Endpoints

- `GET /healthz`, `GET /readyz` — health probes.
- `GET /api/topology` — hub + companion cluster description + the 3 teaser pills for the 5-min close.
- `GET /api/scenarios` — proxies WMS-Stub scenario catalog.
- `POST /api/scenarios/:name/run` — proxies scenario-run trigger to WMS-Stub.
- `GET /api/events` — Server-Sent Events stream of live messages from the four fleet topics (events, missions, ops.events, telemetry). One SSE event per Kafka message.

## Local dev

```
cd console/backend
npm install
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 npm run dev
```

## Container

Builds against UBI9 nodejs-22. Ships as `quay.io/redhat-physical-ai-reference/showcase-console-backend:<sha>` (in-cluster BuildConfig for Phase 1).

## Not in Phase 1 skeletal

- Authentication — Phase 1 ships behind an OpenShift Route with passthrough TLS only; auth lands with Service Mesh authz in Phase 2.
- Persistence — the event stream is tail-mode only (latest); historical replay is a later enhancement.
- MLflow model-registry surface, agentic HIL drawer, compliance evidence panel — all Phase 3 scope per `demos/60-min-deep-dive/script.md`.
