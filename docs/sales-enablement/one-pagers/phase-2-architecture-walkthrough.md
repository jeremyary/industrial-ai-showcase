# Phase 2 Architecture Walkthrough — Operationalized MLOps + Fleet Rollback

Internal Red Hat. Audience: SAs / AEs prepping for a customer conversation about NVIDIA's Mega / Omniverse blueprint on OpenShift.

## The 10-second version

Phase 2 delivers a live 20-minute demo: multi-site fleet management with real GitOps-driven policy promotion, anomaly-triggered rollback measured at <20 seconds, MES-to-mission brownfield integration, a KFP v2 training pipeline with full MLflow lineage, and a Showcase Console that walks all three audience archetypes through the architecture with presenter-guided controls.

## What's demonstrable today

- **Multi-site fleet.** Hub + companion (Factory A) + Factory B on hub. Two factories running simulated warehouse operations with independent Kafka topic isolation, policy versions, and anomaly detection. ACM federates the companion spoke.
- **Policy promotion + anomaly rollback.** Presenter promotes a VLA policy version (v1.3 → v1.4) through the Console. The change is a real `git commit` → Argo CD sync. When an anomaly triggers, auto-rollback fires a `git revert` → Argo re-sync. Measured end-to-end: <20 seconds including anomaly detection, git revert, and Argo reconciliation.
- **VLA training pipeline.** KFP v2 pipeline on DSPA: fine-tune GR00T N1.7-3B on L40S → evaluate → register in RHOAI Model Registry with full lineage (training data, hyperparameters, metrics). Idempotent model registration handles re-runs cleanly. Vault-sourced credentials throughout.
- **MES → Fleet Manager integration.** MES-stub emits SAP-PP/DS-shaped order messages to `mes.orders` Kafka topic. Fleet Manager consumes orders and translates to robot mission scheduling. The demo beat: "your existing MES drives the AI decisioning, it doesn't replace it."
- **Brownfield story.** KubeVirt VM on companion representing a PLC/HMI gateway. Containers and VMs coexist on the same cluster, visible side by side in the Console Architecture view.
- **Isaac Sim digital twin.** Warehouse scene with route-path visualization on the floor during missions. Camera feeds stream through Kafka to the Console. Obstruction detection runs on camera frames via Cosmos Reason.
- **Showcase Console.** Four audience modes (novice, presenter, evaluator, expert). Fleet view with guided demo stepper, per-factory policy version pills, Argo CD sync status, anomaly detection. Lineage view showing training → evaluation → promotion chain. Architecture view with topology diagram. Training view with pipeline status.

## Differentiator claim status (charter §22)

| # | Claim | Status | Phase-2 proof |
|---|---|---|---|
| 1 | On-prem / air-gapped first-class | Partial | Companion SNO operational; air-gap validation via `oc-mirror v2` not yet demonstrated live. |
| 2 | Containers + VMs + vGPU on one cluster | Substantiated | KubeVirt VM + container workloads on companion, visible in Architecture view. |
| 3 | Hybrid → edge → robot, one op model | Substantiated | Hub + companion + Factory B. ACM-federated. Same GitOps patterns at every tier. |
| 4 | OpenShift AI as MLOps backbone | Demonstrated | KFP v2 training pipeline, RHOAI Model Registry, MLflow experiment tracking, DSPA — all live. |
| 5 | Security / supply-chain posture | Substantiated | Vault secrets management, NetworkPolicies per workload, Kafka TLS, STIG scanning, ClusterImagePolicy. Documented in `security-posture.md`. |
| 6 | Open model choice | Demonstrated | GR00T N1.7-3B served via vLLM/KServe; training pipeline is model-agnostic by design. |
| 7 | Agentic orchestration via MCP | Designed | HIL Approval Drawer design spec complete. Implementation is Phase 3. |
| 8 | Day-2 lifecycle done right | Demonstrated | GitOps promotion + rollback measured live. ACM policy propagation. Argo CD drift detection. |

## Key architecture components

