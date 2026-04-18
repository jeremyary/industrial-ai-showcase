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

### 6. No probes / health checks
- **What**: Neither the PoC chart nor the upstream Compose stack ship liveness/readiness probes for Nucleus services.
- **Why**: NVIDIA doesn't publish recommended probe endpoints.
- **Fix**: Part D adds probes based on observed TCP-accept + HTTP response patterns. May need to research per-service which endpoint is a useful liveness signal.
- **Risk until closed**: a deadlocked service doesn't get restarted by K8s; requires operator to notice.

### 7. No Service Mesh enrollment
- **What**: Nucleus services communicate in plaintext inside the cluster.
- **Why**: Part E scope.
- **Fix**: Part E adds ServiceMeshMember + PeerAuthentication STRICT.
- **Risk until closed**: east-west traffic within `omniverse-nucleus` namespace is unencrypted. Lab acceptable.

### 8. No NetworkPolicies
- **What**: Default-allow within the namespace, and default-allow cross-namespace ingress to Nucleus services.
- **Why**: Part D scope.
- **Fix**: Part D adds default-deny baseline + explicit allowlists for `openshift-ingress`, other consumer namespaces (Kit, Isaac Sim, USD Search, VSS, GR00T).
- **Risk until closed**: over-broad network reachability in a namespace holding an asset-serving identity substrate. Lab acceptable.
