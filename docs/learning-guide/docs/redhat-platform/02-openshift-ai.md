# Red Hat OpenShift AI (RHOAI)

## What RHOAI is

Red Hat OpenShift AI (formerly Red Hat OpenShift Data Science) is the
AI/ML platform that installs as an operator on OpenShift. It provides
the tools for the full ML lifecycle: model development, training
pipelines, experiment tracking, model serving, and model registry.

RHOAI installs from OperatorHub. The operator creates a
`DataScienceCluster` CR that manages its components. The current
release line is 3.x, with early-access features available alongside
generally available ones.

- [RHOAI Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/)

## Core components

### KServe — Model serving

KServe is the primary model serving component for large models (LLMs,
VLMs, VLAs). It provides Kubernetes-native model deployment with two
CRDs:

**ServingRuntime**: Defines the inference engine. RHOAI ships
pre-configured runtimes for vLLM on NVIDIA, AMD, and Intel hardware.
The ServingRuntime specifies the container image, protocol (REST,
gRPC), and resource defaults.

**InferenceService**: Declares what model to serve — the model
location (S3 URI, PVC path), the ServingRuntime to use, and the
resource requirements (GPU count, memory).

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vla-policy
spec:
  predictor:
    model:
      modelFormat:
        name: vLLM
      runtime: vllm-nvidia-runtime
      storageUri: s3://models/vla-policy-v1.4
      resources:
        limits:
          nvidia.com/gpu: 1
```

KServe depends on OpenShift Serverless (Knative Serving) for
autoscaling (including scale-to-zero) and OpenShift Service Mesh for
traffic management. A `RawDeployment` mode is available for simpler
setups without Knative/Service Mesh dependencies.

- [KServe on RHOAI](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html-single/deploying_models/)

### Data Science Pipelines (KFP v2)

Kubeflow Pipelines v2 for automating ML workflows. Pipelines are
defined as Python code using the KFP SDK, compiled to YAML, and
submitted to the pipeline server.

A typical physical AI pipeline:

```
data_prep → fine_tune → evaluate → validate_onnx → register_model
```

Each step runs as a container with defined inputs, outputs, and
resource requirements. The `DataSciencePipelinesApplication` (DSPA) CR
deploys the pipeline server in a namespace.

Pipelines are declarative: the YAML definition can be stored in Git
and managed via GitOps, making pipeline versions as auditable as any
other cluster configuration.

- [Data Science Pipelines on RHOAI](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/working_with_data_science_pipelines/)

### Model Registry

A centralized catalog of trained models with metadata:

- **Version**: Which training run produced this model
- **Lineage**: What dataset, hyperparameters, and pipeline produced it
- **Metrics**: Training loss, validation accuracy, task success rate
- **Deployment status**: Where is this model currently serving
- **Format**: ONNX, PyTorch, TensorRT

The registry is the bridge between training (data science team) and
deployment (platform team). A data scientist registers a model; a
platform engineer promotes it to production via GitOps.

### MLflow

MLflow (Developer Preview in RHOAI 3.x) provides experiment tracking
and model management:

- **Experiment tracking**: Log hyperparameters, metrics, and artifacts
  per training run. Compare runs visually. Identify the best
  configuration.
- **Model versioning**: Track model versions with stage transitions
  (staging → production).
- **Artifact storage**: Model checkpoints, evaluation results,
  configuration files stored alongside the training run.

MLflow uses Kubernetes namespaces as workspaces and Kubernetes RBAC
for authorization. The Red Hat-published container is
`rhoai/odh-mlflow-rhel9`.

### Training Operator (KFTO)

The Kubeflow Training Operator manages distributed training jobs on
Kubernetes. It creates `PyTorchJob` CRs that define master and worker
pods across multiple nodes and GPUs.

For physical AI, this is how foundation model fine-tuning runs:

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: groot-finetune
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      template:
        spec:
          containers:
            - name: train
              image: training-image:latest
              resources:
                limits:
                  nvidia.com/gpu: 1
    Worker:
      replicas: 3
```

The Training Operator handles pod lifecycle, distributed communication
setup (rendezvous), and failure recovery. Kueue manages job scheduling
and GPU quota enforcement.

### Kueue — Workload scheduling

Red Hat's build of Kueue provides quota management and prioritized job
scheduling for AI workloads. It manages:

- `ClusterQueues` with GPU-class-aware resource budgets
- `LocalQueues` per namespace for team-level allocation
- Priority-based scheduling (training yields to inference during demos)
- Preemption policies for urgent workloads

Kueue is the scheduler that ensures training jobs do not starve
inference services when GPU resources are limited.

## How components compose

The components form an end-to-end MLOps workflow:

1. **Develop** in Jupyter notebooks (RHOAI Workbenches)
2. **Automate** with Data Science Pipelines (KFP v2)
3. **Train** with Training Operator, scheduled by Kueue
4. **Track** experiments and artifacts in MLflow
5. **Register** models in Model Registry with lineage metadata
6. **Serve** via KServe with vLLM runtimes, autoscaled by Knative
7. **Promote** new model versions through GitOps (PR → merge → Argo CD)
8. **Monitor** via OpenShift monitoring + DCGM GPU telemetry

Every step is declarative, auditable, and manageable through the same
Kubernetes primitives you already know.

## Key takeaways

- RHOAI provides the full ML lifecycle on OpenShift: notebooks,
  pipelines, training, experiment tracking, model registry, and
  serving.
- KServe with vLLM is the model serving standard — InferenceService
  CRs declare the model, ServingRuntime CRs declare the engine.
- KFP v2 pipelines automate training workflows as DAGs of containerized
  steps.
- MLflow tracks experiments; Model Registry catalogs artifacts; Kueue
  manages GPU scheduling.
- The entire stack is operator-managed and GitOps-compatible.

## Further reading

- [RHOAI Self-Managed Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4) —
  Comprehensive platform documentation.
- [KServe Documentation](https://kserve.github.io/website/) —
  Upstream model serving project.
- [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/) —
  Upstream pipeline orchestration.
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html) —
  Experiment tracking and model registry.
