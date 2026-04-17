# 03 — Data Flows

Four loops animate this system. Each is described here with component participants, event semantics, and the demo beats it supports.

## Loop 1 — Operational inference (factory runtime)

This is the "this is physical AI running right now" loop. It's what Archetype A sees in the first 30 seconds.

### Participants

- Cameras (simulated in Isaac Sim, physical in production)
- Metropolis VSS (visual summaries)
- Kafka topic `fleet.events` (VSS output)
- Fleet Manager (consumes events)
- Kafka topic `fleet.missions` (Fleet Manager output)
- Mission Dispatcher
- Robot Brain (GR00T via vLLM on KServe)
- Robots (Nova Carter AMRs, Unitree G1 humanoid — in sim, on MicroShift edge)
- Kafka topic `fleet.telemetry` (robots report back)
- Showcase Console (observer)

### Flow

```
Camera (USD sensor) 
  ↓ RTSP stream / GStreamer pipeline
Metropolis VSS (NIM)
  ↓ structured summary events
Kafka: fleet.events
  ↓
Fleet Manager — decides intervention
  ↓
Kafka: fleet.missions
  ↓
Mission Dispatcher — routes to specific robot brain instance
  ↓ gRPC
Robot Brain (GR00T via vLLM) — observation in, action out
  ↓
Robot (sim or real) — executes action
  ↓
Kafka: fleet.telemetry
  ↓
Observability (Prometheus, Tempo) + Showcase Console dashboard
```

### Key event schemas

Defined in `workloads/fleet-manager/schemas/` as Avro. Core event types:

- `CameraSummaryEvent`: `{camera_id, timestamp, zone_id, summary_text, detected_entities[], anomaly_score}`
- `Mission`: `{mission_id, target_robot_id, mission_type, parameters, deadline}`
- `TelemetryEvent`: `{robot_id, timestamp, pose, joint_state, battery, current_mission_id, status}`

### Demo beats this supports

- "What physical AI looks like running" (Archetype A)
- "Watch as the system detects a bottleneck and reroutes fleet autonomously" (Archetype A/B)
- "Observability and trace across all layers in one pane" (Archetype C — open the Tempo view, show the full trace)
- "Cross-site event correlation" in multi-site mode (Archetype C — Loop 1 happens on Spoke A while being observed from hub)

### Failure modes the demo intentionally surfaces

- **Camera-to-VSS outage**: show fallback to historical summaries, alerting in Grafana.
- **Robot-brain unavailable**: show KServe autoscaling spinning up a replacement, and fleet manager throttling mission issuance until it's back.
- **Kafka broker lost**: show the 3-broker replication and zero-downtime continuation.

Each is scripted into the Showcase Console as a "introduce fault" button with a clear narrative.

---

## Loop 2 — Policy training and promotion

This is the MLOps backbone loop. It's what Archetype B and C recognize as the "this is actually operationalized" moment.

### Participants

- Kubeflow Pipelines (orchestration)
- Isaac Lab (training)
- Isaac Sim (as training env)
- MLflow (tracking + registry)
- ODF S3 bucket (artifact store, checkpoints)
- KServe + vLLM (serving)
- Argo CD (promotion via GitOps)
- ACM (multi-site rollout)

### Flow

```
Data scientist launches Kubeflow Pipeline
(or: agent-triggered pipeline — Loop 4 integrates here)
  ↓
Pipeline step 1: Launch Isaac Lab training job
  ↓ parallel envs (N * Isaac Sim headless workers)
Isaac Lab: checkpoint every K steps → S3 bucket
  ↓ metrics stream to MLflow Tracking
Pipeline step 2: Evaluation run
  ↓ curated evaluation scenarios (a subset of Mega's Isaac Lab-Arena equivalent)
Pipeline step 3: Register candidate in MLflow Model Registry
  ↓ lineage: scenario manifest versions, sim-sha, parent-model-sha
Pipeline step 4: Validation gate
  ↓ automated (metric thresholds) or human-approval
Pipeline step 5: Produce serving manifest (Kustomize overlay)
  ↓ commit to infrastructure/gitops/apps/robot-brain/ (PR)
Merge → Argo CD syncs to hub serving
  ↓ ACM PolicyGenerator propagates serving manifest to spokes
Edge rollout via ACM ManifestWork to MicroShift targets
```

### Governance embedded

- Every promotion produces an MLflow-recorded artifact pinned to a Git SHA.
- Every edge deployment is traceable to an MLflow model version and the sim episodes that validated it.
- Rollback is a `git revert` — Argo CD reconciles the previous version back.

### Demo beats this supports

- "Here's how we train a robot policy" (Archetype B)
- "Every deployment is traceable to the simulated scenarios that validated it" (Archetype C)
- "Safe rollout across factories: canary to Spoke A, observe, promote to Spoke B" (Archetype C)
- "Rollback: this model started performing worse in production — watch the rollback propagate in under 2 minutes" (Archetype C)

---

## Loop 3 — Synthetic data generation and distribution expansion

This is the "the stack teaches itself" loop. It's the GTC 2026 story made tangible for customers.

