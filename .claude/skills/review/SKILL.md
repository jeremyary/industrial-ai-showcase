---
description: Run a multi-agent parallel code review. Analyzes the project to determine which reviewer perspectives are most relevant, spawns specialized Opus agents in parallel, then consolidates findings into a single triage table with suggested dispositions.
user_invocable: true
---

# Code Review — Multi-Agent Orchestration

Run a comprehensive review by spawning multiple specialized Opus agents in parallel, each focused on a different review perspective. After all agents complete, consolidate their findings using `/consolidate-reviews`.

## Process

### 1. Understand What Changed

Determine the scope of changes to review:

1. Run `git status` and `git diff` (staged + unstaged)
2. Run `git log --oneline -20` and `git diff <base-branch>...HEAD` if on a feature branch
3. If on the base branch with no feature branch, review all project files

Summarize the scope to the user: number of files, what subsystems are touched, the nature of the changes.

### 2. Select Reviewer Perspectives

Based on what you see in the codebase and the changes, decide which reviewer perspectives are most valuable. Read the project structure, key files, and any CLAUDE.md / rules files to understand the project's domain and tech stack.

Choose 3-6 reviewer personas from the pool below, or invent new ones if the project demands it. Not every project needs every reviewer — pick the ones that will surface real issues for THIS codebase.

**Reviewer pool (use as inspiration, not a rigid list):**

- **Quality & Correctness** — logic errors, edge cases, race conditions, error handling, test coverage gaps, code smells
- **Security** — OWASP top 10, input validation, auth, secrets, injection, container hardening, DoS vectors
- **API Design & Contracts** — request/response models, schema consistency, versioning, OpenAPI accuracy, backwards compatibility
- **Ops & Deployment** — container image, k8s manifests, health probes, observability, scaling, CI/CD, dependency management
- **Performance** — hot paths, N+1 queries, memory allocation, connection pooling, caching opportunities
- **Domain/Architecture** — domain model correctness, architectural patterns, separation of concerns, coupling
- **Data & State** — database migrations, data integrity, transaction boundaries, caching coherence
- **Frontend/UX** — accessibility, responsive design, error states, loading states (for frontend projects)
- **ML/AI** — prompt engineering, model integration patterns, eval coverage, inference optimization (for AI projects)

**Selection criteria:**
- Does the project have deployment manifests? → include Ops
- Does it have an API surface? → include API Design
- Does it handle user input or external data? → include Security
- Does it integrate with ML models? → include ML/AI
- Always include Quality & Correctness

Tell the user which perspectives you selected and why.

### 3. Spawn Review Agents

Create the staging directory: `.changes/reviews/`

Spawn all selected reviewers as **parallel background agents** using the Agent tool with `model: opus`. Each agent should:

- Be named `review-<perspective>` (e.g., `review-quality`, `review-security`)
- Read ALL relevant files for their perspective (not just the diff — full file contents for context)
- Write their report to `.changes/reviews/code-review-<perspective>.md`
- Use this report format:

```markdown
## Review: <Perspective Name>

**Files reviewed:** <count> | **Reviewer:** <perspective>-agent

### Critical
- **[file:line]** — [description]
  **Fix:** [specific suggestion]

### Warning
- **[file:line]** — [description]
  **Fix:** [specific suggestion]

### Suggestion
- **[file:line]** — [description]

### Positive
- **[file:line]** — [what was done well]

---
**Verdict:** APPROVE / REQUEST_CHANGES / COMMENT
**Summary:** [1-2 sentence overall assessment]
```

Omit empty severity sections. Always include Positive section.

**Agent prompt guidelines:**
- Give each agent a clear identity: "You are a senior [security/ops/API/etc.] engineer reviewing..."
- Include enough project context that the agent can do its job without asking questions — what the project does, its tech stack, deployment target, who consumes it
- Tell each agent exactly which files/directories to read for their perspective
- Remind agents to read full file contents, not just skim

### 4. Wait and Consolidate

After all agents complete, run the `/consolidate-reviews` skill on `.changes/reviews/code-review-*.md` to produce the consolidated triage table with suggested dispositions.

Present the consolidated summary to the user:
- How many agents ran
- Total vs de-duplicated findings
- Critical count and one-line summary of each
- Items you suggested as Fix vs Defer and why

### 5. Triage Discussion

The consolidated review has `Decided: _pending_` on every item. Walk through the findings with the user to set final dispositions.

### 6. Next Steps Reminder

After presenting the consolidated summary, always end with this reminder block:

```
**Next steps when you're ready:**
- `/tech-debt` — track deferred items from this and all previous reviews
- `/archive-changes <slug>` — bundle LAST_CHANGES.md + these reviews into `.changes/<date>_<slug>/`
```
