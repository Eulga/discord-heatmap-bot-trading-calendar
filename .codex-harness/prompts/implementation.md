# Implementation Session Prompt

You are the implementation session.

Start:

```sh
python3 .codex-harness/bin/harness.py heartbeat implementation
```

Inputs:

- `AGENTS.md`
- `.codex-harness/state.json`
- `.codex-harness/requirements.md`
- `.codex-harness/reports/01-analysis.md`
- Current repository state and relevant source files

Responsibilities:

- Implement only the approved analysis scope.
- Preserve unrelated user changes.
- Add or update focused tests when needed.
- Update the minimum required docs/logs under `docs/context/` or operations docs
  when behavior or operator truth changes.
- Record changed files, important decisions, and verification commands.

Completion:

- Write `.codex-harness/reports/02-implementation.md`.
- If ready for code review, run:

```sh
python3 .codex-harness/bin/harness.py complete implementation .codex-harness/reports/02-implementation.md
```

- If blocked, run:

```sh
python3 .codex-harness/bin/harness.py block implementation .codex-harness/reports/02-implementation.md "<reason>"
```
