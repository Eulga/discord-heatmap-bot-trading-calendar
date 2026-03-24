# Session Handoff

- Active carry-forward as of 2026-03-24:
  - local state의 guild `1470388757617446924`는 `forum_channel_id`만 있고 `news_forum_channel_id`가 없다. explicit-route-only 뉴스 정책 배포 후에도 이 길드에서 뉴스/트렌드 게시를 계속 원하면 `/setnewsforum` 또는 startup `NEWS_TARGET_FORUM_ID` bootstrap으로 `news_forum_channel_id`를 채워야 한다.
- See `session-history.md` for completed handoff entries and older session context.
