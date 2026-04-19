# cosmos

NVIDIA Cosmos world-foundation-model family. Deployed as KServe InferenceServices on the hub.

- **`reason-2/`** — Cosmos Reason 2 (scene reasoning VLM). **Phase 1** — powers the 5-min demo's camera-event beat via `camera-adapter/`.
- **`predict/`** — Cosmos Predict 2.5 (world model for pre-dispatch admission check). **Phase 3** — not yet scaffolded; arrives with the 60-min demo.
- **`transfer/`** — Cosmos Transfer 2.5 (scene-variation synthetic-data generation). **Phase 2** (limited pass for 20-min) + **Phase 3** (full synthetic-data factory).

NGC entitlement required for all three; see `docs/licensing-gates.md`.
