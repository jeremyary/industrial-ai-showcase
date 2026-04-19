# nucleus

**Role**: NVIDIA Omniverse Nucleus — USD asset substrate. Operational on hub since prior work; Phase 0 / Session 16 codified the deployment as native Kubernetes workloads per ADR-024.

**Phase**: 1 (plan item 2) — already landed before Phase 1 kicked off.

## Status (verified 2026-04-19)

Already **live and Argo-reconciled** at `infrastructure/gitops/apps/platform/nucleus/` — that directory is the source of truth, not a sibling `chart/` under this workload dir. The ApplicationSet `platform` auto-generates a `platform-nucleus` Application that reconciles the namespace, Vault-backed pull secrets, Nucleus microservices (service-auth, service-discovery, service-lft, service-search, service-tagging), SCC binding, NetworkPolicy, and associated Services.

Hardened per Session 16:
- Vault-backed NGC pull secret via VSO (`kv/ngc/api-key`).
- Service Mesh-member where applicable, mTLS-enforced.
- NetworkPolicy-scoped ingress.
- Probes wired.
- `strategy: Recreate` on Deployments holding LevelDB exclusive file locks.

## What this `workloads/nucleus/` directory is for

Documentation + any Phase-2+ additions (e.g., scene-ingest helpers, USD asset promotion pipelines) that aren't cluster-operational. The chart-codification work landed at the infrastructure layer; no further Phase-1 work here.

## References

- `docs/07-decisions.md` ADR-024 (native-K8s Nucleus deployment choice).
- `infrastructure/gitops/apps/platform/nucleus/README.md` (the operational manifest set).
- Phase 1 item 2 in `docs/04-phased-plan.md`.
