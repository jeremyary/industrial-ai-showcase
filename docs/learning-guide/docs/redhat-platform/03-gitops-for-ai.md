# GitOps for AI Workloads

## Why GitOps matters for physical AI

GitOps — declaring all cluster state in Git and using a controller
(Argo CD) to reconcile the cluster to match — is a familiar pattern
for infrastructure management. For AI workloads, GitOps becomes more
than a deployment convenience. It becomes the **governance and
auditability mechanism** that regulated industries require.

When a robot policy change causes a safety incident, the questions
are: What changed? When? Who approved it? What was running before?
Can we revert? GitOps answers all of these from the Git log.

## Red Hat OpenShift GitOps

Red Hat OpenShift GitOps is the productized distribution of Argo CD.
It installs from OperatorHub and provides a controller that
continuously reconciles cluster state against a Git repository.

### How it works

1. **Declare** the desired state in Git: Kubernetes manifests,
   Kustomize overlays, Helm charts.
2. **Argo CD watches** the Git repository for changes.
3. When a change is detected, Argo CD **compares** the desired state
   (Git) with the actual state (cluster).
4. If they differ, Argo CD **syncs** — applying the changes to bring
   the cluster into alignment.
5. If someone manually changes the cluster, Argo CD **detects drift**
   and reports the resource as OutOfSync.

### Application and ApplicationSet

An `Application` CR tells Argo CD what to manage:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: model-serving
spec:
  source:
    repoURL: https://github.com/org/repo.git
    path: infrastructure/gitops/apps/workloads/model-serving
  destination:
    server: https://kubernetes.default.svc
    namespace: inference
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

An `ApplicationSet` generates multiple Applications from a single
definition, using generators:

- **Git directory generator**: One Application per directory in a Git
  path. Add a new directory → new Application appears automatically.
- **Cluster generator**: One Application per managed cluster (from
  ACM). Add a new spoke cluster → workloads deploy automatically.
- **Matrix generator**: Combine generators for cross-product
  deployment (every workload × every cluster).

ApplicationSets are the mechanism for fleet-scale deployment: define
the workload stack once, and it fans out to all matching clusters.

## GitOps patterns for AI

### Model promotion as a Git commit

When a new model version is ready for production:

1. The training pipeline registers the model in the Model Registry.
2. A promotion PR is opened that updates the InferenceService manifest:

```yaml
# Before
storageUri: s3://models/vla-policy-v1.3

# After
storageUri: s3://models/vla-policy-v1.4
```

3. The PR is reviewed — checking training metrics, evaluation results,
   safety assessments.
4. On merge, Argo CD detects the change and rolls out the new model.

The promotion is a Git commit with: author, timestamp, review
approval, and the exact diff of what changed. This is the audit trail.

### Policy rollback as a Git revert

If the new model causes problems:

```bash
git revert <promotion-commit-hash>
git push
```

Argo CD detects the revert and rolls back to the previous model
version. The rollback is itself a Git commit — timestamped, attributed,
and explaining why the revert happened.

This is identical to reverting any other Git change. The model
deployment is just another piece of declarative state in the
repository.

### Configuration-as-code for ML

Beyond model versions, GitOps manages:

- **Safety thresholds**: Anomaly detection sensitivity, speed limits,
  restricted zones — all declared in ConfigMaps or custom resources,
  managed in Git.
- **Pipeline definitions**: KFP pipeline YAML stored in Git and
  applied via Argo CD. Pipeline versions are commits.
- **ServingRuntime configurations**: Inference engine settings, batch
  sizes, concurrency limits.
- **Network policies**: Per-workload isolation rules.
- **RBAC**: Per-namespace role bindings for team access.

Everything that affects how the AI system behaves is in Git, reviewed,
and auditable.

## GitOps + MLOps intersection

Training produces artifacts (model checkpoints, metrics, SBOMs). Those
artifacts land in object storage and get registered in the Model
Registry / MLflow. The deployment side — InferenceService YAML,
ServingRuntime config, Kueue definitions — lives in Git.

The bridge is the promotion PR: a CI step (or a human) updates the
Git-side manifests to point to the newly registered model. This cleanly
separates "ML produces artifacts" from "platform deploys artifacts,"
with Git as the control plane for the deployment half.

```
Training Pipeline (MLOps)           Deployment (GitOps)
─────────────────────────          ─────────────────────
Dataset → Train → Eval             Git repo → Argo CD → Cluster
     │                                  ↑
     └── Register model ──PR──────────┘
         (MLflow/Registry)     (update InferenceService)
```

## Multi-cluster GitOps

For multi-site physical AI deployments:

- **Hub cluster** hosts Argo CD, the Git repository connection, and
  ApplicationSets.
- **Spoke clusters** (factory-edge SNO nodes) are registered as Argo CD
  destinations via ACM integration (`GitOpsCluster` CR).
- **ApplicationSets** use the cluster generator to deploy workloads
  to all matching spokes.
- **Per-site overrides** use Kustomize overlays: a base configuration
  shared across all sites, with site-specific values (model version,
  calibration, network addresses) in per-site overlays.

A model promotion flows from the hub Git repo to all spoke clusters
through Argo CD. A rollback at one site can be independent of other
sites by using per-site overlay directories.

## Key takeaways

- GitOps provides the audit trail, reproducibility, and rollback
  mechanism that regulated physical AI deployments require.
- Model promotions are reviewed PRs. Rollbacks are git reverts. Every
  change is attributed and timestamped.
- ApplicationSets enable fleet-scale deployment across multiple
  clusters — define once, deploy everywhere.
- The GitOps/MLOps intersection separates artifact production
  (training) from artifact deployment (GitOps), with the promotion PR
  as the bridge.

## Further reading

- [OpenShift GitOps Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/) —
  Red Hat's Argo CD distribution.
- [Argo CD ApplicationSets](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/1.16/html-single/argo_cd_application_sets/) —
  Multi-application and multi-cluster deployment.
- [Argo CD Documentation](https://argo-cd.readthedocs.io/) —
  Upstream project documentation.
