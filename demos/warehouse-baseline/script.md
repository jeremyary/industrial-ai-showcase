# 5-min Warehouse Baseline demo script

**Audience**: Archetype A — "What is industrial physical AI?"
**Length**: 5 minutes. Hard cap — this is the session that has to fit in a hallway conversation or the first 5 minutes of a longer meeting.
**Venue**: the Showcase Console, novice mode. Single demo path, scripted, no improvised navigation.

## What this demo substantiates

A lean subset of the charter differentiators, hit contextually rather than announced:

- **#3 Hybrid cloud → factory edge → robot, one operational model** — core visual: hub and companion cluster running together, a mission crossing between them.
- **#1 On-prem and air-gapped first-class** — mentioned once, early, as a positioning line.
- **#8 Day-2 lifecycle done right** — mentioned once as closing line.

Everything else is off-surface for this demo. No security, no MLOps, no agentic. Those are 20-min and 60-min territory.

## The customer concern we lead with

**Not**: "look at this Red Hat stack."
**Yes**: "this is a warehouse with physical AI running. Let me show you what that means, and where Red Hat fits."

## Scene + robots + components

Per `assets/README.md`:
- Scene: NVIDIA SimReady Warehouse Pack (warehouse interior with racks, aisles, loading zones).
- Primary robot: Nova Carter AMR (pallet pickup / aisle navigation).
- Secondary robot: Unitree G1 humanoid (visible in scene but not active in the 5-min script).
- Simulated cameras mounted on ceilings at key vantage points.

