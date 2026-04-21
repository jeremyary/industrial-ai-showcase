# apps/kit-appstreaming

NVIDIA Kit App Streaming (KAS) control plane. Browser-embeddable streaming of Kit apps (Isaac Sim in Phase 1) via the KAS session-manager architecture.

**Phase**: 1 tail (plan item 4 — Kit App Streaming). Per `docs/07-decisions.md` ADR-026's Thor follow-up and the user-confirmed choice to use the KAS-mediated architecture rather than direct-browser WebRTC.

## Checkpoint sequence

1. **Namespace + NGC auth** (this landing) — `omni-streaming` + `flux-operators` namespaces, Vault-backed `ngc-api-key` → rendered `ngc-pull-secret` (dockerconfigjson) + `ngc-omni-user` (generic user/pass — the form KAS Helm charts consume).
2. `memcached` Helm chart — shader cache shared by all Kit pods KAS spawns.
3. `flux2` in `flux-operators` — KAS uses Flux for streaming-app reconciliation.
4. `kit-appstreaming-rmcp` — Resource Management Control Plane.
5. `kit-appstreaming-applications` — Application + Profile registry. Isaac Sim 5.1 GA application profile is POSTed here.
6. `kit-appstreaming-manager` — Session Manager. Warm-pool config keeps 1+ Kit pod pre-warmed for demo responsiveness.
7. **OpenShift Route + TLS passthrough** — OSD-compatible substitute for the AWS NLB chart (which we can't use on managed OSD).
8. **Replace the static `apps/isaac-sim` Deployment** — once KAS serves sessions, the static pod is redundant. Nothing else in the repo references it (audited — only `workloads/isaac-sim/scenarios/warehouse_baseline.py` itself).
9. **Console `Stage` panel** — embeds KAS's JS SDK, shows live Isaac Sim warehouse viewport.

## Why KAS and not direct browser WebRTC

Isaac Sim 5.1 moved the officially-supported browser-streaming path to KAS-mediated sessions. Direct-to-pod browser WebRTC still technically works on 5.0 but is no longer NVIDIA's blessed path, and 5.1 regresses it on some hardware (e.g., Jetson Thor per NVIDIA forums). KAS is the path NVIDIA maintains forward through 6.0. See `docs/07-decisions.md` if this gets formalized as an ADR.

## Why Kit app is not a static Deployment under KAS

KAS's Session Manager spawns Kit app pods **on-demand** when a browser session is requested, then tears them down. Static Deployments don't fit this model. Our Phase-1 `apps/isaac-sim/` Deployment is kept alive during KAS bring-up for verification but retired at checkpoint #8.

## Sources

- [Kit App Streaming Installation — docs.omniverse.nvidia.com](https://docs.omniverse.nvidia.com/ovas/latest/deployments/infra/installation.html)
- [kit-appstreaming-rmcp NGC Helm chart](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/helm-charts/kit-appstreaming-rmcp)
- [kit-appstreaming-manager NGC Helm chart](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/helm-charts/kit-appstreaming-manager)
- [kit-appstreaming-applications NGC Helm chart](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/helm-charts/kit-appstreaming-applications)
