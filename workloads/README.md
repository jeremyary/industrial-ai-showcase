# workloads

Deployable components. One subdirectory per component, each self-contained: container build (if we build our own), Helm chart, tests, README.

## Conventions

- Each chart follows the structure in `docs/06-repo-structure.md` (templates, values.yaml, values.demo.yaml, values.prod.yaml, README).
- Container `Dockerfile`s live under `<workload>/container/`; Tekton pipelines discover them automatically.
- Images published to `quay.io/redhat-physical-ai-reference/<component>:<sha>` with semver tags at milestone cuts.
- GPU workloads pin with `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L40S | NVIDIA-L4 }` per ADR-018. Charts expose `gpuProduct` as a required value — no default.

## Phase activation

- **Phase 1**: nucleus, usd-search, isaac-sim, kit-app-streaming, vss, groot-serving, fleet-manager, mission-dispatcher, wms-stub, mlflow.
- **Phase 2**: isaac-lab.
- **Phase 3**: cosmos, mcp-servers, langgraph-orchestrator.

`common/` holds shared chart library and Python utilities consumed across workloads.
