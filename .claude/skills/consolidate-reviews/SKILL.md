---
description: Consolidate multiple review files into a single de-duplicated triage table. Reads review files, merges overlapping findings, surfaces disagreements, and outputs a structured document for user triage.
user_invocable: true
---

# Review Consolidation

You are running the review consolidation skill. Your job is to read multiple review files for a single artifact, de-duplicate findings, surface disagreements, and produce a compact triage table for the user.

## Usage

```
/consolidate-reviews plans/reviews/requirements-review-*.md
/consolidate-reviews plans/reviews/technical-design-phase-1-review-*.md
```

The argument is a glob pattern or space-separated list of review file paths.

## Process

### 1. Read All Review Files

Read every file matching the provided pattern. For each file, extract:
- Reviewer name (from filename: `*-review-<reviewer>.md`)
- Verdict (APPROVE, REQUEST_CHANGES, NEEDS_DISCUSSION)
- Individual findings with their severity (Critical, Warning, Suggestion, Positive)
- For each finding: the description, affected location (file/section), and suggested resolution

### 1.5. Cross-Reference TECH_DEBT.md

Before de-duplicating, read `.changes/TECH_DEBT.md` (if it exists) and identify any findings that match items already tracked there. Remove these from the triage table and list them in a separate "Already Tracked" section with the mapping (e.g., "W-3 → TD-7"). This prevents the user from re-triaging issues that were already decided in previous reviews.

### 2. De-duplicate Findings

Two findings are duplicates when they:
- Reference the same file, section, or concept
- Describe the same root cause or concern
- Suggest the same or compatible resolutions

When merging duplicates:
- Keep the highest severity across reviewers
- Note all reviewers who flagged the issue
- Merge suggested resolutions (if compatible) or note the variations

### 3. Identify Disagreements

Flag findings where reviewers disagree on:
- **Severity** — one reviewer says Critical, another says Suggestion for the same issue
- **Resolution** — reviewers propose conflicting fixes for the same issue
- **Verdict** — one reviewer approves, another requests changes

### 4. Produce Consolidated Output

Write the consolidated review to `plans/reviews/<artifact>-review-consolidated.md`.

Determine the artifact name from the input pattern:
- `requirements-review-*.md` -> artifact is `requirements`
- `technical-design-phase-1-review-*.md` -> artifact is `technical-design-phase-1`
- `product-plan-review-*.md` -> artifact is `product-plan`
- `architecture-review-*.md` -> artifact is `architecture`
- `work-breakdown-phase-N-review-*.md` -> artifact is `work-breakdown-phase-N`

## Output Format

```markdown
# Consolidated Review: <Artifact Name>

**Reviews consolidated:** <comma-separated list of review files>
**Date:** <current date>
**Verdicts:** <reviewer: verdict, reviewer: verdict, ...>

## Summary

- Total findings across all reviews: N
- De-duplicated findings: M
- Reviewer disagreements: K
- Breakdown: X Critical, Y Warning, Z Suggestion, W Positive

## Triage Required

### Critical (must fix before proceeding)

| # | Finding | Flagged By | Suggested Resolution | Suggested Disposition | Decided |
|---|---------|-----------|---------------------|----------------------|---------|
| C-1 | <description> | Architect, Orchestrator | <resolution> | <Fix/Improvement/Defer/Dismiss + brief rationale weighing project goals> | _pending_ |
| C-2 | ... | ... | ... | ... | _pending_ |

### Warning (should fix)

| # | Finding | Flagged By | Suggested Resolution | Suggested Disposition | Decided |
|---|---------|-----------|---------------------|----------------------|---------|
| W-1 | ... | ... | ... | ... | _pending_ |

### Reviewer Disagreements

| # | Issue | Reviewer A | Reviewer B | Suggested Disposition | Decided |
|---|-------|-----------|-----------|----------------------|---------|
| D-1 | <issue description> | <reviewer>: <position + severity> | <reviewer>: <position + severity> | <disposition + rationale> | _pending_ |

### Suggestions (improve if approved)

| # | Finding | Flagged By | Suggested Resolution | Suggested Disposition | Decided |
|---|---------|-----------|---------------------|----------------------|---------|
| S-1 | ... | ... | ... | ... | _pending_ |

### Positive (no action needed)

- <positive finding 1> — <reviewer>
- <positive finding 2> — <reviewer>
```

## Disposition Values

There are two disposition columns:

- **Suggested Disposition** — YOUR recommendation when generating the consolidation, weighing the finding against the project's actual goals and context.
- **Decided** — Starts as `_pending_`. Updated to the final decision after triage discussion with the user. Valid values: `Fix`, `Improvement`, `Defer`, `Dismiss`. Items marked `Defer` are picked up by the `/tech-debt` skill for tracking.

Valid dispositions for both columns:

| Disposition | Meaning |
|-------------|---------|
| **Fix** | Must be addressed before proceeding |
| **Improvement** | Would make the artifact better but not blocking |
| **Defer** | Valid concern but out of scope for this artifact |
| **Dismiss** | Disagree with finding — document rationale |

Always include a brief rationale tied to the project context. For example, a production-grade auth concern might be "Defer — demo environment behind VPN, no public exposure" while a robot safety issue might be "Fix — robot could execute fabricated waypoints during live demo."

## Guidelines

- **Compact output.** Target ~100-200 lines for a typical 3-reviewer gate. The point is to reduce what the orchestrator needs to read, not to produce another long document.
- **Preserve attribution.** Every finding must note which reviewer(s) flagged it. This matters for the "Explain It to Me" protocol.
- **Higher severity wins.** When de-duplicating, if one reviewer says Critical and another says Warning, the consolidated finding is Critical.
- **Suggest dispositions in context.** Unlike the individual reviewers (who flag everything they see), your job is to weigh each finding against the project's actual goals. A finding that's Critical for a production banking app might be Defer for a Summit demo. Always explain your reasoning. The user makes the final call.
- **Location details stay in individual reviews.** The consolidated table omits file:line locations to keep it scannable. The user can drill into the individual review files for specifics.
- **Omit empty sections.** If there are no disagreements, skip the Disagreements section. If there are no Critical findings, skip that section.
