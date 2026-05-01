# Cosmos — World Foundation Models

## The world foundation model concept

Large language models learn patterns of language from text. Vision
models learn patterns of appearance from images. World foundation
models learn patterns of the **physical world** from video — how
objects move, how light behaves, how physics governs interactions.

NVIDIA Cosmos is a family of world foundation models purpose-built for
physical AI. The models understand and generate representations of the
physical world at a level that enables synthetic data generation, scene
understanding, and predictive simulation for robotics and industrial
automation.

## The three Cosmos models

### Cosmos Predict

**What it does**: Generates future video frames — predicting what the
world will look like given the current state and, optionally, a
proposed action.

**Input modes**:

- **Text-to-world**: Generate a video from a text description.
  *"A forklift navigates a warehouse aisle, fluorescent lighting,
  concrete floor."*
- **Image-to-world**: Generate a video starting from a given image.
- **Video-to-world**: Extend an existing video into the future,
  optionally conditioned on actions.

**Action conditioning**: The most important mode for robotics. Given
the robot's current camera view and a planned action (gripper
displacement, navigation command), Predict generates what the camera
would see after the action executes. This enables planning by
imagination — evaluating actions before committing to them physically.

**Model sizes**: Cosmos Predict 2.5 is available in 2B and 14B
parameter versions. Sequences up to 30 seconds. 720p resolution.

**Physical AI use case**: Pre-dispatch validation. Before sending a
mission to a physical robot, simulate it through Predict to check for
safety violations, trajectory feasibility, or unexpected outcomes.

- [Cosmos Predict Research](https://research.nvidia.com/labs/cosmos-lab/cosmos-predict2.5/)

### Cosmos Transfer

**What it does**: Transforms synthetic or simulated video into
photorealistic video while preserving the spatial structure and motion
of the input. This is video-to-video domain adaptation.

**Control signals**: Transfer accepts structured control inputs that
guide the generation while preserving spatial layout:

| Control mode | Input | Structural preservation |
|-------------|-------|------------------------|
| **Depth** | Depth map video | Strong — preserves 3D layout |
| **Edge** | Edge detection map | Strong — preserves outlines and structure |
| **Segmentation** | Semantic segmentation | Strong — preserves object boundaries and classes |
| **Blur (vis)** | Blurred RGB | Weak — preserves rough layout but allows more freedom |

Control signals can be provided explicitly (extracted from the
simulation using Replicator annotators) or computed on-the-fly from
the input video.

**Physical AI use case**: Sim-to-real bridge. Isaac Sim renders a
warehouse scene. The rendering looks synthetic. Transfer takes the
synthetic rendering plus depth maps and produces a photorealistic
version — same geometry, same motion, but visually indistinguishable
from real camera footage. These photorealistic frames become training
data.

**Critical constraint**: Cosmos Transfer 2.5-2B requires approximately
65 GB of VRAM at 720p resolution. This exceeds the capacity of L40S
(48 GB) GPUs but fits on systems with larger unified memory pools or
H100/H200 GPUs.

- [Cosmos Transfer Research](https://research.nvidia.com/labs/cosmos-lab/cosmos-transfer2.5/)

### Cosmos Reason

**What it does**: A vision-language model with spatiotemporal awareness
and chain-of-thought reasoning, built for understanding the physical
world. It analyzes images and video, reasoning about what it sees step
by step.

**Capabilities**:

- Interpret scenes with physical understanding (object interactions,
  cause-and-effect)
- Chain-of-thought reasoning about spatial relationships and dynamics
- 2D/3D point localization and bounding box detection with explanations
- Predict outcomes of physical interactions

**Architecture**: 8B parameters, based on the Qwen2.5-VL architecture.
Served via vLLM with an OpenAI-compatible API.

**Physical AI use cases**:

- **Safety monitoring**: Analyze camera feeds for hazards, obstructions,
  or safety violations using natural-language reasoning.
- **Data curation**: Automatically evaluate and annotate synthetic
  training datasets for quality and relevance.
- **Scene understanding**: Provide contextual understanding for robot
  planning ("Is there space to place the pallet next to the
  racking?").

- [Cosmos Reason Documentation](https://docs.nvidia.com/cosmos/latest/reason2/index.html)

## How the three models compose

The Cosmos models form a pipeline that spans the physical AI lifecycle:

```
1. Predict generates novel scenarios
   "What does a warehouse look like during a night shift?"

2. Transfer makes them photorealistic
   Synthetic rendering + depth map → photorealistic video

3. Reason analyzes and understands
   "Is the forklift maintaining safe distance from the worker?"
```

In practice:

- **Predict** creates diverse training scenarios from text descriptions
  or extends existing sim recordings with novel variations (different
  weather, lighting, activity levels).
- **Transfer** bridges the sim-to-real visual gap, producing training
  data that is both spatially accurate (from simulation) and visually
  realistic (from the diffusion model).
- **Reason** provides runtime perception — analyzing real camera feeds
  with physical understanding, serving as the "eyes" of the safety and
  monitoring system.

## Deployment patterns

### Cosmos Reason on KServe/vLLM

Cosmos Reason is a transformer-based VLM that serves via vLLM with
an OpenAI-compatible API. It deploys as a standard KServe
InferenceService on a GPU with sufficient VRAM (16+ GB for the 8B
model).

### Cosmos Predict and Transfer as batch workloads

Predict and Transfer are diffusion models — not LLMs. They cannot be
served via vLLM. They run as batch jobs: load the model, process the
input, generate output, exit. Processing times are measured in minutes
to hours per video clip, not milliseconds per request.

Deployment options:

- **Docker batch container**: Run on a GPU host with sufficient VRAM.
  For Transfer at 720p, this means 65+ GB of GPU memory.
- **Kubernetes Job**: A pod that runs the inference script, writes
  output to storage, and exits. Scheduled by Kueue or standard
  Kubernetes job scheduling.
- **NIM container**: NVIDIA's optimized inference container with
  TensorRT acceleration. Validated on Hopper 80GB+ GPUs.
- **Open weights**: The models are available from HuggingFace under the
  NVIDIA Open Model License. Open weights run on broader GPU hardware
  (including Blackwell and Ampere architectures) but without TensorRT
  optimization.

## Key takeaways

- Cosmos is a family of world foundation models: Predict (video
  generation/prediction), Transfer (sim-to-real domain adaptation),
  and Reason (visual understanding with physical reasoning).
- They compose into a pipeline: generate scenarios → make them
  photorealistic → understand and analyze them.
- Reason is an LLM-style model served via vLLM. Predict and Transfer
  are diffusion models that run as batch workloads.
- Transfer's VRAM requirement (65 GB at 720p) makes GPU selection a
  critical deployment decision.

## Further reading

- [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/) —
  Product overview.
- [Cosmos Documentation](https://docs.nvidia.com/cosmos/latest/introduction.html) —
  Technical documentation for all Cosmos models.
- [Cosmos Transfer 2.5 on HuggingFace](https://huggingface.co/nvidia/Cosmos-Transfer2.5-2B) —
  Open weights and model card.
- [Cosmos Predict Post-Training Guide](https://docs.nvidia.com/cosmos/latest/predict2.5/post-training/) —
  Fine-tuning Predict for domain-specific tasks.
