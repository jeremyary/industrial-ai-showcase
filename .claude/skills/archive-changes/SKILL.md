---
description: Archive the current LAST_CHANGES.md and any review files to .changes/<date>_<slug>/ for permanent reference. Use after reviewing and approving a changeset to preserve the educational deep-dive and reviews together. Pass an optional slug argument to name the changeset (e.g., /archive-changes initial-build).
user_invocable: true
---

# Archive Changes

Archive the current `LAST_CHANGES.md` and associated review files into a named subdirectory under `.changes/` so they're preserved together for future reference.

## Usage

```
/archive-changes <slug>
/archive-changes
```

The slug is a short, kebab-case label for the changeset (e.g., `initial-build`, `camera-frames-refactor`, `health-probe-fix`). If omitted, fall back to timestamp-only naming.

## Process

1. **Verify LAST_CHANGES.md exists** at the project root. If it doesn't, tell the user to run `/last-changes` first.

2. **Extract the date** from the `> Generated: YYYY-MM-DD HH:MM` line in LAST_CHANGES.md. If no timestamp is found, use today's date.

3. **Determine the archive directory name:**
   - With slug argument: `.changes/YYYY-MM-DD_<slug>/` (e.g., `.changes/2026-04-03_initial-build/`)
   - Without slug: `.changes/YYYY-MM-DD_HHMM/` (e.g., `.changes/2026-04-03_1100/`)

4. **Create the archive directory** and copy files into it:
   - Copy `LAST_CHANGES.md` to `.changes/<dir>/LAST_CHANGES.md`
   - If `.changes/reviews/` exists and contains files, move (not copy) the entire contents into `.changes/<dir>/reviews/`. The `.changes/reviews/` staging area should be empty after archival so it's clean for the next review cycle.

5. **Do not delete** `LAST_CHANGES.md` from the project root — it stays as the current working document.

6. **Confirm** to the user:
   - The archive directory path
   - Number of files archived (LAST_CHANGES.md + N review files)
   - That `.changes/reviews/` staging area has been cleared
