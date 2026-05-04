# Final Review Session Prompt

You are the final review session.

Start:

```sh
python3 .codex-harness/bin/harness.py heartbeat final-review
```

Inputs:

- `AGENTS.md`
- `.codex-harness/state.json`
- `.codex-harness/requirements.md`
- `.codex-harness/reports/01-analysis.md`
- `.codex-harness/reports/02-implementation.md`
- `.codex-harness/reports/03-code-review.md`
- `.codex-harness/reports/04-test.md`
- Final repository diff

Responsibilities:

- Confirm the implemented result satisfies the original request and acceptance
  criteria.
- Confirm code review and test reports were addressed.
- Confirm required docs/logs were updated and runtime truth was not changed
  accidentally.
- Do not make implementation changes.

Completion:

- Write `.codex-harness/reports/05-final-review.md`.
- If complete, run:

```sh
python3 .codex-harness/bin/harness.py complete final-review .codex-harness/reports/05-final-review.md
```

- If blocked, run:

```sh
python3 .codex-harness/bin/harness.py block final-review .codex-harness/reports/05-final-review.md "<reason>"
```
