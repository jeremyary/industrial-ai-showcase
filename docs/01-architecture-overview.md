# 01 — Architecture Overview

This document describes the architecture in narrative form. The component-by-component spec lives in `02-component-catalog.md`; the data-flow sequences live in `03-data-flows.md`. Read all three together when you need the full picture.

## Layering

The reference is organized into seven layers, stacked from substrate to experience:

1. **Foundation** — OpenShift cluster, GPU Operator, GitOps, ACM, storage, observability, security baseline.
2. **Platform services** — OpenShift AI, Service Mesh, AMQ Streams, Data Foundation buckets.
3. **NVIDIA stack** — Nucleus / USD backend, Isaac Sim, Isaac Lab, Kit App Streaming, Cosmos Predict/Transfer, Cosmos Reason 2 (VLM for perception), GR00T / OpenVLA serving.
4. **Integration layer** — Fleet manager, mission dispatcher, WMS stub, MCP servers, LangGraph agents.
5. **Edge layer** — Device Edge / MicroShift targets, GitOps spokes, bootable containers.
6. **Experience layer** — The Showcase Console.
7. **Operations layer** — Runbooks, demos, observability dashboards, incident playbooks.

Each layer depends only on the ones beneath it. The Showcase Console reaches all the way down via deliberate APIs, but it never bypasses the platform.

## The deployment topology

The showcase runs as a **federated deployment** from the start, because the multi-site story is one of Red Hat's sharpest differentiators and it cannot be faked.

- **Hub cluster** — the primary OpenShift cluster with 2–3 L40S nodes. Hosts the Mega core (Nucleus, Isaac Sim, Cosmos, GR00T, Metropolis, fleet manager), the Showcase Console, and the ACM hub for managing spokes.
- **Spoke cluster A** — represents "Factory A." A smaller OpenShift cluster (Single-Node OpenShift is fine initially, a 3-node compact cluster in maturity). Runs the local fleet manager slice, local cameras→Metropolis pipeline, and edge-ready policy serving.
- **Spoke cluster B** — represents "Factory B." Same pattern as A. Demonstrates independent per-site operation while central policy governance holds.
- **Edge targets** — MicroShift nodes simulating Jetson-class edge compute at each factory. In the first incarnation these can be VMs; physical Jetson Thor/Orin devices can be swapped in later.

For the lab reality: Spokes A and B may be Single-Node OpenShift instances running as virtual machines, or OpenShift Virtualization-hosted nested clusters on the hub, depending on hardware available. The architecture is indifferent to this as long as the control-plane topology is real.

## The core loops

The entire system is animated by four closed loops. Each one is a full end-to-end pathway through the stack, and each one is a distinct demo "beat" the Showcase Console can invoke.

### Loop 1 — Operational inference (factory runtime)

