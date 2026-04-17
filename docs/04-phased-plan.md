# 04 — Phased Plan

Five phases, ordered by dependency rather than calendar time. Each phase ends with a demoable state and a sales-enablement artifact. Phases are not expected to overlap except where noted.

## Phase 0 — Foundation

**Goal**: both clusters (OSD hub + self-managed companion) are fit for purpose. GitOps, operators, observability, storage, security baseline, and cross-cluster registration are all in place. Nothing application-level yet.

**Entry criteria**
- Hub OSD cluster is provisioned with 2–3 L40S and 2–3 L4 GPU nodes.
- Existing Nucleus deployment is identified and documented.
- NVIDIA GPU Operator is already installed on OSD hub (pre-existing).
- Red Hat OpenShift AI 3.4 is already installed on OSD hub (pre-existing).
- Companion cluster host is selected (GMKTec Evo-X2, ORIGIN PC, or dedicated lab box — see ADR-017).
- Git repository is initialized following `docs/06-repo-structure.md`.

**Work breakdown**

1. **Hub (OSD) validation and documentation**
   - Document hardware inventory, node labels, topology. Capture exact OSD version and MachinePool instance families in `infrastructure/baseline/osd-hub-state.md`.
   - Confirm the existing GFD labels on GPU nodes via `oc get nodes -l nvidia.com/gpu.present=true -o json | jq '.items[].metadata.labels'`. Capture the exact `nvidia.com/gpu.product` values (expected: `NVIDIA-L40S` and `NVIDIA-L4` — confirm exact strings). No custom labels are added; this is verification only.
   - Verify existing NVIDIA GPU Operator ClusterPolicy covers both L40S and L4; document driver versions.
   - Verify RHOAI 3.4.0 EA1 DataScienceCluster state; confirm component enablement (trainer is enabled per ADR-020 once drafted; spark is disabled per ADR-021 once drafted).
   - Smoke test: run a Job requesting `nvidia.com/gpu: 1` with `nodeSelector: nvidia.com/gpu.product=NVIDIA-L40S`, confirm it schedules on an L40S node and `nvidia-smi` reports correctly. Repeat for L4.
   - Check whether **OpenShift Virtualization** is available/installable on this OSD instance — document the finding. This answers a key open question in the component catalog for entry #4.

2. **Companion cluster provisioning**
   - Install self-managed OpenShift on the selected companion host (per OD-8; default path is GMKTec Evo-X2 with SNO).
   - Apply MachineConfig baseline: at minimum the STIG-aligned profile; FIPS-mode toggle if companion host supports it.
   - Install GPU Operator on companion if NVIDIA GPU present on the chosen companion host.
   - Install OpenShift Virtualization operator + HyperConverged CR on companion (unless OSD handles this — see item 1).
   - Document companion state in `infrastructure/baseline/companion-state.md`.

3. **Operator installs via OpenShift GitOps bootstrap (on OSD hub unless noted)**
   - Validate Node Feature Discovery is present (pre-existing alongside GPU Operator).
   - OpenShift Data Foundation — install if not present; otherwise use SRE-provided StorageClasses and note the delta.
   - OpenShift Pipelines (Tekton).
   - OpenShift Service Mesh v2 (control plane in `istio-system`).
   - OpenShift Logging (Loki) + LokiStack.
   - OpenTelemetry Operator + Tempo Operator.
   - Grafana Operator.
   - CloudNativePG.
   - Red Hat Advanced Cluster Management (hub-only install on OSD).
   - Ansible Automation Platform.
   - Streams for Apache Kafka (AMQ Streams) operator (installed in Phase 0; Kafka clusters instantiated in Phase 1).

4. **GitOps skeleton**
   - Argo CD installed via OperatorHub, targeting this repo's `infrastructure/gitops/` root.
   - ApplicationSet pattern established: one ApplicationSet per layer, with environment overlays.
   - Cluster directory pattern: `clusters/hub/`, `clusters/companion/`, `clusters/spoke-a/` (Phase 2), `clusters/spoke-b/` (Phase 2).
   - Root Applications defined for each of the above operators, reconciling their CRs.

