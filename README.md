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
Use `.env` primarily for secrets and bootstrap defaults.
Per-server forum posting uses `/setforumchannel`.
Per-guild channel/forum routing lives in `data/state/state.json`.
`DEFAULT_FORUM_CHANNEL_ID` in `.env` is now bootstrap-only: on startup, if that forum channel is accessible, the bot copies it into the matching guild's `data/state/state.json` and runtime routing then reads state.
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
App state is stored separately at `data/state/state.json`.

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
Detailed non-live integration case mapping: `docs/specs/integration-test-cases.md`
Detailed live capture case mapping: `docs/specs/integration-live-test-cases.md`

## 7) Git workflow (recommended)

```powershell
git add .
git commit -m "chore: bootstrap python discord bot"
```

`git init` is already done. `.gitignore` excludes venv/cache/.env.

외부 벤더 문서, 스프레드시트, PDF 같은 참고 원문은 `docs/references/external/` 아래에 모아 둡니다.


## 8) MVP 확장 기능 (뉴스/장마감/watch)

신규 슬래시 명령어:
- `/watch add symbol:<종목명|종목코드|티커>`
- `/watch remove symbol:<종목명|종목코드|티커>`
- `/watch list`
- `/health`
- `/last-run`
- `/source-status`
- `/setnewsforum`
- `/seteodforum`
- `/setwatchchannel`

신규 스케줄:
- KST `07:30` 아침 뉴스 브리핑 (`NEWS_BRIEFING_TIME`)
- KST `16:20` 장마감 요약 (`EOD_SUMMARY_TIME`, 현재는 pause)
- watchlist 폴링 (`WATCH_POLL_INTERVAL_SECONDS`, 기본 60초)

### 환경변수
- `NEWS_BRIEFING_ENABLED=true|false`
- `NEWS_BRIEFING_TIME=07:30`
- `NEWS_BRIEFING_TRADING_DAYS_ONLY=true|false`
- `NEWS_PROVIDER_KIND=mock|naver|marketaux|hybrid`
- `MARKET_DATA_PROVIDER_KIND=mock|kis`
- `DART_API_KEY=<optional>`
- `KIS_APP_KEY=<optional>`
- `KIS_APP_SECRET=<optional>`
- `MARKETAUX_API_TOKEN=<optional>`
- `MASSIVE_API_KEY=<optional>`
- `TWELVEDATA_API_KEY=<optional>`
- `OPENFIGI_API_KEY=<optional>`
- `NAVER_NEWS_CLIENT_ID=<optional>`
- `NAVER_NEWS_CLIENT_SECRET=<optional>`
- `NAVER_NEWS_DOMESTIC_QUERY=국내 증시`
- `NAVER_NEWS_GLOBAL_QUERY=미국 증시`
- `NAVER_NEWS_DOMESTIC_QUERIES=국내 증시,코스피 지수,코스닥 지수,원달러 환율,한국은행 금리`
- `NAVER_NEWS_GLOBAL_QUERIES=미국 증시,나스닥,S&P 500,연준,FOMC`
- `NAVER_NEWS_DOMESTIC_STOCK_QUERIES=삼성전자,SK하이닉스,현대차,한화에어로스페이스,셀트리온`
- `NAVER_NEWS_GLOBAL_STOCK_QUERIES=엔비디아,애플,마이크로소프트,테슬라,마이크론`
- `MARKETAUX_NEWS_GLOBAL_QUERY=Nasdaq OR S&P 500 OR Federal Reserve OR FOMC OR Treasury yields`
- `MARKETAUX_NEWS_GLOBAL_QUERIES=...`
- `MARKETAUX_NEWS_COUNTRIES=us`
- `MARKETAUX_NEWS_LANGUAGE=en`
- `NAVER_NEWS_LIMIT_PER_REGION=20`
- `NAVER_NEWS_MAX_AGE_HOURS=24`
- `INTEL_API_TIMEOUT_SECONDS=5`
- `INTEL_API_RETRY_COUNT=1`
- `EOD_SUMMARY_ENABLED=false|true`
- `EOD_SUMMARY_TIME=16:20`
- `WATCH_POLL_ENABLED=true|false`
- `WATCH_POLL_INTERVAL_SECONDS=60`
- `WATCH_ALERT_THRESHOLD_PCT=3.0`
- `WATCH_ALERT_COOLDOWN_MINUTES=10`
- `INSTRUMENT_REGISTRY_REFRESH_ENABLED=false|true`
- `INSTRUMENT_REGISTRY_REFRESH_TIME=06:20`
- `LOG_FILE_PATH=data/logs/bot.log`
- `LOG_RETENTION_DAYS=7`
- `LOG_CONSOLE_ENABLED=true`
- `ADMIN_STATUS_CHANNEL_ID=<optional>`
- `NEWS_TARGET_FORUM_ID=<optional bootstrap forum channel id>`
- `EOD_TARGET_FORUM_ID=<optional bootstrap forum channel id>`
- `WATCH_ALERT_CHANNEL_ID=<optional bootstrap text channel id>`

