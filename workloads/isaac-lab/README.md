# isaac-lab

**Role**: NVIDIA Isaac Lab training pipeline — runs as a Kubeflow Pipeline: scenario manifest → parallel Isaac Lab training Jobs → MLflow metrics → candidate policy → evaluation → MLflow Model Registry.

**Phase**: 2 (plan item 3 under Phase 2). Do not populate in Phase 1.

## Planned interfaces (Phase 2)

- Input: scenario manifest (references assets in Nucleus + optional Cosmos Transfer variations from `workloads/cosmos/transfer/`).
- Output: MLflow-registered policy with full lineage (training data → scenarios → metrics → approver).
- Compute: multi-GPU training Job on L40S-class nodes.

## Status

Empty scaffold. Phase 2.
