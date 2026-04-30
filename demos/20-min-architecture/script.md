# 20-min Architecture Walkthrough demo script

**Audience**: Archetype B — "We're evaluating or piloting physical AI."
**Length**: 20 minutes. Four roughly-5-minute segments.
**Venue**: the Showcase Console, evaluator mode. Navigates between Stage, Architecture, Lineage, and Fleet views.

**Revision note (post-persona-review)**: this script was revised after the Phase-1 persona-review pass (see `demos/review-synthesis.md`). Three substantive changes vs. the original:
- Segment 4's brownfield beat (PLC-gateway VM + MES-stub + Purdue overlay) was promoted from a 30-second mention to a full beat at the explicit request of both the auto-OEM (Linda) and the internal-field-SA (Priya) personas.
- The rollback beat's timing claim is now explicitly a *measured number from the performance-envelope doc*, not a round-number aspirational claim. The script carries a placeholder that gets replaced with the real p50 once Phase 2 measures it.
- Multi-site fan-out credibility is split: the demo shows hub + companion + one spoke live; the 40-site operating math lives in a sidecar doc (`docs/sales-enablement/fleet-scale-operating-math.md`) referenced during the demo, not faked-out live.

## What this demo substantiates

Primary differentiators (core beats):
- **#3 Hybrid cloud → factory edge → robot** — now with multi-site (spoke clusters), not just hub + companion.
- **#4 OpenShift AI as MLOps backbone** — the retraining and promotion flow, shown live.
- **#8 Day-2 lifecycle done right** — policy promotion + rollback without stopping the fleet.

Secondary (one-line surface):
- **#2 One platform for containers + VMs + vGPU** — the legacy-controller VM visible on companion.
- **#1 On-prem / air-gap** — referenced at the open and the close.

Off-surface:
- **#5 Security** — engineer-only concern; 60-min demo.
- **#6 Open model choice** — named once in passing; 60-min demo.
- **#7 Agentic orchestration** — explicitly deferred to 60-min.

## The customer concern we lead with

**Not**: "Red Hat's architecture for physical AI."
**Yes**: "When you deploy physical AI across N factories, three questions dominate operations: how do you keep policies current across the fleet, how do you know a policy is safe before promoting it, and how do you roll back in minutes when something regresses? The rest of this conversation is how Red Hat answers those three."

## Components exercised (superset of the 5-min)

Everything in the 5-min script, plus:
- **MLflow** (RHOAI-managed) — model registry + experiment tracking UI.
- **Isaac Lab training pipeline** — Kubeflow Pipeline running a policy-retrain job end-to-end.
- **Cosmos Transfer 2.5 (limited)** — one variation pass on existing sim frames to demonstrate synthetic-data-assisted training. Full Cosmos Predict/Transfer pipeline stays 60-min territory.
- **ACM** — multi-site rollout to a second spoke cluster.
- **Argo CD** — GitOps promotion visible.
- **OpenShift Virtualization on companion** — a Windows or legacy-Linux VM representing a factory-floor PLC gateway, visible in a side panel.
- **Showcase Console** — adds Architecture view, Lineage view, Fleet view. Novice-mode Stage view still available as the "return home" target between segments.

## Four segments, roughly 5 minutes each

### Segment 1 (0:00 – 5:00) — "The operating picture" (recap + deepen)

Opens with the 5-min warehouse baseline loop running, but with two additions:
1. The Fleet view panel opens showing TWO factory sites (Factory A on the companion we already have; Factory B on a second spoke cluster). Mission flow is to Factory A; Factory B is showing idle-but-healthy telemetry.
2. Bottom of the Console shows a timeline of "policy versions deployed" across the fleet — today all factories run `vla-warehouse-v1.3`.

**Narration template**:
> "You saw the 5-minute loop — camera event, fleet decision, robot action. Same loop is running across every factory site in your fleet, coordinated from the datacenter hub. Here's Factory A on the left, Factory B on the right. Same robot policy, same fleet manager, same mission flow. Different physical sites. Now let me show you the three questions that dominate operating this."

### Segment 2 (5:00 – 10:00) — "Training a new policy with lineage"

