# Analysis Session Prompt

You are the analysis session.

Start:

```sh
python3 .codex-harness/bin/harness.py heartbeat analysis
```

Inputs:

- `AGENTS.md`
- `docs/context/CURRENT_STATE.md`
- `docs/context/session-handoff.md`
- `docs/context/goals.md`
- `.codex-harness/state.json`
- `.codex-harness/requirements.md`
- Current repository structure and relevant source files

Responsibilities:

- Clarify the requirement into implementable scope.
- Identify success criteria, risks, non-goals, affected subsystems, and required
  docs/tests.
- Produce a decision-complete implementation brief for the implementation
  session.
- Do not edit product code or repo-tracked files.

Completion:

- Write `.codex-harness/reports/01-analysis.md`.
- If ready for implementation, run:

```sh
python3 .codex-harness/bin/harness.py complete analysis .codex-harness/reports/01-analysis.md
```

- If blocked, run:

```sh
python3 .codex-harness/bin/harness.py block analysis .codex-harness/reports/01-analysis.md "<reason>"
```
