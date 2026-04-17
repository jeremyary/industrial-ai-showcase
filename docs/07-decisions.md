# 07 — Decisions (ADR log)

Architecture decisions recorded here. Each entry follows a lightweight ADR format: context, decision, consequences, status.

When a new material decision is made, add an entry. When a decision is superseded, mark the old one and add a new one.

---

## ADR-001: NVIDIA Mega Omniverse Blueprint as the canonical reference

**Status**: Accepted

**Context**: Choosing the organizing reference architecture for the showcase. Options considered: (a) a custom industrial-AI reference built from scratch, (b) NVIDIA's Mega Omniverse Blueprint, (c) NVIDIA's DSX Blueprint, (d) a broader "Omniverse Enterprise" generic reference.

**Decision**: We implement NVIDIA's Mega Omniverse Blueprint as the canonical reference and position Red Hat as its first-class enterprise substrate.

**Consequences**:
- Every customer conversation about Mega becomes a conversation where Red Hat has relevant substance.
- We are dependent on Mega's ongoing evolution; we adopt updates as they ship.
- We do not compete with Mega or propose an alternative; we implement it better operationally.
- DSX is deliberately out of scope as a primary reference but we may position OpenShift as relevant to DSX in talk tracks.

---

## ADR-002: Keep Nucleus for Phase 1; introduce `ovstorage` variant in Phase 2

**Status**: Accepted

**Context**: NVIDIA introduced modular libraries at GTC 2026, including `ovstorage` as a Kubernetes-native replacement for parts of Nucleus's functionality. Customers today are on Nucleus; the strategic direction is toward `ovstorage`.

**Decision**: The reference implements Nucleus first (Phase 1) because it matches the current customer install base. In Phase 2, we add an `ovstorage`-based variant as an alternate path. Both remain supported going forward.

**Consequences**:
- Customers currently on Nucleus have a clean migration story.
- Customers adopting `ovstorage` greenfield have a direct path.
- We carry a documentation burden of maintaining two patterns; this is an acceptable cost for customer optionality.

---

## ADR-003: GR00T primary; Pi-0 and OpenVLA as BYO alternatives

**Status**: Accepted

**Context**: The "robot brain" is a pivotal component. Choices: serve only GR00T, serve only open models, or serve GR00T with architectural BYO support.

**Decision**: GR00T N1.7 is the primary VLA served in the reference. The serving layer (vLLM + KServe) is architecturally model-agnostic; Pi-0, OpenVLA, and customer-fine-tuned models plug in through configuration without code changes outside a YAML.

**Consequences**:
- Default demos use GR00T, reflecting NVIDIA's flagship status in customer conversations.
- Customers concerned about model vendor lock-in see a concrete BYO path.
- Serving-layer code must remain model-agnostic; don't bake GR00T assumptions into the serving wrappers.

---

## ADR-004: MLflow (RHOAI Early Access) for experiment tracking and model registry

**Status**: Accepted

**Context**: Prior evaluation compared MLflow and Langfuse. Both have advocates. RHOAI Early Access ships with MLflow integrated.

**Decision**: MLflow is the single tracking and registry choice. Do not introduce Langfuse alongside.

