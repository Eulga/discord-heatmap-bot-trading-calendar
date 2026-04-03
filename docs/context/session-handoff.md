# Session Handoff

- Active carry-forward as of 2026-03-27:
  - `ship-develop` skill은 이제 trailing bare branch argument를 target base branch로 해석한다. 예: `[$ship-develop](/Users/jaeik/Documents/discord-heatmap-bot-trading-calendar/.agents/skills/ship-develop/SKILL.md) master` -> current branch를 `master`로 ship -> script는 `--base master`로 실행한다. 인자가 없으면 기본값은 계속 `develop`이다.
  - local state의 guild `1470388757617446924`는 `forum_channel_id`만 있고 `news_forum_channel_id`가 없다. explicit-route-only 뉴스 정책 배포 후에도 이 길드에서 뉴스/트렌드 게시를 계속 원하면 `/setnewsforum` 또는 startup `NEWS_TARGET_FORUM_ID` bootstrap으로 `news_forum_channel_id`를 채워야 한다.
  - local state의 guild `332110589969039360`는 아직 `watch_alert_channel_id=460011902043553792`만 있고 `watch_forum_channel_id`가 없다. watch hard cut 배포 후 이 길드에서 watch forum flow를 계속 쓰려면 `/setwatchforum`으로 forum route를 명시적으로 다시 설정해야 한다.
- See `session-history.md` for completed handoff entries and older session context.
