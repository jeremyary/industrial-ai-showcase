# 08 — GPU Resource Planning

The OSD hub has **two classes of GPUs** — L40S and L4 — each numbered 2 to 3 nodes. Total GPU pool: **4 to 6 GPUs**. The constraint is **pod-per-GPU within each class** — no MIG, no time-slicing, no vGPU partitioning. Workloads are pinned to the class appropriate for their profile via `nodeSelector: { gpu-class: l40s | l4 }`.

This document is the canonical source for how GPUs are allocated. Every component that consumes GPU declares its class and footprint here; changes require updating this document.

## Hardware baseline

**L40S pool (2–3 nodes)** — ray-traced simulation, physics, training, large-model serving
- 48 GB GDDR6 ECC — comfortably fits GR00T + KV cache, Cosmos Predict/Transfer, large agent brains.
- Ada Lovelace, 4th-gen RT cores — strong for Isaac Sim's ray-traced sensor rendering.
- ~90 TFLOPS FP32, 300 W TDP.
- GFD label: `nvidia.com/gpu.product=NVIDIA-L40S` (confirm exact string in Phase 0 baseline).

**L4 pool (2–3 nodes)** — inference, VLMs, agent serving, embeddings
- 24 GB GDDR6 — fits most inference workloads comfortably; will not fit GR00T with generous KV cache.
- Ada Lovelace, inference-optimized.
- ~30 TFLOPS FP32, 72 W TDP.
- GFD label: `nvidia.com/gpu.product=NVIDIA-L4` (confirm exact string in Phase 0 baseline).

Both pools enforce pod-per-GPU via the NVIDIA GPU Operator default (`mig.strategy: none`, no time-slicing entries in the device plugin config).

**Provisioning note**: GPU node provisioning on OSD is SRE-managed cloud infrastructure (instance family selection, node count adjustments go through SRE). GPU labels, however, are applied automatically by NVIDIA GPU Operator's GFD component and require no customer intervention. Record actual product-label values and instance families in `infrastructure/baseline/osd-hub-state.md`.

## The scheduling problem, simplified

Because the two classes are distinct pools, the scheduling problem splits cleanly. L40S-class workloads contend only with other L40S-class workloads; L4-class workloads contend only with other L4-class workloads. The rotating-slot friction of a single-class 3-GPU plan largely dissolves.

Within each class, scheduling is still pod-per-GPU with priority classes and queueing for bursty consumers.

## GPU consumers by class

Each entry includes class assignment and rationale.

### L40S-class consumers

#### GC-1: Omniverse Kit App Streaming render session
- **Class**: L40S. RT cores matter for quality rendering; 48 GB headroom for scene complexity growth.
- **Footprint**: 1 GPU per active streaming session.
- **Mode**: always-on during demo hours.
- **Notes**: one concurrent streaming session per GPU; concurrent seller demos would need additional L40S nodes.

#### GC-2: Isaac Sim live demo instance
- **Class**: L40S. Ray-traced sensor rendering + physics; this is the clearest-cut L40S case.
- **Footprint**: 1 GPU per sim instance.
- **Mode**: always-on during demo hours.

#### GC-3: GR00T N1.7 serving (vLLM)
- **Class**: L40S. Model + action-head + KV cache footprint for typical batch sizes exceeds comfortable L4 headroom; latency goal also benefits from L40S compute.
- **Footprint**: 1 GPU.
- **Mode**: warm-pinned during humanoid-exercising demos; scale-from-zero otherwise.

#### GC-4: Cosmos Predict 2.5 NIM
- **Class**: L40S. World-model inference with sizable memory needs.
- **Footprint**: 1 GPU.
- **Mode**: bursty (synthetic data generation + agent-tool use); not concurrent with a live operational demo by default.

#### GC-5: Cosmos Transfer NIM
- **Class**: L40S.
- **Footprint**: 1 GPU.
- **Mode**: bursty. Often queued behind Cosmos Predict in pipeline flows.

#### GC-7: Isaac Lab training workers
- **Class**: L40S. Training benefits from the larger VRAM for batch size and the higher FP32 throughput.
- **Footprint**: 1 GPU per worker; scales to 2–3 workers for data-parallel training.
- **Mode**: bursty; runs during explicit training windows (Mode C). Must not run concurrently with a live demo's Kit + Isaac Sim allocation.

