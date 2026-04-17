# OSD Hub Cluster Baseline

Captured state of the OpenShift Dedicated hub cluster. This file is living documentation — re-capture when material state changes (operator upgrades, GPU node replacement, RHOAI version bumps).

- **Captured**: 2026-04-17
- **Captured by**: Session 01 (feat/p0-session-01-foundation)
- **Cluster role**: hub (per ADR-017)

---

## 1. Cluster identity and version

| Field | Value |
|---|---|
| Product | OpenShift Dedicated (internal Red Hat instance) |
| OCP version | 4.21.5 |
| Kubernetes version | v1.34.4 |
| Container runtime | cri-o 1.34.5-3.rhaos4.21.gita8af6ea.el9 |
| Node OS | Red Hat Enterprise Linux CoreOS 9.6.20260303-1 (Plow) |
| Node kernel | 5.14.0-570.96.1.el9_6.x86_64 |
| Cloud substrate | AWS (`ec2.internal` node hostnames) |
| Region / AZ | us-east-1 / **us-east-1a (single AZ — see Findings)** |
| `oc` client version | 4.17.11 |

---

## 2. Access verification

- User: `jary@redhat.com`
- `oc auth can-i '*' '*' --all-namespaces`: **yes** (cluster-admin confirmed per ADR-017)
- `oc debug node/<node>`: **denied** by SRE (first concrete OSD restriction observed — see Findings, item 5)

---

## 3. Node inventory

12 nodes total: 3 masters, 2 infra/worker, 7 workers. All single AZ (`us-east-1a`).

| Node | Role | Instance type | GPU | Age |
|---|---|---|---|---|
| ip-10-0-0-125 | master | _(SRE-managed, opaque)_ | — | 25d |
| ip-10-0-42-47 | master | _(SRE-managed, opaque)_ | — | 25d |
| ip-10-0-53-188 | master | _(SRE-managed, opaque)_ | — | 25d |
| ip-10-0-32-46 | infra,worker | r5.xlarge | — | 25d |
| ip-10-0-51-63 | infra,worker | r5.xlarge | — | 25d |
| ip-10-0-23-31 | worker | m5.2xlarge | — | 25d |
| ip-10-0-33-214 | worker | m5.2xlarge | — | 25d |
| ip-10-0-5-155 | worker | m5.2xlarge | — | 2d |
| ip-10-0-62-118 | worker | m5.2xlarge | — | 4d |
| ip-10-0-4-55 | worker | **g6e.4xlarge** | **1× NVIDIA-L40S** | 44h |
| ip-10-0-55-35 | worker | **g6e.4xlarge** | **1× NVIDIA-L40S** | 4d |
| ip-10-0-57-143 | worker | **g6e.4xlarge** | **1× NVIDIA-L40S** | 2d 22h |

(Master instance types are not visible to cluster-admin on OSD; node-label `instance-type` is absent on masters. Treat as SRE-managed.)

---

## 4. GPU inventory and canonical product strings

**These strings are load-bearing for ADR-018.** All workload charts pin GPU class with `nodeSelector: { nvidia.com/gpu.product: <string> }`. The canonical strings on this cluster, confirmed verbatim via `oc get nodes -l nvidia.com/gpu.present=true -o json | jq '.items[].metadata.labels'` on 2026-04-17, are:

```yaml
# L40S pool (3 nodes currently):
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-L40S

# L4 pool (0 nodes currently — SRE ticket needed, see Findings):
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-L4    # expected form; verify once L4 nodes land
```

Per-L40S-node GFD labels (identical across all three L40S workers):

| Label | Value |
|---|---|
| `nvidia.com/gpu.present` | `true` |
| `nvidia.com/gpu.product` | `NVIDIA-L40S` |
| `nvidia.com/gpu.memory` | `46068` (MiB) |
| `nvidia.com/gpu.family` | `ada-lovelace` |
| `nvidia.com/gpu.count` | `1` |
| `nvidia.com/gpu.machine` | `g6e.4xlarge` |
| `nvidia.com/mig.strategy` | `single` |
| `feature.node.kubernetes.io/pci-10de.present` | `true` |
| `.status.capacity["nvidia.com/gpu"]` | `1` |

