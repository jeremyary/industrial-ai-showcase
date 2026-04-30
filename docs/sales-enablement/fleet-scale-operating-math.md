# Fleet-Scale Operating Math

> [!NOTE]
> This project was developed with assistance from AI tools.

This document provides scaling projections for the Warehouse Blueprint architecture.
Every number is either **measured on the reference cluster** or **derived from upstream
documentation** with the source cited. Where we have not measured, we say so.

## Reference Cluster Baseline (Measured)

| Dimension | Value | Source |
|-----------|-------|--------|
| Hub cluster | 1 × OSD (13 nodes: 3 master, 2 infra, 3 GPU, 5 worker) | Cluster inventory |
| Spoke clusters | 1 × companion (bare-metal, single node) | ACM ManagedCluster |
| Simulated factories | 2 (Factory A on companion, Factory B on hub) | Topic inventory |
| Kafka brokers | 3 × (500m–2 CPU, 2–4 Gi each) | Pod resource specs |
| Kafka topics | 13 total (5 per factory + 3 shared) | KafkaTopic CRs |
| Argo CD apps | 53 | Application list |
| ACM managed clusters | 1 (companion) | ManagedCluster list |
| Rollback elapsed time | 6–18s (bimodal: Argo poll timing) | Measured 2026-04-30, 6 runs |

## Per-Factory Kafka Footprint

Each factory adds 5 dedicated Kafka topics:

| Topic | Partitions | Message size | Rate (during mission) | Rate (idle) |
|-------|------------|-------------|----------------------|-------------|
| `{factory}.telemetry` | 6 | ~276 B | 5 Hz per robot | 0 |
| `{factory}.missions` | 6 | ~436 B | Bursty (per dispatch) | 0 |
| `{factory}.ops-events` | 6 | ~210 B | ~2/mission lifecycle | 0 |
| `{factory}.cameras.{cam}` | 1 | ~50–100 KB (JPEG) | 10 Hz per camera | 10 Hz |
| `{factory}.cameras.commands` | 1 | ~100 B | Rare | 0 |

Message sizes measured from Pydantic model serialization. Camera frame sizes depend
on resolution and compression; 50–100 KB is typical for 640×480 JPEG.

**Per-factory steady-state bandwidth (1 robot active, 1 camera):**

- Telemetry: 5 Hz × 276 B = **1.4 KB/s**
- Camera: 10 Hz × 75 KB = **750 KB/s**
- Missions + events: negligible (bursty, <1 KB/s amortized)
- **Total per factory: ~750 KB/s** (dominated by camera frames)

**Without camera streaming (companion-local only):**

- **Total per factory: ~2 KB/s** (telemetry + events)

## Kafka Scaling Projections

### Topic and partition growth

| Factories | Dedicated topics | Total partitions (dedicated) | Shared topics | Total partitions |
|-----------|-----------------|------------------------------|---------------|-----------------|
| 2 | 10 | 40 | 3 (fleet-wide) | 55 |
| 10 | 50 | 200 | 3 | 215 |
| 50 | 250 | 1,000 | 3 | 1,015 |
| 100 | 500 | 2,000 | 3 | 2,015 |

**AMQ Streams (Strimzi) documented limits:**

- Partitions per broker: recommended ≤4,000 (Strimzi docs, "Designing your deployment")
- With 3 brokers and RF=3: effective partition budget is ~4,000 total
- **At 100 factories (2,015 partitions): within budget on 3 brokers**
- **At 200 factories (~4,000 partitions): approaching single-broker limit, add a 4th broker**