**Consequences**:
- Simpler stack, one pane of experiment-tracking glass.
- Dependency on RHOAI's integrated MLflow build; revisit if RHOAI changes direction.
- If LLM-agentic observability (traditionally Langfuse's sweet spot) is needed, we lean on OpenTelemetry for agent traces instead.

---

## ADR-005: LangGraph as the agentic framework

**Status**: Accepted (see also ADR-019 for the Llama Stack wrapping pattern)

**Context**: The team has deep experience with LangGraph in other internal projects. Alternatives include CrewAI, AutoGen, LlamaIndex Agents, and raw LangChain.

**Decision**: LangGraph is the one agentic framework used in this reference.

**Consequences**:
- Consistent with team standards; existing patterns transfer.
- Agentic workflows are expressed as graphs; that mental model becomes part of the reference documentation.
- Llama Stack (ADR-019) wraps LangGraph for customer-facing governance (HIL, guardrails, PII detection) — the two compose rather than compete.
- If OpenClaw or similar frameworks mature, we evaluate them for interoperability, not replacement.

---

## ADR-006: OpenShift Service Mesh v2 (Istio-based) for east-west traffic

**Status**: Superseded by ADR-020

**Context**: Zero-trust and observability across many services are required. Options include OpenShift Service Mesh v2 (Istio), Service Mesh v3 if available, or no mesh with mTLS handled ad-hoc.

**Decision**: Service Mesh v2 is used from Phase 0.

**Consequences**:
- All workload namespaces participate via sidecar injection.
- We pay the complexity cost upfront; benefits (mTLS, tracing, traffic shaping) compound.
- Sidecar-based rather than ambient — revisit in a future ADR if ambient matures in Red Hat's offering.

**Superseded by ADR-020**: The 2026-04-17 hub baseline found Service Mesh 3 (the `sail-operator`-based Istio productization) already installed rather than v2. ADR-020 adopts Service Mesh 3 and preserves the sidecar-default posture this ADR established.

---

## ADR-007: AMQ Streams (Kafka) as the primary event bus

**Status**: Accepted

**Context**: Fleet events, missions, and telemetry need a durable, ordered, high-throughput event bus. Alternatives: AMQ Broker (JMS), NATS, RabbitMQ.

**Decision**: AMQ Streams (Kafka) is the single event-bus choice. MirrorMaker 2 federates hub ↔ spoke.

**Consequences**:
- Customers familiar with Kafka immediately recognize the pattern.
- Schema evolution governed via Schema Registry + Avro.
- Learning curve for teams new to Kafka; documented in component-level READMEs.

---

## ADR-008: Unitree G1 as the primary humanoid sim embodiment

**Status**: Accepted

**Context**: The reference includes a humanoid scenario. Options: NVIDIA-sampled models (GR1, H1), Unitree G1, Boston Dynamics Atlas (via public descriptions), Figure, 1X NEO. The choice affects USD asset quality, commercial availability (for eventual hardware use), and narrative breadth.

**Decision**: Unitree G1 is the primary humanoid in sim. Other humanoids (Agility Digit, Apptronik Apollo, Boston Dynamics Atlas) appear as secondary scenario variants as assets become available.

**Consequences**:
- Commercially purchasable if Phase 4+ wants hardware integration.
- Strong community interest and published references.
- Chosen despite GR00T being specifically trained/supported on multiple humanoids — the serving architecture is embodiment-pluggable so we can add others.

---

## ADR-009: Sigstore-based signing + SPDX SBOMs as the supply-chain posture

**Status**: Accepted

**Context**: Enterprise and regulated-industry customers expect a concrete supply-chain story. Options range from no signing, to GPG-signed RPMs only, to a full Sigstore/SPDX/SLSA story.

**Decision**: Every image built by this project is Cosign-signed; SBOMs in SPDX JSON generated with Syft; images carry SLSA provenance attestations; `policy.sigstore.dev` admission controller enforces signatures cluster-side.

**Consequences**:
- Phase 0 includes Sigstore infrastructure — not a "we'll do it later" topic.
- Third-party NVIDIA images are mirrored into our registry with annotations noting upstream signatures where present.
- This is a talking point for every security-conscious customer; supports the Archetype C expert conversation directly.

---

## ADR-010: Fleet manager stays vendor-neutral; integrations via adapters

**Status**: Accepted

**Context**: Real factories have specific WMS / MES / SCADA systems (SAP, Oracle, KION, rockwell). Options: bake in a reference integration to one system, stay vendor-neutral and provide adapter interfaces.

**Decision**: The fleet manager is vendor-neutral. Specific integrations (KION, SAP, Siemens) are adapters implementing a defined interface, added per customer engagement — not shipped in the core reference.

**Consequences**:
- The core reference doesn't privilege any specific partner.
- Accenture, IBM Consulting, Deloitte can deliver partner-specific adapters as engagement-specific value.
- WMS stub provides enough function for demos; real-system integrations are Phase 4 conversation starters.

---

## ADR-011: Multi-site from Phase 2, not optional

**Status**: Accepted

**Context**: The multi-site story is one of Red Hat's sharpest differentiators. It would be simpler to skip ACM federation in the reference and add it only in customer engagements.

**Decision**: Multi-site with at least two spokes is a Phase 2 deliverable, non-optional.

**Consequences**:
- Lab hardware budget must accommodate two spoke clusters (even if they're SNO VMs nested on the hub via OpenShift Virtualization).
- Demos that depend on multi-site become core, not bonus.
- If the federation doesn't work, we find out early rather than in a customer PoC.

---

## ADR-012: Omniverse Kit App Streaming over thick-client VDI for demo delivery

**Status**: Accepted

**Context**: Showing an interactive Omniverse Kit app during a demo requires either a thick-client workstation (local or VDI) or Kit App Streaming (browser-based WebRTC).

**Decision**: Kit App Streaming is the demo delivery path. Thick-client VDI is not part of the reference.

**Consequences**:
- No per-seller workstation setup required; any browser works.
- GPU usage: one L40S per active streaming session during demos. Schedule accordingly.
- Customer-facing stability depends on WebRTC + the Route configuration; document carefully.

---

## ADR-013: Showcase Console is a first-class deliverable

**Status**: Accepted

**Context**: The sales-enablement layer could be an afterthought (generic slides + pointing at the repo) or a first-class product deliverable (a purpose-built tool).

**Decision**: The Showcase Console is first-class — built from Phase 1, grown each subsequent phase, and treated as the primary interface between Red Hat field teams and customers.

**Consequences**:
- Engineering effort for the Console is non-trivial and must be budgeted.
- Every phase has a Console workstream.
- Sellers need training (the three-stage training path).
- Future hires for this project should include a frontend-capable engineer alongside the infrastructure and ML folk.

---

## ADR-014: Siemens Xcelerator integration is Phase 4, not earlier

**Status**: Accepted

**Context**: Red Hat already has a Siemens relationship (Amberg). The temptation is to lead with a Siemens-specific integration.

**Decision**: Siemens-specific integration waits until Phase 4. The reference must be proven first — multi-vertical, multi-scenario, production-credible — before approaching Siemens for joint artifacts.

**Consequences**:
- Phase 1–3 work is vendor-neutral and broadly applicable.
- The Siemens conversation, when opened, comes from a position of substance: "here's what we already built; let's integrate your Xcelerator stack" rather than "let's build something together."
- Other partner conversations (Foxconn Fii, KION, Accenture) may open in parallel during Phase 3–4.

---

## ADR-015: RHOAI 3.4.0 EA1 is the committed distribution; MLflow is shipped via `odh-mlflow-rhel9`

**Status**: Accepted

**Context**: Red Hat OpenShift AI 3.4.0 Early Access 1 is installed on the hub cluster. MLflow is shipped as a Red Hat-published container (`rhoai/odh-mlflow-rhel9:v3.4.0-ea.1`, Beta release phase) — available via the Red Hat Ecosystem Catalog. This closes what was a hedged-open question in earlier drafts of this ADR.

**Decision**: The reference runs on RHOAI 3.4.0 EA1 on the hub. MLflow is the committed tracking and model-registry layer, deployed via the Red Hat-published container. Phase 1 work verifies the component is enabled in the installed DataScienceCluster; if not enabled by default, we enable it via the DSC component toggle rather than falling back to a standalone community chart.

**Consequences**:
- No standalone MLflow Helm chart. The Red Hat container is the supported path.
- EA channel posture applies: no Red Hat support, no CVE backports, no supported in-place upgrade path to GA (moving to GA will require fresh install). See R-14.
- MLflow backend is Postgres via CloudNativePG; artifact store is an S3-compatible bucket (ODF or OSD-equivalent).
- The `workloads/common/python-lib/tracking/` abstraction remains in place so consumer code is insulated from future RHOAI-internal MLflow implementation changes.
- Additional RHOAI 3.4 EA1 components worth knowing about (Feature Store, Models-as-a-Service, LLM Compressor, Llama Stack) are addressed in their own ADRs or OD entries; this ADR is strictly about MLflow.

---

## ADR-016: Cosign + SBOM + SLSA — what "secure supply chain" means in this project

**Status**: Accepted (extends ADR-009)

**Context**: Supply-chain security is broadly scoped. This ADR locks the specifics of what we actually do.

**Decision**:
- **Signing**: Cosign keyless (Fulcio) when building in GitHub Actions; Cosign with Vault-stored private key when building in in-cluster Tekton.
- **SBOM**: Syft-generated SPDX JSON attached as an image attestation.
- **Provenance**: SLSA-style provenance attestation generated in CI; includes build environment, source commit, dependencies.
- **Verification**: `policy.sigstore.dev` admission controller on all clusters; policies require at least one valid signature from our identity.

**Consequences**:
- This is the concrete answer to "tell me about your supply chain" in every security conversation.
- CI complexity goes up; cost is acceptable.

---

## ADR-017: OSD hub with self-managed companion cluster — reasons for keeping the companion

**Status**: Accepted

**Context**: The hub cluster is an internal Red Hat OpenShift Dedicated (OSD) instance on which we hold `cluster-admin`. This is a favorable environment: most customer-facing OSD restrictions (namespace-scoped admission, restricted SCCs, managed operator catalogs) don't apply because cluster-admin clears them. However, three realities persist:

1. **MachineConfigs on OSD remain fragile.** Even with cluster-admin, SRE's infrastructure automation manages host state on OSD. Custom MachineConfigs for STIG profiles, FIPS toggles, kernel tuning, or IOMMU reconfiguration can be reverted or cause conflicts. Treating MachineConfig-dependent work as OSD-appropriate is risky.
2. **OSD is inherently internet-adjacent.** It's a Red Hat-managed service with egress to Red Hat's observability and subscription systems. Claiming "air-gapped" about an OSD cluster is misleading; serious air-gap validation needs an environment where we control every network egress.
3. **Customer-facing narrative demands self-managed substrate.** Real industrial customers run self-managed OpenShift in factory datacenters. The reference must demonstrate the full stack on that substrate, not just on managed OSD. Without a companion, the "Red Hat can do this on-prem" story is narrative rather than demonstrated.

**Decision**: The reference runs primarily on the OSD hub, and maintains a **self-managed companion cluster** for specific purposes that OSD cannot credibly serve regardless of permission level. The companion cluster:

- Hosts the MachineConfig-based hardening demonstrations (STIG profile, FIPS mode, kernel tuning) — work that would be fragile on OSD due to SRE's automation.
- Serves as the true air-gap validation environment where we control all egress.
- Provides the "customer parity" demonstration — the reference running on the same substrate a customer would run in their factory datacenter.
- Hosts OpenShift Virtualization + vGPU Kit workstations *if* that capability is unavailable on this specific OSD instance (TBD — verify early in Phase 0).

Everything else — Nucleus, Isaac Sim, GR00T serving, Cosmos NIMs, VSS, fleet manager, MCP servers, the LangGraph orchestrator, Llama Stack governance, the Showcase Console, ACM hub, cluster-scoped Sigstore admission, full NetworkPolicy mesh — runs on the OSD hub where cluster-admin makes it straightforward.

**Consequences**:
- The companion cluster is justified on merits (self-managed customer parity, MachineConfig safety, air-gap integrity) rather than forced by OSD permission limits.
- Phase 0 includes a "provision companion" work item, but its scope is narrower than an earlier draft assumed: MachineConfig work, air-gap test harness, and optionally OpenShift Virtualization.
- `infrastructure/gitops/clusters/` still has hub, companion, spoke-a, spoke-b — the topology is unchanged from earlier drafts.
- ACM on OSD manages the companion as a spoke; this is itself a useful demonstration of "Red Hat managing managed + self-managed OpenShift as one fleet."
- The talk track simplifies: "the reference deploys on any OpenShift substrate; we demonstrate it across managed (OSD) and self-managed footprints side-by-side." Honest and strong.
- Companion host selection remains OD-8. With the narrower scope, GMKTec Evo-X2 as the default host covers more of the companion's purpose (MachineConfig + air-gap) without needing an NVIDIA GPU; ORIGIN PC is only required if we specifically want to demonstrate vGPU Kit workstations and it's not available on OSD.

**Supersedes**: earlier drafts of this ADR that characterized OSD as heavily restricted and framed the companion as a forced workaround. Those assumptions were based on a dedicated-admin access model that doesn't apply here.

---

## ADR-018: GPU class targeting via GFD-provided `nvidia.com/gpu.product` labels

**Status**: Accepted

**Context**: The hub has 2–3 L40S nodes and 2–3 L4 nodes. Workloads need to target the right class. The NVIDIA GPU Operator's GFD (GPU Feature Discovery) component automatically applies `nvidia.com/gpu.product` labels — `NVIDIA-L40S` and `NVIDIA-L4` respectively — plus related labels like `nvidia.com/gpu.memory`, `nvidia.com/gpu.family`, and `nvidia.com/gpu.count`. NFD applies `feature.node.kubernetes.io/pci-10de.present=true` on any NVIDIA-GPU-bearing node.

An earlier draft of this ADR proposed introducing a custom `gpu-class=l40s | l4` label. That's worse: it duplicates information GFD already provides, creates drift risk on node replacement, and requires maintaining a parallel labeling pipeline.

**Decision**: Workloads target GPU class exclusively via the standard GFD labels:

```yaml
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-L40S   # or NVIDIA-L4
resources:
  limits:
    nvidia.com/gpu: 1
```

No custom labels. No taint+toleration layer on top — GFD's labels are the authoritative selector, and the existing GPU Operator `nvidia.com/gpu` resource request provides the GPU-requirement gate.

**L40S-targeted workloads** (use `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L40S }`):
- Omniverse Kit App Streaming render session
- Isaac Sim live demo instance
- GR00T N1.7 serving
- Cosmos Predict 2.5 NIM
- Cosmos Transfer NIM
- Isaac Lab training workers

**L4-targeted workloads** (use `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L4 }`):
- Metropolis VSS VLM
- LangGraph agent brain LLM (when selected model fits 24 GB)
- USD Search API embedding generation
- USD Code / USD Verify NIMs

**Consequences**:
- Zero custom labeling infrastructure. Labels survive node replacement automatically because GFD reapplies them.
- Selector strings are the canonical GPU product names — stable across GPU Operator versions for a given GPU model.
- The exact product-label string (`NVIDIA-L40S` vs `NVIDIA-L40S-XX` variants) must be confirmed during Phase 0 baseline capture via `oc get nodes -l nvidia.com/gpu.present=true -o json | jq '.items[].metadata.labels'` — document the exact strings in `infrastructure/baseline/osd-hub-state.md`.
- The Helm chart library in `workloads/common/chart-library/` exposes `gpuProduct` as a required value (not a free-form custom label) to force explicit choice at install time. The class-imbalance alert (Grafana) monitors for mis-scheduled workloads by correlating `kube_pod_spec_nodeSelector` with actual node `gpu.product` labels.
- Dev Mode A/B/C allocation (in `docs/08-gpu-resource-planning.md`) remains conceptually correct — the "L40S pool" and "L4 pool" are the two `nvidia.com/gpu.product` partitions of the cluster.

---

## ADR-019: Llama Stack as the HIL + safety layer around LangGraph-driven agents

**Status**: Accepted (Phase 3 workstream; scaffolding begins Phase 1)

**Context**: RHOAI 3.4 EA1 ships Llama Stack (upstream 0.3.5) with a distribution of capabilities relevant to our agentic orchestration story: Human-in-the-Loop tool-call approval, safety guardrails, PII detection, TrustyAI integration for evaluation, and a FIPS-compatible deployment pattern. LangGraph (ADR-005) remains the orchestration framework the team has standardized on.

For Loop 4 (agentic orchestration on physical-AI operations), the question is whether Llama Stack replaces LangGraph (it doesn't — ADR-005 holds), runs in parallel (messy), or wraps LangGraph as a safety and governance layer (the right answer). Real industrial customers will not allow LLM agents to modify fleet state without an operator approving the action; HIL is not optional for serious enterprise deployments of Loop 4.

**Decision**: LangGraph remains the orchestration framework (ADR-005 holds). Llama Stack is added as a **wrapping layer** around agent-initiated operations in Loop 4. Specifically:

- LangGraph graphs define the agent logic (what to plan, which tools to call, how to compose results).
- Llama Stack's Agents API provides the customer-visible interface for operator interactions — the HIL approval UX, guardrails on inputs and outputs, PII detection on any text the agent touches, audit trail integration.
- Tool calls that modify state (fleet interventions via `mcp-fleet`, scenario launches via `mcp-isaac-sim`, model promotions via `mcp-mlflow`) must pass through HIL approval unless explicitly allowlisted.
- Tool calls that are purely read-only (inspect fleet state, query MLflow, browse Nucleus) bypass HIL — no operator would want to approve every read.
- TrustyAI integration provides evaluation signal for agent outputs, feeding back into observability.

**Consequences**:
- Loop 4 becomes a two-layer stack: LangGraph (orchestration) + Llama Stack (governance). Slightly more complex than LangGraph alone; dramatically more defensible to enterprise customers.
- Phase 1 does not deploy Llama Stack. Phase 1's agentic elements are placeholders; real agentic work is Phase 3. But the Showcase Console's agent panel is designed from Phase 1 to accommodate HIL interactions when they come online.
- The HIL pattern itself becomes a differentiator to talk about — "Red Hat's posture is that LLM agents should ask operators before touching production" lands well with security-conscious customers.
- Llama Stack is FIPS-compatible in 3.4 EA1, which aligns with the companion-cluster FIPS story (ADR-017). Agentic demos for regulated customers can demonstrate the combination.
- OD-5 (agent brain model selection) gains a new criterion: the model must be compatible with Llama Stack's Agents API (most open-weight models with good tool-use are; check compatibility before committing).

---

## ADR-020: OpenShift Service Mesh 3 supersedes v2 for east-west traffic

**Status**: Accepted (supersedes ADR-006)

**Context**: ADR-006 chose OpenShift Service Mesh v2 (the Maistra-based Istio variant) for east-west traffic, with an explicit note that Service Mesh v3 was a valid option "if available."

Phase 0 Session 01 baseline capture (2026-04-17) found that **Service Mesh 3 is the version installed on the OSD hub** — `servicemeshoperator3.v3.3.1`, via the `stable` channel of the `redhat-operators` catalog. Service Mesh 3 is the Red Hat productization of upstream Istio built on the `sail-operator` pattern and supports both sidecar injection (the default) and ambient mode. It is not backward-compatible with v2 at the operator or CR level.

Installing v2 alongside v3 on the same cluster would be an anti-pattern: two control planes, conflicting sidecar injection webhooks, doubled operational cost. The pragmatic and strategically aligned choice is to honor what is installed.

**Decision**: OpenShift Service Mesh 3 (the `servicemeshoperator3` operator, currently `v3.3.1` on the hub) is the single mesh for east-west traffic. Sidecar injection remains the default workload-participation mode, preserving ADR-006's operational posture (mTLS, workload identity, east-west tracing). Ambient mode is evaluated per-workload as the reference matures; no blanket commitment either direction.

ADR-006 is superseded. All prior references to "Service Mesh v2" in the project docs should be read as "Service Mesh 3" going forward; a doc sweep happens naturally as Phase 0 sessions touch the affected files.

**Consequences**:

- All workload namespaces still participate via sidecar injection. Zero-trust posture from ADR-006 is preserved; Service Mesh 3 is a capability superset of v2, so nothing is lost.
- The CR topology differs from v2: `ServiceMeshControlPlane` (v2) → `Istio` + `IstioCNI` + `IstioRevision` + `IstioRevisionTags` (v3). Any mesh CRs in this repo must use v3 shapes from the start; there are none yet (pre-implementation), so no migration burden.
- Ambient mode becomes available as an option for workloads where sidecar overhead is costly — a live-demo Isaac Sim or Kit App Streaming pod with sidecar-induced GPU-adjacent latency is a plausible candidate. Any adoption of ambient-per-workload requires its own ADR so we don't drift into a mixed-mode posture by accident.
- FIPS compatibility is unchanged — Service Mesh 3 is FIPS-compatible, aligning with ADR-017 (companion) and ADR-019 (Llama Stack).
- Doc updates: `docs/01-architecture-overview.md`, `docs/04-phased-plan.md`, and any other file referencing "Service Mesh v2" get corrected as the Phase 0 session that lands mesh CRs touches them.

---

## ADR-021: MinIO operator for in-cluster S3 on OSD hub; ODF not installed here

**Status**: Accepted (first use: Session 03)

**Context**: Phase 1+ workloads need an S3-compatible object store — MLflow artifacts (ADR-015 called for "S3-compatible artifact store (ODF or OSD-equivalent)"), USD asset staging for Nucleus-adjacent services, future object consumers. The OSD hub runs on AWS Nitro instances with only AWS EBS-backed StorageClasses (`gp2`, `gp3`); no S3 endpoint exists in-cluster. Session 03 baseline confirmed no ODF / NooBaa / RGW / Ceph CRDs are present.

Installing ODF on cloud-managed OSD duplicates EBS block storage behind a Ceph layer whose storage substrate (local disks) doesn't match Nitro cleanly. ADR-015 already hedged "ODF or OSD-equivalent"; this ADR picks the OSD-equivalent.

**Decision**: Install the MinIO operator (`minio-object-store-operator`, Certified catalog) on **both** the OSD hub and the companion cluster once it comes online. MinIO tenants provide S3-compatible object storage backed by PVCs on the host's default StorageClass (`gp3` on hub; whatever the companion surfaces). **ODF is not installed anywhere in this reference.** One operational model across hub and companion is simpler than two, and MinIO tenants mirror cleanly to air-gapped customer sites where AWS S3 isn't reachable.

**Consequences**:
- MLflow artifact store (ADR-015) is a MinIO tenant bucket. No change to the `workloads/common/python-lib/tracking/` abstraction.
- USD asset bucket for Nucleus-adjacent services is a MinIO tenant. Keeps the `ovstorage` migration story (ADR-002) on the table — MinIO buckets are swappable for `ovstorage` without code change.
- Backup/DR for object content is PVC-level (EBS snapshots). Acceptable for a reference deployment; production customers bring their own backup story.
- Air-gap: MinIO tenant images mirror cleanly; compatible with customer sites where AWS S3 is unavailable.
- Companion cluster gets MinIO too (Session 12 installs the same Subscription); ODF is not revisited.

---

These are decisions we're aware of but not yet making — they're documented in `09-risks-and-open-questions.md` rather than being forced here.

- Physical hardware: do we buy a Unitree G1 for Phase 4 hardware integration?
- Console naming: "Showcase Console" vs "Forge" vs other — marketing decision.
- Companion cluster host (ADR-017): GMKTec Evo-X2 vs ORIGIN PC vs dedicated lab hardware — deferred to Phase 0 provisioning.
- ACM's replacement (if one emerges in Red Hat's roadmap): not a current concern.

---

## ADR template for future additions

```
## ADR-NNN: Title

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-MMM

**Context**: What problem does this decision address?

**Decision**: What is the decision?

**Consequences**: What follows from it, positive and negative?
```
