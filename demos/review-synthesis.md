# Persona-review synthesis

**Date**: 2026-04-18
**Input**: five Opus agents role-playing customer/internal personas reading the three demo scripts.
**Purpose**: identify overarching gaps and high-value concepts. Not a solve-everything punch list.

## Personas

| # | Persona | Archetype | Dominant question |
|---|---|---|---|
| 1 | Linda Park — VP Manufacturing IT, mid-tier European automotive OEM | A | "Is this relevant to my brownfield plant?" |
| 2 | Marcus Chen — Director of Warehouse Technology, large NA 3PL (~40 DCs) | B | "Show me Day-181 at 40 sites, not Day-1 at 2." |
| 3 | Dr. Aiko Tanaka — Principal Engineer, Foxconn Fii Industrial AI | C | "What changes about the operating model I already have?" |
| 4 | Col. (Ret.) Jim Holbrook — Manufacturing Engineering Director, defense-primed electronics | C + regulatory | "Can I pass a DCSA audit with this?" |
| 5 | Priya Raghavan — Senior Solution Architect, Red Hat field | Internal fit | "Can I actually walk into a meeting with this?" |

## Overarching gaps (where ≥2 personas converged)

### Gap 1 — Warehouse-only scene pigeonholes the whole showcase

- **Linda**: "Warehouse is the exact wrong opener… I almost check out at minute one."
- **Marcus**: in his lane, but "aisle obstruction is a 2018 vendor demo; my Locus fleet already reroutes."
- **Priya**: "4 of 6 of my accounts wrong-foot on warehouse. I'd open with the 20-min architecture slide and skip the cold open."

**Pattern**: a single SimReady Warehouse scene shuts the door on ~⅔ of the target field. The demo is a logistics demo wearing an industrial-AI jacket.

### Gap 2 — "Multi-site" is two sites, which is not multi-site

- **Marcus**: "Factory A + Factory B is a two-site story. I have 40 DCs. I came asking Day-181, you showed Day-1 with a second pane."
- **Aiko**: "40 factories × 200 robots — show me where your stack breaks. The script has zero numbers."

**Pattern**: the 20-min rollback beat does not answer the fleet-scale question; it postpones it. ACM at 40-site fan-out, Kafka MirrorMaker partitioning, hub loss, GitOps blast radius — all absent.

### Gap 3 — Brownfield / existing-stack integration is a 30-second sentence

- **Linda**: "No bridge from my current stack to this one. Does OpenShift go next to VMware or instead of? Does my SAP PP/DS talk to Fleet Manager? The PLC-gateway-as-VM beat is what I needed demo to lead with, and it gets 30 seconds."
- **Priya**: "The PLC VM beat is the single most useful sentence in the repo for my auto accounts. Don't let it get cut."

**Pattern**: the whole showcase reads as greenfield for a brownfield buyer. Every real industrial customer is brownfield.

### Gap 4 — The HIL approval drawer is unspecified, and it IS the differentiator

- **Aiko**: "What does the operator see at the approval moment? 'Approve this PR' is not governance. The drawer must show: MCP tool calls used for context, counterfactual reasoning, guardrail outcomes, TrustyAI eval score vs incumbent. Script hand-waves this as a Phase-3 UX design item. That's where the demo lives or dies."
- **Linda**, **Marcus**: both flagged HIL-opens-a-PR as the single highest-value moment — but only on the promise of that pattern, not its substance.

**Pattern**: the strongest moment in the 60-min demo rests on a beat whose content is admitted-TBD in Open Items.

### Gap 5 — No performance numbers anywhere

- **Aiko**: p99 latency under load, VLA hot-swap tail latency, HIL round-trip, Cosmos Predict pre-flight overhead, Llama Stack governance overhead in command path — ALL absent.
- **Marcus**: "Under 90 seconds… your own open items admit that number is aspirational. Don't quote a number to me you haven't measured."

**Pattern**: every number in the scripts is aspirational. A 60-min deep-dive with zero measured numbers fails the expert audience.

### Gap 6 — Security produces evidence-shaped gestures, not SSP-grade artifacts

