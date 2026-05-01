# GR00T & Embodied AI Models

## What GR00T is

GR00T (Generalist Robot 00 Technology) is NVIDIA's foundation model
for humanoid robots. It is a Vision-Language-Action (VLA) model —
taking camera images and language instructions as input and producing
continuous robot actions as output.

GR00T is significant not because it is the only VLA (OpenVLA, pi-0,
RT-2 are alternatives) but because it is designed as part of an
integrated pipeline: train in Isaac Sim with Isaac Lab, serve on
Jetson hardware, and deploy through the same infrastructure stack
that manages all other NVIDIA AI workloads.

## Dual-system architecture

GR00T N1 uses a dual-system architecture inspired by cognitive science
(Daniel Kahneman's *Thinking, Fast and Slow*):

### System 2: Slow, deliberate reasoning

A Vision-Language Model (VLM) — specifically a variant of Cosmos
Reason — that interprets the environment through vision and language.
System 2 processes camera observations and language instructions to
understand the scene, interpret the task, and form a high-level plan.

System 2 operates at relatively low frequency (1–10 Hz) and handles
the "thinking" part of robot behavior: understanding what it sees,
reasoning about what to do, and producing a latent representation
that captures the intended action.

### System 1: Fast, reactive action

A Diffusion Transformer (DiT) that generates continuous robot actions
— joint positions, end-effector trajectories — from the System 2
representation. System 1 mirrors reflexive, intuitive behavior:
translating the plan into smooth, physically executable motion.

The DiT generates action chunks — sequences of several timesteps of
motor commands — rather than single-step actions. This produces
temporally coherent motion that looks natural rather than jerky.

### How they connect

```
Camera images    ┐
                 ├─→ VLM (System 2) ─→ Latent plan ─→ DiT (System 1) ─→ Joint actions
Language command ┘
```

The VLM runs periodically (re-evaluating the scene and instruction),
while the DiT runs at higher frequency (continuously generating smooth
motor commands from the latest plan). This separation allows the robot
to react quickly to environmental changes while maintaining a coherent
understanding of its task.

## Training approach

GR00T is trained on diverse data:

**Human video**: Egocentric videos of humans performing manipulation
tasks (from the EgoScale dataset — 20,000+ hours). GR00T N1.5
introduced the FLARE (Future Latent Representation Alignment) loss
that enables learning manipulation priors from human video and
transferring them to robot control. This is powerful because human
video is vastly more abundant than robot demonstration data.

**Robot teleoperation**: Humans operating physical robots through
leader-follower mechanisms or VR teleoperation, generating paired
observation-action data.

**Simulation**: Isaac Sim and Isaac Lab provide unlimited training
scenarios with automatic labeling. GR00T-Mimic generates synthetic
motion data for specific robot embodiments.

**Cross-embodiment**: GR00T uses a relative end-effector action space
shared across human and robot embodiments. This means manipulation
skills learned from human video transfer to robots without
architecture changes.

## Embodiment-agnostic design

GR00T is designed to work across different humanoid robot platforms —
Unitree G1, Unitree H1, Agility Digit, Figure, 1X NEO, and others.
The model learns manipulation and locomotion skills in a body-agnostic
representation, then adapts to specific robots through fine-tuning.

This is analogous to how a language model handles many languages
through a shared tokenizer: GR00T handles many robot bodies through a
shared action representation.

## SONIC: Whole-body control

GR00T provides the high-level "brain" — deciding what to do. SONIC
(Synthesized Open Natural Interactive Control) provides the low-level
"body" — deciding how to move.

SONIC is a humanoid behavior foundation model trained on large-scale
human motion capture data. It produces whole-body motor commands that
are dynamically stable, human-like, and cover locomotion, manipulation,
and multi-contact behaviors.

The separation: GR00T's VLA determines *"reach for that box with the
right hand while walking to the shelf"*. SONIC determines *"here are
the exact joint trajectories for all 40+ joints that accomplish that
motion without falling over."*

- [SONIC GitHub](https://github.com/NVlabs/GR00T-WholeBodyControl)

## The N1 model series

GR00T N1 has evolved rapidly:

| Version | VLM Backbone | DiT Size | Key Advancement |
|---------|-------------|----------|----------------|
| **N1** (Mar 2025) | Eagle VLM | 16 layers | Initial dual-system architecture |
| **N1.5** | Eagle 2.5 VLM | 16 layers | FLARE loss for learning from human video |
| **N1.6** | Cosmos-Reason-2B | 32 layers | 2x larger DiT, bimanual manipulation |
| **N1.7** | Cosmos-Reason2-2B (Qwen3-VL) | 32 layers | Relative end-effector actions, 20K hrs human video |

Each version has improved transfer performance (from simulation to
real hardware) and task diversity (from single-arm grasping to
bimanual coordination and mobile manipulation).

- [GR00T Developer Page](https://developer.nvidia.com/isaac/gr00t)
- [GR00T N1 Paper](https://research.nvidia.com/publication/2025-03_nvidia-isaac-gr00t-n1-open-foundation-model-humanoid-robots)
- [GR00T on GitHub](https://github.com/NVIDIA/Isaac-GR00T)

## Training and deploying GR00T

### Fine-tuning

GR00T N1 is designed to be fine-tuned for specific robots and tasks:

1. **Collect demonstrations**: Teleoperate the target robot performing
   the target tasks. Typically 50–200 demonstrations per task.
2. **Fine-tune**: Use LoRA or full fine-tuning to adapt the pretrained
   GR00T model to the specific robot's kinematics and task domain.
3. **Evaluate**: Test in Isaac Sim with the robot's URDF/USD model,
   then on real hardware.
4. **Export**: Convert to ONNX and optimize with TensorRT for
   deployment on Jetson hardware.

### Deployment

GR00T policies deploy to NVIDIA Jetson hardware (Orin, Thor) for
on-robot inference. The System 2 VLM runs at 1–5 Hz (re-evaluating
the scene), while the System 1 DiT runs at 15–30 Hz (generating motor
commands). Total inference latency is within the robot's control loop
budget.

For serving from a cluster rather than on-robot, GR00T policies can
be served via KServe with a custom predictor container, accessed by
the robot over a local network.

## GR00T in the broader VLA landscape

| Model | Organization | Embodiment focus | Action head | Open weights |
|-------|-------------|-----------------|-------------|-------------|
| **GR00T N1** | NVIDIA | Humanoids | Diffusion Transformer | Yes |
| **OpenVLA** | Stanford/Berkeley | General manipulation | Action tokenization | Yes |
| **pi-0** | Physical Intelligence | General manipulation | Flow matching | No |
| **RT-2** | Google DeepMind | Single-arm manipulation | Action tokenization | No |
| **Octo** | UC Berkeley | Multi-embodiment | Diffusion | Yes |

GR00T differentiates through its dual-system architecture, embodiment-
agnostic design, NVIDIA ecosystem integration (Isaac Sim training,
Jetson deployment), and the scale of pretraining on human video data.

## Key takeaways

- GR00T is a VLA foundation model for humanoid robots with a
  dual-system architecture: VLM for reasoning, DiT for motor control.
- It is embodiment-agnostic — the same pretrained model fine-tunes for
  different robot platforms.
- Training uses human video, robot teleoperation, and simulation data,
  with the FLARE loss enabling transfer from human demonstrations.
- SONIC provides the whole-body controller layer beneath GR00T's
  high-level decisions.
- Deployment targets Jetson edge hardware for on-robot inference.

## Further reading

- [GR00T N1 Blog](https://developer.nvidia.com/blog/accelerate-generalist-humanoid-robot-development-with-nvidia-isaac-gr00t-n1/) —
  Technical overview of the N1 architecture and capabilities.
- [GR00T N1.6 Blog](https://developer.nvidia.com/blog/building-generalist-humanoid-capabilities-with-nvidia-isaac-gr00t-n1-6-using-a-sim-to-real-workflow/) —
  Sim-to-real workflow for humanoid capabilities.
- [Open X-Embodiment](https://robotics-transformer-x.github.io/) —
  The open dataset powering cross-embodiment robot learning.
