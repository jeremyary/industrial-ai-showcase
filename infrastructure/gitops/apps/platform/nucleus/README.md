# nucleus

NVIDIA Omniverse Enterprise Nucleus 2023.2.9 as native Kubernetes workloads reconciled by Argo CD. Per ADR-024, this is Red Hat's operational differentiation over NVIDIA's Compose-only posture. We own this chart.

## Origin

Forked at Session 16 from [RHEcosystemAppEng/nvidia-omniverse-nucleus](https://github.com/RHEcosystemAppEng/nvidia-omniverse-nucleus/tree/main/deploy-native) PoC, then:

- Helm-rendered with 2023.2.9 image set (chart pinned to 2023.2.7).
- `app.kubernetes.io/managed-by: helm` and `helm.sh/chart:` labels stripped — Kustomize manages this now, not Helm.
- Imperative `deploy.sh` logic (namespace create, SCC grant, NGC secret create, crypto-secret generate) replaced by Git-reconciled manifests + Argo pre-sync hooks.
- `nucleus-passwords` and `crypto-secrets` still generated in-cluster rather than Vault-sourced — see `KNOWN-ISSUES.md` for Part D migration.
- Two NVIDIA services absent from the PoC chart (`ingress-router:1.1.4`, `auth-router-gateway:1.4.7`) — landing in Part C.

## Image set (2023.2.9)

| Service | Image tag |
|---|---|
| nucleus-api | 1.14.53 |
| nucleus-auth | 1.5.8 |
| nucleus-discovery | 1.5.5 |
| nucleus-lft | 1.14.53 |
| nucleus-lft-lb | 1.14.53 |
| nucleus-log-processor | 1.14.53 |
| nucleus-navigator | 3.3.6 |
| nucleus-resolver-cache | 1.14.53 |
| nucleus-search | 3.2.12 |
| nucleus-tagging | 3.1.35 |
| nucleus-thumbnails | 1.5.14 |
| utl-monpx | 1.14.53 |

Tags verified against NGC `nvcr.io/nvidia/omniverse/*` on 2026-04-18. The itemized 2023.2.9 release notes cover api/auth/discovery/search/tagging/thumbnails; the other five are resolved to their latest `1.14.x`/`3.3.x` tags pending confirmation from the PB 25h1 Compose manifest.

## Topology

- **12 Deployments**, each a standalone service.
- **One shared `ReadWriteOnce` PVC** (`nucleus-data`, 500 GiB on `gp3-csi`) with `subPath` mounts to isolate each service's data dir. Per NVIDIA constraints, Nucleus does not run on NFS/SMB/iSCSI — RWO block only. This forces all Nucleus pods onto a single node; node failure = Nucleus outage.
- **8 OpenShift Routes**, path-based on a single hostname (`nucleus.apps.<cluster-apps-domain>`). Navigator at `/`, API at `/omni/api`, Auth at `/omni/auth`, Discovery at `/omni/discovery`, LFT at `/omni/lft`, Search at `/omni/search`, Tagging at `/omni/tagging`, Auth login form at `/omni/auth-login`.
- **Dedicated `nucleus` ServiceAccount** with `anyuid` SCC bound via RoleBinding (NVIDIA images use `/root/eula.sh` entrypoint, which requires UID 0). Grant is SA-scoped so other workloads in the namespace keep the restricted SCC.

## Hostname — cluster-specific

`SERVER_IP_OR_HOST` in `configmap.yaml` and the `host:` fields in `routes.yaml` are currently hard-coded to the hub cluster's apps-domain. To deploy this chart on a different cluster, search-replace the hostname (one-line edit). A Kustomize replacement pattern could automate this; left as a Phase-2 polish.

## Secrets

| Secret | Source |
|---|---|
| `ngc-pull-secret` | Vault `kv/ngc/api-key` → VSS (`ngc-api-key`) → render Job (`ngc-pullsecret-render`) transforms to `dockerconfigjson`. |
| `nucleus-passwords` | Vault `kv/nucleus/passwords` → VSS. Rotate: `vault kv put` + bounce auth pod. |
| `crypto-secrets` | Vault `kv/nucleus/crypto` → VSS. Seven keys (JWT keypairs, salts, discovery token). Rotate carefully — tokens issued before rotation become invalid. |

## One-time setup

Before the first sync, seed Vault with passwords + crypto material. Both require the Vault root token (held by the operator since Vault init).

### `kv/nucleus/passwords`

```bash
oc exec -n vault -it vault-0 -- sh
# inside pod:
export VAULT_TOKEN=<root-token>
vault kv put kv/nucleus/passwords \
  master-password=<strong-password> \
  service-password=<strong-password>
exit
```

### `kv/nucleus/crypto`

Generate the 7 keys once, then seed. Example flow (run inside the vault pod shell for convenience, export VAULT_TOKEN first):

```bash
# keypairs + salts + token
WORK=$(mktemp -d)
openssl genrsa 4096 2>/dev/null > $WORK/auth_root_of_trust_pri
openssl rsa -pubout < $WORK/auth_root_of_trust_pri 2>/dev/null > $WORK/auth_root_of_trust_pub
openssl genrsa 4096 2>/dev/null > $WORK/auth_root_of_trust_lt_pri
openssl rsa -pubout < $WORK/auth_root_of_trust_lt_pri 2>/dev/null > $WORK/auth_root_of_trust_lt_pub
dd if=/dev/urandom bs=1 count=128 2>/dev/null | od -An -tx1 | tr -d ' \n' | head -c 256 > $WORK/svc_reg_token
dd if=/dev/urandom bs=1 count=4   2>/dev/null | od -An -tx1 | tr -d ' \n' | head -c 8   > $WORK/pwd_salt      # blake2b caps at 16
dd if=/dev/urandom bs=1 count=128 2>/dev/null | od -An -tx1 | tr -d ' \n' | head -c 256 > $WORK/lft_salt

# Assemble to a JSON that vault kv put accepts via stdin
python3 -c "
import json, sys
keys = ['auth_root_of_trust_pri','auth_root_of_trust_pub','auth_root_of_trust_lt_pri','auth_root_of_trust_lt_pub','svc_reg_token','pwd_salt','lft_salt']
out = {k: open(f'$WORK/{k}').read() for k in keys}
print(json.dumps(out))
" | vault kv put kv/nucleus/crypto -
```

Rotation that preserves token validity: copy the existing values, then rotate one key at a time and restart dependent pods in sequence.

## Verification (once Argo syncs)

```bash
# All 12 deployments Ready:
oc get deploy -n omniverse-nucleus

# Navigator UI (plain HTTP — Routes have no TLS block, matching upstream SERVICE_DEPLOYMENTS advertisement):
open "http://nucleus.apps.$(oc get ingresses.config cluster -o jsonpath='{.spec.domain}')/"

# Creds for the `omniverse` admin user:
#   master-password from `nucleus-passwords` Secret (seeded into Vault at `kv/nucleus/passwords`)
```

**End-to-end client validation** (Session 19): Omniverse Launcher on a workstation authenticates against `omniverse://nucleus.apps.<domain>/` with `omniverse` / master-password and navigates the asset tree. In-cluster `omni.client` (bootstrapped via `isaacsim.SimulationApp`) performs authenticated uploads — see `../nucleus-seeder/`.

## Asset seeding

The `nucleus-seeder` Job at `../nucleus-seeder/` is a one-shot that mirrors the Phase-1 warehouse asset tree from the public Isaac Sim 6.0 asset CDN into this Nucleus, so the deployment is air-gap-capable at demo time. Run it after:

1. Nucleus Deployments all Ready + Routes responding.
2. Navigator browser login verified with the `omniverse` / master-password combo (confirms auth service is serving; a broken auth layer is opaque otherwise).

Re-run anytime a new `SEED_ROOTS` prefix is added. Safe to re-run — uses `CopyBehavior.OVERWRITE`.

## Divergence from NVIDIA's Compose

See `docs/07-decisions.md` ADR-024 for the full rationale. Short version: NVIDIA ships Nucleus as Docker Compose; we run the same container images as K8s Deployments because the operational surface is what Red Hat differentiates on.

## Related

- `infrastructure/gitops/apps/platform/ngc-secrets/README.md` — NGC credential pattern this chart uses.
- `infrastructure/gitops/apps/platform/vault/README.md` — Vault init + root-token operator notes.
- `KNOWN-ISSUES.md` — running log of Path B costs.
