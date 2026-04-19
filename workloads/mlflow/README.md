# mlflow

**Role**: experiment tracking + model registry + artifact store. Shipped as part of RHOAI 3.4 EA1 (container `registry.redhat.io/rhoai/odh-mlflow-rhel9:<sha>`, `MLflow` CR reconciled by the RHOAI MLflow operator).

**Phase**: 1 (plan item 1). Foundational — no GPU, enables later MLOps story.

## Live state (verified 2026-04-19)

MLflow is **deployed and healthy** on the OSD hub. Phase 0 / prior sessions stood up the full stack; Phase 1 item 1 is validation + documentation work, not a fresh deploy.

| Component | State |
|---|---|
| `MLflow` CR (`mlflow.opendatahub.io/v1`) | `mlflow` namespace, `status.conditions[Available]=True`, ArgoCD-tracked via `platform-mlflow:mlflow.opendatahub.io/MLflow:openshift-gitops/mlflow` |
| MLflow server | `mlflow-6f5db59fcc-*` in `redhat-ods-applications`, 2/2 Running (main + ca-bundle-watcher sidecar) |
| MLflow operator | `mlflow-operator-controller-manager-*` in `redhat-ods-applications`, 1/1 Running |
| Backend database | CloudNativePG cluster `mlflow-db` in `mlflow` namespace, 1 instance healthy. Connection via `mlflow-db-app` secret (keys: `uri`, `host`, `port`, `dbname`, `username`, `password`). |
| Artifact store | MinIO in `mlflow` namespace, exposed at `http://minio.mlflow.svc.cluster.local:9000`. S3 credentials in `mlflow-s3-credentials` secret (keys: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`). Artifacts path `s3://mlflow-artifacts/`. |
| Artifact serving | `serveArtifacts: true` — clients reach MLflow via the server rather than direct S3 access. |

## Endpoints

- **In-cluster**: `https://mlflow.redhat-ods-applications.svc.cluster.local:8443` (TLS, selector `app=mlflow`). All Phase-1+ workloads call MLflow via this service.
- **External (RHOAI data-science-gateway)**: `https://rh-ai.apps.jary-qs-0323.7w5j.p1.openshiftapps.com` — routes through the RHOAI dashboard + gateway class (`data-science-gateway-data-science-gateway-class` route, passthrough TLS).
- **MinIO console** (admin / debugging only): `minio.mlflow.svc.cluster.local:9001` — no public route by default.

## How downstream workloads connect

Phase 1 Python services (`fleet-manager`, `mission-dispatcher`, `wms-stub`, `camera-adapter`, `vla-serving-host`) import the shared `common_lib.tracking` wrapper rather than the `mlflow` client library directly. The wrapper:
- Reads the Postgres URI via Kubernetes Secret `mlflow-db-app` (mounted into the pod as env via `envFrom`).
- Reads the S3 artifact store credentials from Secret `mlflow-s3-credentials` (same pattern).
- Points the MLflow tracking client at the in-cluster service URL.
- Provides opinionated helpers: `start_run()`, `log_policy_artifact()`, `register_model_version()`.

This insulates downstream code from RHOAI-internal MLflow details and lets us swap the tracking backend later without rewriting every caller.

## No code in this workload

The MLflow deployment is operator-managed; there's no chart, Dockerfile, or source code here. This directory is documentation + an anchor for future Phase-1-item-1 follow-up work (e.g., tightening the `MLflow` CR spec, adding model-registry policy, configuring access control).

## References

- ADR-015 (MLflow shipped with RHOAI 3.4 EA1).
- ADR-021 (MinIO fallback for S3 on OSD hub; ODF not available on this OSD instance).
- Phase 1 item 1 in `docs/04-phased-plan.md`.
