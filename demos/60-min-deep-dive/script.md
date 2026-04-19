# 60-min Technical Deep-Dive demo script

**Audience**: Archetype C — "Foxconn/Siemens-tier — already running pieces of the NVIDIA stack."
**Length**: 60 minutes (with a 90-minute-flex option if the engineer wants to go deeper on any one segment).
**Venue**: the Showcase Console, expert mode. Live access to cluster terminals encouraged. Reference repo forked open on a second screen.

**Revision note (post-persona-review)**: this script was revised after the Phase-1 persona-review pass (see `demos/review-synthesis.md`). Substantive changes from the original:
- Segment 1's Cosmos Predict beat now explicitly frames the world-model as a *pre-dispatch admission check* (mission rejected before command ever reaches the robot) rather than "a safety layer" generally. The expert-audience persona (Foxconn-tier) flagged this as one of only two non-table-stakes ideas in the original 60-min — strengthening the framing protects that beat.
- Segment 2's HIL drawer content is now specified, not hand-waved. What the operator sees when approving a state-modifying tool call IS the differentiator; the drawer surfaces diff, blast-radius, MCP tool-call trace, TrustyAI eval, guardrail outcomes, and CAC/PIV-bound approval. The full spec lives in the Phase-2 HIL Drawer Design Spec ADR.
- Segment 3 now names the specific STIG profile (`ocp4-stig-node`), cites FIPS 140-3 validated status per component in the robot command path, and adds a *policy-artifact provenance chain* beat (training → MLflow → signed → admitted). Honesty note: the live cluster runs on OSD; the air-gap walkthrough runs on the companion cluster. The script calls that out explicitly rather than eliding it.
- OSCAL evidence bundle export is a stretch Phase-3 item (if tractable; otherwise Phase 5). The regulated-industry persona flagged this as the single feature that moves defense-sector conversations from "interesting" to "capability-statement."
- Llama Stack governance is on the GitOps / PR-open path only, NEVER inline in serving-time robot command flow. Adding approval latency to 10Hz+ VLA inference is a design invariant, not a preference. This is now an explicit hard constraint.

## What this demo substantiates

Everything. The 60-min is where the full differentiator set earns its demo surface — because only this audience cares about the depth.

Primary (core segment):
- **#7 Agentic orchestration via MCP** — the 60-min has the only live agent interaction. Core beat: operator composes a fleet what-if via natural language, sees the agent's plan, approves/modifies via Llama Stack HIL, observes the result.

Secondary (full-beat each):
- **#5 OT-grade provenance** — tampered-model-rejected-at-admission demo. Air-gap rebuild walkthrough.
- **#6 Open model choice** — live VLA swap mid-session.
- **#4 MLOps with full synthetic-data pipeline** — Cosmos Predict + Cosmos Transfer produce new scenarios; Isaac Lab trains on them; policy registers with full data lineage.

Context-setters (referenced not demoed):
- **#1 #2 #3 #8** are all in by now from prior segments; 60-min reinforces without re-demoing.

## The customer concern we lead with

**Not**: "here's every feature."
**Yes**: "You already run the pieces. You're asking what changes about the operational model, and whether the claims we make about operations, security, and agents actually hold up under inspection. We built this for that conversation."

## Structural approach — 4 segments of 15 minutes each

Unlike the 5-min and 20-min which are single narrative arcs, the 60-min is four loosely-coupled deep-dives that share a common cluster. Seller can re-order or skip based on engineer's interest.

- **Segment 1 (15 min)**: MLOps deep-dive — full synthetic-data factory. Target: the engineer asking "how does your training pipeline actually work?"
- **Segment 2 (15 min)**: Agentic operator — LangGraph + MCP + Llama Stack HIL. Target: the engineer asking "how does LLM safely touch the physical world?"
- **Segment 3 (15 min)**: Security posture — OT-grade provenance + admission + air-gap. Target: the engineer asking "how does this pass our security review?"
- **Segment 4 (15 min)**: Open-model swap + operational depth — live VLA change, observability drill-down, repo + quickstart close. Target: the engineer asking "how flexible is this under my constraints?"

