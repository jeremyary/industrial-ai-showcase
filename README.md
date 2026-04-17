# Red Hat Physical AI Reference — Mega on OpenShift

A production-grade reference implementation of NVIDIA's Mega Omniverse Blueprint running entirely on Red Hat's hybrid-cloud portfolio. This repository is the working blueprint that positions Red Hat as the canonical enterprise substrate for NVIDIA's Physical AI stack — across datacenter, factory edge, and robot.

## Who this is for

This project simultaneously serves three audiences:

1. **Red Hat sales specialists** walking into industrial-AI conversations with customers ranging from "what is Omniverse" to Foxconn/Siemens-tier operators. They need narrative, demo, and deep-dive materials they can pull from in the moment.
2. **Red Hat field SAs and partner SIs** (Accenture, IBM Consulting, Deloitte) who need a reproducible reference they can adapt for customer PoCs.
3. **Industrial-AI engineers at customers** who leave a meeting and ask "show me the code." They get a public repository that's specified, deployable, and extensible to their environment.

## The five propositions the showcase substantiates

1. Every component of NVIDIA's Mega blueprint runs on OpenShift, day-one.
2. Containers, VMs, and vGPU workstations unify on a single operational platform.
3. One GitOps-driven fleet model spans hybrid cloud, factory datacenter, factory edge, and robot.
4. The "robot brain" MLOps lifecycle is first-class — training, registry, serving, monitoring — with bring-your-own-model freedom (GR00T ships as primary; nothing is locked to it).
5. The entire stack is deployable on-prem, air-gapped, with Red Hat's enterprise security and supply-chain posture.

## Repository layout

```
physical-ai-reference/
├── README.md                    # You are here
├── CLAUDE.md                    # Working conventions for AI-assisted coding sessions
├── docs/
│   ├── 00-project-charter.md    # Mission, audiences, differentiators, non-goals
│   ├── 01-architecture-overview.md
│   ├── 02-component-catalog.md  # Every component specced
│   ├── 03-data-flows.md         # The four core loops
│   ├── 04-phased-plan.md        # Phase 0 through Phase 4
│   ├── 05-sales-enablement.md   # The Showcase Console + collateral
│   ├── 06-repo-structure.md     # Final repo layout for the implementation
│   ├── 07-decisions.md          # ADRs
│   ├── 08-gpu-resource-planning.md  # Concrete scheduling under 2–3 L40S constraint
│   └── 09-risks-and-open-questions.md
├── infrastructure/              # Phase 0+ — GitOps, operators, cluster config
├── workloads/                   # Phase 1+ — Helm charts and manifests per component
├── assets/                      # USD scenes, robot descriptions, CAD converters
├── demos/                       # Runbooks for each scripted demo scenario
├── console/                     # The Showcase Console (web UI for sales)
├── edge/                        # Device Edge / MicroShift configs
├── tools/                       # Ancillary tooling, CAD-to-USD, etc.
└── tests/                       # CI, smoke tests, E2E
```

## Where to start

- **Just arrived**: read `docs/00-project-charter.md` then `docs/01-architecture-overview.md`.
- **Engineer picking up a build task**: start from `docs/04-phased-plan.md`, find the phase and workstream, then read the matching entries in `docs/02-component-catalog.md`.
- **Sales / field**: read `docs/05-sales-enablement.md` — then watch the demo videos in `demos/`.
- **Starting an AI-assisted coding session**: read `CLAUDE.md` first, always.

## Current status

**Design phase.** The docs in this repository specify what will be built. No production implementation yet. Nucleus on OpenShift exists from prior work and is the one component already operational.

## Primary references

- NVIDIA Mega Omniverse Blueprint: https://build.nvidia.com and related Technical Blog entries
- NVIDIA Omniverse modular libraries (GTC 2026): `ovrtx`, `ovphysx`, `ovstorage`
- NVIDIA Isaac Sim 6.0 and Isaac Lab 3.0 documentation
- Red Hat OpenShift AI, Red Hat Device Edge / MicroShift, Red Hat Advanced Cluster Management
- Red Hat Enterprise Linux for NVIDIA (H2 2026)

Each document in `docs/` carries its own citations and primary-source links in a "References" section at the bottom.
