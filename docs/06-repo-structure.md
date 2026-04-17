# 06 — Repository Structure

The canonical layout the implementation follows. This is the Git repository Claude Code will work inside.

## Top-level

```
physical-ai-reference/
├── README.md
├── CLAUDE.md
<!-- LICENSE deliberately omitted: AI-generated content has unresolved copyright status and cannot be licensed by us. A human with Red Hat Legal guidance must decide if/when a LICENSE is added. See .claude/rules/ai-compliance.md. -->
├── CODEOWNERS
├── .github/
│   ├── workflows/                   # CI: lint, build, sign, SBOM, test
│   └── ISSUE_TEMPLATE/
├── docs/
│   ├── 00-project-charter.md
│   ├── 01-architecture-overview.md
│   ├── 02-component-catalog.md
│   ├── 03-data-flows.md
│   ├── 04-phased-plan.md
│   ├── 05-sales-enablement.md
│   ├── 06-repo-structure.md         # (this file)
│   ├── 07-decisions.md              # ADRs
│   ├── 08-gpu-resource-planning.md
│   ├── 09-risks-and-open-questions.md
│   ├── diagrams/                    # Mermaid + SVG sources
│   │   ├── 01-layers.mmd
│   │   ├── 02-topology.mmd
│   │   ├── 03-loops.mmd
│   │   ├── 04-security-surfaces.mmd
│   │   ├── 05-gpu-allocation.mmd
│   │   ├── 06-mega-mapping.svg      # authored; not generated
│   │   └── README.md
│   ├── deployment/
│   │   ├── prerequisites.md
│   │   ├── cluster-setup.md
│   │   ├── phased-install.md
│   │   └── runbooks/
│   ├── sales-enablement/            # Internal, not customer-facing
│   │   ├── talk-tracks/
│   │   │   ├── archetype-a.md
│   │   │   ├── archetype-b.md
│   │   │   └── archetype-c.md
│   │   ├── objection-cards/
│   │   ├── competitive/
│   │   ├── discovery-questions.md
│   │   └── training-checklist.md
│   └── customer-narratives/
│
├── infrastructure/
│   ├── gitops/
│   │   ├── README.md
│   │   ├── bootstrap/               # The initial Argo CD and ApplicationSet scaffolding
│   │   ├── clusters/
│   │   │   ├── hub/                 # OSD hub — most workloads live here
│   │   │   ├── companion/           # Self-managed — Virtualization, MachineConfig, FIPS, air-gap validation (ADR-017)
│   │   │   ├── spoke-a/
│   │   │   └── spoke-b/
│   │   ├── apps/                    # One dir per Application
│   │   │   ├── nucleus/
│   │   │   ├── usd-search/
│   │   │   ├── isaac-sim/
│   │   │   ├── kit-app-streaming/
│   │   │   ├── vss/
│   │   │   ├── cosmos/
│   │   │   ├── groot-serving/
│   │   │   ├── fleet-manager/
│   │   │   ├── mission-dispatcher/
│   │   │   ├── wms-stub/
│   │   │   ├── mcp-servers/
│   │   │   ├── langgraph-orchestrator/
│   │   │   └── console/
│   │   └── overlays/                # per-env customization (dev, demo, prod)
│   │       ├── dev/
│   │       ├── demo/
│   │       └── prod/
│   ├── operators/
│   │   ├── nvidia-gpu/              # CRs for NVIDIA GPU Operator
│   │   ├── openshift-virt/
│   │   ├── odf/
│   │   ├── pipelines/
│   │   ├── service-mesh/
│   │   ├── acm/
│   │   ├── amq-streams/
│   │   ├── openshift-ai/
│   │   └── ...
│   ├── security/
│   │   ├── sigstore/
│   │   │   ├── policy-controller/   # Both hub and companion — cluster-admin makes this direct on both
│   │   │   └── keys/
│   │   ├── network-policies/
│   │   ├── scc/                     # Custom SCCs — cluster-admin on hub, native on companion
│   │   ├── stig-machineconfig/      # Companion cluster only (MachineConfigs fragile on OSD)
│   │   └── fips/                    # Companion cluster only
│   └── observability/
│       ├── grafana-dashboards/
│       ├── prometheus-rules/
│       ├── tempo-config/
│       └── loki-config/
│
├── workloads/
│   ├── nucleus/                     # Existing deployment, codified
│   │   ├── chart/
│   │   ├── values/
│   │   └── README.md
│   ├── usd-search/
│   ├── isaac-sim/
│   │   ├── container/
│   │   │   ├── Dockerfile
│   │   │   ├── startup/
│   │   │   └── tests/
│   │   ├── chart/
│   │   ├── scenarios/               # Isaac Sim scenario configs (references assets)
│   │   └── README.md
│   ├── isaac-lab/
│   │   ├── container/
│   │   ├── pipelines/               # Kubeflow Pipeline definitions
│   │   └── README.md
│   ├── kit-app-streaming/
│   │   ├── factory-viewer/          # Custom Kit app
│   │   ├── chart-overrides/
│   │   └── README.md
│   ├── cosmos/
│   │   ├── predict-25/
│   │   ├── transfer/
│   │   └── README.md
│   ├── vss/
│   │   ├── chart-overrides/
│   │   └── README.md
│   ├── groot-serving/
│   │   ├── runtime/                 # vLLM runtime wrapper
│   │   ├── inference-services/      # KServe InferenceService definitions for GR00T, Pi-0, OpenVLA
│   │   ├── preprocessors/           # robot-observation preprocessing
│   │   └── README.md
│   ├── fleet-manager/
│   │   ├── src/
│   │   ├── schemas/                 # Avro schemas for Kafka events
│   │   ├── chart/
│   │   ├── tests/
│   │   └── README.md
│   ├── mission-dispatcher/
│   │   ├── src/
│   │   ├── chart/
│   │   ├── tests/
│   │   └── README.md
│   ├── wms-stub/
│   │   ├── src/
│   │   ├── chart/
│   │   └── README.md
│   ├── mcp-servers/
│   │   ├── mcp-isaac-sim/
│   │   │   ├── src/
│   │   │   ├── chart/
│   │   │   └── schemas/
│   │   ├── mcp-fleet/
│   │   ├── mcp-mlflow/
│   │   ├── mcp-nucleus/
│   │   └── README.md
│   ├── langgraph-orchestrator/
│   │   ├── src/
│   │   ├── graphs/                  # LangGraph graph definitions per task type
│   │   ├── prompts/
│   │   ├── chart/
│   │   └── README.md
│   └── common/
│       ├── chart-library/           # Shared Helm chart library for consistent patterns
│       └── python-lib/              # Shared Python utilities across services
│
├── assets/
│   ├── scenes/
│   │   ├── warehouse-baseline/
│   │   │   ├── scene.usd
│   │   │   ├── README.md
│   │   │   └── metadata.yaml
│   │   ├── electronics-line/        # Phase 4
│   │   └── automotive-subassembly/  # Phase 4
│   ├── robots/
│   │   ├── unitree-g1/
│   │   │   ├── usd/
│   │   │   ├── urdf/
│   │   │   ├── policies/            # baseline policies + test policies
│   │   │   └── README.md
│   │   ├── nova-carter/
│   │   └── robotic-arms/
│   ├── sensors/
│   │   ├── cameras/
│   │   └── lidars/
│   └── cad-conversions/             # source CAD → OpenUSD conversion artifacts
│
├── console/
│   ├── frontend/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── backend/
│   │   ├── src/
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── chart/
│   ├── scenarios/                   # Scenario definitions (beats, audience applicability)
│   │   ├── warehouse-baseline.yaml
│   │   ├── warehouse-bottleneck.yaml
│   │   ├── warehouse-new-policy.yaml
│   │   ├── electronics-line.yaml    # Phase 4
│   │   └── automotive-subassembly.yaml  # Phase 4
│   ├── assets/                      # Console-specific art, icons
│   └── README.md
│
├── demos/
│   ├── warehouse-baseline/
│   │   ├── script.md
│   │   ├── recording.mp4            # large file; Git LFS
│   │   ├── beats/                   # one file per beat, with talking points
│   │   └── handoff-template/
│   ├── 20-min-architecture/
│   │   ├── script.md
│   │   └── ...
│   ├── 60-min-deep-dive/
│   │   ├── script.md
│   │   └── ...
│   └── README.md
│
├── edge/
│   ├── microshift/
│   │   ├── ansible/                 # Playbooks for provisioning edge hardware
│   │   ├── image-mode/              # bootc / bootable container image builds
│   │   └── configs/
│   ├── holoscan/                    # Phase 3+
│   └── README.md
│
├── tools/
│   ├── cad-to-usd/                  # Scripts for CAD → OpenUSD
│   ├── scenario-gen/                # Scripts that generate scenario manifests
│   ├── lab-deploy/                  # One-shot lab deployment scripts (customer handoff)
│   └── dev/                         # Developer utilities
│
└── tests/
    ├── integration/
    │   ├── loop-1-operational/
    │   ├── loop-2-mlops/
    │   ├── loop-3-synthetic/
    │   └── loop-4-agentic/
    ├── e2e/
    ├── smoke/
    └── chaos/                       # Fault-injection tests for demo-visible recovery behaviors
```