On-site cameras (simulated by the companion's fake-camera service in Phase 1) publish frames to Kafka. A hub-side obstruction-detector pod calls Cosmos Reason 2-8B for visual reasoning and emits structured safety alerts. The fleet manager consumes alerts alongside pending missions, replans when an active route crosses an alerted zone, and dispatches reroutes. On the companion edge, the Mission Dispatcher's Waypoint Planner drives the robot pose and calls OpenVLA on pick for the manipulation policy. Telemetry federates back to hub; the Isaac Sim digital twin reflects reality. Observability traces the whole path. See `03-data-flows.md` for topics and schemas.

**What this demonstrates**: "this is a physical AI factory running." Applies to all three audience archetypes; the narrative layering differs by depth.

### Loop 2 — Policy training and promotion

A policy-training job runs Isaac Lab 3.0 with a scenario configuration. The trained policy is registered in the OpenShift AI model registry with MLflow tracking. A validation run in Isaac Sim evaluates the policy against a curated scenario suite. Results return to MLflow. A human (or, later, an automated gate) promotes the policy. GitOps picks up the new serving manifest and rolls it out — first to the hub, then via ACM to the edge targets.

**What this demonstrates**: "this is MLOps for physical AI, with governance, lineage, and safe promotion." Primary appeal: Archetypes B and C.

### Loop 3 — Synthetic data generation and fleet learning

Cosmos Transfer and Cosmos Predict 2.5 generate synthetic scenes and action-conditioned videos. These feed back into Isaac Sim as new training scenarios. Isaac Lab trains improved policies against the larger distribution. The improved policies enter Loop 2. Real-world edge telemetry (from the sim-to-real loop) feeds back into Cosmos for re-grounding.

**What this demonstrates**: "the stack learns from its own fleet." Primary appeal: Archetype C.

### Loop 4 — Agentic orchestration

A LangGraph agent, triggered by a Showcase Console command or a scheduled analysis, calls MCP servers exposing Omniverse, Isaac Sim, and the fleet manager. The agent can compose a what-if experiment (spin up a scenario, run policy variants, collect metrics, summarize), a fleet intervention (route-around-incident, load-balance), or a data-gathering exploration (coverage analysis of training distribution).

**What this demonstrates**: "LLM agents become operators of the physical world, self-hosted, on Red Hat." Primary appeal: Archetype C, with emerging relevance to Archetype B.

## Why this topology rather than a single cluster

A temptation is to keep everything in one OpenShift cluster for simplicity. Resist it. Three reasons:

1. **The multi-site story is the hybrid-cloud argument in miniature.** Without real ACM federation, Red Hat's strongest differentiator is an assertion, not a demo.
2. **Edge constraints must be honored.** MicroShift on constrained hardware will reveal what falls over when you try to run the full hub stack there. That's exactly what customers with real factories need to see Red Hat has already solved.
3. **The sales narrative depends on it.** Every industrial customer operates N factories, each of which is its own site. Demonstrating N=2 spokes is enough to be credible; demonstrating N=1 is not.

## Cross-cutting concerns

### Security and supply chain

Enforced from Phase 0, not retrofitted:

- All images built by this project are Sigstore-signed via Cosign in CI. `policy.sigstore.dev` admission controller enforces signature verification at the cluster edge.
- SBOMs in SPDX JSON generated per image (Syft), attached as image attestations.
- Base images are UBI9-minimal or NVIDIA CUDA-on-UBI variants; no Alpine, no Debian slim, no untrusted pulls.
- Host nodes apply a STIG-aligned MachineConfig profile; FIPS mode available as a toggle.
- East-west traffic is mTLS via Service Mesh; all service-to-service auth uses workload identity from the mesh, not static tokens.
- Shop-floor network reach from pods uses Multus NetworkAttachmentDefinitions, with explicit allowlists documented per deployment.
- Secrets via OpenShift built-in Secret + External Secrets Operator pulling from Vault in environments where that's available; in-cluster HashiCorp Vault deployment as a fallback.

### Observability

Single pane of glass across OpenShift monitoring (Prometheus + Thanos), OpenShift Logging (Loki), OpenTelemetry traces (Tempo), and GPU-specific metrics (DCGM exporter). Dashboards target three personas:

- **Operator view** — cluster health, GPU utilization, sim throughput, policy serving QPS and latency.
- **Data scientist view** — training progress, validation results, MLflow integration deep links.
- **Sales view** — the simplified dashboards surfaced inside the Showcase Console during demos; show what matters for the audience, hide the rest.

### Storage

- **USD assets**: Nucleus-backed initially; S3-compatible object store via ODF RGW for forward-compatibility with `ovstorage`-based deployments.
- **Datasets and checkpoints**: block storage (ODF) for training I/O; object storage for cold archive.
- **Image registry**: OpenShift internal registry, mirrored from Quay for the upstream content the project consumes.
- **Scene library**: Git LFS for smaller USD scenes; larger scenes live on Nucleus.

### Networking

- Hub cluster exposes services via HAProxy-backed Routes; internal-only endpoints stay as Services with ClusterIP.
- Nucleus exposes WebSocket + HTTPS via Route with SNI.
- Kit App Streaming exposes WebRTC signaling via Route, with the streaming data plane on a dedicated Route with WebRTC-aware TLS termination.
- Spoke-to-hub traffic flows over ACM's Submariner or equivalent; fleet events traverse MirrorMaker on Kafka.
- Edge-to-spoke for MicroShift nodes uses standard Kubernetes primitives over ingress; failover to queue-based messaging for intermittent connectivity.

## What NVIDIA provides that we consume

This list is the "upstream dependency" surface. When these change (and they will, given the velocity of NVIDIA's releases), this reference needs to adapt — but nothing we build should *replace* anything in this list.

- Nucleus / `ovstorage` for USD collaboration.
- Isaac Sim / Isaac Lab for simulation and RL training.
- Omniverse Kit SDK + Kit App Streaming for building and streaming apps.
- Cosmos Predict 2.5 / Cosmos Transfer NIMs for world foundation models.
- GR00T N1.7 (and forthcoming N2) as the primary humanoid VLA; OpenVLA for the Phase-1 warehouse demo on the AMD edge.
- Cosmos Reason (VLM) for visual reasoning / obstruction detection — replaces the earlier Metropolis VSS plan per ADR-027.
- Omniverse MCP servers for agentic access.
- Jetson Thor / Orin as edge compute targets (on the roadmap side).
- GPU Operator, Network Operator (on the OpenShift substrate side).

## What we build that is genuinely additive

This list is the reason the project exists. None of these are in any NVIDIA reference; they are Red Hat's value-add:

- The GitOps topology spanning hub → spoke → edge with bootable-container identity across all three.
- The ACM federation for multi-site policy and scenario governance.
- The MLflow-backed MLOps layer for robot brains, with lineage to sim episodes.
- The OpenShift Virtualization integration to run Omniverse Kit workstations and container sims on one cluster.
- The Showcase Console and its audience-aware presentation abstraction.
- The LangGraph/MCP agentic orchestration spine.
- The security/compliance/air-gapped posture baked in.
- The specific fleet-manager integration pattern that keeps the reference vendor-neutral across WMS, MES, and SCADA systems.

## Non-obvious architectural choices worth calling out

- **Nucleus stays** for Phase 1, even though `ovstorage` is architecturally cleaner. Reason: customers are on Nucleus today and need migration guidance, not purism. A Phase-2 variant adds an `ovstorage` path.
- **Kit App Streaming is a deliberate choice over thick-client Kit workstations for demos.** The Showcase Console embeds a Kit App Streaming viewport; no remote desktops, no VNC, no fat-client distribution.
- **Everything that serves LLM/VLA inference goes through vLLM/KServe, including the Cosmos NIMs where possible.** Reason: one serving surface, consistent observability, consistent lifecycle. Where NIMs can't be replaced because they're packaged as runnables themselves, they're deployed as OpenShift Deployments with KServe-equivalent observability wrappers.
- **Cosmos Reason 2-8B replaces Metropolis VSS for the Phase-1 camera-event path.** The narrow "event from camera" job is the only perception beat any demo script needs; the 8-GPU VSS footprint doesn't justify itself here. See ADR-027.
- **Unitree G1 is the primary humanoid embodiment in sim** because it's commercially purchasable, has good sim assets, and is popular enough that references resonate across customers. The architecture is embodiment-pluggable; the Unitree choice is for the primary scripted demo.
- **GR00T is served, Pi-0/OpenVLA are supported via config.** The serving layer takes a model profile (checkpoint, tokenizer config, action-space spec) as a CR; swapping is a YAML change. This is "bring your own model" made operational.

## Diagrams

Mermaid and SVG source files live in `docs/diagrams/`. The canonical set of diagrams we maintain:

- `01-layers.svg` — the seven-layer stack.
- `02-topology.svg` — hub, spokes, edge.
- `03-loops.svg` — the four core loops.
- `04-security-surfaces.svg` — trust boundaries, mTLS scope, signing checkpoints.
- `05-gpu-allocation.svg` — how the 2–3 L40S are allocated across demo and training modes.
- `06-mega-mapping.svg` — NVIDIA Mega component diagram on top of Red Hat substrate.

Diagram `06-mega-mapping.svg` is the single most important visual asset in the entire project. It is the image on every one-pager, every deck, every GitHub social preview.