MIG strategy `single` means one GPU per node exposed as one resource — consistent with ADR-018's "no MIG, no time-slicing, no vGPU splitting" rule.

---

## 5. NVIDIA GPU Operator

| Field | Value |
|---|---|
| Operator CSV | `gpu-operator-certified.v25.10.1` |
| Channel | `v25.10` (certified-operators catalog) |
| Namespace | `nvidia-gpu-operator` |
| ClusterPolicy name | `gpu-cluster-policy` |
| ClusterPolicy state | `ready` (last reconciled 2026-04-15T20:13:53Z) |
| DCGM enabled | true |
| DCGM exporter enabled | true |
| MIG manager enabled | true (`mig.strategy: single`) |
| Driver / toolkit / device-plugin / GFD versions | bundled in operator v25.10.1; no per-component pinning |

No re-install required; validated only.

---

## 6. Node Feature Discovery

| Field | Value |
|---|---|
| Operator subscription | `nfd` (openshift-nfd namespace) |
| Channel | `stable` (redhat-operators) |
| Status | reconciled; GFD labels present on GPU nodes as expected |

---

## 7. Red Hat OpenShift AI (RHOAI)

| Field | Value |
|---|---|
| Operator CSV | `rhods-operator.3.4.0-ea.1` |
| Channel | `beta` (redhat-operators) |
| Namespace | `redhat-ods-operator` |
| DataScienceCluster name | `default-dsc` |
| DSC phase | `Ready` |
| Reported release | `OpenShift AI Self-Managed` v`3.4.0-ea.1` |

DSC component matrix:

| Component | managementState |
|---|---|
| `aipipelines` | Managed |
| `dashboard` | Managed |
| `feastoperator` | Managed |
| `kserve` | Managed |
| `kueue` | **Unmanaged** |
| `llamastackoperator` | Managed |
| `mlflowoperator` | **Managed** (already enabled — see Findings) |
| `modelregistry` | Managed |
| `ray` | Managed |
| `sparkoperator` | **null (not configured)** |
| `trainer` | Managed |
| `trainingoperator` | Managed |
| `trustyai` | Managed |
| `workbenches` | Managed |

Against the `CLAUDE.md` expectations:
- `trainer = Managed` ✓
- `spark` disabled ✓ (managementState is null, i.e. not configured)
- `mlflowoperator = Managed` ✓ (Phase 1 Work Item 0 is effectively already done; Phase 1 just needs to validate backend config)
- `llamastackoperator = Managed` — ready for ADR-019 Phase 3 work
- `trustyai = Managed` — ready for ADR-019 evaluation signal integration
- `ray = Managed` and `trainingoperator = Managed` — ready for Phase 2 Isaac Lab distributed training
- `kueue = Unmanaged` — note; could be flipped to Managed if Phase 2 queueing needs arise

---

## 8. OpenShift Virtualization availability — **OD-9 ANSWER**

| Check | Result |
|---|---|
| `kubevirt-hyperconverged` in `redhat-operators` catalog | **Yes, installable** |
| `kubevirt-hyperconverged` installed (CSV present) | No |
| `HyperConverged` CRD present | No (operator not installed) |
| Node CPU virt extensions (VMX/SVM) visible | **Cannot verify — `oc debug node` denied by SRE**; however, AWS `g6e.4xlarge`, `m5.2xlarge`, `r5.xlarge` are all Nitro-virtualized instance families and do **not** expose nested virtualization to workloads. Running KubeVirt VMs would require `.metal` bare-metal instance families. |

### OD-9 resolution

**OpenShift Virtualization is not a viable use of this OSD hub.** The operator is installable from the catalog, but the underlying AWS Nitro instance families do not expose hardware virtualization extensions to the guest kernel, so KubeVirt VMs would fail to start (or run in dramatically degraded software-emulation mode). Switching the MachinePool to `.metal` would require an SRE request and is a large ask.

**Implication**: per ADR-017, the self-managed companion cluster is where OpenShift Virtualization lives in this reference. OD-9 is **resolved in favor of the companion-cluster design**; this is no longer a "TBD" in the component catalog. The "one platform for containers, VMs, and vGPU workstations" differentiator is demonstrated across the hub+companion pair rather than on the hub alone — which is consistent with the hub+companion talk-track that ADR-017 already anticipated.

