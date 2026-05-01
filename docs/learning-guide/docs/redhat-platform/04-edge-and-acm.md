# Edge & Multi-Cluster Management

## Red Hat Advanced Cluster Management (ACM)

ACM is the multi-cluster management layer for OpenShift. It runs on a
hub cluster and manages spoke (managed) clusters — provisioning,
monitoring, and governing them from a single control plane.

For physical AI, ACM is the mechanism that governs a fleet of factory-
edge clusters the same way a fleet manager governs a fleet of robots:
centralized policy, distributed execution.

### Core capabilities

**ManagedCluster registration**: Each spoke cluster runs a lightweight
agent (klusterlet) that communicates with the hub. ACM can provision
new clusters (via Hive), import existing clusters, or accept self-
managed clusters. Managed clusters are labeled with metadata (region,
GPU class, environment, role) that drives policy placement.

**Policy-based governance**: ACM Policies are Kubernetes CRDs that
define compliance requirements. A `Policy` resource contains one or
more templates (ConfigurationPolicy, CertificatePolicy, etc.) that
declare what must exist or must not exist on target clusters.

```yaml
apiVersion: policy.open-cluster-management.io/v1
kind: Policy
metadata:
  name: require-network-baseline
spec:
  remediationAction: enforce
  policy-templates:
    - objectDefinition:
        apiVersion: policy.open-cluster-management.io/v1
        kind: ConfigurationPolicy
        metadata:
          name: deny-all-ingress
        spec:
          remediationAction: enforce
          object-templates:
            - complianceType: musthave
              objectDefinition:
                apiVersion: networking.k8s.io/v1
                kind: NetworkPolicy
                ...
```

**Placement**: Defines which clusters receive which policies, based on
label selectors. "Apply this STIG compliance scan to all clusters
labeled `role: companion`" or "Deploy the VLA serving stack to all
clusters with `nvidia.com/gpu.product: NVIDIA-L4`."

**PlacementBinding**: Connects a Policy to a Placement — the policy
applies to the clusters selected by the placement rule.

**Remediation modes**:

- `inform`: Report violations but do not fix them. For audit and
  monitoring.
- `enforce`: Automatically remediate violations — create missing
  resources, correct drifted configurations. For active governance.

### ACM + GitOps integration

ACM integrates with Argo CD through `GitOpsCluster` CRs. When a new
managed cluster registers with ACM, it can be automatically added as
an Argo CD destination. ApplicationSets using the cluster generator
then deploy workloads to the new cluster without manual intervention.

This enables a "zero-touch" edge provisioning pattern:

1. A new factory-edge SNO cluster boots and self-registers with ACM.
2. ACM applies baseline policies (RBAC, network, compliance scanning).
3. The GitOpsCluster CR adds it as an Argo CD destination.
4. ApplicationSets deploy the workload stack (inference, dispatch,
   monitoring).
5. The new site is operational without anyone SSHing into a server.

### Multi-cluster observability

ACM includes a MultiClusterObservability capability based on Thanos.
Each managed cluster runs a metrics collector that remote-writes to
the hub's Thanos Receiver. The hub aggregates metrics across all
clusters, enabling:

- Fleet-wide GPU utilization dashboards
- Cross-site inference latency comparison
- Anomaly detection across the entire fleet
- Compliance evidence aggregation for auditors

- [ACM Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/)

## Single Node OpenShift (SNO)

SNO collapses the OpenShift control plane and worker into a single
machine. It runs the full OpenShift stack (API server, etcd,
controllers, operators) alongside workloads on one server.

### Why SNO for factory edge

- **Single server**: Many factory edge locations have space and power
  for one server, not three. SNO runs on one machine.
- **Full OpenShift**: Despite being a single node, SNO supports the
  full operator ecosystem — GPU Operator, Service Mesh, Compliance
  Operator, Vault Secrets Operator. The same tools and patterns you
  use on the hub work on SNO.
- **ACM-managed**: SNO clusters register as managed clusters with ACM,
  receiving policies, workloads, and monitoring from the hub.
- **GPU support**: A factory-edge SNO with an L4 or L40S GPU runs
  KServe inference workloads with the same InferenceService CRDs
  used on the hub.

### Installation

SNO installs via the Assisted Installer (web-based or API-driven).
For large-scale edge deployments, image-based installation provides
a pre-install-at-central-site, ship-to-remote-site, reconfigure-on-
boot pattern that scales to hundreds of sites.

- [SNO Installation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/installing_on_a_single_node/)

## MicroShift — Minimal edge Kubernetes

MicroShift is a minimal Kubernetes distribution for devices with
limited resources (2 CPU cores, 2 GB RAM). It runs on RHEL for Edge
and provides basic container orchestration without the full OpenShift
control plane overhead.

**Where MicroShift fits**: On-robot compute (Jetson-class devices,
industrial PCs) where you need container management but cannot run
a full Kubernetes API server. MicroShift is managed via Ansible and
updated through rpm-ostree.

**Where SNO fits**: Factory IT closet servers with more resources (16+
cores, 64+ GB RAM, GPU). Runs the full OpenShift stack for inference
serving, local fleet dispatch, and monitoring.

- [MicroShift Documentation](https://docs.redhat.com/en/documentation/red_hat_build_of_microshift/)

## The hub-spoke pattern for physical AI

The complete pattern for multi-site physical AI:

**Hub (data center / cloud)**:
- Training workloads (GPU clusters with L40S/H100)
- Isaac Sim digital twin (L40S with RT cores)
- Cosmos world models (batch generation on L40S or Thor)
- Fleet Manager (centralized mission dispatch and policy)
- Model Registry and MLflow (experiment tracking)
- Console / dashboard (multi-site oversight)
- ACM hub (governance, observability)
- Argo CD (GitOps control plane)

**Spoke (factory edge, SNO)**:
- VLA inference serving (L4 or L40S, via KServe)
- Mission Dispatcher (local mission execution)
- Camera feeds and perception (Cosmos Reason on L4)
- Local Kafka (event streaming, federated to hub)
- Telemetry collection (metrics and events)

**Data flows**:
- Hub → spoke: Model updates, policy changes, mission assignments
  (via GitOps + Kafka)
- Spoke → hub: Telemetry, camera frame references, safety alerts
  (via Kafka MirrorMaker 2)

## Key takeaways

- ACM provides centralized governance over distributed factory-edge
  clusters — policy enforcement, compliance scanning, and observability
  from a single hub.
- Policies with `enforce` remediation ensure every spoke meets baseline
  requirements automatically.
- SNO runs the full OpenShift stack on a single server at the factory
  edge, supporting GPU workloads and the full operator ecosystem.
- MicroShift provides minimal container orchestration for on-robot
  devices.
- The hub-spoke pattern separates training and management (hub) from
  inference and execution (spoke), with GitOps and Kafka as the
  communication channels.

## Further reading

- [ACM Governance](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.13) —
  Policy-based cluster governance.
- [SNO Edge Computing](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/edge_computing/) —
  Edge computing patterns on OpenShift.
- [Red Hat Device Edge](https://docs.redhat.com/en/documentation/red_hat_device_edge/) —
  MicroShift and RHEL for Edge documentation.
