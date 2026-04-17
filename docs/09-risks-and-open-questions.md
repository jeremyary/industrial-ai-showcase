# 09 — Risks and Open Questions

Everything in this document is known but not resolved. This is the list the implementation team consults before making a decision that would close one of these off — and the list that gets updated as decisions accumulate.

Items fall into four buckets: **open decisions** (things we will decide, we're just not deciding now), **risks** (things that could go wrong), **unknowns** (things dependent on external parties), and **contingencies** (what-if plans).

---

## Open decisions

### OD-1: Naming the Showcase Console

**Question**: "Showcase Console" is the working name. Marketing / product may prefer something stronger — "Forge" has been floated as alternative.

**Why it's open**: naming is a marketing function; we don't need to close it yet. Code and docs use "Showcase Console" as placeholder.

**Trigger to resolve**: before the first external demo of the Console, or before a blog post / Red Hat Summit submission referencing it.

**How to resolve**: loop in the Red Hat product marketing team for the Physical AI / Industrial space with the three-option shortlist (Showcase Console, Forge, marketing's alternative) and a brief context doc.

### OD-2: Acquiring a physical Unitree G1

**Question**: Phase 4 allows for a physical Unitree G1 as a "hardware integration peak." Do we actually buy one?

**Why it's open**: a G1 is a ~$16K investment plus safety infrastructure (nets, stanchions, E-stop, recovery harness). Worth it only if Phase 4 reaches a maturity where hardware integration is the next credible step — and only if we have a physical lab space and a safety officer.

**Trigger to resolve**: entering Phase 4 with a proven sim story and a customer engagement where hardware integration would be the inflection point.

**How to resolve**: budget proposal + lab safety plan + success criteria. Defer until Phase 3 is complete.

### OD-3: True air-gap validation vs documented path — RESOLVED via ADR-017

**Status**: Resolved by ADR-017 (OSD hub + self-managed companion cluster strategy).

**Resolution**: True air-gap validation happens on the self-managed companion cluster, where we have full control over registry mirrors, admission, and network egress. The OSD hub is inherently internet-adjacent (Red Hat-managed); any air-gap claim about the OSD hub alone would be misleading.

**Implication for the reference story**: The external narrative is "the full reference deploys on any Red Hat OpenShift substrate; the air-gapped path is demonstrated on self-managed OpenShift, which is the deployment mode every regulated-industry customer runs anyway." This is honest and strong.

**Remaining work**: air-gap validation becomes a Phase 2 exit criterion on the companion (and on any self-managed spoke that joins). Track as a Phase 2 work item rather than an open decision.

### OD-4: Second spoke cluster — physical hardware vs nested on companion

**Question**: Spoke clusters can be Single-Node OpenShift on physical hardware, or nested clusters running as VMs on OpenShift Virtualization on the **companion cluster** (not the hub — the OSD hub doesn't run Virtualization per ADR-017). Which do we use for Phase 2?

**Why it's open**: depends on hardware budget and companion-cluster capacity. Nested on companion is cheaper if companion host has the headroom; physical is more credible for customer demos of the multi-site story.

**Risk**: nested-only demos sometimes feel less authentic when an experienced customer probes. But architecturally, it's the same story.

**Recommendation**: physical Spoke A (dedicated lab hardware or SNO on a spare workstation), nested Spoke B on the companion cluster. Budget-friendly compromise; physical spoke demonstrates "the real thing" while nested proves the architectural point at scale.

**Trigger to resolve**: Phase 2 entry.

### OD-5: LLM brain for the LangGraph agent

**Question**: Which LLM do we ship serving for the agentic orchestrator's "brain"?

**Why it's open**: Nemotron variants are ideal from an NVIDIA-alignment standpoint, but Mistral, Qwen, Llama, and DeepSeek-Distill families are all credible. Each has different serving footprints on L40S.

**Constraints**:
- Must fit on 1 L4 (24 GB) by preference; L40S (48 GB) if the best-fitting model pushes past 24 GB.
- Must have strong tool-use / structured-output capability — the agent is MCP-driven, needs reliable function calling.
- Should be open-weight — "you can run this yourself" is part of the narrative.
- Must be compatible with Llama Stack's Agents API (ADR-019) — most open-weight models with good tool-use are; verify before committing.

**Capability to use**: RHOAI 3.4 EA1 ships **LLM Compressor** (Developer Preview) as a workbench image + pipeline runtime. This lets us compress a larger model (a Qwen3-14B or Nemotron variant) for efficient vLLM deployment on L4 — potentially making the L4 target practical for a stronger base model than would otherwise fit. Benchmark the compressed variants alongside the native candidates.

**Recommendation**: Nemotron-class as default; pluggable to customer-provided OpenAI-compatible endpoint for customers who want to use their own licensed models. LLM Compressor is the lever for fitting stronger models in L4 budget if native variants underperform.

**Trigger to resolve**: Phase 3 entry. Benchmark 2–3 candidates (native and LLM-Compressor-compressed) against the specific agentic tasks in `workloads/langgraph-orchestrator/graphs/`.

### OD-6: The Tekton vs Argo Workflows vs Kubeflow Pipelines boundary

**Question**: We have three workflow systems in the reference: Tekton (CI / container builds), Argo CD (GitOps reconciliation), and Kubeflow Pipelines (ML training orchestration). Is there overlap? Should we collapse any?

**Consideration**: Kubeflow Pipelines is bundled with RHOAI and is the natural fit for training workflows. Tekton is the natural fit for image builds. Argo CD is strictly reconciliation and doesn't overlap. The three are distinct in our mental model.

**Decision**: keep all three for now; each does its own job. Document the boundaries clearly in `docs/deployment/runbooks/`.

**Still open**: whether Argo Workflows should join (for non-training, non-build long-running workflows — e.g., scenario-expansion orchestration that isn't strictly an ML pipeline). Defer to Phase 3.

### OD-7: Console auth model for external customers

**Question**: The Showcase Console runs on a Red Hat cluster for Red Hat sellers. For customer handoff (give them a lab environment), do we:
(a) give them access to our cluster with a scoped identity,
(b) deploy a per-customer instance in their environment,
(c) route them through a shared but tenant-isolated SaaS-style deployment?

**New option from RHOAI 3.4 EA1**: **Models-as-a-Service (MaaS)** is available as a Technology Preview. MaaS exposes models through managed API endpoints with centralized consumption policies. For customer handoff, this reshapes option (a): instead of broad cluster access, customers get scoped MaaS API keys against a specific model deployment, with consumption policies enforced centrally. Much cleaner than broad cluster access for quick evaluations.

**Recommendation**: (b) remains the most credible for serious customer engagements (fork-and-deploy in their cluster). MaaS-based (a) becomes the better lightweight option for quick evaluations. (c) is out of scope until / unless there's productization.

**Trigger to resolve**: Phase 3 customer-handoff work.

### OD-8: Companion cluster host selection

**Question**: Per ADR-017, the self-managed companion cluster needs a host. Three candidates are viable from existing hardware: GMKTec Evo-X2 Mini PC (128 GB RAM, Ryzen AI Max+ 395 with integrated Radeon 8060S, 2 TB SSD), ORIGIN PC (RTX 5090, 128 GB RAM, i9-13900KX32), or dedicated lab hardware not yet acquired.

**Why it's open**: each host has trade-offs:
- **GMKTec Evo-X2**: plenty of CPU/RAM for the baseline companion workloads (OpenShift Virtualization without vGPU, MachineConfig STIG, FIPS, cluster-scoped Sigstore admission, air-gap validation). The integrated Radeon is useless for NVIDIA vGPU passthrough, so the Kit-workstation-with-vGPU demonstration is blocked on this host alone. Best for the "infrastructure-side differentiators" but not the vGPU story.
- **ORIGIN PC**: RTX 5090 enables the full vGPU Kit workstation demonstration. Downside: it's a primary workstation used for daily coding + gaming; running it as a cluster host 24/7 conflicts with its primary role.
- **Dedicated lab hardware**: cleanest, but costs money and lead time. A mid-range workstation with an NVIDIA RTX card (A4000, A5000, or RTX 6000 Ada) would cover everything.

**Recommendation**: stage the decision. Start with GMKTec Evo-X2 as the Phase 0 companion — it covers the majority of the differentiator demonstrations (MachineConfig, FIPS, air-gap, Sigstore, Virtualization *without* GPU passthrough). For the vGPU-specific Kit workstation demo: if OSD supports OpenShift Virtualization (see OD-9), use OSD; otherwise either schedule vGPU demo sessions on the ORIGIN PC, or treat it as a Phase 4 investment trigger for dedicated lab hardware.

**Trigger to resolve**: Phase 0 companion provisioning.

### OD-9: OpenShift Virtualization availability on this OSD instance

**Question**: Is OpenShift Virtualization available and installable on this specific internal OSD instance? Cluster-admin access clears the permission gate, but availability also depends on the OSD subscription tier, cloud substrate (the underlying cloud's nested-virtualization support), and whether SRE has enabled the relevant operator catalog.

**Why it's open**: unverified until Phase 0 baseline capture.

**Implications**:
- **If available on OSD**: the vGPU Kit workstation story can run on the hub (using L40S nodes for vGPU). Companion cluster's role simplifies — no longer needs OpenShift Virtualization for that demo, can stay focused on MachineConfig hardening and air-gap.
- **If not available on OSD**: companion hosts OpenShift Virtualization; companion host selection (OD-8) leans toward ORIGIN PC or dedicated lab hardware for vGPU capability.

**Trigger to resolve**: Phase 0 baseline capture — this is item #1 of the Phase 0 validation work.

---

## Risks

### R-1: NVIDIA API-surface churn outpaces our adaptation

**Description**: NVIDIA is shipping rapidly. Cosmos versions, Isaac Sim versions, GR00T checkpoints, Kit SDK, and the MCP servers all evolve quickly. Our integrations (container images, NIM wrappers, Helm value sets) could lag and break.

**Likelihood**: high.

**Impact**: medium — a broken integration is usually an afternoon's fix, not a project crisis, but accumulated rot degrades the reference over time.

**Mitigations**:
- Pin every upstream version explicitly (container image digests, chart versions).
- Run a weekly upgrade-test CI job that attempts pulls + smoke tests of newer versions and reports diffs.
- Keep a living changelog in `docs/CHANGELOG.md` tracking upstream version bumps we've absorbed.

### R-2: Kit App Streaming production stability

**Description**: WebRTC-based streaming is technically demanding — NAT traversal, codec negotiation, Route configuration, browser variance. A demo that relies on it is fragile.

**Likelihood**: medium.

**Impact**: high during a live seller engagement.

**Mitigations**:
- Always maintain pre-recorded fallback captures per scenario.
- Showcase Console detects streaming failures and transitions gracefully to replay mode.
- Pre-flight check in the Console before opening a Stage view: verifies streaming backend is healthy.
- Document known-good browser versions for sellers.

### R-3: GR00T commercial licensing friction

**Description**: GR00T N1.7 is offered under a commercial license with specific terms. If terms change or require per-customer agreements, deployments slow down.

**Likelihood**: low but non-zero.

**Impact**: medium — BYO-model fallback (Pi-0, OpenVLA) exists, so no story-ending risk, but would degrade the headline demo.

**Mitigations**:
- Track licensing terms in `docs/licensing/groot.md`.
- Keep Pi-0 and OpenVLA configurations tested and current — not sitting bit-rotted.
- If a customer engagement needs a specific model, surface licensing context to the account team early.

### R-4: MLflow in RHOAI Early Access changes shape

**Description**: RHOAI Early Access is, by definition, not committed API surface. MLflow integration details could shift. Commitments we build against could break.

**Likelihood**: medium over the project lifetime.

**Impact**: medium — the project's MLOps layer assumes MLflow; if RHOAI drops it or replaces it, we have work to do.

**Mitigations**:
- Keep MLflow interactions behind a thin abstraction in `workloads/common/python-lib/tracking/`.
- Monitor RHOAI roadmap announcements; update the project ADR log if shifts are material.
- If RHOAI GA settles on something different, plan a migration phase rather than letting drift accumulate.

### R-5: The Showcase Console is the wrong level of ambition

**Description**: The Console is a real software product. It takes real engineering. Scope creep and timeline overruns are typical for UI-heavy projects — and the Console is the most UI-heavy part.

**Likelihood**: medium.

**Impact**: high — if the Console is late or incomplete, the sales-enablement story evaporates.

**Mitigations**:
- Skeletal Console in Phase 1, deliberately rough. Don't polish before it works end-to-end.
- Each phase adds capability increments, not "finally make it pretty."
- Explicit scope guardrails: no pricing calculators, no self-service customer flows, no analytics dashboards beyond what embeds Grafana.
- Consider bringing in a dedicated frontend engineer rather than treating this as a side task for the infra team.

### R-6: Demo-time GPU contention

**Description**: A seller opens the Console during a scheduled training window and the cluster is in Mode C. The transition takes 2+ minutes; the customer meeting is not scheduled around cluster state.

**Likelihood**: medium.

**Impact**: high (demo goes sideways in front of a customer).

**Mitigations**:
- The Showcase Console shows cluster mode in real time and warns if training is active.
- Training windows are scheduled via a shared calendar visible to all sellers.
- Default posture: training windows are outside "seller hours" (e.g., evenings and weekends).
- Emergency-abort control for training jobs if needed, with clear understanding of checkpoint status.

### R-7: Multi-site federation fragility

**Description**: ACM + MirrorMaker + Submariner work well in healthy conditions, but cross-site network issues reveal their limits. A live demo of "propagate policy from hub to Spoke A" can stall if cross-cluster routing is blipping.

**Likelihood**: medium during early Phase 2 work; decreases as the topology matures.

**Impact**: medium during demos; acceptable in Mode B (show the recording, explain the concept).

**Mitigations**:
- Pre-flight check in the Console for multi-site demos — verifies hub-spoke connectivity before letting the seller start.
- Pre-recorded fallback for cross-site beats specifically.
- Chaos testing in `tests/chaos/` that intentionally breaks cross-site connectivity and validates graceful degradation.

### R-8: Dependency on a single internal Nucleus deployment

**Description**: The existing Nucleus deployment on OpenShift was stood up outside this project's GitOps discipline. Drift is likely; bringing it under GitOps in Phase 1 may uncover configuration differences.

**Likelihood**: high.

**Impact**: low-to-medium — discovery and codification is normal; a one-off effort.

**Mitigations**:
- First Phase 1 work item is "snapshot Nucleus current state into `workloads/nucleus/`."
- Treat the codification as a fresh install validation, not just a read-and-transcribe.

### R-9: Scenario asset authoring is unglamorous but load-bearing

**Description**: USD authoring for the warehouse and other scenes is a specialized skill. The scenes are what customers see first — they must be credible. If the team lacks USD authoring capability, either hire, contract, or lean heavily on NVIDIA sample scenes.

**Likelihood**: depends on team composition.

**Impact**: medium — inauthentic-looking scenes undermine the otherwise-strong demo.

**Mitigations**:
- Lean on NVIDIA sample scenes and Omniverse Marketplace assets where possible.
- Budget for contract USD authoring if internal capacity is thin.
- Keep the warehouse scene simple enough to be credible rather than ambitious and broken.

### R-10: "Air-gapped" claim fragility

**Description**: Claiming air-gap support invites serious customers to test it. Every dependency that silently reaches the internet is a credibility bomb.

**Likelihood**: medium.

**Impact**: high if a customer proves a violation.

**Mitigations**:
- Air-gap validation as a Phase 2 exit criterion (see OD-3).
- Dependency inventory in `docs/deployment/air-gap-inventory.md` — every external pull documented, every mirrorable artifact identified.
- Disconnected test environment spun up periodically in CI to catch regressions.

### R-11: OSD SRE ticket latency for infrastructure-layer changes

**Description**: Although we hold cluster-admin on the OSD hub, infrastructure-layer changes remain SRE-managed: GPU machine pool adjustments (adding/removing nodes, changing instance families), underlying cloud-resource provisioning, and (rarely) base image updates. Each is a ticket with a response SLA measured in business days.

**Likelihood**: medium — SRE is responsive, and most work we do doesn't touch infrastructure.

**Impact**: low — most phase progress doesn't depend on these tickets; when they do, it's predictable delay rather than surprise.

**Mitigations**:
- Front-load any anticipated infrastructure requests in Phase 0 planning.
- Mark SRE-gated work items clearly in the phased plan; sequence non-gated work first so progress continues during ticket cycles.
- Maintain a "pending SRE requests" section in `infrastructure/baseline/osd-hub-state.md`.
- Companion-cluster work proceeds unblocked by any OSD SRE latency — use that in parallel when useful.

### R-12: OSD posture changes unpredictably

**Description**: OpenShift Dedicated evolves. Features may be added (e.g., OpenShift Virtualization support on OSD would materially change ADR-017), or restrictions tightened (e.g., operator catalog curation). Architecture decisions pinned to today's OSD capabilities could shift.

**Likelihood**: low-to-medium over the project lifetime.

**Impact**: low per individual change; medium cumulative if we don't notice.

**Mitigations**:
- Track OSD release notes and feature-availability changes quarterly.
- If a capability becomes available on OSD that we currently route through companion (e.g., Virtualization), revisit ADR-017 rather than silently pretending nothing changed.
- Keep the companion-cluster strategy in place even if OSD gains capabilities — the self-managed path has standalone value for customer-facing narrative, not just for OSD-gap-filling.

### R-13: GPU class drift (workloads scheduled to wrong GPU product)

**Description**: Workloads that should target L4 end up on L40S (or vice versa) due to missing `nvidia.com/gpu.product` nodeSelector, default Helm chart values targeting one class implicitly, or a chart being deployed with a stale GPU product string. Silent wrong-class scheduling wastes L40S on inference or underpowers sims on L4.

**Likelihood**: medium early in Phase 1 as the pattern becomes muscle memory.

**Impact**: medium — performance degradation, not outright failure, but demo-visible if sims lag or inference OOMs.

**Mitigations**:
- The Helm chart library in `workloads/common/chart-library/` exposes `gpuProduct` as a required, non-defaulted value — no chart installs without an explicit choice.
- Grafana class-imbalance alert (documented in `docs/08-gpu-resource-planning.md`) fires if a pod with a given `nvidia.com/gpu.product` selector lands on a node with a different product label (shouldn't happen if selectors are correct, but detects label-drift edge cases).
- PR template includes a "GPU product targeting declared?" checkbox for anything touching GPU workloads.
- Every new GC-N entry in the GPU planning doc is code-reviewed specifically for class assignment rationale.

### R-14: RHOAI EA → GA transition requires fresh install

**Description**: RHOAI Early Access releases (3.4 EA1 included) do not support in-place upgrades to GA — the transition is always a fresh install. When RHOAI 3.5 GA (or later) ships and we want to move off EA, the reference cluster has to be reinstalled rather than upgraded. State (DataScienceCluster config, MLflow backend data, model registry, notebooks) must migrate manually.

**Likelihood**: certainty, not probability — the transition will happen eventually.

**Impact**: medium — a planned maintenance event rather than an incident. Painful if unplanned or if state migration hasn't been exercised.

**Mitigations**:
- All stateful configuration lives in Git (GitOps): DataScienceCluster CR, MLflow config, pipeline definitions.
- MLflow backend (Postgres via CNPG) and artifact store (S3) live outside RHOAI's control plane — survive a RHOAI reinstall.
- Document the reinstall + migration procedure as soon as Phase 1 is stable, in `docs/deployment/runbooks/rhoai-ea-to-ga-migration.md`, as a running draft rather than waiting for necessity.
- Schedule the transition for a natural boundary (a phase completion, a quiet week) rather than reactively.
- Do not accumulate state in RHOAI-internal components that has no GitOps source of truth.

---

## Unknowns

### U-1: RHEL for NVIDIA (H2 2026) specifics

**What we don't know**: exact release date, exact feature set, exact relationship to the GPU Operator.

**Dependency**: affects Phase 2+ decisions about driver management and edge image-mode builds.

**Plan**: design to adapt when it ships. Don't make architectural decisions that preclude adopting it.

### U-2: NVIDIA Omniverse modular library (`ovrtx`, `ovphysx`, `ovstorage`) stability

**What we don't know**: whether these are production-ready in H2 2026, what their migration story from Nucleus looks like in practice, whether customers adopt them or stay on Nucleus.

**Dependency**: Phase 2's "ovstorage variant" (ADR-002) depends on the libraries being credible.

**Plan**: track closely; if they slip, delay the variant. Don't stall the main Nucleus path on it.

### U-3: Siemens receptivity

**What we don't know**: whether Siemens wants to collaborate in the way we anticipate when we approach them with the reference. The existing Red Hat-Siemens relationship is real but Physical AI is a new axis.

**Dependency**: Phase 4.

**Plan**: build without them; approach when ready; accept that the Siemens overlay may be different from our current assumptions.

### U-4: The velocity of the rest of the physical-AI market

**What we don't know**: whether Boston Dynamics, Agility, Apptronik, Figure, or 1X ship compelling SDKs that demand our attention; whether a non-NVIDIA physics engine gains traction (MuJoCo-MJX trajectory, for example).

**Dependency**: our long-term positioning.

**Plan**: quarterly market scan documented in `docs/market-scan.md` (living doc). Course-correct as warranted.

### U-5: The Claude Code project workflow itself

**What we don't know**: as another Opus 4.7 instance takes the Claude Code seat and implements this plan, what will break down. Novel workflow.

**Dependency**: the entire implementation phase.

**Plan**: keep `CLAUDE.md` updated aggressively with lessons learned. Start each implementation session with a brief "lessons from last session" note appended to `CLAUDE.md` if relevant.

### U-6: RHOAI 3.4 MLflow availability specifics

**What we don't know**: whether MLflow is GA, tech-preview, or not-present in the specific RHOAI 3.4 build installed on the hub. MLflow's integration state in RHOAI has shifted across versions and may be gated behind component toggles or channel selection.

**Dependency**: Phase 1 work item 0 directly; Phase 2 MLOps stream downstream.

**Plan**: **RESOLVED** — MLflow is definitively shipped in RHOAI 3.4 EA1 as `rhoai/odh-mlflow-rhel9:v3.4.0-ea.1`. See ADR-015. This entry is retained for historical context and will be removed in the next cleanup.

### U-7: Feature Store adoption for fleet-derived features

**What we don't know**: whether Feature Store (Feast-based, Tech Preview in RHOAI 3.4 EA1) is a better fit for the fleet-telemetry-derived features that robot-brain preprocessors consume, versus the Phase 1 plan of Kafka → Postgres → in-process feature computation.

**Dependency**: Phase 2+. Phase 1 ships without Feature Store; nothing blocks evaluation.

**Plan**: at the start of Phase 2, evaluate Feature Store against the then-current fleet telemetry feature patterns. Adoption criteria: (a) does it simplify the robot-brain preprocessor code meaningfully? (b) does its RBAC model help with the multi-tenant hub story? (c) is the Tech Preview mature enough to depend on? If all three are yes, adopt; document in a new ADR. If not, stay on the Phase 1 pattern and revisit later.

---

## Contingencies

### C-1: One GPU node fails mid-engagement

**Scenario**: Seller is in a live customer meeting; a GPU node drops.

**Response**: Console auto-transitions to Mode B. Scenarios requiring GR00T + VSS + Kit streaming concurrently downgrade to replay mode. Seller gets a polite banner: "We're running degraded — some interactive elements will play back from recording." Customer usually doesn't notice unless the seller draws attention to it.

### C-2: Nucleus unavailability

**Scenario**: Nucleus pod crashes or Route fails.

**Response**: Isaac Sim continues running against its local asset cache; scene can't be reloaded until Nucleus returns, but the active sim keeps going. Console shows "Nucleus degraded" warning; scenario transitions pause until recovery. Recovery is ~60 seconds for a pod restart.

### C-3: Complete cluster unavailability

**Scenario**: scheduled maintenance, unexpected outage, or early-morning-meeting-in-a-different-timezone demo where the cluster isn't warmed up.

**Response**: Console ships with a local replay bundle. Seller opens it; every scripted scenario plays from recording with zero live dependency. Honest disclosure: "For logistical reasons we're playing from recording today; the live system is available at [link] for your team to explore after."

### C-4: An NVIDIA component we depend on is deprecated

**Scenario**: NVIDIA announces end-of-life for a NIM or a blueprint component.

**Response**: evaluate replacement; if available, plan an ADR and migration as a bounded workstream. If no replacement, document the gap honestly in the reference — an absence we call out is less damaging than a silently broken demo.

### C-5: The reference is too complex for its intended audience

**Scenario**: Feedback accumulates that Archetype A customers can't follow even the 5-minute demo without losing thread.

**Response**: ruthlessly simplify the Archetype A path. The 5-minute demo can become 3 minutes. The Stage view for novice mode can hide more. Audience-aware design means we can do this without compromising the Archetype C path. Requires listening — the Console's telemetry about audience-mode transitions and depth-drawer usage is the data source.

---

## When to revisit this document

- Start of every phase (do any open decisions need to close before we proceed?)
- After every significant customer engagement (what did we learn?)
- When an ADR is added that resolves an open decision (move it from here to ADR log, mark resolved).
- Quarterly market scan (new risks? new unknowns?).
