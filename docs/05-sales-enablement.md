# 05 — Sales Enablement

The sales-enablement layer is not a downstream deliverable — it is co-equal with the reference implementation. This document specifies the Showcase Console in detail, the tiered demo architecture, the audience matrix, and the supporting collateral.

## The central deliverable: the Showcase Console

The Showcase Console is the single tool Red Hat field teams use in customer engagements. It is a web application that runs on OpenShift, accessed by sellers from a browser in the meeting room (or on a call). It serves as demo driver, architecture reference, talk-track prompter, and handoff package generator — all with audience-aware presentation.

### Design principles

1. **One tool, many conversations.** A seller should not juggle a deck, a demo environment, a whiteboard, and a laptop terminal. The Console is the one thing they look at.
2. **Audience-aware depth.** Every feature declares which audience archetype(s) it applies to. The Console reveals or suppresses features based on the current audience mode.
3. **Scripted beats, improvised framing.** Demos run through scripted storyboards, but the seller's narration adapts to the room. The Console shows the seller the next beat and the matching talking points, not a locked teleprompter.
4. **Depth on demand.** Any claim on the screen can be clicked to reveal the underlying architecture, the underlying data, or the underlying code. Nothing is purely visual — everything is verifiable.
5. **Honest about limits.** Time budgets are visible. If the seller has 10 minutes left and clicks into a 20-minute path, the Console says so.
6. **Offline-capable fallback.** If the demo cluster is unavailable, the Console replays pre-recorded captures seamlessly, with visible-but-polite indicators that it's a recording.
7. **Customer hand-off.** After a session, the Console can export a customer-specific package (slide deck PDF, architecture diagrams customized with their logos in a respectful way, and a pointer to a lab environment they can keep exploring).

### Core concepts in the Console

- **Scenarios**: the top-level units (e.g., "Warehouse — Baseline"). Each scenario encapsulates a USD scene, a fleet configuration, a policy set, and a sequence of beats.
- **Beats**: the atomic "do X" steps inside a scenario. A beat might be "introduce bottleneck in Zone B" or "show the VSS summary for camera 3." Each beat has expected duration, audience applicability, and matching talking points.
- **Audience modes**: `novice` (Archetype A), `evaluator` (Archetype B), `expert` (Archetype C). Mode is switchable at any time; the Console re-renders accordingly.
- **Time budget**: a countdown the seller sets at the start (e.g., "I have 15 minutes"). The Console suggests which scenarios and beat sequences fit.
- **Depth drawers**: any UI element with more underlying detail has a "show me the architecture / data / code" drawer. Drawer content is audience-filtered.
- **Differentiator overlay**: an ambient side panel that contextualizes the current screen with the relevant Red Hat differentiator (the eight from the charter). Expert mode surfaces these more prominently; novice mode surfaces them more softly.
- **Agent prompt**: a natural-language input box wired to the LangGraph agentic orchestrator (Phase 3+). Sellers can literally ask the system questions during a demo — but the Console also warns about time cost.
- **Handoff drawer**: at any point the seller can say "capture this for the customer" and the Console stages a package.

### Console views

Five primary views that a seller navigates:

1. **Stage view** — the live demo surface. A Kit App Streaming embedded viewport dominates; analytics overlays and VSS summaries layer in. Bottom bar shows the current scenario and beat, with a Next button.
2. **Architecture view** — the Mega-on-OpenShift diagram, clickable. Any component zooms in to a detail pane with talking points and depth drawers.
3. **Lineage view** — for expert-mode conversations about MLOps. Shows model lineage, sim provenance, and MLflow links.
4. **Fleet view** — multi-site fleet overview across spokes, with real-time status.
5. **Agent view** — the natural-language prompt box + agent plan visualization + live results. Phase 3+.

A persistent top bar everywhere shows: current audience mode, time budget remaining, current scenario, seller notes (visible only to the seller).

### Technical shape

- **Frontend**: React 18 + TypeScript, Vite build. PatternFly as the component library for Red Hat visual consistency. State in Zustand. WebRTC for the Kit App Streaming embed; WebSocket for live fleet state.
- **Backend**: Fastify (Node.js/TypeScript) as the BFF. Directly reaches Kubernetes (via kubeconfig), Kafka (live state), MLflow (lineage), Grafana (dashboard embeds), and the LangGraph orchestrator (agent prompts).
- **Auth**: OpenID Connect via Red Hat SSO (Keycloak). Every seller has a named identity; actions are audited.
- **Deployment**: native OpenShift app — Deployment + Service + Route. Packaged as a Helm chart in `console/chart/`.
- **Offline mode**: backend detects cluster unavailability and switches to replay mode, streaming from a local asset bundle of pre-recorded captures.
- **Customization**: customer-specific branding overlays supported via a config CR; sellers can pre-configure before a meeting.

