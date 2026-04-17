# vault

HashiCorp Vault, single-replica, file-backed, for the Phase 0 Secrets substrate. Swap to HA Raft + KMS-backed unseal for production per customer site.

## One-time init + unseal (after first sync)

Vault starts sealed. Run these once:

```bash
# 1. Initialize
oc exec -n vault vault-0 -- vault operator init -key-shares=5 -key-threshold=3

# Record the 5 unseal keys and the initial root token somewhere durable.
# These are NEVER committed to Git. Rotate the root token after the
# substrate is operational.

# 2. Unseal (three of five keys)
for key in KEY1 KEY2 KEY3; do
  oc exec -n vault vault-0 -- vault operator unseal "$key"
done

# 3. Export root token to your shell for subsequent setup
export VAULT_TOKEN=<initial-root-token>
export VAULT_ADDR=http://$(oc get route -n vault vault -o jsonpath='{.spec.host}')  # if Route exists
```

## One-time KV engine + K8s auth setup

Executed by an operator with root token:

```bash
# Enable KV v2 at kv/
vault secrets enable -path=kv kv-v2

# Enable Kubernetes auth
vault auth enable kubernetes

# Wire to the cluster's TokenReview API
vault write auth/kubernetes/config \
  kubernetes_host=https://kubernetes.default.svc:443 \
  disable_iss_validation=true

# Policy allowing VSO to read any kv secret (scope tightening is a later ADR)
vault policy write vso-read - <<EOF
path "kv/data/*" {
  capabilities = ["read"]
}
EOF

# Role binding: any ServiceAccount in any namespace can assume this role
vault write auth/kubernetes/role/vso-read \
  bound_service_account_names='*' \
  bound_service_account_namespaces='*' \
  policies=vso-read \
  ttl=24h
```

## Seeding the Phase-0 placeholder Secrets into Vault

Run once after Vault is unsealed:

```bash
vault kv put kv/mlflow/s3   AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
vault kv put kv/obs/s3      AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
vault kv put kv/cosign/signer   private-key-pem=@cosign.key   password=...
```

VSO CRs under `infrastructure/gitops/apps/security/*-secrets/` reference these KV paths and project them as Kubernetes Secrets into the right namespaces.

## After a pod restart

Vault re-seals. Re-run the unseal step (step 2 above). Production deploys use KMS-backed auto-unseal to avoid this.
