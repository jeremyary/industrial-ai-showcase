# Physical & Industrial AI Learning Guide

This guide is for engineers with a solid foundation in containers, Kubernetes,
and cloud-native infrastructure who are stepping into the world of physical AI,
industrial AI, and the technology ecosystems that support them.

By the time you work through this material, you will understand:

- What physical AI and industrial AI are, why they matter, and how they differ
  from the AI you already encounter in software systems
- The core technical concepts — digital twins, simulation, embodied AI,
  synthetic data, and the models that make robots perceive and act
- How NVIDIA's ecosystem (Omniverse, Isaac, Cosmos, GR00T) provides the
  simulation, training, and inference infrastructure for physical AI
- How Red Hat's platform (OpenShift, OpenShift AI, GitOps, ACM) provides
  the operational foundation that takes physical AI from research to
  production
- How these two ecosystems compose into a stack that covers the full
  lifecycle — from simulated training environments to deployed robots
  on factory floors

## How to use this guide

The guide is organized into five parts that build on each other:

**Part 1: Foundations** starts with the big picture — what physical AI is,
why factories are different from data centers, what digital twins and
simulation actually do, and why embodied AI is a fundamentally different
problem than building a chatbot. Read this first. The concepts here
underpin everything that follows.

**Part 2: Technical Concepts** goes deeper into the technologies that make
physical AI work — scene description formats, vision-language models,
the leap to vision-language-action models, world models, the MLOps
lifecycle for physical systems, edge computing constraints, and fleet
orchestration. This is where you build the vocabulary and mental models
you will need.

**Part 3: NVIDIA Ecosystem** maps NVIDIA's product and platform offerings
to the concepts from Parts 1 and 2. Omniverse, Isaac Sim, Cosmos,
GR00T, NIMs, Nucleus — what each does, how they relate, and where they
sit in the larger picture.

**Part 4: Red Hat Platform** does the same for Red Hat's stack —
OpenShift AI, model serving, training pipelines, GitOps for ML,
multi-cluster edge management, and the security/compliance posture
that regulated industries demand.

**Part 5: Bringing It Together** shows how these ecosystems compose —
the end-to-end flow from a simulated warehouse scene to a trained robot
policy running on a factory floor, managed by the same infrastructure
patterns you already use for conventional workloads.

Work through the material at whatever pace suits you. Some sections will
feel familiar if you have adjacent experience (ML pipelines, GPU
scheduling). Others will be genuinely new territory. Both are expected.

## Serving this guide locally

This guide is built with [MkDocs](https://www.mkdocs.org/) and the
[Material theme](https://squidfunk.github.io/mkdocs-material/). To
browse it as a website:

```bash
cd docs/learning-guide
pip install mkdocs-material
mkdocs serve
```

Then open [http://localhost:8000](http://localhost:8000).

The guide also deploys automatically to GitHub Pages on every push to
`main` that touches `docs/learning-guide/`. The markdown files read
well in any editor or directly on GitHub as well.
