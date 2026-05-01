# Isaac Sim & Isaac Lab

## Isaac Sim

Isaac Sim is NVIDIA's robotics simulation application built on the
Omniverse platform. It provides the environment where robots train,
test, and validate before deployment to physical hardware.

### What it provides

**Physics simulation via PhysX 5**: GPU-accelerated rigid body, soft
body, and articulated body dynamics. PhysX computes what happens when
objects interact — collisions, stacking, joint constraints, motor
forces. GPU parallelism enables running thousands of environments
simultaneously for reinforcement learning.

**Ray-traced sensor simulation**: Using RTX hardware, Isaac Sim renders
camera output that closely matches what real cameras see — accurate
shadows, reflections, material appearance, and depth. Beyond cameras,
it simulates LiDAR (with accurate beam patterns and noise), depth
sensors, IMUs, contact sensors, and ultrasonic sensors.

This is not game-engine approximation. Isaac Sim's sensors produce
physically-based output designed to minimize the sim-to-real gap for
perception models.

**ROS 2 integration**: Isaac Sim includes ROS 2 libraries and a bridge
that publishes and subscribes to ROS topics. Robot software developed
against ROS 2 can run against Isaac Sim as a drop-in replacement for
the real robot — same message types, same TF frames, same interfaces.

**OpenUSD scene description**: Scenes are described in USD, enabling
the layered composition, collaboration, and asset management described
in the [OpenUSD chapter](../technical-concepts/01-openusd.md). Robot
models, environment assets, sensor configurations, and physics
properties all live in the USD scene.

**Headless and containerized operation**: Isaac Sim runs headless on
servers and in containers (`nvcr.io/nvidia/isaac-sim`), with optional
WebRTC streaming for remote visualization. This is the deployment
model for cloud/Kubernetes-based simulation at scale.

### Isaac Sim for physical AI

In the physical AI workflow, Isaac Sim serves as:

- **Training environment**: Where robot policies learn through RL or
  imitation learning.
- **Synthetic data generator**: Where labeled training images are
  rendered with domain randomization.
- **Validation testbed**: Where policies are evaluated against diverse
  scenarios before hardware deployment.
- **Digital twin runtime**: Where the real-time state of a physical
  facility is mirrored and monitored.

- [Isaac Sim Documentation](https://docs.isaacsim.omniverse.nvidia.com/)
- [Isaac Sim on GitHub](https://github.com/isaac-sim/IsaacSim)

## Omniverse Replicator

Replicator is the synthetic data generation (SDG) framework within
Isaac Sim. It automates the creation of labeled training datasets from
simulation.

### Annotators

Annotators extract ground-truth labels from the rendered scene:

| Annotator | Output | Use case |
|-----------|--------|----------|
| `rgb` | RGBA image | Visual perception training |
| `depth` / `distance_to_camera` | Per-pixel depth | 3D perception, obstacle detection |
| `semantic_segmentation` | Per-pixel class labels | Scene understanding |
| `instance_segmentation` | Per-pixel object IDs | Object counting, tracking |
| `normals` | Per-pixel surface normals | Surface analysis |
| `motion_vectors` | Per-pixel optical flow | Motion estimation |
| `bounding_box_2d` / `bounding_box_3d` | Object bounding boxes | Object detection |

All annotators run simultaneously on the same render product — you
capture all label types in a single pass.

### Domain randomization

Replicator's Randomizer API introduces variability into scenes:

- Object pose, scale, and texture randomization
- Lighting variation (intensity, color, position)
- Camera angle and position randomization
- Background and distractor object randomization
- Material property randomization

Randomization happens in-place without reloading assets, making it
computationally efficient for generating thousands of variations.

### Writers

Writers export annotated data to standard formats (COCO, KITTI) for
consumption by training pipelines. Custom writers can output to any
format needed.

- [Replicator Tutorials](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/index.html)

## Isaac Lab

Isaac Lab is the open-source, GPU-accelerated framework for robot
learning built on Isaac Sim. It provides the tooling for reinforcement
learning and imitation learning at scale.

### Relationship to Isaac Gym

Isaac Gym was NVIDIA's earlier RL framework — a standalone preview
that proved the concept of GPU-parallel RL training (thousands of
environments on one GPU). Isaac Gym is no longer supported.

Isaac Lab replaces it with a modular, composable architecture built
on the full Isaac Sim platform. This means Isaac Lab inherits all of
Isaac Sim's capabilities: Omniverse rendering, USD scene description,
comprehensive sensor simulation, and extensibility.

### Key capabilities

**Massively parallel GPU simulation**: Run 4,096+ simultaneous
environments on a single GPU. Each environment is a complete robot +
scene instance. This eliminates the CPU bottleneck that limits
traditional simulation — the physics, rendering, and RL training all
run on the GPU without data transfers to CPU.

**Environment design**: Isaac Lab provides a modular system for
building training environments: define the robot, the scene, the
task (observations, actions, rewards), and the domain randomization
strategy. Environments are composable — swap the robot, change the
scene, or modify the task without rewriting everything.

**Integrated training**: Isaac Lab works with standard RL libraries
(rl_games, Stable-Baselines3, RSL-rl) and supports both RL and
imitation learning workflows.

**Export**: Trained policies export to ONNX and TensorRT for
deployment on edge hardware (Jetson) or model serving infrastructure
(KServe).

### Training at scale

To illustrate the scale: training a locomotion policy for a quadruped
robot typically requires 10–100 million environment steps. With Isaac
Lab running 4,096 parallel environments at 60 Hz simulated time, this
is:

- 10M steps ÷ 4,096 environments ÷ 60 Hz ≈ 40 seconds of wall-clock
  time for the simulation
- Plus RL algorithm compute ≈ minutes to an hour total

Compare to a physical robot collecting data in real time: 10M steps at
real-world rates would take months. GPU simulation compresses this by
3–4 orders of magnitude.

- [Isaac Lab](https://developer.nvidia.com/isaac/lab)
- [Isaac Lab on GitHub](https://github.com/isaac-sim/IsaacLab)

## Key takeaways

- Isaac Sim provides physics simulation, ray-traced sensor output,
  ROS 2 integration, and USD scene management for robotics — all in
  a containerizable, headless-capable application.
- Replicator generates labeled synthetic training data with domain
  randomization — depth, segmentation, bounding boxes, and more, all
  extracted automatically from the render pipeline.
- Isaac Lab enables GPU-parallel RL and imitation learning at scale —
  thousands of simultaneous environments, compressing months of
  real-world training into hours.

## Further reading

- [NVIDIA Isaac Platform](https://developer.nvidia.com/isaac) —
  Overview of the full Isaac ecosystem.
- [Isaac Sim Container Installation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html) —
  Running Isaac Sim in containers for server/cloud deployment.
- [Isaac Lab Quick Start](https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html) —
  Getting started with Isaac Lab for RL training.