### Participants

- Cosmos Predict 2.5 NIM (world model for video generation)
- Cosmos Transfer NIM (domain adaptation)
- Isaac Sim (as scenario runner for Cosmos-seeded worlds)
- MLflow (tracking the dataset lineage)
- S3 buckets (staged scenarios, generated videos, curated datasets)
- LangGraph agent (the coordinator — this loop is usually agent-driven)

### Flow

```
Trigger: scheduled, manual, or agent decision (Loop 4)
  ↓
Agent asks Cosmos Predict to generate N scenarios with prompt seeds
  ↓ generated action-conditioned videos → S3
Agent asks Cosmos Transfer to domain-adapt against real images
  ↓ adapted video/image frames → S3
Agent composes Isaac Sim scenario manifests referencing the adapted content
  ↓ scenario manifests → Nucleus
Agent launches Isaac Lab training runs on the expanded scenario set
  ↓ joins Loop 2 for the remainder
```

### Demo beats this supports

- "The training distribution isn't limited by what we've physically recorded" (Archetype B/C)
- "The agent can explore the edge of the operational envelope autonomously" (Archetype C)
- "Synthetic data is traced to real-world anchors — no ungrounded hallucination" (Archetype C)

### Important boundaries

- Cosmos NIMs are GPU-heavy. In reference footprint, they share GPU with Isaac Sim via scheduling queues — they don't run concurrently with live demo sims. See `docs/08-gpu-resource-planning.md`.
- Generated datasets are explicitly marked as synthetic in MLflow metadata so customers can filter by provenance.

---

## Loop 4 — Agentic orchestration

This is the most contemporary / Red Hat-distinctive loop. It's where LangGraph agents become operators of the physical-AI stack through MCP.

### Participants

- LangGraph agent runtime (on OpenShift AI)
- Agent brain (vLLM-served Nemotron or equivalent)
- MCP servers:
  - `mcp-isaac-sim` (scenario control)
  - `mcp-fleet` (fleet state, overrides)
  - `mcp-mlflow` (experiments, models)
  - `mcp-nucleus` (assets)
- The Showcase Console (issues commands, observes)

### Flow

```
Trigger: user command in Showcase Console or scheduled run
  ↓
LangGraph agent receives high-level goal
  e.g., "Evaluate whether adding 2 more humanoids changes throughput"
  ↓
Agent plans — breaks down into concrete MCP calls
  ↓
mcp-nucleus: stage a scene variant with 2 extra G1s
mcp-isaac-sim: launch N parallel simulation runs
mcp-fleet: observe resulting throughput over the runs
mcp-mlflow: log results
  ↓
Agent summarizes outcome
  ↓
Showcase Console displays — with citations to scenarios, MLflow run IDs, telemetry excerpts
```

### Why this loop matters

Two reasons. First, it's a walkable answer to "what's the agentic AI story for physical operations?" — a question every customer asks in 2026, and one where NVIDIA's answer is mostly aspirational. Second, it closes the storytelling loop for Red Hat: it uses LangGraph (the team's standard), MCP (the emerging tool-access standard), OpenShift AI (the MLOps substrate), and the entire Mega implementation underneath — one coherent narrative.

### Demo beats this supports

- "Ask the system a what-if question and watch it answer" (every archetype, but especially Archetype C)
- "The agent isn't a chatbot — it's running experiments in a real physics sim and summarizing results" (Archetype C)
- "This is what agentic AI looks like when it's grounded in the physical world" (Archetype B)

---

## Cross-loop interactions

Loops are not isolated. The interesting stories happen at the seams:

- **Loop 1 anomaly → Loop 4 investigation**: Fleet Manager detects an anomalous pattern; agent is invoked to investigate by running sim experiments; produces a hypothesis.
- **Loop 3 scenario → Loop 2 training → Loop 1 deployment**: Agent generates edge-case scenarios; they feed into a training run; resulting policy deploys to edge; Loop 1 behavior visibly improves.
- **Loop 2 promotion → Loop 1 observation**: A new policy promoted through Loop 2 is observed in action through Loop 1; metrics visibly change.

These cross-seams are the scripted demo climaxes.

---

## Timing expectations (for scripting)

Each loop has a characteristic time budget. The Showcase Console uses these to avoid over-promising in demo timing:

- **Loop 1 event-to-action**: seconds. Can be shown live in any demo.
- **Loop 2 training → promotion → edge deployment**: minutes for the deploy portion (shown live), hours-to-days for real training (pre-computed for demos; the live demo uses a precomputed training run that "just finished"). Script accordingly.
- **Loop 3 synthetic-data generation**: minutes per small batch, hours for a meaningful dataset expansion. Demo uses pre-staged outputs; the process itself is illustrated in recorded clips.
- **Loop 4 agentic investigation**: variable — a simple query is a minute or two; a serious what-if is 10–30 minutes. Script a "short agent run" for live demos; keep the longer-running investigations as case studies.

Honesty about these time budgets in sales conversations is a feature, not a bug. Customers can smell a faked demo immediately.
