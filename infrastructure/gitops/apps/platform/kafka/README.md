# platform/kafka

**Phase**: 1 (plan item 5). Phase-0 installed the AMQ Streams operator; this landing instantiates the Kafka cluster + Phase-1 topics.

## What's here

- `namespace.yaml` — `fleet-ops` namespace. Phase-1 hub workloads (fleet-manager, wms-stub, camera-adapter) live here. Mission-dispatcher lives in `robot-edge` on the companion cluster.
- `kafka.yaml` — `Kafka/fleet` CR in KRaft mode (annotations `strimzi.io/node-pools=enabled` + `strimzi.io/kraft=enabled`). Two listeners: `plain:9092` (internal, no-TLS) for dev/demo convenience; `tls:9093` (internal, mTLS) for the production path — Phase 1 workloads use `plain` until Service Mesh mTLS is wired in Phase 1 item 11 follow-up.
- `kafkanodepool.yaml` — `KafkaNodePool/fleet-brokers` with 3 replicas, combined `[controller, broker]` roles, 20Gi per-broker persistent-claim on `gp3` (default SC on hub OSD).
- `topics.yaml` — four `KafkaTopic` CRs: `fleet.events`, `fleet.missions`, `fleet.telemetry`, `fleet.ops.events`. Partitions 6 / replicas 3 / min.isr 2 / 7-day retention. Topic names use dotted notation per Kafka convention.

## What's NOT here (intentionally)

- **mTLS Kafka listener configuration on producers/consumers** — Phase 1 services bootstrap via the plain listener. mTLS hardening lands when Service Mesh is wired through Fleet Manager / Mission Dispatcher (Phase 1 follow-up, or early Phase 2).
- **Schema Registry** — Strimzi ships with `KafkaConnect` / `KafkaConnector` but not Schema Registry directly. We use Confluent Schema Registry or Apicurio as a separate deployment; landing in a sibling Application (`platform/schema-registry/`) in follow-up work. Until then, Phase-1 services use JSON payloads with Pydantic models; Avro migration is a follow-up.
- **MirrorMaker2 to companion** — Phase 2 scope (20-min Segment 3 multi-site rollback beat). Not wired in Phase 1; Mission Dispatcher on companion polls the hub cluster's Kafka directly via the companion network.
- **Kafka Exporter / Cruise Control** — deferred; add when observability demand outpaces what the Strimzi UserOperator + TopicOperator surface.

## Phase 2 additions (do not apply to Phase 1)

- MirrorMaker2 CR for `fleet.missions` replication hub → companion (+ spoke-a, spoke-b).
- Schema Registry (Apicurio or Confluent) in `platform/schema-registry/`.
- mTLS enforcement via Service Mesh VirtualService / DestinationRule.

## Argo reconciliation

Picked up by the `platform` ApplicationSet (`infrastructure/gitops/clusters/hub/appsets/platform.yaml`) — git-directory generator creates an Application `platform-kafka` on first reconcile.