| Component | What it does | Where it runs |
|-----------|-------------|---------------|
| Fleet Manager | Consumes MES orders, dispatches robot missions, monitors anomalies, triggers rollback | Hub (`fleet-ops`) |
| Mission Dispatcher | Receives missions, executes on simulated robot, reports telemetry | Companion (Factory A), Hub (Factory B) |
| Isaac Sim | Digital-twin warehouse simulation with physics, camera feeds, route visualization | Hub (L40S, requires RT cores) |
| Cosmos Reason | Vision-language anomaly analysis on camera frames | Hub (L40S) |
| WMS Stub | Simulates warehouse management system, provides demo scenario controls | Hub (`fleet-ops`) |
| MES Stub | Emits manufacturing execution orders to Kafka | Hub (`fleet-ops`) |
| VLA Training Pipeline | KFP v2: fine-tune → evaluate → register model with lineage | Hub (DSPA, L40S for training) |
| Showcase Console | React/TypeScript dashboard with audience modes, guided demo controls | Hub (`fleet-ops`) |
| Kafka (AMQ Streams) | 3-broker cluster, per-factory topic isolation, KRaft mode | Hub (`fleet-ops`) |

## Talk-track hooks by archetype

- **A (novice).** "Watch the Console — we'll promote a new AI policy to one factory, see an anomaly, and watch the system roll itself back in under 20 seconds. The robot never stops. Now imagine that across 50 factories." Use the guided demo stepper. The Console does the talking.
- **B (evaluator).** Argo CD sync panel embedded in the Fleet view. "Every change is a git commit — promotion, rollback, configuration. Show me the diff, show me who approved it, show me the audit trail. This is the same GitOps you'd run in production." Point at the Lineage view: "Training run → model registration → policy promotion — full provenance, click through each step."
- **C (expert).** Fleet-scale operating math doc: Kafka partition projections to 100 factories, ACM fan-out at 5% of documented capacity, hub resource summary. Security posture doc: Vault-managed secrets, NetworkPolicies, Kafka listener isolation, STIG compliance scanning. "These aren't aspirational — here are the manifests, here are the numbers."

## What's new since Phase 1

- Multi-site fleet (Factory A on companion + Factory B on hub) with independent policy versions
- MES-to-mission brownfield integration (SAP-PP/DS-shaped orders)
- VLA training pipeline with RHOAI Model Registry lineage
- GitOps-driven policy promotion and anomaly-triggered rollback (<20s measured)
- Console guided demo stepper, Fleet view with Argo CD sync panel, Lineage view, Architecture view
- Vault-managed credentials for DSPA, Model Registry, build secrets
- Fleet-scale operating math and security posture sales-enablement docs
- HIL Approval Drawer design spec (Phase 3 prep)

## Caveats (mention before the customer asks)

- Factory B runs on the hub, not a separate spoke cluster — the multi-site story uses Kafka topic isolation, not physical separation. The architecture supports physical separation via ACM; the demo topology consolidates for resource efficiency.
- The training pipeline fine-tunes GR00T N1.7-3B but the resulting checkpoint is not yet hot-swapped into the live serving endpoint during the demo. Training → registration → lineage is live; deployment of the trained model is a manual step.
- Camera streaming from companion to hub goes through Kafka, not direct WebRTC. This is the demo topology; production spoke deployments would consume camera feeds locally.
- Rollback timing (6–18s, bimodal) depends on Argo CD's reconciliation poll cycle. Manual sync is used in the demo for consistent timing.
- Cosmos Reason is validated by NVIDIA on Hopper/Blackwell; running on L40S is outside the validated matrix but functional for demo purposes.

## Deeper reading

- `demos/20-min-architecture/script.md` — the full scripted demo flow.
- `docs/sales-enablement/fleet-scale-operating-math.md` — scaling projections with sourced numbers.
- `docs/sales-enablement/security-posture.md` — deployed security controls and honest gaps.
- `docs/plans/hil-approval-drawer-design.md` — HIL design spec for Phase 3.
- `docs/07-decisions.md` — ADR-019 (Llama Stack HIL), ADR-020 (Service Mesh 3), ADR-027 (Isaac Sim digital twin).