## Components exercised (superset of the 20-min)

Everything in 20-min, plus:
- **Cosmos Predict 2.5** — world-model for action validation / scene prediction.
- **Cosmos Transfer 2.5** — full pipeline, not the 20-min's one-pass teaser.
- **LangGraph agentic orchestrator** — Python service.
- **MCP servers** — `mcp-isaac-sim` and `mcp-fleet` as the demo-earning two. `mcp-mlflow` optional if the segment naturally calls for it. `mcp-nucleus` NOT shipped unless the agent segment grows to demand it.
- **Llama Stack HIL** — approval gate in front of state-changing tool calls.
- **ClusterImagePolicy** — Sigstore enforce showing a tampered artifact rejected.
- **Compliance Operator** scan evidence (referenced, not live-scanned).
- **Air-gap mirror topology** — diagram + actual `oc-mirror v2` artifact paths.
- **Alternative VLA Kustomize overlay** — for the live-swap moment.
- **Trace pipelines (Tempo / OTEL)** — end-to-end trace of a mission showing up in the observability stack.

## Segment 1 (0:00 – 15:00) — Synthetic-data factory + MLOps lineage

**Opening**:
> "You've seen the 20-minute version of MLOps — train a policy, register it, promote it. Here's what sits underneath. When your existing training data isn't sufficient — you need the AMR trained for rare edge cases, or you want the humanoid trained for a scene you haven't physically captured — here's the synthetic-data factory."

**Beats**:

1. **Cosmos Predict 2.5 as a pre-dispatch admission check** (0:00 – 3:00). Show a proposed mission routed through Cosmos Predict *before* Fleet Manager dispatches it to the companion cluster. Cosmos Predict runs the mission as a world-model simulation on the projected scene state; if the predicted rollout violates a safety or latency envelope, the mission is rejected at the Fleet Manager boundary and an alternate is proposed — the robot never receives the command. "This is a world-model acting as an admission check, not a training aid. Most people are using Cosmos Predict post-hoc for evaluation. Here it sits inline between mission planning and dispatch — think of it as 'pre-flight ValidatingAdmissionWebhook for physical actions.' The latency budget for this gate is in the performance-envelope doc; you'd bound it the same way you'd bound any admission hop."

