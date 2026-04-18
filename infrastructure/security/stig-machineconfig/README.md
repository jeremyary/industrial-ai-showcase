# STIG posture — companion cluster

Companion SNO is scanned against DISA STIG V2R3 via the Compliance Operator. This directory records which remediations were applied, which were waivered, and why.

## Scan binding

```
infrastructure/gitops/apps/companion/compliance-scan/scansettingbinding.yaml
```

Binds three profiles (pinned V2R3 for reproducible audit evidence):

- `ocp4-stig-v2r3` — cluster-level config (APIServer, OAuth, project templates).
- `ocp4-stig-node-v2r3` — per-node OpenShift config (kubelet, CRI-O).
- `rhcos4-stig-v2r3` — RHCOS OS (auditd, sysctls, sshd).

ScanSetting `companion-stig-scan-only` has `autoApplyRemediations: false`. Every apply is explicit; no surprise reboots.

## First-scan disposition (Session 11, 2026-04-17)

- **Initial scan**: 36 PASS, 119 FAIL, 12 MANUAL across 167 rules. 106 auto-remediations available.
- **After Session-11 apply batch** (105 remediations; `sshd-disabled` waivered): **137 PASS, 19 FAIL, 12 MANUAL**. FAIL count dropped from 119 → 19 (−100) in one reboot.

The 19 remaining FAILs break down as:

- **1 waivered** — `rhcos4-stig-v2r3-master-service-sshd-disabled` (strand risk).
- **3 N/A by topology** — USBGuard rules (`configure-usbguard-auditbackend`, `service-usbguard-enabled`, `usbguard-allow-hid-and-hub`). KVM VM has no USB subsystem.
- **1 node-level policy default** — `ocp4-stig-node-v2r3-master-reject-unsigned-images-by-default`. Companion CIP is scoped (only `quay.io/openshift-release-dev/ocp-v4.0-art-dev`), not a cluster-wide default-deny. Phase-1 scope expansion addresses this.
- **14 Phase-1 deferred** — everything needing an IdP (`idp-is-configured`, `oauth-*`, `kubeadmin-removed`), cluster-logging (`cluster-logging-operator-exist`, `audit-log-forwarding-*`), or cosmetic templates (`classification-banner`, `openshift-motd-exists`), plus the registry allowlist and resource-quota-per-project rules.

### Applied in the Session-11 batch (105 remediations)

All auto-remediations from all three scans **except** the one strand-risk exclusion (see below). One composite MachineConfig → one node reboot.

Categories covered:

- **OCP platform config** (8 rems): etcd encryption cipher, APIServer audit profile, OAuth token lifetime/idle timeout, default NetworkPolicy + ResourceQuota on new projects.
- **RHCOS auditd rules** (~80 rems): DAC modifications (chmod/chown/setxattr/etc.), file-deletion events, execution of privileged utilities (semanage/setfacl/setsebool), login UIDs immutable after first use.
- **RHCOS sysctls** (~10 rems): kernel hardening — `kernel.dmesg_restrict`, `kernel.perf_event_paranoid`, etc.
- **RHCOS audit config** (~8 rems): audit daemon config, rate limits, backlog sizing.

### Waivered (not applied)

| Rule | Why |
|---|---|
| `rhcos4-stig-v2r3-master-service-sshd-disabled` (V-257583) | Disabling sshd on RHCOS breaks `oc debug node/...` — the only out-of-cluster break-glass path into this SNO. Lab companion, no redundant nodes, no console access story. |

### FAILs without an auto-remediation (MANUAL review)

Roughly 13 rules FAIL that the operator cannot auto-fix. Categories:

- **Configure an IdP** (`idp-is-configured`, `oauth-provider-selection-set`) — Phase 1+ when we know which IdP the showcase uses.
- **Install cluster-logging operator** (`cluster-logging-operator-exist`, `audit-log-forwarding-*`) — Phase 0 deferred; Session 14 territory.
- **Install container-security-operator** (`container-security-operator-exists`) — Phase 1 optional.
- **Configure OAuth login/logout templates + classification banner** (`oauth-login-template-set`, `oauth-logout-url-set`, `classification-banner`, `openshift-motd-exists`) — cosmetic; punt to Phase 1 when the showcase console lands.
- **Remove kubeadmin** (`kubeadmin-removed`) — would strand cluster access; keep until a real IdP is wired up.
- **Restrict registry allowlist** (`ocp-allowed-registries`, `ocp-allowed-registries-for-import`) — needs a scoped list of registries; Phase 1 when showcase images clarify scope.

### FAILs that are SNO-topology artifacts (permanent waiver)

A handful of rules score FAIL because the profiles expect multi-node HA (3-member etcd, separate worker/master pools). They don't apply to an SNO lab cluster and cannot be remediated without adding nodes. Documented here rather than fighting them in the scan.

## Post-apply re-scan

After the Session-11 apply, re-scan and capture PASS/FAIL deltas:

```bash
export KUBECONFIG=~/.kube/companion.kubeconfig
oc --insecure-skip-tls-verify annotate compliancescan/ocp4-stig-v2r3 \
  -n openshift-compliance compliance.openshift.io/rescan= --overwrite
oc --insecure-skip-tls-verify annotate compliancescan/ocp4-stig-node-v2r3-master \
  -n openshift-compliance compliance.openshift.io/rescan= --overwrite
oc --insecure-skip-tls-verify annotate compliancescan/rhcos4-stig-v2r3-master \
  -n openshift-compliance compliance.openshift.io/rescan= --overwrite
```

Results land as new `ComplianceCheckResult` objects. The evidence bundle for audit is produced via `oc compliance fetch-raw` — ARF XML from the `rs-<scan>` PVC (backed by `lvms-vg1`).

## Scheduled re-scan

ScanSetting `companion-stig-scan-only` has `schedule: "0 6 * * *"`. Fresh scan runs nightly at 06:00 cluster time; drift from the Session-11 baseline surfaces in the morning's `ComplianceCheckResult` diff.

## Related

- `infrastructure/security/fips/README.md` — FIPS evidence; several STIG rules directly verify FIPS state and score PASS because of `fips: true` at install.
- `.plans/session-11-research.md` — research brief behind the Session-11 decisions.
- `infrastructure/gitops/apps/companion/compliance-scan/` — the ScanSetting and ScanSettingBinding manifests.
- `infrastructure/gitops/apps/companion/cluster-image-policy/` — the ClusterImagePolicy applied alongside this batch to address `reject-unsigned-images-by-default`.
