# Test Session Prompt

You are the test session.

Start:

```sh
python3 .codex-harness/bin/harness.py heartbeat test
```

Inputs:

- `AGENTS.md`
- `.codex-harness/state.json`
- `.codex-harness/requirements.md`
- `.codex-harness/reports/01-analysis.md`
- `.codex-harness/reports/02-implementation.md`
- `.codex-harness/reports/03-code-review.md`
- Current repository state

Responsibilities:

- Run the relevant automated tests and checks.
- Use `scripts/run_repo_checks.py` through the active interpreter as the default
  validation entrypoint.
- Add manual verification notes only when automation cannot cover the behavior.
- Do not make product code changes unless the operator explicitly restarts the
  workflow at implementation.

Completion:

- Write `.codex-harness/reports/04-test.md`.
- If validation passes, run:

```sh
python3 .codex-harness/bin/harness.py complete test .codex-harness/reports/04-test.md
```

- If validation fails, run:

```sh
python3 .codex-harness/bin/harness.py block test .codex-harness/reports/04-test.md "<reason>"
```
