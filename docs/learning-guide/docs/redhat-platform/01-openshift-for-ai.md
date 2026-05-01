# OpenShift as the AI Platform

## Why Kubernetes for AI

If you already work with OpenShift, you understand container
orchestration, declarative configuration, the operator pattern, and
namespace isolation. These same primitives that manage web applications
and databases also manage AI workloads — but with GPU scheduling added
as a first-class resource.

Kubernetes matters for AI because:

**GPU scheduling**: AI workloads request GPUs the same way they request
CPU and memory — `nvidia.com/gpu: 1` in the resource limits. The
scheduler places pods on nodes with available GPUs. No manual SSH to
GPU servers, no ad-hoc allocation scripts.

**Namespace isolation**: Training teams, inference services, and
simulation workloads run in separate namespaces with independent RBAC,
resource quotas, and network policies. A training job cannot
accidentally consume the GPU reserved for a production inference
service.

**Operator pattern**: Complex stateful services — model servers,
training controllers, pipeline engines, GPU drivers — are managed
declaratively through operators. The GPU Operator handles the entire
NVIDIA driver stack. OpenShift AI manages model serving, pipelines,
and registries. You declare what you want; operators reconcile.

**Horizontal scaling**: Training workers scale via ReplicaSets.
Inference replicas scale based on request load (Knative autoscaling,
including scale-to-zero). Fleet management services scale to match
the number of managed robots and sites.

## The NVIDIA GPU Operator on OpenShift

The GPU Operator installs from OperatorHub and manages the full
GPU software stack on every GPU node:

- **NVIDIA datacenter driver**: The kernel module that lets the OS
  communicate with the GPU.
- **NVIDIA Container Toolkit**: Enables containers to access GPUs —
  the bridge between the container runtime and the GPU driver.
- **Kubernetes Device Plugin**: Advertises `nvidia.com/gpu` resources
  to the kubelet so the scheduler can allocate GPUs to pods.
- **GPU Feature Discovery (GFD)**: Automatically labels nodes with
  GPU-specific metadata.
- **DCGM Exporter**: Exposes GPU telemetry (utilization, temperature,
  memory usage, power draw) as Prometheus metrics.

All of these deploy as DaemonSets managed by a single `ClusterPolicy`
CR. When a new GPU node joins the cluster, the operator automatically
installs the driver stack and makes the GPU available for scheduling.

### Node Feature Discovery (NFD)

NFD is a prerequisite operator that detects hardware features on each
node. For GPU nodes, NFD detects the NVIDIA PCI vendor ID and labels
the node, which triggers the GPU Operator to deploy its DaemonSets.

### GPU Feature Discovery labels

GFD applies labels that identify the GPU's capabilities:

```
nvidia.com/gpu.product=NVIDIA-L40S
nvidia.com/gpu.memory=49152
nvidia.com/gpu.family=ada-lovelace
nvidia.com/gpu.count=1
```

Workloads target specific GPU classes using these labels:

```yaml
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-L40S
resources:
  limits:
    nvidia.com/gpu: 1
```

No custom labels are needed. GFD labels are reapplied automatically
on node replacement, so GPU targeting survives infrastructure changes.

- [GPU Operator on OpenShift](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/index.html)

## What OpenShift adds over vanilla Kubernetes

For AI workloads, OpenShift provides:

**Integrated monitoring**: OpenShift ships Prometheus, AlertManager,
and a console metrics view out of the box. The GPU Operator's DCGM
Exporter feeds GPU telemetry directly into this stack — GPU
utilization, memory, temperature, and power are visible in the
OpenShift Console without additional configuration.

**OperatorHub**: The GPU Operator, Node Feature Discovery, OpenShift
AI, Service Mesh (for KServe), and Serverless (for KServe autoscaling)
all install from OperatorHub with lifecycle management. On vanilla
Kubernetes, you manage Helm charts, CRDs, and upgrades yourself.

**Security Context Constraints (SCCs)**: OpenShift enforces least-
privilege by default. The GPU Operator creates its own SCCs for
privileged components (driver DaemonSets), while user GPU workloads
run under the standard `restricted` SCC — they request
`nvidia.com/gpu: 1` and the device plugin handles the rest
transparently. The user pod does not need elevated privileges.

**Routes**: Model serving endpoints exposed via Routes get automatic
TLS termination and hostname-based routing. No manual cert-manager
configuration.

**GPU Monitoring Dashboard**: NVIDIA provides an OpenShift Console
plugin that embeds GPU metrics directly in the Console's Observe
section.

## GPU workload patterns on OpenShift

### Training workloads

Training runs as Kubernetes Jobs or custom resources managed by the
Kubeflow Training Operator:

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: vla-finetune
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      template:
        spec:
          containers:
            - name: pytorch
              resources:
                limits:
                  nvidia.com/gpu: 1
              nodeSelector:
                nvidia.com/gpu.product: NVIDIA-L40S
```

Training is typically a batch operation: schedule the job, consume GPU
for the duration, release when complete. Kueue (Kubernetes job
queueing) manages priority and fairness when multiple training jobs
compete for limited GPU resources.

### Inference workloads

Model serving runs as Deployments or KServe InferenceServices — long-
running pods that accept requests and return predictions:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: cosmos-reason
spec:
  predictor:
    model:
      modelFormat:
        name: vLLM
      runtime: vllm-runtime
      resources:
        limits:
          nvidia.com/gpu: 1
```

Inference workloads need low latency, high availability, and
autoscaling. KServe with Knative provides scale-to-zero for bursty
workloads and scale-up for traffic spikes.

### Simulation workloads

Isaac Sim runs as a Deployment with GPU resources, often with
additional requirements:

- RT core access (L40S or RTX GPUs for ray tracing)
- Large shared memory (`/dev/shm`) for physics engine data
- Persistent storage for scene assets (from Nucleus)
- Network access for streaming output (WebRTC or HLS)

Simulation workloads are typically always-on during operational hours
and represent the largest sustained GPU consumers.

## Key takeaways

- OpenShift extends Kubernetes for AI with GPU scheduling, integrated
  monitoring, OperatorHub-managed components, and security enforcement.
- The GPU Operator + NFD handle the entire NVIDIA stack: driver,
  container toolkit, device plugin, feature discovery, and telemetry.
- GFD labels enable workload-to-GPU-class targeting without custom
  node labels.
- AI workloads fit standard Kubernetes patterns: Jobs for training,
  Deployments/InferenceServices for serving, StatefulSets for
  simulation.

## Further reading

- [GPU Operator on OpenShift](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/index.html) —
  Installation and configuration guide.
- [NFD Operator on OpenShift](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/install-nfd.html) —
  Node Feature Discovery setup.
- [GPU Monitoring Dashboard](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/enable-gpu-monitoring-dashboard.html) —
  Enabling GPU metrics in the OpenShift Console.
- [Red Hat OpenShift Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/) —
  Platform documentation.
