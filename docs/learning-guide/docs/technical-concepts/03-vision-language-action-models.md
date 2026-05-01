# Vision-Language-Action Models

## The leap from seeing to doing

A Vision-Language Model understands what it sees and can describe it in
words. But it cannot pick up the object it just described. It cannot
navigate to the location it just identified. It produces text, not motor
commands.

A Vision-Language-Action Model (VLA) closes this gap. It takes the same
inputs — images from the robot's cameras and natural language
instructions — and produces **robot actions**: joint positions,
end-effector velocities, gripper commands. A single model that sees,
understands language, and controls a physical body.

This is the foundational architecture for the current generation of
physical AI systems. VLAs replace the traditional robotics pipeline —
where separate perception, planning, and control modules are hand-
engineered and chained together — with an end-to-end learned model.

## How VLAs work

### Architecture

A VLA extends the VLM architecture with an action output head:

```
Camera image(s) → Vision Encoder → Projection → Language Model → Action Head → Robot actions
                                                      ↑
                                              Language instruction
```

The key components:

**Vision encoder**: Same as in a VLM — a pretrained ViT (SigLIP,
DINOv2, CLIP) that converts camera images into patch embeddings.

**Language model backbone**: A pretrained LLM that serves as the
"brain" — processing visual features and language instructions to
reason about what action to take.

**Action head**: The new component. It maps the language model's
internal representations to robot actions. Approaches vary:

- **Action tokenization**: Discretize the continuous action space into
  tokens and train the language model to predict them as if they were
  text. The model outputs "action tokens" that are decoded into
  joint positions. This is the approach used by RT-2 and OpenVLA.

- **Diffusion action head**: Use a diffusion model as the action
  decoder, generating smooth, multi-step action trajectories. This
  produces higher-quality continuous actions than tokenization. Used
  by pi-0 and GR00T N1.

- **Flow matching**: A variant of diffusion that generates actions
  through a continuous normalizing flow. Used by newer GR00T N1
  versions.

### Action space

The action space defines what the robot can do. Common representations:

- **Joint positions**: Direct specification of each joint angle. The
  most common for manipulation arms.
- **End-effector pose**: 6-DOF position and orientation of the robot's
  hand/tool. The controller converts this to joint commands via inverse
  kinematics.
- **End-effector velocity**: Rate of change of position and orientation.
  Smoother than position commands for reactive control.
- **Relative actions**: Delta from the current position rather than
  absolute targets. More robust to calibration errors and generalizes
  better across embodiments.

### Observation space

What the VLA receives as input:

- **Camera images**: One or more RGB camera views (wrist camera,
  overhead camera, scene cameras)
- **Proprioceptive state**: Joint positions, velocities, gripper
  opening — the robot's sense of its own body
- **Language instruction**: Natural language description of the task
  ("pick up the red cup and place it on the tray")
- **Task context** (optional): Previous observations, goal images,
  or other conditioning information

## Key VLA models

### RT-2 (Google DeepMind, 2023)

The paper that established VLAs as a paradigm. RT-2 showed that a
vision-language model (PaLI-X, 55B parameters) could be fine-tuned
to output robot actions by representing actions as text tokens.

The key result: RT-2 exhibited **emergent capabilities** — the ability
to follow instructions involving concepts the robot had never been
trained on, by leveraging the VLM's web-scale pretraining. When asked
to "pick up the object that dinosaurs would be scared of" (a toy
meteor), RT-2 succeeded despite never being trained on that instruction
— it reasoned about the concept using knowledge from language
pretraining.