현재 데이터 소스는 기능별로 단계가 다릅니다. `watch_poll`은 `MARKET_DATA_PROVIDER_KIND=kis`일 때 KIS live quote를 primary로 사용하고, 미국 종목은 `MASSIVE_API_KEY`가 있으면 Massive snapshot을 fallback으로 붙입니다.
실사용 전환용 외부 API 계약은 `docs/specs/external-intel-api-spec.md`를 기준으로 맞춥니다.
watch 종목 검색은 live 외부 search API가 아니라 local instrument registry를 기준으로 동작합니다.
bundled snapshot artifact는 `bot/intel/data/instrument_registry.json`이고, runtime refresh를 켜면 `data/state/instrument_registry.json`이 같은 프로세스에서 우선 사용됩니다.
raw 참고자료는 `docs/references/external/` 아래에 두고, bot 내부 daily refresh는 이 raw snapshot을 우선 사용하지 않고 live source를 직접 다시 가져옵니다.
registry 재생성이 필요하면 `.\.venv\Scripts\python.exe scripts/build_instrument_registry.py`를 사용합니다.
스크립트는 repo `.env`의 `DART_API_KEY`를 자동으로 읽고, OpenDART corpCode 기준 국내 상장사 master와 KRX 공식 ETF/ETN/ELW/PF finder 기준 국내 structured product master를 함께 반영합니다.
`INSTRUMENT_REGISTRY_REFRESH_ENABLED=true`를 켜면 bot scheduler가 매일 `INSTRUMENT_REGISTRY_REFRESH_TIME`에 full rebuild를 시도하고, 성공했을 때만 runtime override artifact를 교체합니다.
현재 refresh는 `added/removed` 요약까지만 남기며, inactive/delisted marker와 watchlist reconciliation report는 아직 구현되지 않았습니다.
`MASSIVE_API_KEY`는 Massive(구 Polygon.io)용 기본 env 이름이고, 코드에서는 legacy `POLYGON_API_KEY`도 fallback으로 읽습니다. Massive snapshot fallback은 plan entitlement가 없으면 `massive-entitlement-required`로 실패할 수 있습니다.
뉴스 브리핑은 `NEWS_PROVIDER_KIND=naver`와 네이버 Search API Client ID/Secret을 주면 실제 검색 결과 기반으로 동작할 수 있습니다.
`NEWS_PROVIDER_KIND=hybrid`는 국내는 Naver, 해외는 Marketaux를 사용합니다.
네이버 뉴스 브리핑은 단일 query보다 `NAVER_NEWS_*_QUERIES`의 다중 query + provider 내부 중요도 점수화가 더 안정적입니다.
현재 뉴스 선별은 `거시 헤드라인 query`와 `헤드라인급 종목 query`를 함께 사용하고, 개별 종목 기사는 실적/가이던스/규제/대형 계약 같은 고영향 이벤트가 있을 때만 통과시키는 방향을 권장합니다.
`/watch add`와 `/watch remove`는 autocomplete를 지원하고, 저장값은 `KRX:005930`, `NAS:AAPL` 같은 canonical symbol입니다.
채널 라우팅의 source of truth는 `data/state/state.json`입니다. `setforumchannel`, `setnewsforum`, `seteodforum`, `setwatchchannel`이 길드별 설정을 state에 저장하고, startup은 legacy env channel IDs를 matching guild state로 한 번만 bootstrap합니다.
운영 원칙은 `민감정보는 env`, `mutable channel/forum routing은 state`입니다.
runtime은 더 이상 `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`를 cross-guild fallback으로 직접 읽지 않습니다.
`/source-status`의 `instrument_registry` row는 현재 active source(`runtime|bundled`)와 loaded counts를 함께 보여주고, `/last-run`에는 `instrument_registry_refresh` job row가 추가됩니다.
`/source-status`는 `instrument_registry`, `kis_quote`, `naver_news`, `marketaux_news`, `massive_reference`, `twelvedata_reference`, `openfigi_mapping`의 configured/degraded/disabled 상태를 함께 보여줍니다.
bootstrap용 `WATCH_ALERT_CHANNEL_ID`는 forum channel이 아니라 일반 text/messageable channel이어야 합니다.
`eod_summary`는 2026-03-20 기준 잠정 중단 상태라 기본값이 `false`입니다.
현재 뉴스 스케줄 포스트는 같은 날 기준 `국내 경제 뉴스 브리핑`과 `해외 경제 뉴스 브리핑` 두 개의 daily thread로 분리해서 올립니다.
같은 뉴스 스케줄에서 `[YYYY-MM-DD 트렌드 테마 뉴스]` thread도 별도로 생성되며, 이 thread는 starter message + 국내/해외 content message 구조로 업데이트됩니다.
트렌드 테마는 curated taxonomy 기반으로 region별 3~5개를 목표로 선별하고, 한 지역이 3개 미만이면 해당 섹션은 `(유의미한 테마 부족)` placeholder로 처리합니다.