5. **Security baseline**
   - **Hub (OSD, cluster-admin)**: Cosign keys generated (private in Vault; public in repo). `policy.sigstore.dev` admission controller installed in warn mode (graduates to enforce in Phase 1) — cluster-admin allows direct installation on OSD. Default deny-all NetworkPolicy in every workload namespace; allowlists per workload. Custom SCCs for workloads requiring them, reviewed for least privilege.
   - **Companion (self-managed)**: MachineConfig STIG profile applied. FIPS mode validated if applicable to companion host. `policy.sigstore.dev` in enforce mode — the companion-side baseline demonstrates the full recommended customer-deployable pattern where nothing is delegated to SRE.
   - Internal image registry: OpenShift internal registry on both clusters; quay.io mirror credentials via image pull secrets.

6. **Observability baseline**
   - User-workload monitoring enabled on OSD (cluster monitoring is SRE-managed; user workloads go through the user-workload-monitoring stack).
   - Thanos federation for cross-cluster metrics (hub ↔ companion at Phase 0; hub ↔ spokes added Phase 2).
   - Default Grafana instance with at minimum: cluster health, GPU utilization (DCGM), node health dashboards, and a "GPU class allocation" panel showing which workloads occupy which `nvidia.com/gpu.product` class.

7. **Multi-cluster registration**
   - ACM on OSD registers the companion cluster as a managed cluster.
   - Verify GitOps reconciliation reaches companion workloads via ACM's ApplicationSet delivery pattern.

8. **Documentation deliverables**
   - `docs/deployment/prerequisites.md` — hardware/software required for hub + companion.
   - `docs/deployment/cluster-setup.md` — the steps from pre-existing-OSD through companion provisioning to Phase 0 complete.
   - `infrastructure/gitops/README.md` — the Argo CD topology.
   - `infrastructure/baseline/osd-hub-state.md` and `companion-state.md` — living documents tracking actual installed versions.

**Exit criteria**
- Every installed operator on hub + companion is healthy and reconciled from Git.
- DCGM exporter shows all GPUs visible in Grafana, grouped by `nvidia.com/gpu.product`.
- A test Job using `nvidia.com/gpu: 1` and the appropriate `nvidia.com/gpu.product` nodeSelector runs successfully on both an L40S and an L4 node and reports the correct device via `nvidia-smi`.
- OpenShift Virtualization availability question for the OSD instance is answered and documented.
- ACM on OSD has registered the companion cluster; cross-cluster Argo CD Application reconciles to companion.
- A developer can bring up a clone of hub state using only what's in Git (plus documented out-of-band steps for secrets and any SRE-ticketed infrastructure provisioning).
- Companion cluster has MachineConfig STIG profile applied; FIPS-mode status documented.

**Phase 0 demo / artifact**
- Not a customer-facing demo. An internal one-pager: "OpenShift as the foundation for NVIDIA Physical AI — OSD hub + self-managed companion, L40S + L4 GPU pools, ready for workloads." Useful for early internal alignment conversations with field teams.

---

## Phase 1 — Mega Core

**Goal**: the NVIDIA Mega blueprint is implemented on OpenShift in its core shape. The operational inference loop (Loop 1) works end-to-end. A first scripted demo is possible. The Showcase Console exists in skeletal form.

**Entry criteria**
- Phase 0 complete.
- Nucleus operational and accessible from new namespaces.

**Work breakdown**

0. **RHOAI MLflow enablement and configuration**
   - Inspect the existing RHOAI 3.4 EA1 DataScienceCluster on the hub; confirm MLflow component state.
   - Enable the MLflow component in the DSC if not already active. The shipped container is `rhoai/odh-mlflow-rhel9:v3.4.0-ea.1` (per ADR-015).
   - Configure the MLflow backend: Postgres via CloudNativePG in a dedicated namespace; S3-compatible artifact store (ODF RGW or OSD-equivalent).
   - Establish the `workloads/common/python-lib/tracking/` abstraction so downstream code is insulated from RHOAI-internal MLflow details.
   - Document the final enabled configuration in `workloads/mlflow/README.md`.

1. **Nucleus validation and codification**
   - Formalize the existing Nucleus deployment as a chart in `workloads/nucleus/`.
   - Argo CD syncs Nucleus state henceforth (stop hand-managed drift).
   - Expose Nucleus as a Service Mesh member; enforce mTLS for consumers.

2. **USD Search API**
   - Deploy NVIDIA's USD Search API Helm chart to a dedicated namespace.
   - Configure backend against Nucleus.
   - Index an initial set of assets (warehouse scene, Nova Carter, Unitree G1, sensor library).

