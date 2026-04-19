# Licensing gates

Model, dataset, and API-key constraints that shape what we can actually build in the showcase. Each entry names the gate, our current posture, and what unblocks a different posture if we ever need it.

This is a living doc — update as gates resolve (or don't).

## 1. BONES-SEED motion dataset

**What**: Humanoid motion-capture dataset used as training data for NVIDIA's GEAR-SONIC whole-body controller.

**License**: Commercial license required for organizations with revenue over $1M. Red Hat is over the threshold.

**Status**: Direct contact with bones.studio has gone unanswered. No commercial agreement in hand.

**Impact**: GEAR-SONIC is tightly coupled to BONES-SEED's motion format; community alternatives (CMU, AMASS, LaFAN1) aren't drop-in-compatible. Means we cannot train a GEAR-SONIC WBC policy ourselves in any demo-able way.

**Our posture**: **Tier-1 (WBC) is out of scope for implementation.** We keep the three-tier hierarchy (WBC / VLA / Mission Planner) as *conceptual framing* in demo narration — it's physically accurate and earns engineer respect — but we only *build and showcase* Tier-2 and Tier-3. Tier-1 is talk-track only: "the on-robot whole-body controller runs at 200-250 Hz using NVIDIA's published models; Red Hat hosts Isaac Lab training pipelines when customers want to customize — the orchestration is proven, training a specific WBC policy is gated on dataset licensing and out of scope here."

**What would change this**: licensing resolution with bones.studio OR migrating to a WBC framework that doesn't depend on BONES-SEED (HumanPlus, Humanoid-Gym, OmniH2O — all would require weeks of new work to replace GEAR-SONIC specifically).

---

## 2. GR00T VLA family (N1 / N1.5 / N1.6 / N1.7)

**What**: NVIDIA's humanoid vision-language-action foundation model. Charter differentiator #6 originally positioned GR00T as "primary VLA with pluggable alternatives."

**License**: NVIDIA OneWay Noncommercial. Commercial use by Red Hat requires a partnership agreement.

**Status**: No agreement currently in place.

**Options**:

- **(a) Seek partnership agreement via Red Hat–NVIDIA account relationship.** Best long-term posture. Timeline uncertain.
- **(b) PoC / research stance.** Legal-gray-area — the showcase is reference material, not a commercialized product. Requires legal review before we take it publicly.
- **(c) Promote an open VLA to primary.** Options: OpenVLA (MIT), pi-0 (Apache-2.0), SmolVLA (Apache-2.0). GR00T demoted to "also works — platform is model-agnostic" demo beat.

**Our posture**: **Option (c) as default.** Open VLA primary; GR00T shown as one of several. This is actually *stronger* for differentiator #6 — we prove the platform isn't locked to NVIDIA's model by running on an open one, then show NVIDIA's model drops in without code changes. Option (a) stays on the table; if the partnership lands, GR00T becomes primary without rework (the serving layer takes a model profile as a CR per ADR-003).

**What would change this**: partnership agreement signed, OR legal review clears (b) for the reference-material scope.

---

## 3. NGC API key

**What**: Authentication token for `nvcr.io` image pulls and NGC catalog resource downloads.

**Status**: Current key is a 90-day trial (per brainstorming doc). Sufficient for Phase 0/1 development; expires.

**Impact**: Some entitlements we needed at Phase 0/1 are already entitlement-gated even with a valid key — `nucleus-compose-stack-pb25h1`, `ingress-router`, `auth-router-gateway` all returned 401 during Nucleus Session 16. A longer-term enterprise-entitled key would likely unlock more than just longevity.

**Our posture**: Track expiry; request renewal before 90-day window closes. Separately, request Red Hat ↔ NVIDIA NGC enterprise entitlement for the Nucleus Compose stack + associated gated images. Not a Phase-1 critical-path blocker — we've worked around individual gated resources (see ADR-024 closing note on `ingress-router` / `auth-router-gateway`).

**What would change this**: permanent org-level NGC enterprise entitlement established.

---

## 4. Cosmos family attribution

**What**: Cosmos Reason 2, Cosmos Predict 2.5, Cosmos Transfer 2.5 — world-model and scene-reasoning foundation models.

**License**: NVIDIA Open Model License (generally permissive for commercial use with attribution). Requires displaying "Built on NVIDIA Cosmos" or equivalent.

**Status**: Usable. Attribution obligations straightforward.

**Our posture**: Include attribution in the Showcase Console credits, READMEs for any component that calls Cosmos, and demo script sign-off. No other constraint.

**What would change this**: license terms update (unlikely to tighten, more likely to stay or loosen).

---

## 5. Nemotron 3 family

**What**: NVIDIA's LLM family used as the mission-planner brain (Tier-3).

**License**: Open Model License; permissive commercial use.

**Status**: Usable via NGC + via Hugging Face mirrors. Nemotron-3-Nano-4B fits on a single L40S; Super-120B needs H100/B200.

**Our posture**: Nano variant fits our GPU budget and serves the 0.25-1 Hz mission-planner role adequately. No license gate.

---

## 6. Isaac Sim / Isaac Lab / Omniverse Kit

**License**: NVIDIA Software License — commercial use permitted, but some use cases (notably public cloud redistribution of modified derivatives) are restricted.

**Status**: Usable for our reference-material / on-prem-showcase scope.

**Our posture**: No immediate concern. Any customer forking our reference inherits the Omniverse licensing conversation with NVIDIA, which is the normal path.

---

## 7. Unitree G1 USD models + Nova Carter USD

**License**: Published by NVIDIA as Isaac Sim samples, generally freely usable for simulation. Physical-robot use of the same models inside a paid customer product is a separate conversation customers have with Unitree / the robot vendor — out of our scope.

**Status**: Usable.

---

## Consolidated impact on scope

| Gate | Our choice | Alternative if gate resolves |
|---|---|---|
| BONES-SEED / GEAR-SONIC | Tier-1 WBC out-of-scope; talk-track only | Build WBC training demo if licensing resolves |
| GR00T family | Open VLA primary, GR00T as secondary | GR00T promoted to primary if partnership lands |
| NGC API key | 90-day trial; rep-ask for enterprise entitlement | Longer-lived entitled key |
| Cosmos family | Usable with attribution | — |
| Nemotron family | Usable | — |
| Isaac / Omniverse | Usable for reference-material | — |
| Unitree / Nova Carter USDs | Usable | — |

## Charter + phased-plan downstream effects

- **Charter differentiator #6 ("open model choice")** stays as-written but its demo *proof* shifts: open VLA primary, NVIDIA's VLA as one of the interchangeable alternatives.
- **Phased-plan Phase 1 item 10** ("Robot Brain serving — GR00T primary") gets re-ordered: primary becomes an open VLA; GR00T becomes one of the configured alternatives.
- **Phased-plan Phase 2 item 2** (Isaac Lab training pipeline) narrows: we train a VLA fine-tune (open-VLA-compatible) in sim, NOT a WBC policy. The pipeline architecture stays the same; what runs through it changes.
- **Three-tier narrative framing**: keep in demo scripts; implement only Tier-2 + Tier-3. This is captured in the "three-tier as demo spine" evaluation task (#21).

## Rep-ask list (consolidated)

When a conversation with NVIDIA account team / partnership team happens, bring these together:

1. GR00T commercial-use partnership agreement for Red Hat reference-material use.
2. NGC enterprise entitlement for the `nucleus-compose-stack-pb25h1` resource + associated gated images (`ingress-router`, `auth-router-gateway`, any other gated Nucleus components).
3. Long-lived NGC API key (replace 90-day trial).
4. Optionally — confirm "Built on NVIDIA Cosmos" attribution format that satisfies their license requirement for our public-facing surface.
