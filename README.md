# Discord Bot (Python)

## 1) Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
```

Set your bot token in `.env`.
Per-server forum posting uses `/setforumchannel` (optional fallback: `DEFAULT_FORUM_CHANNEL_ID` in `.env`).
If you want specific accounts to run admin commands in any server, set `DISCORD_GLOBAL_ADMIN_USER_IDS` (comma-separated user IDs).

## 2) Run

```powershell
python -m bot.main
```

Docker (background):

```powershell
docker compose up -d --build
```

Logs:

```powershell
docker compose logs -f discord-bot
```

Runtime logs are also written to `data/logs/bot.log` by default.
When you use Docker, `data/logs/` is mounted so log files survive container recreation.

Stop:

```powershell
docker compose down
```

## 3) Architecture

- `bot/app`: app bootstrap, settings, shared types
- `bot/common`: clock/fs/errors utilities
- `bot/forum`: state repository + forum upsert service
- `bot/markets`: cache + capture orchestration + market providers
- `bot/features`: slash command feature modules (`kheatmap`, `usheatmap`)

## 4) Quick test

In your Discord server, first confirm slash commands `/health`, `/kheatmap`, and `/usheatmap` are visible.
- `/health` should reply ephemerally with the latest job/provider status.
- Set each server's forum channel first with `/setforumchannel`.
- Toggle auto schedule per server with `/autoscreenshot mode:on|off`.
- The bot stores forum channel per server and posts to that server's configured channel.
- Per command, it keeps one daily post and edits the first message on repeated runs.
- Post titles:
  - `[YYYY-MM-DD 한국장 히트맵]` for `kheatmap`
  - `[YYYY-MM-DD 미국장 히트맵]` for `usheatmap`
- Heatmap images are saved locally and reused for up to 1 hour.
- When auto schedule is ON, it runs on KST:
  - `15:35` -> `kheatmap`
  - `06:05` -> `usheatmap`
- Auto schedule executes only on trading days:
  - `kheatmap` runs only when KRX (`XKRX`) is open.
  - `usheatmap` runs only when NYSE (`XNYS`) is open (based on New York local date).
  - If calendar check fails, it logs the reason and skips that run.

## 5) Discord permissions

In the target server/channel, ensure the bot can:
- Use Application Commands
- Send Messages
- Attach Files
- Create/Send messages in forum posts
- Manage Server permission for users who run `/setforumchannel`

## 6) Tests

Default (exclude live network tests):

```powershell
pytest
```

Live capture tests only:

```powershell
pytest -m live
```

Live tests call real websites, so they can be flaky due to network/site-side protections.

## 7) Git workflow (recommended)

```powershell
git add .
git commit -m "chore: bootstrap python discord bot"
```

`git init` is already done. `.gitignore` excludes venv/cache/.env.


## 8) MVP 확장 기능 (뉴스/장마감/watch)

신규 슬래시 명령어:
- `/watch add symbol:<종목코드>`
- `/watch remove symbol:<종목코드>`
- `/watch list`
- `/health`
- `/last-run`
- `/source-status`
- `/setnewsforum`
- `/seteodforum`
- `/setwatchchannel`

신규 스케줄:
- KST `07:30` 아침 뉴스 브리핑 (`NEWS_BRIEFING_TIME`)
- KST `16:20` 장마감 요약 (`EOD_SUMMARY_TIME`, KRX 거래일에만)
- watchlist 폴링 (`WATCH_POLL_INTERVAL_SECONDS`, 기본 60초)

### 환경변수
- `NEWS_BRIEFING_ENABLED=true|false`
- `NEWS_BRIEFING_TIME=07:30`
- `NEWS_BRIEFING_TRADING_DAYS_ONLY=true|false`
- `EOD_SUMMARY_ENABLED=true|false`
- `EOD_SUMMARY_TIME=16:20`
- `WATCH_POLL_ENABLED=true|false`
- `WATCH_POLL_INTERVAL_SECONDS=60`
- `WATCH_ALERT_THRESHOLD_PCT=3.0`
- `WATCH_ALERT_COOLDOWN_MINUTES=10`
- `LOG_FILE_PATH=data/logs/bot.log`
- `LOG_RETENTION_DAYS=7`
- `LOG_CONSOLE_ENABLED=true`
- `ADMIN_STATUS_CHANNEL_ID=<optional>`
- `NEWS_TARGET_FORUM_ID=<optional>`
- `EOD_TARGET_FORUM_ID=<optional>`
- `WATCH_ALERT_CHANNEL_ID=<optional>`

현재 MVP의 데이터 소스는 provider 교체 가능한 mock 구현입니다. 운영 전 실제 API provider로 교체하세요.
실사용 전환용 외부 API 계약은 `docs/specs/external-intel-api-spec.md`를 기준으로 맞춥니다.
