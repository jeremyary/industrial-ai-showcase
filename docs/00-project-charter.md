# 00 — Project Charter

## Mission

Build a complete, operationally credible reference implementation of NVIDIA's Mega Omniverse Blueprint on Red Hat OpenShift — and the sales-enablement stack that turns it into a walk-in-ready offering for Red Hat field teams engaging customers across the full maturity spectrum, from Omniverse-curious to Siemens/Foxconn-class operators.

The project has two inseparable outputs:

1. A working, deployable, documented reference stack that substantiates Red Hat's claim to be a first-class partner in industrial physical AI.
2. A sales-enablement layer — centered on the Showcase Console — that turns the reference into something Red Hat sellers and field engineers can actually wield in customer meetings of any duration and depth.

Neither half succeeds without the other. A gorgeous demo with no verifiable stack beneath it becomes PowerPoint. A flawless reference implementation no one can present becomes a GitHub repository nobody finds.

## Strategic framing

NVIDIA's consistent posture through GTC 2025 and GTC 2026 is: *here is the operating system for the $50T physical AI industry — run it on DGX / OVX / DGX Cloud.* The GTC 2026 announcements — the new modular libraries (`ovrtx`, `ovphysx`, `ovstorage`), Kit App Streaming's Kubernetes-native CRDs + Helm charts, MCP servers for Omniverse — make the stack more cloud-native than ever, but NVIDIA still does essentially no work on the "how do you operate this across a heterogeneous hybrid fleet over five years" problem.

That is the seam Red Hat fits through. NVIDIA ships the Physical AI stack; Red Hat operationalizes it everywhere it has to run — including, critically, the on-prem factory datacenters, air-gapped defense sites, and robots themselves where the customer's actual work happens.

Every artifact this project produces is in service of that frame.

## The eight differentiators (the "value claims" we must substantiate)

These are the claims Red Hat makes in customer meetings that this reference has to back up with running code and deployable artifacts:

1. **On-prem and air-gapped are first-class.** Siemens Amberg, Foxconn Fii, TSMC Phoenix — none of these run IP-sensitive factory twins on DGX Cloud. This stack must deploy identically on-prem and offline.
2. **One platform for containers, VMs, and vGPU workstations.** Omniverse Kit workstations need vGPU-backed VMs; Isaac Sim runs as GPU-passthrough containers; Nucleus and USD services are microservices; NIMs are containers. OpenShift Virtualization + GPU Operator handles all three on a single cluster. (Note: in this reference the unified container + VM + workstation demonstration lives on a self-managed companion cluster because the OSD hub does not offer OpenShift Virtualization — see ADR-017. The differentiator is architectural; the demonstration is cross-cluster.)
3. **Hybrid cloud → factory edge → robot, one operational model.** RHEL → OpenShift → Device Edge → MicroShift → bootable containers on Jetson. Same container image, signed once, deploys anywhere in the chain. ACM + Ansible + Argo CD federate the fleet.
4. **OpenShift AI as the MLOps backbone for "robot brains."** Training/fine-tuning of GR00T variants, experiment tracking via MLflow, model registry with lineage to the sim episodes that validated each policy version, serving via vLLM, distributed training via KubeRay.
5. **Security and supply-chain posture appropriate to OT.** Sigstore-signed images, SBOMs, STIG profiles, FIPS mode, Multus for shop-floor network attachments, zero-trust east-west via Istio. These are not afterthoughts; they appear from Phase 0.
6. **Open model choice.** Cosmos and GR00T ship as primary, but nothing is locked to them. Customers can plug in Pi-0, OpenVLA, or their own fine-tune without rebuilding the architecture.
7. **Agentic orchestration via MCP.** Omniverse's new MCP servers expose simulation operations to LLM agents. LangGraph-based agents on OpenShift AI orchestrate sim scenarios, synthetic-data generation, and fleet interventions — something customers can self-host rather than rent.
8. **Day-2 lifecycle done right.** Operators for every component, GitOps-driven updates, rolling patches without stopping production. The Siemens Amberg case study already establishes this pattern; the reference extends it to physical AI.

Each of these appears in the Showcase Console and can be pulled up on-demand during any customer conversation.

## Audience segmentation

Three customer archetypes drive the design. The same showcase must serve all three without ever feeling mismatched.

### Archetype A — "What is Omniverse?"

The customer is early. They've heard the term, seen a glossy industrial-metaverse video, and are trying to understand whether this is relevant to their operations. Their question is conceptual, not technical.

- **What they need**: a clear visual of what physical AI *is* when it's running; an intuitive sense of the problem it solves; a reason to believe Red Hat is a credible part of the conversation.
- **What we give them**: a 5-minute scripted demo loop showing the warehouse twin, robots moving, analytics overlays, and Red Hat's hybrid story in background.
- **Success**: they walk away understanding Omniverse+Mega as a category, knowing Red Hat is a serious player, and wanting a follow-up.

### Archetype B — "We're evaluating / piloting."

The customer has done the research. They've read NVIDIA's blueprints, perhaps run an Isaac Sim tutorial. They're trying to understand how Red Hat specifically adds value versus running on DGX Cloud or a cloud hyperscaler.

