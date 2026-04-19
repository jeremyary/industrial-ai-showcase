# Asset inventory — publicly available USD scenes and robot models

What we can actually use for demo scenes and robot embodiments, sourced from publicly-available content only. No authoring, no contracting. If a demo beat wants something not on this list, the beat gets rewritten around what IS on the list.

All items here fall under the Isaac Sim / Omniverse license posture already analyzed in `docs/licensing-gates.md` §6 — commercial use permitted for reference-material / on-prem-showcase scope.

## Scenes

### NVIDIA SimReady Warehouse Pack
- **What**: Curated warehouse-interior collection — ~18 GB, ~763 USD assets. Full warehouse environment + modular components (racks, pallets, zones, forklifts, loading docks) with semantic labeling and physics baked in.
- **Source**: NVIDIA Omniverse content CDN, accessible from Isaac Sim's NVIDIA Assets browser (`Window > Browsers > NVIDIA Assets > Industrial`). Also available as direct CloudFront download referenced by the SimReady docs.
- **Usable for**: the primary "Warehouse — Baseline" demo scene. Supports forklift / AMR movement, pallet manipulation, zone demarcation, safety-hazard scenarios.
- **Status**: known-working — has been successfully loaded in Isaac Sim 5.1 for warehouse demos in adjacent work, supports Isaac Sim 6.0 per NVIDIA's 6.0 samples.
- **Source**: [NVIDIA SimReady assets documentation](https://developer.nvidia.com/omniverse/simready-assets)

### NVIDIA SimReady Industrial Pack
- **What**: Smaller industrial pack — ~1.8 GB, ~72 USD assets. Factory-floor components (conveyor belts, workstations, safety equipment). Complements the warehouse pack when a scene leans more "assembly line" than "logistics."
- **Usable for**: secondary / variant scenes for Phase-4 verticalization (e.g., Electronics Manufacturing Line) if that comes into scope. Not Phase-1-necessary.
- **Source**: Same NVIDIA Omniverse content CDN path; bundled with Isaac Sim sample collection.

### Isaac Sim 6.0 stock warehouse scene (Warehouse01)
- **What**: Ships inside the Isaac Sim 6.0 sample content, accessible in the content browser under `Industrial/Buildings/Warehouse/`. Lighter-weight than SimReady pack — a simpler warehouse shell suitable for fast-iteration testing or low-GPU scenes.
- **Usable for**: development scenes, unit-test scenes, quickstart. Not the demo primary.
- **Source**: [Isaac Sim 6.0 warehouse tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/digital_twin/warehouse_logistics/tutorial_static_assets.html)

### NVIDIA Showroom / Palletjack tutorial scene
- **What**: Small scene used in NVIDIA's [Isaac Sim Module 3 synthetic-data tutorial](https://docs.nvidia.com/learning/physical-ai/getting-started-with-isaac-sim/latest/synthetic-data-generation-for-perception-model-training-in-isaac-sim/index.html). Generates synthetic palletjack images for object-detection training.
- **Usable for**: synthetic-data-generation demos (Phase 3 item). Object-detection training pipeline end-to-end.
- **Source**: Isaac Sim tutorial scene bundle.

## Robots

### Nova Carter
- **What**: NVIDIA's reference AMR (autonomous mobile robot) platform, built on the Nova Orin compute + sensor stack. Integrated with Isaac ROS for Nav2-based navigation.
- **Usable for**: the "mobile warehouse robot" role — pallet pickup/delivery, aisle navigation, charging-dock docking.
- **Source**: Ships with Isaac Sim samples. Additional tutorials at [NVIDIA Isaac ROS Nova Carter docs](https://nvidia-isaac-ros.github.io/concepts/manipulation/index.html).

### Unitree G1 (humanoid)
- **What**: Unitree Robotics' 29-DOF or 37-DOF humanoid. Commercially purchasable real robot with published USD models and RL training environments.
- **Usable for**: the "humanoid robot" role — dexterous manipulation, reach-and-place tasks, human-robot interaction demos.
- **Source primary**: [unitreerobotics/unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab) (official Unitree repo). [unitreerobotics/unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab) for RL baselines.
- **Source secondary**: [abizovnuralem/go2_omniverse](https://github.com/abizovnuralem/go2_omniverse) — community repo with Go2/G1 support including ROS2 hooks.
- **License**: Sim assets are openly published. Physical-robot deployment licensing is a separate conversation with Unitree, out of scope for us.

### Unitree Go2 (quadruped)
- **What**: Unitree's quadruped. Easier RL target than the humanoid; often used as a "walking test" precursor.
- **Usable for**: secondary demo beat if a quadruped fits a vertical scenario better than a humanoid (inspection, perimeter patrol). Not Phase-1-necessary.
- **Source**: Same repos as G1.

## Scene variation (instead of authoring new scenes)

When a demo beat wants variation (different lighting, weather, damaged state, edge cases), the path forward is **Cosmos Transfer 2.5** (Phase 3 synthetic data scope), not new scene authoring. Cosmos Transfer takes renders of our existing scenes and produces photoreal variations, which feed VLA training data generation. That's the answer to "can we have a nighttime warehouse / rainy factory loading dock / busy-with-workers warehouse?" — yes, via Cosmos, not by hand.

## What this inventory does NOT include

- **Custom warehouse scenes representing a specific customer's floor plan** — out of scope, no authoring.
- **Vertical-specific scenes** (automotive subassembly, electronics SMT line, etc.) — Phase 4 items; tackled only if a customer conversation specifically demands one, and even then we look first for publicly-available vertical references (NVIDIA DSX blueprint assets, BMW/PepsiCo showcased scenes where public).
- **Summit-floor-plan scenes** — specific real-venue reproductions are a separate project effort (the user's parallel work); they're not a dependency of this showcase.

## How this inventory gates demo scripts

The three demo scripts (tasks #14, #15, #16) can only specify beats that the above scenes + robots can support. If a script wants "the robot walks into a dense urban pedestrian environment," the script gets rewritten to "the robot navigates a warehouse aisle past simulated human workers" — because a warehouse scene + a Unitree G1 is what we have.

Updates to this inventory are welcome as new scenes become publicly available. Do NOT add items requiring authoring or contracted work.
