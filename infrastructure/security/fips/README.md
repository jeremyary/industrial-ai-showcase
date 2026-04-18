# FIPS posture — companion cluster

The companion SNO was installed with `fips: true` as a day-1 decision. This directory records the evidence bundle proving that the cluster genuinely runs in FIPS mode, and documents the one audit caveat that comes with this install path.

## Evidence

All three signals auditors ask for are present. Capture them with:

```bash
export KUBECONFIG=~/.kube/companion.kubeconfig
oc --insecure-skip-tls-verify debug node/companion-0 -- \
  chroot /host sh -c 'echo "fips_enabled=$(cat /proc/sys/crypto/fips_enabled)"; \
    echo "cmdline-fips=$(cat /proc/cmdline | tr \" \" \"\n\" | grep -i fips)"; \
    echo "crypto-policy=$(update-crypto-policies --show)"'
```

Expected output (captured 2026-04-17 during Session 10):

| Signal | Value | Meaning |
|---|---|---|
| `/proc/sys/crypto/fips_enabled` | `1` | Kernel's crypto subsystem is in FIPS mode. |
| Kernel cmdline `fips=1` | present | Kernel was booted into FIPS from the start, not retrofitted. |
| `update-crypto-policies --show` | `FIPS` | System-wide crypto policy forces FIPS-approved algorithms. |

Plus the cluster-level install record:

```bash
oc get cm cluster-config-v1 -n kube-system -o jsonpath='{.data.install-config}' | grep -iE '^fips'
# → fips: true
```

## The `hostcrypt-check-bypassed` caveat

The install was rendered on a Fedora 43 host that is not itself in FIPS mode. The static `openshift-install` binary normally refuses to render a FIPS-mode ISO from a non-FIPS host (guaranteeing the installer's own manifest-hashing used FIPS-validated crypto). We bypassed that gate with `OPENSHIFT_INSTALL_SKIP_HOSTCRYPT_VALIDATION=1`. Per ADR-017 amendment and [openshift/installer#hostcrypt](https://github.com/openshift/installer/blob/main/pkg/hostcrypt/static.go), this records:

- The **cluster** runs in FIPS mode (evidence above).
- The **installer run** was not FIPS-attested.

In OCP 4.21 this annotation is stamped on the install-config ConfigMap only — it does not propagate to `ClusterVersion.metadata.annotations`. Evidence that the bypass was used:

```bash
oc get cm cluster-config-v1 -n kube-system -o jsonpath='{.data.install-config}' | \
  grep -i hostcrypt
# → annotations carry hostcrypt-check-bypassed=true in the stored install-config record
```

### Audit disposition

Immaterial for **demonstrating FIPS posture** — the running cluster's kernel, crypto libraries, container runtime, and Compliance Operator STIG scans all evaluate against FIPS-validated modules and score accordingly.

Material for a **formal CNSA / FIPS 140-3 audit of the install chain** — an auditor would need evidence that every key used for ignition bootstrap was generated on FIPS-validated crypto. The Fedora installer host cannot produce that evidence.

### Closing the gap

Two paths if this ever becomes material:

1. **Reinstall from a RHEL 9 host in FIPS mode** using the `openshift-install-rhel9` tarball's FIPS-capable `openshift-install-fips` binary. No bypass env var; annotation absent.
2. **Run the installer inside a RHEL 9 container on the Fedora host** with a FIPS-enabled host. Fragile — the container inherits the host kernel's FIPS state, and a non-FIPS host kernel still fails the check.

Path (1) is clean. Neither path is on the Phase-0 critical path.

## Related

- `infrastructure/security/stig-machineconfig/` — the STIG profile evidence, including rules that specifically check FIPS state (`rhcos4-stig` FIPS rules score PASS).
- `docs/07-decisions.md` ADR-017 amendment — full context for the bypass decision.
- `tools/companion-install/install-config.template.yaml` — the template with `fips: true` and the inline explanation.
