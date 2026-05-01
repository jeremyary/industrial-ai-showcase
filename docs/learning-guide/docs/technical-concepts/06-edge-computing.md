# Edge Computing for Robotics

## Why robots cannot rely on the cloud

If you are accustomed to deploying workloads in the cloud — where
compute is elastic, bandwidth is plentiful, and latency to storage is
single-digit milliseconds — the constraints of edge robotics will
require a shift in thinking.

A robot on a factory floor cannot round-trip to a cloud data center for
every inference decision. The physics do not allow it:

### Latency

A robot arm executing a pick-and-place operation needs inference
results within 10–100 milliseconds. A round trip to a cloud endpoint
adds 50–200+ milliseconds of network latency, even on a fast
connection. For a robot catching a falling object or avoiding a
collision, 200ms is the difference between success and failure.

**The math**: Light travels ~200km in a millisecond through fiber.
A cloud region 500km away has a minimum round-trip latency of ~5ms
(speed-of-light floor), but real-world latency including routing,
encryption, and load balancer processing is typically 20–80ms. Add
inference time on the cloud GPU and the total budget is consumed.

### Bandwidth

A robot with four cameras at 720p, 30fps generates approximately
100 Mbps of raw video data. Streaming this to the cloud for
processing is expensive and often impractical — factory networks may
have limited uplink bandwidth, and many cameras across a fleet would
saturate the connection.

Edge inference processes the video locally, sending only results
(detections, decisions, telemetry) upstream. This reduces bandwidth
by orders of magnitude.

### Autonomy

Factory networks go down. Internet connections are interrupted.
Maintenance activities require network segments to be isolated.
A robot that depends on cloud connectivity for basic operation stops
working when the network is unavailable.

Edge inference ensures the robot operates independently.
Cloud connectivity enhances operation (fleet-wide analytics, model
updates, centralized monitoring) but is not required for moment-to-
moment function.

### Air gaps

As discussed in the [Industrial AI chapter](../foundations/02-industrial-ai.md),
many manufacturing environments are partially or fully air-gapped.
Models must be deployed to the edge through controlled, disconnected
channels — not pulled from cloud registries at runtime.

## Edge hardware for physical AI

Edge compute for robotics spans a range of form factors:

### On-robot compute

GPUs embedded in or mounted on the robot itself:

- **NVIDIA Jetson Orin**: The current standard for on-robot AI
  compute. Available in multiple configurations (Orin Nano, Orin NX,
  AGX Orin) with 8–64 GB unified memory and up to 275 TOPS INT8
  performance. Runs Linux (JetPack SDK) with CUDA, TensorRT, and
  container support.
- **NVIDIA Jetson Thor**: Next-generation robotics compute module
  with 128 GB unified memory and a Blackwell-architecture GPU.
  Designed for transformer-based VLA models that exceed Orin's
  memory capacity.
- **Intel/AMD industrial PCs**: x86-based edge computers with
  optional NVIDIA GPUs. More power and heat but also more compute.

On-robot compute handles the lowest-latency tasks: motor control,
collision avoidance, basic perception. The constraint is power, heat,
and physical size.

### Near-edge compute

Servers in the factory's IT room or OT infrastructure closet, within
the same physical facility as the robots:

- **NVIDIA-certified servers with L4 or L40S GPUs**: Run in a
  standard rack, connected to the factory network. Handle inference
  workloads that need more compute than on-robot hardware but cannot
  tolerate cloud latency.
- **Single Node OpenShift (SNO)**: Full OpenShift control plane and
  workloads on a single server. Provides container orchestration,
  GPU scheduling, and operator-based lifecycle management at the
  edge. Managed as an ACM spoke from the hub cluster.
- **MicroShift**: Minimal Kubernetes for resource-constrained edge
  devices. Runs on RHEL for Edge, managed via Ansible.

Near-edge servers typically handle tasks like VLA inference, vision-
language reasoning, and local fleet coordination.

### Hub / data center

The centralized cluster:

- **Training**: GPU clusters (L40S, H100) for fine-tuning foundation
  models on domain-specific data.
- **Simulation**: GPU servers running Isaac Sim digital twins for
  training, validation, and monitoring.
- **Fleet management**: Centralized mission dispatch, policy promotion,
  anomaly analytics.
- **Model registry**: Centralized model versioning and promotion
  pipeline.

## The hub-spoke pattern

Physical AI deployments follow a hub-spoke architecture:

