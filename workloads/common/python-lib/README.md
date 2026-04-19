# common/python-lib

Shared Python utilities consumed by all Phase-1+ Python services (`fleet-manager`, `mission-dispatcher`, `wms-stub`, `camera-adapter`, `vla-serving-host`).

**Phase**: 1 (grows across phases).

## Planned modules

- `common_lib.kafka` — thin wrapper around `confluent-kafka-python` with Avro Schema Registry integration and structured-logging hooks.
- `common_lib.tracking` — MLflow-tracking abstraction that insulates downstream code from RHOAI-internal MLflow details (per Phase 1 item 1 in `docs/04-phased-plan.md`).
- `common_lib.logging` — `structlog` configuration, correlation-ID middleware for FastAPI, OpenTelemetry trace propagation.
- `common_lib.config` — `pydantic-settings`-based config loading from env + ConfigMaps.
- `common_lib.schemas` — generated-from-Avro Pydantic models for Kafka event payloads (`FleetEvent`, `FleetMission`, `FleetOpsEvent`, `FleetTelemetry`).

## Usage

Consumed as a local path dependency from each service's `pyproject.toml`:

```toml
[tool.uv.sources]
common-lib = { path = "../common/python-lib", editable = true }
```

## Status

Scaffolding only. Modules land as services need them — we avoid building a library speculatively ahead of consumer needs.
