# GPU Architecture for AI Workloads

## Why GPU selection matters

Choosing the right GPU for an AI workload is not about getting "the
fastest one." Different workloads have fundamentally different resource
profiles, and different GPU classes are designed for different points
in that space. Getting this wrong means either wasting expensive
hardware or hitting memory walls that prevent the workload from running
at all.

**VRAM is the primary constraint** for model serving. A model that does
not fit in GPU memory cannot run on that GPU without significant
degradation (offloading to CPU memory, quantization, or sharding across
multiple GPUs). A 7B parameter model in FP16 requires approximately
14 GB just for weights, plus memory for key-value cache, activations,
and framework overhead. Total memory consumption during inference is
typically 1.5–2.5x the model weight size.

**Memory bandwidth** is the secondary constraint for inference. Large
language models are memory-bandwidth-bound during autoregressive
generation — the speed at which tokens are generated is limited by how
fast weights can be read from GPU memory, not by compute throughput.
HBM (High Bandwidth Memory) provides 2–5x the bandwidth of GDDR,
which directly translates to higher token generation rates.

**Compute throughput** is the primary constraint for training. Tensor
cores perform the matrix multiplications that dominate training. More
tensor cores with higher throughput = faster training.

## GPU classes relevant to physical AI

### NVIDIA L4 — Inference at the edge and in the data center

| Spec | Value |
|------|-------|
| Architecture | Ada Lovelace |
| VRAM | 24 GB GDDR6 |
| Memory bandwidth | 300 GB/s |
| TDP | 72 W |
| Tensor cores | 4th generation |
| RT cores | 3rd generation |
| Compute capability | 8.9 |
| Form factor | Single slot, low profile |

**Where it fits**: Dense inference deployment. The low power (72W) and
small form factor enable packing multiple L4s in a server. Fits models
up to ~7B parameters in FP16, or larger models with INT8/INT4
quantization. The go-to GPU for cost-effective inference serving.

**Physical AI use**: Inference serving for VLMs, robot policy serving,
embedding models. Does NOT have the VRAM for large model training or
photorealistic simulation rendering.

### NVIDIA L40S — The converged AI + graphics GPU

| Spec | Value |
|------|-------|
| Architecture | Ada Lovelace |
| VRAM | 48 GB GDDR6 with ECC |
| Memory bandwidth | 864 GB/s |
| TDP | 300 W |
| Tensor cores | 4th generation (FP8 via Transformer Engine) |
| RT cores | 3rd generation |
| Compute capability | 8.9 |

**Where it fits**: The most versatile GPU for physical AI workloads.
48 GB VRAM fits larger models (13B–70B with quantization), runs Isaac
Sim with full ray-traced rendering (RT cores), and handles moderate-
scale training. Good at everything, best-in-class at nothing.

**Physical AI use**: Isaac Sim digital twin (requires RT cores for
photorealistic rendering), VLA training (fine-tuning on 48 GB fits
most models), Cosmos Reason inference, and medium-scale model serving.
Cannot fit Cosmos Transfer at 720p (requires 65 GB).

### NVIDIA A100 — Previous-generation data center workhorse

| Spec | Value |
|------|-------|
| Architecture | Ampere |
| VRAM | 40 GB or 80 GB HBM2e |
| Memory bandwidth | 1.5–2.0 TB/s |
| TDP | 300–400 W |
| Tensor cores | 3rd generation |
| MIG support | Yes (up to 7 instances) |
| Compute capability | 8.0 |

**Where it fits**: Still widely deployed. The 80 GB HBM2e variant
provides more memory than L40S and significantly higher bandwidth.
Suitable for training and serving large models. MIG (Multi-Instance
GPU) support allows partitioning into up to 7 isolated instances for
multi-tenant serving.

**Physical AI use**: Large model training, high-throughput inference.
Does NOT have RT cores for photorealistic rendering — cannot run
Isaac Sim with ray tracing.

### NVIDIA H100 / H200 — Current-generation data center

| Spec | H100 | H200 |
|------|------|------|
| Architecture | Hopper | Hopper |
| VRAM | 80 GB HBM3 | 141 GB HBM3e |
| Memory bandwidth | 3.35 TB/s | 4.8 TB/s |
| Tensor cores | 4th generation (Transformer Engine) |
| MIG support | Yes (up to 7 instances) |
| Compute capability | 9.0 |

**Where it fits**: Large-scale training and serving of the biggest
models. The H200's 141 GB HBM3e holds 70B+ parameter models in FP16
without sharding. 4.8 TB/s bandwidth delivers exceptional token
generation throughput.

**Physical AI use**: Cosmos Transfer at 720p (65 GB requirement fits
in H100/H200), large VLA training, Cosmos Predict inference. The
validated GPU class for NVIDIA's NIM containers.

### NVIDIA B200 / GB200 — Next generation (Blackwell)

| Spec | B200 |
|------|------|
| Architecture | Blackwell |
| VRAM | 192 GB HBM3e |
| Memory bandwidth | ~8 TB/s |
| Tensor cores | 5th generation (FP4 support) |
| Compute capability | 10.0+ |

**Where it fits**: Frontier-scale training and inference. GB200 NVL72
connects 72 GPUs into a single NVLink domain for training
trillion-parameter models. Not commonly available for most enterprise
deployments yet.