#### GC-6: Cosmos Reason 2-8B (VLM perception)
- **Class**: L40S. 8B **Qwen3-VL-derivative** model in bfloat16; NVIDIA specs 32 GB minimum. `--max-model-len=8192` (image-token footprint exceeds the 4096 default). Requires **vLLM ≥ 0.11.0** + `--reasoning-parser qwen3`.
- **Footprint**: 1 GPU.
- **Mode**: warm during demos exercising camera-driven situational awareness (the Phase-1 warehouse-obstruction beat and its Phase-2+ variants).
- **Notes**: supersedes the earlier Metropolis VSS slot per ADR-027. Consumed by the hub-side obstruction-detector pod. The 2B variant was trialed on L4 and failed the quality bar (couldn't distinguish empty from pallet-blocked aisle); 8B on L40S is the Phase-1 choice.

### L4-class consumers

#### GC-8: USD Search API embedding
- **Class**: L4. Embedding generation is lightweight and batch-tolerant.
- **Footprint**: 1 GPU when active; idle most of the time.
- **Mode**: cold; activates only during bulk asset-indexing runs.

#### GC-9: USD Code / USD Verify NIMs
- **Class**: L4. Small models; inference-characteristic; agent-invoked.
- **Footprint**: 1 GPU each when active.
- **Mode**: cold until an agent calls them; KServe scale-from-zero.

#### GC-10: LangGraph agent brain LLM (Phase 3+)
- **Class**: L4 by default. The chosen model must fit in 24 GB (this constrains OD-5 — Qwen3-14B in int4 or Nemotron-Nano variants fit; larger Nemotron or DeepSeek models push toward L40S).
- **Footprint**: 1 GPU.
- **Mode**: warm during agent-enabled demos; scale-from-zero otherwise.
- **Fallback**: if no suitable model fits 24 GB while preserving tool-use quality, target an L40S slot instead. Record the decision as an addendum to ADR-018.

## Runtime modes

The cluster operates in a named mode at any time. The Showcase Console backend observes the mode and advises sellers accordingly.

### Mode A — Demo (full GPU configuration)

L40S allocation:
- L40S-1 → GC-1 Kit App Streaming render session (demo-critical)
- L40S-2 → GC-2 Isaac Sim live demo (demo-critical)
- L40S-3 → GC-6 Cosmos Reason 2-8B (warm during Phase-1 warehouse demo)
- L40S-4 → rotating: GC-3 GR00T, or GC-4/GC-5 Cosmos when the scenario exercises synthetic data (Phase 2+ humanoid / synthetic-data scenarios)

L4 allocation:
- L4-1 → GC-10 agent brain (Phase 3+) or GC-9 USD Code/Verify rotating slot
- L4-2 → free / bursty (USD Search embeddings, small NIMs, scale-from-zero workloads)

All demo-critical workloads run warm; rotating slots cycle on scenario transitions with visible "staging next scenario" pauses (20–40 seconds) covered by the Console's transition screens.

### Mode B — Demo (degraded: one GPU node down in either class)

Degradation is class-specific:

- **L40S degraded (one L40S down)**: L40S-4 rotating slot is unavailable first. Scenarios requiring GR00T or Cosmos Predict/Transfer concurrent with Kit streaming + Isaac Sim + Cosmos Reason fall back to replay mode for the affected beats. If Cosmos Reason's node drops, the warehouse-obstruction beat goes cold. Kit streaming + Isaac Sim remain live; the visible demo still feels intact.
- **L4 degraded (one L4 down)**: agent brain or USD Code/Verify is unavailable. Console surfaces the constraint and selects scenarios that don't need the lost workload.

In either case, the seller doesn't have to cancel — the Console routes them to a compatible scenario selection.

### Mode C — Training

Entered explicitly via a `TrainingWindow` CR; the Showcase Console refuses live demos while the CR is active and shows the window's end time.

- All L40S nodes available for Isaac Lab training workers (data-parallel across 2–3 workers).
- Optional: Cosmos Predict / Transfer pipeline runs on one L40S concurrently with training on the others, if scheduled.
- **L4 pool continues serving** — agent brain, USD Code/Verify stay available. Cosmos Reason lives on L40S and is affected by training windows unless a dedicated L40S slot is reserved. Agent-driven analyses and small-NIM flows can continue during training windows as long as they don't need L40S themselves.

Exiting training mode: ongoing training jobs are checkpointed and either paused or terminated; demo-stack scale-from-zero brings things back in ~2 minutes.

## Scheduling mechanics

How the cluster actually enforces the above.

### Node labels and nodeSelector pinning

Every GPU-consuming pod declares:
```yaml
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-L40S   # or: NVIDIA-L4
resources:
  limits:
    nvidia.com/gpu: 1
```

No custom labels, no taint+toleration layer on top. GFD's automatic labeling is the authoritative source; the `nvidia.com/gpu: 1` resource request is the GPU-requirement gate. This is intentionally minimal — ADR-018 explicitly rejects introducing custom `gpu-class` labels to avoid duplicating GFD's work and drift risk.

The GPU Operator ClusterPolicy ensures GFD labels survive node replacement; no cluster-admin intervention needed beyond validating the labels are present during Phase 0 baseline.

Exact product-label strings must be verified during Phase 0: run `oc get nodes -l nvidia.com/gpu.present=true -o json | jq '.items[].metadata.labels'` and record the exact values in `infrastructure/baseline/osd-hub-state.md`. The expected strings are `NVIDIA-L40S` and `NVIDIA-L4`, but GPU Operator version variations occasionally produce different casing or suffixes — use whatever GFD actually applies.

### Priority classes

Three PriorityClass definitions in `infrastructure/gitops/apps/priority-classes/`:

- `demo-critical` (1_000_000): Kit App Streaming + Isaac Sim live. Preempts anything below in its namespace.
- `demo-rotating` (100_000): GR00T, Cosmos-as-agent-tool, Cosmos Reason, agent brain — whichever is the active rotating slot in either class. Preempts training jobs on its GPU.
- `training` (1_000): Isaac Lab workers, Cosmos NIMs when serving the synthetic-data pipeline. Yields to anything above.

### Per-class scheduling discipline

Mode transitions use customer-applied role labels *on top of* the GFD product labels, managing which pods occupy which specific node within a class. In Mode A, three L40S nodes carry the custom label `role=demo-pinned` (Kit streaming, Isaac Sim, Cosmos Reason) and a fourth L40S (if provisioned) carries `role=demo-rotating` (GR00T / Cosmos Predict-Transfer, scenario-dependent). L4 nodes carry `role` values like `agent-brain` or `available`. These role labels are customer-applied (cluster-admin makes this direct) and are orthogonal to the GFD-applied product labels — workloads pin via both: `nvidia.com/gpu.product` for class, `role` for within-class assignment.

Mode transitions update role labels via a small controller or Ansible playbook. Observable via `oc get nodes -l nvidia.com/gpu.present=true --show-labels`.

### Preemption and training window discipline

Same pattern as before: training jobs submit via Kubeflow Pipelines, are queued through Kueue, and run only during declared training windows (via `TrainingWindow` CR). Outside training windows, the cluster is always in Mode A.

Kueue's ClusterQueue definitions are class-aware — an L40S ClusterQueue and an L4 ClusterQueue — so the queue manager knows which pool a job targets.

### KServe scale-from-zero

All inference services use `minReplicas: 0`. GR00T, Cosmos, Cosmos Reason, USD Code/Verify, agent brain — all drop to zero when idle, freeing their GPU. Cold-start latency is 10–40 seconds; the Showcase Console's scenario transitions account for this.

Kit App Streaming runs pinned (no scale-from-zero) during demo hours — cold-start latency is unacceptable mid-meeting.

## Capacity planning by phase

Each phase's GPU profile.

### Phase 0 — Foundation
- GPU consumers: none steady-state; only validation tests on both classes.
- Runs in any configuration.

### Phase 1 — Mega Core
- Steady-state: GC-1, GC-2, GC-6 (L40S always-on during Phase-1 warehouse demo).
- Phase 1 requires **3 L40S** to run all warm-pinned workloads concurrently. GR00T / Cosmos Predict-Transfer rotating slot needs a 4th L40S to be warm alongside; otherwise it's scale-from-zero on the rotating slot when needed.
- Degraded (Mode B) scenarios still operate meaningfully because the agent brain (Phase 3+) and smaller NIMs run on L4.

### Phase 2 — MLOps, Edge, Multi-Site
- Adds GC-7 Isaac Lab (L40S, Mode C only).
- Demo scenarios don't change GPU profile from Phase 1.
- Training windows scheduled via calendar coordination; Console enforces via `TrainingWindow` CR.

### Phase 3 — Agentic + Synthetic Data
- Adds GC-4, GC-5 Cosmos (L40S, bursty) and GC-9 USD Code/Verify (L4, bursty).
- Adds GC-10 agent brain (L4 by default — model selection is OD-5; if chosen model exceeds 24 GB, promotes to L40S).
- Synthetic-data generation campaigns run in Mode C; agent-driven short explorations run in Mode A using the rotating L40S slot.

### Phase 4 — Verticalization
- No new per-scenario GPU consumers. Additional scenario packs reuse existing footprint.
- Concurrent-seller demos require adding GPU nodes.

## Observability for GPU allocation

Dashboards a human can check at a glance:

- **"Mode status"** (Grafana panel, embedded in Showcase Console expert drawer): which mode, which pods occupy which GPUs per class, time-in-current-mode.
- **DCGM metrics**: per-GPU utilization, memory, temperature, power. Grouped by class.
- **Queue depth** (Kueue metrics): pending training jobs per class, wait times.
- **Scale-from-zero events** (KServe metrics): cold-starts observed per service, used for tuning transition timing.
- **Class imbalance alert**: triggers if a workload lands on the wrong `nvidia.com/gpu.product` class — signals a nodeSelector mistake, chart misconfiguration, or a default Helm value that silently targeted the wrong class.

## Discipline for adding GPU workloads

When proposing a new GPU consumer:

1. **Classify**: always-on, rotating, or bursty?
2. **Measure memory**: does it fit 24 GB (target L4) or does it need 48 GB (target L40S)?
3. **Measure cold-start**: if >60 seconds, it needs pinning during relevant demos.
4. **Assign class**: based on memory + workload character. Document why.
5. **Update this document**: new GC-N entry with class assignment.
6. **Update mode tables**: if it changes concurrency in either class.
7. **Update phase capacity planning**: which phase introduces it.

Don't merge a PR that adds a GPU workload without completing this checklist.

## Future: MIG on higher-end GPUs (not current concern)

Neither L40S nor L4 supports MIG. If the pool is ever upgraded to H100 / GB200-class GPUs that support MIG, the class model gets richer: a single H100 can carry several MIG partitions, each able to host a distinct inference workload. That's a post-reference consideration; current plan assumes whole-GPU workloads throughout.
