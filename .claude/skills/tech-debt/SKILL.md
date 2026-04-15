---
description: Incrementally update .changes/TECH_DEBT.md by adding newly deferred items from the latest consolidated review. Run before /archive-changes to ensure deferred items are captured.
user_invocable: true
---

# Technical Debt Tracker

Incrementally update `.changes/TECH_DEBT.md` by scanning the most recent consolidated review for items marked `Defer` that aren't already tracked. This preserves deferred items before a review is archived, so nothing falls through the cracks.

## Process

### 1. Read Current State

Read `.changes/TECH_DEBT.md` if it exists. Note the highest `TD-N` ID so new items get appended with the next number.

### 2. Find the Latest Consolidated Review

Look in the staging area first:
- `.changes/reviews/*-consolidated.md`

If staging is empty, find the most recently archived one:
- `.changes/*/reviews/*-consolidated.md` (sorted by directory date)

### 3. Extract New Deferred Items

Parse the consolidated review for table rows where `Decided` contains `Defer`. For each, extract:
- The finding ID (e.g., C-3, W-5, S-2)
- The finding description
- The original severity (Critical, Warning, Suggestion — inferred from ID prefix)
- The suggested resolution
- The deferral rationale from the Suggested Disposition column
- The source (archive slug or `staging`)

**Skip items already in TECH_DEBT.md.** Match by description content, not by finding ID (since C-3 in one review is unrelated to C-3 in another). If an item's description substantially matches an existing TD entry, skip it.

### 4. Append New Items

Add each new deferred item to the appropriate category section in TECH_DEBT.md with the next available `TD-N` ID. Categorize by content:

- **Security** — auth, input validation, injection, secrets, TLS, container hardening
- **Reliability** — retries, timeouts, health probes, training hyperparameters, reward tuning
- **Code Quality** — type safety, test coverage, documentation, code patterns
- **Ops & Deployment** — dependency pinning, image tags, manifests, Makefile, container build

Update the `Last updated` timestamp and `Sources` count in the header.

### 5. Flag Untriaged Items

Also scan for rows where `Decided` is still `_pending_`. Report these to the user — they need triage before archiving.

### 6. Report

Tell the user:
- How many new items were added (with their TD-N IDs)
- How many were already tracked (skipped)
- Whether any untriaged items remain
- The file is ready for `/archive-changes`

## File Format

```markdown
# Technical Debt

> Last updated: YYYY-MM-DD HH:MM
> Sources: N consolidated reviews scanned

## Active Debt

Items deferred during review triage. Each links back to its source review for full context.

### Security

| # | Finding | Original Severity | Suggested Resolution | Deferred Because | Source |
|---|---------|------------------|---------------------|-----------------|--------|
| TD-1 | <description> | Critical | <resolution> | <rationale> | <archive slug or "staging"> |

### Reliability
...

### Code Quality
...

### Ops & Deployment
...
```

## Guidelines

- **Stable IDs.** Once a `TD-N` ID is assigned, it never changes. Always append new items at the end with the next sequential number.
- **Incremental, not full rebuild.** Don't rewrite the file from scratch — read, diff, append. Existing items are preserved exactly as written.
- **Omit empty sections.** If no items fall in a category, skip that section.
- **Don't editorialize.** The rationale column should reflect what was decided during triage, not new opinions.
- **Source = where to find details.** Use the archive slug (e.g., `2026-04-08_initial-build`) for archived reviews, or `staging` for the current unarchived review.
