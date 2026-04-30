# Phase 1 Warehouse Baseline — The 5-Minute Operational Loop

Internal Red Hat. Audience: SAs / AEs prepping for a customer conversation about NVIDIA's Mega / Omniverse blueprint on OpenShift.

## The 10-second version

Phase 1 delivers a live 5-minute demo: a warehouse robot receives a mission, navigates to pick a pallet, encounters an obstruction detected by a vision-language model, gets rerouted in real time, completes the mission — all visible in a digital twin and a Showcase Console. Every component runs on OpenShift, federated across a hub and a companion edge cluster.

## What's demonstrable today

- **End-to-end operational loop.** WMS dispatches a mission → Fleet Manager assigns it → Mission Dispatcher on the companion cluster executes it → Waypoint Planner navigates the robot → VLA handles manipulation on pick → telemetry flows back to the hub → Isaac Sim digital twin reflects the real-time state. All visible in the Console's event stream.
- **Vision-language anomaly detection.** Fake-camera on the companion publishes frames to Kafka. Obstruction-detector on the hub sends frames to Cosmos Reason 2-8B (Qwen3-VL derivative on vLLM). Structured safety alerts flow back through Kafka. Fleet Manager replans the active mission around the obstruction. The robot never stops — it reroutes.
- **Isaac Sim digital twin.** Warehouse scene on L40S with the Unitree G1 humanoid, forklifts, pallets, and approach-point markers. Twin-update subscriber consumes telemetry from Kafka and moves prims to match. Route paths are drawn on the warehouse floor during missions. Camera viewport streams to the Console via MJPEG.
- **Cross-cluster federation.** Hub (13-node cluster) + companion (bare-metal SNO). Kafka topics cross the WAN via TLS-passthrough Routes. Missions flow hub→companion, telemetry flows companion→hub. ACM manages the companion as a spoke.
- **Showcase Console.** React/TypeScript with Fastify backend. Stage view with embedded Isaac Sim viewport, real-time event trace panel, topology status dots, two demo buttons (Dispatch Mission, Drop Pallet). Audience-mode toggle scaffolded. Offline-fallback mode plays cached recording when cluster is unavailable.

## Key architecture components

| Component | What it does | Where it runs |
|-----------|-------------|---------------|
| Fleet Manager | Receives events, dispatches missions, replans on safety alerts | Hub (`fleet-ops`) |
| Mission Dispatcher | Executes missions via Waypoint Planner, calls VLA on pick | Companion (`warehouse-edge`) |
| Waypoint Planner | 5 Hz pose emission along route, approach-point pause/clearance | Companion (inside Mission Dispatcher) |
| VLA Serving (OpenVLA) | Manipulation policy for pick actions | Companion host (Fedora, ROCm/HIP, host-native) |
| Isaac Sim | Digital-twin warehouse simulation + viewport MJPEG stream | Hub (L40S, RT cores) |
| Cosmos Reason 2-8B | Vision-language obstruction detection from camera frames | Hub (L40S, vLLM) |
| Obstruction Detector | Routes camera frames to Cosmos Reason, publishes structured alerts | Hub (`fleet-ops`) |
| Fake Camera | Publishes pre-generated warehouse JPEGs to Kafka | Companion (`warehouse-edge`) |
| WMS Stub | Scripted mission generator with demo scenario controls | Hub (`fleet-ops`) |
| Showcase Console | Event stream, viewport, topology, demo buttons | Hub (`fleet-ops`) |
| Kafka (AMQ Streams) | 3-broker, per-topic isolation, cross-cluster TLS Routes | Hub (`fleet-ops`) |

## Differentiator claim status (charter §22)

