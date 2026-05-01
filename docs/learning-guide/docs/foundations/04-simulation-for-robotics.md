# Simulation for Robotics

## Why simulation is not optional

If you come from software engineering, training a model means assembling
a dataset, running a training loop, and evaluating on a test set. The
data exists; you just need enough of it. In robotics, the data problem
is fundamentally harder.

A robot learning to pick objects from a bin will fail thousands of times
before succeeding. Each failure means a dropped object, a potential
collision, wear on the hardware, and someone resetting the scene
manually. A single grasp attempt takes 5–10 seconds in the real world.
A million attempts — a modest number for reinforcement learning — would
take 116 continuous days of operation with no downtime, no maintenance,
and no broken hardware.

Simulation changes this equation. A GPU cluster running thousands of
parallel simulated environments can generate the equivalent of years
of robot experience in hours. Failed grasps cost nothing. Scenes reset
instantly. No hardware breaks. No one gets hurt.

This is why virtually every modern physical AI system is trained
primarily in simulation and then transferred to real hardware — a
process called **sim-to-real transfer**.

## Physics engines

At the core of every robotics simulator is a physics engine — the
software that computes what happens when objects interact. Different
engines make different trade-offs between speed, accuracy, and the
types of physical phenomena they can model.

### PhysX (NVIDIA)

PhysX is NVIDIA's physics engine and the dominant choice for
GPU-accelerated robotics simulation. PhysX 5 supports:

- Rigid body dynamics (boxes, spheres, meshes colliding and stacking)
- Articulated bodies (robot arms with joints, constraints, motors)
- Soft body simulation (deformable objects)
- Fluid simulation (particles, liquids)
- GPU parallelism (thousands of environments running simultaneously)

PhysX uses a temporal Gauss-Seidel (TGS) solver for contact resolution,
which trades some accuracy for stability and speed. This makes it
excellent for training at scale where you need thousands of parallel
environments, even if individual contacts are not perfectly accurate.

PhysX 5 is open-source under the BSD-3 license.