Source: [Strimzi — Designing your Kafka deployment](https://strimzi.io/docs/operators/latest/deploying#con-overview-components-str)

### Bandwidth at the hub

Camera frames are the dominant load. Two deployment models:

**Model A — Camera frames stay at the spoke (recommended):**

Each factory's camera feed is consumed locally by the companion-side mission dispatcher
and Isaac Sim viewer. Only telemetry, missions, and events cross the WAN to the hub.

| Factories | Hub inbound bandwidth |
|-----------|-----------------------|
| 10 | ~20 KB/s |
| 50 | ~100 KB/s |
| 100 | ~200 KB/s |

**Model B — Camera frames forwarded to hub (current demo topology):**

The demo forwards camera frames to the hub for the console viewer. At scale, this
becomes the bottleneck.

| Factories | Hub inbound bandwidth |
|-----------|-----------------------|
| 10 | ~7.5 MB/s |
| 50 | ~37.5 MB/s |
| 100 | ~75 MB/s |

**Recommendation:** Model A for production. Model B is demo-only. At >10 factories,
camera streams should be consumed at the spoke or via direct WebRTC to the viewer.

### Broker resource scaling

| Factories | Brokers | CPU (total) | Memory (total) | Storage (total) |
|-----------|---------|-------------|----------------|-----------------|
| 2 (current) | 3 | 1.5–6 cores | 6–12 Gi | 30 Gi |
| 10 | 3 | 1.5–6 cores | 6–12 Gi | 50 Gi |
| 50 | 3 | 3–9 cores | 12–24 Gi | 200 Gi |
| 100 | 5 | 5–15 cores | 20–40 Gi | 500 Gi |

These are estimates based on Strimzi sizing guidance for the given partition counts
and message rates. We have not load-tested beyond 2 factories. The storage estimate
assumes 7-day retention (current config: `log.retention.hours: 168`).

## Argo CD Scaling

### Per-factory GitOps footprint

Each factory adds 1 Argo CD Application (via ApplicationSet git-directory generator).
The Application manages a Kustomization with ~6 resources (namespace, deployment,
service, configmap, imagestream, serviceaccount).

| Factories | Argo Applications (factory) | Total Argo Applications |
|-----------|---------------------------|------------------------|
| 2 (current) | 2 | 53 |
| 10 | 10 | 61 |
| 50 | 50 | 101 |
| 100 | 100 | 151 |

**OpenShift GitOps documented guidance:**

- Default Argo CD controller: tested to ~300 Applications (Red Hat OpenShift GitOps docs)
- ApplicationSet generator creates Applications declaratively from directory structure
- Sharding (multiple controller replicas with hash-based assignment) available for >300 apps

Source: [OpenShift GitOps — Scaling](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/)

**At 100 factories (151 apps): well within single-controller capacity.**

### Rollback timing at scale

Measured rollback on the reference cluster: 6–18s. The variance comes from Argo CD's
reconciliation poll interval (default 180s, but manual sync is used in the demo).

At scale, rollback targets a single factory's Application — it does not fan out.
The git-revert + Argo-sync path is per-Application, so rollback time is **independent
of fleet size**. What changes at scale is the probability of concurrent rollbacks.

**What we have NOT measured:**

- Rollback time when Argo controller is under load from many concurrent syncs
- Whether the GitHub API rate limit (5,000 requests/hour for authenticated tokens)
  becomes a bottleneck for git-revert operations at high concurrency
- Impact of webhook-driven sync vs poll-driven sync on rollback latency

## ACM Fan-Out

### Spoke cluster provisioning

ACM manages spoke clusters via ManagedCluster CRs. Each factory site runs a spoke
cluster with the mission-dispatcher, fake-camera, and policy-version ConfigMap.

| Factories | ManagedClusters | ACM Policies (est.) |
|-----------|----------------|---------------------|
| 1 (current) | 1 | ~5 |
| 10 | 10 | ~50 |
| 50 | 50 | ~250 |
| 100 | 100 | ~500 |

**ACM documented limits:**

- ACM 2.12: tested to 2,000 managed clusters (Red Hat ACM documentation,
  "Sizing your cluster")
- Policy propagation: seconds per cluster, limited by the policy-propagator controller

Source: [Red Hat ACM — Scaling](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/)

**At 100 factories: 5% of ACM's documented capacity.**

### What ACM manages per spoke

- GPU Operator configuration (ClusterPolicy)
- Namespace + RBAC for workloads
- Kafka consumer credentials (MirrorMaker or direct)
- Policy compliance (security baseline, node configuration)
- Observability collection (metrics forwarded to hub Prometheus/Thanos)

## Hub Resource Summary

Projecting hub resource requirements by component:

| Component | 2 factories (measured) | 10 factories (projected) | 50 factories | 100 factories |
|-----------|----------------------|------------------------|--------------|---------------|
| Kafka brokers | 3 pods, 6 CPU, 12 Gi | 3 pods, 6 CPU, 12 Gi | 3 pods, 9 CPU, 24 Gi | 5 pods, 15 CPU, 40 Gi |
| Argo CD | 1 controller, 250m, 1 Gi | Same | Same | Same |
| ACM | ~2 Gi overhead | ~3 Gi | ~5 Gi | ~8 Gi |
| Fleet Manager | 1 pod, 200m, 256 Mi | 1 pod, 500m, 512 Mi | 2 pods, 1 CPU, 1 Gi | 3 pods, 2 CPU, 2 Gi |
| Console backend | 1 pod, 100m, 256 Mi | Same | Same | Same |
| **Hub total (excl. GPU)** | **~8 CPU, 16 Gi** | **~9 CPU, 18 Gi** | **~14 CPU, 32 Gi** | **~22 CPU, 52 Gi** |

**GPU workloads are per-factory in production.** Each factory site runs its own
VLA inference and perception stack on local GPUs — the robot cannot tolerate
WAN round-trips for real-time action selection. The hub may run centralized
workloads (training, scene simulation, anomaly analysis) that serve multiple
factories, but inference is always spoke-local. Per-spoke GPU requirements
depend on the embodiment and model: NVIDIA documents a 16 GB minimum for
GR00T N1.7-3B inference, so a single 24 GB GPU (e.g., L4, A10G) handles
one robot; multi-robot sites need proportional GPU capacity.

The reference demo consolidates GPU workloads onto the hub for simplicity
(2 factories, no real WAN). This is a demo topology choice, not an
architectural recommendation.

**Spoke GPU footprint (per factory, production):**

| Workload | VRAM required | Count | Notes |
|----------|--------------|-------|-------|
| VLA inference (GR00T N1.7-3B) | 16 GB minimum (NVIDIA GR00T N1 docs); ~7 GB actual model footprint at bf16 | 1 per robot | 10 Hz action output; 100ms latency budget. A 3B-param model in bf16 occupies ~6–7 GB VRAM. NVIDIA's documented minimum is 16 GB, which provides headroom for the vision encoder, KV cache, and action head. A 24 GB GPU (L4, A10G, Jetson AGX Orin) is the documented deployment target. Smaller VLAs (SmolVLA-450M, π0) fit comfortably with even more headroom. |
| Perception / anomaly detection | 8–16 GB (model-dependent) | 0–1 | Depends on whether perception runs at the spoke or hub. A dedicated camera-analysis model (e.g., a small VLM or classical CV pipeline) at the spoke fits on a 24 GB GPU. In our reference, Cosmos Reason runs centrally on the hub — but a production deployment with WAN latency constraints may push perception to the spoke. |
| **Spoke GPU total** | | **1–2 GPUs per factory** | Exact sizing depends on VLA model choice and whether perception is spoke-local |

NVIDIA's documented deployment targets for GR00T inference include Jetson AGX
Orin (32–64 GB unified memory) and Jetson Thor for onboard/edge inference.
Datacenter GPUs with ≥16 GB VRAM (L4, T4, A10G) are suitable for
rack-mounted spoke deployments. Smaller open VLAs (OpenVLA-7B in INT4,
SmolVLA, π0) have similar or lower requirements.

**Hub GPU footprint (centralized, shared):**

| Workload | VRAM required | Count | Scales with |
|----------|--------------|-------|-------------|
| VLA fine-tuning (GR00T N1.7-3B) | 40–48 GB per GPU (NVIDIA recommends multi-GPU; single-GPU fine-tuning requires ≥40 GB) | 1–2 | Training frequency, not factory count. Data-parallel across 2–3 GPUs for faster convergence. NVIDIA's LeRobot-based fine-tuning examples target multi-GPU setups with 48 GB-class GPUs. |
| Scene simulation (Isaac Sim) | 16 GB minimum, 48 GB recommended for complex scenes (NVIDIA Isaac Sim requirements). **Requires RT cores** for ray-traced sensor rendering — i.e., L40S, RTX 6000 Ada, or RTX 4090; L4, A100, and H100 lack RT cores and cannot run Isaac Sim. | 1 per concurrent sim | Number of sim environments, not factory count |
| Cosmos Reason (anomaly analysis) | 32 GB minimum for the 8B model (NVIDIA Cosmos Reason docs). Validated on Hopper (H100/H200) and Blackwell architectures. | 1 | Event volume from all factories. Scales slowly — a single instance handles events from many factories since analysis is per-image, not streaming. |

Hub GPU workloads scale with training cadence and simulation demand, not
linearly with factory count. Isaac Sim's RT core requirement constrains GPU
selection to Ada Lovelace or newer consumer/professional GPUs (L40S, RTX 6000
Ada). Cosmos Reason is validated on Hopper and Blackwell; Ada Lovelace (L40S)
may work but is not in NVIDIA's validated matrix.

## Failure Modes

### Hub loss

If the hub becomes unreachable:

- **Spoke robots continue operating.** The mission-dispatcher and VLA inference run
  locally on the spoke. Active missions complete. The robot does not stop.
- **New missions are not dispatched.** The Fleet Manager on the hub creates missions.
  Spokes queue locally if hub connectivity is lost (Kafka consumer offset tracking).
- **Telemetry buffers on the spoke.** Kafka producers buffer locally. When connectivity
  restores, messages are delivered in order (at-least-once semantics).
- **Policy updates are frozen.** Argo CD cannot sync. The last-applied policy remains
  active. This is safe — no rollback can happen, but no promotion either.

**We have not tested hub-loss scenarios.** The above is architectural analysis, not
measured behavior.

### Spoke loss

If a spoke becomes unreachable:

- **Hub observability shows stale data.** Telemetry stops updating. The console would
  show the last-known position and status.
- **Other spokes are unaffected.** Kafka topic isolation (per-factory topics) means
  one spoke's failure creates no backpressure on others.
- **Missions in flight are lost** for that spoke. No acknowledgment reaches the hub.
  The Fleet Manager would need timeout-based detection (not currently implemented).

### Kafka broker loss

With RF=3 and `min.insync.replicas=2`:

- **1 broker loss: no data loss, no downtime.** Producers and consumers continue
  with the remaining 2 brokers. Leader election is automatic.
- **2 broker loss: producers block.** Cannot meet min-ISR. Consumers can still read
  existing data. The cluster is degraded but not destroyed.

## What This Document Does Not Cover

- **Network topology between hub and spokes.** VPN, SD-WAN, direct connect — this
  is site-specific and affects latency, not throughput math.
- **Multi-region hub HA.** The reference uses a single hub. Active-passive hub failover
  is possible via ACM but not demonstrated.
- **Kafka MirrorMaker for spoke-to-hub replication.** The reference uses direct
  producer-to-hub connections. MirrorMaker is an option for air-gapped or
  network-segmented deployments but is not deployed.
- **Cost modeling.** Cloud instance sizing and pricing are customer-specific.
- **Multi-GPU scale-out.** Multi-GPU inference (tensor parallelism, pipeline
  parallelism) for higher throughput is a separate capacity planning exercise.
- **Cosmos Transfer / world-generation models.** Cosmos Transfer 2.5-2B requires
  ~65 GB VRAM (NVIDIA docs) — it does not fit on a single L40S (48 GB) and is
  not deployed in the reference. Multi-GPU or H100 deployment is required.
