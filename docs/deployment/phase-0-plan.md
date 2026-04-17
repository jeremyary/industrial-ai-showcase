# Phase 0 Kickoff Plan — Session Backlog

This plan orders the remaining Phase 0 work (post–Session 01) into concrete Claude Code sessions. It is the backlog Session 02 onward works through in order, with explicit parallel tracks where the work is genuinely independent.

- **Source of truth for Phase 0 scope**: `docs/04-phased-plan.md` (Phase 0 section).
- **Baseline of current cluster state**: `infrastructure/baseline/osd-hub-state.md`.
- **Authoritative decisions**: `docs/07-decisions.md`. Pay attention to ADR-017, ADR-018, ADR-019, **ADR-020** (Service Mesh 3).

---

## Purpose

Session 01 delivered: repo scaffold, OSD hub baseline capture with OD-9 resolution, ADR-020 adoption of Service Mesh 3, and this backlog document. What remains is everything else Phase 0 requires to exit — GitOps, platform operators, mesh, RHOAI validation, observability, security baseline, companion provisioning, multi-cluster federation, and a final exit review.

Each session below is scoped to fit in a single Claude Code session with human supervision. Where a single phase item would clearly overrun a session (e.g. companion provisioning), it is split across numbered sub-sessions.

---

## Phase 0 exit criteria (from `docs/04-phased-plan.md`) — with Session 01 annotations

| Exit criterion | Satisfied by |
|---|---|
| Every installed operator on hub + companion is healthy and reconciled from Git. | Sessions 02 – 05 (hub), 11 – 12 (companion), 13 (cross-cluster apps). |
| DCGM exporter shows all GPUs visible in Grafana, grouped by `nvidia.com/gpu.product`. | Session 07 (baseline Grafana dashboards). |
| A test Job using `nvidia.com/gpu: 1` and the appropriate `nvidia.com/gpu.product` nodeSelector runs successfully on both an L40S and an L4 node and reports the correct device via `nvidia-smi`. | Session 06 for L40S immediately; L4 portion runs once L4 nodes are self-provisioned (Finding 1, `infrastructure/baseline/osd-hub-state.md`). |
| **OpenShift Virtualization availability question for the OSD instance is answered and documented.** | **Done in Session 01 (OD-9 resolved: installable but unusable on AWS Nitro; KubeVirt lives on companion per ADR-017).** |
| ACM on OSD has registered the companion cluster; cross-cluster Argo CD Application reconciles to companion. | Session 13. |
| A developer can bring up a clone of hub state using only what's in Git (plus documented out-of-band steps for secrets and any SRE-ticketed infrastructure provisioning). | Incrementally satisfied; validated in Session 15 (exit review). |
| Companion cluster has MachineConfig STIG profile applied; FIPS-mode status documented. | Session 11. |

---

## Parallel tracks

Three tracks run in parallel once Session 02 establishes GitOps bootstrap.

```
Session 01 (done)
   |
   v
Session 02  — GitOps bootstrap (blocks everything downstream)
   |
   +---> HUB TRACK:         03 -> 04 -> 05 -> 06 -> 07 -> 08
   |
   +---> COMPANION TRACK:   09 -> 10 -> 11 -> 12
   |                        (starts as soon as OD-8 is resolvable;
   |                         independent of hub track 03-08)
   |
   +---> (once both tracks reach their endpoints:)
         INTEGRATION TRACK: 13 -> 14 -> 15
```

The hub track and companion track **do not block each other** after Session 02. Hub track sessions 03 – 08 can run sequentially while companion track sessions 09 – 12 run in parallel with them. Integration sessions 13 – 15 need both tracks to have reached their respective endpoints.

---

## Session-by-session backlog

Every session is: **one feature branch, one PR, DCO-signed, `Co-Authored-by: Claude` trailer, Conventional Commits title**. Branch naming: `feat/p0-session-NN-<short-slug>`.

### Session 02 — GitOps bootstrap

- **Scope**: Install OpenShift GitOps (Argo CD) on the hub. Define the ApplicationSet pattern and seed the cluster directory structure under `infrastructure/gitops/clusters/hub/`. Bootstrap Argo CD from `infrastructure/gitops/bootstrap/`.
- **Deliverables**:
  - Subscription + Operator install manifests under `infrastructure/gitops/bootstrap/`.
  - Root ApplicationSet seeds, targeting `infrastructure/gitops/apps/`.
  - `clusters/hub/` layout populated with an initial `AppProject` and SSO integration if relevant.
  - `infrastructure/gitops/README.md` authored (currently absent; intentional per Session 01 cut).
