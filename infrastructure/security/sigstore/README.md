# Sigstore / image-signature enforcement — companion cluster

Companion SNO enforces image signatures at the CRI-O pull layer via the platform-shipped `config.openshift.io/v1 ClusterImagePolicy` (CIP). OCP 4.21 ships this built-in; the community `policy-controller-operator` is **not** installed — see commit history for PR #12 which removed that path.

## Platform-shipped CIP

OCP 4.21 installs a platform CIP named `openshift` (not editable — managed by the payload) that enforces Red Hat's release-signing key on:

- `quay.io/openshift-release-dev/ocp-release` — the release-payload manifest image.

## Companion-added CIPs

| CIP | Scope | Key | Purpose |
|---|---|---|---|
| `companion-ocp-component-images` | `quay.io/openshift-release-dev/ocp-v4.0-art-dev` | Red Hat release-signing key (same as platform) | Extends release-key enforcement to the OCP component images CVO pulls out of the payload (operator operand images). Platform CIP's scope is narrower. |

Manifest: `infrastructure/gitops/apps/companion/cluster-image-policy/`.

## Intentionally deferred

- **`registry.redhat.io` product images** — signed by a different chain (GPG keys, not sigstore public keys). Requires the Red Hat container catalog public key, separate import process, and — most importantly — a validated test pull to confirm signature verification works before applying (an over-scoped CIP that can't verify signatures cluster-bricks every pull). Phase 1, once signing identity and key retrieval story is locked per ADR-016/023.
- **`ghcr.io/<our-org>` (showcase-built images)** — requires locked signing identity (keyless Fulcio via GHA OIDC vs. cosign key in Vault). Phase 1, alongside the first built showcase image.

## Behavior notes

- CIPs enforce at **image pull**, not API admission. An unsigned image's Pod is admitted, scheduled, lands on the node — and then ImagePullBackOffs with event text `Source image rejected: A signature was required, but no signature exists`.
- Scopes not covered by any CIP fall through to `insecureAcceptAnything` (OCP 4.21 default). The user CIP only enforces for scopes it names — this is the knob for staged rollout.
- Every CIP create/edit triggers MCO to re-render `/etc/containers/policy.json`, which drains + reboots the node. On SNO this is an API-downtime event. Plan CIP changes alongside other MachineConfig changes.

## `keys/` directory

Currently empty. Reserved for non-inline key material if we ever need to ship large keys alongside CIP manifests (rare — most are small enough to inline in `keyData`).

## Related

- `.plans/session-11-research.md` §3 — full research brief on ClusterImagePolicy spec, gotchas, and enforcement semantics.
- `infrastructure/security/stig-machineconfig/README.md` — the STIG rule `ocp4-stig-node-v2r3-master-reject-unsigned-images-by-default` expects a CIP in place; this is what satisfies it.
