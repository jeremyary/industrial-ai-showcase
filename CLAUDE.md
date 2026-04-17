# Claude Code project conventions

This file is read automatically at the start of any Claude Code session in this repository. It is the persistent context that keeps work coherent across sessions and engineers.

## Project mission in one sentence

Build the reference implementation of NVIDIA's Mega Omniverse Blueprint on Red Hat OpenShift, plus the sales-enablement artifacts that let Red Hat walk into any industrial-AI conversation as a first-class partner.

## Hard constraints you must respect

- **Hub cluster is OpenShift Dedicated (OSD); we have `cluster-admin`.** This is an internal Red Hat OSD instance, not a customer cluster. Cluster-admin access removes most of the operational restrictions customers face on OSD, but a few realities persist:
  - **MachineConfigs on OSD are fragile.** SRE's automation manages the underlying infrastructure, and custom MachineConfigs can be overridden, reverted, or cause conflicts. Treat MachineConfig-dependent work (STIG profiles, FIPS toggles, IOMMU, kernel tuning) as **companion-cluster work by default** unless there's a specific reason to test on OSD.
  - **GPU / node provisioning** is SRE-managed cloud infrastructure, not a customer-authored MachinePool. Additional GPU nodes go through SRE.
  - **OpenShift Virtualization availability on this specific OSD instance** is TBD — check before assuming. If it's available on OSD with cluster-admin, great; if not, the companion cluster hosts the vGPU workstation story.
  - **Cluster-scoped admission controllers** (`policy.sigstore.dev`), **custom SCCs**, **cluster-wide resources**, and **operator installs** are all fine — cluster-admin clears the way.
  - See ADR-017 for the companion-cluster strategic rationale (proof of the self-managed customer story, not forced by OSD limits).
- **GPU budget is two classes, pod-per-GPU across both**:
  - 2–3 × NVIDIA **L40S** (48 GB each) — ray-traced sim, physics, training, large-model serving.
  - 2–3 × NVIDIA **L4** (24 GB each) — inference, agent brains, VSS, embeddings, small NIMs.
  - No MIG, no time-slicing, no vGPU splitting.
  - **GPU class selection uses the GPU Operator's native GFD labels — do not introduce custom labels.** Workloads pin with `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L40S }` or `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L4 }`, together with `nvidia.com/gpu: 1` in resource limits. NFD + NVIDIA GPU Operator apply these labels automatically on both node classes; no SRE ticket needed for labeling.
  - See `docs/08-gpu-resource-planning.md` before adding any GPU workload.
- **Deployment target is OpenShift**. Not vanilla Kubernetes, not minikube. All manifests use OpenShift primitives (Routes, SecurityContextConstraints, Projects, Operators) where appropriate. OperatorHub is the default installation method for anything that has an operator.
- **GitOps-first**. Nothing is `oc apply`'d by hand into the cluster in long-lived state. Argo CD reconciles from this repo. See `infrastructure/gitops/` for the hub + companion + spoke layouts.
- **Air-gapped must remain possible**. Every external dependency (container image, chart, model) must be mirrorable. Don't introduce components that require live internet access at runtime without an offline path documented. **Air-gap validation happens on the companion cluster, not on OSD** — OSD is inherently internet-adjacent as a Red Hat-managed service.
- **Nucleus is already operational** on OpenShift from prior work. Treat it as a pre-existing dependency, not something to re-build. When adding new Nucleus-adjacent services, reuse the existing deployment pattern.
- **NVIDIA GPU Operator is already installed** on the OSD hub, with GFD labels in place. Don't re-install; validate the existing ClusterPolicy and build on it.
- **Red Hat OpenShift AI 3.4.0 EA1 is already installed** on the OSD hub with all components enabled including `trainer` (Kubeflow Training Operator). Don't re-install RHOAI; Phase 1 validates and configures what's present.

## Preferred technologies (already chosen — don't re-litigate)

- **Observability for LLM/agentic workloads**: MLflow (shipped as `rhoai/odh-mlflow-rhel9:v3.4.0-ea.1` with RHOAI 3.4 EA1 — ADR-015). Do not introduce Langfuse alongside.
- **Model serving**: vLLM via KServe.
- **Agentic framework**: LangGraph (ADR-005) as the orchestration framework. **Llama Stack (ADR-019) wraps LangGraph** as the governance layer for HIL tool-call approval, guardrails, and PII detection on Loop 4 agentic operations — starting Phase 3. Don't deploy Llama Stack in Phase 1; do design the agent-interaction surfaces with HIL in mind from day one.
- **MCP** for tool surfaces exposed to agents.
- **Messaging**: AMQ Streams (Kafka) for fleet events, missions, telemetry.
- **Service mesh**: OpenShift Service Mesh (Istio) for east-west zero-trust and observability.
- **Storage**: OpenShift Data Foundation for block + object; USD assets can also land in S3-compatible bucket via ODF's RGW.
- **Frontend**: React + TypeScript for the Showcase Console. PatternFly for Red Hat-consistent styling.
- **Primary humanoid in sim**: Unitree G1. Design for pluggable embodiments; other humanoids are Phase-4 overlay work.

