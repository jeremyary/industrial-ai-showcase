# apps/isaac-sim

NVIDIA Isaac Sim 5.0.0 headless runner, L40S-class GPU, livestream over WebRTC into the Showcase Console Stage viewport.

**Phase**: 1 (plan item 3).

## What's here

- `namespace.yaml` — `isaac-sim` namespace, PSA=privileged + SCC-sync disabled (Isaac Sim runs as root).
- `vault-auth.yaml` + `vault-static-secret-ngc.yaml` — Vault-backed NGC API key, per the pattern in `platform/ngc-secrets/README.md`.
- `ngc-pullsecret-render-job.yaml` — the Argo pre-sync hook that renders `ngc-pull-secret` (dockerconfigjson) from the plain-text api-key Secret.
- `serviceaccount.yaml` + `scc-anyuid-binding.yaml` — SA + anyuid grant.
- `pvc.yaml` — two PVCs: 50 Gi shader/asset cache, 10 Gi logs.
- `deployment.yaml` — single-replica `Deployment` (Recreate strategy) with `nvidia.com/gpu.product=NVIDIA-L40S` nodeSelector, 1 GPU, WebRTC + livestream ports.
- `service.yaml` — ClusterIP on the streaming ports.
- `networkpolicy.yaml` — permissive egress (Phase 1); ingress scoped to `fleet-ops` / openshift-ingress / cluster-monitoring.

## Kit startup

Uses `runheadless.sh` with `livestream/webrtcEnabled=true`. That boots a headless Kit app connected to the local Nucleus at `omniverse://nucleus-api.omniverse-nucleus.svc.cluster.local` and exposes WebRTC on `49100`.

The scenario / scene selection is controlled by scenario configs under `workloads/isaac-sim/scenarios/`. Phase 1 uses a SimReady Warehouse scene (specific layout pinned in the scenario config).

## Cold start

First boot compiles shaders for every USD asset referenced by the scene; this is CPU + GPU heavy and can take 5–10 minutes. The readiness probe is set to a 2-minute initial-delay with a 10-minute failure budget; the liveness probe gets a 10-minute initial-delay for the same reason.

## Known rough edges to expect on first run

- **Image pull is huge**: the `nvcr.io/nvidia/isaac-sim` image is on the order of 20 GB. First-pod pull on a cold node will take a long time.
- **EULA environment**: both `ACCEPT_EULA=Y` and `PRIVACY_CONSENT=Y` are set. If the image uses a different variable name in your tag, startup will loop on the EULA prompt.
- **Nucleus connection**: Isaac Sim's first USD asset fetch may time out if Nucleus isn't reachable. The Omniverse client caches heavily once warm.

## Not yet here

- **Factory Viewer Kit app** (`workloads/kit-app-streaming/factory-viewer/`) — custom Kit app that embeds the Isaac Sim viewport into the Console. Phase 1 tail.
- **RTSP camera streams** — `workloads/camera-adapter/` consumes camera frames via RTSP once scene cameras are exposed. Phase 1 tail.
- **Scene variation via Cosmos Transfer** — Phase 2.
