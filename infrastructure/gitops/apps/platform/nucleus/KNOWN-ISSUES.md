# Nucleus chart — known issues

Running log of Path B (ADR-024) operational costs. Each item should either close (with the commit/PR that fixed it) or convert to a tracked design decision.

## Part B (Session 16 foundation)

### 1. `nucleus-passwords` — **closed in Part D**
Migrated to `VaultStaticSecret` reading `kv/nucleus/passwords`. Rotation is `vault kv put` + bounce the auth pod. Plain Secret manifest removed.

### 2. `crypto-secrets` — **closed in Part D**
Migrated to `VaultStaticSecret` reading `kv/nucleus/crypto`. JWT keypairs, discovery token, and salts now live in Vault; the in-cluster generating Job is removed. One-time seed procedure documented in the chart README. Cluster-rebuild no longer invalidates tokens — rebuild reads from Vault.

### 3. Two services from PB 25h1 Compose intentionally not reproduced — `ingress-router`, `auth-router-gateway`
- **What**: NVIDIA's PB 25h1 Compose includes `ingress-router:1.1.4` and `auth-router-gateway:1.4.7`.
- **Why not shipped**: Research established both are architecturally redundant on OpenShift. `ingress-router` is NGINX path-based reverse proxy — OpenShift Routes (`routes.yaml`) cover this exactly. `auth-router-gateway` is a renamed SSO Gateway for SAML IdP federation; NVIDIA docs confirm Nucleus runs with local username/password auth (our Phase-1 config) without it. Kit / Isaac / other `omniverse://` clients authenticate directly against `auth-service` and never touch the gateway unless SAML is wired up.
- **Not a gap.** Closed, not deferred.
- **If SSO is ever needed (Phase 3+)**: federate via Red Hat build of Keycloak → Nucleus OIDC (`USE_OPENID_SSO` in `configmap.yaml`, currently off). Do NOT hand-roll SAML.

### 4. Cluster-apps-domain hardcoded
- **What**: `configmap.yaml` and `routes.yaml` have `nucleus.apps.<specific-OSD-cluster-domain>` baked in.
- **Why**: Rendered once at Session 16 authoring time.
- **Fix**: Kustomize post-render patch, or a small `Kustomize replacements:` block that reads the hub's `ingresses.config/cluster` domain at sync time.
- **Risk until closed**: forking the chart for another cluster requires a one-line search-replace. Low risk, visible cost.

### 5. Single-node co-location for all Nucleus pods (NVIDIA storage constraint)
- **What**: One RWO PVC + `subPath` mounts force all 12 Nucleus pods onto the same node. Pod anti-affinity would just make them Pending.
- **Why**: NVIDIA's Nucleus planning doc forbids NFS/SMB/iSCSI. Nucleus expects Linux-local fsync semantics; RWX filesystems don't reliably honor them.
- **Fix**: Structural — not solvable without NVIDIA changing their position on network filesystems or us swapping to `ovstorage` (Phase 3+ when that's GA).
- **Risk until closed**: node failure takes Nucleus down for the duration of pod rescheduling + re-mount. Accept for Phase-1. A customer deployment would use multi-replica Nucleus Enterprise on separate nodes with external load-balancing — outside our SNO/lab setup.

### 6. Probes — **closed in Part D (TCP-socket probes)**
10 of 12 services have TCP-socket readiness + liveness probes on their primary port. `log-processor` and `thumbnails` are internal workers with no listening port — K8s restarts them on process exit, no probe target exists. Nucleus services' endpoints speak WebSocket (return HTTP 426 on plain GET), so TCP-socket probes are the uniform option; HTTP probes would false-fail. Probe timing: readiness 20s/10s/3s, liveness 60s/20s/5s, failureThreshold 3.

### 7. Service Mesh — **closed in Part E (PERMISSIVE mode)**
Namespace joined the `default` Istio revision via the `istio.io/rev: default` label. Intra-mesh pod-to-pod calls get mTLS automatically (both sides have istio-proxy sidecars). PeerAuthentication is **PERMISSIVE** rather than STRICT so OpenShift Router can continue reaching Nucleus Routes over plaintext without refactoring to an Istio Ingress Gateway — STRICT is a Phase-2+ item tied to cluster-wide router strategy. `ngc-pullsecret-render` Job opts out of injection (Jobs with sidecars never Complete).

### 8. NetworkPolicies — **closed in Part D**
`networkpolicy.yaml` ships four policies: `default-deny-ingress` (no pod reachable until explicitly allowed), `allow-intra-namespace` (Nucleus services reach each other via Discovery), `allow-openshift-ingress` (Routes work), `allow-openshift-monitoring` (Prometheus/MCO scrape). Egress stays default-allow for Phase 1 (image pulls, NGC auth, kube-dns, Vault); Phase 2+ can tighten.

When Phase-1 consumer namespaces land (USD Search, Kit, Isaac Sim, VSS, GR00T), each gets its own `allow-from-<consumer>` Policy naming the source namespace via `namespaceSelector`. Extending this file is the pattern.