---

## 9. Other operators installed (SRE-managed or pre-existing workload operators)

**Workload-relevant (pre-existing, usable for Phase 0+):**

| Operator | CSV / version | Channel | Namespace |
|---|---|---|---|
| NVIDIA GPU Operator | `gpu-operator-certified.v25.10.1` | v25.10 | nvidia-gpu-operator |
| NFD | latest via subscription | stable | openshift-nfd |
| RHOAI | `rhods-operator.3.4.0-ea.1` | beta | redhat-ods-operator |
| OpenShift Pipelines (Tekton) | `openshift-pipelines-operator-rh.v1.21.1` | latest | openshift-operators |
| **Red Hat OpenShift Service Mesh 3** | `servicemeshoperator3.v3.3.1` | stable | openshift-operators |
| Kueue | `kueue-operator.v1.3.1` | stable-v1.3 | openshift-kueue-operator |
| Kernel Module Management | `kernel-module-management.v2.6.0` | stable | openshift-kmm |
| JobSet | via subscription | stable-v1.0 | openshift-jobset-operator |
| Authorino | `authorino-operator.v1.3.0` | stable | openshift-operators |
| cert-manager | `cert-manager-operator.v1.18.1` | stable-v1 | openshift-cert-manager-operator |
| Limitador | `limitador-operator.v1.3.0` | stable | openshift-operators |
| Red Hat Connectivity Link (Gateway API) | `rhcl-operator.v1.3.2` | stable | openshift-operators |
| DNS Operator | `dns-operator.v1.3.0` | stable | openshift-operators |

