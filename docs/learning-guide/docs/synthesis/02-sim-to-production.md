# From Simulation to Production

## The end-to-end lifecycle

This chapter traces the complete lifecycle of a physical AI capability
— from the moment someone asks "can we automate pallet handling in the
warehouse?" to a fleet of robots performing the task in production.
Each step maps to concepts and technologies covered earlier in this
guide.

## Phase 1: Digital twin construction

**Goal**: Create a physically accurate virtual replica of the target
environment.

**Activities**:

- Import facility CAD data (floor plans, racking layouts, equipment
  positions) into OpenUSD format via Omniverse Connectors
- Enrich with physics properties: collision meshes, material
  properties (friction, mass), actuator models
- Configure sensors: camera positions, LiDAR placements, depth sensor
  fields of view
- Store the twin in Nucleus for collaborative access
- Validate: does the virtual warehouse look and behave like the real
  one?

**Technologies**: OpenUSD, Omniverse Connectors, Nucleus, Isaac Sim

## Phase 2: Simulation and training

**Goal**: Train a robot policy that can perform the target task in
simulation.

**Activities**:

- Define the task in Isaac Lab: observations (camera images,
  proprioception), actions (joint commands, gripper), rewards (task
  completion, collision avoidance, efficiency)
- Run reinforcement learning or imitation learning across thousands
  of parallel environments
- Apply domain randomization: randomize lighting, textures, object
  positions, physics parameters
- Generate synthetic training data with Omniverse Replicator:
  annotated RGB, depth, segmentation
- Apply domain adaptation with Cosmos Transfer: make synthetic data
  photorealistic
- Track experiments in MLflow: hyperparameters, metrics, artifacts

**Technologies**: Isaac Sim, Isaac Lab, Omniverse Replicator, Cosmos
Transfer, MLflow, PyTorch

## Phase 3: Evaluation and validation

**Goal**: Verify that the trained policy works — first in simulation,
then on real hardware.

**Activities**:

- Evaluate in simulation: run the policy across diverse test scenarios
  in Isaac Sim, measure success rate, collision rate, and efficiency
- Generate scenario variations with Cosmos Predict: test edge cases
  that were not in the training distribution
- Validate on physical hardware: deploy to a test robot, run a limited
  set of real-world tasks, measure sim-to-real transfer accuracy
- Safety verification: verify the policy respects safety constraints
  (speed limits, force limits, keep-out zones)
- Export to ONNX/TensorRT for deployment-ready format

**Technologies**: Isaac Sim, Cosmos Predict, Cosmos Reason (for
automated evaluation), ONNX, TensorRT

## Phase 4: Model registration and promotion

**Goal**: Make the validated model available for production deployment
through a governed, auditable process.

**Activities**:

- Register the model in the Model Registry with full metadata: version,
  training run, dataset, evaluation results, embodiment, action space
- Sign the model artifact with Cosign; generate SBOM
- Open a promotion PR that updates the InferenceService manifest in
  Git to reference the new model version
- Review the PR: check metrics, safety results, lineage, SBOM
- Merge: Argo CD detects the change and begins rollout

**Technologies**: RHOAI Model Registry, MLflow, Sigstore/Cosign,
Git, Argo CD

## Phase 5: Deployment and serving

**Goal**: Deploy the model to production inference infrastructure and
begin serving.

**Activities**:

- Argo CD syncs the InferenceService update to the target cluster(s)
- KServe pulls the model from storage, starts the serving pod with
  the appropriate GPU
- For multi-site deployment: ApplicationSets fan out to spoke clusters
  via ACM integration
- For canary deployment: route a fraction of requests to the new model,
  monitor performance
- Verify: the new model serves correctly, latency is within budget,
  no regressions

**Technologies**: KServe, vLLM, Argo CD, ACM, OpenShift GPU Operator

## Phase 6: Fleet operation and monitoring

**Goal**: Operate the robot fleet with the deployed policy, monitor
performance, and detect issues.

**Activities**:

- Fleet Manager dispatches missions to robots
- Robots execute missions using the deployed VLA policy
- Telemetry flows from robots to the hub via Kafka federation
- Cosmos Reason monitors camera feeds for safety anomalies
- Digital twin reflects real-time fleet state
- Dashboards show fleet performance: mission completion rates, anomaly
  scores, inference latency

**Technologies**: Fleet Manager, Kafka (AMQ Streams), Cosmos Reason,
Isaac Sim (digital twin), Prometheus/Thanos, Console dashboard

## Phase 7: Continuous improvement

**Goal**: Use production data to improve the next generation of models.

**Activities**:

- Identify failure modes from production telemetry and monitoring
- Generate targeted training data for failure scenarios (Cosmos
  Predict + Transfer)
- Collect real-world data from production robots (with privacy and
  consent considerations)
- Retrain: mix new synthetic data with production data in the next
  training pipeline run
- Evaluate, register, promote, deploy — the cycle repeats

**Technologies**: All of the above, in a continuous loop

## The lifecycle as a loop

```
        ┌─────────────────────────────────────────────┐
        │                                             │
        ▼                                             │
  Twin Construction → Training → Evaluation → Registration
                                                    │
                                                    ▼
  Continuous Improvement ← Monitoring ← Operation ← Deployment
        │                                             │
        └─────────────────────────────────────────────┘
```

This loop runs continuously. Each iteration improves the model based
on production experience, broadens the training data, and addresses
newly discovered edge cases. The platform infrastructure (OpenShift,
GitOps, ACM) provides the operational foundation that makes this loop
sustainable — not a one-time heroic effort but a routine operational
practice.

## Key takeaway

Physical AI is not a single model deployment. It is a continuous loop
from simulation through training, validation, deployment, operation,
and back. The technology stack exists to make this loop repeatable,
auditable, and safe — turning physical AI from a research project into
an operational capability.