## Conventions

### Helm chart structure

Every deployable component has its own chart under `workloads/*/chart/` following a consistent structure:

```
chart/
├── Chart.yaml                       # includes sourceImageRef
├── values.yaml                      # defaults
├── values.demo.yaml                 # overrides for demo environment
├── values.prod.yaml                 # overrides for prod environment
├── templates/
│   ├── _helpers.tpl
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── route.yaml
│   ├── servicemonitor.yaml
│   └── networkpolicy.yaml
└── README.md                        # chart-specific docs
```

### Container build conventions

Every `workloads/*/container/` directory is buildable independently. Tekton pipelines discover these via a convention:
- `container/Dockerfile` present → build
- `container/tests/` present → run before push
- `container/.containerignore` used to scope context

Container images are tagged `quay.io/redhat-physical-ai-reference/<component>:<sha>` with additional semver tags when major milestones warrant.

### Signing and attestation

- Cosign signs every image at publish time.
- SBOM (SPDX JSON) attached as image attestation.
- Provenance attestation (SLSA-style) attached.
- Policy-controller in-cluster verifies signatures at admission time.

### Documentation conventions

- Every `workloads/*/` has a README covering: purpose, how to build, how to run locally, how to deploy, where it appears in the phased plan.
- Every `docs/*.md` has a "References" section at the bottom linking primary sources.
- Every ADR in `docs/07-decisions.md` uses a consistent format.
- Anything visual: source file (Mermaid `.mmd` or SVG) lives in `docs/diagrams/`.