**OSD-managed (SRE operators — don't touch):**
- cloud-ingress-operator, custom-domains-operator, deployment-validation-operator, managed-upgrade-operator, configure-alertmanager-operator, must-gather-operator, osd-metrics-exporter, rbac-permissions-operator, route-monitor-operator, splunk-forwarder-operator, managed-velero-operator

**Catalog sources active:** `certified-operators`, `community-operators`, `redhat-marketplace`, `redhat-operators` — all READY.

**NOT yet installed** (Phase 0 sessions 2–3 will install these):
- OpenShift GitOps (Argo CD) — Session 2
- OpenShift Data Foundation — Session 3 (or accept OSD-provided StorageClasses + provision S3 separately)
- OpenShift Logging + LokiStack — Session 3
- OpenTelemetry Operator + Tempo Operator — Session 3
- Grafana Operator — Session 5
- CloudNativePG — Session 3
- Red Hat Advanced Cluster Management — Session 3
- Ansible Automation Platform — Session 3
- Streams for Apache Kafka (AMQ Streams) — Session 3

---

## 10. Sigstore admission state

- CRDs matching `sigstore` or `policy-controller`: **none**.
- Admission webhook for image signing: not installed.

Baseline: nothing in place yet. Phase 0 Session 6 installs `policy.sigstore.dev` in warn mode; graduates to enforce in Phase 1.

---

## 11. Findings that need action

These are the items that need to be raised, filed as SRE tickets, or resolved via ADR before Phase 0 can be called complete.

### Finding 1 — **L4 GPU nodes are absent (blocker for ADR-018 and Phase 1+)**

`CLAUDE.md` declares the GPU budget as **2–3 × L40S + 2–3 × L4**. The cluster currently has 3 × L40S and **zero L4 nodes**. Workloads planned for the L4 class (Metropolis VSS VLM, LangGraph agent brain LLM, USD Search embedding generation, USD Code / USD Verify NIMs — per ADR-018) have no nodes to land on.

**Recommended action**: open an SRE ticket to provision 2–3 L4-bearing worker nodes. On AWS, the `g6.xlarge` / `g6.2xlarge` families back L4. Include in the ticket:
- Target count: 2–3 nodes
- Instance family: `g6.xlarge` or equivalent L4-bearing family
- Same AZ or multi-AZ preference (see Finding 4)
- Expected GFD label after provisioning: `nvidia.com/gpu.product: NVIDIA-L4` (verify exact string once nodes land)

This ticket is on the **critical path for Phase 1** — without L4s, Metropolis VSS cannot be deployed to the class ADR-018 specifies.

### Finding 2 — **Service Mesh 3 is installed; ADR-006 specifies v2**

ADR-006 decision was "OpenShift Service Mesh v2 (Istio-based) for east-west traffic" with a note that ambient-mode should be reconsidered "in a future ADR if ambient matures in Red Hat's offering." The installed operator is **OpenShift Service Mesh 3** (`servicemeshoperator3.v3.3.1`), not v2.

Service Mesh 3 is the upstream-Istio-based version (the `sail-operator` pattern) with both sidecar and ambient options. It is strategically aligned with where Red Hat is taking the mesh story, and installing v2 alongside it on the same cluster would be an anti-pattern.

**Recommended action**: draft **ADR-020** superseding ADR-006 with the Service Mesh 3 decision. Proposed body:
- Decision: Service Mesh 3 (current `servicemeshoperator3`), Istio-based, with sidecar injection remaining the default pattern. Ambient mode evaluated per-workload as the reference matures.
- Reason: v3 is the installed, supported, and strategically aligned version on the hub; v2 would be a regression.
- Consequences: existing ADR-006 consequences (mTLS, tracing, traffic shaping, upfront complexity) still apply; no change in east-west zero-trust posture.

**Do not proceed with any Service Mesh-dependent work until ADR-020 is drafted and approved by the user.**

### Finding 3 — **OpenShift GitOps (Argo CD) is not yet installed**

No GitOps Subscription present. This is the first work item for Phase 0 Session 2. No action needed in Session 01 beyond noting it.

### Finding 4 — **Single-AZ deployment (`us-east-1a` only)**

All 12 nodes live in `us-east-1a`. A full-AZ outage takes the entire hub down. For an internal reference this is low-stakes, but worth noting in the field-team talk track: customer-facing production references would span AZs.

**Recommended action**: no immediate change; note in the one-pager as a known Phase-0-appropriate simplification.

### Finding 5 — **`oc debug node/...` is denied by SRE**

First concrete OSD SRE restriction encountered. ADR-017 anticipated this class of friction ("MachineConfigs on OSD are fragile; SRE's automation manages the underlying infrastructure"). `oc debug node` is a softer restriction than MachineConfig but confirms SRE has trimmed some host-level debugging paths.

**Recommended action**: none direct. Note for future sessions that any host-level inspection (kernel params, CPU features, IOMMU state) cannot be done via `oc debug node` on this hub and should be done on the companion cluster where we own the substrate.

### Finding 6 — **MLflow is already enabled**

`mlflowoperator` is `Managed` in the DSC and the DSC is `Ready`. The Phase 1 Work Item 0 plan said "Inspect the existing RHOAI 3.4 EA1 DataScienceCluster on the hub; confirm MLflow component state. Enable the MLflow component in the DSC if not already active." The answer is: already active.

**Recommended action**: Phase 1 Work Item 0 scope reduces to: configure the MLflow backend (Postgres via CNPG, S3 artifact store via ODF RGW or equivalent) and the `workloads/common/python-lib/tracking/` abstraction. The "enable in DSC" step can be skipped.

---

## 12. SRE ticket queue (consolidated)

From the findings above, these tickets belong on the SRE queue and can be filed in parallel with Session 02+ work:

| Ticket | Priority | Finding |
|---|---|---|
| Provision 2–3 × L4-bearing worker nodes (`g6.xlarge` family or equivalent), same AZ acceptable for now | **Critical path for Phase 1** | Finding 1 |
| (none — `oc debug node` restriction is accepted as-is, see ADR-017) | — | Finding 5 |

---

## References

- `CLAUDE.md` — hard constraints (GPU budget, preferred technologies, hub/companion split)
- `docs/04-phased-plan.md` — Phase 0 work breakdown
- `docs/07-decisions.md` — ADR-017 (hub + companion), ADR-018 (GFD label GPU targeting), ADR-015 (RHOAI 3.4.0 EA1 + MLflow)
- `docs/08-gpu-resource-planning.md` — L40S/L4 workload placement
- `docs/09-risks-and-open-questions.md` — OD-8 (companion host), OD-9 (OpenShift Virtualization — **resolved here**)
