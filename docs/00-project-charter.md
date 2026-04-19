# 00 — Project Charter

## Mission

Build a concrete, operationally credible end-to-end showcase of NVIDIA's Physical AI stack running on Red Hat OpenShift — driven by three scripted demos at three audience depths — and the sales-enablement stack that turns it into something Red Hat field teams can walk into a customer conversation with on no notice.

The project has two inseparable outputs:

1. A working, deployable, documented reference stack that substantiates Red Hat's claim to be a first-class substrate for industrial physical AI.
2. A sales-enablement layer — centered on the Showcase Console — that turns the reference into something Red Hat sellers and field engineers can actually wield in customer meetings of any duration and depth.

Neither half succeeds without the other. A gorgeous demo with no verifiable stack beneath it becomes PowerPoint. A flawless reference implementation no one can present becomes a GitHub repository nobody finds.

## Strategic framing

NVIDIA's consistent posture through GTC 2025 and GTC 2026 is: *here is the operating system for the $50T physical AI industry — run it on DGX / OVX / DGX Cloud.* The GTC 2026 announcements — Omniverse modular libraries (`ovrtx`, `ovphysx`, `ovstorage`), Kit App Streaming's Kubernetes-native CRDs and Helm charts, MCP servers for Omniverse — make the stack more cloud-native than ever, but NVIDIA still does essentially no work on the "how do you operate this across a heterogeneous hybrid fleet over five years" problem.

That is the seam Red Hat fits through. NVIDIA ships the Physical AI stack; Red Hat operationalizes it everywhere it has to run — including, critically, the on-prem factory datacenters, air-gapped defense sites, and robots themselves where the customer's actual work happens.

Every artifact this project produces is in service of that frame.

## The eight differentiators (the "value claims" we must substantiate)

These are the claims Red Hat makes in customer meetings that this reference has to back up with running code and deployable artifacts. `docs/sales-enablement/differentiator-mapping.md` maps each one to the specific industrial concern it addresses and which of the three demos surfaces it.

1. **On-prem and air-gapped are first-class.** Industrial customers with IP-sensitive factory twins, air-gapped defense sites, and regulated-manufacturing environments can't run production physical AI on public clouds. This stack must deploy identically on-prem and offline.
2. **One platform for containers, VMs, and vGPU workstations.** Legacy SCADA / PLC / HMI workstations coexist with modern containerized AI workloads on every real factory floor. OpenShift Virtualization + GPU Operator consolidates all three surfaces on a single cluster.
3. **Hybrid cloud → factory edge → robot, one operational model.** RHEL → OpenShift → Device Edge → MicroShift → bootable containers on Jetson. Same container image, signed once, deploys anywhere in the chain. ACM + Ansible + Argo CD federate the fleet.
4. **OpenShift AI as the MLOps backbone for "robot brains."** Training and fine-tuning of VLA variants, experiment tracking via MLflow, model registry with full lineage back to the sim episodes and synthetic-data batches that validated each policy version, serving via vLLM.
5. **OT-grade provenance, air-gap, and segmentation.** When AI models are commanding physical robots on a factory floor, supply-chain attestation is operational control, not checkbox compliance. Every model update, every policy change, every command crossing into OT networks carries cryptographic provenance back to the training run that produced it.
6. **Open model choice.** The Physical AI model ecosystem is moving fast. Customers may bring their own VLA, world model, or fine-tune from their own partnerships. The serving layer takes a model profile as configuration — swap the VLA, the rest of the architecture doesn't change.
7. **Agentic orchestration via MCP.** LangGraph agents on OpenShift AI operate the factory — not just infrastructure — calling MCP-wrapped tools for sim, fleet, and MLflow operations. Anything that changes physical state routes through Llama Stack's HIL gate. Customers self-host this rather than rent it.
8. **Day-2 lifecycle done right.** Operators for every component, GitOps-driven updates, rolling policy promotions across multi-site fleets without stopping the line, rollback in minutes when validation regresses. Factory uptime is the metric.

Each of these appears in the Showcase Console and can be pulled up on-demand during any customer conversation.

## Audience segmentation

Three customer archetypes drive the design. The same showcase must serve all three without ever feeling mismatched.

### Archetype A — "What is industrial physical AI?"

The customer is early. They've heard the terms, seen a glossy industrial-metaverse video, and are trying to understand whether this is relevant to their operations. Their question is conceptual, not technical.

- **What they need**: a clear visual of what physical AI *is* when it's running; an intuitive sense of the problem it solves; a reason to believe Red Hat is a credible part of the conversation.
- **What we give them**: a 5-minute scripted demo loop showing the warehouse twin, robots moving, event flow, and Red Hat's hybrid story in background.
- **Success**: they walk away understanding physical AI as a category, knowing Red Hat is a serious player, and wanting a follow-up.

### Archetype B — "We're evaluating / piloting."

The customer has done the research. They've read NVIDIA's materials, perhaps run an Isaac Sim tutorial. They're trying to understand how Red Hat specifically adds value versus running on DGX Cloud or a cloud hyperscaler.

- **What they need**: an architecture-level conversation that maps the physical-AI components to Red Hat substrate; concrete differentiation on hybrid/edge/security; references.
- **What we give them**: a 20-minute architecture walkthrough driven from the Showcase Console, with differentiators surfaced contextually, plus access to the public reference repo for their team to explore.
- **Success**: they can defend a choice to run the physical-AI stack on Red Hat to their own leadership; they engage an SA or SI for a pilot.