3. **Isaac Sim headless runner**
   - Build and publish an Isaac Sim 6.0 runner container image based on `nvcr.io/nvidia/isaac-sim`, baked with custom startup scripts and the warehouse scenario pack.
   - Sign the image (Cosign). Generate SBOM.
   - Deploy as a Deployment (not Job) for the "live demo sim" pod. Another pattern (Job-based) arrives in Phase 2 for training.

4. **Kit App Streaming**
   - Deploy the NVIDIA Kit App Streaming Helm charts.
   - Build a minimal Kit app ("Factory Viewer") that loads the warehouse USD scene from Nucleus and streams to web clients.
   - Expose via Route (WebRTC signaling + streaming).

5. **Kafka (AMQ Streams)**
   - Deploy 3-broker Kafka cluster.
   - Define topics: `fleet.events`, `fleet.missions`, `fleet.telemetry`, `fleet.ops.events`.
   - Schema Registry deployed; Avro schemas from `workloads/fleet-manager/schemas/`.

6. **Metropolis VSS**
   - Deploy the VSS blueprint Helm charts.
   - Configure input: RTSP streams from the Isaac Sim live sim's simulated cameras.
   - Configure output: Kafka `fleet.events` topic.

7. **Fleet Manager (v1)**
   - Python + FastAPI service. Consumes `fleet.events`, emits `fleet.missions`.
   - Decision policy for v1 is rule-based (not agentic yet). Upgrades to LangGraph-based in Phase 3.
   - Persist state to Postgres.

8. **Mission Dispatcher (v1)**
   - Python service. Consumes `fleet.missions`, calls robot-brain endpoints via gRPC.
   - Emits execution events to `fleet.ops.events`.

9. **WMS Stub**
   - Simple mock service emitting scripted mission streams; used to drive deterministic demo scenarios.

10. **Robot Brain serving (v1 — GR00T primary)**
    - vLLM runtime deployed as a KServe ServingRuntime.
    - GR00T N1.7 served as an InferenceService with a custom preprocessing handler for robot observations.
    - Pi-0 and OpenVLA configured as alternative InferenceService definitions but not active by default.

11. **Showcase Console (skeletal)**
    - React + TypeScript front-end, Fastify + TypeScript back-end.
    - Embeds the Kit App Streaming viewport.
    - Shows a single scripted demo path: "Warehouse — Baseline."
    - Audience-mode toggle present in UI but all modes currently show the same content (enriched in later phases).
    - Has a dashboard panel pulling from the sales-view Grafana dashboard.

12. **First scripted demo**
    - "Warehouse — Baseline" scenario pack: 5-minute narrated walk-through, with a recording cached locally for offline fallback.
    - Script documented in `demos/warehouse-baseline/script.md`.

**Exit criteria**
- The operational inference loop (Loop 1) runs end-to-end from simulated camera through VSS through Fleet Manager through GR00T-served robot brain through a sim robot.
- A sales rep can open the Showcase Console, click "Warehouse — Baseline," and walk through a 5-minute demo.
- The reference is deployable in its current shape from scratch using the documented GitOps bootstrap.

**Phase 1 demo / artifact**
- "Warehouse — Baseline" 5-minute demo (live + recorded).
- Architecture poster showing Mega components mapped onto Red Hat substrate, with Phase-1 components highlighted.
- One-pager: "Red Hat implementation of NVIDIA Mega — what we've built."

---

## Phase 2 — MLOps, Edge Loop, and Multi-Site

**Goal**: the policy training/promotion loop (Loop 2) works end-to-end. The edge layer exists and can receive deployments from ACM. Multi-site federation with at least two spokes is demonstrable.

**Entry criteria**
- Phase 1 complete.
- RHOAI 3.4 MLflow availability resolved per ADR-015 (either enabled in-product or a standalone fallback running).

**Work breakdown**

1. **OpenShift AI configuration for MLOps workflows**
   - DataScienceCluster CR already present (Phase 0 validated). Phase 1 enabled MLflow if needed.
   - Configure MLflow backend: Postgres (CNPG) + S3 artifact store (ODF or OSD-equivalent S3).
   - Configure model registry.
   - Build notebook server image with Isaac Lab dependencies.

