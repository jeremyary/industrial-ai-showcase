# NIMs — NVIDIA Inference Microservices

## What NIMs are

NVIDIA Inference Microservices (NIMs) are pre-packaged, GPU-optimized
containers for deploying AI model inference. Each NIM wraps a specific
model with an optimized inference runtime, industry-standard APIs, and
production-ready configuration.

If you deploy containerized workloads on Kubernetes, NIMs fit directly
into your existing workflow. They are OCI container images pulled from
NVIDIA's NGC registry (`nvcr.io/nim/`), deployed as Deployments or
Jobs, exposed via Services and Routes. The optimization they provide
is inside the container — TensorRT compilation, batching strategies,
and GPU-specific kernel selection that would otherwise require
significant engineering effort.

## How NIMs differ from raw model serving

You can deploy a model from HuggingFace directly: download weights,
write a serving script with FastAPI, handle tokenization, batching,
and concurrency yourself. This works but leaves performance and
operational readiness on the table.

NIMs provide:

**Pre-optimized inference engines**: NIMs use TensorRT, TensorRT-LLM,
vLLM, or other frameworks, selected and tuned per model per GPU. A NIM
for Llama 3.1 on H100 uses a different engine configuration than the
same model on L4. You do not choose or configure the engine — the NIM
selects the optimal path at startup based on the detected hardware.

**Industry-standard APIs**: LLM NIMs expose OpenAI-compatible
endpoints (`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`).
Existing code that calls the OpenAI API works with NIMs by changing
the base URL. VLM NIMs accept images as base64-encoded content in the
messages array, matching the OpenAI multimodal API shape.

**Production packaging**: Health check endpoints, graceful shutdown
handling, Prometheus-compatible metrics, and published CVE reports per
container version. These are the operational basics that custom serving
scripts often lack.

**No model preparation work**: You do not quantize, convert, or
profile the model yourself. The NIM handles optimization at startup.
This is why cold-start times can be 10–60+ seconds — the TensorRT
engine compilation or model loading happens during initialization.

## NIM API shape

For LLM NIMs, the API is OpenAI-compatible:

```
POST http://<nim-host>:8000/v1/chat/completions
Content-Type: application/json

{
  "model": "meta/llama-3.1-8b-instruct",
  "messages": [
    {"role": "user", "content": "What is physical AI?"}
  ],
  "max_tokens": 512
}
```

For VLM NIMs (like Cosmos Reason), images are passed as base64:

```json
{
  "model": "nvidia/cosmos-reason2-8b",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
        {"type": "text", "text": "Is there an obstruction in the aisle?"}
      ]
    }
  ]
}
```

Some specialized NIMs (like Cosmos Transfer) use custom REST APIs
rather than the OpenAI format. The API shape is documented per NIM.

## Deploying NIMs on Kubernetes

NIMs deploy as standard Kubernetes workloads:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama-3-1-8b
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: nim
          image: nvcr.io/nim/meta/llama-3.1-8b-instruct:latest
          env:
            - name: NGC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: ngc-credentials
                  key: api-key
          resources:
            limits:
              nvidia.com/gpu: 1
          ports:
            - containerPort: 8000
```

**Key considerations:**

- **NGC API key**: Required to pull NIM images from `nvcr.io`. Stored
  as a Kubernetes Secret, referenced in the pod spec or image pull
  secret.
- **GPU resources**: `nvidia.com/gpu: 1` requests one GPU from the
  NVIDIA device plugin. The NIM auto-detects the GPU model and selects
  the appropriate optimization profile.
- **Model cache**: First startup downloads model weights and may
  compile TensorRT engines. Use a PVC to cache these across pod
  restarts.
- **Shared memory**: Some NIMs require increased shared memory
  (`/dev/shm`). Set `emptyDir.medium: Memory` for the shm volume.

NVIDIA provides Helm charts for NIM deployment:
- [NIM Helm Deployment](https://docs.nvidia.com/nim/large-language-models/latest/deploy-helm.html)

## NIMs vs. vLLM on KServe

For LLM serving, you have two paths:

**NIM container**: NVIDIA-optimized, pre-packaged, NGC-hosted. Includes
TensorRT-LLM optimizations specific to the GPU. Requires NGC license
(90-day eval available).

**vLLM on KServe**: Open-source model serving via Red Hat OpenShift AI's
KServe integration. Uses the vLLM engine with a ServingRuntime CR.
No NGC license required. You manage the model download and
configuration.

| Aspect | NIM | vLLM on KServe |
|--------|-----|---------------|
| **Optimization** | TensorRT-LLM, GPU-specific profiles | vLLM engine, PagedAttention |
| **API** | OpenAI-compatible | OpenAI-compatible |
| **Model management** | Built into container | Model URI in InferenceService CR |
| **License** | NGC / NVIDIA AI Enterprise | Open source (Apache 2.0) |
| **Autoscaling** | Manual replicas or external | Knative-based, including scale-to-zero |
| **Multi-model** | One model per NIM container | One model per InferenceService |

For many use cases, vLLM on KServe with open-weight models provides
equivalent functionality without the NGC dependency. NIMs provide value
when TensorRT-LLM's GPU-specific optimization yields measurable
throughput or latency improvements.

## Access requirements

NIMs require an **NVIDIA AI Enterprise** subscription or developer
program membership for self-hosted deployment. The NGC API key
authenticates access to the container registry and model downloads.

Free evaluation options:

- **build.nvidia.com**: Hosted NIM endpoints for testing and
  prototyping. No local GPU required.
- **90-day evaluation**: Self-hosted deployment trial available with
  a business email.

## Key takeaways

- NIMs are GPU-optimized, pre-packaged containers for model inference
  — deploy on Kubernetes like any other workload.
- They provide TensorRT optimization, OpenAI-compatible APIs, and
  production packaging (health checks, metrics, CVE scanning).
- Deployment is standard Kubernetes: container image + GPU resource
  request + NGC credentials.
- For LLM serving, NIMs compete with vLLM on KServe — NIMs offer
  deeper optimization, KServe offers open-source flexibility.

## Further reading

- [NVIDIA NIM Overview](https://developer.nvidia.com/nim) —
  Product overview and available models.
- [NIM Documentation](https://docs.nvidia.com/nim/index.html) —
  Technical documentation hub for all NIM types.
- [NIM Getting Started](https://docs.nvidia.com/nim/large-language-models/latest/getting-started.html) —
  Quickstart for deploying your first NIM.
- [Build.nvidia.com](https://build.nvidia.com/) — Try NIMs via
  hosted API endpoints.
