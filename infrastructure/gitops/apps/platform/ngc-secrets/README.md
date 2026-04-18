# ngc-secrets — NGC credential pattern for consumer namespaces

NVIDIA NGC API key lives in Vault at `kv/ngc/api-key` (field `api_key`). Any workload namespace that pulls from `nvcr.io` or calls NGC catalog APIs consumes it via the same VaultStaticSecret + Kubernetes-Secret pattern established in Session 08b.

This directory holds no reconciled manifests — only the pattern documentation and a reusable stanza. Each consumer's own kustomize manifests (`apps/platform/nucleus/`, `apps/platform/isaac-sim/`, etc.) instantiate the CRs below scoped to their namespace.

## Seed the Vault path (one time per cluster)

```bash
# Operator runs from a shell with .env sourced and oc logged into hub
oc exec -n vault -it vault-0 -- sh
# inside the pod:
export VAULT_TOKEN=<root-token-from-init>
vault kv put kv/ngc/api-key api_key=<NGC_API_KEY>
vault kv get -field=api_key kv/ngc/api-key  # verify
```

Root token is held by the operator from Vault init (see `infrastructure/gitops/apps/platform/vault/README.md`). VSO's `vso-read` policy can read this path but not write it — writes stay manual.

## Pattern: VaultStaticSecret → docker-config-json imagePullSecret

NVIDIA container images on `nvcr.io` authenticate with username `$oauthtoken` and the API key as password. VSO renders the plain api_key; a small init-job in the consumer namespace transforms it into a docker-config-json Secret suitable for `imagePullSecrets` references.

### 1. Per-namespace VaultAuth + VaultConnection

Every consumer namespace needs one `VaultAuth` + one `VaultConnection`, matching the pattern in `infrastructure/gitops/apps/observability/storage/vault-auth.yaml`. Copy those two files verbatim into the consumer's kustomize dir.

### 2. Per-namespace VaultStaticSecret reading kv/ngc/api-key

```yaml
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultStaticSecret
metadata:
  name: ngc-api-key
  namespace: <consumer-namespace>
spec:
  vaultAuthRef: vault
  type: kv-v2
  mount: kv
  path: ngc/api-key
  destination:
    name: ngc-api-key     # plain Secret with one key: api_key
    create: true
    overwrite: true
  refreshAfter: 1h
```

### 3. Derive the docker-config-json Secret from the api-key Secret

A small Job watches the VSS-rendered `ngc-api-key` and produces `ngc-pull-secret` of type `kubernetes.io/dockerconfigjson`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ngc-pullsecret-render
  namespace: <consumer-namespace>
  annotations:
    argocd.argoproj.io/hook: Sync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: OnFailure
      serviceAccountName: ngc-pullsecret-render
      containers:
        - name: render
          image: registry.redhat.io/openshift4/ose-cli:latest
          command:
            - /bin/bash
            - -c
            - |
              set -euo pipefail
              KEY=$(oc get secret ngc-api-key -o jsonpath='{.data.api_key}' | base64 -d)
              AUTH=$(printf '$oauthtoken:%s' "$KEY" | base64 -w0)
              CONF=$(printf '{"auths":{"nvcr.io":{"username":"$oauthtoken","password":"%s","auth":"%s"}}}' "$KEY" "$AUTH")
              oc create secret generic ngc-pull-secret \
                --type=kubernetes.io/dockerconfigjson \
                --from-literal=.dockerconfigjson="$CONF" \
                --dry-run=client -o yaml | oc apply -f -
```

Plus a ServiceAccount + Role + RoleBinding granting it `secrets: get, create, patch` on its own namespace. The Job re-runs on every sync; idempotent.

### 4. Reference `ngc-pull-secret` from Pod specs

```yaml
spec:
  imagePullSecrets:
    - name: ngc-pull-secret
```

If you need NGC auth at **runtime** (e.g. to call `ngc` CLI or NGC catalog APIs), mount `ngc-api-key` directly:

```yaml
env:
  - name: NGC_API_KEY
    valueFrom:
      secretKeyRef:
        name: ngc-api-key
        key: api_key
```

## Rotation

`vault kv put kv/ngc/api-key api_key=<new-key>` on hub. VSS refreshes within `refreshAfter` (1h default). Re-run the render Job (`kubectl create job --from=job/ngc-pullsecret-render`) to regenerate the docker-config secret immediately, or wait for the next Argo sync.

## When to use this directory

- Reference the pattern from a consumer app's README.
- Do NOT put VaultStaticSecrets here — they need to live in each consumer namespace, which means they live alongside that app's manifests, not here.
- First consumer: `apps/platform/nucleus/` (Session 16 Part B).
