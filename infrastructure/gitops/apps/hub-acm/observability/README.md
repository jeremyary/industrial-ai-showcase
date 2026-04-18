# hub-acm/observability — MultiClusterObservability

Hub-side MCO manifests that deploy the Thanos stack + Grafana on the hub and auto-deploy the `metrics-collector` addon onto every ACM-managed cluster. Managed clusters `remote_write` their platform metrics to the hub Thanos Receiver; long-term retention lives in MinIO (`obs-storage/thanos` bucket).

## What reconciles from Git

- `namespace.yaml` — `open-cluster-management-observability`
- `multiclusterobservability.yaml` — the MCO CR (Thanos sizing, storage config, addon spec, retention)

## What's imperative (one-time setup, kept out of Git)

Two secrets in `open-cluster-management-observability` that contain credentials and are created imperatively to avoid committing secret material:

### 1. `multiclusterhub-operator-pull-secret`

MCO needs the cluster pull-secret in its own namespace. Copy from `openshift-config`:

```bash
oc get secret -n openshift-config pull-secret -o yaml | \
  sed -e 's/namespace: openshift-config/namespace: open-cluster-management-observability/' \
      -e 's/name: pull-secret/name: multiclusterhub-operator-pull-secret/' \
      -e '/resourceVersion:/d' -e '/uid:/d' -e '/creationTimestamp:/d' | \
  oc apply -f -
```

### 2. `thanos-object-storage`

Thanos config pointing at the MinIO in `obs-storage` (shared with Session 07 observability; pre-created `thanos/` bucket in Session 14):

```bash
AK=$(oc get secret -n obs-storage obs-minio-credentials -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
SK=$(oc get secret -n obs-storage obs-minio-credentials -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: thanos-object-storage
  namespace: open-cluster-management-observability
type: Opaque
stringData:
  thanos.yaml: |
    type: s3
    config:
      bucket: thanos
      endpoint: minio.obs-storage.svc.cluster.local:9000
      insecure: true
      access_key: $AK
      secret_key: $SK
EOF
```

The MinIO bucket must exist first:

```bash
oc run -n obs-storage --rm --restart=Never -i --attach minio-probe \
  --image=minio/mc:latest --env="HOME=/tmp" \
  --env="MINIO_ROOT_USER=$(oc get secret -n obs-storage obs-minio-credentials -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)" \
  --env="MINIO_ROOT_PASSWORD=$(oc get secret -n obs-storage obs-minio-credentials -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)" \
  --command -- sh -c 'mc alias set s http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb -p s/thanos'
```

## What MCO deploys

On the hub (`open-cluster-management-observability` namespace):

- `observability-thanos-receive-default-*` (3 replicas by default; tune via spec for SNO-equivalent sizing)
- `observability-thanos-store-memcached-*`
- `observability-thanos-query`
- `observability-thanos-query-frontend`
- `observability-thanos-compact`
- `observability-thanos-rule`
- `observability-alertmanager`
- `observability-observatorium-operator`
- `grafana-*`
- `rbac-query-proxy`

On each ACM-managed cluster (via the `observability-controller` addon): `metrics-collector` DaemonSet that reads local Prometheus (both `openshift-monitoring` and `openshift-user-workload-monitoring`) and remote_writes to hub Thanos Receiver.

## Retention (this deployment)

- `retentionResolutionRaw: 30d` — raw samples kept 30 days in ingesters.
- `retentionResolution5m: 60d` — 5-minute downsampled, 60 days.
- `retentionResolution1h: 90d` — 1-hour downsampled, 90 days.
- `retentionInLocal: 1d` — local PVC retention (ingester-side), 1 day.

All three downsamples live in MinIO long-term. Bump up for real workloads.

## Unified Grafana

MCO ships its own Grafana (branded as "ACM Grafana" or "Observatorium") reachable via the console's Observe → Virtual Machines/Observability menu, or via the `grafana-route` in `open-cluster-management-observability`. Dashboards include a `cluster` selector so the same dashboard renders per-cluster views of hub + companion.

Per ADR-022 we keep the Cluster Observability Operator (COO) UIPlugin for hub-local metrics drill-downs; MCO Grafana is the multi-cluster dashboard surface. Two panes of glass, different scopes, both sanctioned Red Hat patterns.

## Companion side

`infrastructure/gitops/apps/companion/user-workload-monitoring/` enables user-workload monitoring on companion so workload metrics (not just platform metrics) are scraped and made available to metrics-collector for remote_write.

## Verification

```bash
oc get mco observability -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
# → True

oc get managedclusteraddon observability-controller -n companion -o jsonpath='{.status.conditions[?(@.type=="Available")].status}'
# → True (metrics-collector running on companion)

oc exec -n open-cluster-management-observability deploy/observability-thanos-query -- \
  curl -sG 'http://localhost:10902/api/v1/query' --data-urlencode 'query=up{cluster="companion"}' | jq '.data.result | length'
# → >0 (hub Thanos has companion metrics)
```
