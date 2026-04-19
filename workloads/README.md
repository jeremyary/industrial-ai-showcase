# workloads

Deployable components. One subdirectory per component, self-contained: Python source (where applicable), Helm chart (where cluster-deployed), tests, README.

## Conventions

- Each chart follows `docs/06-repo-structure.md` — `Chart.yaml`, `values.yaml`, `values.demo.yaml`, `values.prod.yaml`, `templates/`, `README.md`.
- Container `Dockerfile`s live under `<workload>/container/`; Tekton pipelines discover them automatically.
- Images published to `quay.io/redhat-physical-ai-reference/<component>:<sha>` with semver tags at milestone cuts.
- GPU workloads pin with `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L40S | NVIDIA-L4 }` per ADR-018. Charts expose `gpuProduct` as a required value — no default.
- Python services use a shared skeleton (`common/python-lib`) + per-service `pyproject.toml`. Python 3.12+, `ruff` + `mypy`, `FastAPI` for HTTP, `confluent-kafka` for Kafka, `pydantic` for schemas, `structlog` for logging.
- All source files produced or substantially modified with AI assistance carry the disclosure comment per `.claude/rules/ai-compliance.md`.

## Phase activation

Aligned to the three demo scripts as scope gates (see `docs/04-phased-plan.md`).

**Phase 1 — 5-min Warehouse Baseline demo** (`demos/warehouse-baseline/script.md`)
- `nucleus/` — existing deployment, codified as Argo-reconciled chart (item 2).
- `mlflow/` — RHOAI-shipped MLflow, configuration/enablement notes (item 1).
- `isaac-sim/` — headless runner container + SimReady Warehouse scene + scripted scenarios (item 3).
- `kit-app-streaming/` — NVIDIA Kit App Streaming + minimal Factory Viewer Kit app (item 4).
- `camera-adapter/` — custom RTSP→Kafka service fronted by Cosmos Reason 2 (item 6). Replaces the cut VSS blueprint.
- `cosmos/reason-2/` — Cosmos Reason 2 KServe ServingRuntime + values (item 6).
- `fleet-manager/` — Python FastAPI, Kafka consumer/producer, rule-based v1 decisioning (item 7).
- `mission-dispatcher/` — Python service on companion SNO; HTTP-calls host VLA endpoint (item 8).
- `wms-stub/` — deterministic scenario emitter (item 9).
- `vla-serving-host/` — OpenVLA-7B host-native on companion Fedora node via podman + systemd + ROCm (item 10, per ADR-026). Not a KServe pod in Phase 1.
- `common/python-lib/` — shared Python utilities (Kafka client wrappers, MLflow tracking abstraction, structured logging).

**Phase 2 — 20-min Architecture demo** (`demos/20-min-architecture/script.md`)
- `isaac-lab/` — Kubeflow Pipeline: scenario manifest → training → evaluate → MLflow Model Registry.
- `cosmos/transfer/` — Cosmos Transfer 2.5 limited deployment for scene variations (one pass, not full pipeline).
- *New workload*: `mes-stub/` — SAP-PP/DS-shaped order emitter for the brownfield beat (planned; not yet scaffolded).

**Phase 3 — 60-min Deep Dive** (`demos/60-min-deep-dive/script.md`)
- `cosmos/predict/` — Cosmos Predict 2.5 as pre-dispatch admission check.
- `cosmos/transfer/` — full synthetic-data factory pipeline.
- `mcp-servers/` — `mcp-isaac-sim`, `mcp-fleet`, `mcp-mlflow`. (`mcp-nucleus` deferred unless demo-earning.)
- `langgraph-orchestrator/` — LangGraph agentic service, MCP tool-using.
- *Arrives with Jetson Thor hardware*: `vla-serving-pod/` — KServe custom predictor + vLLM/transformers on Thor (second edge pattern per ADR-026).

**Cut from Phase 1** (story-driven audit — no demo consumer):
- ~~`usd-search/`~~ — cut; no downstream consumer in any of the three demo scripts.
- ~~`vss/`~~ — cut; full Metropolis VSS 8-GPU pipeline replaced by Cosmos Reason 2 on a single L4 for the narrow "event from camera" job.
- ~~`groot-serving/`~~ — renamed to `vla-serving-pod/` and deferred to Phase 3 (Thor arrival); licensing per `docs/licensing-gates.md` keeps GR00T pluggable-not-primary.

## Shared substrate

`common/` holds shared chart library and Python utilities consumed across workloads.