**Physical AI use**: Cosmos Transfer/Predict with maximum batch sizes,
largest VLA training, next-generation model development.

### NVIDIA Jetson — Edge compute for robots

| Platform | VRAM | Architecture | Use case |
|----------|------|-------------|----------|
| Jetson Orin Nano | 8 GB unified | Ampere | Basic edge inference |
| Jetson Orin NX | 8–16 GB unified | Ampere | Mid-range robot inference |
| Jetson AGX Orin | 32–64 GB unified | Ampere | High-end robot inference |
| Jetson AGX Thor | 128 GB unified | Blackwell | VLA serving, on-robot foundation models |

Jetson modules use **unified memory** — CPU and GPU share the same
memory pool. This is different from discrete GPUs where CPU and GPU
memory are separate. Unified memory simplifies programming (no manual
CPU↔GPU copies) but limits available memory to a single pool.

**Physical AI use**: On-robot inference for VLA policies, local
perception, and autonomous operation. Jetson Thor's 128 GB unified
memory is specifically designed for running transformer-based VLA
models on the robot itself.

## Key GPU specs for physical AI workloads

| Workload | Critical spec | Recommended GPU |
|----------|--------------|----------------|
| Isaac Sim (ray tracing) | RT cores + VRAM ≥ 16 GB | L40S |
| VLA training (fine-tune) | VRAM ≥ 40 GB + bandwidth | L40S, A100 80 GB, H100 |
| VLA inference (serving) | VRAM ≥ 16 GB + low latency | L4, L40S |
| Cosmos Reason (8B VLM) | VRAM ≥ 16 GB | L40S, L4 (quantized) |
| Cosmos Transfer (2B, 720p) | VRAM ≥ 65 GB | H100, H200, Jetson Thor |
| Cosmos Predict (2B) | VRAM ≥ 33 GB | L40S, H100 |
| On-robot inference | Power ≤ 60W, VRAM ≥ 8 GB | Jetson Orin, Jetson Thor |

## Tensor cores and precision

Tensor cores are specialized hardware units on NVIDIA GPUs designed
for the matrix multiplications that dominate deep learning. Each GPU
generation adds support for lower-precision data types that enable
faster compute and smaller memory footprint:

| Precision | Bits per element | Memory savings vs. FP32 | Typical use |
|-----------|-----------------|------------------------|-------------|
| FP32 | 32 | baseline | Legacy training |
| TF32 | 19 (Tensor Float) | ~1.7x | Training (automatic on Ampere+) |
| BF16 | 16 (Brain Float) | 2x | Training (standard) |
| FP16 | 16 | 2x | Inference, some training |
| FP8 | 8 | 4x | Inference (Hopper Transformer Engine) |
| INT8 | 8 | 4x | Quantized inference |
| INT4 | 4 | 8x | Aggressive quantization |
| FP4 | 4 | 8x | Next-gen inference (Blackwell) |

The **Transformer Engine** (Hopper and later) automatically selects
between FP8 and FP16 precision per-layer during transformer model
execution, maximizing throughput while maintaining accuracy.

## GPU partitioning

### Whole-GPU allocation

One pod gets one entire GPU. Simplest model, maximum isolation, and
fully predictable performance. No GPU sharing overhead. This is the
recommended approach for production AI inference where latency
predictability matters.

### Multi-Instance GPU (MIG)

Available on A100, H100, and H200. Partitions a single GPU into up to
7 isolated instances, each with dedicated streaming multiprocessors,
memory bandwidth, and VRAM. MIG provides hardware-level isolation and
guaranteed QoS between tenants.

**Not available on L4 or L40S.**

### Time-slicing

The GPU multiplexes between workloads in time. All workloads share the
same memory space — no isolation, no fault boundaries, no performance
guarantees. Acceptable for development and non-latency-sensitive
workloads. Not recommended for production inference.

## Key takeaways

- VRAM is the primary constraint for model serving — the model must
  fit in GPU memory.
- L4 (24 GB, 72W) is the cost-effective inference GPU. L40S (48 GB,
  RT cores) is the versatile physical AI GPU. H100/H200 handle the
  largest models and training workloads.
- RT cores (L40S, RTX GPUs) are required for photorealistic simulation
  rendering — not all GPUs have them.
- Jetson provides edge compute for on-robot inference, with unified
  memory simplifying deployment.
- Whole-GPU allocation is the default for production; MIG for
  multi-tenant on H-class GPUs.

## Further reading

- [NVIDIA CUDA GPUs](https://developer.nvidia.com/cuda-gpus) —
  Complete list of GPU compute capabilities.
- [NVIDIA L40S Datasheet](https://www.nvidia.com/en-us/data-center/l40s/) —
  Specifications and use cases.
- [NVIDIA H100 Datasheet](https://www.nvidia.com/en-us/data-center/h100/) —
  Data center GPU specifications.
- [NVIDIA Jetson](https://developer.nvidia.com/embedded-computing) —
  Edge compute platform for robotics.
- [GPU Operator on OpenShift](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/index.html) —
  Deploying and managing GPUs on OpenShift.
- [Multi-Instance GPU](https://www.nvidia.com/en-us/technologies/multi-instance-gpu/) —
  MIG overview and documentation.
