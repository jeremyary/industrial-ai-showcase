# Further Reading & Resources

## Foundational reading

### Books

- **Pfeifer, R. & Bongard, J. (2006). *How the Body Shapes the Way We
  Think: A New View of Intelligence*. MIT Press.**
  The academic foundation for embodied intelligence — why physical
  interaction shapes cognition.

- **Sutton, R. & Barto, A. (2018). *Reinforcement Learning: An
  Introduction* (2nd ed.). MIT Press.**
  [incompleteideas.net/book/the-book.html](http://incompleteideas.net/book/the-book.html)
  The foundational RL textbook. Essential for understanding how robot
  policies are trained in simulation.

- **Nikolenko, S. I. (2021). *Synthetic Data for Deep Learning*.
  Springer.**
  Comprehensive treatment of synthetic data generation, domain
  randomization, and domain adaptation.

### Papers

- **Brohan, A., et al. (2023). "RT-2: Vision-Language-Action Models
  Transfer Web Knowledge to Robotic Control."**
  [arXiv:2307.15818](https://arxiv.org/abs/2307.15818)
  The paper that established VLAs as a paradigm.

- **Tobin, J., et al. (2017). "Domain Randomization for Transferring
  Deep Neural Networks from Simulation to the Real World."**
  [arXiv:1703.06907](https://arxiv.org/abs/1703.06907)
  The seminal domain randomization paper.

- **Ha, D. & Schmidhuber, J. (2018). "World Models."**
  [arXiv:1803.10122](https://arxiv.org/abs/1803.10122)
  The influential paper framing world models as learned environment
  simulators.

- **LeCun, Y. (2022). "A Path Towards Autonomous Machine
  Intelligence."**
  [openreview.net](https://openreview.net/pdf?id=BZ5a1r-kVsf)
  Yann LeCun's position paper on world models and the JEPA
  architecture.

- **Driess, D., et al. (2023). "PaLM-E: An Embodied Multimodal
  Language Model."**
  [arXiv:2303.03378](https://arxiv.org/abs/2303.03378)
  Demonstrating VLMs for embodied reasoning.

- **Zhao, W., et al. (2020). "Sim-to-Real Transfer in Deep
  Reinforcement Learning for Robotics: a Survey."**
  [arXiv:2009.13303](https://arxiv.org/abs/2009.13303)
  Comprehensive survey of sim-to-real techniques.

- **Sculley, D., et al. (2015). "Hidden Technical Debt in Machine
  Learning Systems." NeurIPS 2015.**
  The foundational paper on ML operational challenges — relevant to
  understanding why MLOps matters.

## NVIDIA ecosystem

### Documentation

- [NVIDIA Physical AI](https://www.nvidia.com/en-us/ai/physical-ai/)
  — Platform overview and vision
- [NVIDIA Omniverse](https://docs.omniverse.nvidia.com/) —
  Platform documentation
- [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/) —
  Robotics simulation
- [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) — RL/IL training
  framework
- [Cosmos Models](https://docs.nvidia.com/cosmos/latest/introduction.html)
  — World foundation models
- [GR00T](https://developer.nvidia.com/isaac/gr00t) — Humanoid robot
  foundation model
- [NIMs](https://docs.nvidia.com/nim/index.html) — Inference
  microservices
- [OpenUSD](https://openusd.org/) — Scene description standard
- [Alliance for OpenUSD](https://aousd.org/) — Governance body

### Developer resources

- [NVIDIA Developer](https://developer.nvidia.com/) — SDKs, tools,
  tutorials
- [NVIDIA Isaac Platform](https://developer.nvidia.com/isaac) —
  Robotics platform overview
- [build.nvidia.com](https://build.nvidia.com/) — Try NIM APIs online
- [NGC Catalog](https://catalog.ngc.nvidia.com/) — Container images,
  models, Helm charts
- [NVIDIA Cosmos Cookbook](https://nvidia-cosmos.github.io/cosmos-cookbook/)
  — Recipes for Cosmos model usage

### GitHub repositories

- [Isaac Sim](https://github.com/isaac-sim/IsaacSim)
- [Isaac Lab](https://github.com/isaac-sim/IsaacLab)
- [GR00T](https://github.com/NVIDIA/Isaac-GR00T)
- [SONIC WBC](https://github.com/NVlabs/GR00T-WholeBodyControl)
- [PhysX](https://github.com/NVIDIA-Omniverse/PhysX)
- [Cosmos Transfer](https://github.com/nvidia-cosmos/cosmos-transfer2.5)

## Red Hat ecosystem

### Documentation

- [OpenShift Container Platform](https://docs.redhat.com/en/documentation/openshift_container_platform/)
- [Red Hat OpenShift AI](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/)
- [Red Hat OpenShift GitOps](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/)
- [Red Hat ACM](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/)
- [Single Node OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/installing_on_a_single_node/)
- [MicroShift](https://docs.redhat.com/en/documentation/red_hat_build_of_microshift/)
- [Compliance Operator](https://docs.redhat.com/en/documentation/openshift_container_platform/4.19/html/security_and_compliance/compliance-operator)

### GPU on OpenShift

- [NVIDIA GPU Operator on OpenShift](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/index.html)
- [GPU Monitoring Dashboard](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/enable-gpu-monitoring-dashboard.html)

### Upstream projects

- [KServe](https://kserve.github.io/website/) — Model serving
- [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/)
  — ML pipeline orchestration
- [MLflow](https://mlflow.org/) — Experiment tracking
- [Argo CD](https://argo-cd.readthedocs.io/) — GitOps
- [Strimzi](https://strimzi.io/) — Kafka on Kubernetes
- [Sigstore](https://www.sigstore.dev/) — Software signing
- [MuJoCo](https://mujoco.org/) — Physics engine

## Standards and frameworks

- **ISA/IEC 62443** — Industrial cybersecurity standard.
  [isa.org](https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards)
- **ISO 23247** — Digital twin framework for manufacturing.
  [iso.org](https://www.iso.org/standard/75066.html)
- **NIST SP 800-82 Rev. 3** — Guide to OT Security.
  [csrc.nist.gov](https://csrc.nist.gov/pubs/sp/800/82/r3/final)
- **DISA STIGs** — Security Technical Implementation Guides.
  [access.redhat.com](https://access.redhat.com/compliance/disa-stig)
- **SLSA** — Supply-chain Levels for Software Artifacts.
  [slsa.dev](https://slsa.dev/)
- **Industry 5.0** — EU research and innovation framework.
  [ec.europa.eu](https://research-and-innovation.ec.europa.eu/research-area/industrial-research-and-innovation/industry-50_en)

## Open-source datasets

- **Open X-Embodiment** — Robot manipulation data from 22 embodiments.
  [robotics-transformer-x.github.io](https://robotics-transformer-x.github.io/)
- **DROID** — Distributed Robot Interaction Dataset.
  [droid-dataset.github.io](https://droid-dataset.github.io/)
- **BridgeData V2** — Large-scale robot manipulation dataset.
  [rail-berkeley.github.io/bridgedata](https://rail-berkeley.github.io/bridgedata/)

## Open-source VLA models

- **OpenVLA** — Open-source VLA based on Llama 2 + SigLIP.
  [openvla.github.io](https://openvla.github.io/)
- **Octo** — General-purpose robot policy for fine-tuning.
  [octo-models.github.io](https://octo-models.github.io/)
- **GR00T N1** — NVIDIA's humanoid foundation model.
  [github.com/NVIDIA/Isaac-GR00T](https://github.com/NVIDIA/Isaac-GR00T)
