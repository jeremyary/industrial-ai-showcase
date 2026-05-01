# MLOps for Physical AI

## Why MLOps matters more for robots

If you have experience with ML in production — model training pipelines,
experiment tracking, model registries, A/B testing — you have a head
start. But MLOps for physical AI introduces constraints that software
ML does not face:

**Physical consequences of model failures.** A recommendation model
that serves a bad suggestion loses a click. A robot policy that
generates a bad action damages equipment, drops a part, or injures a
person. The deployment pipeline must be more rigorous.

**Multi-stage artifact chain.** A software ML model has a dataset and
a checkpoint. A physical AI model has a simulation scene, synthetic
data generation parameters, domain randomization settings, domain
adaptation outputs, training hyperparameters, evaluation results in
simulation, evaluation results on hardware, and deployment
configuration. Every link in this chain must be traceable.

**Environment-dependent performance.** A language model works the same
way regardless of where it runs (modulo hardware speed). A robot policy
trained in simulation may behave differently on different physical
robots due to calibration differences, sensor variations, and
environmental factors. Deployment must account for per-site
calibration.

**Safety certification.** Regulated industries (automotive, aerospace,
pharmaceutical) require evidence that the deployed model meets safety
standards. This means tracing from the deployed inference endpoint back
through the training pipeline to the source data, with every step
auditable and reproducible.

## The physical AI MLOps lifecycle

```
1. Data Collection
   ├── Simulation: Isaac Sim scenes, domain randomization, synthetic data
   ├── Teleoperation: Human-operated robot demonstrations
   └── Production: Real-world data from deployed robots

2. Data Preparation
   ├── Domain adaptation (Cosmos Transfer)
   ├── Data curation and filtering (Cosmos Reason)
   └── Dataset assembly and versioning

3. Training
   ├── Foundation model fine-tuning (LoRA, full fine-tune)
   ├── Distributed training (multi-GPU, multi-node)
   └── Experiment tracking (MLflow)

4. Evaluation
   ├── Simulation evaluation (Isaac Sim, task success rate)
   ├── Hardware validation (real-robot test suite)
   └── Safety verification (constraint checking)

5. Registration
   ├── Model registry entry (version, lineage, metrics)
   ├── Artifact signing (Sigstore)
   └── SBOM generation

6. Deployment
   ├── Promotion (GitOps: PR → review → merge → Argo CD sync)
   ├── Model serving (KServe, vLLM, custom predictor)
   └── Per-site configuration (calibration, safety limits)

7. Monitoring
   ├── Inference telemetry (latency, throughput, error rate)
   ├── Task performance (success rate, completion time)
   ├── Anomaly detection (behavioral drift)
   └── Fleet-level analytics
```

## Key MLOps components

### Experiment tracking (MLflow)

MLflow records every training run with its hyperparameters, metrics,
artifacts, and lineage. For physical AI, the experiment record must
include:

- **Source data**: Which simulation scenes were used? What domain
  randomization parameters? What teleoperation sessions?
- **Training configuration**: Model architecture, learning rate,
  batch size, number of steps, GPU type, training duration.
- **Metrics**: Training loss, validation loss, simulation task success
  rate, sim-to-real transfer accuracy.
- **Artifacts**: Model checkpoints, evaluation videos, configuration
  files.

MLflow provides the audit trail: given a deployed model, you can trace
back to exactly how it was trained, on what data, with what results.

### Training pipelines (Kubeflow Pipelines / KFP v2)

Kubeflow Pipelines automate the training workflow as a directed acyclic
graph (DAG) of steps:

```
Data preparation → Fine-tuning → Evaluation → Validation → Registration
```

Each step runs as a container in Kubernetes. Pipelines ensure
reproducibility — the same pipeline definition with the same inputs
produces the same outputs. They also handle resource scheduling (GPU
allocation), artifact passing between steps, and failure handling.

In the physical AI context, the pipeline often includes simulation-
specific steps:

```
Scene generation → Synthetic data rendering → Domain adaptation →
Dataset assembly → Fine-tuning → Sim evaluation → Hardware evaluation →
Model registration
```

### Model registry

