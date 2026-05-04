# Reports

Each role writes exactly one primary completion report:

- `01-analysis.md`
- `02-implementation.md`
- `03-code-review.md`
- `04-test.md`
- `05-final-review.md`

Use this structure:

```md
# <Role> Report

## Status

complete | blocked

## Inputs Read

- AGENTS.md
- .codex-harness/state.json
- .codex-harness/requirements.md
- <previous report, if any>
- <other inspected files or commands>

## Work Performed

- <summary>

## Findings

- <findings, defects, decisions, or confirmations>

## Evidence

- <tests, commands, diffs, logs, or manual checks>

## Next Step

- <clear instruction for the next role or operator>
```
