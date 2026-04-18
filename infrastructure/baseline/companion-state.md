# Companion Cluster Baseline

Captured state of the self-managed companion SNO. Counterpart to `osd-hub-state.md` — structure is intentionally mirrored so drift from the hub is obvious at a glance. Living documentation — re-capture when material state changes (operator installs, FIPS/STIG remediations applied, reboots to accommodate MachineConfigs).

- **Captured**: 2026-04-17
- **Captured by**: Session 10 (`feat/p0-session-10-companion-baseline`)
- **Cluster role**: companion (per ADR-017)
- **Companion purpose**: MachineConfig-dependent work (FIPS, STIG), air-gap validation, customer-parity self-managed demo. See ADR-017.

Capture is produced by `tools/companion-install/capture-baseline.sh`:

```bash
export KUBECONFIG=~/.kube/companion.kubeconfig
tools/companion-install/capture-baseline.sh > /tmp/companion-baseline-raw.txt
```

The raw output is reviewed, then its facts land in the sections below.

---

## 1. Cluster identity and version

| Field | Value |
|---|---|
| Product | OpenShift Container Platform (self-managed, agent-based install) |
| OCP version | 4.21.5 |
| Kubernetes version | v1.34.4 |
| Container runtime | cri-o 1.34.5-3.rhaos4.21.gita8af6ea.el9 |
| Node OS | Red Hat Enterprise Linux CoreOS 9.6.20260303-1 (Plow) |
| Node kernel | 5.14.0-570.96.1.el9_6.x86_64 (identical to hub) |
| Release image digest | `quay.io/openshift-release-dev/ocp-release@sha256:ae0711cb2b35d8661d086945e0578f9cd2d417093e910e47169447db5dd9f8bd` |
| Substrate | KVM VM on Fedora 43 (GMKTec Evo-X2, AMD Ryzen AI Max+ 395) |
| VM network | macvtap on host `eno1`; VM IP static `10.0.0.80` (nmstate) |
| Cluster name / baseDomain | `companion` / `lab.local` |
| API endpoint | `https://api.companion.lab.local:6443` (workstation `/etc/hosts` mapping → 10.0.0.80) |
| Infrastructure name | `companion-hhfr7` |
| Platform | `None` (bare-metal / agent-based) |
| FIPS mode | **enabled at install (day-1)**; install-host crypt check bypassed — see §9b + ADR-017 amendment |

---

## 2. Access verification

- User: `system:admin` (via kubeconfig cert-auth)
- `oc auth can-i '*' '*' --all-namespaces`: **yes** (cluster-admin confirmed)
- `oc debug node/companion-0`: **works** (unlike OSD, which SRE restricts). Load-bearing for §9b FIPS kernel-cmdline verification and Session 11 Compliance Operator remediations.

---

## 3. Node inventory

1 node (SNO — master + worker role on the same node).

| Node | Status | Roles | vCPU | RAM | Disk | GPU | Age at capture |
|---|---|---|---|---|---|---|---|
| companion-0 | Ready | control-plane,master,worker | 16 | 64 GiB (65,821,332 Ki) | 250 GB (qcow2, /dev/vda; ephemeral-storage 249 GiB allocatable) | — | 51m |

Allocatable (after kube/system reservations): 15500m CPU, 64,670,356 Ki memory, 239,973,624,229 bytes ephemeral-storage, 250 pods.

No GPUs — companion is CPU-only for Phase 0-3. The Fedora host's Ryzen AI Max+ iGPU is not passed through.

---

## 4. GPU inventory and canonical product strings

**None.** No GPU-bearing nodes on companion. `nvidia.com/gpu.present=true` label count: **0** (confirmed).

This is recorded explicitly so Session 12 (KubeVirt) does not attempt GPU passthrough on the companion, and so workload scheduling logic that branches on GPU class (ADR-018) correctly treats the companion as a CPU-only cluster.

---

## 5. NVIDIA GPU Operator

**Not installed.** `clusterpolicy` CRD absent. Expected — no GPUs. Session 12 revisits only if we add KubeVirt GPU passthrough; not expected in Phase 0.

