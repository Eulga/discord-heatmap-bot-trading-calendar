# Codex Harness

This directory provides a repo-local, file-based harness for staged Codex work.
Use it for larger changes that should move through clean analysis,
implementation, review, test, and final-review sessions.

The harness is an agent operating tool. It is not bot runtime behavior, not a
current implementation spec, and not a replacement for the canonical docs in
`docs/context/`.

## Flow

The fixed workflow is:

1. `intake` -> analysis session
2. `analysis_ready` -> implementation session
3. `implementation_ready` -> code review session
4. `review_ready` -> test session
5. `test_ready` -> final review session
6. `done`

If a role cannot safely continue, it writes its report and marks the harness as
`blocked`.

## Files

- `requirements.template.md`: tracked template for the source request,
  acceptance criteria, constraints, and approved scope notes.
- `state.template.json`: tracked initial state template.
- `requirements.md`: ignored runtime copy created by `init`.
- `state.json`: ignored runtime state created by `init`.
- `reports/`: `README.md` is tracked; role reports are ignored runtime files.
- `prompts/`: copyable starting prompts for clean Codex sessions.
- `bin/harness.py`: state helper for initialization, status, heartbeat, prompt
  lookup, completion, and blocking.

## Operator Commands

Use the active interpreter for the current OS:

```sh
# macOS/Linux
python3 .codex-harness/bin/harness.py init --request "Implement the requested change"
python3 .codex-harness/bin/harness.py status
python3 .codex-harness/bin/harness.py next
python3 .codex-harness/bin/harness.py prompt analysis

# Windows
py -3 .codex-harness/bin/harness.py init --request "Implement the requested change"
py -3 .codex-harness/bin/harness.py status
```

At the start of a role session:

```sh
python3 .codex-harness/bin/harness.py heartbeat analysis
```

At successful completion:

```sh
python3 .codex-harness/bin/harness.py complete analysis .codex-harness/reports/01-analysis.md
```

When blocked:

```sh
python3 .codex-harness/bin/harness.py block analysis .codex-harness/reports/01-analysis.md "missing acceptance criteria"
```

## Role Contract

Every role must:

- Read `AGENTS.md`, `state.json`, `requirements.md`, its prompt, the previous
  report, and the current repository state.
- Treat `docs/context/CURRENT_STATE.md`, `session-handoff.md`, and `goals.md`
  as the starting context for repo truth.
- Avoid relying on chat history from previous sessions.
- Keep work inside its role boundary.
- Write a report using the common report format.
- Update `state.json` through `bin/harness.py`.