- [PhysX on GitHub](https://github.com/NVIDIA-Omniverse/PhysX)

### MuJoCo

MuJoCo (Multi-Joint dynamics with Contact) was developed by Emanuel
Todorov at the University of Washington and is now maintained by Google
DeepMind as open-source software. It is the standard physics engine for
reinforcement learning research.

MuJoCo uses a convex optimization approach to contact resolution that
is more physically accurate than impulse-based solvers, particularly
for manipulation tasks where contact dynamics (friction, sliding,
rolling) are critical. It is fast on CPU and has GPU-accelerated
variants (MuJoCo XLA / MJX) for massive parallelism.

The "MuJoCo benchmarks" (a set of locomotion and manipulation tasks)
are a standard evaluation suite for RL algorithms.

- [MuJoCo](https://mujoco.org/)
- Todorov, E., Erez, T., & Tassa, Y. (2012). "MuJoCo: A physics
  engine for model-based control." IROS 2012.

### Bullet / PyBullet

Bullet is an open-source physics engine (zlib license) widely used in
robotics research. PyBullet provides a Python API that integrates with
OpenAI Gymnasium environments, making it popular for RL experiments.
It is less accurate for contact-rich manipulation than MuJoCo but
freely available and well-documented.

- [PyBullet](https://pybullet.org/)

### Drake

Drake (from MIT and Toyota Research Institute) is not just a physics
engine but a full systems framework for model-based design and control.
It uses a hydroelastic contact model that is more physically principled
than penalty-based methods, making it particularly strong for
manipulation planning and control verification.

- [Drake](https://drake.mit.edu/)

## Rendering: ray tracing vs. rasterization

Robots that use cameras need to be trained on images that look like what
real cameras see. The rendering method used to generate those training
images directly affects how well the trained policy transfers to reality.

### Rasterization

Rasterization is the traditional real-time rendering approach: project
3D triangles onto a 2D screen, apply textures, and approximate lighting
effects (shadows, reflections, ambient occlusion) with various hacks.
It is fast — games run at 60+ FPS using rasterization — but the results
have telltale visual differences from real photographs.

Shadows are hard-edged or use imprecise shadow maps. Reflections are
screen-space approximations that fail for off-screen objects. Indirect
lighting is faked with ambient terms. A vision model trained on
rasterized images learns these artifacts as features, causing failures
when it encounters real camera images.

### Ray tracing

Ray tracing simulates the physical behavior of light. Rays are cast from
the camera through each pixel, bouncing off surfaces according to
material properties (reflection, refraction, absorption, scattering).
This naturally produces:

- Soft shadows with correct penumbrae
- Accurate reflections (including inter-object reflections)
- Global illumination (light bouncing between surfaces)
- Physically correct depth of field and motion blur
- Caustics (light focused through transparent materials)

The resulting images are photorealistic because the process mirrors
real optics. NVIDIA's RTX GPUs provide hardware-accelerated ray tracing
(dedicated RT cores) that makes this feasible at the resolutions and
frame rates needed for training data generation.

### Why this matters for robotics

If you train a vision model on rasterized images, the model learns
visual features specific to rasterization artifacts. When deployed on
a real robot with a real camera, the visual domain gap causes
performance degradation. Ray-traced training images reduce this gap
because they more closely match what real cameras capture.

This is why NVIDIA Isaac Sim uses RTX ray tracing as its rendering
pipeline — the synthetic training data it produces is closer to reality,
which means better sim-to-real transfer.

## The sim-to-real gap

The sim-to-real gap is the performance drop that occurs when a policy
trained in simulation is deployed on a physical robot. No simulation
perfectly replicates reality, and the differences compound:

### Visual domain gap

Simulated images differ from real camera images in:

- Lighting subtleties (simulated light lacks atmospheric scattering,
  dust particles, subtle color shifts from wall bounces)
- Material appearance (real surfaces have scratches, wear, subsurface
  scattering that is computationally expensive to simulate)
- Sensor characteristics (real cameras have lens distortion, vignetting,
  chromatic aberration, rolling shutter, noise patterns unique to their
  sensor hardware)
- Environmental complexity (real scenes have infinite small details —
  cable clutter, stains, wear marks — that are impractical to model)

### Physics gap

Simulated physics differs from reality in:

- Contact dynamics (friction is hard to model accurately — it depends
  on surface finish, contamination, temperature, speed)
- Actuator behavior (real motors have backlash, cogging torque, thermal
  drift, cable routing effects)
- Object properties (simulated masses and moments of inertia are
  estimates from CAD models; real objects have manufacturing tolerances)
- Deformable interactions (cables, fabric, soft packaging behave
  differently in simulation than in reality)

### Strategies for closing the gap

#### Domain randomization

The most widely used approach. During training, randomize visual and
physical parameters extensively — lighting, textures, object positions,
friction coefficients, sensor noise — so that the policy learns to be
invariant to these variations. The real world becomes "just another
randomization" that falls within the training distribution.

This was demonstrated spectacularly by OpenAI's Dactyl project, which
trained a Shadow Hand to manipulate a Rubik's cube entirely in
simulation with massive domain randomization, then transferred directly
to physical hardware.

- Tobin, J., et al. (2017). "Domain Randomization for Transferring
  Deep Neural Networks from Simulation to the Real World."
  [arXiv:1703.06907](https://arxiv.org/abs/1703.06907)

#### System identification

Measure the real system's physical parameters (friction, damping, motor
curves) and tune the simulation to match. This reduces the physics gap
for a specific robot in a specific environment, but does not help with
generalization to new environments.

#### Domain adaptation

Use a neural network to transform simulated images to look like real
images (or learn features that are invariant to the synthetic/real
distinction). This is covered in detail in the
[Synthetic Data chapter](06-synthetic-data.md).

#### Sim-to-real fine-tuning

Train the base policy in simulation, then fine-tune with a small amount
of real-world data. This combines the data efficiency of simulation with
the fidelity of real experience. The simulation provides the broad skill;
real data provides the calibration.

## Key simulators for robotics

| Simulator | Physics | Rendering | Primary use case | License |
|-----------|---------|-----------|-----------------|---------|
| **NVIDIA Isaac Sim** | PhysX 5 (GPU) | RTX ray tracing | Industrial robotics, synthetic data, RL at scale | Free for individuals |
| **MuJoCo** | MuJoCo (CPU/GPU) | Basic OpenGL | RL research, manipulation, locomotion | Apache 2.0 |
| **Gazebo** | DART/Bullet | OGRE2 (rasterization) | ROS integration, algorithm prototyping | Apache 2.0 |
| **PyBullet** | Bullet | OpenGL | RL research, education | zlib |
| **CoppeliaSim** | Multiple backends | OpenGL | Education, multi-physics comparison | Free for education |
| **SAPIEN** | PhysX | GPU rendering | Articulated object manipulation | MIT |

Isaac Sim is covered in detail in
[Part 3: NVIDIA Ecosystem](../nvidia-ecosystem/02-isaac.md).

## Reinforcement learning in simulation

Reinforcement learning (RL) is the dominant paradigm for training robot
control policies in simulation. The pattern:

1. **Environment**: The robot and its surroundings, implemented in the
   simulator. Defined by an observation space (what the robot sees/senses)
   and an action space (what the robot can do).

2. **Policy**: A neural network that maps observations to actions. This
   is what you are training.

3. **Reward function**: A scalar signal that tells the policy how well
   it is doing. Designing good reward functions is an art —
   poorly-specified rewards lead to "reward hacking" where the agent
   finds unintended shortcuts.

4. **Parallel environments**: The key advantage of GPU-accelerated
   simulation. Run thousands of copies of the environment simultaneously,
   each with a different randomization, collecting experience in
   parallel. NVIDIA Isaac Lab can run 4,096+ environments on a single
   GPU.

5. **Policy optimization**: Algorithms like PPO (Proximal Policy
   Optimization) or SAC (Soft Actor-Critic) update the policy network
   based on accumulated experience across all parallel environments.

6. **Evaluation**: Test the trained policy on held-out scenarios in
   simulation, then on real hardware. Measure success rate, efficiency,
   and safety metrics.

### The RL data scale

To put the compute requirements in perspective: training a locomotion
policy for a quadruped robot typically requires 10–100 million
environment steps. At 1,000 parallel environments running at 1,000 Hz
simulated time, this is 10,000–100,000 seconds of wall-clock time
(roughly 3–28 hours on a single GPU). Training a dexterous manipulation
policy can require 1–10 billion steps, pushing to days or weeks even
with massive parallelism.

This is why GPU-accelerated physics is not a convenience — it is a
requirement. CPU-based simulation cannot achieve the throughput needed
for modern RL at scale.

## Key takeaways

- Simulation is essential for physical AI because real-world training
  is too slow, expensive, dangerous, and data-scarce.
- Physics engines (PhysX, MuJoCo, Bullet, Drake) compute physical
  interactions; the choice affects accuracy, speed, and GPU utilization.
- Ray-traced rendering produces photorealistic training images that
  reduce the visual sim-to-real gap.
- The sim-to-real gap has visual, physics, and embodiment components;
  it is addressed through domain randomization, system identification,
  domain adaptation, and fine-tuning.
- Reinforcement learning in simulation requires massive parallelism
  (thousands of environments) enabled by GPU-accelerated physics.

## Further reading

- Zhao, W., et al. (2020). "Sim-to-Real Transfer in Deep Reinforcement
  Learning for Robotics: a Survey."
  [arXiv:2009.13303](https://arxiv.org/abs/2009.13303)
- OpenAI (2019). "Solving Rubik's Cube with a Robot Hand."
  [arXiv:1910.07113](https://arxiv.org/abs/1910.07113) —
  The landmark domain randomization result.
- Rudin, N., et al. (2022). "Learning to Walk in Minutes Using Massively
  Parallel Deep Reinforcement Learning." CoRL 2021.
  [arXiv:2109.11978](https://arxiv.org/abs/2109.11978) —
  Isaac Gym-based locomotion training transferred to real quadrupeds.
- NVIDIA Isaac Sim documentation —
  [developer.nvidia.com/isaac-sim](https://developer.nvidia.com/isaac-sim)
- NVIDIA Isaac Lab —
  [isaac-sim.github.io/IsaacLab](https://isaac-sim.github.io/IsaacLab/)