## Decisions locked in

Before making changes that would contradict these, stop and ask the human:

- GR00T N1.7 is the primary VLA served, but the serving layer is architecturally model-agnostic. Plugging in Pi-0, OpenVLA, or a customer's fine-tuned model must always work without code changes outside a config.
- Siemens-specific partner integration is **explicitly out of scope** until Phase 4+ (gated on proving the reference works first).
- The sales-enablement Showcase Console is a **first-class deliverable**, not an afterthought. It starts skeletal in Phase 1 and grows every phase.

## Coding conventions

- **Python** for agentic code, ML tooling, and backend services. Type hints required. `ruff` + `mypy` in CI.
- **Go** for operators and controllers if any are written from scratch. Kubebuilder for scaffolding.
- **TypeScript** for Showcase Console front- and back-end. Vite + React on the front, Fastify on the API side.
- **Helm** for deployable components; use umbrella charts sparingly — prefer one chart per component with ApplicationSets composing them.
- **Kustomize overlays** are allowed for environment variance (dev / demo / prod), but chart values are preferred for component configuration.
- **YAML manifests**: stable field order, comments for non-obvious choices. Use `yq` in scripts.
- **Shell**: `bash` with `set -euo pipefail`. Anything longer than ~50 lines should be Python or Ansible instead.

## Git conventions

- Trunk: `main`. Release branches only if we cut formal versions (unlikely pre-1.0).
- Every change is a PR. PR titles use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
- PRs must link to the phase + workstream from `docs/04-phased-plan.md` they advance.
- Signed commits required (DCO sign-off minimum; Sigstore preferred).
- Every container image produced by this repo is Sigstore-signed in CI.
- SBOMs generated per image (Syft → SPDX JSON) and stored alongside the image.

## Before you start writing code

Run this mental checklist:

1. **Have you read the relevant docs?** At minimum `00-project-charter.md`, `01-architecture-overview.md`, and the component-catalog entry for what you're touching.
2. **Is there already a decision recorded?** Check `docs/07-decisions.md` before introducing new choices. Pay specific attention to ADR-017 (OSD + companion), ADR-018 (GPU class targeting via GFD labels), and ADR-019 (Llama Stack HIL wrapping).
3. **Does this workload belong on OSD hub or the companion cluster?** Anything needing MachineConfig, FIPS toggle, OpenShift Virtualization (if unavailable on this OSD), or true air-gap validation belongs on companion. Everything else defaults to hub.
4. **Does this respect the GPU budget?** If it adds a GPU workload, it needs an entry in the GPU scheduling doc — including which class (L40S or L4) it targets and why. Use `nvidia.com/gpu.product` selectors, not custom labels.
5. **Does this have an offline path?** If a user in an air-gapped environment couldn't install this, reconsider.
6. **Will this need a talk-track update?** If a customer-visible behavior changes, the sales enablement docs likely need updating too.

## Asking for human input

If any of the following come up, stop and surface the question rather than guessing:

- A decision that contradicts or would modify anything in `docs/07-decisions.md`.
- An introduction of a new preferred technology not listed above.
- A scope expansion beyond the current phase — especially anything that creeps toward the Siemens-specific Phase 4 work.
- A workaround that compromises the air-gapped deployability.
- A desire to apply a MachineConfig on the OSD hub (it likely belongs on companion — confirm).
- Anything that would require more than 2 L40S concurrently for the *demo* pathway (training pathways can be queued).
- A model selection that won't fit the L4 24 GB budget when a workload was slated for L4.

## Claude Code specific tips

- This repo is big. When asked to work on something, scope reads narrowly — don't load the whole repo into context unless necessary.
- When writing Helm values, always cite the upstream chart version you're targeting.
- When touching the Showcase Console, keep the audience-mode abstraction intact — every feature should declare which audiences it applies to.
- When writing tests, prefer integration tests against a Kind cluster to unit tests of deployment logic.