- **Depends on**: Session 01.
- **OSD vs companion**: hub.
- **GPU workload?**: No.
- **Estimated sessions**: 1.

### Session 03 — Platform operators wave 1

- **Scope**: Install the "platform plumbing" operators — the boring-but-necessary layer that every application needs: storage, database, logging, tracing, dashboards.
- **Operators**: ODF (or document using SRE-provided StorageClasses + provision separate S3 via ObjectBucketClaim if possible), CloudNativePG, OpenShift Logging + LokiStack, OpenTelemetry Operator + Tempo Operator, Grafana Operator.
- **Deliverables**:
  - Subscription + per-operator CR manifests under `infrastructure/operators/{odf,cnpg,logging,otel-tempo,grafana}/`.
  - Argo CD Applications wiring them up under `infrastructure/gitops/apps/operators/` (convention to establish this session).
- **Depends on**: Session 02.
- **OSD vs companion**: hub.
- **GPU workload?**: No.
- **Estimated sessions**: 1–2. If ODF is not available and we fall back to OSD StorageClass + standalone S3 path, that adds complexity; split if needed.

### Session 04 — Service Mesh 3 control plane

- **Scope**: Install the Service Mesh 3 control plane per ADR-020 — `Istio` + `IstioCNI` + `IstioRevision` + `IstioRevisionTags` CRs. Establish the sidecar-injection convention for future workload namespaces. Deliberate choice not to enable ambient mode cluster-wide; ambient adoption per-workload needs its own ADR.
- **Deliverables**:
  - CRs under `infrastructure/operators/service-mesh/`.
  - Control plane namespace convention (e.g., `istio-system` for the `Istio` CR) documented.
  - Workload-namespace injection tag (e.g., `istio-injection: enabled`) convention in the chart library.
- **Depends on**: Session 02 (GitOps bootstrap). Independent of Session 03.
- **OSD vs companion**: hub. Companion mesh install is folded into Session 12 to keep companion-track overhead low.
- **GPU workload?**: No.
- **Estimated sessions**: 1.

### Session 05 — Orchestration operators

- **Scope**: Install the operators that orchestrate things rather than just sit there: ACM hub, AMQ Streams operator (Kafka clusters come Phase 1), Ansible Automation Platform.
- **Deliverables**:
  - Subscription manifests under `infrastructure/operators/{acm,amq-streams,aap}/`.
  - ACM `MultiClusterHub` CR on hub (managed-cluster registrations land in Session 13).
  - Argo CD Applications.
