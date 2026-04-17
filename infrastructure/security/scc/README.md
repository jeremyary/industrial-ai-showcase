# Security Context Constraints (SCCs)

No SCCs live here yet. OCP's `restricted-v2` default covers every workload deployed through Phase 0.

## When a workload needs a custom SCC

1. Author the SCC manifest under `workloads/<component>/scc/` (not here — workload-specific SCCs live with the workload that needs them).
2. Bind the SCC to the workload's ServiceAccount only — never to `system:authenticated`.
3. Document the privilege gap + justification in the workload's README.
4. Open a security-review-required PR (additional reviewer beyond normal approval).

This directory hosts **cross-cutting SCCs** — ones that multiple workloads share. Empty in Phase 0; expect first entries in Phase 2+ when Isaac Lab training needs access to `nvidia.com/gpu` resources with non-default UIDs.

## Related

- `docs/07-decisions.md` — ADR-009, ADR-016 for supply-chain + signing context.
- `infrastructure/security/network-policies/` — companion east-west restriction layer.