### Branch and PR conventions

- Trunk: `main`
- Feature work: `feat/<phase>-<workstream>-<short-descriptor>` e.g. `feat/p1-fleet-manager-v1`
- Docs-only changes: `docs/<short-descriptor>`
- Every PR is linked to a Phase + Workstream in its title line.
- PRs require CI green + one approval + DCO sign-off.
- Squash-merge by default; merge commits allowed for cross-component feature integration.

### Secret handling

- Nothing secret in Git. Ever.
- Secrets live in HashiCorp Vault (deployed to OpenShift or external). External Secrets Operator syncs to ExternalSecret CRs and thence to Kubernetes Secrets.
- For developers without Vault access, a `vault-stub` pattern with ephemeral Secrets is documented for isolated lab work.
- The Cosign signing key lives in Vault; a public key is committed to `infrastructure/security/sigstore/keys/public/`.

### Git LFS usage

Large binary artifacts use Git LFS:
- USD scene files in `assets/scenes/*/scene.usd`
- USD assets larger than 1MB
- Recorded demo videos in `demos/*/recording.mp4`
- Large presentation PDFs, if any

Everything else stays in regular Git.

### File naming

- Markdown: lowercase with hyphens (`phased-plan.md`)
- YAML: lowercase with hyphens (`values.demo.yaml`)
- Python: snake_case
- TypeScript: kebab-case for files, camelCase for exported identifiers
- Directories: lowercase with hyphens