### Archetype C — "Foxconn/Siemens-tier — already running pieces of the NVIDIA stack."

The customer already operates parts of the stack. They have internal expertise. They are not impressed by flashy visuals; they want to know what Red Hat changes about the operational model they already have.

- **What they need**: a deep, verifiable, engineer-to-engineer case for switching their runtime substrate to Red Hat or extending it to new deployments; specific operational gaps Red Hat fills; day-2 lifecycle substance; real numbers.
- **What we give them**: a 60–90 minute deep dive with live access to the reference cluster, walk-throughs of the GitOps structure, the operator set, security posture, multi-site federation, edge rollout, and a complete public repo they can fork.
- **Success**: they pull down the repo, stand up a variant in their own lab within a week, and an engagement matures from there.

**Critically**: the Showcase Console must be the single tool that handles all three modes gracefully, with deliberate transitions between them. A sales rep in the room with Archetype A who suddenly realizes they're also talking to Archetype C (the engineer their AE brought along) must be able to switch depths without breaking stride.

## Non-goals (what this project is *not*)

To keep scope defensible, explicitly *not* part of this effort:

- **A replacement or fork of NVIDIA's frameworks.** We consume NVIDIA's Physical AI components (Omniverse, Isaac, Cosmos, VLAs, MCP servers) as upstream; when they release updates we adapt. Our value is the substrate, the orchestration, and the operations layer — not the physical-AI models themselves.
- **A replacement for NVIDIA's models.** Cosmos and NVIDIA's VLAs are ours to serve, not to rebuild. (Primary VLA is an open model per `docs/licensing-gates.md`; NVIDIA's VLAs slot in as pluggable alternatives.)
- **A productized SaaS offering.** This is reference material. Productization may follow but is a separate effort.
- **A tour of every NVIDIA Omniverse use case.** Focus is industrial fleet operations. DSX (AI factories), medical (Isaac for Healthcare), and other verticals are adjacent and worth noting in talk tracks; not implemented here.
- **A Siemens Xcelerator integration — yet.** Siemens-specific work is Phase 4+ and gated on the reference being mature first.
- **A humanoid hardware robotics lab.** The Unitree G1 lives in sim for the showcase. A physical G1 may be added later (see `09-risks-and-open-questions.md`); it's not a blocker.
- **A broad review of agentic frameworks.** LangGraph is the choice. Evaluating alternatives is not in scope.
- **USD scene authoring.** We use publicly-available scenes only (see `assets/README.md`). If a demo beat wants something that public assets can't support, the beat changes to fit what's available, not the other way around.

## Success criteria

The project succeeds when:

1. A Red Hat seller can walk into any industrial-AI meeting, open the Showcase Console, and run a compelling session at any of the three audience depths without prior setup.
2. A Red Hat field SA can stand up the reference in a customer's own OpenShift cluster within a documented time budget (target: under one engineering-week).
3. A customer engineer who forks the public repo can deploy a functional subset of the stack in their own lab within one day using published quickstarts.
4. Each of the three scripted demos runs end-to-end, on the live reference cluster, for its target audience depth.
5. The sim-to-real-capable loop works end-to-end: a policy can be trained in sim, registered, validated in sim, promoted, and deployed via GitOps to a MicroShift edge target (sim-to-real gate; the "real" side is VM-or-MicroShift-stand-in until physical hardware is in scope).
6. The multi-site story works: ACM federates at least two "factory" clusters and can deploy coordinated changes.
7. The reference passes a security review substantial enough to be credible for regulated industry conversations — framed as OT-grade provenance + air-gap + segmentation, not generic-Red-Hat-security checkboxes (see `docs/sales-enablement/differentiator-mapping.md` §5).
8. The Showcase Console is used — in recorded sessions with real sellers as proof — and generates meeting outcomes that existing generic decks don't.

## Primary references

This project tracks evolving NVIDIA and Red Hat reference points. These are upstream components we consume, not specifications we implement verbatim.

**NVIDIA (physical AI components we deploy on our substrate)**
- Omniverse Nucleus — USD asset substrate
- Omniverse modular libraries (GTC 2026): `ovrtx`, `ovphysx`, `ovstorage`
- Omniverse Kit App Streaming (Kubernetes-native)
- Isaac Sim 6.0 + Isaac Lab 3.0 on Newton 1.0 physics
- Cosmos Reason 2 — scene-reasoning VLM
- Cosmos Predict 2.5 / Cosmos Transfer 2.5 — world-foundation models (Phase 3)
- Nemotron 3 — mission-planner LLM
- Open VLAs (OpenVLA / pi-0 / SmolVLA) as primary; NVIDIA GR00T as pluggable alternative (see `docs/licensing-gates.md`)
- Omniverse MCP servers

**Red Hat (substrate)**
- Red Hat OpenShift 4.x + Virtualization
- Red Hat OpenShift AI
- Red Hat Advanced Cluster Management
- Red Hat Device Edge / MicroShift
- Red Hat Ansible Automation Platform
- Red Hat Enterprise Linux for NVIDIA (H2 2026; design should anticipate this)

**Reference customer narratives** (used in talk tracks, not dependencies)
- Siemens Amberg (existing Red Hat OpenShift customer; industrial manufacturing)
- Foxconn Fii (NVIDIA Blackwell production)
- BMW Debrecen (FactoryExplorer on Omniverse Kit SDK)
- KION + Accenture (warehouse autonomy)
- Caterpillar (Omniverse digital twins + Nemotron voice AI on Jetson Thor)
