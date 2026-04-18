# hub-acm — companion registration + cross-cluster Argo CD

Hub-side manifests that register the companion SNO as an ACM-managed cluster and wire the hub's Argo CD to reconcile companion workloads from Git. Applied on the hub; the companion side receives only the klusterlet bootstrap material (one-time manual import per Session 13).

## Directory layout

| Path | Purpose |
|---|---|
| `clusterset/` | `ManagedClusterSet: clusters-companion` — role-based set, scoped for companion-class clusters distinct from the ACM defaults (`default`, `global`). |
| `managedcluster/` | `ManagedCluster: companion` + `KlusterletAddonConfig` + its namespace. `hubAcceptsClient: true` pre-approves the join. |
| `gitops-integration/` | `ManagedClusterSetBinding` into `openshift-gitops` so Placement can reach the set; `Placement: all-companion` selects every cluster in `clusters-companion`; `GitOpsCluster: companion-gitops` tells ACM to maintain Argo cluster Secrets for placed clusters. |
| `appset-companion/` | `ApplicationSet: companion-apps` — matrix generator combining cluster decisions × Git directories under `apps/companion/*` → one Argo Application per directory, destination=companion. |

## Why a matrix generator

The hub already has a Git-generator AppSet (`operators`) that reconciles `apps/operators/*` to the hub cluster. We can't reuse that pattern for companion because the same `apps/operators/*` path would try to install operators on the hub too. Companion-only apps live under `apps/companion/*`; this AppSet scopes a matrix (companion cluster × companion directories) so none of the existing hub AppSets double-sync.

If we add more managed clusters (spokes, edge) later, the matrix generator expands naturally — label the new clusters into `clusters-companion` (or add a new ClusterSet) and every `apps/companion/*` directory reconciles to each cluster.

## Why `applicationManager` is enabled in `KlusterletAddonConfig`

The legacy ACM-Argo integration path inside `GitOpsCluster` reads the `<cluster>-application-manager-cluster-secret` that this addon provisions. Without it, `GitOpsCluster` fails with `ClusterRegistrationFailed: legacy secret not found`. Even though we don't use ACM's native Application Lifecycle Management (we use Argo), the `applicationManager` addon must be on for Argo cluster registration to succeed.

## Companion-side bootstrap (one-time, manual)

Because the hub (OSD on AWS) cannot reach the companion SNO directly (RFC1918 address on a local LAN behind NAT), ACM's auto-import path (hub pushes klusterlet to spoke) does not work. Manual import via the workstation, which can reach both clusters:

```bash
# On workstation with hub kubeconfig active:
oc apply -k infrastructure/gitops/apps/hub-acm/clusterset
oc apply -k infrastructure/gitops/apps/hub-acm/managedcluster

# Wait for hub to generate the import material:
until oc get secret -n companion companion-import >/dev/null 2>&1; do sleep 5; done

# Extract + apply on companion:
oc get secret -n companion companion-import -o jsonpath='{.data.crds\.yaml}' | base64 -d > /tmp/klusterlet-crds.yaml
oc get secret -n companion companion-import -o jsonpath='{.data.import\.yaml}' | base64 -d > /tmp/klusterlet-import.yaml
KUBECONFIG=~/.kube/companion.kubeconfig oc --insecure-skip-tls-verify apply -f /tmp/klusterlet-crds.yaml
KUBECONFIG=~/.kube/companion.kubeconfig oc --insecure-skip-tls-verify apply -f /tmp/klusterlet-import.yaml

# Then finish the hub side:
oc apply -k infrastructure/gitops/apps/hub-acm/gitops-integration
oc apply -k infrastructure/gitops/apps/hub-acm/appset-companion
```

The klusterlet on companion calls home to the hub API over outbound HTTPS (companion has internet egress). No hub→companion inbound required — pull-model per CLAUDE.md.

## Verification

```bash
# On hub:
oc get managedcluster companion                                # JOINED=True AVAILABLE=True
oc get gitopscluster -n openshift-gitops companion-gitops      # Ready=True
oc get application.argoproj.io -n openshift-gitops | grep companion   # 7 apps, Synced+Healthy
```

Argo reaches companion via ACM's `cluster-proxy` addon (shared internal service on hub); destination server URL is `https://cluster-proxy-addon-user.multicluster-engine.svc.cluster.local:9092/companion`. No direct hub→companion API connectivity needed.