2. **Isaac Lab training pipeline**
   - Kubeflow Pipeline that:
     - Accepts a scenario manifest + hyperparameters
     - Launches Isaac Lab training as a parallel Job set
     - Streams metrics to MLflow
     - Produces a candidate policy checkpoint
     - Runs evaluation against a curated scenario set
     - Registers in MLflow Model Registry with full lineage

3. **Policy serving update flow**
   - Kustomize overlay generator that produces a new serving InferenceService manifest from an MLflow model URI.
   - PR-based promotion workflow; Argo CD reconciles on merge.
   - Rollback via `git revert` documented.

4. **Edge layer: MicroShift targets**
   - Ansible playbooks for provisioning MicroShift on x86 VMs (representing edge) or Jetson hardware if available.
   - Bootable-container image build: one image signed once, deploys identically to hub workload or edge.
   - GitOps spoke pattern: edge nodes register to ACM, receive workloads via ManifestWork.

5. **ACM multi-site**
   - Register at least two spoke clusters (SNO instances).
   - Define a Mega policy that federates: Nucleus read-only replica at each spoke, local Fleet Manager slice, local VSS deployment scaled to spoke size.
   - Policy-based rollout of a new robot-brain version to Spoke A first, observe, promote to Spoke B.

6. **Enhanced observability**
   - MLflow integration with the Showcase Console data-scientist view.
   - Multi-site dashboards (Thanos federation).
   - OpenTelemetry traces spanning hub → spoke for mission round-trips.

7. **Showcase Console grows**
   - Audience modes now differentiate: novice shows simplified, expert shows architecture overlay and lineage panels.
   - New scripted path: "Warehouse — New Policy Rollout" (20-minute demo).
   - New scripted path: "Warehouse — Bottleneck and Recovery" (20-minute demo).

8. **Second scripted demo: 20-minute architecture walkthrough**
   - Script documented in `demos/20-min-architecture/script.md`.

**Exit criteria**
- A policy trained in Isaac Lab can be promoted through MLflow and deployed to the hub + two spokes via GitOps without any manual kubectl commands.
- Loop 2 is demonstrable live.
- The Showcase Console drives a 20-minute architecture-level conversation cleanly.
- The edge layer receives a robot-brain serving image that originated from the hub build pipeline.

**Phase 2 demo / artifact**
- 20-minute architecture demo.
- A recorded "fully operationalized MLOps for physical AI" reel (~8 minutes) suitable for YouTube/LinkedIn.
- Detailed architecture white paper suitable for sharing with prospective customers (drawn from the docs in this repo, with an executive summary).

---

## Phase 3 — Agentic Orchestration and Synthetic Data Factory

**Goal**: the agentic orchestration loop (Loop 4) works end-to-end. Synthetic data generation via Cosmos is operational and integrated with the training pipeline.

**Entry criteria**
- Phase 2 complete.
- Cosmos NIMs are accessible (NGC licensing resolved).

**Work breakdown**

1. **Cosmos Predict 2.5 NIM deployment**
   - As a KServe-wrapped Deployment on the hub.
   - Document GPU scheduling (this is a large model; coordinate with live-demo GPU allocation — see `docs/08-gpu-resource-planning.md`).

2. **Cosmos Transfer NIM deployment**
   - Same pattern; generally not concurrent with Cosmos Predict in the reference footprint.

3. **Synthetic-data pipeline**
   - Kubeflow Pipeline that orchestrates Cosmos Predict → Cosmos Transfer → scenario manifest generation → upload to Nucleus → registration in an MLflow dataset registry.

4. **MCP servers**
   - `mcp-isaac-sim`: Python-based MCP server wrapping Isaac Sim control operations.
   - `mcp-fleet`: wraps the Fleet Manager API.
   - `mcp-mlflow`: wraps MLflow REST + model registry operations.
   - `mcp-nucleus`: wraps Nucleus operations.
   - Each server deployed as its own workload, secured by Service Mesh.

5. **LangGraph agentic orchestrator**
   - Python service using LangGraph.
   - Agent brain: vLLM-served model sized for L4 by default (see OD-5); use LLM Compressor if stronger-but-larger candidate needs to fit.
   - Tool access exclusively via MCP servers above.
   - State persistence to Postgres.

6. **Llama Stack governance layer (ADR-019)**
   - Enable Llama Stack component in the DSC.
   - Configure Llama Stack's Agents API to front the LangGraph orchestrator: tool calls that modify state (fleet interventions, scenario launches, model promotions) route through HIL approval; read-only tool calls bypass.
   - Enable safety guardrails + PII detection on agent inputs and outputs.
   - Wire TrustyAI evaluation signal into observability.
   - Showcase Console agent panel surfaces the HIL approval UX — operator taps approve/reject before a state-modifying tool call executes.

