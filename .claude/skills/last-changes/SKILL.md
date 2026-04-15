---
description: Generate or update LAST_CHANGES.md at the project root with an educational deep-dive of everything that was just built or changed. Designed for after significant build sessions where the user needs to fully understand the AI-generated code before reviewing.
user_invocable: true
---

# Last Changes — Educational Deep-Dive

Generate `LAST_CHANGES.md` at the project root. This file educates the developer on everything that was just built or changed, so they can review, understand, and take ownership of AI-generated code.

## Process

Follow these steps in order:

### 1. Determine Scope of Changes

Identify what changed. Use these sources in priority order:

1. **Uncommitted changes**: `git status` and `git diff` (staged + unstaged)
2. **Recent commits on this branch**: `git log --oneline -20` and `git diff <base-branch>...HEAD`
3. If on the base branch with no feature branch, use uncommitted changes only

Collect the full list of files added, modified, and deleted.

### 2. Read and Understand Every Changed File

Read **every** file that was added or modified. Do not summarize from memory or the diff alone — re-read the actual file contents so the explanation is accurate to what's on disk right now.

For each file, understand:
- What it does and why it exists
- How it connects to other files in the project
- Key design decisions and trade-offs made
- Any non-obvious patterns or conventions used

### 3. Write LAST_CHANGES.md

Write (or overwrite) `LAST_CHANGES.md` at the project root using the structure below. The tone should be **a senior engineer walking a colleague through the code** — technical but approachable, explaining the "why" not just the "what".

```markdown
# What Changed

> Generated: <YYYY-MM-DD HH:MM> | Files: <N> added, <N> modified, <N> deleted

<1-2 paragraph executive summary: what was built, what problem it solves, and the high-level architecture.>

## Architecture & Data Flow

<Explain how the pieces fit together. Use a simple ASCII diagram if the system has multiple components that interact. Trace the primary data/request flow end-to-end.>

## File-by-File Walkthrough

### `<file-path>`
**Purpose:** <one line>

<Explain what this file does, why it's structured the way it is, and how it fits into the larger system. Call out:>
- Key functions/classes and what they do
- Design decisions (why X approach over Y)
- Dependencies on other files
- Anything non-obvious or that the developer should pay special attention to during review

<Repeat for each file, grouped logically (not alphabetically). Group related files together under a shared heading if they form a subsystem.>

## Key Design Decisions

<Bulleted list of architectural and implementation choices made, with brief rationale. Focus on decisions the developer might question or want to change.>

## What to Watch For

<Things the developer should specifically verify, test, or think critically about:>
- Security considerations
- Assumptions that might not hold
- Hard-coded values that may need tuning
- Areas most likely to need iteration

## How to Verify

<Concrete steps the developer can take right now to validate the changes work:>
- Commands to run (tests, linter, local stack)
- What to look for in the output
- Manual testing steps if applicable

## Glossary (if needed)

<Define any domain terms, acronyms, or project-specific concepts that appear in the code. Skip this section if everything is self-explanatory.>
```

### Writing Guidelines

- **Be specific.** Don't say "handles configuration" — say "reads SCENE_MODEL_URL and PLANNER_MODEL_URL from environment variables, falls back to localhost defaults for local dev."
- **Explain the why.** Don't just describe what code does — explain why it was written that way. "Uses AsyncOpenAI because the FastAPI endpoints are async and we don't want to block the event loop during model calls."
- **Flag uncertainty.** If a design choice could reasonably go either way, say so. The developer needs to know where they have room to change things.
- **Don't repeat the code.** Reference line numbers and function names, but don't paste code blocks unless a specific snippet needs annotation.
- **Keep it honest.** If something is a rough first pass or a known shortcut, say so. This is for the developer to understand the code, not to sell it.
- **Respect the Red Hat AI compliance rules.** This document IS the developer's tool for fulfilling their human-in-the-loop review obligation.
