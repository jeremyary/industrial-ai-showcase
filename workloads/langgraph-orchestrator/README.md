# langgraph-orchestrator

**Role**: agentic orchestration via LangGraph (ADR-005) wrapped by Llama Stack's HIL + safety layer (ADR-019). Tool access exclusively via `mcp-servers/`.

**Phase**: 3 (plan item 4 under Phase 3). Do not populate in Phase 1.

## Hard constraint (design invariant, per ADR-026 and `demos/60-min-deep-dive/script.md`)

Llama Stack governance sits on the **GitOps / PR-open path only**, NEVER inline in serving-time robot command flow. No approval-gated hop between VLA inference and robot action. Adding latency to 10 Hz+ VLA inference is a deal-killer per Archetype-C persona review.

## Status

Empty scaffold. Phase 3.