- **Depends on**: Session 03 (needs CNPG for AAP's Postgres, unless AAP ships its own).
- **OSD vs companion**: hub.
- **GPU workload?**: No.
- **Estimated sessions**: 1.

### Session 06 — RHOAI DSC validation + GPU smoke tests

- **Scope**: Validate the running RHOAI 3.4.0 EA1 DataScienceCluster matches expectations per `CLAUDE.md` and ADR-015. Run GPU smoke tests.
- **Deliverables**:
  - Confirmation test Jobs in `tests/smoke/gpu/` for each GPU class:
    - L40S: `nodeSelector: { nvidia.com/gpu.product: NVIDIA-L40S }` + `resources.limits.nvidia.com/gpu: 1`; runs `nvidia-smi`; passes.
    - L4: same pattern with `NVIDIA-L4` — **runs once L4 nodes are self-provisioned** (per Finding 1 of the baseline). If L4s are not present at session time, skip with a clearly noted TODO and come back to it when L4s land.
  - RHOAI DSC component matrix confirmation (re-run of the baseline Section 7 check; flag any drift).
  - MLflow backend wiring (Postgres via CNPG — needs Session 03; S3-compatible bucket via ODF or equivalent) — this is the remaining part of Phase 1 Work Item 0 per `docs/04-phased-plan.md`, pulled left since the DSC toggle is already Managed.
- **Depends on**: Session 03 (CNPG + storage).
- **OSD vs companion**: hub.
- **GPU workload?**: Yes — smoke-test only, L40S immediately, L4 pending.
- **Estimated sessions**: 1, plus a ~0.25-session re-visit once L4 nodes exist.

### Session 07 — Observability baseline

- **Scope**: Enable user-workload monitoring on OSD. Land the baseline Grafana dashboards (cluster health, DCGM GPU utilization grouped by `nvidia.com/gpu.product`, **GPU class allocation panel** that correlates `kube_pod_spec_nodeSelector` with actual node product labels to detect mis-scheduling per ADR-018). Land the Prometheus class-imbalance alert rule.
- **Deliverables**:
  - `ConfigMap/user-workload-monitoring-config` in `openshift-user-workload-monitoring`.
  - GrafanaDashboard CRs checked in under `infrastructure/observability/grafana-dashboards/`.
  - PrometheusRule CRs under `infrastructure/observability/prometheus-rules/`.
  - Tempo + Loki tenant configs in `infrastructure/observability/{tempo-config,loki-config}/`.
- **Depends on**: Session 03 (Grafana/Logging/OTel-Tempo operators present), Session 06 (DCGM exporter confirmed healthy).
- **OSD vs companion**: hub. Companion observability rolls in via Session 14 (Thanos federation).
- **GPU workload?**: Reads GPU metrics; does not run GPU workloads.
- **Estimated sessions**: 1.

### Session 08 — Hub security baseline

- **Scope**: Install `policy.sigstore.dev` admission controller in **warn mode** on the hub. Seed Cosign key material (public keys in Git under `infrastructure/security/sigstore/keys/`; private keys in Vault — Vault install itself is a prerequisite, see below). Author the default deny-all NetworkPolicy template in the chart library so every future workload namespace inherits it. Draft the custom SCC catalog (no SCCs applied yet; workloads bring their own SCC requirements Phase 1+).
- **Deliverables**:
  - Sigstore policy-controller Subscription + `ClusterImagePolicy` in warn mode.
  - Cosign public keys in `infrastructure/security/sigstore/keys/`.
  - Default deny-all NetworkPolicy template in the chart library.
  - Decision note on Vault: either install in-cluster HashiCorp Vault this session, or accept a deferred secrets story through Session 10 and use `ExternalSecrets` with a stub backend until then. Recommend in-cluster Vault now because Sigstore signing key storage benefits from it immediately.
- **Depends on**: Session 03 (cert-manager — already installed pre-Phase-0 per Session 01 baseline, so this is really just a confirmation).
- **OSD vs companion**: hub. Companion security (STIG, FIPS, Sigstore **enforce** mode) is Session 11.
- **GPU workload?**: No.
- **Estimated sessions**: 1 (slightly tight; split if Vault in-cluster is chosen).

### Session 09 — Companion cluster provisioning (OD-8 resolution + install)

- **Scope**: Resolve OD-8 (companion host selection among GMKTec Evo-X2, ORIGIN PC, or dedicated lab hardware). Install self-managed OpenShift on the selected host (SNO pattern for GMKTec; 3-node compact for others if hardware allows). Register access (kubeconfig; if remote, ngrok or equivalent exposure path documented).
- **Deliverables**:
  - OD-8 resolution noted in `docs/09-risks-and-open-questions.md`.
  - Installer artifacts / Assisted Installer ISO preserved under `tools/companion-install/` (create as needed).
  - Companion kubeconfig on the user's workstation; access path documented for future sessions.
  - Draft `infrastructure/baseline/companion-state.md` stub (populated properly in Session 10).
- **Depends on**: Can start in parallel with Session 02 — only user decision + physical/remote hardware action. Claude Code sessions support the installer workflow.
- **OSD vs companion**: companion.
- **GPU workload?**: Depends on host choice. GMKTec Evo-X2 has no NVIDIA GPU (Intel/AMD integrated); ORIGIN PC with NVIDIA GPU is the only companion option that enables vGPU Kit workstation demos.
- **Estimated sessions**: 2 — one for OD-8 + install; one for post-install validation.
- **Note**: this session can be partially async while the installer runs; reconvene Claude Code session once the companion API is reachable.

### Session 10 — Companion baseline capture

- **Scope**: Mirror of Session 01 for the companion cluster. Run equivalent `oc` commands; populate `infrastructure/baseline/companion-state.md` with node inventory, operator state, GPU inventory (if any), SCC posture, OCP Virt availability on companion (likely yes, since it's self-managed bare metal or close to it).
- **Deliverables**: `infrastructure/baseline/companion-state.md` living document.
- **Depends on**: Session 09.
- **OSD vs companion**: companion.
- **GPU workload?**: No; inventory only.
- **Estimated sessions**: 1.

### Session 11 — Companion security baseline (STIG + FIPS + Sigstore enforce)

- **Scope**: Apply the STIG-aligned MachineConfig profile (this is the substantive companion-only capability per ADR-017 — MachineConfigs are fragile on OSD). Validate FIPS mode if the companion host supports it. Install Sigstore policy-controller in **enforce mode** (stricter than hub's warn mode).
- **Deliverables**:
  - STIG MachineConfig manifests in `infrastructure/security/stig-machineconfig/`.
  - FIPS validation notes in `infrastructure/security/fips/` (empty today; populated this session).
  - Sigstore policy-controller config (enforce) under `infrastructure/security/sigstore/policy-controller/` targeted at companion via ApplicationSet.
- **Depends on**: Session 09, Session 10.
- **OSD vs companion**: companion.
- **GPU workload?**: No.
- **Estimated sessions**: 1–2.

### Session 12 — Companion OpenShift Virtualization + mesh

- **Scope**: Install OpenShift Virtualization on the companion per ADR-017 (this is where VM-based demos live). `HyperConverged` CR configured. If the companion host is ORIGIN PC with NVIDIA GPU, also configure vGPU (`NodeFeatureDiscovery` + GPU Operator + vGPU driver baked into MachineOSConfig or similar). Service Mesh 3 control plane on companion (mirror of Session 04).
- **Deliverables**:
  - KubeVirt operator Subscription + HyperConverged CR under `infrastructure/operators/openshift-virt/`.
  - vGPU configuration (if applicable) documented.
  - Service Mesh 3 CRs on companion under `infrastructure/operators/service-mesh/` with companion overlay.
- **Depends on**: Session 11.
- **OSD vs companion**: companion.
- **GPU workload?**: vGPU configuration if ORIGIN PC.
- **Estimated sessions**: 1–2 depending on vGPU complexity.

### Session 13 — ACM registration of companion; cross-cluster Argo CD

- **Scope**: Register companion cluster as a managed cluster under ACM on the hub. Verify a cross-cluster Argo CD Application reconciles to companion via ACM's ApplicationSet delivery pattern.
- **Deliverables**:
  - `ManagedCluster` + `ManagedClusterSet` + `Klusterlet` manifests.
  - Example Argo CD Application that reconciles to companion and is observable from the hub.
  - `docs/deployment/cluster-setup.md` chapter on multi-cluster federation.
- **Depends on**: Session 05 (ACM hub), Session 12 (companion fully up).
- **OSD vs companion**: both.
- **GPU workload?**: No.
- **Estimated sessions**: 1.

### Session 14 — Thanos federation + companion user-workload monitoring

- **Scope**: Enable user-workload monitoring on companion. Federate hub ↔ companion metrics via Thanos. Extend the baseline Grafana dashboards to differentiate per-cluster.
- **Deliverables**:
  - Thanos sidecar + querier config.
  - Hub Grafana datasource updated to query cross-cluster.
  - Dashboard variant with `cluster` selector.
- **Depends on**: Session 07 (hub observability), Session 13 (ACM federation live).
- **OSD vs companion**: both.
- **GPU workload?**: No.
- **Estimated sessions**: 1.

### Session 15 — Phase 0 exit review + one-pager

- **Scope**: Walk every Phase 0 exit criterion; confirm satisfied or document waiver. Produce the "OpenShift as the foundation for NVIDIA Physical AI" internal one-pager artifact (Phase 0 demo per `docs/04-phased-plan.md`). Pre-flight for Phase 1.
- **Deliverables**:
  - Exit checklist under `docs/deployment/phase-0-exit-review.md`.
  - One-pager under `docs/sales-enablement/one-pagers/phase-0-foundation.md`.
  - List of Phase 1 preconditions (e.g., L4 nodes present, NGC credentials configured, Nucleus deployment codified).
- **Depends on**: Sessions 02 – 14.
- **OSD vs companion**: both.
- **GPU workload?**: No.
- **Estimated sessions**: 0.5 (smaller than a typical session).

---

## Summary table

| # | Title | Depends on | Cluster | GPU class used | Est. sessions |
|---|---|---|---|---|---|
| 02 | GitOps bootstrap | 01 | hub | — | 1 |
| 03 | Platform operators wave 1 | 02 | hub | — | 1–2 |
| 04 | Service Mesh 3 control plane | 02 | hub | — | 1 |
| 05 | Orchestration operators (ACM, AMQ Streams, AAP) | 03 | hub | — | 1 |
| 06 | RHOAI DSC validation + GPU smoke tests + MLflow backend | 03 | hub | L40S (L4 pending) | 1 + 0.25 follow-up |
| 07 | Observability baseline | 03, 06 | hub | — | 1 |
| 08 | Hub security baseline (Sigstore warn, Vault, NetworkPolicy template) | 03 | hub | — | 1 |
| 09 | Companion provisioning (OD-8 + install) | (parallel with 02) | companion | — | 2 |
| 10 | Companion baseline capture | 09 | companion | — | 1 |
| 11 | Companion security (STIG, FIPS, Sigstore enforce) | 10 | companion | — | 1–2 |
| 12 | Companion OpenShift Virt + Service Mesh 3 | 11 | companion | vGPU if ORIGIN PC | 1–2 |
| 13 | ACM companion registration + cross-cluster Argo CD | 05, 12 | both | — | 1 |
| 14 | Thanos federation + companion monitoring | 07, 13 | both | — | 1 |
| 15 | Phase 0 exit review + one-pager | 02–14 | both | — | 0.5 |

Total: **14 sessions, roughly 14–18 session-weeks** depending on how the parallel tracks sequence.

---

## Preconditions the user manages (not Claude sessions)

These are user actions that do not map to Claude Code sessions; they gate or unblock specific sessions above.

- **L4 node self-provisioning**: user adds `g6.xlarge` (or equivalent) L4-bearing worker nodes directly when a session needs them. First session that requires L4: Session 06 (L4 portion of smoke tests), but the critical consumer is Phase 1 Metropolis VSS.
- **Companion host selection (OD-8)**: user decides GMKTec Evo-X2 vs ORIGIN PC vs dedicated lab hardware. This decision is made during Session 09.
- **NGC API key provisioning**: required from Phase 1 for pulling NVIDIA images. Not a Phase 0 gate, but land in Vault during Session 08 so it's ready.
- **Cosign signing identity**: user decides keyless (Fulcio in GitHub Actions) vs key-based (Vault-stored private key for in-cluster Tekton). ADR-016 allows both; Session 08 pins per-environment.
- **SRE tickets**: none required for Phase 0.

---

## Cross-cutting notes

- **Branch naming**: `feat/p0-session-NN-<slug>`. Example: `feat/p0-session-02-gitops-bootstrap`.
- **PR titles**: Conventional Commits (`feat:`, `chore:`, `docs:`, `fix:`, `refactor:`). Each PR links its phase + workstream.
- **Commit trailers**: `Co-Authored-by: Claude` (no model name, per `.claude/rules/ai-compliance.md`).
- **Every session starts with**: (a) read `CLAUDE.md`, (b) read the target session's entry in this file, (c) re-confirm the baseline file reflects current cluster state, (d) author `.plans/session-NN-plan.md` for user approval before touching code.
- **Every session ends with**: one squash-merged PR, the baseline file updated if cluster state changed, this document updated if scope shifted, and a clear handoff for the next session in its description.
- **Session scope creep**: if a session starts spilling into the next one's scope, STOP, surface the boundary to the user, and either close the current session with a partial PR or formally re-scope.
- **ADR contradictions**: STOP and surface; never work around. Session 01 hit this with ADR-006 vs the installed Service Mesh 3, resolved via ADR-020. Expect one or two more through Phase 0 as real state meets assumptions.

---

## Known open questions beyond this backlog

These are deliberately not Phase 0 session topics; noted so they don't get lost.

- **OD-5** (agent brain model selection for Loop 4) — Phase 3 concern; constraint added by ADR-019 (must be Llama Stack Agents API compatible).
- **Nucleus codification** — pre-existing deployment, formalized Phase 1 rather than Phase 0.
- **CI workflows** (Sigstore signing + SBOM generation in GitHub Actions) — deliberately deferred from Session 01 per the Session 01 plan; plausible Phase 0 addition as a 16th session if we want signing posture to exist before Phase 1 image builds begin. Flag for the user.

---

## References

- `docs/04-phased-plan.md` — Phase 0 work breakdown and exit criteria (authoritative).
- `docs/07-decisions.md` — ADR-017 (hub + companion), ADR-018 (GFD GPU class targeting), ADR-019 (Llama Stack HIL), **ADR-020 (Service Mesh 3)**.
- `infrastructure/baseline/osd-hub-state.md` — current hub state; findings that shaped this plan.
- `CLAUDE.md` — hard constraints every session must respect.