```
                    ┌─────────────────────────┐
                    │         Hub              │
                    │  Training / Simulation   │
                    │  Fleet Mgmt / Registry   │
                    │  Observability           │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
        │  Site A    │ │  Site B    │ │  Site C    │
        │  SNO/Edge  │ │  SNO/Edge  │ │  SNO/Edge  │
        │  Inference │ │  Inference │ │  Inference │
        │  Dispatch  │ │  Dispatch  │ │  Dispatch  │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │              │              │
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │ Robots  │   │ Robots  │   │ Robots  │
         │ Cameras │   │ Cameras │   │ Cameras │
         │ Sensors │   │ Sensors │   │ Sensors │
         └─────────┘   └─────────┘   └─────────┘
```

### Data flows

**Hub → spoke (commands):**

- Model updates (new policy versions, configuration changes)
- Mission assignments
- Policy promotions (via GitOps)
- ACM governance policies

**Spoke → hub (telemetry):**

- Robot telemetry (positions, joint states, task completion)
- Inference metrics (latency, throughput, error rates)
- Camera frames (selectively, not full video — bandwidth constraints)
- Safety alerts and anomaly reports

**Data flow mechanisms:**

- **GitOps (Argo CD)**: Declarative state flows from hub Git repo to
  spoke clusters via ACM + ApplicationSets.
- **Kafka federation**: Event data flows spoke→hub via Kafka
  MirrorMaker 2, which replicates topics across clusters.
- **Direct API**: For latency-sensitive queries, spoke services call
  hub APIs (fleet manager, model registry) directly.

### Disconnected operation

When network connectivity to the hub is lost:

- The spoke continues operating with its current model versions and
  configuration.
- Mission dispatch falls back to local rules (if the Fleet Manager is
  hub-resident) or continues with the local Mission Dispatcher.
- Telemetry buffers locally (in Kafka) and forwards when connectivity
  returns.
- Model updates wait until connectivity is restored and the GitOps
  sync completes.

This resilience is why the spoke must have sufficient compute and
storage to operate independently — it is not a thin client.

## Edge deployment challenges

### Model optimization for edge

Foundation models are large. A 7B parameter VLA in FP16 requires 14 GB
of GPU memory just for weights. Edge GPUs (Jetson Orin NX: 8–16 GB)
cannot fit these models without optimization:

- **Quantization**: Reduce precision from FP16 to INT8 or INT4.
  Reduces memory by 2–4x with modest accuracy loss.
- **Pruning**: Remove redundant model parameters.
- **Distillation**: Train a smaller "student" model to mimic a
  larger "teacher" model.
- **TensorRT optimization**: NVIDIA's inference optimizer that fuses
  layers, selects optimal kernels, and quantizes for the target
  hardware.

### Over-the-air (OTA) model updates

Updating models on edge devices in the field:

- Models are packaged as container images or stored in model registries.
- Updates flow through GitOps: the InferenceService manifest in Git is
  updated to reference the new model version.
- ACM propagates the change to spoke clusters.
- Argo CD on the spoke syncs the new manifest and triggers a rollout.
- For air-gapped sites, model artifacts are staged to a local mirror
  registry during scheduled connectivity windows.

### Resource management

Edge nodes are resource-constrained. A single-node OpenShift cluster
running inference, local Kafka, and observability agents must carefully
budget CPU, memory, and GPU across all workloads. Kueue (the Kubernetes
job queueing system) and resource quotas ensure that inference workloads
do not starve operational services.

## Key takeaways

- Edge computing is not optional for robotics — latency, bandwidth,
  autonomy, and air-gap constraints make cloud-only deployment
  impractical for real-time robot control.
- The hub-spoke pattern separates training and fleet management (hub)
  from inference and mission execution (spoke/edge).
- Edge hardware ranges from on-robot modules (Jetson) to near-edge
  servers (SNO with GPU) to full edge clusters.
- Model optimization (quantization, TensorRT) is essential for fitting
  foundation models on edge hardware.
- GitOps + ACM provides the deployment pipeline from hub to edge,
  with disconnected operation as a first-class design concern.

## Further reading

- [NVIDIA Jetson Developer](https://developer.nvidia.com/embedded-computing) —
  NVIDIA's edge compute platform for robotics and AI.
- [Red Hat Single Node OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/installing_on_a_single_node/) —
  Full OpenShift on a single server for edge deployments.
- [Red Hat MicroShift](https://docs.redhat.com/en/documentation/red_hat_build_of_microshift/) —
  Minimal Kubernetes for constrained edge devices.
- [NVIDIA TensorRT](https://developer.nvidia.com/tensorrt) —
  High-performance inference optimizer for NVIDIA GPUs.
