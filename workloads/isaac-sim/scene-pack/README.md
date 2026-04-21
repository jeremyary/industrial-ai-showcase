# scene-pack

Phase-1 scene-pack overlay USD generator. Per ADR-027 step 5.

## What it produces

`warehouse_scene_pack.usda` — a USD composition that:
- **Sublayers** `Isaac/Environments/Digital_Twin_Warehouse/small_warehouse_digital_twin.usd` from Nucleus (the NVIDIA-branded digital-twin-styled warehouse seeded by `apps/platform/nucleus-seeder`).
- **Adds** Phase-1 placements on top, all driven off `workloads/warehouse/warehouse-topology.yaml`:
  - Forklift `fl-07` referenced at its home dock with the right rotation.
  - Approach-point markers (low green disks) at each topology approach-point.
  - Dock markers (flat blue pads) at each dock.
  - `UsdGeomCamera` prims at each topology camera position + rotation, carrying a `showcase:publishesTopic` custom attribute so twin-update subscribers can bind camera prims → Kafka topics without a second lookup.

Isaac Sim at demo time opens the scene-pack overlay, not the raw warehouse USD. The `warehouse_baseline.py` scenario code (`workloads/isaac-sim/scenarios/`) will be retargeted in a follow-up.

## Why a generator instead of a hand-authored USDA

Every coordinate in the overlay comes from `warehouse-topology.yaml`. Hand-authoring the same numbers into the USD and the yaml would re-introduce the drift problem ADR-027 created the yaml to solve. The generator regenerates the USDA from the yaml in seconds — a coordinate change is "edit yaml, re-run builder Job, reload scene in Isaac Sim."

## How it runs

Same Kit-bootstrap pattern as `apps/platform/nucleus-seeder`:

1. Launch `isaacsim.SimulationApp({"headless": True})` up front so `pxr.Usd` and `omni.client` work in a bare Python process.
2. Open the topology yaml, build a new stage with `Usd.Stage.CreateNew`, sublayer the warehouse, define placement prims.
3. Save the USDA locally, then `omni.client.copy_async` it to `<NUCLEUS_ROOT>/ScenePacks/warehouse_scene_pack.usda`.

The Kubernetes Job wrapper is at `infrastructure/gitops/apps/platform/scene-pack-builder/`.

## Asset-id resolution

`warehouse-topology.yaml` uses logical asset ids (e.g. `nvidia/Forklift_A01`) instead of hard-coded Nucleus URLs, so the same yaml works across different Nucleus deployments. This generator keeps the id → URL mapping (`ASSET_REFS` near the top of `generate_overlay.py`) — the one place that cares about the deployment-specific Nucleus root. If you change `NUCLEUS_ROOT`, no other consumer of the topology yaml needs to change.

## Re-running

Safe to re-run anytime — `CopyBehavior.OVERWRITE` on the Nucleus target. Isaac Sim scene consumers reload the stage to pick up changes.

## What it doesn't do yet (followups)

- Aisle signage prims (text labels on the floor / wall). Purely cosmetic for the demo; skipped in v1.
- Pallet prim placement on obstruction. Done by the runtime **twin-update subscriber** (Session-18 plan step 11) — it reads `pallets.pallet-a47.obstruction_position` from the topology yaml and places the asset when a `fleet.safety.alerts` event fires. Not baked into the static overlay.
- Lights / stage illumination. Inherited from the sublayered warehouse; revisit if the existing lighting isn't enough for the camera-orbit smoke test.