Components exercised (and only these):
- Nucleus (serving the warehouse USD scene).
- Isaac Sim (headless runner, streaming Kit App Streaming viewport into the Console).
- Kit App Streaming (web viewport in the Console).
- Cosmos Reason 2 + custom RTSP→Kafka adapter (video events from simulated cameras). Replaces VSS per `docs/04-phased-plan.md` edit (task #20).
- Kafka topic `fleet.events` (camera output).
- Fleet Manager (consumes events, emits missions).
- Kafka topic `fleet.missions`.
- Mission Dispatcher on companion cluster (receives missions, routes to local VLA).
- Open VLA + scene reasoning on companion (emits robot action).
- Kafka topic `fleet.telemetry` (robot reports back).
- Showcase Console (shows all of the above as one coherent picture).

## Minute-by-minute script

### Minute 0:00 – 0:45 — Opening line and scene establishment

**Narration** (seller speaks; the exact words are a template, not a teleprompter):

> "What you're looking at is a warehouse. A mobile robot is moving pallets, a humanoid is standing by for tasks that need dexterity, and ceiling cameras are watching the aisles. Every piece you see — the simulation, the AI that interprets the cameras, the decisioning, the commands going back to the robots — is running on Red Hat OpenShift. Not on cloud services somewhere. On this cluster, which could be sitting in that customer's facility." *[differentiator #1 surfaces here, one sentence, no dwelling]*

**Note (post-review)**: the prior version of this narration generalized to "logistics, automotive parts, manufacturing line." Archetype-A persona review (automotive OEM) flagged this as a tell — the visual is warehouse, not an assembly line, and hedging loses credibility. Commit to warehouse here; cross-vertical credibility comes from the Phase-2 scene-pack decision (second scene) and the 20-min brownfield beat, not from overgeneralized narration on a warehouse visual.

**Console view**: Stage view. The Kit App Streaming viewport dominates the screen, showing the warehouse interior from an overhead camera angle. Nova Carter AMR visible in an aisle. Unitree G1 visible at a workstation. Lower bar shows two cluster-health dots labeled "Hub — factory operations" and "Companion — robot edge."

### Minute 0:45 – 1:45 — The event loop happens, narrated

**Narration**:

> "Watch camera 2. A pallet has just shifted into an aisle where an AMR — that's the mobile robot — is scheduled to pass. In a traditional setup, that's a safety incident. Here —" *[pause, wait for the event]* "— the camera feed is being interpreted by an edge AI model that understands scenes. It just emitted an event: 'aisle 3, obstruction.' That event flowed into the fleet manager, which made a decision: re-route the AMR. The new mission was dispatched, and the AMR is taking an alternate path now."

**Console view**: Stage view remains. Overlay appears on camera 2 showing "Event: aisle-3-obstruction — confidence 0.91." Arrow animation shows the event flowing to "Fleet Manager" panel, which emits a "Mission: reroute-AMR-07" pill that flows to the "Companion cluster" panel. AMR visibly changes path in the viewport.

*[differentiator #3 surfaces as the visual itself — the mission crossing cluster boundaries is the demo]*

### Minute 1:45 – 2:45 — The robot executes, we see the hybrid topology

**Narration**:

> "Here's the part Red Hat makes possible. The mission came from a cluster that represents your factory's datacenter — Fleet Manager, training pipelines, the coordination layer. The decision to act went to a second cluster — the one that represents the factory-floor edge, closer to the robot itself. That's where the robot-brain model runs, where local inference happens, where the robot actually gets its command. Same Kubernetes, same images, same tooling, same operations team — but two clusters, because real factories have datacenter and edge. You can't do this on a cloud service; the edge piece is physically at the factory."

**Console view**: Stage view transitions briefly to Architecture view (a simple two-cluster topology diagram with a link between them). Mission pill animation flows from Hub → Companion along the link, then a telemetry pill animates Companion → Hub as the AMR reports progress. Transition back to Stage view.

### Minute 2:45 – 3:45 — Telemetry + observability as the closing concrete

**Narration**:

> "The AMR just finished the re-routed mission. That telemetry came back to the hub — here it is in the right panel. Every camera event, every fleet decision, every robot action carries a correlation ID. If the AMR does something unexpected tomorrow, an engineer pulls that trace — which policy version, which event, which decision, which command. That's the kind of auditability OT environments need."

**Console view**: Stage view. A mini-panel on the right shows a trace with an actual correlation ID (e.g., `trace-id: 4f3a…c917`): event → decision → mission → robot action → completion. Timestamps visible. One specific telemetry entry highlighted. Phase 1 ships real OpenTelemetry trace IDs — not mock — so this beat survives scrutiny.

**Note (post-review)**: Archetype-B persona review flagged the original "trace back through every step" line as a promise the visual didn't substantiate. Fix: show a real correlation ID on-screen, matching what the OTel pipeline actually produces.

### Minute 3:45 – 4:30 — The "what else is possible" teaser

**Narration**:

> "What you just saw is the operational loop — one robot, one event, one decision, one action. The full picture also includes: retraining the robot's policy when the model gets stale, rolling out a new policy to every factory at once, letting an AI assistant help operators explore what-if scenarios before committing changes. If any of that's worth 20 minutes of a deeper conversation, that's the next step."

**Console view**: Stage view with three pill-teasers appearing at the top of the panel, each labeled — "Retrain & promote", "Multi-site rollout", "Agentic operator". These are not clickable in the novice-mode 5-min script; they foreshadow the 20-min and 60-min demos.

### Minute 4:30 – 5:00 — Close

**Narration**:

> "Everything you saw runs on-prem, air-gap-capable, with the same operational model Red Hat already supports for thousands of production customers. The fleet moves; the line doesn't stop when you update it. That's what we bring to the physical-AI conversation." *[differentiator #8 surfaces in one sentence]*

**Console view**: Stage view holds. Seller closes the Console or transitions to follow-up — "would you like the 20-minute deeper look, or should I leave you with the repo?"

## Beat → differentiator map (grep-able by script author and reviewer)

```
BEAT 00:00 — differentiator #1 (on-prem / air-gap)
BEAT 01:30 — differentiator #3 (hybrid → edge → robot) — core visual
BEAT 02:45 — differentiator #3 (topology diagram)
BEAT 03:30 — differentiator #5 (OT-grade provenance — one-line surface only; not core)
BEAT 04:30 — differentiator #8 (day-2 lifecycle)
```

## Hard constraints

- **No agentic panel open**. Phase-1-skeletal Console; agentic is 60-min territory.
- **No MLflow / model-registry UI**. 20-min territory.
- **No security-checkbox content**. No FIPS, no STIG, no Sigstore. If the customer asks, redirect to 60-min follow-up.
- **No multi-site visible**. Hub + companion is the topology; no spokes. Multi-site is 20-min territory.
- **No scene authoring, no custom assets**. Uses SimReady warehouse + Nova Carter + Unitree G1 only.
- **No live model training or inference-metric dashboards**. The trace panel shows operational events, not model metrics.
- **Kit App Streaming viewport is pre-recorded fallback when live cluster is unavailable** — per charter success criterion that offline fallback must look seamless.

## What this demo's existence gates (scope on Phase 1 implementation)

For the 5-min script to be runnable, Phase 1 must deliver:

1. SimReady warehouse scene loaded into Nucleus.
2. Isaac Sim 6.0 headless runner rendering the warehouse + Nova Carter AMR with simulated cameras.
3. Kit App Streaming Helm chart deployed and embedded in Console.
4. Cosmos Reason 2 + custom RTSP-to-Kafka adapter producing `fleet.events` from simulated camera frames.
5. Kafka (AMQ Streams) with topics: `fleet.events`, `fleet.missions`, `fleet.telemetry`.
6. Fleet Manager v1 (Python + FastAPI, rule-based decisioning).
7. Mission Dispatcher on companion consuming `fleet.missions`.
8. Open VLA serving on companion (KServe + vLLM). Scene reasoning optional for Phase 1 if the VLA handles it directly; otherwise Cosmos Reason 2 also runs here.
9. WMS Stub on hub emitting scripted scenarios (for deterministic demo runs).
10. Showcase Console skeletal — Stage view with Kit viewport embed, event-trace right panel, two-cluster topology dots, three closing teaser pills.

**Not required for the 5-min demo** (and therefore not Phase 1 critical path):
- USD Search API (cut).
- Full VSS 8-GPU pipeline (cut; Cosmos Reason replaces for the narrow "event from camera" job).
- MLflow backend beyond what's needed to serve the VLA (artifact store; no training demo in Phase 1).
- Isaac Lab training pipeline (Phase 2).
- LangGraph + MCP + Llama Stack (Phase 3).
- ACM multi-site spoke provisioning (Phase 2).
- Cosmos Predict / Cosmos Transfer (Phase 3).
- Cluster Compliance Operator / FIPS / STIG demo surfacing (kept in stack, not surfaced in this demo).

## Open items to resolve before recording the demo as an offline-fallback

- Which specific warehouse-floor layout from the SimReady pack. The pack has multiple configurations; pick one.
- Whether the "aisle 3 obstruction" event is triggered by a pre-scripted scenario in the Isaac Sim scene (WMS-Stub driven) or by an actual Cosmos Reason detection from a live camera frame. Pre-scripted is more reliable for a 5-min sales demo; live detection is more impressive for Archetype C. For the 5-min novice version, **use pre-scripted deterministic scenario**.
- Exact copy of the seller's narration — the template above is guidance; Phase 1 item 12 (first scripted demo artifact) refines this with specific wording.
