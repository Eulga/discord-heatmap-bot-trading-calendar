# AGENTS.md

Agent instructions for the Discord bot repository.

## Read Order

1. `docs/IMPLEMENTATION.md`
2. `docs/operations/runtime-runbook.md`
3. `docs/operations/config-reference.md`
4. `README.md`

Old context logs, reports, to-be specs, and historical handoff documents are not current project truth.

## Working Rules

- Keep changes small and deliberate.
- Do not expose tokens, channel IDs beyond already-tracked operational examples, credentials, or private runtime data.
- Use `scripts/run_repo_checks.py` as the default verification entrypoint when code changes are made.
- Update `docs/IMPLEMENTATION.md` when a feature boundary or responsibility changes.
- Update `docs/operations/config-reference.md` when environment variables or defaults change.
- Update `docs/operations/runtime-runbook.md` when deployment, debugging, or operator steps change.
- If Korean text is touched, check for mojibake before finishing.
- Commit messages must be written in Korean when the user asks to commit.

## Repository Boundaries

- This bot sends Discord messages, manages Discord roles, handles dashboard login buttons, and runs Discord command handlers.
- It does not own market data. Market data belongs to `StockDataController`.
- It does not own web users, sessions, or reports. Those belong to `Stock-Dashboard`.
- Discord channel, thread, role, message, and guild IDs are delivery/auth metadata.

## Verification

Default:

```bash
python scripts/run_repo_checks.py
```

Use a narrower command only when the task is clearly limited and the narrower check covers the changed path.
