# Red Hat AI Compliance

This rule codifies Red Hat's policies on the use of AI code assistants. It applies to all
files and all agents.

## Human-in-the-Loop Obligation

- All AI-generated code **must** be reviewed, tested, and validated by a human before merge
- The developer who commits AI-generated code is accountable for its correctness, security, and legal compliance
- AI output is a starting point, not a finished product — treat it as untrusted input that requires verification
- Never merge AI-generated code without running the project's test suite and linter

## Sensitive Data Prohibition

- **Never** input the following into AI prompts or context:
  - Red Hat confidential or proprietary information
  - Customer data or personally identifiable information (PII)
  - Trade secrets, internal architecture details, or infrastructure specifics
  - Credentials, API keys, tokens, or passwords
  - Internal hostnames, URLs, or network topology (e.g., `*.redhat.com`, `*.corp.redhat.com`)
- Use synthetic or anonymized data when providing examples to AI tools
- When describing a problem, abstract away identifying details — focus on the technical pattern, not the specific system

## AI Marking Requirements

All AI-assisted work must be marked to maintain transparency and traceability.

### Source File Comment
Every code file produced or substantially modified with AI assistance must include a comment near the top:

- **JS/TS:** `// This project was developed with assistance from AI tools.`
- **Python:** `# This project was developed with assistance from AI tools.`
- **Other languages:** Use the appropriate comment syntax with the same text

This is a Red Hat policy requirement (see "Guidelines on Use of AI Generated Content"), not just a style preference.

### Commit Trailers
When committing code that was written or substantially shaped by an AI tool, include a trailer in the commit message using ONE of these choices:

- `Co-Authored-by: Claude` — for commits where AI assisted but a human drove the design and logic
- `Generated-by: Claude` — for commits where the code is substantially AI-generated

These trailers go in the footer section of the commit message, after the body.

**Do not include model names or version identifiers in the trailer.** `Co-Authored-by: Claude` is the authorised form; no `[Opus 4.x]`, no `Claude Code`, no model suffixes. This keeps attribution stable across model upgrades and avoids the impression that a specific model release is being endorsed.

### Pull Request Descriptions
When a PR contains substantial AI-generated code, note this in the PR description. Include the same trailer in the PR description footer:

- `Co-Authored-by: Claude`

Same rule as commits: no model name.

### README

When a project contains substantial AI-generated code, include a note in the README following the title and summary description like this:

> [!NOTE]
> This project was developed with assistance from AI tools.

## Copyright and Licensing

AI-generated content has unresolved copyright status. Our collaboration (human + AI) cannot issue a license on content whose copyright status we do not control. This is not a stylistic preference — it is a legal constraint.

- **Never** generate, draft, or request a `LICENSE` file in any form.
- **Never** add license headers to source files.
- **Never** add license declarations to project metadata (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod` headers, chart metadata, container labels, etc.).
- **Never** recommend or template a license choice, even "just as a placeholder."
- **Never** mention or reference a license in README files, documentation, contribution guides, or PR descriptions.
- If a scaffolding template, linter, or tool complains about a missing license, leave it unsatisfied and flag the gap as a human-to-resolve TODO. Do **not** satisfy the tool by inventing a license.
- Licensing decisions must be made by humans with Red Hat Legal guidance. That is not an AI task, and no AI commit or PR should include license material of any kind.
- Verify that generated code does not closely match existing copyrighted implementations — if output looks suspiciously specific or familiar, investigate its origin.
- Do not use AI to generate code that incorporates or derives from code with incompatible licenses.
- All dependencies must use Red Hat-approved licenses (reference the [Fedora Allowed Licenses](https://docs.fedoraproject.org/en-US/legal/allowed-licenses/) list). Dependency license vetting is a human review item.

## Upstream Contribution Policy

- Before contributing AI-generated code to an upstream or open-source project, check whether that project has a policy on AI-generated contributions
- If the upstream project **prohibits** AI-generated contributions, do not submit AI-generated code to that project
- If the upstream project's policy is **unclear**, disclose AI assistance in the contribution (e.g., in the commit message or PR description)
- When contributing to Red Hat-led upstream projects, follow the project-specific guidance — if none exists, default to disclosure

## Security Review of AI-Generated Code

- Treat AI-generated code with the **same or higher** scrutiny as human-written code
- Pay special attention to these areas in AI-generated code:
  - Input validation and sanitization
  - Authentication and authorization logic
  - Cryptographic operations and secrets handling
  - SQL/query construction (watch for injection vulnerabilities)
  - File system and network operations
  - Deserialization of untrusted data
- AI tools may generate code that looks correct but contains subtle security flaws — do not trust it implicitly
- Run the project's security scanning tools (SAST, dependency audit) on all AI-generated code before merge