Transitions to Architecture view briefly to show the MLOps sub-architecture, then to Lineage view.

**Narration**:
> "An engineer has a new warehouse scenario — suppose we've observed the AMRs hesitating at a specific turn in dense traffic. They want to train an improved policy. Here's the pipeline." *[Lineage view activates]* "This is the Kubeflow pipeline launching an Isaac Lab training run. It picks up a scenario manifest — including any synthetic variations from Cosmos Transfer — runs training, evaluates against a scripted scenario suite, and lands the checkpoint in MLflow." *[Console shows: scenario manifest → pipeline job → training progress → evaluation results → model registry entry]* "Every piece of this is traceable. The new policy version `vla-warehouse-v1.4` knows exactly which training data produced it, which scenarios validated it, and who approved it for promotion."

**Console view**: Lineage view. Shows a directed graph: scenario manifest → Isaac Lab training job (running) → MLflow experiment with metrics → model registry entry → pending-promotion state. A side panel shows the Cosmos Transfer variations used.

*[differentiator #4 surfaces as the visible lineage graph, plus the live pipeline run]*

### Segment 3 (10:00 – 15:00) — "Promotion, rollout, rollback"

Transitions to Fleet view.

**Narration**:
> "Here's the promotion. The engineer opens a PR — Argo CD picks it up, rolls `v1.4` to Factory A only, watches telemetry for the evaluation window." *[Console shows PR merging; Argo sync visible; Factory A's version pill changes to v1.4 in the fleet view]* "Factory B is still on `v1.3`. Both sites are reporting telemetry. If the new policy held up — promote to Factory B via another PR. If it didn't —" *[Console shows an anomaly-score spike on Factory A; an 'auto-rollback' pill appears; version pill reverts to v1.3]* "— Argo reverts to the last-known-good commit, the fleet goes back to `v1.3` automatically. On this topology, anomaly-to-rollback completes in under 20 seconds — that's a git revert, an Argo sync, and a policy update, measured live. Factory A's robots kept moving through the rollback."

**Measured baseline (2026-04-30, hub cluster, 2 factories)**: anomaly-detected → rolled-back ranges 6–18s across runs. The variance is Argo CD's reconciliation cycle (2s if we land near a poll, 14s if we don't). Git commit is consistent at ~1s. Includes a 3s intentional pause so the audience sees the anomaly state before rollback begins. These are single-cluster, 2-factory numbers — honest baseline, not at-scale projections.

**At-scale note for the narration**: if the evaluator asks "what about 40 sites," the seller points to `docs/sales-enablement/fleet-scale-operating-math.md` — the operating-math sidecar doc covers ACM fan-out characteristics, Kafka partitioning, hub-loss behavior, GitOps blast-radius at real-customer scale. The live demo shows hub + companion + one spoke because that's what the reference cluster provisions; multi-site credibility comes from measured math in the doc, not from a faked-up 40-site live deployment.

**Console view**: Fleet view. Two factory panels side by side. Version pills animate. Anomaly-score sparkline visible on Factory A. Argo sync status shows "syncing → synced → reverting → synced" in sequence. Timeline at bottom shows the full event sequence with timestamps.

*[differentiator #8 surfaces as the visible rollback without downtime]*
*[differentiator #3 reinforced — two factories coordinated from one hub]*

### Segment 4 (15:00 – 20:00) — "Brownfield reality + close"

**Rewritten post-review**: the original Segment 4 surfaced three one-liners (VM alongside containers, air-gap, agentic teaser). The Archetype-A OEM persona called out that the PLC-gateway VM beat was "the single most useful sentence in the repo" for auto/aerospace accounts but got only 30 seconds. The internal Red Hat SA persona confirmed: "don't let this get cut." Segment 4 now gives the brownfield story 3–4 minutes and absorbs air-gap + agentic as brief closers.

**Narration**:

> *[Architecture view; Purdue-model overlay appears with Levels 1–4 annotated, OpenShift deployment shown clearly sitting alongside existing L1/L2, not replacing it]* "Before I close, I want to address the question every industrial customer asks in the first five minutes, that we've deliberately saved for last: *what happens to the stack I already have?* Your factory floor today has PLCs, HMIs, a SCADA system, an MES talking to SAP. You are not going to rip that out. We didn't design around that; we designed *through* it." *[companion-cluster side panel expands, showing a KubeVirt VM running a legacy HMI/PLC-gateway alongside the robot-brain inference pod]*
>
> "That VM running next to the container pod is a representative legacy PLC gateway — Windows, HMI software, the kind of thing every one of your plants has today. It's on the companion cluster. Same operations team, same GitOps, same RBAC, same image signing policy as everything else on that cluster. OpenShift Virtualization lets you run it as a peer to containers, not a second infrastructure you maintain separately. This is how we meet a real factory where it is — containers *and* VMs on one platform."
>
> *[Console switches to MES-stub view; a stream of order messages is visible flowing into Kafka's `mes.orders` topic; Fleet Manager shows it consuming those orders]*
>
> "Second piece of the brownfield story: your existing MES doesn't go away either. In this reference, an MES-stub is emitting SAP-PP/DS-shaped order messages; Fleet Manager is consuming them as mission input alongside the camera events you saw earlier. The AI decisioning runs *downstream* of your production planning, not in place of it. If you're running SAP, Oracle, Infor, Siemens Opcenter — the integration is Kafka topics and a translation layer, not a replacement."
>
> *[Architecture view returns with Purdue overlay; cross-level data flows highlighted]*
>
> "And just to be explicit on the Purdue layering because this always comes up: OpenShift sits at your Level 3 site-operations layer and above. The PLC network at Level 1 and the HMI/SCADA segment at Level 2 remain where they are, with the boundary enforced by NetworkPolicy and whatever DMZ architecture you already operate. We're not asking you to redraw your OT network."
>
> *[transition to brief closers; Console switches to a small panel showing mirror-registry topology, then returns to Architecture view]*
>
> "Two brief things before I close. This whole environment runs fully on-prem, with a supported air-gap deployment path. Image registry, model artifacts, every dependency mirrored inside your walls via `oc-mirror`. IP never leaves the facility. And there's an agentic layer we haven't touched today — natural-language operator interface, fleet interventions gated on human approval. That's a separate 60-minute conversation, not something I want to rush here."
>
> *[closing]* "What you saw today: a policy trained on your hub, promoted across a multi-site fleet, rolled back cleanly when it regressed, running alongside the legacy stack you already operate. All on substrate you control. If you want the engineer-depth version, we have a deep-dive. If you want to fork the repo and have your team start there, the whole thing is public."

**Console views**: Architecture view with Purdue overlay as the primary frame for this segment. Side panels toggle between KubeVirt VM inspection, MES-stub order flow, mirror-registry topology. Returns to Stage view as the closer.

*[differentiator #2 now a real beat, not a one-liner; #1 one-line surface; #7 explicit deferral to 60-min]*

*[Addresses review Gap 3 (Linda OEM VP: "no bridge from my current stack to this one"; Priya SA: "don't let this get cut")]*

## Beat → differentiator map

```
00:00 — context (no differentiator surfaced — setting the customer concern)
00:30 — #3 (multi-site in operating picture)
05:30 — #4 (MLOps lineage — the core beat)
07:30 — #4 (Isaac Lab training pipeline live)
08:30 — #4 (MLflow model registry + lineage)
10:30 — #8 (GitOps-driven promotion)
12:00 — #8 + #3 (multi-site ordering)
13:30 — #8 (auto-rollback on anomaly)
15:00 — #2 (VM alongside containers) — one-line surface
16:00 — #1 (on-prem + air-gap) — one-line surface
17:00 — #7 (agentic teaser) — one-line surface
19:30 — close
```

## Hard constraints

- **The rollback moment must be real, not animated**. The visual of the fleet version pill reverting has to come from an actual Argo sync that actually reverted a commit. Pre-scripted on the hub, but reproducible.
- **The rollback timing claim must be a measured number from the performance-envelope doc**, not a round-number aspiration. If the measured p50 is 137 seconds, the narration says 137 seconds. Persona-review feedback explicit: "don't quote a number to me you haven't measured."
- **No agent panel interaction**. Teaser only. Open that door and we're 20 minutes over.
- **MLflow UI surfaces in a carefully-controlled way**. Show the run and its metrics + lineage graph. Don't open a full MLflow UI for the customer to browse — that's engineer detail.
- **Factory A and Factory B are visually distinct** — different names, maybe different subtle branding, so the viewer believes they're separate sites. Console design decision.
- **No security content**. Not FIPS, not STIG, not Sigstore. If the evaluator specifically asks, redirect: "there's a dedicated engineer-depth walkthrough on security posture — we'd want the 60-minute version for that."
- **Scene-configurable if Phase 2 research yields a second SimReady scene**. If discrete-assembly or process/packaging is available, the 20-min's scene loads from ConfigMap and the seller can pick a scene matching the customer's vertical before running the demo. If not, the script commits to warehouse and the seller opens with a narration acknowledging the vertical mismatch for non-logistics customers ("we're showing you warehouse because that's the scene publicly available — the platform story maps identically to your assembly/process line").
- **Brownfield beat (Segment 4) is non-negotiable once the PLC VM + MES-stub are built**. It's the single most-field-valuable beat in this demo per internal-SA persona review. If a segment has to get cut for time, cut something else.
- **Multi-site credibility lives in two places**: live (hub + companion + one spoke, three clusters visibly reconciling) and doc (`docs/sales-enablement/fleet-scale-operating-math.md` for 10/40-site operating math). Don't try to fake more clusters live.

## What this demo's existence gates (Phase 2 scope)

In addition to everything Phase 1 built for the 5-min, Phase 2 must deliver:

1. **RHOAI MLflow fully operational** with experiment tracking + model registry (already in Phase 0/1 foundation; Phase 2 wires UI into Console).
2. **Isaac Lab training pipeline** as Kubeflow Pipeline: scenario manifest → train → evaluate → register.
3. **Cosmos Transfer 2.5 limited deployment** — produce scene variations for one named scenario, feed into training. Not the full synthetic-data-factory pipeline (that's 60-min / Phase 3).
4. **Second spoke cluster (Factory B)** provisioned via ACM. Same GitOps patterns as companion (spoke-a / spoke-b scaffolding already in `infrastructure/gitops/clusters/`).
5. **Cross-spoke Kafka MirrorMaker** or equivalent for mission flow to multiple factories.
6. **ACM RBAC-based policy rollout** — the PR-merge-to-Argo-sync-to-spoke path, including the anomaly-triggered rollback.
7. **KubeVirt VM on companion** representing the legacy PLC gateway. One VM, boots clean, exposed only to internal factory network via NetworkPolicy.
8. **Showcase Console grows**: Stage view gets a second-factory panel; Architecture view; Lineage view; Fleet view with per-site version pills and anomaly sparklines.

**Not required for 20-min and therefore not Phase 2 critical path**:
- Cosmos Predict 2.5 (world-model for safety layer — Phase 3).
- Full agentic stack (Phase 3).
- Llama Stack HIL (Phase 3).
- Any MCP servers (Phase 3).
- STIG scan surfacing in Console (Phase 3 / 60-min only).
- Physical-robot integration (Phase 4).

## Open items to resolve before recording

- Which scenario specifically drives the retraining beat ("AMRs hesitating at a specific turn in dense traffic" is placeholder — pick something visualizable).
- How to visibly represent Cosmos Transfer's contribution without diverting into a Phase-3 beat. Suggestion: show one side-by-side "original render vs. transferred variation" stills in the Lineage view, don't run Cosmos live.
- Timing on the rollback moment — the 90-second claim is ambitious. Measure actual Argo+Kafka propagation time on the multi-site topology once provisioned. Script adjusts to reality.
- Factory naming. "Factory A / Factory B" is placeholder; seller-usable names (maybe reflecting a specific customer-evocative industry, e.g. "Amberg-West / Amberg-East" for Siemens-adjacent conversations, or plain "Site-01 / Site-02" for generic).
- Whether the PLC-gateway VM content is visible (a Windows login screen? a SCADA-like HMI running?) or just named. Depends on what Phase 2 actually builds for the VM workload.
