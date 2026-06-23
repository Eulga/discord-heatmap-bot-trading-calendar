# 설정 기준

주요 환경변수만 정리한다.

| 변수 | 용도 |
| --- | --- |
| `DISCORD_TOKEN` | 봇 토큰 |
| `DATABASE_URL` | 봇 상태 DB |
| `STOCK_DASHBOARD_BASE_URL` | 사용자가 접속할 대시보드 URL |
| `STOCK_DASHBOARD_INTERNAL_BASE_URL` | 봇이 내부에서 호출할 대시보드 URL |
| `STOCK_DASHBOARD_INTERNAL_TOKEN` | 대시보드 내부 API 호출 토큰 |
| `DISCORD_LOGIN_CHANNEL_ID` | 로그인 버튼 채널 |
| `DISCORD_ROLE_ASSIGN_CHANNEL_ID` | 관심종목 역할 선택 채널 |
| `DISCORD_WATCH_ALERT_CHANNEL_ID` | 관심종목 알림 채널 |
| `DISCORD_NEWS_CHANNEL_ID` | 뉴스 채널 |
| `DISCORD_SCHEDULE_CHANNEL_ID` | 일정/어닝 알림 채널 |
| `DISCORD_MARKET_REPORT_CHANNEL_ID` | 시장 리포트 채널 |
| `DISCORD_WATCH_REPORT_CHANNEL_ID` | 관심종목 리포트 채널 |
| `STOCK_DASHBOARD_REPORT_POLL_INTERVAL_SECONDS` | 리포트 전송 후보 조회 주기 |

운영 URL은 `.env`에서만 관리한다.
디스코드 메시지에 잘못된 한글 도메인처럼 보이는 URL이 뜨면 `STOCK_DASHBOARD_BASE_URL` 값부터 확인한다.