- Brohan, A., et al. (2023). "RT-2: Vision-Language-Action Models
  Transfer Web Knowledge to Robotic Control."
  [arXiv:2307.15818](https://arxiv.org/abs/2307.15818)

### OpenVLA (Stanford/Berkeley, 2024)

The first fully open-source VLA. Built on a Llama 2 language model
backbone with a SigLIP vision encoder, trained on the Open X-Embodiment
dataset (manipulation data from 22 different robot embodiments).

OpenVLA demonstrated that VLAs do not require proprietary, billion-
parameter models. A 7B parameter model, fully open-source, achieves
competitive performance on standard manipulation benchmarks. It is
designed to be fine-tuned on specific robot hardware and tasks.

- Kim, M.J., et al. (2024). "OpenVLA: An Open-Source Vision-Language-
  Action Model."
  [openvla.github.io](https://openvla.github.io/)

### pi-0 (Physical Intelligence, 2024)

A VLA from Physical Intelligence (a company founded by researchers from
Google DeepMind, Stanford, and UC Berkeley) that uses a flow-matching-
based action head instead of action tokenization. This produces smoother,
more precise actions — important for contact-rich manipulation tasks.

pi-0 demonstrated strong performance on a diverse set of real-world
manipulation tasks, including tasks requiring dexterity, bimanual
coordination, and long-horizon planning.

- [Physical Intelligence pi-0](https://www.physicalintelligence.company/blog/pi0)

### NVIDIA GR00T N1 (2025)

NVIDIA's foundation model for humanoid robots. GR00T uses a dual-system
architecture:

- **System 2** (slow, deliberate): A VLM (based on Cosmos Reason)
  processes camera observations and language instructions, performing
  scene understanding and high-level planning.
- **System 1** (fast, reactive): A Diffusion Transformer generates
  continuous robot actions — smooth joint trajectories that execute the
  plan with physically stable motion.

GR00T is embodiment-agnostic, using a relative end-effector action
space that generalizes across different humanoid robots. It is trained
on a combination of human video demonstrations, robot teleoperation
data, and simulation trajectories from Isaac Sim.

GR00T is covered in detail in
[Part 3: NVIDIA Ecosystem](../nvidia-ecosystem/04-groot.md).

### Octo (UC Berkeley, 2024)

A general-purpose robot policy trained on the Open X-Embodiment dataset.
Octo is designed as a foundation model that is fine-tuned for specific
robots and tasks rather than used directly. It demonstrates the
data-scaling approach: train on diverse multi-robot data, then
specialize.

- [Octo](https://octo-models.github.io/)

## Training VLAs

### Data sources

VLA training requires paired data: observations (images) matched with
actions (what the robot did in response). Data comes from:

**Teleoperation**: A human operator controls the robot through a
joystick, haptic device, or leader-follower mechanism (like the ALOHA
setup). The robot records camera images and the corresponding actions
the human commanded. This produces high-quality demonstration data but
is labor-intensive.

**Simulation**: Robots acting in simulated environments (Isaac Sim,
MuJoCo) generate observation-action pairs at scale. Domain
randomization ensures diversity. This is orders of magnitude cheaper
than teleoperation but requires sim-to-real transfer.

**Human video**: VLMs pretrained on web-scale video learn manipulation
priors from watching humans perform tasks. GR00T N1.5 introduced the
FLARE loss that explicitly enables learning from egocentric human
video and transferring those priors to robot control.

**Autonomous exploration**: The robot explores its environment using
RL or curiosity-driven objectives, generating its own experience. This
is the most scalable approach in principle but requires sophisticated
reward shaping.

### The Open X-Embodiment dataset

The largest open dataset for robot learning, assembled by a
collaboration of 32 research labs. It contains over 1 million robot
trajectories from 22 different robot embodiments performing diverse
manipulation tasks. Open X-Embodiment enables training cross-embodiment
policies — models that generalize across different robot bodies.

- [Open X-Embodiment](https://robotics-transformer-x.github.io/)

### Fine-tuning

VLAs are typically pretrained on large diverse datasets and then
fine-tuned on specific hardware and tasks. Fine-tuning adapts the
model to the specific robot's kinematics, sensor characteristics, and
target task. Techniques like LoRA (Low-Rank Adaptation) reduce the
compute cost of fine-tuning by updating only a small fraction of the
model's parameters.

## VLAs vs. traditional robotics pipelines

### Traditional pipeline

```
Camera → Object detection → Pose estimation → Grasp planning → Motion planning → Motor control
```

Each module is hand-engineered, with carefully designed interfaces
between stages. A failure at any stage propagates downstream. Adding a
new capability (handling a new object type) requires modifying multiple
modules.

### VLA pipeline

```
Camera + instruction → VLA model → Robot actions
```

End-to-end: the model learns the entire mapping from perception to
action. New capabilities emerge from training data rather than
engineering effort. The model can generalize to novel situations by
leveraging its pretrained knowledge.

### Trade-offs

| Aspect | Traditional pipeline | VLA |
|--------|---------------------|-----|
| **Interpretability** | Each module has clear inputs/outputs | Black-box end-to-end |
| **Precision** | Can achieve sub-millimeter accuracy | Currently ~centimeter precision |
| **Data requirements** | Minimal for hand-tuned parameters | Thousands to millions of demonstrations |
| **Generalization** | Poor — each new scenario needs engineering | Good — leverages pretrained world knowledge |
| **Development speed** | Slow — expert engineering per task | Fast once the base model exists |
| **Safety verification** | Each module can be tested independently | Harder to verify — behavior emerges from weights |

For now, the practical approach is hybrid: VLAs handle perception and
high-level planning where generalization matters, while traditional
control handles low-level motor execution where precision and
verifiability matter. GR00T's dual-system architecture (VLM for
understanding + diffusion head for motor control, paired with SONIC
for whole-body stability) exemplifies this hybrid approach.

## Key takeaways

- VLAs extend VLMs to output robot actions, enabling end-to-end
  learned control from camera images and language instructions.
- Action generation approaches include tokenization (treating actions
  as text), diffusion (generating smooth trajectories), and flow
  matching.
- Training data comes from teleoperation, simulation, and human video,
  with the Open X-Embodiment dataset providing the largest open source.
- VLAs trade the interpretability and precision of traditional
  pipelines for generalization and development speed.
- The practical state of the art is hybrid: VLAs for perception and
  planning, traditional control for motor execution and safety.

## Further reading

- Brohan, A., et al. (2022). "RT-1: Robotics Transformer for
  Real-World Control at Scale."
  [arXiv:2212.06817](https://arxiv.org/abs/2212.06817) — The
  predecessor to RT-2, demonstrating transformer-based robot control.
- Kim, M.J., et al. (2024). "OpenVLA: An Open-Source Vision-Language-
  Action Model." [openvla.github.io](https://openvla.github.io/)
- O'Neill, A., et al. (2024). "Open X-Embodiment: Robotic Learning
  Datasets and RT-X Models."
  [robotics-transformer-x.github.io](https://robotics-transformer-x.github.io/)
- Zhao, T.Z., et al. (2023). "Learning Fine-Grained Bimanual
  Manipulation with Low-Cost Hardware." (ACT/ALOHA)
  [arXiv:2304.13705](https://arxiv.org/abs/2304.13705)
