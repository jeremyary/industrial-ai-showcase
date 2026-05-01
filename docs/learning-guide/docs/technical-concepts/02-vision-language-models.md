# Vision-Language Models

## What VLMs are

A Vision-Language Model (VLM) is a neural network that processes both
images and text, understanding the relationship between what it sees
and what it reads. Unlike a pure image classifier (which assigns a
label to an image) or a pure language model (which generates text), a
VLM can:

- **Answer questions about images**: "What objects are in this scene?"
  "Is there an obstruction in the aisle?"
- **Describe images in natural language**: Generate captions that
  capture the content and context of a visual scene.
- **Ground language in visual content**: Given a text query like "the
  red forklift near the loading dock," locate the corresponding region
  in the image.
- **Reason about spatial relationships**: "Is the pallet closer to
  the wall or the conveyor?"

VLMs are the perception backbone of physical AI. They enable robots
and systems to understand their environment through the combination of
visual input and natural language — rather than through narrow,
task-specific classifiers trained on limited label sets.

## How VLMs work

### Architecture

Most modern VLMs share a common architecture with three components:

**1. Vision encoder**: Processes the input image into a set of visual
features. Typically a Vision Transformer (ViT) pretrained on large
image datasets. Common choices include:

- **SigLIP** — a contrastive vision-language model from Google that
  learns to align images and text in a shared embedding space
- **DINOv2** — a self-supervised vision model from Meta that learns
  strong visual features without text supervision
- **CLIP** — OpenAI's Contrastive Language-Image Pre-training model,
  one of the earliest successful vision-language models

The vision encoder converts a raw image (e.g., 224×224 or 384×384
pixels) into a sequence of patch embeddings — each patch represents
a region of the image as a high-dimensional vector.

**2. Language model**: A large language model (LLM) that processes
text and generates responses. This is typically a pretrained
transformer: Llama, Qwen, Mistral, or a similar architecture.

**3. Projection layer**: A module that maps the vision encoder's
output into the language model's embedding space, allowing the LLM
to "see" the image as if it were part of the text sequence. This can
be a simple linear projection, an MLP, or a more complex cross-attention
mechanism.

### Training

VLMs are trained in stages:

1. **Vision encoder pretraining**: The vision encoder is pretrained
   (often with contrastive learning on image-text pairs) to produce
   meaningful visual features.

2. **Alignment training**: The projection layer is trained to align
   visual features with the language model's representation space,
   typically using image-caption pairs.

3. **Instruction tuning**: The full model is fine-tuned on
   instruction-following datasets — visual question answering, image
   description, visual reasoning — to produce a model that responds
   helpfully to user queries about images.

## VLMs in physical AI

VLMs serve several roles in physical AI systems:

### Safety and anomaly detection

A VLM monitoring camera feeds can reason about scenes in natural
language. Instead of training a narrow classifier for each possible
hazard, you prompt the VLM:

- "Is there anything blocking the emergency exit?"
- "Are any workers in the forklift's path?"
- "Is the pallet stack leaning dangerously?"

The VLM reasons about the scene using its general understanding of
physical objects, spatial relationships, and safety concepts — knowledge
it acquired during pretraining on web-scale data.

### Scene understanding for planning

Before a robot acts, it needs to understand its environment. A VLM can
process the robot's camera feed and answer questions that inform
planning:

- "What objects are on the table?"
- "Is there space to place the box next to the container?"
- "Which bin contains red components?"

This contextual understanding feeds into the robot's task planner,
which decides what to do next.

### Data curation and labeling

VLMs can automatically annotate and curate training datasets —
classifying scenes, describing content, identifying edge cases, and
filtering low-quality data. This is particularly valuable for the
synthetic data pipeline, where millions of generated images need
quality assessment.

## Key VLM models

### CLIP (OpenAI, 2021)

Contrastive Language-Image Pre-training. Trained on 400 million
image-text pairs from the internet. CLIP learns a shared embedding
space where images and text that describe the same concept are close
together. It demonstrated zero-shot image classification — classifying
images into categories it was never explicitly trained on by comparing
image embeddings to text embeddings of category names.

CLIP's significance was showing that natural language supervision (image
captions from the web) could produce visual representations that rival
task-specific supervised models.

- Radford, A., et al. (2021). "Learning Transferable Visual Models
  From Natural Language Supervision."
  [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)

### LLaVA (Large Language and Vision Assistant, 2023)

One of the first open-source VLMs to demonstrate strong multimodal
instruction following. LLaVA connects a CLIP vision encoder to a Llama
language model through a simple projection layer. Despite its
architectural simplicity, LLaVA showed that a pretrained vision encoder
plus a pretrained LLM plus alignment training on instruction data
produces a capable multimodal assistant.

- Liu, H., et al. (2023). "Visual Instruction Tuning."
  [arXiv:2304.08485](https://arxiv.org/abs/2304.08485)

### Qwen-VL (Alibaba, 2024+)

A family of vision-language models based on the Qwen language model.
Qwen2-VL and Qwen2.5-VL added native video understanding (processing
video frames, not just single images) and improved spatial reasoning.
NVIDIA's Cosmos Reason model is built on the Qwen2.5-VL architecture,
demonstrating its suitability for physical-world understanding.

### PaLI / PaLM-E (Google, 2023)

PaLM-E (Pathways Language Model - Embodied) was one of the first models
to demonstrate that a VLM could be used for embodied reasoning — taking
robot camera observations and generating plans for physical tasks. It
showed that scaling VLMs gives emergent capabilities for spatial
reasoning and physical understanding that smaller models lack.

- Driess, D., et al. (2023). "PaLM-E: An Embodied Multimodal
  Language Model."
  [arXiv:2303.03378](https://arxiv.org/abs/2303.03378)

## From VLMs to VLAs

VLMs understand the visual world through language. But they cannot act
on it — they produce text, not motor commands. The extension from
seeing and describing to seeing and acting is what Vision-Language-Action
models provide. This is covered in the
[next chapter](03-vision-language-action-models.md).

## Key takeaways

- VLMs combine vision encoders and language models to understand images
  through natural language — enabling open-ended visual reasoning rather
  than narrow classification.
- In physical AI, VLMs provide safety monitoring, scene understanding,
  and data curation capabilities.
- The architecture follows a pattern: vision encoder → projection layer
  → language model, trained through alignment and instruction tuning.
- VLMs are the perception foundation that VLA models extend with
  action output for robot control.

## Further reading

- [CLIP](https://openai.com/research/clip) — OpenAI's foundational
  vision-language contrastive model.
- [LLaVA Project](https://llava-vl.github.io/) — The open-source
  visual instruction tuning project.
- [Qwen-VL Models](https://huggingface.co/Qwen) — Alibaba's
  vision-language model family on HuggingFace.
- Bordes, F., et al. (2024). "An Introduction to Vision-Language
  Modeling."
  [arXiv:2405.17247](https://arxiv.org/abs/2405.17247) — A
  comprehensive survey of VLM architectures and training approaches.