- **What they need**: an architecture-level conversation that maps Mega components to Red Hat substrate; concrete differentiation on hybrid/edge/security; references.
- **What we give them**: a 20-minute architecture walkthrough driven from the Showcase Console, with differentiators surfaced contextually, plus access to the public reference repo for their team to explore.
- **Success**: they can defend a choice to run the NVIDIA stack on Red Hat to their own leadership; they engage an SA or SI for a pilot.

### Archetype C — "Foxconn/Siemens-tier — already running pieces of the NVIDIA stack."

The customer already operates parts of the stack. They have internal expertise. They are not impressed by flashy visuals; they want to know what Red Hat changes about the operational model they already have.

- **What they need**: a deep, verifiable, engineer-to-engineer case for switching their runtime substrate to Red Hat or extending it to new deployments; specific operational gaps Red Hat fills; day-2 lifecycle substance; real numbers.
- **What we give them**: a 60–90 minute deep dive with live access to the reference cluster, walk-throughs of the GitOps structure, the operator set, security posture, multi-site federation, edge rollout, and a complete public repo they can fork.
- **Success**: they pull down the repo, stand up a variant in their own lab within a week, and an engagement matures from there.

**Critically**: the Showcase Console must be the single tool that handles all three modes gracefully, with deliberate transitions between them. A sales rep in the room with Archetype A who suddenly realizes they're also talking to Archetype C (the engineer their AE brought along) must be able to switch depths without breaking stride.

## Non-goals (what this project is *not*)

To keep scope defensible, explicitly *not* part of this effort:

- **A replacement for Mega**. We implement Mega, we don't fork it. When NVIDIA releases updates to the blueprint, we adopt them. Our value is the substrate, not the blueprint.
- **A replacement for NVIDIA's models**. Cosmos and GR00T are ours to serve, not to rebuild.
- **A productized SaaS offering**. This is reference material. Productization may follow but is a separate effort.
- **A tour of every NVIDIA Omniverse use case**. We focus on Mega (industrial fleets). DSX (AI factories) and medical (Isaac for Healthcare) are adjacent and worth noting in talk tracks, but not implemented here.
- **A Siemens Xcelerator integration — yet**. Siemens-specific work is Phase 4+ and gated on the reference being mature first.
- **A humanoid hardware robotics lab**. The Unitree G1 lives in sim for the showcase. A physical G1 may be added later (see `09-risks-and-open-questions.md`); it's not a blocker.
- **A broad review of agentic frameworks**. LangGraph is the choice. Evaluating alternatives is not in scope.

## Success criteria

The project succeeds when:

1. A Red Hat seller can walk into any industrial-AI meeting, open the Showcase Console, and run a compelling session at any of the three audience depths without prior setup.
2. A Red Hat field SA can stand up the reference in a customer's own OpenShift cluster within a documented time budget (target: under one engineering-week).
3. A customer engineer who forks the public repo can deploy a functional subset of the stack in their own lab within one day using published quickstarts.
4. Every Mega blueprint component is represented, verifiably running, and documented.
5. The sim-to-real loop works end-to-end: a policy can be trained in sim, registered, validated in sim, promoted, and deployed via GitOps to a MicroShift edge target.
6. The multi-site story works: ACM federates at least two simulated "factory" clusters and can deploy coordinated changes.
7. The reference passes a security review substantial enough to be credible for regulated industry conversations (supply chain signed, SBOMs present, STIG profile applied to host nodes).
8. The Showcase Console is used — in recorded sessions with real sellers as proof — and generates meeting outcomes that existing generic decks don't.

## Primary references

This project tracks several evolving NVIDIA and Red Hat reference points:

**NVIDIA (Physical AI stack)**
- Mega Omniverse Blueprint — https://build.nvidia.com/nvidia/mega-industrial-digital-twin
- Omniverse modular libraries (GTC 2026): `ovrtx`, `ovphysx`, `ovstorage` — NVIDIA Technical Blog
- Omniverse Kit App Streaming (Kubernetes-native) — NVIDIA docs
- Isaac Sim 6.0 + Isaac Lab 3.0 on Newton 1.0 physics — NVIDIA developer docs
- Cosmos Predict 2.5 / Cosmos Transfer — NVIDIA NGC / NIM catalog
- GR00T N1.7 — Hugging Face + NVIDIA NGC
- Metropolis Video Search & Summarization blueprint — NVIDIA AI Blueprint catalog
- Omniverse MCP servers + NemoClaw integration — NVIDIA Technical Blog, April 2026

**Red Hat (substrate)**
- Red Hat OpenShift 4.x + Virtualization
- Red Hat OpenShift AI (Early Access with MLflow)
- Red Hat Advanced Cluster Management
- Red Hat Device Edge / MicroShift
- Red Hat Ansible Automation Platform
- Red Hat Enterprise Linux for NVIDIA (H2 2026; design should anticipate this)

**Reference customer narratives** (used in talk tracks, not dependencies)
- Siemens Amberg (existing Red Hat OpenShift customer; industrial Xcelerator stack is first to support Mega)
- Foxconn Fii (NVIDIA Blackwell production + Mega adoption)
- BMW Debrecen (FactoryExplorer on Omniverse Kit SDK)
- KION + Accenture (first Mega adopter for warehouse)
- Caterpillar (Omniverse digital twins + Nemotron voice AI on Jetson Thor)