| # | Claim | Status | Phase-1 proof |
|---|---|---|---|
| 1 | On-prem / air-gapped first-class | Partial | Companion SNO operational on bare metal; `oc-mirror v2` not yet demonstrated. |
| 2 | Containers + VMs + vGPU on one cluster | Partial | KubeVirt live on companion; PLC gateway VM is Phase 2. |
| 3 | Hybrid → edge → robot, one op model | Substantiated | Hub + companion federated. Missions cross the WAN. Same GitOps patterns both sides. |
| 4 | OpenShift AI as MLOps backbone | Substantiated | RHOAI 3.4 EA1 with MLflow + Model Registry operational. Training pipeline is Phase 2. |
| 5 | Security / supply-chain posture | Substantiated | Vault secrets, Kafka TLS, NetworkPolicies, STIG scanning, ClusterImagePolicy on companion. |
| 6 | Open model choice | Demonstrated | OpenVLA on companion (ROCm), Cosmos Reason 2-8B on hub (vLLM). Pluggable alternatives (SmolVLA, π0) pre-provisioned. |
| 7 | Agentic orchestration via MCP | Aspirational | Phase 3 (LangGraph + Llama Stack per ADR-019). |
| 8 | Day-2 lifecycle done right | Substantiated | Full GitOps reconciliation. ACM cross-cluster. Operator-driven upgrades. |

## The 5-minute demo flow

1. **Open Console.** Topology shows hub + companion healthy. Isaac Sim viewport shows the warehouse floor.
2. **Dispatch Mission.** Click the button. Fleet Manager assigns pallet retrieval to the G1 robot. Watch the robot begin navigating in the twin.
3. **Drop Pallet.** Click the button mid-mission. Fake-camera switches to the obstruction frame. Cosmos Reason detects it, safety alert fires, Fleet Manager replans the route around the blocked aisle. Robot reroutes without stopping.
4. **Mission completes.** Robot arrives at the new pick point, VLA handles the pick, telemetry confirms completion. Full trace visible in the Console event panel.
5. **Close.** Three teaser pills on screen: "Retrain & promote," "Multi-site rollout," "Agentic operator" — each a later phase.

## Talk-track hooks by archetype

- **A (novice).** "This is a warehouse robot running a real AI brain, managed by the same OpenShift you'd use for any enterprise workload. The obstruction detection is a vision-language model — not a rules engine. Watch it react in real time." Keep it visual — the Console and twin do the work.
- **B (evaluator).** "Two clusters, one Git repo, one Argo CD. The robot's edge cluster is a single-node OpenShift on bare metal — same as what you'd bolt to a factory floor. Missions cross encrypted Kafka links. This is the topology you'd run at scale." Point at the event trace.
- **C (expert).** "The VLA runs on ROCm on consumer hardware — we're not locked to NVIDIA for edge inference. Cosmos Reason is a Qwen3-VL derivative served via vLLM on L40S. The obstruction-detector publishes structured JSON, not free-text — it's auditable. Ask me about the Kafka listener isolation or the Vault auth chain."

## Caveats (mention before the customer asks)

- VLA serving on the companion runs host-native (podman on Fedora), not inside the OpenShift cluster. The companion's AMD APU lacks first-class GPU Operator support on OpenShift. This is honestly named in the demo narration per ADR-026. Pod-native serving returns in Phase 3 with Jetson Thor.
- Camera frames are pre-generated stills, not live video from a real camera. The obstruction detection is real (Cosmos Reason analyzes each frame), but the source frames are synthetic.
- Isaac Sim viewport streams via MJPEG, not WebRTC. OpenShift HTTPS-only Routes can't carry the UDP data plane without an NLB, which is out of scope. MJPEG is lower latency than it sounds for a demo.
- Cosmos Reason 2-8B is validated by NVIDIA on Hopper/Blackwell; running on L40S is outside the validated matrix but functional.
- The Waypoint Planner uses straight-line segments between topology waypoints, not a full Nav2-class path planner. Sufficient for the demo warehouse; production robotics would use the embodiment's native navigation stack.

## What Phase 2 adds

- Multi-site fleet (Factory A + Factory B) with independent policy versions
- GitOps-driven policy promotion and anomaly-triggered rollback (<20s)
- VLA training pipeline (KFP v2) with RHOAI Model Registry lineage
- MES-to-mission brownfield integration
- Console Fleet view, Lineage view, Architecture view with guided demo stepper

## Deeper reading

- `demos/warehouse-baseline/script.md` — the full 5-minute scripted demo.
- `docs/04-phased-plan.md` Phase 1 section — work breakdown and exit criteria.
- `docs/07-decisions.md` — ADR-025 (Mission Dispatcher on companion), ADR-026 (host-native VLA), ADR-027 (Isaac Sim digital twin).
- `workloads/vla-serving-host/` — host-native VLA runtime documentation.
