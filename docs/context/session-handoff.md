# Session Handoff

- Active carry-forward as of 2026-04-16:
  - Repo agent 운영 기본선이 올라갔다. 검증 엔트리포인트는 이제 `python scripts/run_repo_checks.py`로 표준화됐고, `.github/workflows/pr-checks.yml`이 `collect`, `unit`, `integration` non-live 검증을 PR/push에 실행한다.
  - repo-local Codex skill이 4개 추가됐다: `pr-review`, `ci-triage`, `docs-sync`, `scheduler-watch-review`. 구현보다 review/triage/docs 동작을 repo 규칙에 맞게 반복시키는 용도다.
  - 현재 로컬 셸에서는 `.venv`가 존재하지만 바로 실행 가능한 repo-local Python 경로가 확인되지 않았다. 문서/CI는 `python scripts/run_repo_checks.py` 기준으로 맞췄지만, 실제 개발 머신별 virtualenv activation 절차는 필요 시 다시 점검해야 한다.
- Active carry-forward as of 2026-04-03:
  - PR #19의 후속 Codex review finding 2건은 로컬에서 수정됐다. `/watch add`는 이제 registry에 없는 canonical/legacy fast-path symbol을 거절하고, news/EOD scheduler는 exact-minute-only가 아니라 same-day catch-up으로 한 번 실행된다. 관련 targeted regression은 `tests/unit/test_watch_command.py`와 `tests/integration/test_intel_scheduler_logic.py`에서 통과했다.
  - PR #19 Codex review의 `/watch stop` stale-thread P1은 로컬에서 수정됐다. 이제 update-only starter refresh가 `None`을 반환해도 symbol status는 `inactive`로 내려가고 runtime state도 정리된다. 관련 regression은 `tests/integration/test_watch_forum_flow.py`에 추가됐다.
  - `ship-develop` skill은 이제 trailing bare branch argument를 target base branch로 해석한다. 예: `[$ship-develop](/Users/jaeik/Documents/discord-heatmap-bot-trading-calendar/.agents/skills/ship-develop/SKILL.md) master` -> current branch를 `master`로 ship -> script는 `--base master`로 실행한다. 인자가 없으면 기본값은 계속 `develop`이다.
  - local state의 guild `1470388757617446924`는 `forum_channel_id`만 있고 `news_forum_channel_id`가 없다. explicit-route-only 뉴스 정책 배포 후에도 이 길드에서 뉴스/트렌드 게시를 계속 원하면 `/setnewsforum` 또는 startup `NEWS_TARGET_FORUM_ID` bootstrap으로 `news_forum_channel_id`를 채워야 한다.
  - local state의 guild `332110589969039360`는 아직 `watch_alert_channel_id=460011902043553792`만 있고 `watch_forum_channel_id`가 없다. watch hard cut 배포 후 이 길드에서 watch forum flow를 계속 쓰려면 `/setwatchforum`으로 forum route를 명시적으로 다시 설정해야 한다.
- See `session-history.md` for completed handoff entries and older session context.
