---
name: codex-harness
description: Use when initializing, continuing, inspecting, or operating this repo's staged Codex harness under .codex-harness, especially for long tasks that should move through analysis, implementation, code-review, test, and final-review sessions with file-based reports and state.
---

# Codex Harness

Use this skill when the user wants staged Codex work rather than a single
continuous session.

## When To Use

- A large change needs clean analysis, implementation, review, test, and final
  review passes.
- The user asks to initialize, continue, inspect, or operate `.codex-harness`.
- The current session needs to hand the next role a prompt and a report-based
  source of truth.

Do not use it for small single-session edits unless the user explicitly asks for
the harness.

## Workflow

1. Read `AGENTS.md`, `.codex-harness/README.md`, `.codex-harness/state.json`
   if present, and `.codex-harness/requirements.md` if present.
2. If runtime files do not exist, initialize them:
   - macOS/Linux: `python3 .codex-harness/bin/harness.py init --request "<request>"`
   - Windows: `py -3 .codex-harness/bin/harness.py init --request "<request>"`
3. Run `python3 .codex-harness/bin/harness.py next` or the Windows equivalent.
4. Print or use the matching role prompt from `.codex-harness/prompts/`.
5. Each role writes the expected report under `.codex-harness/reports/`.
6. Complete or block through `bin/harness.py`; do not hand-edit `state.json`.

## Role Boundaries

- `analysis`: inspect and produce an implementation brief; do not edit files.
- `implementation`: implement only approved analysis scope and update required
  docs/tests.
- `code-review`: defect-first review; do not edit files.
- `test`: run relevant checks through `scripts/run_repo_checks.py` by default.
- `final-review`: confirm acceptance criteria, review/test closure, and docs.

## Runtime Files

`requirements.md`, `state.json`, and role reports are intentionally ignored by
git. Tracked templates live beside them so new runs can start from a known
baseline without polluting the worktree.
