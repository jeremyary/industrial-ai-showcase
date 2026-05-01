# The Physical AI Stack

## How the pieces compose

The previous chapters covered individual concepts and technologies.
This chapter shows how they compose into a complete system — from
simulated warehouse to deployed robot fleet, managed by the same
infrastructure patterns you use for conventional workloads.

## The layered architecture

```
┌──────────────────────────────────────────────────────┐
│                  Enterprise / Hub                     │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Training  │  │ Model    │  │ Fleet Management  │  │
│  │ Pipeline  │  │ Registry │  │ & Orchestration   │  │
│  │ (KFP v2) │  │ (RHOAI)  │  │                   │  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       │              │                 │              │
│  ┌────▼──────────────▼─────────────────▼──────────┐  │
│  │              GitOps (Argo CD)                    │  │
│  │              Policy (ACM)                        │  │
│  │              Observability (Prometheus/Thanos)   │  │
│  └──────────────────────┬─────────────────────────┘  │
│                         │                            │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │            OpenShift (Kubernetes)               │  │
│  │            GPU Operator / NFD                    │  │
│  │            Security (Vault, Sigstore, Mesh)     │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                          │
              GitOps + Kafka Federation
                          │
┌──────────────────────────────────────────────────────┐
│                  Factory Edge / Spoke                  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Inference │  │ Mission  │  │ Camera / Sensors  │  │
│  │ (KServe)  │  │ Dispatch │  │                   │  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       │              │                 │              │
│  ┌────▼──────────────▼─────────────────▼──────────┐  │
│  │         Single Node OpenShift (SNO)             │  │
│  │         GPU Operator (L4 / L40S)                │  │
│  │         ACM Agent (klusterlet)                  │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                          │
              Local network / fieldbus
                          │
┌──────────────────────────────────────────────────────┐
│                  Robot / Field Devices                 │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ VLA Brain│  │  Motors   │  │   Cameras         │  │
│  │ (Jetson) │  │ Actuators │  │   Sensors         │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Layer 1: OpenShift + GPU infrastructure

The foundation. OpenShift provides container orchestration, the GPU
Operator manages NVIDIA hardware, NFD provides hardware discovery,
and the security stack (Vault, Sigstore, Service Mesh, NetworkPolicies)
provides the trust layer.

This layer is the same whether you are running a web application, a
database, or a robot brain. Your OpenShift knowledge transfers
directly.

### Layer 2: Platform services

GitOps (Argo CD) manages all declarative state. ACM governs multi-
cluster policy. Observability (Prometheus, Thanos) provides metrics.
These are the operational services that make the AI workloads
manageable at fleet scale.

### Layer 3: AI workloads

Training pipelines (KFP v2 + Training Operator) produce models. Model
Registry tracks versions and lineage. Fleet Management coordinates
robots. These are the AI-specific applications that run on the
platform.

### Layer 4: Edge

Single Node OpenShift at the factory edge runs inference (KServe +
vLLM), mission dispatch, and local perception. It is ACM-managed and
GitOps-synchronized with the hub.

### Layer 5: Physical

The robots themselves — running VLA policies on Jetson hardware,
connected to the edge cluster over the factory network.

## NVIDIA components mapped to the stack

| Stack layer | NVIDIA component | Role |
|-------------|-----------------|------|
| Simulation | Isaac Sim + Omniverse | Digital twin, training environment, synthetic data |
| Simulation | Nucleus | Asset management for 3D scenes |
| Simulation | PhysX 5 | Physics engine |
| World models | Cosmos Predict | Scenario generation, pre-dispatch validation |
| World models | Cosmos Transfer | Sim-to-real domain adaptation |
| Perception | Cosmos Reason | Scene understanding, safety monitoring |
| Robot brain | GR00T N1 | VLA foundation model for humanoid control |
| Motor control | SONIC | Whole-body controller |
| Inference | NIMs / TensorRT | Optimized model serving |
| Edge hardware | Jetson Orin / Thor | On-robot compute |
| GPU infrastructure | GPU Operator + GFD | Hardware management |

## Red Hat components mapped to the stack

| Stack layer | Red Hat component | Role |
|-------------|------------------|------|
| Platform | OpenShift | Container orchestration, security, networking |
| AI platform | OpenShift AI (RHOAI) | Model serving, training, pipelines, registry |
| Deployment | Argo CD (OpenShift GitOps) | GitOps state management, model promotion |
| Multi-cluster | ACM | Fleet-wide governance, policy enforcement |
| Edge | SNO / MicroShift | Factory-edge Kubernetes |
| Messaging | AMQ Streams (Kafka) | Fleet telemetry, events, cross-cluster federation |
| Service mesh | OpenShift Service Mesh | mTLS, traffic management, observability |
| Secrets | Vault + VSO | Credential management |
| Compliance | Compliance Operator | STIG scanning, remediation tracking |
| Supply chain | Sigstore + Tekton Chains | Image signing, provenance, SBOMs |

## The data flow

```
Isaac Sim renders warehouse scene
    │
    ├─ Replicator extracts RGB + depth + segmentation
    │
    ├─ Cosmos Transfer produces photorealistic variations
    │
    └─ Training pipeline (KFP v2) fine-tunes GR00T/VLA on synthetic data
         │
         └─ Model registered in Registry with full lineage
              │
              └─ Promotion PR opened in Git
                   │
                   └─ Reviewed, merged → Argo CD deploys to edge cluster
                        │
                        └─ KServe serves new policy on L4 GPU
                             │
                             └─ Robot executes missions with new policy
                                  │
                                  └─ Telemetry flows back to hub via Kafka
                                       │
                                       └─ Cosmos Reason monitors camera feeds
                                            │
                                            └─ Anomaly detected → Fleet Manager
                                                 replans → cycle continues
```

## Key insight

The physical AI stack is not a separate universe from enterprise IT.
It is enterprise IT extended with:

- **Simulation** (Isaac Sim) as a first-class workload type alongside
  web apps and databases
- **Foundation models** (GR00T, Cosmos) as a model category alongside
  NLP and recommendation models
- **Physical feedback loops** (robot telemetry, camera feeds) as a
  data source alongside API logs and metrics
- **Edge clusters** (SNO) as deployment targets alongside cloud regions

The platform skills transfer. The infrastructure patterns transfer.
What is new is the physical domain knowledge — the concepts in Part 1
and Part 2 of this guide.

## Key takeaways

- The physical AI stack layers: infrastructure → platform services →
  AI workloads → edge → physical devices.
- NVIDIA provides the simulation, models, and inference optimization.
  Red Hat provides the platform, deployment, governance, and security.
- The data flow connects simulation through training, promotion,
  serving, monitoring, and back — a closed loop from virtual to
  physical.
- Your existing Kubernetes/OpenShift skills are the foundation —
  physical AI extends them, it does not replace them.