- **Jim**: "Differentiator-mapping §5 reframe is correct posture, but Segment 3 doesn't produce an SSP evidence chain. STIG baseline isn't named. FIPS 140-3 per component isn't stated. SLSA level unstated. Training-data provenance is waved at. No OSCAL evidence bundle export."

**Pattern**: right framing, vendor-demo execution. For regulated buyers this is the difference between "interesting" and "I'd write a capability statement."

## Convergent strengths (keep these; they earned their moments)

1. **HIL-opens-a-PR (not direct cluster touch)** — Linda, Marcus, Aiko all flagged it. Marcus: "worth the hour." Linda: "first time 'LLM in a factory' didn't terrify me."
2. **Rollback without stopping the line** — Linda, Marcus, Priya leaning-forward moment.
3. **Cosmos Predict as *pre-dispatch admission check*** (not just training aid) — Aiko flagged as a genuinely non-table-stakes idea.
4. **Tamper-rejected-at-admission** with real rejected artifact in audit log — Jim: "genuine NIST 800-53 CM-5 / SI-7 control I can point to."
5. **OT-grade provenance framing** — Priya: "stealing that language for Thursday."
6. **Honest about limits** — Jim: "surfacing 19 FAILs with dispositions is the tell that someone sober wrote this."

## High-value concepts worth weighing (not commitments)

- **Scene-pack matrix** — same 5-min script skeleton across warehouse / discrete-assembly / process-packaging. Single biggest surface-area multiplier per Priya. Gated on what NVIDIA SimReady / publicly available scenes support without authoring.
- **Brownfield-bridge narrative** — one slide/beat somewhere in the 20-min that names MES, PLC, VMware coexistence explicitly. "OpenShift next to your existing stack, not instead of." Linda's biggest ask.
- **Fleet-scale reference architecture doc** — not a demo beat, a sidecar doc. 10/40-site bandwidth, partitioning, hub sizing, failure modes. Marcus's gate for a real deal. Aiko's demand for numbers.
- **HIL drawer content spec** — define what the approval drawer actually shows before Phase 3 builds it. Aiko's deal-breaker.
- **OSCAL evidence bundle export** — if the Console could emit a signed OSCAL-formatted evidence bundle (SSP component definition + ComplianceAsCode results + Sigstore attestations + SBOMs + HIL approval log), Jim moves from "interesting" to "capability statement." Biggest single-feature unlock for regulated-industry track.
- **Measured number set (even small)** — publish a performance envelope doc early, even if it only covers the hub+companion topology. "We measured X, expect Y at scale" beats "under 90 seconds."
- **Honest fork-time rescoping** — Priya: "5-min loop in a week, 20-min in two" is a defensible public success criterion. One-week full-stack isn't.

## What this review does NOT claim

- It does not mean fix all six gaps. Some are Phase-3 territory by design (drawer spec, OSCAL export). Some are structural (scene-pack matrix) and need to be decided, not just scheduled.
- It does not mean rewrite the scripts. Convergent praise says the script architecture is right; the gaps are content depth, scene diversity, and claims-vs-evidence.
- It does not replace technical review. These are audience-fit reads, not implementation correctness checks.

## Suggested next decision points (for human, not for implementation)

1. **Scene-pack decision**: commit to one scene for the reference demo, or invest in a matrix of 2–3 scenes sharing a script skeleton? This is a scope decision that affects every phase.
2. **Brownfield beat**: is there a credible way to demo a SimReady assembly scene with a KubeVirt-hosted Siemens-like S7 simulator or MES-stub talking to Fleet Manager? If yes, it becomes the 20-min's lead moment. If no, it stays a narration sentence.
3. **Fleet-scale doc scope**: should we produce a sidecar "operating-at-scale" doc for Archetype B/C even if we never demo 40 sites live? Relatively cheap, covers a clear convergent gap.
4. **OSCAL evidence bundle**: does a Phase-3 item get added for this, or is it explicitly out-of-scope with a documented reason?
5. **Demo performance-envelope doc**: commit to measuring and publishing what the hub+companion topology actually does, even with small numbers? This is the single cheapest number-credibility move.