---

## 6. Node Feature Discovery (NFD)

**Not installed.** `nodefeature` CRD absent. No GPU → no GFD need. May be installed alongside KubeVirt in Session 12 if we need hardware-feature labels for VM placement.

---

## 7. Red Hat OpenShift AI (RHOAI)

**Not installed.** `datasciencecluster` CRD absent. RHOAI is an OSD-hub-only component per the layered plan. Companion does not host ML workloads in Phase 0-3.

---

## 8. OpenShift Virtualization (KubeVirt)

Not installed in Phase 0. PackageManifest availability and nested-virt kernel-capability captured for Session 12 readiness:

- `kubevirt-hyperconverged` PackageManifest: **available**, catalog=`redhat-operators`, defaultChannel=`stable`
- Installed CSV: **none** (no kubevirt install yet)
- Nested virt on node: **`svm` present** (AMD SVM exposed — confirmed via `oc debug node` + `/proc/cpuinfo`). Session 12 can proceed.

---

## 9. Platform-shipped built-ins of interest

### 9a. Sigstore admission (`config.openshift.io/v1 ClusterImagePolicy`)

OCP 4.21 ships `ClusterImagePolicy` built-in. Companion is the target for **enforce-mode** image-policy demonstration (tighter than hub's posture). Session 11 authors additional CIPs per `.plans/session-11-research.md`.

- `clusterimagepolicies.config.openshift.io` CRD present: **yes**
- Platform's default `openshift` CIP enrolled: **yes** (age at capture: 57m)

### 9b. FIPS state

| Check | Expected | Actual |
|---|---|---|
| `fips=1` on RHCOS kernel cmdline | present | **present** |
| `/proc/sys/crypto/fips_enabled` on node | `1` | **`1`** |
| Install-config ConfigMap `fips:` field | `true` | **`true`** (confirmed in `kube-system/cluster-config-v1`) |
| `install.openshift.io/hostcrypt-check-bypassed` annotation on ClusterVersion | `"true"` | **empty** (annotation did not propagate to ClusterVersion metadata in 4.21; bypass evidence lives in the install-config record only) |

The cluster is genuinely FIPS-enabled at the kernel + crypto-provider level. The `hostcrypt-check-bypassed` signal is recorded only in the install-config ConfigMap in 4.21; it does not appear on the ClusterVersion object. Session 11's FIPS evidence bundle captures both locations.

---

## 10. Installed operators

Fresh OCP 4.21.5 — only platform-default operators:

- **Subscriptions**: none.
- **CSVs**: `packageserver` (Succeeded) in `openshift-operator-lifecycle-manager`. No others.

Session 11 will add Compliance Operator; Session 12 adds KubeVirt; Session 13 adds ACM klusterlet (pull-model).

---

## 11. Catalog sources

All four default OperatorHub catalogs READY:

| Catalog | Display | Status |
|---|---|---|
| certified-operators | Certified Operators | READY |
| community-operators | Community Operators | READY |
| redhat-marketplace | Red Hat Marketplace | READY |
| redhat-operators | Red Hat Operators | READY |

Confirms outbound connectivity to `registry.redhat.io` / `quay.io` — the companion is **not** air-gapped at this point in its lifecycle. Air-gap validation (per ADR-017) is a later exercise that will involve catalog mirroring via `oc-mirror v2`.

---

## 12. Network

- CNI: **OVNKubernetes**
- Cluster network: `10.128.0.0/14`, hostPrefix `/23`
- Service network: `172.30.0.0/16`
- Machine network: `10.0.0.0/24` (LAN; static node IP `10.0.0.80`)

---

## 13. StorageClasses

**None.** `oc get storageclass` returns `No resources found`.

**This is a Phase-0 gap.** SNO installs without a default dynamic provisioner. Consequences:

- Any `PersistentVolumeClaim` will stay `Pending` indefinitely.
- Compliance Operator's `rawResultStorage` PVC (Session 11) will not bind.
- Monitoring stack PVCs (Prometheus retention, Alertmanager) are currently running on `emptyDir` — acceptable for a showcase, lost on pod restart.
- KubeVirt (Session 12) needs a storage backend for VM disks.

Session 11 must install a storage provisioner before it can use persistent `rawResultStorage`. Candidates:

1. **`lvms-operator`** (LVM Storage Operator) — Red Hat-shipped, purpose-built for SNO, ships LVMCluster CRD that provisions a `lvms-vg1` StorageClass on local block devices. Lightweight. Preferred.
2. **`local-storage-operator` + static PVs** — lower-level, more manual.
3. **`odf-operator`** — too heavy for a 1-node SNO; not recommended here.

Action item: Session 11 opens with `lvms-operator` install, then Compliance Operator, then STIG ScanSettingBinding. Alternative: use `emptyDir: {}` for `rawResultStorage` (acceptable for a demo where ARF XML doesn't need to persist across pod restarts).

---

## 14. ClusterOperator rollup

All **34 of 34** cluster operators `AVAILABLE=True PROGRESSING=False DEGRADED=False`.

Oldest operator reported age at capture: 50m (`machine-config`). Newest: 26m (`monitoring`). Most settled in the 27-49m band, consistent with the observed bootstrap timeline:

- Initial ISO boot: ~18:16 local (2026-04-17)
- bootstrapInPlace shutdown: ~18:25 local (VM powered off mid-install as designed)
- Manual VM restart: ~18:29 local
- All COs Available: 18:56:54 local

Total wall-clock from ISO boot to all-Available: ~40 minutes (including the ~4-min human-in-the-loop restart gap).

---

## 15. Findings and drift from hub

Compared to `osd-hub-state.md`:

| Dimension | Hub (OSD) | Companion (this cluster) |
|---|---|---|
| Node count | 12 (3 master + 9 worker/infra) | 1 (control-plane + worker combined) |
| Cloud substrate | AWS `us-east-1a` (SRE-managed) | KVM VM on Fedora 43 (local) |
| GPU | 3 × L40S + 2 × L4 | none |
| RHOAI | 3.4.0 EA1 installed | not installed |
| Service Mesh | Service Mesh 3 installed | not installed |
| GPU Operator / NFD | installed + labels applied | not installed |
| `oc debug node` | **denied** by SRE | **permitted** — load-bearing for §9b + Session 11 |
| FIPS | not enabled | **enabled day-1** (with hostcrypt bypass caveat) |
| Platform | AWS/OSD | `None` (bare-metal / agent) |
| Ingress cert / DNS | OSD-managed cluster domain | self-signed, `/etc/hosts` override for `*.lab.local` |
| StorageClasses | ODF + AWS gp3 | **none** — see §13 |
| Operator Subscriptions | many (RHOAI, CNPG, AMQ Streams, Vault, GPU Operator, NFD, Mesh, etc.) | none |

Single-node topology is the biggest operational difference. Every MachineConfig change (FIPS, STIG node remediations, LVM install) reboots the only node — there is no rolling drain. Session 11 must plan reboots explicitly.

---

## 16. Known follow-ups (Session 11+)

- **Install storage provisioner** (LVMS) — prerequisite for Compliance Operator PVC (Session 11).
- Install Compliance Operator, bind `ocp4-stig`, `ocp4-stig-node`, `rhcos4-stig` profiles with `autoApplyRemediations: false` (Session 11 — see `.plans/session-11-research.md`).
- Author tight `ClusterImagePolicy` (Red Hat registry enforce) for companion (Session 11). Defer GHCR CIP to Phase 1 when showcase images start being built.
- Document `hostcrypt-check-bypassed` disposition in README + risk register (Session 11).
- Consider rebuilding host on RHEL 9 + FIPS-capable installer to drop the hostcrypt-bypass caveat — Phase-1+ optional, not on critical path.
- Install OpenShift Virtualization + validate nested-virt VM for vGPU Kit workstation story (Session 12). Nested `svm` already confirmed present here.
- Register companion to hub ACM as a spoke via pull-model klusterlet (Session 13).
- Join companion to Thanos federation for hub's unified metrics view (Session 14).
