# World Models & Foundation Models for Robotics

## What a world model is

A world model is an AI system that learns to predict how the physical
world behaves — what will happen next given the current state and a
proposed action. Where a VLM understands a single frame ("there is a
forklift next to the racking"), a world model understands dynamics
("if the forklift turns left and accelerates, it will reach the
loading dock in 12 seconds and must slow before the corner").

World models are significant for physical AI because they enable
**prediction without physical execution**. A robot can "imagine" the
consequences of an action before committing to it. A fleet manager can
simulate the outcome of a schedule change before deploying it. A safety
system can predict whether a trajectory will lead to a collision before
the collision happens.

The term "world foundation model" — used by NVIDIA for the Cosmos
family — extends this to models trained at sufficient scale to
generalize across physical domains, analogous to how large language
models generalize across language tasks.

## Types of world models

### Physics-based models

Classical simulations: rigid-body dynamics, fluid dynamics,
thermodynamics, finite element analysis. These are the "world models"
that engineering has used for decades. They are accurate within their
assumptions (Newtonian mechanics, known material properties) but
require explicit specification of every relevant physical parameter.

Physics-based models are deterministic and interpretable. They are also
computationally expensive, brittle to unmodeled phenomena, and require
expert setup.

### Learned dynamics models

Neural networks trained to predict future states from current states
and actions. Given a sequence of observations (camera frames, sensor
readings) and a proposed action, the model predicts the next
observation. This is the approach used by modern world foundation
models.

**Advantages**: Learn directly from data without explicit physics
specification. Can capture phenomena that are hard to model
analytically (deformable objects, complex contact, fluid-solid
interaction). Scale with data and compute.

**Disadvantages**: Require large training datasets. Can hallucinate
physically impossible outcomes. Difficult to guarantee accuracy or
bound prediction errors. Not interpretable in the way physics
simulations are.

### Hybrid models

Combine physics simulation with learned components. The physics engine
handles well-understood phenomena (rigid-body dynamics, gravity);
learned components handle hard-to-model phenomena (friction, contact
deformation, sensor noise). This is increasingly the practical
approach — the simulation provides the structure, and learning fills
the gaps.

## Video prediction as world modeling

A powerful framing: if a model can predict the next frames of a video
given an action, it has implicitly learned a model of the world. The
video captures everything visible about the physical state — object
positions, lighting, shadows, reflections — and predicting its future
requires understanding of physics, object permanence, and dynamics.

This is the approach taken by NVIDIA's **Cosmos Predict** model. Given
a current video and a description of what should happen (text prompt or
action conditioning), it generates future video frames. The quality of
the predicted video reflects the model's understanding of physical
dynamics.

### Action-conditioned prediction

For robotics, the most useful form of video prediction is
**action-conditioned**: given the current camera view and a proposed
robot action (e.g., "move gripper 5cm left, close gripper"), predict
what the camera will see after the action executes. This enables:

- **Planning by imagination**: The robot generates candidate action
  sequences, predicts their outcomes via the world model, and selects
  the sequence with the best predicted outcome.
- **Pre-dispatch validation**: Before sending a mission to a physical
  robot, simulate it through the world model to check for safety
  violations.
- **Counterfactual reasoning**: "What would have happened if the robot
  had taken a different action?" — useful for learning from failures.

## Foundation models for robotics

The "foundation model" concept — large-scale pretraining on diverse
data, followed by task-specific fine-tuning — has transformed language
(GPT, Llama) and vision (CLIP, DINOv2). It is now being applied to
robotics:

### Robot foundation models

Models pretrained on diverse robot experience across many embodiments,
tasks, and environments. Rather than training a policy from scratch
for each robot and task, you fine-tune a foundation model that already
understands general principles of manipulation, navigation, and
physical interaction.

Key examples:

- **GR00T N1** (NVIDIA): Foundation model for humanoid robots, trained
  on human video and robot teleoperation data.
- **Octo** (UC Berkeley): General-purpose robot policy trained on the
  Open X-Embodiment dataset across 22 embodiments.
- **RT-X** (Google DeepMind + consortium): Policies trained on the
  same Open X-Embodiment data, demonstrating positive transfer across
  robot types.

### World foundation models

Models pretrained to understand the dynamics of the physical world,
usable across domains (robotics, autonomous vehicles, industrial
simulation). NVIDIA positions Cosmos as this type of model:

- **Cosmos Predict**: Generates video predictions of future world
  states.
- **Cosmos Transfer**: Adapts visual domains (making synthetic data
  photorealistic).
- **Cosmos Reason**: Understands and reasons about physical scenes.

These models are covered in detail in
[Part 3: NVIDIA Ecosystem](../nvidia-ecosystem/03-cosmos.md).

## World models in the physical AI lifecycle

World models serve different roles at different stages:

### During training

The world model acts as the simulation engine — providing the
environments in which robot policies train. When combined with domain
randomization and domain adaptation, world models generate the diverse
experience that policies need to generalize.

### During validation

Before deploying a new policy, the world model predicts how it will
behave in target scenarios. If the predicted behavior violates safety
constraints or fails to achieve task objectives, the policy is rejected
without risking physical hardware.

### During deployment

The world model enables runtime prediction and planning. A deployed
robot can use its world model to plan actions several steps ahead,
selecting trajectories that avoid predicted obstacles and achieve
predicted goals. A fleet manager can use a world model to simulate
the effect of schedule changes or policy updates before applying them.

## Key takeaways

- World models predict how the physical world behaves — enabling
  planning, validation, and counterfactual reasoning without physical
  execution.
- Modern world models learn dynamics from video and sensor data,
  complementing (not replacing) physics-based simulation.
- Foundation models for robotics apply the pretrain-then-fine-tune
  paradigm to physical interaction, enabling generalization across
  embodiments and tasks.
- NVIDIA's Cosmos family represents the world foundation model
  approach — Predict, Transfer, and Reason composing into a physical
  understanding pipeline.

## Further reading

- Ha, D. & Schmidhuber, J. (2018). "World Models."
  [arxiv.org/abs/1803.10122](https://arxiv.org/abs/1803.10122) —
  The influential paper framing world models as learned environment
  simulators for RL.
- LeCun, Y. (2022). "A Path Towards Autonomous Machine Intelligence."
  [openreview.net/pdf?id=BZ5a1r-kVsf](https://openreview.net/pdf?id=BZ5a1r-kVsf) —
  Yann LeCun's position paper on world models as the path to
  human-level AI, proposing the JEPA architecture.
- NVIDIA Cosmos Documentation —
  [docs.nvidia.com/cosmos/latest/introduction.html](https://docs.nvidia.com/cosmos/latest/introduction.html)