*[Persona-review note: this framing — pre-dispatch admission vs. post-hoc evaluation — was flagged by the expert audience as a genuinely differentiated idea. Don't weaken it in delivery.]*

2. **Cosmos Transfer 2.5 producing scenario variations** (3:00 – 7:00). Take one existing sim scene; generate four variations (night lighting, rainy loading dock, morning fog, busy-with-workers). Each variation becomes a training scenario. Show the generated images side-by-side with the original renders. "This is how you close the sim-to-real gap without capturing real footage in every condition."

3. **Isaac Lab training on the augmented dataset** (7:00 – 11:00). Launch a training run. Real metrics stream in to MLflow. Lineage graph updates live showing: original scene → Cosmos Transfer variations → training dataset → job → checkpoint. "Every piece of this has a provenance trace. When a policy later misbehaves in production, you can walk backward from the robot's action to the specific synthetic frame it trained on."

4. **Model registry with full lineage** (11:00 – 15:00). Open the registry entry. Engineer can click from the registered model → training run metrics → scenario manifest → synthetic-data batch → source sim scene. Data classification, SBOMs per model artifact. "This is what OT-grade provenance looks like for an AI model."

*[differentiators #4 (deep) + #5 (provenance framing woven in)]*

## Segment 2 (15:00 – 30:00) — Agentic operator with HIL

**Opening**:
> "Operators in industrial environments are swamped with dashboards. The ask we hear constantly is 'can I ask the system questions in plain language.' Which is fine for read-only questions. It's terrifying when the question wants to make changes. Here's how Red Hat's stack handles that."

**Beats**:

1. **Ask a read-only question** (15:00 – 18:00). Engineer types: "what's the average mission completion rate in Factory A's Zone 3 over the last 24 hours?" The agent plans its approach, calls `mcp-fleet` and `mcp-mlflow` read tools, returns a summary. No HIL gate triggered — read-only. "Straightforward — the agent is a tool-using LLM and the tools are MCP wrappers."

2. **Ask a what-if question requiring sim** (18:00 – 23:00). Engineer types: "what if we added two more humanoids to Zone B during shift change?" The agent plans: spin up a scenario variant in Isaac Sim, run current policy on it, compare to baseline. Plan appears in the Console. *[HIL gate triggers]* Engineer reviews the plan — what the agent wants to do, what resources it will consume, what it'll measure. Engineer approves. Scenario runs. Results come back. "Compute cost visible, time cost visible, and the engineer approved before anything spun up."

3. **Ask a mutating question — and see the drawer** (23:00 – 28:00). Engineer types: "promote the new policy to Factory B." *[HIL gate triggers immediately; drawer slides in from the right]* This is the beat that matters — what's in the drawer IS the governance. The drawer renders six panes:
   - **Proposed diff**: the Git diff of the overlay commit the agent wants to open a PR with. Side-by-side with what's currently deployed.
   - **Blast radius**: which clusters, which namespaces, which workloads receive this change, how many robots affected, estimated rollout duration.
   - **MCP tool-call trace**: the read-only tool calls the agent made to build context (what it looked at in MLflow, what it queried from `mcp-fleet`), so the operator can see the agent's reasoning path, not just its conclusion.
   - **Guardrail outcomes**: PII scan pass/fail, Llama Stack safety config results, any blocked tool-call attempts along the way.
   - **TrustyAI eval**: score of the proposed policy (v1.4) vs. the incumbent (v1.3) on a held-out scenario suite — the same suite that gated the original policy promotion, now recomputed fresh.
   - **Approval binding**: CAC/PIV identity of the operator clicking Approve, timestamp, bound to an immutable audit record on the Console's signed approval log. In regulated environments this is writeable to WORM storage.

   Engineer reviews. Can edit the proposed diff inline if small, approve-as-is, or reject with a required reason. *[Approves]* Agent opens the PR against `infrastructure/gitops/`. Argo CD picks it up. Factory B rolls to v1.4. "The agent didn't touch the cluster. It composed a change, surfaced what it wanted to do and why, and you — with your identity bound to the audit record — approved the PR. The merge is the commit; the commit is the deployment. The pattern reframes 'LLM touching OT' as 'LLM participating in the review process your team already trusts.'"

   *[Persona-review note: this is THE single most-differentiating beat in the entire 60-min across all personas. Priya and Linda both called out the "agent opens a PR instead of the cluster API" line as the moment that updated their priors on AI safety in OT. Drawer content per the Phase-2 HIL Approval Drawer Design Spec ADR — do not ship the drawer without the six panes; if any pane isn't ready, cut the beat rather than fake it.]*

4. **Show the guardrails and latency boundary** (28:00 – 30:00). Briefly open the Llama Stack safety config. PII detection on inputs. Guardrails on outputs. TrustyAI evaluation signal in the observability stack. "One thing worth saying explicitly because I know it's your next question: Llama Stack governance sits on the GitOps / PR-open path. It is *not* inline in the serving-time command flow to the robot. The 10Hz-and-faster inference path has zero governance-added latency; nothing approval-gated sits between the VLA and the robot action. Governance happens when a *change* is proposed, not on every inference. We treat that separation as a design invariant."

*[differentiator #7 deep; #8 reinforced via GitOps path]*

## Segment 3 (30:00 – 45:00) — Security posture, OT-grade

**Opening**:
> "You've been asking about security since we started. Here's what that looks like concretely. Not 'we sign images' — operational control for OT environments."

**Beats**:

1. **Tampered VLA rejected at admission** (30:00 – 34:00). Engineer simulates an unsigned or signature-broken VLA artifact being pushed to the cluster. Cluster admission denies it at CRI-O with a Sigstore policy violation. Console shows the event + the traceback. "Every VLA, every world model, every policy artifact that commands a physical robot has to trace to a signed training run. The chain can't be broken; if it is, the artifact never runs."

2. **Air-gap rebuild walkthrough (honestly scoped)** (34:00 – 39:00). "One honest call-out up front: the cluster you've been watching this whole demo is our OSD hub — Red Hat-managed, internet-adjacent by design. The air-gap story runs on the companion cluster, not OSD. That's intentional and that's how our customer deployment model works: the hub can be anywhere that suits your connectivity posture; the factory-side cluster is where air-gap actually matters." Show `oc-mirror v2` artifact paths for every image in the stack. Walk through the "no-outbound-network" mode of the companion cluster — physically switch its network off during the demo if the topology allows. Show a rebuild runbook. "This is the environment a regulated-manufacturer or defense customer runs. Nothing outbound. Artifacts mirror in; nothing exits."

3. **Network segmentation for factory floor** (39:00 – 41:00). Open the NetworkPolicy set for the companion cluster. Show: robot-brain inference pod can only be reached by mission dispatcher, only on mTLS, only from a specific service account. Open the Istio mesh diagram. "The 'factory-floor VLAN' is expressed as admission policy. Your Purdue-model Level-1 segmentation remains at L1 — we don't replace it — but the L3/L4 boundary where OpenShift sits is NetworkPolicy-enforced and one L3 hop away from the PLC VLAN."

4. **Policy-artifact provenance chain** (41:00 – 43:00). Open the Console's Lineage panel on a live-served policy. Click-navigate: served InferenceService → signed image digest → SBOM → registered MLflow model → training run → scenario manifest → synthetic-data batch → source sim scene. Every link is a cryptographic chain, not a display-only pointer. "This is the full training-to-deployment attestation chain. When the customer policy commands a robot, you can trace the policy back to the specific synthetic scene it trained on, signed at every hop. The image-signing chain alone is table-stakes; this — the training-data-to-action chain — is the OT-grade piece."

5. **Compliance evidence in Console** (43:00 – 45:00). Navigate to the security panel. Compliance Operator scan results for the companion cluster, running the **`ocp4-stig-node` profile** (specific version cited from `docs/sales-enablement/security-posture.md`) — {N_PASS}/{N_TOTAL} STIG rules PASS, {N_FAIL} FAIL with documented dispositions. For each FAIL, the disposition text is visible: accepted-risk rationale, scheduled-remediation date, or N/A-by-topology explanation. FIPS 140-3 validated status visible per component in the robot command path (RHCOS, OpenSSL, Go crypto; Kafka TLS path; KServe + vLLM; Llama Stack; Fleet Manager outbound). Signed image inventory + SBOMs per artifact. "Auditor hands you a 'show me compliance evidence' request — this is that. The 19 FAILs aren't hidden; each one has a disposition. And for components that can't run FIPS-validated today, we say so explicitly rather than claiming 'FIPS on.' That's the difference between passing an audit and filing an SSP false statement."

   **Stretch (Phase 3 if tractable, else Phase 5)**: click Export Bundle. Console emits a signed, OSCAL-formatted evidence package — SSP component definition, Compliance Operator results, Sigstore attestations, SBOMs, HIL approval log — auditor-consumable, no repackaging. "If your environment requires OSCAL, you export the bundle here. If it doesn't, the same data is browsable." *[If OSCAL export isn't shipped by Phase 3, the seller skips this sub-beat and the script acknowledges Phase 5 delivery in the close.]*

*[differentiator #5 deep surface, OT-framed throughout]*

## Segment 4 (45:00 – 60:00) — Open-model swap + operational depth + close

**Opening**:
> "Last segment, couple of things I want to show. Platform flexibility, then the operational backbone, then I'll leave you with the repo."

**Beats**:

1. **Live VLA swap** (45:00 – 49:00). "The platform is model-agnostic. We default to OpenVLA; you might have your own VLA fine-tune or want to evaluate NVIDIA's GR00T. Here's what a swap looks like." *[Kustomize overlay change; Argo sync; new model profile picked up by KServe ServingRuntime; Fleet Manager doesn't notice; robot keeps operating]* "That's a serving-runtime config change. No code, no rebuild."

2. **End-to-end trace of a mission** (49:00 – 53:00). Open Tempo. Show a single mission's trace — camera event → scene reasoning → fleet decision → cross-cluster dispatch → VLA inference → action → robot telemetry → back to observability. Every hop instrumented. "Every operational question — 'why did this mission take so long, what failed, where's the bottleneck' — answerable from trace data."

3. **Quick tour of the repo** (53:00 – 57:00). Fork the repo open on a second screen. Point at the `infrastructure/gitops/apps/` directory — one directory per component. Show the phased plan, the decision log, the risks register. "This is all public. Your team can read the ADRs to understand why each choice was made. Quickstarts for each component are in the README. Your SA and your engineers can run this in your own lab starting today."

4. **Close** (57:00 – 60:00). 
> "What you saw — a working industrial physical AI stack on Red Hat, end-to-end: digital twin, sim-to-training pipeline, multi-site fleet ops, agentic operator with HIL, OT-grade security posture, full GitOps backbone. Every piece of it running on the same substrate you already know. If any of this is useful for an engagement in progress, the public repo is forkable; your SA can stand up a variant in your own lab in under a week; if you want a pilot, that's the next conversation."

*[differentiator #6 surfaces explicitly via live swap; #4 #5 #7 #8 reinforced; #1 #2 #3 referenced in close]*

## Beat → differentiator map

```
00:00 — opening (no surface — setting customer concern)
00:30 — #4 + #5 (provenance framing, opens segment 1)
03:00 — #4 (Cosmos Transfer synth data)
07:00 — #4 (Isaac Lab training with lineage)
11:00 — #4 (model registry + SBOMs + provenance)
15:00 — #7 opening (agentic teaser)
18:00 — #7 (read-only agent question)
23:00 — #7 (state-changing with HIL gate) — CORE BEAT
28:00 — #7 (guardrails + TrustyAI)
30:00 — #5 opening (security posture, OT framing)
30:30 — #5 (tampered artifact rejected)
34:00 — #5 (air-gap rebuild)
39:00 — #5 (segmentation as admission policy)
42:00 — #5 (compliance evidence in Console)
45:00 — #6 (live VLA swap) — CORE BEAT
49:00 — #8 (end-to-end Tempo trace)
53:00 — (repo tour, no single differentiator — operational depth)
57:00 — close (references 1 + 2 + 3 briefly, not demoed)
```

## Hard constraints

- **HIL gate moment in segment 2 must be a real approval**, not a fake UI pause. Llama Stack has to actually block and require operator input. The drawer's six panes (proposed diff, blast radius, MCP tool-call trace, guardrail outcomes, TrustyAI eval, CAC/PIV-bound approval) must all be populated from real data — not placeholders. If any pane is placeholder-only, cut the beat rather than ship it.
- **Llama Stack governance is NEVER inline in serving-time command flow** — it sits on the GitOps / PR-open path only. This is a design invariant, not a preference. No approval-gated hop between VLA inference and robot action. Serving p99 must be independent of HIL enablement; published numbers in the performance-envelope doc verify this.
- **Tampered-artifact rejection must actually fail admission**, with the real event trace visible in the cluster. Rehearse; if the CRI-O log output is confusing, adjust the Console's security panel to surface a human-readable version.
- **VLA swap in segment 4 must be observable** — show the old model profile in KServe ServingRuntime before the swap, and the new one after, via actual `oc get` commands.
- **Compliance evidence in the Console is pulled from actual Compliance Operator scan results**, not mocked. If the scan has drifted recently, the number shown updates. STIG profile name is cited exactly (`ocp4-stig-node`, version from the Phase-2 security-posture doc).
- **FIPS 140-3 claims are per-component, not global.** "FIPS: on" as a Console state is forbidden. The panel lists each component in the robot command path with its validated/non-validated status. Components without validated crypto are marked as such, not hidden.
- **Air-gap honesty**: if the live cluster under demo is OSD (internet-adjacent), the narration says so, and the air-gap walkthrough runs on the companion. Do not elide the hybrid-posture reality.
- **60-min must not exceed 60 minutes** — segments are structurally independent so the seller can trim one if an engineer wants to dig into another. Target: each segment ends at or before its 15-minute mark.

## What this demo gates (Phase 3 scope)

In addition to Phase 1 + Phase 2, Phase 3 must deliver:

1. **Cosmos Predict 2.5** deployed as KServe InferenceService. Used for action-validation safety-layer beat in segment 1.
2. **Cosmos Transfer 2.5** deployed; Kubeflow pipeline step that takes a scenario manifest + image outputs from Cosmos Writer-equivalent and produces variations.
3. **LangGraph agentic orchestrator** service — Python, persists to Postgres, wired through Llama Stack for HIL.
4. **MCP servers**: `mcp-isaac-sim`, `mcp-fleet`. Optionally `mcp-mlflow` if segment 1 deepens. `mcp-nucleus` NOT shipped unless a demo-earning use appears.
5. **Llama Stack HIL** deployed, with Agents API front of the LangGraph orchestrator. Safety guardrails + PII detection enabled.
6. **TrustyAI** signal available in observability.
7. **ClusterImagePolicy expanded** to include the VLA-serving image scope + any model registry artifacts. Demonstrated tamper-rejection.
8. **Compliance evidence UI panel in Showcase Console** pulling live Compliance Operator data.
9. **Alternative VLA Kustomize overlay** — predefined, testable — to support the live-swap beat.
10. **OTEL / Tempo trace pipeline end-to-end** from camera event through all services to observability.
11. **Showcase Console grows**: Agent panel with HIL approval drawer; Security panel with compliance evidence + admission events; live model-swap visualization (ServingRuntime before/after).

**Not required for 60-min** (and therefore NOT Phase 3 critical path):
- Physical-robot integration (Phase 4, optional, hardware-dependent).
- Vertical-specific scenario packs (Phase 4, customer-demand-driven).
- Siemens Xcelerator integration (Phase 4+, gated on partnership).

## Open items

- **Segment 2's specific "what-if" scenario**. "Two more humanoids to Zone B" is placeholder. Pick something the Isaac Sim scene can actually execute in demo time (under 90 seconds of sim time for the scenario to complete). This constrains what the agent can meaningfully ask.
- **Segment 2's HIL approval UX** → **RESOLVED in Phase 2**. The drawer content is specified in the Phase-2 HIL Approval Drawer Design Spec ADR (six panes: diff, blast radius, MCP trace, guardrail outcomes, TrustyAI eval, CAC/PIV-bound approval). Phase 3 implements to that spec; no UX design work remaining at Phase 3 entry.
- **Segment 3's tamper demo**. Which specific artifact do we tamper? VLA model file? Policy bundle? Decide during Phase 3 implementation; the beat needs something visually meaningful to the engineer audience, not abstract. Ideally: a signed policy-artifact whose training-run attestation has been tampered, so the rejection demonstrates the *training-data-to-action* provenance chain rather than just image signing.
- **OSCAL bundle scope**. The stretch beat in Segment 3 Beat 5 either lands in Phase 3 or formally slides to Phase 5. Decision gates on Phase-3 engineering capacity after MCP/LangGraph/Llama Stack core is in.
- **Segment 4's VLA swap target**. Which open VLA → which open VLA? Or open → GR00T (if licensing resolves by then)? Decision hangs on timing of the `docs/licensing-gates.md` path.
- **Repo-tour cadence**. The 4-minute tour can go deep or stay shallow depending on the engineer's questions. Prepare two flavors in the Console — a "surface tour" and a "dive into ADR-024" option, selectable on the fly.
- **60→90 minute stretch plan**. If the engineer wants 90 minutes: extra beat suggestions per segment (training-run watch in segment 1, a second agent scenario in segment 2, a specific compliance evidence file walkthrough in segment 3, edge rollout to MicroShift in segment 4).
- **Numbers**. The performance-envelope doc is v1 at Phase 2 and v2 at Phase 3. Segment 4 Beat 2 (end-to-end Tempo trace) should cite real p50/p99 from the doc, not display them generically. Whichever numbers aren't yet measured at Phase-3 entry become Phase-5 updates to the script.