7. **Fleet Manager upgrade (v2 — hybrid)**
   - Rule-based fast path (for standard missions) remains.
   - Agentic path for anomaly investigation: when an event scores above an anomaly threshold, dispatch to agentic orchestrator for deeper analysis and hypothesis generation. Investigation actions that propose fleet interventions route through Llama Stack HIL.

8. **Showcase Console grows**
   - Agentic interaction panel: natural-language command box, agent plan visualization, results panel, **HIL approval drawer** surfacing pending tool calls.
   - New scripted path: "Ask the system — what if we added 2 more humanoids to Zone B?" (60-minute deep dive segment).

9. **Third scripted demo: 60-minute technical deep dive**
   - Script documented in `demos/60-min-deep-dive/script.md`.
   - Includes live agent run, MLflow walkthrough, multi-site policy rollout, rollback, and security posture tour.

**Exit criteria**
- Loop 3 and Loop 4 are both demonstrable live.
- A customer engineer can issue a natural-language question through the Showcase Console and watch the agent compose and execute a sim experiment.
- Synthetic data produced via the pipeline can be used in a training run, and the resulting policy is traceable back to the synthetic scenarios that trained it.

**Phase 3 demo / artifact**
- 60-minute technical deep-dive demo with scripted agent runs.
- Blog post series (3+ posts) on the Red Hat Developer blog covering: the agentic pattern, the synthetic data factory, the multi-site MLOps story.

---

## Phase 4 — Verticalization and Partner Overlays

**Goal**: the reference becomes an enablement surface for partner-specific engagements. Industry vertical scenario packs exist. The Siemens conversation can begin with real artifacts to show.

**Entry criteria**
- Phase 3 complete.
- The reference has been exercised in at least three customer-facing engagements and received feedback.

**Work breakdown**

1. **"Electronics Manufacturing Line" scenario pack**
   - A new USD scene representing a surface-mount electronics line.
   - Scenario-specific fleet manager configuration, sensors, policies.
   - Showcase Console path for Foxconn/Pegatron-style conversations.

2. **"Automotive Subassembly" scenario pack**
   - A new scene representing a subassembly cell.
   - Variations demonstrating humanoid integration for parts picking.
   - Showcase Console path for BMW/Mercedes/Hyundai-style conversations.

3. **Siemens-specific overlay**
   - Adapter for Siemens Xcelerator platform integration (specifically Teamcenter X and Process Simulate).
   - Walk-through of how Siemens' Mega-compatible stack lands on top of the Red Hat reference.
   - Coordination with the existing Red Hat–Siemens account relationship (Amberg reference).

4. **Partner enablement package**
   - SI enablement curriculum — for Accenture, IBM Consulting, Deloitte.
   - Reusable Ansible collection for customer-site deployment.
   - Published case-study templates.

5. **Physical robot integration (optional)**
   - If hardware budget supports: a physical Unitree G1 integrated with the edge stack.
   - Sim-to-real policy transfer as the demo peak.

**Exit criteria**
- Three distinct vertical scenario packs work in the Showcase Console.
- The reference has documented integrations with at least one enterprise industrial platform (Siemens Xcelerator as the flagship).
- Partner SIs are actively delivering engagements built on this reference.

**Phase 4 demo / artifact**
- Vertical-specific 60-minute demos.
- Siemens joint-presentation materials (once that relationship has been opened).
- Red Hat Summit / GTC session materials showcasing real-customer outcomes.

---

## Cross-phase concerns

Some work is continuous, not phase-scoped.

- **Documentation**: every new component or data flow updates the relevant doc the same PR. Documentation rot is a bug.
- **Demos**: every phase produces a video recording of its flagship demo. Recordings land in `demos/<name>/recordings/`.
- **Testing**: integration tests for each loop land incrementally; end-to-end tests follow in Phase 2+.
- **Security**: Sigstore enforcement tightens from warn → enforce in Phase 1. FIPS mode test runs become continuous in Phase 2.
- **Talk tracks**: every phase's sales enablement artifact feeds back into the talk track doc (`docs/05-sales-enablement.md`). This is a living document.