### Deliberately *not* in the Console

- No pricing / licensing calculators. Those live with the account team's normal tools.
- No customer-facing onboarding flows. The Console is for the Red Hat-led meeting, not as a self-service portal.
- No direct cluster-admin operations. Sellers can see and trigger scripted scenarios; they cannot (via the Console) deploy arbitrary workloads.

---

## The scripted demo library

Three primary demo durations, each with multiple scenario variations. The seller selects based on audience and available time.

### 5-minute visual loop

**Audience**: Archetype A (novice) — foyer meetings, trade-show booth walk-ups, introducing the topic in a broader conversation.

**Scripted path**:
- Open Stage view with "Warehouse — Baseline" pre-loaded.
- Beat 1 (0:00–0:45): "This is a warehouse digital twin. These robots and this humanoid are running against real physics and real sensor simulation." Pan around the scene using Kit App Streaming.
- Beat 2 (0:45–2:00): "Watch them operate against a mission stream." Trigger a scripted mission sequence. Show VSS analytics summarizing activity.
- Beat 3 (2:00–3:30): "Same code, same signed container, deploys to the actual robot at the factory edge." Switch to edge view showing a simulated Jetson receiving the policy.
- Beat 4 (3:30–5:00): "All of this runs on Red Hat's hybrid cloud — on-prem, air-gapped, or cloud. The NVIDIA stack is the engine; Red Hat is the operational substrate." Show architecture view with Mega components highlighted over the OpenShift substrate diagram.
- Close with: "If any of this is on your roadmap, let's schedule a deeper conversation."

Works live against a running cluster or as a replay.

### 20-minute architecture walkthrough

**Audience**: Archetype B (evaluator) — scheduled customer meetings with an evaluating technical audience.

**Scripted path** (outline; full script in `demos/20-min-architecture/script.md`):
- 0:00–2:00: 5-minute loop, compressed.
- 2:00–5:00: Architecture view. Walk through Mega components and their Red Hat implementations. Highlight the eight differentiators as they naturally appear in the diagram.
- 5:00–9:00: MLOps narrative. Lineage view. Show a policy traced from training run → MLflow registration → sim validation → GitOps merge → hub deploy → spoke deploy → edge deploy.
- 9:00–13:00: Multi-site fleet view. Demonstrate a policy rollback propagating across two spokes.
- 13:00–17:00: Security posture deep drawer. Supply-chain attestations, signed images, STIG profile, air-gapped reference path.
- 17:00–20:00: Q&A + handoff. Offer to expose the public reference repo to their team; offer an SA follow-up for a PoC scoping conversation.

### 60-to-90-minute technical deep dive

**Audience**: Archetype C (expert) — scheduled technical sessions with experienced engineers at prospective customers.

**Scripted path** (outline; full script in `demos/60-min-deep-dive/script.md`):
- 0:00–5:00: Brief scenario baseline; skip the visual loop if the audience is already oriented.
- 5:00–15:00: MLOps loop demonstrated live — launch a training pipeline, show it streaming metrics into MLflow, show the registration and promotion through to a hub serving deployment.
- 15:00–25:00: Multi-site live demonstration — propagate a policy update to Spoke A, observe metrics shift, propagate to Spoke B.
- 25:00–40:00: Rollback + chaos. Induce a fault (broker loss, GPU failure, camera outage). Show observability, autoscaling, and GitOps-driven recovery.
- 40:00–55:00: Agent view — pose a what-if question, watch the agent compose and execute a sim experiment, review its summary.
- 55:00–75:00: Open exploration — offer the customer's engineers a terminal into a lab environment with the reference already deployed, let them poke around with the seller facilitating.
- 75:00–90:00: Architectural Q&A; deep drawer tour of whatever they want; handoff and next-steps conversation.

---

## Audience matrix

What the Console exposes or suppresses based on `audience` mode.

| Feature / View | Novice | Evaluator | Expert |
|---|---|---|---|
| Stage view (main scene) | ✓ full | ✓ full | ✓ full + debug overlays available |
| VSS summaries | ✓ simplified phrasing | ✓ | ✓ with raw event JSON accessible |
| Architecture view | Available, not surfaced proactively | ✓ surfaced at natural moments | ✓ always in peripheral awareness |
| Lineage view | ✗ | Available on request | ✓ surfaced when relevant |
| Fleet view | Simplified ("2 sites, healthy") | ✓ with metrics | ✓ full with raw Thanos queries accessible |
| Agent view | Phase 3+; simplified queries shown with clear prompts | ✓ | ✓ with agent plan inspection |
| Red Hat differentiator overlay | Soft, in-aside | Contextual callouts | Prominently positioned |
| Code / manifest drawers | ✗ | ✓ for architecture components | ✓ everywhere |
| MLflow, Grafana, Argo CD links | ✗ | ✓ on architecture clicks | ✓ first-class |
| Handoff package | Simple scenario doc + diagrams | + Reference repo pointer + lab credentials | + Full fork-ready handoff with their team added to the private lab |