A centralized catalog of trained models with metadata: version, source
dataset, training run, evaluation metrics, deployment status, and
lineage. The registry is the handoff point between training (data
science) and deployment (platform engineering).

For physical AI, the registry must capture robot-specific metadata:

- **Embodiment**: Which robot platform is this model trained for?
- **Action space**: What actions does the model output?
- **Sensor requirements**: What cameras/sensors does the model expect?
- **Safety constraints**: What are the model's operational limits?

### Model serving (KServe)

KServe provides Kubernetes-native model serving with:

- **InferenceService**: A CRD that declares what model to serve, from
  where, with what resources.
- **ServingRuntime**: Defines the inference engine (vLLM for
  transformer-based VLAs, custom predictors for other architectures).
- **Autoscaling**: Scale replicas based on request load, including
  scale-to-zero for bursty workloads.
- **Canary deployment**: Route a percentage of traffic to a new model
  version for gradual rollout.

For physical AI, model serving latency is critical: inference must
complete within the robot's control loop deadline (typically
10–100ms for manipulation, 50–500ms for navigation).

## GitOps for model deployment

Model promotion in physical AI follows the GitOps pattern:

1. **Training completes** → model registered in registry with version
   and metrics.
2. **Promotion request** → a PR is opened that updates the
   InferenceService manifest in Git to point to the new model version.
3. **Review** → human (or automated) review checks metrics, safety
   evaluation results, and lineage.
4. **Merge** → the PR is merged, changing the declared state in Git.
5. **Sync** → Argo CD detects the change and rolls out the new model
   version.
6. **Verify** → monitoring confirms the new model performs as expected
   in production.

This pattern provides the auditability that regulated industries
require: every model deployment is a reviewed, approved Git commit
with a traceable chain from training data to production serving.

### Rollback

If the new model causes degraded performance or safety concerns:

1. `git revert` the promotion commit.
2. Argo CD detects the revert and rolls back to the previous model
   version.
3. The rollback is another Git commit — auditable, timestamped, with
   the reason documented.

This is identical to how configuration rollbacks work in GitOps — the
model is just another piece of declarative cluster state.

## Physical AI-specific challenges

### Sim-to-real evaluation

Simulation evaluation (task success rate in Isaac Sim) is necessary but
not sufficient. A model that achieves 95% success in simulation may
achieve 60% on real hardware due to the sim-to-real gap. The evaluation
pipeline must include real-hardware tests before promotion, even if
they are limited in scope.

### Per-site calibration

A warehouse in Phoenix and a warehouse in Munich have different layouts,
lighting, and ambient conditions. A model fine-tuned on one may
underperform on the other. The deployment pipeline must support per-site
configuration (camera calibration, workspace boundaries, safety zones)
without retraining the model.

### Continuous learning

Deployed robots generate data that can improve future models. The
challenge is closing this loop while maintaining data quality (not all
production data is useful for training), privacy (production data may
contain PII), and safety (a model trained on production data
inherits any biases or errors in that data).

### Fleet-wide consistency

When managing a fleet of robots across multiple sites, the deployment
pipeline must ensure version consistency — or intentional version
differences where sites are at different rollout stages. ACM
(Advanced Cluster Management) and ApplicationSets provide the
multi-cluster deployment mechanisms.

## Key takeaways

- MLOps for physical AI requires rigorous traceability from deployed
  model back through training, evaluation, and source data — more
  rigorous than software ML because failures have physical consequences.
- The lifecycle includes simulation-specific stages: scene generation,
  synthetic data rendering, domain adaptation, and sim-to-real
  evaluation.
- GitOps provides the deployment mechanism: model promotions are
  reviewed PRs, and rollbacks are git reverts.
- Experiment tracking (MLflow), training pipelines (KFP), model
  registries, and model serving (KServe) compose into the full stack.

## Further reading

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html) —
  Open-source experiment tracking and model registry.
- [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/) —
  Kubernetes-native ML pipeline orchestration.
- [KServe Documentation](https://kserve.github.io/website/) —
  Kubernetes-native model serving.
- Sculley, D., et al. (2015). "Hidden Technical Debt in Machine
  Learning Systems." *NeurIPS 2015*. — The foundational paper on the
  operational challenges of ML in production.