Mode switching mid-demo is expected and smooth — the seller can flip from novice to evaluator when a customer's CTO unexpectedly joins the call.

---

## Supporting collateral

Beyond the Console itself, these artifacts support the field:

### 1. Architecture one-pager
- Primary visual: Mega-on-OpenShift mapping diagram.
- Eight differentiators listed with one-line explanations.
- QR code to the public reference repo.
- Versioned; fits on a single A4 / US Letter double-sided.

### 2. Architecture deep-dive white paper
- 15–25 page technical document covering everything `docs/01-architecture-overview.md` does, written for an external audience.
- Positioned as "Red Hat's reference for NVIDIA Mega."
- Published on redhat.com/resources or equivalent.

### 3. Customer narratives (as they accumulate)
- Short written case studies for each customer engagement that generates permission to publish.
- Templated: context, what they deployed, what they measured, what they learned.

### 4. SI enablement curriculum
- Two-day workshop for Accenture/IBM Consulting/Deloitte engineers.
- Lab-based; uses the reference as the instructional scaffold.
- Certification track (internal Red Hat, not customer-facing).

### 5. Objection handling cards
- Short (one-screen) responses to the top objections we expect. Examples:
  - "Why not just run this on DGX Cloud?" — answer focused on on-prem/air-gapped/sovereignty.
  - "We already use VMware vSphere." — answer focused on OpenShift Virtualization and the unified container+VM story.
  - "We don't have a multi-site problem." — answer focused on how single-site customers still get operational consistency, security posture, and optionality.
  - "We only want the training piece." — answer focused on OpenShift AI + MLflow standalone value and the straightforward expansion path later.

### 6. Competitive positioning
- vs DGX Cloud: agility in your environment.
- vs pure cloud hyperscalers: on-prem/air-gapped + enterprise operational model.
- vs build-your-own Kubernetes: Red Hat has validated, supported, signed this full stack; you don't have to integrate it.

### 7. Discovery question sets (per audience)

**For Archetype A**: "What's driving your interest in industrial AI right now? What's on your factory floor today — AMRs, robotic arms, vision systems? What's your hybrid-cloud strategy?"

**For Archetype B**: "Which parts of the NVIDIA stack are you piloting or considering? Where does the simulation-to-deployment handoff break down today? What's your current approach to policy lifecycle and safe rollout?"

**For Archetype C**: "Tell me about your current operational model for AI models in production. How are you doing multi-site consistency today? Where are the rough edges in your current physical-AI runtime? What's your posture on sovereign compute for these workloads?"

---

## Seller training path

A seller becomes ready to present this material through a three-stage program:

1. **Orientation (half-day)**: watch the recorded demos, read the architecture one-pager, read the audience matrix. Outcome: can intelligently refer to the Console in a conversation.
2. **Shadowing (two sessions)**: sit in on two customer sessions led by a more experienced presenter. Outcome: sees the nuances of audience-mode switching and time-budget discipline.
3. **Co-piloting (two sessions)**: co-lead two customer sessions with a veteran presenter. Outcome: ready to lead.

At each stage, a checklist in `docs/sales-enablement/training-checklist.md` (to be produced) records readiness.

---

## Metrics the sales team cares about

The Console emits telemetry (with seller consent and customer anonymity) on:

- Meeting duration vs scenario length selected
- Audience-mode transitions per meeting
- Most-invoked depth drawers (signals what customers are curious about)
- Most-run agent queries (signals the gaps customers perceive)
- Post-meeting handoff-package exports per session

This feeds back into:
- Content prioritization for future phases
- Training updates (sellers find certain depth drawers hard to explain? Add to training)
- Signal for product management

---

## The "Forge" branding option

Working name for the Console is "Showcase Console." A potentially more evocative alternative is **"Forge"** — it evokes industrial making and aligns with Red Hat's open-source tradition (Sourceforge heritage). Final naming decision is deferred to the marketing team; the working name should remain placeholder-neutral ("Showcase Console") in repo code until decided.

If Forge is adopted: `console/` renames to `forge/`, and brand assets need production. No code-level implications.
