# Development Log

## 2026-05-07
- Context: 사용자가 고정 stock query 대신 KIS 거래량/거래대금 랭킹과 기존 watchlist를 합친 동적 뉴스 query universe로 전환하라고 요청했다.
- Change:
1. `NEWS_COLLECTION_CLOSE_ENABLED`, `NEWS_COLLECTION_CLOSE_TIME`, `NEWS_DYNAMIC_RANKING_ENABLED`, `NEWS_DYNAMIC_SYMBOL_LIMIT`, `NEWS_DYNAMIC_INCLUDE_OVERSEAS` 설정을 추가하고, `news_collection_close` job key를 도입했다.
2. Naver/Marketaux provider `fetch()`가 optional `NewsQueryUniverse`를 받아 macro query 뒤에 동적 stock query를 추가하도록 확장했다.
3. `KisNewsRankingClient`를 추가해 기존 KIS OAuth/request helper를 재사용하고 국내 거래량/해외 거래량/해외 거래대금 ranking row를 `NewsRankingInstrument`로 정규화한다. 국내 거래대금 ranking은 confirmed endpoint가 없어 unavailable로 처리한다.
4. Scheduler가 watchlist + optional KIS ranking으로 query universe를 만들고, KIS ranking 실패/credential 누락은 `kis_news_ranking` provider status와 job detail에만 남긴 뒤 뉴스 수집은 계속 진행하게 했다.
5. `NAVER_NEWS_*_STOCK_QUERIES` 기본값을 개별 종목 중심에서 broad sector fallback 중심으로 조정했고, status/docs/tests를 새 job/config 경계에 맞췄다.
- Verification:
1. `.venv/bin/python -m pytest tests/unit/test_news_query_universe.py tests/unit/test_news_provider.py tests/unit/test_market_provider.py tests/integration/test_intel_scheduler_logic.py -q`
2. `.venv/bin/python scripts/run_repo_checks.py unit`
3. `.venv/bin/python scripts/run_repo_checks.py integration`
4. `.venv/bin/python scripts/run_repo_checks.py collect`
5. `git diff --check`
- Status: done

## 2026-05-06
- Context: 사용자가 기존 뉴스 관련 기능을 전면 수정해 Discord 국내/해외 뉴스 브리핑과 트렌드 테마 송출을 제거하고, 뉴스 수집 후 PostgreSQL 저장까지만 다시 구현하자고 요청했다.
- Change:
1. `news_briefing`/`trend_briefing` 스케줄러 경로와 `/setnewsforum`, `NEWS_TARGET_FORUM_ID`, 뉴스/트렌드 Discord 렌더러를 제거했다.
2. 새 `news_collection` job과 `NEWS_COLLECTION_*` env를 추가했고, scheduler는 forum route 없이 provider fetch 후 DB 저장만 수행한다.
3. `CollectedNewsArticle` 모델과 provider raw payload 보존 경로를 추가하고, Naver/Marketaux provider를 기본 품질필터 중심 수집 경로로 단순화했다.
4. `bot_news_articles` PostgreSQL 테이블과 `(state_key, article_key)` upsert helper를 추가했다. legacy `news_forum_channel_id`와 `bot_news_dedup`은 inert 상태로 남겼고, legacy split-state 재마이그레이션이 수집 기사 테이블을 지우지 않도록 했다.
5. 관련 unit/integration 테스트와 canonical docs/config/runbook/current-state/design decision/handoff를 갱신했다.
- Verification:
1. `.venv/bin/python -m pytest tests/unit/test_news_provider.py tests/unit/test_state_atomic.py tests/unit/test_bot_client.py tests/integration/test_intel_scheduler_logic.py -q`
2. `.venv/bin/python scripts/run_repo_checks.py collect`
3. `.venv/bin/python scripts/run_repo_checks.py unit`
4. `.venv/bin/python scripts/run_repo_checks.py integration`
5. `git diff --check`
- Note:
1. `python3 scripts/run_repo_checks.py collect`는 현재 macOS 기본 `python3`에서 usable pytest interpreter를 찾지 못해 실패했고, repo `.venv` interpreter로 동일 표준 스크립트를 실행해 통과했다.
- Status: done

- Context: 사용자가 로컬 LLM 뉴스 요약 성능 참고 문서를 정밀 분석해 현재 저장소에 도입 가능한 범위를 추려 달라고 요청했다.
- Change:
1. `docs/reports/local-llm-news-summary-adoption-scope-2026-05-06.md`를 추가해 reference memo의 각 제안을 현재 뉴스 provider, scheduler, local model client 구조와 대조했다.
2. 1차 도입 범위를 article-body extraction이 아닌 기존 `NewsItem` metadata 기반 optional regional digest LLM overlay로 좁혔다.
3. `trafilatura`, 뉴스용 `Playwright`, Redis/Celery queue, API LLM hybrid, model tiering은 별도 설계가 필요한 후속 범위로 분리했다.
- Verification:
1. `git diff --check`
- Status: done

- Context: 사용자가 로컬 LLM 기반 경제뉴스 100건 요약 성능 병목 분석과 개선 우선순위 메모를 Markdown 참고 문서로 보관해 달라고 요청했다.
- Change:
1. `docs/references/external/local-llm-news-summary-performance-2026-05-06.md`를 추가해 사용자 제공 분석 메모를 reference-only 문서로 정리했다.
2. 외부 링크와 벤더별 주장, 성능 추정치는 이 작업에서 재검증하지 않았다는 상태 문구를 문서 상단에 추가했다.
3. `docs/references/external/README.md`에 새 참고 문서 항목을 추가했다.
4. `docs/references/external/*` ignore 정책은 유지하되 이번 Markdown 참고 문서만 추적되도록 `.gitignore` 예외를 추가했다.
- Verification:
1. `git diff --check`
- Status: done

- Context: 사용자가 watch `마감가 알림`을 regular `watch_poll` 루프에서 분리하고, due minute을 짧게 놓친 재시작/지연은 복구하되 장기 중단 backfill은 원치 않는다고 요청했다.
- Change:
1. `bot/features/intel_scheduler.py`에 `watch_close_krx`와 `watch_close_us` daily close-finalization job을 추가했다.
2. KRX close job은 KST `16:00:00 <= now < 16:30:00`, US close job은 KST `07:00:00 <= now < 07:30:00` 안에서만 같은 KST 날짜에 1회 실행된다.
3. `_run_watch_poll()`은 regular-session current-price/band updates와 post-due DB close-price catch-up만 담당하고, Discord `마감가 알림` 생성/edit은 close job으로 이동했다.
4. Existing `close_comment_ids_by_session`, `[watch-close:*]` marker, `last_finalized_session_date`, pending adjacent-session protection, and close-price DB persistence are reused.
5. Current-truth docs, the watch-poll functional spec, and runtime runbook now describe the separated close jobs and 30-minute grace windows.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/integration/test_watch_poll_forum_scheduler.py tests/integration/test_intel_scheduler_logic.py`
- Status: done

## 2026-05-05
- Context: 사용자가 로컬 LLM 서버는 dev bot 전용이 아니라 상시 외부 서비스로 별도 관리해야 하므로 서버 재시작 skill에서 제외해 달라고 요청했다.
- Change:
1. `server-restart-dev` skill에서 `llama-server` start/stop/adopt/health-check 절차를 제거했다.
2. `server-restart-dev` agent metadata를 dev bot restart 전용 설명으로 수정했다.
3. README, runtime runbook, config reference, as-is spec, current-state docs에서 로컬 모델 서버 lifecycle은 bot/server restart workflow 밖에서 관리한다는 경계를 반영했다.
- Verification:
1. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/server-restart-dev`
2. `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.agents/skills/server-restart-dev/agents/openai.yaml').read_text()); print('yaml ok')"`
3. `git diff --check`
- Status: done

## 2026-05-05
- Context: 사용자가 `/local ask`용 Mac host `llama-server`를 더 깔끔하게 관리하도록 dev start/stop 스크립트를 추가해 달라고 요청했다.
- Change:
1. `scripts/start_local_model_server.sh`를 추가해 기존 `8081`의 `llama-server`를 PID 파일로 채택하거나, 없으면 Gemma GGUF 모델로 새 서버를 시작하게 했다.
2. `scripts/stop_local_model_server.sh`를 추가해 `data/logs/local-model-server.pid` 또는 `8081`의 matching `llama-server` PID를 안전하게 종료하게 했다.
3. Local model PID/log 경로를 `data/logs/local-model-server.pid`와 `data/logs/local-model-server.log`로 고정했다.
4. `server-restart-dev` skill, README, runtime runbook, config reference, as-is spec, current-state docs에 새 script 기반 운영 절차를 반영했다.
5. Unit test에 shell syntax/executable 검증을 추가했다.
- Verification:
1. `bash -n scripts/start_local_model_server.sh scripts/stop_local_model_server.sh`
2. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_dev_env_scripts.py`
3. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/server-restart-dev`
4. `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.agents/skills/server-restart-dev/agents/openai.yaml').read_text()); print('yaml ok')"`
5. `scripts/start_local_model_server.sh` adopted existing `llama-server` on port `8081` and wrote `data/logs/local-model-server.pid`.
6. `docker compose exec -T discord-bot python -c "... urlopen('http://host.docker.internal:8081/v1/models') ..."` returned the `gemma-e4b` model list.
7. `git diff --check`
- Status: done

## 2026-05-05
- Context: 사용자가 Discord slash command로 Mac host의 로컬 `llama.cpp` 모델에 간단히 명령하는 기능을 구현해 달라고 요청했다.
- Change:
1. `LOCAL_MODEL_*` env 설정을 추가하고 기본 endpoint를 Docker 컨테이너 기준 `http://host.docker.internal:8081/v1`, 모델명을 `gemma-e4b`로 정했다.
2. `/local ask` slash command를 추가해 guild owner/admin 또는 `DISCORD_GLOBAL_ADMIN_USER_IDS` 사용자만 로컬 모델에 prompt를 보낼 수 있게 했다.
3. 로컬 모델 client는 신규 dependency 없이 `urllib.request`를 `asyncio.to_thread()`로 감싸 OpenAI-compatible `/chat/completions`를 호출한다.
4. Prompt/response 길이 제한, timeout/API/invalid-response 실패 처리, ephemeral 기본 응답, optional public 응답 gate를 추가했다.
5. `.env.example`, config reference, runtime runbook, as-is spec, current-state docs에 로컬 모델 설정과 운영 전제를 반영했다.
- Verification:
1. `PYTHONPYCACHEPREFIX=.tmp_pycache /opt/homebrew/bin/python3.11 -m py_compile bot/app/settings.py bot/app/bot_client.py bot/features/local_model/client.py bot/features/local_model/command.py tests/unit/test_local_model_client.py tests/integration/test_local_model_command.py`
2. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_local_model_client.py`
3. `python3 scripts/run_repo_checks.py integration -- tests/integration/test_local_model_command.py`
4. `python3 scripts/run_repo_checks.py unit`
5. `python3 scripts/run_repo_checks.py integration`
6. `python3 scripts/run_repo_checks.py collect`
7. `docker compose config --quiet`
8. `git diff --check`
- Status: done

## 2026-05-05
- Context: 사용자가 서버 재시작 skill을 운영과 개발 두 가지로 분리해 달라고 요청했다.
- Change:
1. 단일 `.agents/skills/server-restart/` skill을 제거하고 `.agents/skills/server-restart-dev/`와 `.agents/skills/server-restart-prod/`로 분리했다.
2. `server-restart-dev`는 현재 dev repo, `discord-heatmap-bot-dev`, Adminer, PostgreSQL `Asia/Seoul` timezone, sibling token/env 검사 금지 정책을 명시한다.
3. `server-restart-prod`는 운영 repo `/Users/jaeik/Documents/discord-heatmap-bot-trading-calendar`, expected production container `discord-heatmap-bot`, dirty worktree preflight, stricter restart/rollback checks를 명시한다.
4. README와 current-state skill summary를 새 skill 이름으로 갱신했다.
- Verification:
1. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/server-restart-dev`
2. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/server-restart-prod`
3. `python3 -c "import pathlib, yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path('.agents/skills').glob('server-restart-*/agents/openai.yaml')]; print('yaml ok')"`
4. `git diff --check`
- Status: done

## 2026-05-05
- Context: 사용자가 개발 DB 설정의 시간대를 한국 기준으로 변경해 달라고 요청했다.
- Change:
1. `docker-compose.yml`의 `postgres` 서비스에 `TZ=Asia/Seoul`, `PGTZ=Asia/Seoul`, server command `timezone=Asia/Seoul`을 추가했다.
2. 기존 개발 DB에는 `ALTER DATABASE discord_heatmap SET timezone TO 'Asia/Seoul'` 및 `ALTER ROLE discord_heatmap SET timezone TO 'Asia/Seoul'`로 새 세션 기본 timezone을 맞췄다.
3. `server-restart` skill과 operations docs에 `SHOW timezone` 검증 절차를 추가했다.
- Verification:
1. `docker compose config --quiet`
2. `docker compose up -d --force-recreate postgres`
3. `docker compose exec postgres pg_isready -U discord_heatmap -d discord_heatmap`
4. `docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SHOW timezone"` confirmed `Asia/Seoul`
- Status: done

## 2026-05-05
- Context: 사용자가 서버 재실행 관련 설정과 안전 절차를 자세히 담은 repo-local skill을 추가해 달라고 요청했다.
- Change:
1. `.agents/skills/server-restart/`를 추가해 Docker Compose/PostgreSQL/Adminer 기준 재실행 절차를 skill로 문서화했다.
2. Skill은 infra/checks-only, live bot restart, `.env` reload, code rebuild, process-only bounce를 구분한다.
3. `.env` secret 노출 금지, `docker compose config --quiet`, duplicate live bot avoidance, schema smoke, log verification, failure stop guidance를 포함했다.
4. README와 current-state agent workflow summary에 `server-restart` skill을 추가했다.
5. 현재 dev 경로의 live bot 컨테이너 이름을 `discord-heatmap-bot-dev`로 고정하고, skill은 sibling project token/container env 검사를 하지 않는 정책으로 맞췄다.
- Verification:
1. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/server-restart`
2. `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.agents/skills/server-restart/agents/openai.yaml').read_text()); print('yaml ok')"`
- Status: done

## 2026-05-05
- Context: 사용자가 watch poll 등록 종목의 마감가를 PostgreSQL에 누적 저장하는 정책으로 변경해 달라고 요청했다.
- Change:
1. `bot_watch_close_prices`를 추가해 `POSTGRES_STATE_KEY + symbol + session_date` 단위로 close price history를 누적 저장한다.
2. `bot_watch_close_price_attempts`를 추가해 post-due catch-up fetch를 15분 단위로 throttle한다.
3. Watch close finalization은 close price가 확정되면 Discord close comment side effect 전에 DB row를 upsert한다.
4. Active watch symbol은 market-specific KST due minute 이후 close price row가 없으면 Discord comment 없이 DB catch-up을 시도한다.
5. `session_close_price`가 없는 catch-up snapshot은 `close-unavailable` attempt로 기록하고 `watch_poll` job 자체는 실패 처리하지 않는다.
6. Tests now cover schema DDL, close-price upsert semantics, attempt throttling, Discord close-comment failure persistence, post-due catch-up, guild-level dedupe, and adjacent `previous_close` fallback source marking.
7. Current-truth docs now describe the accumulated history tables, Adminer/SQL inspection path, and the distinction from legacy `AppState` snapshots.
- Verification:
1. `PYTHONPYCACHEPREFIX=.tmp_pycache python3 -m py_compile bot/forum/state_store.py bot/features/intel_scheduler.py tests/state_store_adapter.py tests/unit/test_state_atomic.py tests/integration/test_watch_poll_forum_scheduler.py`
2. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_state_atomic.py`
3. `python3 scripts/run_repo_checks.py integration -- tests/integration/test_watch_poll_forum_scheduler.py`
4. `python3 scripts/run_repo_checks.py unit`
5. `python3 scripts/run_repo_checks.py integration`
6. `python3 scripts/run_repo_checks.py collect`
7. `docker compose config --quiet`
8. `git diff --check`
9. `docker compose run --rm -v "$PWD:/app" discord-bot python scripts/run_repo_checks.py collect`
10. `docker compose run --rm -v "$PWD:/app" discord-bot python -c "from bot.forum.state_store import ensure_schema_and_migrate; ensure_schema_and_migrate(); print('schema_ok')"`
11. PostgreSQL smoke confirmed `bot_watch_close_prices` and `bot_watch_close_price_attempts` exist; both had row count `0` before future live collection.
12. `docker compose ps` showed `postgres` healthy and `adminer` up, with no live `discord-bot` service running.
- Status: done

## 2026-05-05
- Context: 사용자가 PostgreSQL state를 도메인 row로 분해하고 runtime full-document write 경로를 제거해 달라고 요청했다.
- Change:
1. `bot/forum/state_store.py`를 추가해 `POSTGRES_STATE_KEY` namespace별 split schema, `split_state_v1` migration, legacy JSON import, and granular repository APIs를 구현했다.
2. Startup, command sync, admin/status commands, heatmap runner/cache/forum upsert, auto/news/EOD/watch schedulers, and watch commands now use split-state APIs instead of runtime `load_state()` / `save_state()`.
3. Legacy `bot_app_state.state JSONB` row is preserved as migration/rollback backup; runtime no longer syncs split rows back into that JSON row.
4. Watch delete and alert/session updates now go through compound/row-level repository operations instead of full document rewrites.
5. Tests gained a split-state mapper unit test and a test-only adapter so existing fake Discord integration flows validate behavior without reintroducing runtime full-document state writes.
6. Canonical docs now describe PostgreSQL-only runtime state, split tables, migration behavior, and the remaining distributed lease/outbox risk.
- Verification:
1. `python3 scripts/run_repo_checks.py unit`
2. `python3 scripts/run_repo_checks.py integration`
3. `python3 scripts/run_repo_checks.py collect`
4. `docker compose config --quiet`
5. `docker compose up -d postgres`
6. `docker compose exec postgres pg_isready -U discord_heatmap -d discord_heatmap`
7. `docker compose run --rm -v "$PWD:/app" discord-bot python -c "... ensure_schema_and_migrate(); load_state_snapshot() ..."` confirmed `state_load_ok True`, `guild_count 1`, `command_count 4`.
8. PostgreSQL smoke confirmed `split_state_v1` marker and all 15 `bot_*` tables; row counts included `bot_guild_config=1`, `bot_daily_posts=3`, `bot_watch_symbols=2`, `bot_watch_session_alerts=2`.
9. Existing live `discord-bot` container was stopped before final migration refresh; final `docker compose ps` showed `postgres` healthy and `adminer` up, with no live bot service running.
- Status: done

## 2026-05-05
- Context: 사용자가 PostgreSQL `bot_app_state.state JSONB` 한 row 저장 방식은 유지하면서 lost update를 막는 optimistic locking을 구현해 달라고 요청했다.
- Change:
1. PostgreSQL `bot_app_state` schema에 `version BIGINT NOT NULL DEFAULT 1`을 추가하고, 기존 DB는 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1`로 자동 보정하게 했다.
2. PostgreSQL `load_state()`는 `state, version`을 함께 읽고, version은 persisted `AppState` JSON key가 아니라 loaded state wrapper attribute로 추적한다.
3. PostgreSQL `save_state()`는 loaded state의 expected version으로 `UPDATE ... WHERE state_key = ... AND version = ...`를 수행하고, 성공 시 `version = version + 1`로 증가시킨다.
4. stale version update가 row를 갱신하지 못하면 `RuntimeError("PostgreSQL state backend concurrent update conflict.")`를 그대로 발생시켜 조용한 overwrite를 막는다.
5. File backend behavior는 변경하지 않았고, ad hoc untracked PostgreSQL save는 기존 public API 호환을 위해 현재 row version을 읽은 뒤 update한다.
6. Current-truth docs and design decisions now describe the versioned PostgreSQL state row and non-merge conflict policy.
- Verification:
1. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_state_atomic.py`
2. `python3 scripts/run_repo_checks.py collect`
3. `docker compose config --quiet`
4. `docker compose run --rm -v /Users/jaeik/Documents/discord-heatmap-bot-trading-calendar-dev:/app discord-bot python scripts/run_repo_checks.py collect`
5. `docker compose up -d --build discord-bot`
6. `docker compose exec -T postgres psql ... information_schema.columns ...` confirmed `bot_app_state.version` as non-null `bigint` with default `1`.
7. `docker compose exec -T postgres psql ... SELECT state_key, version, jsonb_typeof(state) ...` confirmed the `default` state row is JSON object with version `3`.
8. `docker compose run --rm discord-bot python -c "... load_state() ..."` confirmed `state_load_ok True`, `guild_count 1`, `command_count 6`.
9. `docker compose ps` confirmed `discord-bot` and `adminer` running and `postgres` healthy; bot logs showed Gateway connection, 11 global commands synced, scheduler start, and watch poll success.
10. `git diff --check`
- Status: done

## 2026-05-05
- Context: 사용자가 heatmap 자동스크린샷도 watch 마감 알림과 동일한 KST 기준 시간으로 변경해 달라고 요청했다.
- Change:
1. `kheatmap` 자동 실행 기준 시각을 KST `16:00`으로 변경했다.
2. `usheatmap` 자동 실행 기준 시각을 KST `07:00`으로 변경했다.
3. `/autoscreenshot on` 확인 문구와 autoscheduler regression 계약을 새 시간에 맞췄다.
4. Current-truth docs now describe the `16:00`/`07:00` heatmap auto-screenshot schedule and preserve the same-day catch-up behavior.
- Verification:
1. `python3 scripts/run_repo_checks.py integration tests/integration/test_auto_scheduler_logic.py`
2. `python3 scripts/run_repo_checks.py unit tests/unit/test_trading_calendar.py`
3. `docker compose up -d --build`
4. `docker compose ps`에서 `discord-bot`, `postgres`, `adminer` 실행 중이고 `postgres`는 healthy임을 확인했다.
5. `docker compose logs --tail=120 discord-bot`에서 Gateway 연결, 11개 global command sync, auto screenshot scheduler 시작, intel scheduler 시작을 확인했다.
- Status: done

## 2026-05-05
- Context: 사용자가 PostgreSQL 상태를 GUI로 확인할 수 있게 하고 dev Docker 서비스를 재실행해 달라고 요청했다.
- Change:
1. `docker-compose.yml`에 `adminer:4` 서비스를 추가했다.
2. Adminer는 `postgres` healthcheck 이후 시작하며, 호스트에는 `127.0.0.1:8080`으로만 노출된다.
3. `docker compose up -d --build`로 `discord-bot`, `postgres`, `adminer`를 재실행했다.
- Verification:
1. `docker compose config --quiet`
2. `docker compose ps`에서 `adminer`, `discord-bot`, `postgres`가 모두 실행 중이고 `postgres`는 healthy임을 확인했다.
3. `docker compose logs --tail=100 discord-bot`에서 Gateway 연결, 11개 global command sync, scheduler 시작, watch poll 성공 로그를 확인했다.
4. `docker compose logs --tail=40 adminer`에서 Adminer PHP development server가 `8080`으로 시작됐음을 확인했다.
- Status: done

## 2026-05-04
- Context: PR #24 Codex review found two follow-up issues in the new `$check-pr-review` clean-merge path.
- Change:
1. Clean PR merges now instruct agents to call `gh pr merge <number> --squash --delete-branch --match-head-commit <headRefOid>` so a last-second unreviewed push cannot be merged after the clean-state check.
2. Local branch cleanup now checks `git branch --list <feature-branch>` before `git branch -D`, and reports `already-gone` if GitHub CLI already deleted the local branch.
3. `.agents/skills/check-pr-review/agents/openai.yaml` was updated to match the pinned merge and idempotent cleanup workflow.
- Verification:
1. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/check-pr-review`
2. `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.agents/skills/check-pr-review/agents/openai.yaml').read_text()); print('yaml ok')"`
3. `git diff --check`
4. `.venv/bin/python scripts/run_repo_checks.py collect`
- Status: done

## 2026-05-04
- Context: 사용자가 `$check-pr-review`에서 PR review가 clean이면 merge 후 remote/local branch 삭제까지 수행하도록 요청했다.
- Change:
1. `.agents/skills/check-pr-review/SKILL.md`의 clean workflow를 squash merge, remote branch deletion, base branch checkout, local feature branch deletion까지 수행하도록 확장했다.
2. Clean merge 전에 local worktree, local HEAD와 PR head 일치, PR mergeability, required checks를 확인하고, 실패하면 `Clean - blocked`로 멈추도록 안전 조건을 추가했다.
3. GitHub가 formal review 대신 top-level Codex clean comment로 결과를 노출하는 경우도 current-head clean review loop로 인정하는 기준을 문서화했다.
4. `.agents/skills/check-pr-review/agents/openai.yaml`의 UI prompt를 새 merge/cleanup behavior에 맞게 갱신했다.
- Verification:
1. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/check-pr-review`
2. `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.agents/skills/check-pr-review/agents/openai.yaml').read_text()); print('yaml ok')"`
3. `git diff --check`
4. `.venv/bin/python scripts/run_repo_checks.py collect`
- Status: done

## 2026-05-04
- Context: 사용자가 repo-local Codex 설정의 모든 명시 모델을 최신 고성능 기본값으로 고정해 달라고 요청했다.
- Change:
1. `.codex/config.toml`의 기본 모델을 `gpt-5.5`, reasoning effort를 `xhigh`, plan-mode reasoning effort를 `xhigh`로 올렸다.
2. `.codex/config.toml`에 `service_tier = "fast"`를 추가해 repo 설정도 fast service tier를 명시하도록 했다.
3. `repo_explorer`, `reviewer`, `docs_researcher`, `integration_tester` custom agent 모델을 모두 `gpt-5.5`와 `xhigh` reasoning effort로 정렬했다.
- Verification:
1. `.venv/bin/python -c "import pathlib, tomllib; [tomllib.loads(path.read_text()) for path in [pathlib.Path('.codex/config.toml'), *pathlib.Path('.codex/agents').glob('*.toml')]]; print('toml ok')"`
2. `rg -n "model\\s*=|model_reasoning_effort\\s*=|plan_mode_reasoning_effort\\s*=|service_tier\\s*=" .codex .agents -g '*.*'`
3. `.venv/bin/python scripts/run_repo_checks.py collect`
4. `git diff --check`
- Status: done

## 2026-05-04
- Context: 사용자가 `$codex-harness`로 PostgreSQL 도입을 요청했고, 완료 기준은 기존 Discord 게시 이후 휘발되는 데이터를 저장하는 것이었다.
- Change:
1. `STATE_BACKEND=file|postgres`, `DATABASE_URL`, `POSTGRES_STATE_KEY` 설정을 추가했다.
2. `bot/forum/repository.py`의 `load_state()` / `save_state()` 표면은 유지하면서, `STATE_BACKEND=postgres`일 때 PostgreSQL `bot_app_state(state_key, state JSONB, updated_at)` row에 기존 `AppState` 문서를 저장하도록 했다.
3. PostgreSQL 첫 load에서 row가 없으면 현재 file state를 seed로 사용하고, PostgreSQL 선택 후 DB/query failure는 empty state fallback 없이 RuntimeError로 실패하게 했다.
4. `requirements.txt`에 `psycopg[binary]`를 추가하고, `docker-compose.yml`에 local `postgres:16-alpine` service와 named volume을 추가했다.
5. `.env.example`, `README.md`, `docs/operations/config-reference.md`, `docs/operations/runtime-runbook.md`, `docs/specs/as-is-functional-spec.md`, `docs/context/CURRENT_STATE.md`, `docs/context/session-handoff.md`, `docs/context/design-decisions.md`를 새 state backend boundary에 맞게 갱신했다.
6. `tests/unit/test_state_atomic.py`에 file default 보존, PostgreSQL URL requirement, seed/upsert/fail-closed behavior 테스트를 추가했다.
- Verification:
1. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_state_atomic.py`
2. `PYTHONPYCACHEPREFIX=/private/tmp/postgres-state-pycache python3 -m py_compile bot/forum/repository.py bot/app/settings.py tests/unit/test_state_atomic.py`
3. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_state_atomic.py tests/unit/test_watchlist_repository.py`
4. `python3 scripts/run_repo_checks.py unit`
5. `python3 scripts/run_repo_checks.py integration`
- Status: done

## 2026-05-04
- Context: 사용자가 `/Users/jaeik/.codex-harness`의 file-based staged Codex workflow를 현재 저장소의 agent 운영 체계에 녹여 달라고 요청했다.
- Change:
1. `.codex-harness/`를 추가해 tracked template/prompt/helper 기반의 analysis -> implementation -> code-review -> test -> final-review workflow를 repo-local로 편입했다.
2. `.codex-harness/bin/harness.py`에 `init` 명령을 추가해 ignored runtime `requirements.md`와 `state.json`을 템플릿에서 생성하도록 했다.
3. `.gitignore`에 run-specific harness state/report 파일을 추가하고, tracked template/README/prompt/helper는 보존했다.
4. repo-local skill `.agents/skills/codex-harness`를 추가해 긴 작업에서 staged harness를 명시적으로 호출할 수 있게 했다.
5. `tests/unit/test_codex_harness.py`를 추가해 init, overwrite protection, prompt/heartbeat/complete/block, outside-report rejection을 고정했다.
6. `README.md`, `AGENTS.md`, `docs/context/CURRENT_STATE.md`, `docs/context/session-handoff.md`, `docs/context/design-decisions.md`를 최소 갱신해 새 agent 운영 도구의 문서 경계를 반영했다.
- Verification:
1. `python3 /Users/jaeik/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/codex-harness`
2. `PYTHONPYCACHEPREFIX=/private/tmp/codex-harness-pycache python3 -m py_compile .codex-harness/bin/harness.py tests/unit/test_codex_harness.py`
3. `python3 scripts/run_repo_checks.py unit -- tests/unit/test_codex_harness.py`
4. `python3 scripts/run_repo_checks.py unit`
- Status: done

## 2026-05-04
- Context: PR #22 Codex follow-up review found that `pending_close_sessions` entries could remain forever after they aged beyond the adjacent-session `previous_close` fallback window.
- Change:
1. `watch_poll` now drops a pending old close target on a KST due-minute poll when the current snapshot session is no longer the immediately adjacent trading session for that target.
2. Dropping a stale pending target removes only the retry state; it does not create a close comment or delete old intraday comments.
3. The watch poll job detail now reports `dropped_pending_close_sessions` so this cleanup is visible without treating it as a failure.
4. Pending close cleanup is handled in a dedicated helper that returns finalized and dropped counts separately.
5. The watch poll regression now covers stale pending close cleanup instead of keeping an unresolvable pending target open forever.
6. Current-truth docs were updated to describe the stale pending cleanup boundary.
- Verification:
1. `python3 scripts/run_repo_checks.py integration tests/integration/test_watch_poll_forum_scheduler.py`
2. `python3 scripts/run_repo_checks.py unit tests/unit/test_watch_cooldown.py`
3. `python3 scripts/run_repo_checks.py integration`
4. `python3 scripts/run_repo_checks.py unit`
5. `python3 scripts/run_repo_checks.py collect`
- Status: done

## 2026-05-04
- Context: PR #22 Codex review found that the KST due-minute gate also suppressed regular-session polling after a missed close due minute.
- Change:
1. `watch_poll` now preserves missed prior-session close targets under `pending_close_sessions` while still rotating to the new regular session and continuing current-price comments plus band alerts.
2. Due-minute finalization now processes pending old close targets before the current active session close target when the same snapshot can close both.
3. Regression coverage now proves a missed KRX close due minute does not stop the next regular-session update, and that the next KST `16:00` tick clears both the pending old close and current close.
4. Watch current-truth docs were updated to describe pending close targets instead of blocking regular-session rotation.
- Verification:
1. `python3 scripts/run_repo_checks.py integration tests/integration/test_watch_poll_forum_scheduler.py`
2. `python3 scripts/run_repo_checks.py unit tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py`
- Status: done

## 2026-05-04
- Context: 사용자가 watch `마감가 알림`을 시장별 한국시간 고정 정각에만 생성하도록 변경해 달라고 요청했다. 합의된 동작은 KRX KST `16:00`, NAS/NYS/AMS KST `07:00`, env/state 설정 없음, missed due minute catch-up 없음이다.
- Change:
1. `bot/features/intel_scheduler.py`에 market prefix별 KST close-finalization due helper를 추가했다.
2. `watch_poll`은 off-hours unfinalized symbol을 due minute이 아니면 warm-up, snapshot fetch, close comment 생성 경로에서 제외한다.
3. 다음 regular session open에서 prior session이 아직 unfinalized이면 due minute 전에는 close finalization만 보류한다.
4. KRX/US exact-minute helper unit tests와 KRX/US close-finalization due gate integration regressions를 추가했고, 기존 close-price-missing / inactive-finalization / prior-session carry-forward expectations를 새 정책에 맞게 조정했다.
5. Current-truth docs and integration inventory now describe KST `16:00`/`07:00` exact-minute finalization and the no catch-up consequence.
- Verification:
1. `python3 scripts/run_repo_checks.py unit tests/unit/test_watch_cooldown.py`
2. `python3 scripts/run_repo_checks.py integration tests/integration/test_watch_poll_forum_scheduler.py`
3. `python3 scripts/run_repo_checks.py collect`
4. `python3 scripts/run_repo_checks.py unit`
5. `python3 scripts/run_repo_checks.py integration`
- Status: done

## 2026-04-24
- Context: PR #21 follow-up Codex review reported that current-price comment recreation could abort when deleting the old current-price comment hit `Forbidden` or `HTTPException`.
- Change:
1. `bot/features/intel_scheduler.py` now treats old current-price comment delete failures during force-recreate as best-effort cleanup failures, logs them, clears the stale current comment ID, and still attempts to send the replacement current-price comment after the band comment.
2. `tests/integration/test_watch_poll_forum_scheduler.py` adds a regression proving a band poll still creates the replacement current-price comment and advances the successful band checkpoint when old current-comment delete fails.
3. Watch docs now state that current-price recreate cleanup failures do not block replacement current-price comment sends.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_watch_poll_forum_scheduler.py -k "recreates_current_comment_when_old_current_delete_fails"`
2. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py`
- Status: done

## 2026-04-24
- Context: PR #21 follow-up Codex review reported that close finalization could still abort when current-price comment cleanup hit `Forbidden` or `HTTPException`.
- Change:
1. `bot/features/intel_scheduler.py` now treats close-finalization current-price comment cleanup as best-effort for `Forbidden`/`HTTPException`, logs the cleanup failure, clears the stored current comment ID, and continues close finalization.
2. `tests/integration/test_watch_poll_forum_scheduler.py` adds a regression proving close comment creation and `last_finalized_session_date` persistence still happen when current-comment delete fails.
3. Watch docs now state that finalization current-price comment cleanup is best-effort.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py`
- Status: done

## 2026-04-24
- Context: PR #21 Codex review reported that current-price comments had become coupled to band comment success, and `/watch stop` could fail when best-effort current-comment cleanup hit Discord errors.
- Change:
1. `bot/features/intel_scheduler.py` now keeps band comment send and current-price comment upsert in separate failure boundaries.
2. Failed band comment sends increment `comment_failures` but do not advance band checkpoints and do not block current-price updates.
3. `/watch stop` now treats current-price comment cleanup `Forbidden`/`HTTPException` as best-effort failures, logs them, clears the stored current comment ID, and still persists inactive status.
4. Regression tests cover both PR review findings.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py`
- Status: done

## 2026-04-24
- Context: 사용자가 `watch_poll`의 현재가 표시를 포럼 게시글 본문 수정에서 thread 하단 comment 수정 방식으로 옮기고, starter 본문은 이번 범위에서 비워두길 요청했다.
- Change:
1. `watch_poll`은 이제 regular session poll에서 starter를 blank 상태로 유지하고 `current_comment_id`로 추적되는 현재가 comment를 생성/수정한다.
2. 같은 poll에서 band comment가 새로 생성되면 기존 현재가 comment를 삭제 후 다시 보내, thread 하단에 최신 현재가 정보가 남도록 했다.
3. close finalization과 `/watch stop`은 stale 현재가 comment를 삭제하고 `current_comment_id`를 정리하며, close comment 누적 기록은 기존 세션별 방식으로 유지한다.
4. 관련 state type/repository helper, command/thread upsert 경로, scheduler job detail(`updated_current_comments`)과 watch 기능 문서를 함께 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py`
- Status: done

## 2026-05-03
- Context: PR #20 follow-up review found remaining validation wrapper issues: current Python with only global `pytest` could bypass the repo `.venv`, fallback `.venv` and bootstrap-reused `.venv` Python versions were not checked, explicit pytest targets still ran the full unit/integration suite, and path-valued, unknown, or alias pytest options could be mistaken for explicit target parsing.
- Change:
1. `scripts/run_repo_checks.py` now treats an interpreter as usable only when it satisfies the repo Python `3.10+` boundary and can import the required test/runtime modules: `pytest`, `pytest_asyncio`, `discord`, and `dotenv`.
2. Interpreter resolution now tries a usable repo `.venv` before accepting the current interpreter, and stale same-OS `.venv` Python versions return explicit rebuild guidance.
3. `build_pytest_args(...)` now omits default `tests/unit` or `tests/integration` paths when the caller supplies an explicit pytest target, including after a `--` separator.
4. Explicit-target detection now skips values for known value-taking pytest options and unknown options, while still recognizing targets after known no-value flags and after a `--` separator.
5. `tests/unit/test_dev_env_scripts.py` adds regressions for global-pytest current Python, old fallback `.venv`, explicit target argument construction, path-valued pytest options, and unknown value-taking options.
6. `scripts/bootstrap_dev_env.py` now rejects an existing same-OS `.venv` when its interpreter is below Python `3.10+`, before installing dependencies into that stale environment.
7. `tests/unit/test_dev_env_scripts.py` adds a bootstrap regression for an old existing `.venv` to ensure rebuild guidance is emitted and install commands are not run.
8. Pytest no-value aliases and flags such as `--lf`, `--ff`, `--nf`, `--sw`, `--pyargs`, `--collect-in-virtualenv`, and `--stepwise-reset` are now recognized before target detection decides whether to inject default suite paths.
- Verification:
1. `python3 scripts/run_repo_checks.py unit tests/unit/test_dev_env_scripts.py`
2. `python3 scripts/run_repo_checks.py unit --lf tests/unit/test_dev_env_scripts.py`
3. `python3 scripts/run_repo_checks.py unit --collect-in-virtualenv tests/unit/test_dev_env_scripts.py`
4. `python3 -c "import ast, pathlib; paths=['scripts/bootstrap_dev_env.py','scripts/run_repo_checks.py','tests/unit/test_dev_env_scripts.py']; [ast.parse(pathlib.Path(p).read_text()) for p in paths]; print('syntax ok')"`
5. `python3 scripts/run_repo_checks.py unit --junitxml reports/unit.xml tests/unit/test_dev_env_scripts.py`
6. `python3 scripts/run_repo_checks.py integration --ignore tests/integration/test_intel_scheduler_logic.py`
7. `python3 scripts/run_repo_checks.py integration --confcutdir tests`
8. `python3 scripts/run_repo_checks.py integration tests/integration/test_intel_scheduler_logic.py`
9. `python3 scripts/run_repo_checks.py unit`
10. `python3 scripts/run_repo_checks.py collect`
11. `python3 scripts/run_repo_checks.py integration`
12. `git diff --check`
- Status: done

## 2026-05-03
- Context: PR #20 review found that `scripts/run_repo_checks.py` could still select an unsupported current Python when that interpreter happened to have `pytest`, and that `docs/specs/integration-test-cases.md` had stale integration inventory counts.
- Change:
1. `choose_pytest_interpreter(...)` now rejects the current interpreter when it is below the repository's Python `3.10+` boundary before checking whether it can import `pytest`, allowing the repo `.venv` fallback or bootstrap guidance to remain authoritative.
2. `tests/unit/test_dev_env_scripts.py` adds a regression for an old current Python with `pytest` installed.
3. `docs/specs/integration-test-cases.md` now matches the collected non-live integration inventory: 90 total cases, including 40 Intel scheduler and 19 Watch forum flow cases.
- Verification:
1. `python3 scripts/run_repo_checks.py unit tests/unit/test_dev_env_scripts.py`
2. `python3 scripts/run_repo_checks.py collect`
3. `python3 -c "import ast, pathlib; paths=['scripts/run_repo_checks.py','tests/unit/test_dev_env_scripts.py']; [ast.parse(pathlib.Path(p).read_text()) for p in paths]; print('syntax ok')"`
4. `python3 scripts/run_repo_checks.py unit`
5. `python3 scripts/run_repo_checks.py integration`
6. `git diff --check`
- Status: done

## 2026-04-16
- Context: PR #20의 첫 GitHub Actions run이 collect/unit/integration 전부에서 실패했다. 원인은 workflow가 `bot.app.settings` import에 필요한 `DISCORD_BOT_TOKEN`을 주지 않아 test collection 자체가 막힌 것이었다.
- Change:
1. `.github/workflows/pr-checks.yml`에 workflow-level placeholder `DISCORD_BOT_TOKEN=ci-placeholder-token`을 추가해 non-live pytest collect/unit/integration job이 import-time settings guard 때문에 중단되지 않도록 했다.
2. `docs/operations/runtime-runbook.md`, `docs/context/CURRENT_STATE.md`, `docs/context/session-handoff.md`를 업데이트해 PR CI가 placeholder token으로 import-time validation만 우회한다는 경계를 현재 문서에 반영했다.
- Verification:
1. `gh run view 24511040944 --log-failed`
2. `DISCORD_BOT_TOKEN=ci-placeholder-token python3 scripts/run_repo_checks.py collect`
3. `DISCORD_BOT_TOKEN=ci-placeholder-token python3 scripts/run_repo_checks.py unit`
4. `DISCORD_BOT_TOKEN=ci-placeholder-token python3 scripts/run_repo_checks.py integration`
- Status: done

## 2026-04-16
- Context: 이전 agent baseline 변경 후에도 `.venv`가 Windows 전용 artifact로 남아 있었고, current-truth 문서 일부가 여전히 raw `.venv\Scripts\python.exe` 또는 `python ...` 경로를 섞어 써서 macOS/Linux local validation이 실제로 복원되지 않았다.
- Change:
1. `scripts/bootstrap_dev_env.py`, `scripts/dev_env_utils.py`, `scripts/__init__.py`를 추가해 repo-local `.venv` bootstrap/recreate 흐름과 OS별 interpreter detection helper를 도입했다.
2. `scripts/run_repo_checks.py`는 이제 current interpreter에 `pytest`가 없으면 current-OS repo `.venv` interpreter를 fallback으로 찾고, `.venv`가 cross-platform mismatch거나 missing이면 `bootstrap_dev_env.py` 안내를 출력하도록 바꿨다.
3. `tests/unit/test_dev_env_scripts.py`를 추가해 `.venv` cross-platform 판별과 pytest interpreter 선택 분기를 고정했다.
4. `README.md`, `AGENTS.md`, `docs/operations/runtime-runbook.md`, `docs/specs/integration-test-cases.md`, `docs/specs/integration-live-test-cases.md`, `.agents/skills/ship-develop/SKILL.md`, `.agents/skills/ci-triage/SKILL.md`, `.agents/skills/scheduler-watch-review/SKILL.md`를 업데이트해 bootstrap/validation 경로를 OS별 active interpreter 기준으로 정렬했다.
5. `docs/context/CURRENT_STATE.md`, `docs/context/session-handoff.md`, `docs/context/design-decisions.md`를 갱신해 새 cross-platform validation baseline을 current context에 반영했다.
- Verification:
1. `python3 -m py_compile scripts/__init__.py scripts/dev_env_utils.py scripts/bootstrap_dev_env.py scripts/run_repo_checks.py tests/unit/test_dev_env_scripts.py`
2. `python3 scripts/bootstrap_dev_env.py --recreate`가 Python `3.10+` requirement와 Docker fallback을 명시적으로 안내하는지 확인
3. `python3 scripts/run_repo_checks.py collect`가 unsupported local Python일 때 bootstrap/Docker fallback 메시지를 반환하는지 확인
4. `docker compose run --rm --build -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py collect`
5. `docker compose run --rm -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py unit`
6. `docker compose run --rm -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py integration`
- Follow-up:
1. `/opt/homebrew/bin/python3.11 scripts/bootstrap_dev_env.py --recreate --with-playwright`
2. `python3 scripts/run_repo_checks.py collect`
3. `python3 scripts/run_repo_checks.py unit`
4. `python3 scripts/run_repo_checks.py integration`
- Note:
1. 실제 macOS host의 `python3`는 여전히 `3.9.6`이지만, Homebrew `python3.11` 설치 후 `.venv`를 `3.11.15`로 재생성했고, `run_repo_checks.py`는 이 `.venv`를 fallback interpreter로 사용해 로컬 collect/unit/integration을 통과했다.
- Status: done

## 2026-04-16
- Context: 사용자가 현재 저장소에 Codex 기반 "AI 에이전트 운영체계" 요소를 실제로 반영해 달라고 요청했다.
- Change:
1. `scripts/run_repo_checks.py`를 추가해 local/CI 공통 pytest 엔트리포인트를 `collect`, `unit`, `integration`, `full` 기준으로 표준화했다.
2. `.github/workflows/pr-checks.yml`을 추가해 PR/push에서 non-live test collection, unit, integration 검증을 실행하도록 했다.
3. `.github/pull_request_template.md`를 추가해 요약, 검증, 문서 반영, 리스크, 롤백 메모를 PR 기본 구조로 고정했다.
4. repo-local Codex skill `pr-review`, `ci-triage`, `docs-sync`, `scheduler-watch-review`를 추가해 반복 review/triage/docs 업무를 저장소 규칙에 맞게 재사용할 수 있게 했다.
5. `README.md`, `AGENTS.md`, `docs/operations/runtime-runbook.md`, `docs/context/CURRENT_STATE.md`, `docs/context/session-handoff.md`, `docs/context/design-decisions.md`를 업데이트해 새 검증 명령과 agent operating baseline을 current-truth 문서에 반영했다.
- Verification:
1. `python3 scripts/run_repo_checks.py collect` 호출 시 새 엔트리포인트가 예상 명령을 구성하는 것까지 확인했고, 현재 sandbox Python에 `pytest`가 없어 collect 단계는 `No module named pytest`로 중단됐다
2. `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/run_repo_checks.py').read_text())"`로 새 스크립트 구문을 확인했다
3. static review로 `.github/workflows/pr-checks.yml`, PR template, skill metadata가 새 검증 명령과 일관되는지 확인했다
4. 이 환경에서는 repo-local virtualenv Python 경로가 바로 확인되지 않아 full/unit/integration 실행까지는 검증하지 못했다
- Status: done

## 2026-04-03
- Context: PR #19 Codex review reported two new P1 items: `/watch add` accepted nonexistent canonical symbols, and news/EOD daily schedulers still missed runs after late start.
- Change:
1. `bot/features/watch/command.py` now loads the instrument registry inside `resolve_watch_add_symbol(...)` and refuses canonical or legacy fast-path symbols unless the registry actually contains them.
2. This closes the `NAS:ZZZZZZ` class of false-success `/watch add` input before it can reach persisted watch state and noisy `watch_poll` failures.
3. `bot/features/intel_scheduler.py` now uses `_should_run_daily_job(...)` for daily news and EOD jobs, so they trigger once per day when `now >= scheduled time` instead of only on exact-minute equality.
4. `tests/unit/test_watch_command.py` adds a regression for unknown canonical symbols, and `tests/integration/test_intel_scheduler_logic.py` adds helper coverage for late-start catch-up plus a scheduler-loop regression that keeps instrument registry refresh at one same-day success run.
- Verification:
1. `docker run --rm -v "$PWD:/work" -w /work discord-heatmap-bot-trading-calendar-discord-bot python -m pytest tests/unit/test_watch_command.py tests/integration/test_intel_scheduler_logic.py -q -x --tb=line -p no:cacheprovider`
2. `docker run --rm -v "$PWD:/work" -w /work discord-heatmap-bot-trading-calendar-discord-bot python -m pytest tests/integration/test_watch_forum_flow.py -q -x --tb=line -p no:cacheprovider`
- Status: done

## 2026-04-03
- Context: PR #19 Codex review가 `/watch stop` stale-thread 경로에서 symbol이 계속 active로 남는 P1을 지적했고, 사용자가 수정 후 서브에이전트 전체 리뷰까지 요청했다.
- Change:
1. `bot/features/watch/command.py`에서 `/watch stop`의 `upsert_watch_thread(..., allow_create=False)` 결과가 `None`일 때 더 이상 조기 실패하지 않도록 바꿨다.
2. 같은 경로는 stale thread를 `degraded` 상태로 기록만 하고, 이후 `set_watch_symbol_thread_status(..., "inactive")`, `clear_watch_symbol_runtime_state(...)`, `save_state(...)`까지 계속 진행하게 수정했다.
3. stale thread로 starter placeholder를 갱신하지 못한 경우에는 성공 응답에 그 사실만 덧붙이고, polling 중단 자체는 성공으로 처리하게 바꿨다.
4. `tests/integration/test_watch_forum_flow.py`에 stale tracked thread handle에서도 symbol status가 `inactive`로 내려가고 runtime cooldown이 정리되는 회귀 테스트를 추가했다.
5. 변경 후 서브에이전트 리뷰를 병행해 현재 local diff 대 `origin/master` 기준 추가 actionable issue가 없는지 재점검했다.
- Verification:
1. `docker run --rm -v "$PWD:/work" -w /work discord-heatmap-bot-trading-calendar-discord-bot python -m pytest tests/integration/test_watch_forum_flow.py -q -x --tb=line -p no:cacheprovider`
2. `docker run --rm -v "$PWD:/work" -w /work discord-heatmap-bot-trading-calendar-discord-bot python -m pytest tests/integration/test_watch_poll_forum_scheduler.py tests/unit/test_watch_command.py -q -x --tb=line -p no:cacheprovider`
3. explorer subagent review 결과: current local diff versus `origin/master`에서 추가 actionable issue 없음
- Status: done

## 2026-04-03
- Context: 사용자가 `ship-develop` 스킬 호출 뒤에 bare branch 인자를 붙이면 target base branch로 해석되게 해 달라고 요청했다.
- Change:
1. `.agents/skills/ship-develop/SKILL.md`에 invocation argument 규칙을 추가해, 기본 base는 `develop`이고 `[$ship-develop](...) master` 같은 호출은 `--base master`로 해석하도록 명시했다.
2. 같은 문서의 Quick Start, preferred command, repo note, done 조건을 chosen base branch 기준으로 일반화했다.
3. `.agents/skills/ship-develop/agents/openai.yaml`의 display name과 default prompt도 trailing branch argument를 base override로 읽는 규칙에 맞게 갱신했다.
- Verification:
1. diff review로 `SKILL.md`와 `agents/openai.yaml`이 모두 `default=develop`, `trailing branch argument overrides base`, `$ship-develop master -> --base master` 규칙을 일관되게 설명하는지 확인했다.
2. 이번 변경은 skill instruction/documentation update라 별도 테스트는 실행하지 않았다.
- Status: done

## 2026-03-30
- Context: 사용자가 `external-intel-provider-rollout` 스킬을 유지하되 신규 기능 설계 도구가 아니라, 이미 합의된 provider rollout을 실행할 때 쓰는 체크리스트로 축소 정렬해 달라고 요청했다.
- Change:
1. `.agents/skills/external-intel-provider-rollout/SKILL.md`를 재작성해 이 스킬이 planning 도구가 아니라 execution checklist라는 전제를 명시했다.
2. 같은 문서에서 뉴스 scope를 `news_briefing + trend_briefing`으로 바로잡고, watch rollout 기준을 현재 runtime의 `WatchSnapshot`, `get_watch_snapshot(...)`, optional `warm_watch_snapshots(...)`, `session_date`, `session_close_price` 계약에 맞게 갱신했다.
3. 문서 업데이트 지침에 `docs/operations/config-reference.md`와 `docs/operations/runtime-runbook.md`를 포함시키고, EOD는 runtime wiring이 아직 `MockEodSummaryProvider()` 기반이라는 점을 repo-specific note로 보강했다.
4. `.agents/skills/external-intel-provider-rollout/agents/openai.yaml`의 표시명과 기본 프롬프트를 plan-first, execution-second 의미로 축소 조정했다.
- Verification:
1. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/external-intel-provider-rollout`
2. diff review로 스킬 본문이 `NewsAnalysis`, `trend_briefing`, `WatchSnapshot`, `get_watch_snapshot(...)`, `warm_watch_snapshots(...)`, canonical ops docs, current mock EOD wiring을 모두 반영하는지 확인했다.
- Status: done

## 2026-03-30
- Context: 사용자가 `ship-develop` 스킬이 PR 생성 후 Codex 리뷰 완료를 기다리지 말고, 리뷰 요청만 던진 뒤 바로 멈추는 기본 흐름으로 바꾸길 요청했다.
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에서 `--codex-review`와 함께 `--wait-codex-seconds`가 없거나 `0`이면 `@codex review`를 올린 직후 `done=pending reason=codex-review-requested`로 종료하도록 바꿨다.
2. `.agents/skills/ship-develop/SKILL.md`의 Quick Start, preferred command, outcome 해석, iterative workflow를 새 two-pass 기본 흐름에 맞게 갱신했다.
3. `.agents/skills/ship-develop/agents/openai.yaml`의 설명 문구를 초기 pass는 Codex review를 요청만 하고 기다리지 않는다는 방향으로 조정했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py`
2. inline mock 검증으로 `--codex-review` + `--wait-codex-seconds 0` 경로가 `codex-review-requested`로 즉시 종료되고 review polling helper를 호출하지 않는 것을 확인했다.
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`
- Status: done

## 2026-03-27
- Context: PR #17 Codex 리뷰에서 legacy `/watch remove`가 남긴 inactive metadata를 `/watch add`로 다시 등록할 때 same-session band checkpoint reset이 빠졌다는 P1이 보고됐다.
- Change:
1. `bot/features/watch/command.py`에서 `/watch add`도 기존 inactive thread metadata가 남아 있는 경우 `_reset_reactivated_same_session_band_state(...)`를 호출하도록 보강했다.
2. `tests/integration/test_watch_forum_flow.py`에 watchlist는 비어 있지만 inactive thread/session-alert metadata가 남은 legacy 재등록 경로 회귀 테스트를 추가했다.
3. `docs/specs/integration-test-cases.md`의 watch forum flow inventory와 `WF-18` 케이스를 현재 collect 결과에 맞게 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_watch_forum_flow.py -q -x --tb=line -p no:cacheprovider`
2. `.\.venv\Scripts\python.exe -m pytest tests/integration --collect-only -q -m "not live"`
- Status: done

## 2026-03-27
- Context: 서브에이전트 변경 리뷰에서 `/watch stop`이 starter 비활성화 실패 후에도 inactive state를 저장해 사용자 화면이 stale active 상태로 남을 수 있다는 P2가 보고됐다.
- Change:
1. `bot/features/watch/command.py`에서 tracked thread가 있는 `/watch stop`은 inactive starter update가 성공한 뒤에만 state를 `inactive`로 저장하도록 순서를 바꿨다.
2. 같은 경로에서 starter update가 실패하거나 stale handle이라 update-only가 불가능하면 command는 실패 응답을 반환하고 기존 active state와 runtime state를 유지하도록 조정했다.
3. `tests/integration/test_watch_forum_flow.py`에 stop 실패 시 active state와 cooldown이 보존되는 회귀 테스트를 추가했다.
4. `docs/specs/watch-poll-functional-spec.md`, `docs/specs/as-is-functional-spec.md`, `docs/specs/integration-test-cases.md`를 새 stop commit 조건과 테스트 inventory에 맞게 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_command.py tests/unit/test_watchlist_repository.py tests/unit/test_watch_cooldown.py tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py -q -x --tb=line -p no:cacheprovider`
2. `.\.venv\Scripts\python.exe -m pytest tests/integration --collect-only -q -m "not live"`
- Status: done

## 2026-03-27
- Context: 사용자가 watch command 정책을 `add/start/stop/delete` 모델로 재정의했고, `add`는 신규 추가만 유지하고 재활성화는 별도 `start`로 분리하라고 요청했다.
- Change:
1. `bot/features/watch/command.py`에서 `/watch start`, `/watch stop`, `/watch delete`를 추가하고 기존 `remove` 의미를 `stop`으로 재구성했다. `/watch add`는 신규 추가만 허용하고 inactive duplicate는 `/watch start` 안내로 바꿨다.
2. 같은 파일에서 `/watch stop`은 watchlist를 유지한 채 runtime state만 정리하고 inactive placeholder update를 update-only로 시도하게 했으며, `/watch delete`는 admin/owner/global-admin만 실행 가능하게 제한했다.
3. `bot/forum/repository.py`, `bot/app/types.py`, `bot/features/watch/thread_service.py`를 갱신해 inactive status-only entry, active-symbol filter, full watch-state delete, Discord thread delete helper를 추가했다.
4. `bot/features/watch/service.py`는 starter/placeholder에 `상태: 실시간 감시중` / `상태: 감시 중단됨` 줄을 명시하도록 바꿨다.
5. `bot/features/intel_scheduler.py`는 active symbol만 장중 poll 대상으로 보고, stopped symbol은 unfinalized session close finalization 대상일 때만 계속 추적하도록 바꿨다.
6. `tests/unit/test_watch_command.py`, `tests/unit/test_watchlist_repository.py`, `tests/unit/test_watch_cooldown.py`, `tests/integration/test_watch_forum_flow.py`, `tests/integration/test_watch_poll_forum_scheduler.py`를 새 command/status 계약에 맞게 갱신하고 `start/stop/delete/list` 회귀를 추가했다.
7. `docs/context/CURRENT_STATE.md`, `docs/context/design-decisions.md`, `docs/specs/as-is-functional-spec.md`, `docs/specs/watch-poll-functional-spec.md`, `docs/specs/integration-test-cases.md`를 현재 구현 truth 기준으로 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_command.py tests/unit/test_watchlist_repository.py tests/unit/test_watch_cooldown.py tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py -q -x --tb=line -p no:cacheprovider`
2. `.\.venv\Scripts\python.exe -m pytest tests/integration --collect-only -q -m "not live"`
- Status: done

## 2026-03-27
- Context: PR #16 재리뷰 후속으로 watch forum-thread remove/re-add 흐름과 legacy hard-cut 문서 정리를 사용자 요청에 따라 마무리했다.
- Change:
1. `bot/features/watch/command.py`에서 `/watch add`가 기존 inactive thread를 복구할 때도 active placeholder starter를 명시적으로 다시 쓰도록 바꿨다.
2. 같은 파일과 `bot/features/watch/thread_service.py`에서 `/watch remove`가 update-only 경로(`allow_create=False`)를 사용하도록 바꿔, 기존 registry가 있어도 stored thread/starter가 stale이면 새 inactive thread를 만들지 않도록 막았다.
3. `bot/app/settings.py`, `bot/app/types.py`, `bot/forum/repository.py`, `tests/unit/test_bot_client.py`에서 더 이상 쓰지 않는 `WATCH_ALERT_CHANNEL_ID` / `watch_alert_channel_id` 경로와 `WATCH_ALERT_COOLDOWN_MINUTES` settings surface를 제거했다.
4. `tests/integration/test_watch_forum_flow.py`에 stale thread handle일 때 recreate를 막는 회귀 테스트와 `/watch remove`의 `allow_create=False` 전달 검증을 추가했다.
5. `.env.example`, `docs/operations/config-reference.md`, `docs/specs/watch-poll-functional-spec.md`, `docs/specs/as-is-functional-spec.md`를 current code 기준으로 갱신해 watch route hard cut과 band comment 정수 label 의도를 명시했다.
6. reviewer follow-up으로 `bot/features/intel_scheduler.py`의 close-price fallback을 adjacent next trading session으로 제한하고, `bot/features/watch/command.py`에서 same-session re-add 시 highest band checkpoint를 reset하도록 보강했다.
7. `tests/integration/test_watch_poll_forum_scheduler.py`, `tests/integration/test_watch_forum_flow.py`, `tests/unit/test_watch_cooldown.py`에 multi-session gap carry-forward와 same-session reactivation edge case 회귀를 추가했다.
8. `bot/features/intel_scheduler.py`에서 malformed persisted symbol을 per-symbol snapshot failure로 처리해 scheduler-wide abort를 막고, `bot/intel/providers/market.py`에서 KRX off-hours close finalization용 stale snapshot 허용 조건을 추가했다.
9. `tests/integration/test_watch_poll_forum_scheduler.py`, `tests/unit/test_market_provider.py`에 malformed symbol isolation과 post-close domestic stale snapshot 허용 회귀를 추가했다.
10. `docs/specs/integration-test-cases.md`의 suite overview를 현재 collect 결과(`non-live 74`, `live 2`)에 맞추고, stale했던 watch text-alert 섹션을 `test_watch_forum_flow.py` / `test_watch_poll_forum_scheduler.py` 기준의 현행 forum-thread coverage로 교체했다.
11. malformed symbol guard가 예상 밖의 session 계산 버그까지 삼키지 않도록 `unsupported-market:*` runtime error만 per-symbol failure로 격리하고, 그 외 오류는 그대로 surface되게 좁혔다.
12. `docs/context/CURRENT_STATE.md`, `docs/specs/as-is-functional-spec.md`, `docs/specs/watch-poll-functional-spec.md`의 `/watch add` 표현을 현재 코드 기준으로 정리해, duplicate add는 no-op이고 stale thread repair command가 아니라는 점을 명시했다.
13. `bot/intel/providers/market.py`에서 post-close stale snapshot 허용 범위를 off-hours session close snapshot 전체로 넓혀, 미국장 close finalization도 stale-quote에 막히지 않게 했다.
14. `tests/unit/test_market_provider.py`에 post-close US snapshot stale 허용 회귀를 추가했다.
15. `bot/features/watch/thread_service.py`에서 기존 watch thread/starter resolve는 `discord.NotFound`일 때만 recreate fallback으로 넘기고, `Forbidden`/`HTTPException`은 bubble되게 바꿔 transient Discord 오류가 duplicate thread를 만들지 않도록 했다.
16. `bot/features/watch/service.py`는 band label `%`를 `max(0.1, WATCH_ALERT_THRESHOLD_PCT) * band` 기준의 trimmed decimal로 렌더링하도록 바꿔, fractional threshold와 sub-1% threshold도 실제 trigger와 같은 문구로 보이게 했다.
17. `tests/integration/test_watch_forum_flow.py`, `tests/unit/test_watch_cooldown.py`와 current-truth docs를 갱신해 transient thread fetch failure non-recreate와 fractional band label rendering을 회귀로 고정했다.
18. `bot/app/bot_client.py`는 startup 시 legacy `watch_alert_channel_id`만 남은 guild를 감지하면 `/setwatchforum` migration 경고를 남기도록 보강했고, `tests/unit/test_bot_client.py` 및 handoff/current-state docs에 현재 로컬 state의 watch migration 필요를 기록했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_market_provider.py -q -x --tb=line -p no:cacheprovider`
2. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py tests/unit/test_market_provider.py tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py tests/unit/test_bot_client.py -q -x --tb=line -p no:cacheprovider`
3. `.\.venv\Scripts\python.exe -m pytest tests/integration --collect-only -q -m "not live"`
- Status: done

## 2026-03-27
- Context: 서브에이전트 코드 리뷰에서 watch forum-thread rollout의 carry-forward finalization, forum route change, KRX stale timestamp 처리에 결함이 지적됐다.
- Change:
1. `bot/features/intel_scheduler.py`를 보강해 prior session이 unfinalized인 상태에서 다음 regular session snapshot이 들어오면, current session state를 reset하기 전에 이전 session close finalization을 먼저 수행하도록 수정했다.
2. `bot/features/watch/thread_service.py`는 기존 symbol thread를 재사용할 때 현재 `watch_forum_channel_id`의 parent forum인지 확인하고, forum route가 바뀐 경우 새 forum에 thread를 다시 만들도록 보완했다.
3. `bot/intel/providers/market.py`는 KRX quote payload의 체결 시각을 `asof`로 파싱해 domestic stale quote 정책이 실제로 동작하도록 수정했다.
4. `tests/integration/test_watch_poll_forum_scheduler.py`, `tests/integration/test_watch_forum_flow.py`, `tests/unit/test_market_provider.py`, `docs/specs/watch-poll-functional-spec.md`에 관련 회귀 테스트와 현재 동작 설명을 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py tests/unit/test_market_provider.py -q`
2. `.\.venv\Scripts\python.exe -m pytest tests/unit tests/integration -q`
- Status: done

## 2026-03-26
- Context: 추가 운영 피드백으로 watch starter의 가격 줄에 시장별 통화 기호가 필요하다는 요청이 들어왔다.
- Change:
1. `bot/features/watch/service.py`에 market prefix 기반 가격 포맷 helper를 추가해 KRX는 `₩`, NAS/NYS/AMS는 `$`를 starter의 `전일 종가`와 `현재가`에 붙이도록 바꿨다.
2. 관련 unit/integration test 기대값과 `docs/specs/watch-poll-functional-spec.md`의 starter contract를 함께 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/integration/test_watch_poll_forum_scheduler.py -q`
- Status: done

## 2026-03-26
- Context: 운영자 기능 테스트 피드백으로 watch starter/comment 문구가 내부 개발용어에 가깝다는 수정 요청이 들어왔다.
- Change:
1. `bot/features/watch/service.py`의 starter 렌더링에서 `기준 세션`, `당일 alert status`, `당일 최고 상승/하락 band` 노출을 제거하고 `전일 종가`, `현재가`, `변동률`, `마지막 갱신`만 남겼다.
2. band comment 문구를 `상승 band 돌파` 형식에서 `{band}% 이상 상승/하락 : {change_pct}` 형식으로 바꿨고, inactive placeholder도 `감시가 중지되었습니다`로 정리했다.
3. 관련 unit/integration test 기대값과 `docs/specs/watch-poll-functional-spec.md`를 함께 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_watch_cooldown.py tests/integration/test_watch_poll_forum_scheduler.py -q`
- Status: done

## 2026-03-26
- Context: 사용자가 승인된 watch forum-thread rollout 계획을 그대로 구현하라고 요청했다.
- Change:
1. `bot/features/intel_scheduler.py`, `bot/features/watch/service.py`, `bot/features/watch/session.py`, `bot/features/watch/thread_service.py`, `bot/features/watch/command.py`, `bot/features/admin/command.py`, `bot/forum/repository.py`, `bot/intel/providers/market.py`, `bot/app/types.py`, `bot/app/bot_client.py`를 갱신해 watch polling을 text alert 모델에서 `watch_forum_channel_id` + persistent symbol thread + `WatchSnapshot` + session-aware band/close finalization 모델로 교체했다.
2. `/setwatchchannel`을 제거하고 `/setwatchforum`을 추가했으며, `/watch add`는 forum route 없으면 거절하고 symbol thread/starter를 즉시 보장하도록 바꿨다.
3. `tests/unit/*`, `tests/integration/*`의 watch 관련 케이스를 forum-thread/session 모델 기준으로 교체하고, 새 scheduler/thread/provider failure recovery 시나리오를 추가했다.
4. `docs/context/CURRENT_STATE.md`, `docs/operations/config-reference.md`, `docs/operations/runtime-runbook.md`, `docs/specs/watch-poll-functional-spec.md`, `docs/specs/as-is-functional-spec.md`, `README.md`를 현재 구현 기준으로 최소 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit tests/integration -q`
2. 결과: 전체 unit/integration watch 회귀 포함 통과.
3. live Discord/KIS smoke는 credential/forum 권한 검증이 없어 이번 세션에서 수행하지 않았다.
- Next:
1. 운영 환경에서 `/setwatchforum -> /watch add -> scheduler poll -> close finalization` live smoke를 1회 수행해 forum 권한, thread follow UX, provider payload 안정성을 확인한다.
- Status: done

## 2026-03-26
- Context: 추가 리뷰에서 `마감가 알림`의 종가 소스와 close finalization partial failure retry semantics가 아직 문서상 열려 있다는 지적이 나왔다.
- Change:
1. `docs/specs/watch-poll-to-be-spec.md`를 보강해 `마감가`는 after-hours current price가 아니라 same-session official regular close price를 사용하도록 고정했다.
2. 같은 문서에 `session_close_price` 기반 close finalization 입력 계약, same-session close comment 재사용, `close_comment_ids_by_session` checkpoint 후 finalization 완료 마킹, delete/create/save 중간 실패 시 retry 규칙을 추가했다.
3. system state 예시의 `watch_reference_snapshots.price`를 `reference_price`로 명확히 바꿨다.
4. `docs/specs/external-intel-api-spec.md`에 `session_close_price` 필드를 추가하고, close summary는 이 값을 사용해야 한다는 규칙을 명시했다.
5. `docs/specs/qa-test-backlog.md`에 regular close price source 검증, `session_close_price` 누락 retry, partial close finalization failure recovery 테스트를 추가하고 failure-injection 항목 번호를 정리했다.
- Verification:
1. To-Be spec, external API contract, QA backlog 사이에서 `마감가=official regular close price`, `session_close_price`, `partial failure retry` 의미가 일관되는지 대조했다.
2. 이번 작업도 문서화만 수행했고 코드 변경이나 live verification은 하지 않았다.
- Next:
1. 구현 전 `session_close_price`를 quote adapter에서 직접 받을지, 별도 close endpoint로 보강할지 provider 설계를 먼저 확정한다.
2. close finalization 구현 시 close comment 재사용 probe와 checkpoint save 순서를 코드 레벨 transaction처럼 정리한다.
- Status: done

## 2026-03-26
- Context: 서브에이전트 reviewer/tester 검토에서 watch To-Be 문서의 regular-session gate, close catch-up, close history state, QA backlog 누락이 지적됐다.
- Change:
1. `docs/specs/watch-poll-to-be-spec.md`를 다시 정리해 intraday update는 regular session open 중에만 허용하고, off-hours는 close finalization-only 경로로 동작하도록 고정했다.
2. 같은 문서에 `first eligible poll after close` 기준의 idempotent catch-up, multi-session close history(`close_comment_ids_by_session`), external `price -> WatchSnapshot.current_price` 매핑, remove mid-session 후 1회 close finalization 규칙을 추가했다.
3. `docs/specs/qa-test-backlog.md`를 새 watch forum-thread 모델 기준으로 갱신해 `/setwatchforum`, `/watch add` route gating, symbol thread reuse, close finalization catch-up, remove 중 세션 정리, 3% ladder edge case, close history persistence 회귀를 추가했다.
4. `docs/context/design-decisions.md`의 2026-03-26 watch target decision을 review 반영본으로 갱신했다.
- Verification:
1. To-Be spec, external quote contract, QA backlog 사이에서 `세션`, `off-hours`, `close finalization`, `price/current_price`, `close history` 의미가 일관되는지 대조했다.
2. 이번 작업도 문서화만 수행했고 코드 변경이나 live verification은 하지 않았다.
- Next:
1. 구현 단계에서는 `WatchSnapshot` internal type과 `close_comment_ids_by_session` state schema를 코드 타입으로 먼저 확정한다.
2. scheduler 구현 전, market calendar helper가 KRX/US 모두에 대해 `session open/close`와 `first eligible poll after close`를 안정적으로 제공하는지 확인한다.
- Status: done

## 2026-03-26
- Context: 사용자가 watch forum-thread To-Be spec을 다시 다듬어 `3% band ladder`, `장마감 intraday comment 정리`, `마감가 알림 영구 보존`, `forum route 없으면 add 거절` 규칙을 고정했다.
- Change:
1. `docs/specs/watch-poll-to-be-spec.md`를 업데이트해 `세션=market-local regular-session trading date`, `3% band 무제한`, `한 poll에서 최고 신규 band 1건 comment`, `intraday comment 삭제 + 마감가 알림 보존`, `watch_forum_channel_id 없으면 /watch add 거절`을 반영했다.
2. `docs/specs/external-intel-api-spec.md`의 watch quote 섹션에 `session_date`가 regular-session trading date 기준이며 band ladder / close finalization reset에 쓰인다는 점을 보강했다.
3. `docs/context/design-decisions.md`의 2026-03-26 watch target decision을 최신 고정안으로 갱신했다.
- Verification:
1. To-Be spec 안에서 `세션`, `band ladder`, `close finalization`, `route gating` 규칙이 서로 충돌하지 않는지 재검토했다.
2. 외부 quote target contract의 `previous_close/session_date` 요구와 To-Be spec의 session/band semantics가 일치하는지 확인했다.
3. 이번 작업도 문서화만 수행했고 코드 변경이나 live verification은 하지 않았다.
- Next:
1. 구현 시 close finalization trigger를 market calendar 기준으로 어디서 계산할지 구체화한다.
2. state schema에는 intraday comment IDs와 session close finalized flag를 어떤 경로에 둘지 먼저 확정한다.
- Status: done

## 2026-03-26
- Context: 사용자가 `watch_poll` 목표 동작을 forum thread + previous_close basis 모델로 고정하고 To-Be 스펙 문서화를 요청했다.
- Change:
1. `docs/specs/watch-poll-to-be-spec.md`를 추가해 guild-symbol persistent thread, starter edit, threshold first-crossing comment, session-level alert persistence, previous_close basis, target state model을 정리했다.
2. `docs/specs/external-intel-api-spec.md`의 watch quote 계약을 target model에 맞춰 `previous_close`, `session_date` 필수 필드가 드러나도록 보강했다.
3. `docs/context/design-decisions.md`에 watch rollout 목표 모델을 accepted decision으로 기록했다.
- Verification:
1. 새 To-Be 문서가 As-Is 문서를 덮어쓰지 않고 별도 목표 명세로 분리됐는지 확인했다.
2. watch target spec과 external intel API contract 사이에서 `previous_close/session_date` 요구사항이 일관되는지 대조했다.
3. 이번 작업은 문서화만 수행했고 코드 변경이나 live verification은 하지 않았다.
- Next:
1. 구현 시작 전 `watch_forum_channel_id`, symbol thread registry, watch snapshot type 확장 범위를 코드 스키마로 구체화한다.
2. 구현 단계에서는 기존 text alert state와 new forum-thread state의 migration plan 및 회귀 테스트 범위를 먼저 확정한다.
- Status: done

## 2026-03-26
- Context: 사용자가 `watch_poll` 전용 기능명세서를 작성해 달라고 요청했다.
- Change:
1. `docs/specs/watch-poll-functional-spec.md`를 새로 추가했다.
2. 문서는 현재 코드 기준의 `watch_poll` 동작, scheduler trigger, provider wiring, baseline/cooldown/latch 규칙, state schema, 상태 기록, 현재 제약과 rollout gap을 분리해 정리했다.
3. 내용 근거는 `bot/features/intel_scheduler.py`, `bot/features/watch/service.py`, `bot/forum/repository.py`, `bot/intel/providers/market.py`, 관련 unit/integration tests로 제한했다.
- Verification:
1. 기존 canonical docs(`as-is-functional-spec`, `external-intel-api-spec`, `config-reference`)와 코드/테스트를 대조해 문서 경계가 섞이지 않도록 확인했다.
2. 이번 작업에서는 live Discord/vendor smoke는 다시 실행하지 않았다.
- Next:
1. `watch_poll`의 market-hours gating 또는 domestic quote freshness 정책이 구현되면 이 문서의 `Current Constraints and Known Gaps`와 `Rollout Alignment Notes`를 함께 갱신한다.
- Status: done

## 2026-03-24
- Context: 사용자가 뉴스 forum routing은 explicit route only로 바꾸고, base guild forum fallback을 제거하라고 요청했다.
- Change:
1. `bot/features/intel_scheduler.py`의 뉴스 경로는 이제 `news_forum_channel_id`가 있을 때만 pending guild로 잡는다.
2. `forum_channel_id`만 있는 길드는 `missing_forum`으로 처리되어 뉴스/트렌드 게시 대상에서 제외된다.
3. startup `NEWS_TARGET_FORUM_ID` bootstrap은 그대로 유지하고, runtime fallback이 아니라 `news_forum_channel_id` state initializer로만 계속 사용한다.
4. `tests/integration/test_intel_scheduler_logic.py`는 뉴스 성공 경로를 explicit `news_forum_channel_id` 기준으로 갱신했고, base-forum-only skip과 mixed routing state를 추가 검증하도록 확장했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_bot_client.py -q`
2. `.\.venv\Scripts\python.exe -m pytest tests\integration\test_intel_scheduler_logic.py -q`
3. 결과: unit `2 passed`, integration `43 passed`
- Next:
1. 현재 local state의 guild `1470388757617446924`는 `forum_channel_id`만 있고 `news_forum_channel_id`가 없어, 배포 후 뉴스/트렌드 게시를 계속 원하면 explicit `/setnewsforum` 또는 startup bootstrap으로 state를 채워야 한다.
- Status: done

## 2026-03-24
- Context: 사용자가 heatmap auto scheduler가 exact scheduled minute를 놓치면 실행을 miss하는 버그를 same-day catch-up 방식으로 고치라고 요청했다.
- Change:
1. `bot/features/auto_scheduler.py`는 이제 `15:35`/`06:05` KST exact-minute match가 아니라, fixed scheduled time 이후 same-day catch-up으로 heatmap auto job을 실행한다.
2. guild state에 `last_auto_attempts`를 추가하고 `bot/forum/repository.py`, `bot/app/types.py`에 helper/type을 보강했다.
3. 정책은 `하루 1회 scheduled auto attempt`로 고정했다. success, holiday, calendar failure, runner failure 모두 그 날의 auto attempt를 소비하고, success일 때만 `last_auto_runs`가 기록된다.
4. trading-day check는 late catch-up 시에도 intended schedule 시각 기준으로 평가되도록 scheduled timestamp로 호출한다.
5. `tests/integration/test_auto_scheduler_logic.py`는 catch-up success, pre-schedule no-op, existing skip guard, failure consumes attempt, state preservation을 포함하도록 확장했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\integration\test_auto_scheduler_logic.py -q`
2. 결과: `10 passed`
- Next:
1. 필요하면 실제 운영에서 scheduled minute 직후 재기동 상황을 한 번 만들어 same-day catch-up이 기대대로 동작하는지 Discord smoke로 확인한다.
- Status: done

## 2026-03-24
- Context: 사용자가 documentation update policy를 현재 구조에 맞게 AGENTS/operating-rules에 반영하라고 요청했다.
- Change:
1. `AGENTS.md`의 Documentation Update Rules를 최소 수정 원칙과 문서별 update trigger 중심으로 교체했다.
2. `docs/context/operating-rules.md`의 Context Update Rules를 current truth, config/runtime, deep spec, logs, backlog/report 경계가 드러나도록 구체화했다.
3. `docs/context/session-handoff.md`에 최신 policy 변경을 남기고, 밀려난 older active block은 `docs/context/session-history.md`로 이동했다.
- Verification:
1. `AGENTS.md`와 `docs/context/operating-rules.md`를 다시 읽어 중복은 줄이고 역할 경계는 유지됐는지 확인했다.
2. `session-handoff.md`가 최신 3개 active block만 유지하는지 확인했다.
3. 이번 단계는 문서 정책 정리 작업이라 테스트는 실행하지 않았다.
- Next:
1. 이후 문서 변경은 새 policy에 맞춰 최소 범위로만 반영한다.
- Status: done

## 2026-03-24
- Context: 사용자가 code verification required 문서 진술을 실제 코드 기준으로 검증하라고 요청했다.
- Change:
1. `bot/app/settings.py`, `bot/features/*`, `bot/app/bot_client.py`, `bot/forum/service.py`, `bot/forum/repository.py`, `bot/intel/providers/*`, `bot/markets/cache.py`를 읽어 exact defaults, authorization boundary, provider wiring을 코드 기준으로 재확인했다.
2. `docs/operations/config-reference.md`에 code-confirmed defaults, bootstrap env 동작, provider wiring, status-only env 역할을 최소 범위로 추가했다.
3. `docs/operations/runtime-runbook.md`에 setup/admin command와 watch/status/manual command의 현재 코드 기준 authorization boundary를 짧게 추가했다.
4. `docs/context/CURRENT_STATE.md`는 current behavior concern과 QA review artifact의 경계를 더 분명히 하도록 canonical pointer와 blocker 섹션 표현을 좁혔다.
- Verification:
1. 코드 검색으로 `ADMIN_STATUS_CHANNEL_ID`가 settings 외 bot code에서 직접 사용되지 않음을 확인했다.
2. `TWELVEDATA_API_KEY`, `OPENFIGI_API_KEY`가 현재 bot code에서는 status row 외 active runtime path에 연결되지 않음을 확인했다.
3. `MASSIVE_API_KEY`/legacy `POLYGON_API_KEY`는 `MARKET_DATA_PROVIDER_KIND=kis`일 때 미국 종목 fallback provider로만 연결되는 것을 확인했다.
4. 이번 단계는 문서 정확도 보강 작업이라 테스트는 실행하지 않았다.
- Next:
1. 추가 문서 개편은 없고, 이후 필요 시 query-list defaults나 heuristic constant 같은 low-value ambiguity만 코드 대조로 좁힌다.
- Status: done

## 2026-03-24
- Context: 사용자가 문서 migration plan의 Phase 3 실행을 요청했다.
- Change:
1. QA test backlog 문서는 이제 `docs/specs/qa-test-backlog.md`에 있다.
2. 최신 consolidated QA review report는 이제 `docs/reports/qa-issue-review-2026-03-24.md`에 있다.
3. `docs/context/CURRENT_STATE.md`, `docs/context/operating-rules.md`의 포인터와 moved report 내부의 supporting evidence 경로를 새 taxonomy에 맞게 갱신했다.
4. `docs/context/session-handoff.md`는 최신 3개 active block만 유지하도록 한 block을 `docs/context/session-history.md`로 내려 보냈다.
- Verification:
1. renamed/moved file 두 개가 실제로 존재하는지 확인했다.
2. Markdown 파일 전역 검색으로 old QA path 참조를 확인했고, navigation/canonical 포인터는 새 경로로 정리됐는지 점검했다.
3. historical log/session archive 안의 old path 표기는 당시 기록 보존을 위해 유지했고, 이번 단계는 문서 taxonomy 조정이라 테스트는 실행하지 않았다.
- Next:
1. 추가 구조 개편은 없고, 이후에는 code verification required로 남겨둔 항목만 필요 시 코드 대조로 정리한다.
- Status: done

## 2026-03-24
- Context: 사용자가 문서 migration plan의 Phase 2 실행을 요청했다.
- Change:
1. `README.md`를 onboarding-only 구조로 축소했다. setup/run/minimal architecture/tests와 deeper-doc links만 남기고, 운영 상세/환경변수/확장 기능 설명은 제거했다.
2. `AGENTS.md`를 agent-rules + canonical-doc pointers 문서로 축소했다. 아키텍처 스냅샷, 운영 규칙 상세, 실행 체크리스트, 트러블슈팅, skills 목록, 다음 세션 TODO, 인터페이스 메모를 제거했다.
3. `docs/context/README.md`의 읽기 순서를 `CURRENT_STATE.md` 우선으로 바꾸고, `session-history.md`와 `operating-rules.md` 역할을 반영했다.
4. `docs/context/session-handoff.md`는 최신 active handoff 3개만 남기고, older handoff 93개를 `docs/context/session-history.md`로 이동했다.
- Verification:
1. `session-handoff.md`의 active block count와 `session-history.md`의 cutover note를 확인했다.
2. trimmed README/AGENTS가 새 context/operations/spec 문서로 적절히 링크하는지 확인했다.
3. 이번 단계는 문서 구조 조정이라 테스트는 실행하지 않았다.
- Next:
1. Phase 3에서 `docs/specs/qa-test-specification.md`와 `docs/specs/qa-issue-document.md`를 성격에 맞는 이름/위치로 재분류한다.
- Status: done

## 2026-03-24
- Context: 사용자가 승인한 문서 migration plan의 Phase 1로 새 구조 문서 초안을 먼저 추가하라고 요청했다.
- Change:
1. `docs/context/CURRENT_STATE.md`를 추가해 current truth, active workstreams, top blockers, do-not-assume를 짧게 요약했다.
2. `docs/context/session-history.md`를 추가해 Phase 2에서 handoff archive를 옮길 대상 파일을 만들었다.
3. `docs/context/operating-rules.md`를 추가해 문서 경계, secrets-vs-state, context update, branch/release rule을 AGENTS 밖으로 분리할 준비를 했다.
4. `docs/operations/runtime-runbook.md`, `docs/operations/config-reference.md`를 추가해 README/AGENTS에서 분리될 운영/설정 내용을 받을 위치를 만들었다.
5. 이번 단계에서는 기존 `README.md`, `AGENTS.md`, `docs/context/session-handoff.md` 본문 구조는 아직 손대지 않았다.
- Verification:
1. 새 문서 5개가 생성됐는지와 이들이 참조하는 핵심 문서 경로가 실제로 존재하는지 `Test-Path`로 확인했다.
2. summary 문서에 exact env defaults, exact schedule defaults, Massive wiring 같은 코드 미검증 진술을 canonical fact로 쓰지 않았는지 재검토했다.
3. 이번 단계는 문서 구조 추가만이라 테스트는 실행하지 않았다.
- Next:
1. Phase 2에서 `README.md`와 `AGENTS.md`를 축소하고, `session-handoff.md`를 최신 handoff만 남기도록 분리한다.
- Status: done

## 2026-03-24
- Context: 사용자가 현재 Markdown 문서 체계를 분석해 덜 오염되고 덜 중복된 개편 방향을 제안해 달라고 요청했다.
- Change:
1. `README.md`, `AGENTS.md`, `docs/context/*`, `docs/specs/*`, `docs/reports/*`, `docs/prompts/*`, `.agents/skills/*`의 역할을 분류하고 중복 책임과 source-of-truth 분산 여부를 점검했다.
2. 핵심 구조 문제로 `AGENTS.md`의 위키화`, `session-handoff.md`의 누적 로그화`, `As-Is/To-Be/current-risk 기준 문서의 분산`을 정리했다.
3. 권장 방향은 `CURRENT_STATE.md` 신설, `session-handoff`와 `session-history` 분리, `AGENTS.md`를 agent rule 중심으로 축소, `README.md`를 onboarding 위주로 축소하는 쪽으로 제안했다.
- Verification:
1. 실제 Markdown 파일 목록과 각 문서 헤더/앞부분을 읽어 근거를 확인했다.
2. 특히 `session-handoff.md`(1041 lines), `development-log.md`(1235 lines), `as-is-functional-spec.md`(1125 lines), `AGENTS.md`(236 lines), `README.md`(169 lines)를 기준으로 비대화와 역할 중복을 판단했다.
3. 이번 작업은 분석/제안만이라 테스트는 실행하지 않았다.
- Next:
1. 사용자가 원하면 다음 단계에서 제안한 구조에 맞춘 실제 문서 개편 패치를 작은 단계로 나눠 진행한다.
- Status: done

## 2026-03-24
- Context: 사용자가 As-Is spec과 QA test spec을 기준으로 execution-ready QA issue document를 요청했다.
- Change:
1. `docs/specs/qa-issue-document.md`를 추가했다.
2. 문서는 `docs/specs/as-is-functional-spec.md`를 authoritative source로, `docs/specs/qa-test-specification.md`를 supporting evidence로 두고 root-cause 단위 이슈 16개를 정리했다.
3. 이슈는 `Defect`, `Incomplete contract`, `Operational risk`, `Documentation gap`로 구분했고, release blocker, implementation phase, GitHub issue shortlist, explicit non-issues까지 포함했다.
- Verification:
1. 생성 문서의 섹션 구조가 요청 형식과 맞는지 확인했다.
2. `## Issue QAI-` 개수를 세어 16개인지 검산했다.
3. 이번 변경은 문서 작업이라 테스트는 추가 실행하지 않았다.
- Next:
1. 후속 작업은 `QAI-01`, `QAI-02`, `QAI-05`, `QAI-03`, `QAI-10` 순으로 실제 GitHub issue/코드 수정으로 옮기면 된다.
- Status: done

## 2026-03-24
- Context: 사용자가 방금 만든 As-Is spec에 future-state/과신 표현이 섞였는지 contamination review를 요청했다.
- Change:
1. `docs/specs/as-is-functional-spec.md`의 일부 문장을 현재 코드 분기 중심 표현으로 낮췄다.
2. 특히 `manual heatmap`, `forum upsert`, `watch poll`, `instrument registry refresh`, `legacy !ping`, `startup bootstrap constraint` 쪽 문장을 "보장"이 아니라 "현재 코드가 시도/거절/기록하는 동작" 기준으로 교정했다.
3. `watch poll`, `legacy !ping` 섹션 confidence는 reachability/semantics ambiguity를 반영해 보수적으로 조정했다.
4. 후속 검산에서 `instrument registry refresh` confidence 문구 오치환을 수정하고, load/search wiring과 외부 데이터 완전성 ambiguity를 분리했다.
- Verification:
1. 수정 후 문서를 다시 읽어 `must`, `requires`, `keep`, `appears`, `guarantee`처럼 과신으로 읽힐 수 있는 문장을 재점검했다.
2. 이번 변경은 문서 작업이라 테스트는 추가 실행하지 않았다.
- Next:
1. 이후 reverse-spec 문서는 feature purpose와 operational constraints를 쓸 때 "attempts", "rejects unless", "records when" 같은 구현 중심 동사만 사용한다.
- Status: done

## 2026-03-24
- Context: 사용자가 현재 코드 기준 As-Is functional specification을 역추출해 달라고 요청했다.
- Change:
1. `docs/specs/as-is-functional-spec.md`를 추가했다.
2. 문서는 README, 설정, 부트스트랩, slash command, scheduler, forum/state persistence, provider, registry, tests를 근거로 현재 구현 동작만 정리했다.
3. 구현 사실과 별도로 `ambiguities`, `observed gaps`, `As-Is vs To-Be boundary`를 분리해 미래 설계 추정을 섞지 않도록 정리했다.
- Verification:
1. `README.md`, `.env.example`, `bot/app/*`, `bot/features/*`, `bot/forum/*`, `bot/intel/*`, `bot/markets/*`, 주요 integration test 파일을 대조해 각 섹션의 근거 경로를 문서에 명시했다.
2. 이번 변경은 문서 작업이라 테스트는 추가 실행하지 않았다.
- Next:
1. 이후 QA/리팩터링 문서는 이 As-Is spec을 baseline으로 삼고, 실제 코드 변경 없이 바꾸고 싶은 동작은 별도 To-Be 문서로 분리한다.
2. 후속 문서 후보는 `state schema`, `scheduler contract`, `command authorization policy`다.
- Status: done

## 2026-03-24
- Context: 사용자가 principal-level QA 리뷰를 바탕으로 테스트 명세 문서를 만들어 달라고 요청했다.
- Change:
1. `docs/specs/qa-test-specification.md`를 추가해 QA 리뷰의 주요 결함을 `unit`, `integration`, `E2E`, `regression`, `failure injection` 테스트 구현 항목으로 변환했다.
2. 명세에는 state fail-open, mock/live fail-closed, watch freshness/timezone, scheduler catch-up, Discord duplicate upsert, 권한/운영 진단 보호 시나리오를 우선순위(`P0~P2`)와 함께 정리했다.
- Verification:
1. 기존 테스트 문서 `docs/specs/integration-test-cases.md`, `docs/specs/integration-live-test-cases.md` 형식과 역할을 대조해 새 문서가 "현재 coverage 설명"이 아니라 "추가 구현할 QA 테스트 backlog" 역할로 분리되게 확인했다.
2. 이번 변경은 문서 작업이라 테스트는 추가 실행하지 않았다.
- Next:
1. 구현 우선순위는 `UT-01`, `UT-02`, `UT-03`, `UT-05`, `IT-01`, `IT-02`, `FI-03` 순으로 두고 실제 test file에 옮긴다.
2. 테스트 구현을 시작할 때는 현재 integration 문서와 중복되지 않도록 새 케이스와 기존 케이스의 경계를 먼저 표시한다.
- Status: done

## 2026-03-24
- Context: 사용자가 slash command 없이도 바로 확인할 수 있게 뉴스/트렌드 게시를 수동 실행해 달라고 요청했다.
- Change:
1. 별도 단발 Python 스크립트로 `bot.features.intel_scheduler._run_news_job()`를 직접 호출했다.
2. 실행 시각 기준 오늘자(`2026-03-24`) `newsbriefing-domestic`, `newsbriefing-global`, `trendbriefing` thread가 새로 생성됐다.
- Verification:
1. run 결과:
   - `news_briefing.status=ok`
   - `trend_briefing.status=ok`
   - detail=`posted=1 failed=0 missing_forum=0 forum_resolution_failures=0 domestic=20 global=12`
   - trend detail=`posted=1 failed=0 missing_forum=0 forum_resolution_failures=0 domestic_themes=3 global_themes=3`
2. state 저장 확인:
   - `newsbriefing-domestic` thread=`1485802325871296643`
   - `newsbriefing-global` thread=`1485802328261922876`
   - `trendbriefing` thread=`1485802330795413606`
3. 실제 `trendbriefing` content message를 fetch해 numbering이 사라진 새 포맷을 확인했다:
   `[국내 트렌드 테마] -> 바이오 -> 근거: ... -> 기사: ...`
4. global section도 동일하게 `금리/Fed -> 근거: ... -> 기사: ...` 형식으로 확인했다.
- Next:
1. 사용자가 Discord에서 실제 가독성을 확인한다.
2. 필요하면 다음 단계로 `| source | time | link` 구분자도 더 부드럽게 정리한다.
- Status: done

## 2026-03-24
- Context: 사용자가 Discord에서 직접 확인할 수 있게 봇을 다시 켜 달라고 요청했다.
- Change:
1. 로컬 workspace에서 `.\.venv\Scripts\python.exe -m bot.main`를 백그라운드 프로세스로 기동했다.
2. stdout/stderr는 `output/bot-startup.out.log`, `output/bot-startup.err.log`로 리다이렉트했다.
- Verification:
1. `data/logs/bot.log` 기준 startup 로그 확인:
   - gateway 연결 성공
   - global commands 11개 sync
   - `Auto screenshot scheduler started`
   - `Intel scheduler started`
   - `Logged in as only_test#5605`
2. 초기 scheduler tick은 `watch_poll status=skipped detail=no-watch-symbols`였다.
3. 프로세스는 launcher parent(`21556`)와 실제 interpreter child(`27068`) 체인으로 살아 있고, Discord gateway 연결은 child process가 보유 중이다.
- Next:
1. 사용자가 Discord에서 trend/news 포맷을 직접 확인한다.
2. 확인이 끝나면 필요 시 봇 프로세스를 정리한다.
- Status: done

## 2026-03-24
- Context: 사용자가 `trendbriefing` 게시글에서 테마 제목 아래 기사 줄에 숫자/기호가 섞여 보여 포맷이 어색하다고 보고했다.
- Change:
1. `bot/features/news/trend_policy.py`는 theme block 제목에서 번호 prefix(`1.`, `2.`)를 제거하고, 테마명을 독립 헤더 라인으로만 렌더링하도록 바꿨다.
2. 같은 파일은 `- 근거:` / `- 기사 ...` 형태 대신 `근거:` / `기사:` 접두사를 사용해 계층 표기를 단순화했다.
3. `tests/unit/test_trend_policy.py`에 plain theme title + `기사:` 포맷 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_trend_policy.py -q` 통과
2. sample render 확인:
   `[국내 트렌드 테마] -> 반도체 -> 근거: ... -> 기사: ...`
- Next:
1. 실제 Discord에서 가독성을 보고, 필요하면 다음 단계로 source/time/link 구분자(`|`)도 더 부드럽게 조정한다.
- Status: done

## 2026-03-24
- Context: 사용자가 영어 `Marketaux` 해외뉴스 trend 품질 이슈를 당분간 보류하고, 뉴스 provider를 `Naver`로 되돌려 한국 기사만 수집하도록 운영 설정을 바꾸길 원했다.
- Change:
1. 로컬 runtime `.env`의 `NEWS_PROVIDER_KIND`를 `hybrid`에서 `naver`로 변경했다.
2. 이 변경으로 현재 뉴스 브리핑/트렌드의 global 경로는 `Marketaux` 영어 기사 대신 `Naver` 검색 결과만 사용한다.
- Verification:
1. `.env`에서 `NEWS_PROVIDER_KIND=naver`로 갱신된 것을 확인했다.
- Next:
1. 만약 사용 의도가 "해외 기사 비활성화"가 아니라 "영어 기사만 제외"라면 현재 상태로 충분하다.
2. 반대로 global thread 자체를 비우거나 끄고 싶다면 별도 코드 변경이 필요하다.
- Status: done

## 2026-03-23
- Context: 전체 modified 파일 리뷰 중 `watch remove -> watch add` 후 첫 알림이 막히는 회귀를 발견했다.
- Change:
1. `bot/forum/repository.py`는 이제 `remove_watch_symbol()`에서 해당 symbol의 runtime watch 메타상태를 같이 지운다.
2. 정리 대상은 guild-level `watch_alert_cooldowns`, `watch_alert_latches`와 system-level `watch_baselines`다.
3. `tests/unit/test_watchlist_repository.py`에 remove 시 runtime state cleanup 회귀를, `tests/unit/test_watch_cooldown.py`에 remove/re-add 후 fresh alert 허용 회귀를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_watch_cooldown.py tests\unit\test_watchlist_repository.py tests\integration\test_intel_scheduler_logic.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀 통과
- Next:
1. 실제 운영 반영이 필요하면 봇 프로세스 또는 Docker Compose 서비스를 재기동한다.
2. 필요하면 follow-up으로 watch symbol 제거 시 관련 provider status/history도 같이 정리할지 검토한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `watch_poll`에서 같은 방향의 비슷한 변동 알림이 10분 뒤 다시 오는 것은 원치 않는다고 보고했다.
- Change:
1. `bot/features/watch/service.py`는 이제 같은 심볼이 같은 방향(`up|down`) 임계치 밖에 계속 머무르는 동안에는 첫 알림만 보내고, 임계치 안으로 한 번 복귀해야 같은 방향 알림을 다시 허용한다.
2. 이를 위해 guild state에 `watch_alert_latches`를 추가했고, canonical symbol migration 시 cooldown/baseline과 함께 latch key도 같이 정규화되게 했다.
3. 기존 `watch_alert_cooldowns`는 유지해 threshold 근처 출렁임에서 짧은 간격 재알림을 계속 막고, 반대 방향 전환은 기존처럼 별도 알림이 가능하게 뒀다.
4. `tests/unit/test_watch_cooldown.py`, `tests/unit/test_watchlist_repository.py`, `tests/integration/test_intel_scheduler_logic.py`에 same-direction suppress 및 rearm 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_watch_cooldown.py tests\unit\test_watchlist_repository.py tests\integration\test_intel_scheduler_logic.py -q` 통과
- Next:
1. 실제 운영 반영을 하려면 실행 중인 봇 프로세스 또는 Docker 컨테이너를 재기동해야 한다.
2. 필요하면 후속으로 `watch_alert_latches`를 `/source-status`나 admin 진단 경로에서 볼 수 있게 할지 검토한다.
- Status: done

## 2026-03-23
- Context: 사용자가 기능별 로그가 제대로 안 찍힌다고 보고해 운영 로그 가시성을 보강해 달라고 요청했다.
- Change:
1. `bot/features/intel_scheduler.py`는 이제 `watch_poll`, `news_briefing`, `trend_briefing`, `eod_summary`, `instrument_registry_refresh`의 `ok|skipped|failed` 결과를 state뿐 아니라 구조화된 파일 로그로도 남긴다.
2. `bot/features/watch/command.py`, `bot/features/admin/command.py`, `bot/features/runner.py`, `bot/features/status/command.py`에 slash command 요청/거절/성공 결과 로그를 추가했다.
3. `bot/app/command_sync.py`의 fail-open 경로는 `print(...)` 대신 logger를 사용하도록 바꿔 파일 핸들러를 타게 했다.
4. logging 보강 직후 전체 `pytest`에서 `FakeInteraction`에 `user`가 없는 테스트 더블 회귀가 드러나, command audit log는 모두 `interaction.user` 부재를 허용하는 helper 경로로 보강했다.
5. reviewer follow-up으로 `bot/intel/providers/market.py`의 `NYS -> AMS` exchange alias retry가 request 단계 `not-found` 예외에서는 계속되지 않는 결함을 추가 수정했고, `tests/unit/test_market_provider.py`에 해당 회귀 테스트를 넣었다.
6. `tests/unit/test_command_sync.py`는 새 logger 경로 기준으로 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_command_sync.py tests\unit\test_watch_command.py tests\unit\test_status_command.py tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀 통과
3. `docker compose up -d --build` 후 `data/logs/bot.log`와 `docker compose logs` 양쪽에서 `bot.features.intel_scheduler [intel] watch_poll status=ok ...` 라인이 실제로 기록되는 것을 확인했다.
- Next:
1. 필요하면 다음 단계로 `news/eod` 성공 로그 필드에 guild/forum counts를 조금 더 구체적으로 넣는다.
2. command audit log가 과도하게 길어지면 guild_id/user_id/result 정도만 남기고 detail truncation을 검토한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `/watch add UCO` 직후 `massive_reference ok=false`가 되는 이유를 버그로 판단했고, 수정까지 요청했다.
- Change:
1. `bot/intel/providers/market.py`의 KIS 해외 단건 조회는 이제 registry가 `NYS`로 저장한 미국 종목이 빈 quote를 돌리면 `AMS`를 한 번 더 재시도한다.
2. 이 fallback은 `NYS <-> AMS` 범위로만 제한해, SEC exchange 표기가 KIS 거래소 코드와 어긋나는 ETF/ETN 계열 오분류를 runtime에서 흡수하도록 했다.
3. `tests/unit/test_market_provider.py`에는 `NYS:UCO`가 1차 `NYS` 조회에서 빈 `last`를 받고도 2차 `AMS` 조회로 회복되는 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py -q` 통과
2. live spot check: `KisMarketDataProvider.get_quote("NYS:UCO", now_kst())`가 `provider='kis_quote'`로 실제 가격을 반환하는 것을 확인했다.
3. `docker compose up -d --build`로 컨테이너를 재기동한 뒤 다음 `watch_poll` tick이 `status=ok`, `processed=2`, `quote_failures=0`으로 회복된 것을 state로 확인했다.
- Next:
1. 장기적으로는 registry build 단계에서 `NYSE Arca` 계열 심볼을 더 정확히 구분할 보강 source가 필요한지 별도로 검토한다.
2. 현재 `provider_status.massive_reference=false`는 과거 fallback 실패 흔적이 남은 상태라, 실제 Massive entitlement 문제와 runtime status UX는 별도 과제로 본다.
- Status: done

## 2026-03-23
- Context: 사용자가 `develop`를 `master`에 반영하고 버전 태그를 달라고 요청했다.
- Change:
1. 로컬 `develop` 기준으로 `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀를 다시 실행했다.
2. `docs/context/session-handoff.md`에 Docker Compose 재기동 결과를 기록한 뒤 `develop`에 커밋하고 `origin/develop`로 push했다.
3. `develop -> master` release PR [#15](https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/15)를 생성했다.
4. GitHub repository rule상 `master`는 merge commit을 허용하지 않아 release PR은 `squash merge`로 마무리했다.
5. release 결과 커밋 `426a7f6 release: merge develop into master (2026-03-23) (#15)`에 git tag `v1.0.2`를 달아 push했다.
6. 이후 로컬 branch ref도 정리해 `master`는 `origin/master`, `develop`는 `origin/develop`를 각각 가리키도록 맞췄다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest -q` 통과
2. `gh pr view 15` 기준 `state=MERGED`, `mergeCommit=426a7f6`
3. `git show v1.0.2` 기준 tag target=`426a7f6`
4. release 직후에는 `origin/master`와 `origin/develop`의 code/runtime tree diff가 없었고, 현재 남은 차이는 release 기록용 `docs/context/development-log.md`, `docs/context/session-handoff.md` 두 파일뿐이다.
- Next:
1. 다음 `develop -> master` 릴리스도 저장소 규칙상 merge commit이 아니라 squash 또는 허용된 선형 방식으로 처리한다.
2. history는 달라도 현재 `master`와 `develop` tree는 같으므로, 후속 작업은 `develop`에서 계속 진행하면 된다.
- Status: done

## 2026-03-23
- Context: 사용자가 서브에이전트 리뷰를 통과할 때까지 반복하고, clean이면 integration subagent까지 돌린 뒤 커밋/푸시하라고 요청했다.
- Change:
1. reviewer finding 기준으로 `bot/features/intel_scheduler.py`의 instrument registry refresh를 한 번 더 보강했다.
2. refresh 실작업은 background task가 `data/state/instrument_registry.json`만 갱신하도록 두고, `job_last_runs`와 `provider_status` 저장은 다시 메인 scheduler loop가 task 완료 시점에만 반영하게 바꿨다. 이로써 detached refresh가 다른 scheduler job의 state save를 stale snapshot으로 덮어쓰는 race를 제거했다.
3. `_should_start_instrument_registry_refresh()`는 이제 configured minute를 놓친 late start에도 같은 날 최초 refresh를 catch-up 실행하고, failed run 뒤에는 same-day retry가 가능하도록 보강했다. 단 `dart-api-key-missing` 같은 static config failure는 분 단위 재시도를 막는다.
4. `tests/integration/test_intel_scheduler_logic.py`에는 `late-start catch-up`, `same-day retry`, `in-flight refresh 중 watch_poll 진행` 회귀를 추가했다.
- Verification:
1. reviewer subagent 재검토 결과 `No actionable issues found.`
2. `.\.venv\Scripts\python.exe -m pytest tests\integration\test_intel_scheduler_logic.py -q` 통과
3. integration subagent 실행 결과 `.\.venv\Scripts\python.exe -m pytest tests/integration` 기준 `55 passed, 2 deselected`
- Next:
1. 현재 변경분을 커밋하고 원격 브랜치에 push한다.
2. 이후 scheduler 관련 추가 변경은 detached background work가 main state save와 충돌하지 않는지부터 다시 본다.
- Status: done

## 2026-03-23
- Context: 사용자가 env와 state의 역할을 프로젝트 최우선 운영 규칙으로 고정하고, 이후 코드리뷰도 이 문서 기준으로 거절할 건 거절하자고 요청했다.
- Change:
1. `AGENTS.md`에 새 최우선 규칙을 추가해 `.env`는 민감정보와 bootstrap/default 값, `data/state/state.json`은 mutable Discord routing 값의 source of truth라고 명시했다.
2. `docs/context/review-rules.md`에는 새 Rule 2를 추가해 `민감정보는 env, mutable routing은 state`를 코드리뷰 acceptance gate로 고정했다.
3. `docs/context/design-decisions.md`, `docs/context/session-handoff.md`, `README.md`, `.env.example`도 같은 문구로 맞춰 문서 간 해석이 갈리지 않게 정리했다.
- Verification:
1. `AGENTS.md`, `review-rules.md`, `README.md`, `.env.example`, `design-decisions.md`, `session-handoff.md`를 대조해 env/state 역할 표현이 같은지 확인했다.
2. 이번 변경은 문서화 작업이라 테스트는 추가 실행하지 않았다.
- Next:
1. 다음 코드리뷰부터 env에 mutable routing을 source of truth로 두는 변경은 원칙 위반으로 바로 reject 기준에 올린다.
2. 새 기능이 채널/포럼 ID를 다룰 때는 먼저 state schema 확장으로 풀고, env는 bootstrap-only인지부터 확인한다.
- Status: done

## 2026-03-23
- Context: 사용자가 env channel IDs가 실운영에서 foreign fallback처럼 읽혀 다른 길드 heatmap이 깨진다고 보고했고, 어떤 라우팅 데이터가 state로 가야 하는지 전체 검토를 요청했다.
- Change:
1. `bot/features/runner.py`는 더 이상 `DEFAULT_FORUM_CHANNEL_ID`를 runtime fallback으로 읽지 않는다. heatmap 실행은 guild state의 `forum_channel_id`만 사용하고, 실제 channel이 같은 guild의 `ForumChannel`인지 검증한다.
2. `bot/features/intel_scheduler.py`도 `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`를 runtime fallback으로 쓰지 않게 바꿨다. 뉴스/EOD는 `news_forum_channel_id/eod_forum_channel_id -> forum_channel_id`, watch는 `watch_alert_channel_id`를 state에서만 읽는다.
3. `bot/app/bot_client.py`에는 startup bootstrap을 추가했다. legacy env channel IDs가 접근 가능하면 matching guild의 `data/state/state.json`에 한 번만 복사하고, 이미 state가 있으면 덮어쓰지 않는다.
4. `.env.example`, `README.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`도 `env bootstrap -> state authoritative` 의미로 갱신했다.
5. 회귀 테스트는 `tests/unit/test_bot_client.py`를 새로 추가해 bootstrap 동작을 고정했고, `tests/integration/test_forum_upsert_flow.py`, `tests/integration/test_intel_scheduler_logic.py`는 state-authoritative routing 기준으로 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_bot_client.py tests\integration\test_forum_upsert_flow.py tests\integration\test_intel_scheduler_logic.py tests\integration\test_auto_scheduler_logic.py -q` 통과
2. invalid-forum regression: state에 foreign/deleted forum channel이 남아 있으면 heatmap command는 `/setforumchannel` 재설정을 요구하는 메시지를 반환한다.
- Next:
1. 봇 재시작 후 startup bootstrap이 현재 `.env`의 channel IDs를 state에 옮기는지 확인한다.
2. 필요하면 다음 단계로 env channel IDs를 완전히 제거할지, 아니면 bootstrap-only legacy로 유지할지 운영 결정을 내린다.
- Status: done

## 2026-03-23
- Context: 사용자가 instrument registry 누락 종목군을 더 보강하고, bot 내부에서 매일 한 번 refresh할 수 있게 적용해 달라고 요청했다.
- Change:
1. `bot/intel/instrument_registry.py`는 이제 KRX structured finder의 `ELW`, `PF` rows도 빌드에 포함한다. 결과적으로 bundled registry counts는 `KRX=8131`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `15649`건으로 늘었다.
2. registry load 순서는 `data/state/instrument_registry.json -> bot/intel/data/instrument_registry.json -> seed`로 바뀌었고, `save_registry()`는 `atomic_write_json` 기반 atomic replace를 사용한다.
3. `registry_status()`는 active source(`runtime|bundled`)와 loaded counts를 함께 노출한다.
4. `bot/features/intel_scheduler.py`에는 `INSTRUMENT_REGISTRY_REFRESH_ENABLED`, `INSTRUMENT_REGISTRY_REFRESH_TIME` 기반 daily refresh job을 추가했다. refresh는 `asyncio.to_thread(...)`로 실행되고, live OpenDART/SEC/KRX fetch가 모두 성공했을 때만 runtime artifact를 교체한다.
5. refresh 결과는 `job_last_runs.instrument_registry_refresh`와 `provider_status.instrument_registry`에 `source=runtime loaded=... added=... removed=...` 형태로 남기고, 실패 시 기존 active registry는 유지한다.
6. `scripts/build_instrument_registry.py`, `.env.example`, `README.md`, `docs/specs/external-intel-api-spec.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`도 새 runtime override 구조와 refresh env를 기준으로 갱신했다.
7. 회귀 테스트는 ELW/PF builder/search, runtime override load, atomic save, status default row, scheduler refresh success/failure/timing까지 추가했다.
- Verification:
1. `$env:PYTHONPATH='.'; .\.venv\Scripts\python.exe scripts\build_instrument_registry.py` 성공 (`records=15649`)
2. registry spot-check:
   - `삼성전자 -> KRX:005930`
   - `KBL002삼성전자콜 -> KRX:58L002`
   - `대신 KOSPI200인덱스 X클래스 -> KRX:0106J0`
3. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_instrument_registry.py tests\unit\test_watch_command.py tests\unit\test_status_command.py tests\integration\test_intel_scheduler_logic.py -q` 통과
- Next:
1. runtime refresh는 기본값이 disabled이므로, 운영 env에서 켤 때 `DART_API_KEY`와 실행 시각을 함께 점검한다.
2. inactive/delisted marker와 watchlist reconciliation report는 다음 단계로 남는다.
- Status: done

## 2026-03-23
- Context: `develop` merge 직전 GitHub Codex review가 `bot/intel/providers/market.py` warm-up 경로에서 same-poll fallback을 막는 P2 3건을 보고했다.
- Change:
1. `KisMarketDataProvider.warm_quotes()`의 국내 종목 prefetch는 `_fetch_and_store()` 대신 best-effort `_warm_fetch_and_store()`를 사용하도록 바꿨다.
2. 그래서 국내 warm-up에서 일시적 KIS 오류가 나도 `_quote_errors`를 오염시키지 않고, 같은 poll cycle의 `get_quote()`가 단건 quote path를 다시 시도할 수 있다.
3. 해외 `multprice` warm-up도 row omission이나 stale/invalid row를 `_quote_errors`로 고정하지 않도록 보정했다.
4. `tests/unit/test_market_provider.py`에는 `stale batch -> single fallback`, `batch row omission -> single fallback`, `domestic warm failure -> single fallback` 회귀를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q` 통과
2. GitHub PR #14의 Codex review findings 기준으로 지적된 same-poll fallback blocker가 현재 코드에서 제거됐는지 재확인했다.
- Next:
1. 수정본을 push한 뒤 `@codex review`를 다시 요청하고 shipping flow를 재개한다.
2. review가 clean이면 `codex/live-watch-rollout-20260323 -> develop` merge를 완료한다.
- Status: done

## 2026-03-23
- Context: 사용자가 신규 상장 상품과 상장폐지 상품을 현재 autocomplete 구조에서 어떤 방식으로 체크할지 물었다.
- Change:
1. 현재 watch autocomplete가 live search가 아니라 generated registry snapshot 기준이라는 점을 다시 확인했다.
2. 신규 상장/상장폐지는 `registry rebuild 전까지 autocomplete에 반영되지 않음`을 현재 동작 기준으로 문서화했다.
3. 다음 운영 보강안으로 `정기 rebuild + 이전 registry와 diff + inactive/delisted 상태 관리 + watchlist reconciliation report`를 설계 기준으로 남겼다.
4. 이 판단은 `README.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`에 함께 반영했다.
- Verification:
1. `scripts/build_instrument_registry.py`가 OpenDART/SEC/KRX ETF/ETN source를 모아 generated artifact를 만드는 current flow를 다시 확인했다.
2. `/watch add` autocomplete와 `resolve_watch_add_symbol()`는 runtime에서 local registry만 읽고, guild state에 저장된 symbol은 registry와 별도로 유지된다는 점을 코드로 재확인했다.
- Next:
1. 실제 자동 추적이 필요해지면 daily refresh job과 old/new diff artifact부터 구현한다.
2. 그다음 inactive/delisted marker와 watchlist reconciliation report를 scheduler/status에 연결한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `KB 천연가스 선물 ETN(H)` 같은 ETN 상품도 `/watch add` autocomplete에서 검색돼야 한다고 보고했다.
- Change:
1. KRX structured finder 경로를 ETF 전용이 아니라 공통 fetch로 정리하고, `ETN` rows를 registry build에 포함시켰다.
2. `bot/intel/instrument_registry.py`에 `fetch_krx_etn_rows()`와 `build_krx_etn_records()`를 추가했고, structured finder `Referer`도 `mktsel`별로 동적으로 맞췄다.
3. `scripts/build_instrument_registry.py`는 이제 OpenDART 상장사 + SEC 미국 종목 + KRX ETF + KRX ETN을 함께 합쳐 generated registry를 만든다.
4. regenerated artifact 기준 registry counts는 `KRX=5382`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `12900`건이다.
5. `tests/unit/test_instrument_registry.py`에는 `KB 천연가스 선물 ETN(H)` 검색/ETN builder 회귀를, `tests/unit/test_watch_command.py`에는 ETN exact-name resolution 회귀를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe scripts/build_instrument_registry.py` 성공 (`records=12900`)
2. `load_registry().search("KB 천연가스 선물 ETN(H)", limit=5)` 결과 `KRX:580020 / score=900` 확인
3. `resolve_watch_add_symbol("KB 천연가스 선물 ETN(H)") -> KRX:580020`
4. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_instrument_registry.py tests\unit\test_watch_command.py -q` 통과
- Next:
1. KRX structured coverage는 이제 ETF에 더해 ETN까지 official finder 기준으로 본다.
2. 필요하면 같은 family로 ELW/PF도 추가 확장할 수 있다.
- Status: done

## 2026-03-23
- Context: 사용자가 ETF가 전혀 검색되지 않는다고 보고했고, 안 되면 autocomplete를 폐기하라고 요청했다.
- Change:
1. 원인을 확인한 결과 국내 registry는 OpenDART corpCode 기반 상장사만 들어 있고, KRX ETF master가 전혀 없었다.
2. `bot/intel/instrument_registry.py`에 KRX 공식 ETF finder endpoint(`dbms/comm/finder/finder_secuprodisu`) fetch/build 경로를 추가했다.
3. `scripts/build_instrument_registry.py`는 이제 OpenDART 상장사 + SEC 미국 종목 + KRX ETF를 함께 합쳐 generated registry를 만든다.
4. regenerated artifact 기준 registry counts는 `KRX=4994`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `12512`건이다.
5. ETF 유입으로 `삼성전자` 같은 exact stock query가 ETF 구성상품 때문에 ambiguity로 바뀌는 회귀가 생겨, `bot/features/watch/command.py`에서 score `>= 900` exact match가 하나면 자동 선택하도록 보정했다.
6. `tests/unit/test_instrument_registry.py`에 `KODEX 200` 검색 회귀를, `tests/unit/test_watch_command.py`에 ETF exact-name resolution 회귀를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe scripts/build_instrument_registry.py` 성공 (`records=12512`)
2. `resolve_watch_add_symbol("삼성전자") -> KRX:005930`
3. `resolve_watch_add_symbol("제주반도체") -> KRX:080220`
4. `resolve_watch_add_symbol("KODEX 200") -> KRX:069500`
5. `resolve_watch_add_symbol("TIGER 200") -> KRX:102110`
6. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_instrument_registry.py tests\unit\test_watch_command.py -q` 통과
- Next:
1. KRX ETF coverage는 이제 official finder 기반으로 본다.
2. 필요하면 이후 ETN/ELW/PF도 같은 KRX finder family로 확장할 수 있다.
- Status: done

## 2026-03-23
- Context: 사용자가 `제주반도체` 수준의 비주류 코스닥 종목도 `/watch add` autocomplete에서 검색되게 만들고, 그 정도가 안 되면 autocomplete를 폐기하라고 요청했다.
- Change:
1. 원인을 확인한 결과 `scripts/build_instrument_registry.py`가 repo `.env`를 읽지 않아 `DART_API_KEY`가 있어도 OpenDART corpCode를 registry build에 반영하지 못하고 있었다.
2. 스크립트에 `load_dotenv(REPO_ROOT / ".env")`를 추가해 `.env`의 `DART_API_KEY`를 자동으로 읽도록 수정했다.
3. generated registry artifact를 다시 빌드했고, 현재 counts는 `KRX=3914`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `11432`건이다.
4. `tests/unit/test_instrument_registry.py`에 `제주반도체` 검색 회귀를 추가했다.
5. `README.md`에도 registry build 스크립트가 `.env`의 `DART_API_KEY`를 자동으로 읽는다는 점을 반영했다.
- Verification:
1. `.\.venv\Scripts\python.exe scripts/build_instrument_registry.py` 성공 (`records=11432`)
2. `load_registry().search("제주반도체", limit=5)` 결과 `제주반도체 / KRX:080220 / score=900` 확인
3. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_instrument_registry.py tests\unit\test_watch_command.py -q` 통과
- Next:
1. watch autocomplete 기준선은 이제 seed 20종목이 아니라 OpenDART corpCode가 반영된 KRX artifact로 본다.
2. 향후 registry refresh 주기가 필요하면 같은 스크립트를 scheduled job으로 올리면 된다.
- Status: done

## 2026-03-23
- Context: 사용자가 남은 큰 작업인 `eod_summary` live 구현과 Massive fallback live 완료에 무엇이 필요한지 정리한 보고서를 요청했다.
- Change:
1. 현재 코드와 문서를 기준으로 두 작업의 선행조건, 구현 작업, 검증 작업, 운영 리스크를 다시 정리했다.
2. 결과는 `docs/reports/eod-massive-completion-report-2026-03-23.md`에 기록했다.
3. 정리 결과 `eod_summary`는 provider 구현보다 `KIS endpoint 조합 확정`이 핵심 blocker이고, Massive fallback은 `계정 entitlement + controlled live fallback smoke`가 핵심 blocker라는 점을 명시했다.
- Verification:
1. `bot/features/intel_scheduler.py`, `bot/intel/providers/market.py`, `bot/features/eod/policy.py`, `docs/specs/external-intel-api-spec.md`, `docs/reports/mvp-data-source-review-2026-03-12.md`를 대조해 gap을 확인했다.
2. Massive pricing/terms와 KIS 포털의 현재 공개 안내도 함께 확인해 외부 prerequisite를 문서에 반영했다.
- Next:
1. 실제 구현 우선순위는 `eod_summary` live provider -> Massive entitlement 확보 후 fallback live smoke 순서로 잡는다.
2. 구현에 들어갈 때는 report의 completion gate를 체크리스트로 사용한다.
- Status: done

## 2026-03-23
- Context: 사용자가 현재 변경분을 모두 커밋한 뒤 `origin/codex/watch-poll-live-quotes` 브랜치에서 가져올 만한 내용을 확인하고 합쳐 달라고 요청했다.
- Change:
1. 현재 워크트리를 `Roll out live watch quotes and provider docs` 커밋으로 먼저 고정했다.
2. `origin/codex/watch-poll-live-quotes`는 단일 커밋 `153e491 feat: use live quotes for watch poll`만 갖고 있었고, diff 검토 결과 실질적인 신규 가치는 `미국 종목 quote fallback routing`이었다.
3. 현재 구조에 맞게 `bot/intel/providers/market.py`에 `MarketDataProviderError`, `MassiveSnapshotMarketDataProvider`, `RoutedMarketDataProvider`를 추가했다.
4. `MARKET_DATA_PROVIDER_KIND=kis`일 때는 KIS를 primary로 유지하고, `MASSIVE_API_KEY`가 있으면 미국 종목에서만 Massive snapshot fallback을 시도하도록 `bot/features/intel_scheduler.py`를 보강했다.
5. 원격 브랜치의 `day.c`/`prevDay.c` 가격 fallback은 `watch_poll` 오탐 위험 때문에 가져오지 않고, `lastTrade` 기반 live price + freshness가 있는 경우만 Massive fallback을 허용했다.
6. `massive-entitlement-required` 오류를 명시적으로 드러내도록 Massive provider 오류 매핑을 넣었고, `.env.example`/`README.md`에도 entitlement 메모를 추가했다.
7. `tests/unit/test_market_provider.py`에는 Massive snapshot normalization과 routed fallback 회귀를, `tests/integration/test_intel_scheduler_logic.py`에는 builder/fallback provider status 회귀를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py tests\unit\test_status_command.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 통과
3. live smoke:
   - `quote_provider`는 현재 `RoutedMarketDataProvider`
   - KIS domestic quote(`KRX:005930`) 성공
   - Massive fallback direct call은 현재 env key 기준 `massive-entitlement-required`
   - controlled Discord `watch_poll` smoke는 다시 성공 (`watch_poll=ok`, alert send 1건 후 delete 1건)
- Next:
1. Massive plan entitlement가 준비되면 미국 종목 실제 fallback quote live smoke를 한 번 더 수행한다.
2. 현재는 KIS primary 경로가 정상이고, Massive는 optional fallback slot로만 열린 상태다.
- Status: done

## 2026-03-23
- Context: 사용자가 `.env` 값을 채운 뒤 `openfigi`를 제외한 나머지 API와 live watch 경로를 실제로 테스트해 달라고 요청했다.
- Change:
1. `.env` 기준 전체 회귀를 다시 실행했고 `.\.venv\Scripts\python.exe -m pytest -q`가 전부 통과하는지 확인했다.
2. live smoke 중 KIS token endpoint가 `접근토큰 발급 잠시 후 다시 시도하세요(1분당 1회)`로 403을 돌려주는 경우가 있었고, 기존 `bot/intel/providers/market.py`는 이를 전부 `kis-auth-failed`로 오분류하던 문제를 수정했다.
3. `_request_json_sync()`는 이제 HTTP 403 body의 `error_code`/`error_description`를 읽어 `EGW00133` 같은 token 발급 rate limit을 `kis-rate-limited`로 분리한다.
4. `tests/unit/test_market_provider.py`에 token issue 403 body가 `kis-rate-limited`로 매핑되는 회귀 테스트를 추가했다.
5. env/live 검증은 다음 순서로 다시 수행했다: DART corpCode zip fetch, Massive ticker reference fetch, TwelveData quote fetch, Naver provider analyze, Marketaux provider analyze, runtime hybrid news analyze, KIS domestic quote fetch, Discord `watch_poll` send/delete smoke.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 통과
3. live env smoke 결과:
   - DART `corpCode.xml` zip fetch 성공
   - Massive reference ticker(`AAPL`) fetch 성공
   - TwelveData `quote(AAPL)` 성공
   - Naver provider analyze 성공 (`briefing_items=8 domestic=3 global=5`)
   - Marketaux provider analyze 성공 (`briefing_items=3 global=3`)
   - runtime hybrid news analyze 성공 (`briefing_items=19 domestic=16 global=3`)
   - KIS + Discord `watch_poll` smoke 성공 (`run_status=ok`, `kis_quote.ok=True`, alert send 1건 후 즉시 delete 1건)
4. Discord 채널 타입 검증도 다시 성공했다: `WATCH_ALERT_CHANNEL_ID`, `ADMIN_STATUS_CHANNEL_ID`는 `TextChannel`, `NEWS_TARGET_FORUM_ID`/`EOD_TARGET_FORUM_ID`는 `ForumChannel`이다.
- Next:
1. 현재 guild `332110589969039360`의 실제 watch route는 env fallback이 아니라 stored `watch_alert_channel_id=460011902043553792` override를 사용한다. env fallback(`1483007026023108739`)로 통일할지 운영에서 결정한다.
2. KIS token issuance는 공급자 제약상 분당 1회라, smoke나 multi-process 진단 시 provider instance를 불필요하게 여러 개 만들지 않도록 주의한다.
- Status: done

## 2026-03-23
- Context: 사용자가 남아 있던 reviewer P2인 KIS warm-up fallback 문제도 이어서 수정해 달라고 요청했다.
- Change:
1. `bot/intel/providers/market.py`의 `_warm_overseas_chunk()`는 batch `multprice` fetch 자체가 실패하거나 batch payload shape가 깨졌을 때 더 이상 chunk 전체 symbol을 `_quote_errors`로 오염시키지 않는다.
2. 이 경우 symbol을 uncached 상태로 남겨 같은 poll cycle의 `get_quote()`가 single-symbol `price` endpoint로 fallback할 수 있게 했다.
3. `tests/unit/test_market_provider.py`에 batch warm-up failure 뒤 single-symbol quote fetch로 회복하는 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q` 통과
- Next:
1. 최신 subagent review에서 지적된 P2/P3는 모두 닫혔고, 남은 큰 검증 항목은 live KIS/Discord smoke다.
- Status: done

## 2026-03-23
- Context: 사용자가 review finding으로 올라온 `/source-status` legacy quote-provider drift를 수정해 달라고 요청했다.
- Change:
1. `bot/features/status/command.py`에 legacy provider alias map을 추가해 `market_data_provider -> kis_quote`, `polygon_reference -> massive_reference`를 같은 경로에서 정규화하도록 정리했다.
2. `_merge_defaults()`는 이제 legacy key와 canonical key가 동시에 있을 때 canonical key 값을 우선한다. 그래서 기존 state 파일에 `market_data_provider`가 남아 있어도 `kis_quote` row 하나만 보이고, stale legacy row가 현재 runtime status를 덮어쓰지 않는다.
3. `tests/unit/test_status_command.py`에 `market_data_provider` 정규화와 canonical-precedence 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_status_command.py -q`
2. 결과는 `6 passed`였다.
- Next:
1. 현재 reviewer finding 중 남은 open 항목은 `bot/intel/providers/market.py`의 warm-up failure가 per-symbol fallback까지 막는 P2 하나다.
- Status: done

## 2026-03-23
- Context: `Polygon.io -> Massive` 브랜드 변경을 현재 저장소의 user-facing 문서와 env/status 이름에 반영하는 작업
- Change:
1. `bot/app/settings.py`는 이제 `MASSIVE_API_KEY`를 우선 읽고, legacy `POLYGON_API_KEY`를 fallback으로 허용한다.
2. `bot/features/status/command.py`의 기본 provider row key를 `massive_reference`로 바꾸고, 과거 state의 `polygon_reference`는 표시 단계에서 canonical key로 승격하도록 맞췄다.
3. `.env.example`, `README.md`, `AGENTS.md`, context docs, `docs/reports/mvp-data-source-review-2026-03-12.md`를 `Massive` 또는 `Massive (구 Polygon.io)` 기준으로 정리했다.
4. `tests/unit/test_status_command.py`는 새 key와 legacy alias 정규화 동작에 맞춰 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_status_command.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 통과
3. rename 범위는 user-facing 문서/env/status 위주로 제한했고, 내부 `instrument_registry`의 `polygon_primary_exchange` 필드는 이번 작업에서 유지한다.
- Next:
1. Massive 실제 adapter를 붙일 때 user-facing 명칭은 `Massive`, 내부 alias는 legacy compatibility로만 유지한다.
- Status: done

## 2026-03-23
- Context: 사용자가 현재 워크트리 변경분에 대해 `integration_tester`와 `reviewer` subagent를 각각 생성해 실행해 달라고 요청했다.
- Change:
1. read-only `integration_tester` subagent를 띄워 `.\.venv\Scripts\python.exe -m pytest tests/integration` 전체 suite를 실행했다.
2. read-only `reviewer` subagent를 띄워 현재 diff를 검토하게 했고, 추가로 `tests\unit\test_market_provider.py`와 `tests\integration\test_intel_scheduler_logic.py` targeted suite를 다시 실행해 KIS/watch 경로를 좁혀 확인했다.
3. 메인 세션에서는 `docs/context/review-rules.md`, 현재 `git status`, 관련 diff를 직접 대조해 subagent 결과를 교차 확인했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration` 결과는 `45 passed, 2 deselected`였다.
2. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q`는 reviewer subagent 기준 통과했다.
- Next:
1. `bot/intel/providers/market.py`에서 batch warm-up 실패 후에도 single-symbol fetch로 회복 가능한 경로를 남기도록 `_quote_errors` 처리 순서를 보정한다.
2. `bot/features/status/command.py` 또는 state migration 쪽에서 legacy `market_data_provider` row가 `/source-status`에 남지 않게 정리한다.
- Status: open

## 2026-03-23
- Context: 사용자가 현재 로컬 `develop`을 원격 저장소와 다시 맞추고, 최신 기준의 다음 작업 우선순위를 파악해 달라고 요청했다.
- Change:
1. `git fetch --prune origin` 후 로컬 `develop`의 미푸시 커밋 1개를 최신 `origin/develop` 위로 rebase해 원격 11커밋을 반영했다.
2. rebase 중 충돌 난 [AGENTS.md](C:/Users/kin50/Documents/New%20project/discord-heatmap-bot-trading-calendar/AGENTS.md)와 [docs/context/design-decisions.md](C:/Users/kin50/Documents/New%20project/discord-heatmap-bot-trading-calendar/docs/context/design-decisions.md)는 최신 원격 문맥을 유지하면서 로컬의 상태 경로 정리 기록만 보존하도록 정리했다.
3. 최신 코드 기준 다음 구현 우선순위를 다시 점검한 결과, [bot/features/intel_scheduler.py](C:/Users/kin50/Documents/New%20project/discord-heatmap-bot-trading-calendar/bot/features/intel_scheduler.py)는 뉴스 provider만 `mock|naver|marketaux|hybrid` 전환을 지원하고, `eod_provider`와 `quote_provider`는 여전히 `MockEodSummaryProvider()`, `MockMarketDataProvider()`로 고정돼 있음을 확인했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest`
2. 결과는 `107 passed, 2 deselected`였다.
- Next:
1. 원격 운영 검증 관점의 최우선 다음 작업은 `WATCH_ALERT_CHANNEL_ID`를 실제 text channel로 바로잡고, live `MarketDataProvider`를 붙여 `watch add -> poll -> alert send` 경로를 실사용 기준으로 닫는 것이다.
2. `eod_summary`는 현재 spec/설계 문서 기준으로 pause 상태이므로, 우선순위를 다시 올리기 전까지는 watch/news 쪽 검증과 운영 안정화가 먼저다.
- Status: done

## 2026-03-22
- Context: 사용자가 `master` 반영 직후 Docker 배포와 compose 점검을 요청했다.
- Change:
1. [docker-compose.yml](C:/Users/kin50/Documents/test/docker-compose.yml)에 `./data/state:/app/data/state` bind mount를 추가했다.
2. 이유는 현재 앱 runtime state 경로가 `data/state/state.json`인데, 기존 compose는 `data/heatmaps`와 `data/logs`만 마운트해 컨테이너 recreate 시 state가 유실될 수 있었기 때문이다.
3. Docker Desktop daemon을 올린 뒤 `docker compose up -d --build`로 `discord-heatmap-bot` 컨테이너를 새 이미지로 recreate 했다.
- Verification:
1. `docker compose config`로 compose 문법과 bind mount 구성이 유효한지 확인했다.
2. `docker compose ps` 기준 `discord-heatmap-bot`이 새 컨테이너로 `Up` 상태다.
3. `data/logs/bot.log` 기준 `2026-03-22 22:26:43`에 `11 commands synced`, `Auto screenshot scheduler started`, `Intel scheduler started`, `Logged in as Drumstick#9496`가 기록됐다.
4. `data/state/state.json`의 `system.job_last_runs.command-sync.status=ok`, `detail=11 commands synced`와 `watch_poll=no-watch-symbols`가 새 컨테이너 기동 직후 시각으로 갱신된 것을 확인했다.
5. `docker inspect discord-heatmap-bot` 기준 bind mount는 `data/heatmaps`, `data/state`, `data/logs` 3개가 모두 연결됐다.
- Next:
1. env 기준 `WATCH_ALERT_CHANNEL_ID`, `ADMIN_STATUS_CHANNEL_ID` 운영값은 별도 Discord smoke 결과대로 여전히 점검 대상이다.
- Status: done

## 2026-03-22
- Context: 사용자가 env의 채널/포럼 ID를 새로 바꾼 뒤 실제 Discord 검증을 다시 요청했다.
- Change:
1. 업데이트된 env 기준으로 `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`, `ADMIN_STATUS_CHANNEL_ID`를 다시 읽고 실제 Discord에서 fetch 검증을 수행했다.
2. `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`는 모두 같은 forum 채널(`1471842980787917005`)을 가리키는 것을 확인했고, 해당 forum에 `discord-env-smoke-default_forum-news_forum-eod_forum` key로 thread 생성 1회와 update 1회를 다시 수행했다.
3. `WATCH_ALERT_CHANNEL_ID`도 같은 forum 채널을 가리키고 있어, watch poll 코드가 기대하는 `discord.abc.Messageable` 텍스트 채널 fallback으로는 사용할 수 없다는 점을 실제 채널 타입 확인으로 검증했다.
4. `ADMIN_STATUS_CHANNEL_ID`는 fetch 시 `403 Missing Access`가 발생해 현재 봇이 그 채널을 읽을 권한조차 갖고 있지 않음을 확인했다.
- Verification:
1. Discord login, Gateway 연결, 글로벌 slash command 11개 sync 재확인.
2. forum env smoke 결과: [default/news/eod forum smoke thread](https://discord.com/channels/332110589969039360/1485250008847614035) 생성 후 즉시 update 성공.
3. watch alert env 결과: forum 채널이라 send smoke를 의도적으로 건너뛰었고, 현재 코드 기준 `watch_alert` fallback으로는 부적합하다는 점을 확인.
4. admin status env 결과: `fetch_channel(1483007026023108739)`가 `403 Forbidden (50001 Missing Access)`로 실패.
- Next:
1. `WATCH_ALERT_CHANNEL_ID`는 forum이 아니라 같은 guild의 일반 text channel 또는 thread/messageable channel로 바꿔야 실제 watch alert fallback이 동작한다.
2. `ADMIN_STATUS_CHANNEL_ID`를 계속 쓸 계획이면 해당 채널에 봇 접근 권한을 먼저 열어야 한다.
- Status: done

## 2026-03-22
- Context: 사용자가 "실제 디스코드까지 실행"하는 live 검증을 요청했다.
- Change:
1. 실제 `.env`의 `DISCORD_BOT_TOKEN`과 `DEFAULT_FORUM_CHANNEL_ID`를 사용해 봇을 Discord Gateway에 로그인시키고, `tree.sync()`가 11개 글로벌 커맨드를 정상 동기화하는지 확인했다.
2. 검증 중 scheduler 부작용을 막기 위해 ad-hoc 부트 스크립트에서는 `auto_screenshot_scheduler`, `intel_scheduler`를 no-op으로 바꿔 짧게 부트했다.
3. 실제 기본 포럼 채널 fallback 경로를 사용해 `discord_live_smoke` key로 forum thread를 1회 생성하고, 같은 thread를 즉시 1회 업데이트해 Discord forum upsert의 create/update 경로를 모두 확인했다.
4. 실제 캡처 이미지 첨부까지 포함해 end-to-end로 확인하기 위해 `kospi` live capture를 수행했고, 생성된 PNG 파일 크기는 `207749` bytes였다.
5. 추가 검증으로 `.\.venv\Scripts\python.exe -m pytest -m live -q`를 실행해 live capture suite 2건도 모두 통과했다.
- Verification:
1. ad-hoc Discord 부트 결과: login 성공, guild 2개 인식, 기본 포럼 채널 fetch 성공, forum posting 관련 권한(`view_channel`, `send_messages`, `send_messages_in_threads`, `create_public_threads`, `manage_threads`, `attach_files`) 확인.
2. command sync 결과: `setforumchannel`, `setnewsforum`, `seteodforum`, `setwatchchannel`, `autoscreenshot`, `health`, `last-run`, `source-status`, `watch`, `kheatmap`, `usheatmap` 총 11개 글로벌 커맨드 sync 성공.
3. 실제 forum upsert 결과: `discord_live_smoke` thread 생성 1회, 같은 thread update 1회 성공.
4. `.\.venv\Scripts\python.exe -m pytest -m live -q` 결과: `2 passed`.
- Next:
1. 이번 검증은 실제 bot login/sync/forum posting까지는 포함했지만, slash interaction 자체를 Discord 사용자 클라이언트에서 눌러 실행한 것은 아니므로 필요하면 운영 서버에서 `/kheatmap` 또는 `/health`를 직접 한 번 더 눌러 interaction 경로를 마저 확인한다.
2. `data/state/state.json`에는 `discord_live_smoke` 오늘자 thread record가 남아 있으니, 같은 key를 다시 쓸지 정리할지 다음 운영 판단에서 결정한다.
- Status: done

## 2026-03-22
- Context: 사용자가 통합 테스트를 실행하거나 검토할 때 바로 참조할 수 있는 상세 케이스 문서를 요청했다.
- Change:
1. [docs/specs/integration-test-cases.md](C:/Users/kin50/Documents/test/docs/specs/integration-test-cases.md)를 추가해 현재 non-live 통합 테스트 43건을 기능 계약 단위로 문서화했다.
2. [docs/specs/integration-live-test-cases.md](C:/Users/kin50/Documents/test/docs/specs/integration-live-test-cases.md)를 추가해 live 캡처 2건을 별도 관리하도록 분리했다.
3. [README.md](C:/Users/kin50/Documents/test/README.md)와 [AGENTS.md](C:/Users/kin50/Documents/test/AGENTS.md) 테스트 가이드에 새 문서 링크를 추가했다.
4. source truth인 현재 `tests/integration/test_intel_scheduler_logic.py` 기준 실제 분포가 `NB 12`, `TR 4`, `EO 8`, `WP 5`라서, 초안 계획의 `NB 13`/`EO 7` 대신 source 수에 맞춘 번호 체계를 사용했다.
- Verification:
1. `pytest.ini`의 `-m "not live"` 규칙과 live marker 문구를 문서에 반영했는지 확인한다.
2. 문서 매핑 수는 non-live 43건, live 2건으로 맞췄다.
3. `README.md`와 `AGENTS.md`에서 새 문서 경로가 정확히 연결되는지 교차 확인한다.
- Next:
1. integration 테스트가 추가되면 먼저 source test 수와 marker를 업데이트하고, 같은 날 문서 케이스 매핑도 같이 갱신한다.
2. 누락 고위험 케이스 섹션에 적어 둔 항목부터 실제 회귀 테스트 후보로 순차 반영한다.
- Status: done

## 2026-03-22
- Context: 사용자가 기능 전체 통합 테스트 전용 subagent를 새로 만들고, 실제로 그 agent 역할로 테스트를 돌려 달라고 요청했다.
- Change:
1. [`.codex/agents/integration-tester.toml`](C:/Users/kin50/Documents/test/.codex/agents/integration-tester.toml)을 추가해 `integration_tester` custom agent를 정의했다.
2. 이 agent는 `workspace-write` sandbox에서 동작하고, 테스트나 검증 요청 시 항상 `.\.venv\Scripts\python.exe -m pytest tests/integration` 전체 suite를 먼저 실행하도록 developer instructions를 고정했다.
3. [AGENTS.md](C:/Users/kin50/Documents/test/AGENTS.md)에 `integration_tester` 역할과 "부분 테스트 대체 금지, 전체 integration 우선" 규칙을 추가했다.
- Verification:
1. `tomllib`로 [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml)과 `.codex/agents/*.toml` 전체 파싱 성공을 확인한다.
2. worker subagent를 `integration_tester` 역할로 실행해 `.\.venv\Scripts\python.exe -m pytest tests/integration`를 실제로 수행했고, 결과는 `43 passed, 2 deselected`였다.
- Next:
1. 다음 세션에서 통합 검증이 필요하면 `integration_tester`를 먼저 호출하고, targeted test는 full integration 이후 추가로만 수행한다.
- Status: done

## 2026-03-22
- Context: PR `#12`의 Codex review가 auto screenshot success 후 `load_state()`를 다시 읽는 보완에 새로운 data-loss 경로가 있다고 지적했다.
- Change:
1. [bot/features/auto_scheduler.py](C:/Users/kin50/Documents/test/bot/features/auto_scheduler.py)에 `_should_skip_last_auto_run_save(...)` 가드를 추가해, refresh read가 비정상적인 empty state로 돌아오면 `last_auto_runs`를 다시 저장하지 않고 warning만 남기도록 조정했다.
2. 이 변경으로 state refresh가 `JSONDecodeError`/`OSError` 등으로 실패해 empty state를 돌려주는 순간에도, runner가 이미 저장한 `daily_posts_by_guild`/`last_images`를 near-empty save로 덮어쓰지 않게 됐다.
3. [tests/integration/test_auto_scheduler_logic.py](C:/Users/kin50/Documents/test/tests/integration/test_auto_scheduler_logic.py)에 refresh read가 empty state를 반환할 때 scheduler가 추가 save를 하지 않고 기존 daily post state를 유지하는 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_auto_scheduler_logic.py -q`
- Next:
1. 이 수정 커밋을 PR `#12`에 반영하고 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-22
- Context: 사용자가 auto screenshot state 유실 fix를 실제 디스크 쓰기 흐름까지 검증해 달라고 요청했다.
- Change:
1. 별도 임시 state 파일을 두고 `process_auto_screenshot_tick()`을 isolated 환경에서 실행해, runner가 먼저 저장한 `daily_posts_by_guild`와 `last_images`가 scheduler의 `last_auto_runs` 기록 뒤에도 유지되는지 확인했다.
2. 실 Discord API 호출은 생략하고, `execute_heatmap_for_guild()`만 동일 tick 안에서 state를 먼저 저장하는 형태로 대체해 on-disk 경쟁 구도를 재현했다.
- Verification:
1. `.\.venv\Scripts\python.exe -`로 ad-hoc 검증 스크립트를 실행해 최종 `state.json`에 `commands.kheatmap.daily_posts_by_guild`, `commands.kheatmap.last_images`, `guilds.1.last_auto_runs.kheatmap`가 함께 남는 것을 확인했다.
- Next:
1. live 운영 검증이 필요하면 봇 재기동 후 실제 auto tick에서 `data/state/state.json`과 운영 로그를 같이 확인한다.
- Status: done

## 2026-03-22
- Context: 사용자가 project custom agent 기본 사용 패턴을 앞으로 재사용 가능한 운영 규칙으로 문서화해 달라고 요청했다.
- Change:
1. [AGENTS.md](C:/Users/kin50/Documents/test/AGENTS.md)에 `Codex Subagent 운영 규칙` 섹션을 추가했다.
2. 기본 3-agent 패턴을 `repo_explorer + reviewer + docs_researcher`로 명시했고, 새 스레드 1회 명시 후 같은 스레드에서는 축약 표현으로 재사용 가능한 약속을 적었다.
3. [docs/context/design-decisions.md](C:/Users/kin50/Documents/test/docs/context/design-decisions.md)와 [docs/context/session-handoff.md](C:/Users/kin50/Documents/test/docs/context/session-handoff.md)에 같은 규칙의 이유와 현재 상태를 반영했다.
- Verification:
1. app UI 기준 `repo_explorer`, `reviewer`, `docs_researcher` custom agent가 모두 생성되는 것을 확인했다.
2. 문서 간 규칙이 모순되지 않도록 [AGENTS.md](C:/Users/kin50/Documents/test/AGENTS.md), [docs/context/design-decisions.md](C:/Users/kin50/Documents/test/docs/context/design-decisions.md), [docs/context/session-handoff.md](C:/Users/kin50/Documents/test/docs/context/session-handoff.md)를 교차 확인했다.
- Next:
1. 다음 새 스레드에서는 subagent 사용 의사를 한 번만 밝히면, 같은 스레드 안에서는 `기본 3-agent 패턴` 같은 축약 표현으로 재사용한다.
- Status: done

## 2026-03-22
- Context: app UI smoke test에서 `repo_explorer`와 `reviewer`는 생성됐지만 `docs_researcher`만 `unknown agent_type`로 거절됐다.
- Change:
1. [`.codex/agents/docs-researcher.toml`](C:/Users/kin50/Documents/test/.codex/agents/docs-researcher.toml)에서 `web_search = "live"`를 제거했다.
- Why:
1. 현재 custom agent 3개 중 `docs_researcher`만 이 키를 추가로 사용했고, 나머지 두 agent는 정상 생성됐다.
2. 공식 subagent 문서의 custom agent 예시는 `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config` 중심이며, 이번 수정은 unsupported/partially-supported key 가능성을 제거하는 호환성 우선 조치다.
- Verification:
1. `tomllib` 기준 [`.codex/agents/docs-researcher.toml`](C:/Users/kin50/Documents/test/.codex/agents/docs-researcher.toml) 파싱은 계속 성공한다.
2. 이후 app UI에서 `docs_researcher`도 정상 생성되는 것을 확인했다.
- Next:
1. 비슷한 custom agent 등록 문제가 다시 나오면 unsupported key 여부를 먼저 점검한다.
- Status: done

## 2026-03-22
- Context: 사용자가 Codex app 재시작과 새 desktop thread 생성 후 project custom agent smoke test를 다시 실행해 달라고 요청했다.
- Change:
1. 코드나 설정 파일은 수정하지 않고, 기존 [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml) 및 [`.codex/agents/repo-explorer.toml`](C:/Users/kin50/Documents/test/.codex/agents/repo-explorer.toml), [`.codex/agents/reviewer.toml`](C:/Users/kin50/Documents/test/.codex/agents/reviewer.toml), [`.codex/agents/docs-researcher.toml`](C:/Users/kin50/Documents/test/.codex/agents/docs-researcher.toml) 기준으로 runtime smoke test만 재실행했다.
- Verification:
1. `Get-Command codex`와 `where.exe codex`로 Codex desktop 번들 실행 파일 경로가 `C:\Program Files\WindowsApps\OpenAI.Codex_26.313.5234.0_x64__2p2nqsd0c76g0\app\resources\codex.exe`로 해석되는 것을 다시 확인했다.
2. `codex --version`, `codex --help`는 둘 다 `Access is denied`로 실패해 shell 기반 smoke test는 여전히 불가능했다.
3. developer `spawn_agent`에 `repo_explorer`, `reviewer`, `docs_researcher`를 각각 넣어 다시 호출했지만 모두 `unknown agent_type`로 실패했다.
4. control로 built-in `explorer` subagent를 띄웠을 때는 [`bot/main.py`](C:/Users/kin50/Documents/test/bot/main.py)를 엔트리포인트로 응답해, desktop thread의 일반 subagent 경로 자체는 계속 정상임을 확인했다.
5. Codex app 로컬 로그 [`codex-desktop-1c769110-b0a4-4a47-8779-b5a6f2f5ca94-12756-t0-i1-034007-0.log`](C:/Users/kin50/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/Codex/Logs/2026/03/22/codex-desktop-1c769110-b0a4-4a47-8779-b5a6f2f5ca94-12756-t0-i1-034007-0.log)에는 `[StdioConnection] stdio_transport_spawned`와 `[AppServerConnection] Codex CLI initialized`가 남아 있어, Electron app 자체는 bundled `codex.exe`를 stdio로 띄우는 데 성공함을 확인했다.
- Next:
1. custom agent는 현재 이 대화/tool runtime에서 노출되지 않으므로, 실제 검증은 Codex app UI의 custom agent 선택 경로에서 직접 실행해 봐야 한다.
2. 필요하면 project custom agents가 desktop UI에 로드되는지와 developer `spawn_agent` 노출 범위가 다른지 분리해서 추가 조사한다.
- Status: done

## 2026-03-22
- Context: 사용자가 project-scoped Codex 설정을 현재 저장소 작업 방식에 맞게 전체적으로 정리해 달라고 요청했다.
- Change:
1. [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml)에 기본 모델(`gpt-5.3-codex`), 기본 reasoning/verbosity, `personality = "pragmatic"`, `plan_mode_reasoning_effort = "high"`, `web_search = "cached"`, `project_doc_max_bytes = 16384`를 추가했다.
2. 같은 파일의 `[agents]`는 `max_threads = 4`, `max_depth = 1`, `job_max_runtime_seconds = 1800`으로 조정해 현재 custom agent 3종을 병렬로 쓰되 과도한 fan-out은 막는 방향으로 맞췄다.
3. [`.codex/agents/repo-explorer.toml`](C:/Users/kin50/Documents/test/.codex/agents/repo-explorer.toml), [`.codex/agents/reviewer.toml`](C:/Users/kin50/Documents/test/.codex/agents/reviewer.toml), [`.codex/agents/docs-researcher.toml`](C:/Users/kin50/Documents/test/.codex/agents/docs-researcher.toml)에 각각 역할별 모델과 reasoning 강도를 명시했다.
4. `docs_researcher`는 문서 검증 작업의 최신성 요구가 높아 `web_search = "live"`를 별도로 설정했다.
- Verification:
1. Python `tomllib`로 [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml)과 `.codex/agents/*.toml` 전부 파싱 성공을 확인한다.
2. 공식 OpenAI Codex 문서 기준 `model`, `model_reasoning_effort`, `model_verbosity`, `personality`, `plan_mode_reasoning_effort`, `web_search`, `project_doc_max_bytes`, `[agents].max_threads|max_depth|job_max_runtime_seconds`가 유효 키인지 대조했다.
3. built-in `explorer` subagent 생성은 성공해 현재 thread의 multi-agent 경로 자체는 살아 있음을 확인했다.
4. 반면 `spawn_agent`는 project custom agent 이름(`repo_explorer`, `reviewer`, `docs_researcher`)을 인식하지 않았고, PowerShell/`cmd`에서 `codex --help` 실행도 `Access is denied`로 막혀 실제 custom-agent runtime smoke test는 수행하지 못했다.
- Next:
1. Codex app을 재시작하거나 custom agents를 직접 선택할 수 있는 UI 경로에서 `repo_explorer`, `reviewer`, `docs_researcher`를 한 번씩 호출해 runtime smoke test를 다시 수행한다.
2. 병렬 탐색이 잦아 대기열이 느껴지면 `max_threads`를 `5`나 `6`으로 올릴지 다시 판단한다.
- Status: done

## 2026-03-20
- Context: `origin/develop`를 fast-forward 한 뒤, 운영 조사에서 드러난 auto screenshot state 유실 가능성을 로컬 `develop`에도 반영했다.
- Change:
1. 로컬 `develop`를 `git pull --ff-only origin develop`으로 `2a69fcd codex/watch registry hybrid news (#11)`까지 올렸다.
2. `bot/features/auto_scheduler.py`는 auto screenshot 성공 후 scheduler metadata를 쓰기 전에 `load_state()`를 다시 호출해, runner가 같은 tick에서 저장한 daily post/cache state를 덮어쓰지 않도록 보완했다.
3. `tests/integration/test_auto_scheduler_logic.py`에 runner가 먼저 오늘자 thread/message state를 저장한 뒤 scheduler가 `last_auto_runs`만 추가하는 회귀 테스트를 넣었다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_auto_scheduler_logic.py -q`
2. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_auto_scheduler_logic.py tests/integration/test_forum_upsert_flow.py -q` 기준 `13 passed`
3. ad-hoc `scheduler -> manual` 재현 시나리오에서 `CREATE_CALLS=1`, `kheatmap 포스트 수정 완료`를 확인해 같은 날짜 thread가 새로 생성되지 않고 수정 경로를 타는 것을 확인했다.
- Next:
1. 필요하면 `origin/codex/fix-auto-screenshot-state`와 현재 로컬 적용분을 기준으로 PR/브랜치 정리를 이어간다.
2. 실제 운영 재기동 후 오늘자 auto screenshot tick에서 `daily_posts_by_guild`와 `last_auto_runs`가 함께 남는지 한 번 더 확인한다.
- Status: done

## 2026-03-20
- Context: 사용자가 KIS 단독 전략의 한계를 보완하되, 당장은 watch 종목명 추가를 우선하고 `eod_summary`는 pause 하길 원했다.
- Change:
1. `bot/intel/instrument_registry.py`, `scripts/build_instrument_registry.py`, `bot/intel/data/instrument_registry*.json`을 추가해 local instrument registry 계층과 generated artifact 흐름을 만들었다.
2. 현재 generated registry는 국내 seed 20종목 + SEC 미국 상장사 7,518건을 합친 7,538건이며, watch 입력은 이를 기준으로 canonical symbol(`KRX:005930`, `NAS:AAPL`)로 정규화된다.
3. `bot/forum/repository.py`는 watchlist/baseline/cooldown의 legacy 값(`005930`, bare US ticker)을 읽을 때 canonical symbol로 자동 승격하고 상태 키도 함께 마이그레이션한다.
4. `bot/features/watch/command.py`는 `/watch add`, `/watch remove`에 autocomplete와 ambiguity handling을 추가했고, `/watch list`와 watch alert는 이제 `이름 + canonical symbol` 형식으로 보여준다.
5. `bot/intel/providers/news.py`에는 `MarketauxNewsProvider`와 `HybridNewsProvider`를 추가했고, `bot/features/intel_scheduler.py`는 `NEWS_PROVIDER_KIND=marketaux|hybrid`와 source별 provider status 기록을 지원한다.
6. `bot/features/status/command.py`는 `instrument_registry`, `kis_quote`, `naver_news`, `marketaux_news`, `massive_reference`, `twelvedata_reference`, `openfigi_mapping`, `eod_provider`의 configured/disabled/paused 상태를 합성해서 보여준다.
7. `bot/app/settings.py`, `.env.example`, `README.md`, `docs/specs/external-intel-api-spec.md`, `AGENTS.md`를 새 provider key, registry 흐름, watch name search, `EOD_SUMMARY_ENABLED=false` 기본값에 맞춰 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe scripts/build_instrument_registry.py` 기준 generated registry artifact 생성 성공 (`records=7538`)
2. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_instrument_registry.py tests/unit/test_watch_command.py tests/unit/test_watchlist_repository.py tests/unit/test_watch_cooldown.py tests/unit/test_status_command.py tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py -q` 기준 전체 통과
3. `.\.venv\Scripts\python.exe -m pytest -q` 기준 전체 통과
- Next:
1. DART API key를 넣고 registry를 다시 생성하면 국내 종목명 커버리지를 full master로 넓힐 수 있다.
2. 실제 운영 전 `NEWS_PROVIDER_KIND=hybrid`와 `MARKETAUX_API_TOKEN`을 넣고 global news fetch 품질을 1회 실반영 검증한다.
3. `Massive`(구 `Polygon.io`)/`Twelve Data`/`OpenFIGI`는 현재 source-status slot만 열려 있으므로, 다음 단계에서 US fallback quote와 reconciliation job으로 확장한다.
- Status: done

## 2026-03-20
- Context: 사용자가 runtime state 파일은 heatmap 캐시와 분리하고, 외부 참고문서는 한 디렉터리에 모이길 원했다.
- Change:
1. state 기본 경로를 `data/heatmaps/state.json`에서 `data/state/state.json`으로 옮겼다.
2. `bot/forum/repository.py`는 새 경로를 기본으로 쓰되, 기존 `data/heatmaps/state.json`이 남아 있으면 자동으로 새 위치로 옮기도록 레거시 마이그레이션을 추가했다.
3. `docs/references/external/README.md`를 추가해 외부 벤더 문서/스프레드시트/PDF의 단일 보관 위치를 만들었다.
4. `.gitignore`, `AGENTS.md`, `README.md`, `docs/context/goals.md`를 새 state 경로와 외부 참고문서 위치 기준으로 갱신했다.
5. 워크스페이스에 남아 있던 `data/heatmaps/state.json`과 외부 참고 xlsx도 각각 `data/state/state.json`, `docs/references/external/` 기준으로 정리했다.
- Verification:
1. `tests/unit/test_state_atomic.py`에 legacy state 파일이 새 경로로 마이그레이션되는 회귀 테스트를 추가했다.
2. `.\.venv\Scripts\python.exe -m pytest` 기준 `89 passed, 2 deselected`
- Status: done

## 2026-03-20
- Context: 사용자가 앞으로의 약속은 모두 문서화하고, 특히 `develop -> master` 릴리스는 release branch 없이 direct PR로 고정하길 원했다.
- Change:
1. `AGENTS.md`에 새 운영 약속은 공통 규칙과 컨텍스트 문서에 함께 남긴다는 문서화 규칙을 추가했다.
2. 같은 문서에 `develop -> master` 릴리스는 앞으로 `develop`에서 바로 `master`로 PR을 연다는 브랜치 운영 약속을 추가했다.
3. `docs/context/design-decisions.md`에 이번 release branch 역동기화 경험을 근거로 direct PR 정책을 설계 결정으로 남겼다.
4. `docs/context/session-handoff.md`에 `PR #10` merge 완료와 현재 direct PR 약속을 최신 상태로 반영했다.
- Verification:
1. 문서 간 기준이 서로 모순되지 않도록 `AGENTS.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`를 교차 확인했다.
- Next:
1. 다음 `develop -> master` 릴리스부터는 별도 release branch를 만들지 않고 direct PR 흐름으로 진행한다.
- Status: done

## 2026-03-20
- Context: 사용자가 runtime state 파일은 heatmap 캐시와 분리하고, 외부 참고문서는 한 디렉터리에 모이길 원했다.
- Change:
1. state 기본 경로를 `data/heatmaps/state.json`에서 `data/state/state.json`으로 옮겼다.
2. `bot/forum/repository.py`는 새 경로를 기본으로 쓰되, 기존 `data/heatmaps/state.json`이 남아 있으면 자동으로 새 위치로 옮기도록 레거시 마이그레이션을 추가했다.
3. `docs/references/external/README.md`를 추가해 외부 벤더 문서/스프레드시트/PDF의 단일 보관 위치를 만들었다.
4. `.gitignore`, `AGENTS.md`, `README.md`, `docs/context/goals.md`를 새 state 경로와 외부 참고문서 위치 기준으로 갱신했다.
5. 워크스페이스에 남아 있던 `data/heatmaps/state.json`과 외부 참고 xlsx도 각각 `data/state/state.json`, `docs/references/external/` 기준으로 정리했다.
- Verification:
1. `tests/unit/test_state_atomic.py`에 legacy state 파일이 새 경로로 마이그레이션되는 회귀 테스트를 추가했다.
2. `.\.venv\Scripts\python.exe -m pytest` 기준 `89 passed, 2 deselected`
- Status: done

## 2026-03-20
- Context: 사용자가 앞으로의 약속은 모두 문서화하고, 특히 `develop -> master` 릴리스는 release branch 없이 direct PR로 고정하길 원했다.
- Change:
1. `AGENTS.md`에 새 운영 약속은 공통 규칙과 컨텍스트 문서에 함께 남긴다는 문서화 규칙을 추가했다.
2. 같은 문서에 `develop -> master` 릴리스는 앞으로 `develop`에서 바로 `master`로 PR을 연다는 브랜치 운영 약속을 추가했다.
3. `docs/context/design-decisions.md`에 이번 release branch 역동기화 경험을 근거로 direct PR 정책을 설계 결정으로 남겼다.
4. `docs/context/session-handoff.md`에 `PR #10` merge 완료와 현재 direct PR 약속을 최신 상태로 반영했다.
- Verification:
1. 문서 간 기준이 서로 모순되지 않도록 `AGENTS.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`를 교차 확인했다.
- Next:
1. 다음 `develop -> master` 릴리스부터는 별도 release branch를 만들지 않고 direct PR 흐름으로 진행한다.
- Status: done

## 2026-03-20
- Context: `master -> develop` sync PR `#10` review에서 forum channel resolution API 오류를 `missing_forum`으로 숨기지 말아야 한다는 P1 finding이 나왔다.
- Change:
1. `bot/features/intel_scheduler.py`의 `_resolve_guild_forum_channel_id()`는 이제 `discord.NotFound`만 진짜 missing channel로 취급하고, 다른 `fetch_channel()` 오류는 그대로 상위로 올린다.
2. 뉴스/EOD scheduler는 거래일 skip 판정을 forum resolution보다 먼저 수행해, 휴장일에는 Discord forum lookup 장애가 있어도 `holiday`/`calendar-failed` 의미가 유지된다.
3. forum resolution 중 API 오류가 난 guild는 failure로 집계하되, 다른 guild는 계속 처리한다.
4. 같은 오류는 더 이상 `missing_forum`/`skipped`로 눙치지 않고 job detail에 `forum_resolution_failures`를 남기며, run status는 `failed`로 기록한다.
5. `tests/integration/test_intel_scheduler_logic.py`에 뉴스/EOD 각각의 forum resolution API failure, mixed guild continuation, holiday-precedence 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_intel_scheduler_logic.py -k "forum_resolution or fallback_forum or news_job or eod_job"` 기준 `24 passed, 4 deselected`
- Next:
1. 수정 커밋을 PR `#10`에 푸시하고 `@codex review`를 다시 요청한다.
2. review가 clean이면 `develop`에 merge해 `master` 릴리스 수정과 `develop` 기준선을 다시 일치시킨다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 추가 review 2건에 맞춰 뉴스/트렌드 partial-delivery status false positive를 닫았다.
- Change:
1. `bot/features/intel_scheduler.py`는 `news_briefing`을 `posted > 0`만으로 `ok` 처리하지 않고, 같은 run의 `failed` count가 0일 때만 `ok`를 남기도록 조정했다.
2. 같은 함수는 `trend_briefing`도 `trend_posted > 0 and trend_failed == 0`일 때만 `ok`가 되도록 맞췄다.
3. `tests/integration/test_intel_scheduler_logic.py`에 뉴스 partial-failure, 트렌드 partial-failure 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py -k "news_job or eod_job"` 기준 `18 passed, 4 deselected`
2. `.\.venv\Scripts\python -m pytest` 기준 `82 passed, 2 deselected`
- Next:
1. release branch 최신 커밋을 PR `#9`에 푸시하고 `@codex review`를 다시 요청한다.
2. 새 review가 clean이면 `master`로 squash merge를 진행한다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 마지막 남은 Codex review finding으로 EOD partial-failure status false positive를 닫았다.
- Change:
1. `bot/features/intel_scheduler.py`는 `eod_summary`를 `posted > 0`만으로 `ok` 처리하지 않고, 같은 run의 `failed` count가 0일 때만 `ok`를 남기도록 조정했다.
2. `tests/integration/test_intel_scheduler_logic.py`에 한 guild post 성공 뒤 다른 guild post 실패가 이어지는 mixed-result EOD 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py -k "eod_job"` 기준 `5 passed, 15 deselected`
2. `.\.venv\Scripts\python -m pytest` 기준 `80 passed, 2 deselected`
- Next:
1. release branch 최신 커밋을 PR `#9`에 푸시하고 `@codex review`를 다시 요청한다.
2. 새 review가 clean이면 `master`로 squash merge를 진행한다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 추가 review에 맞춰 mixed watch_poll failure와 forum stale content id 정리를 보강했다.
- Change:
1. `bot/features/intel_scheduler.py`는 이제 `quote_failures`, `channel_failures`, `send_failures`가 하나라도 있으면 `watch_poll=failed`를 기록한다.
2. `tests/integration/test_intel_scheduler_logic.py`에 partial success 뒤 quote failure가 따라오는 mixed-result watch poll 회귀 테스트를 추가했다.
3. `bot/forum/service.py`는 삭제 대상 follow-up message가 이미 `NotFound`면 stale `content_message_ids`를 상태에서 제거하도록 바꿨다.
4. `tests/integration/test_forum_upsert_flow.py`에 missing follow-up message id cleanup 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py tests/integration/test_forum_upsert_flow.py` 기준 `27 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `79 passed, 2 deselected`
- Next:
1. 수정 커밋을 release branch에 푸시하고 PR `#9`에 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 추가 P1 review로 뉴스/EOD 전역 forum fallback의 guild ownership 검증을 보강했다.
- Change:
1. `bot/features/intel_scheduler.py`에 `_resolve_guild_forum_channel_id()` helper를 추가해, 뉴스와 장마감이 resolved forum channel의 guild 소유권을 확인한 뒤에만 pending queue에 넣도록 바꿨다.
2. 다른 guild 소속 global fallback forum은 `missing_forum`으로 처리해 provider fetch와 posting을 시작하지 않게 했다.
3. `tests/integration/test_intel_scheduler_logic.py`에 뉴스/EOD 각각의 cross-guild fallback forum 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 기준 `18 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `77 passed, 2 deselected`
- Next:
1. 수정 커밋을 release branch에 푸시하고 PR `#9`에 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: `develop -> master` release PR `#9` 재검토에서 watch alert delivery failure를 `ok`로 숨기지 않도록 후속 수정했다.
- Change:
1. `bot/features/intel_scheduler.py`는 `watch_poll` detail에 `alert_attempts`를 추가하고, `channel.send(...)` 실패가 한 건이라도 있으면 `watch_poll=failed`로 기록하도록 바꿨다.
2. `tests/integration/test_intel_scheduler_logic.py`에 실제 signal은 발생하지만 Discord delivery가 실패하는 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 기준 `16 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `75 passed, 2 deselected`
- Next:
1. 수정 커밋을 release branch에 푸시하고 PR `#9`에 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: `develop -> master` 릴리스 검토 중 PR `#9` Codex review가 `watch_poll` 운영 정합성 2건을 지적했다.
- Change:
1. `bot/features/intel_scheduler.py`는 watch alert channel을 해석할 때 channel의 guild 소유권을 확인하고, 다른 guild 채널로 fallback 되면 해당 guild를 실패로 처리하도록 보완했다.
2. 같은 함수는 watch poll run별 `processed`, `quote_failures`, `channel_failures`, `missing_channel_guilds`, `send_failures`를 detail에 남기고, 전부 실패했으면 `failed`, 대상이 없으면 `skipped`, 일부라도 처리했으면 `ok`를 기록하도록 바꿨다.
3. `tests/integration/test_intel_scheduler_logic.py`에 cross-guild fallback 차단과 all-quote-failure status 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 기준 `15 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `74 passed, 2 deselected`
- Next:
1. PR `#9`에 수정 커밋을 푸시하고 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: PR `#8` Codex review 후속 지적 2건을 반영했다.
- Change:
1. `bot/forum/service.py`는 starter thread/message state를 follow-up content sync 전에 먼저 기록하고, content message ids도 sync/deletion 진행에 따라 부분 상태로 갱신하도록 바꿨다.
2. `bot/features/news/trend_policy.py`는 단일 theme block이 너무 길어도 안전하게 분할 또는 truncate되도록 보완해, region message가 Discord 길이 제한을 넘지 않게 했다.
3. `tests/integration/test_forum_upsert_flow.py`, `tests/unit/test_trend_policy.py`에 Codex review 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest` 기준 `72 passed, 2 deselected`
- Next:
1. 같은 PR `#8`에 수정 커밋을 푸시하고 Codex review를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: 기존 국내/해외 뉴스 브리핑과 별도로 `트렌드 테마 뉴스` thread를 추가했다.
- Change:
1. `bot/intel/providers/news.py`에 `NewsAnalysis`, `ThemeDefinition`, `ThemeBrief`, `TrendThemeReport`를 추가하고, conservative briefing items와 wider trend candidates를 분리해 계산하도록 바꿨다.
2. 국내/해외 curated theme taxonomy와 probe query를 넣고, 반복 노출 + 소스 다양성 + 대표 종목/이벤트 신호 기반으로 region별 3~5개 테마를 점수화하도록 구현했다.
3. `bot/forum/service.py`와 `bot/app/types.py`는 starter message 외에 `content_message_ids`를 저장하고, thread 하위 message를 edit/create/delete할 수 있게 확장했다.
4. `bot/features/news/trend_policy.py`를 추가해 `[YYYY-MM-DD 트렌드 테마 뉴스]` starter message와 국내/해외 section message 렌더링을 분리했다.
5. `bot/features/intel_scheduler.py`는 같은 뉴스 tick에서 `trendbriefing` thread를 추가 생성 또는 갱신하며, 한 지역이 3개 미만이면 placeholder로 처리하고 두 지역 모두 3개 미만일 때만 `trend_briefing`을 `skipped`로 남긴다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest` 기준 `69 passed, 2 deselected`
2. 실제 네이버 실데이터 분석 기준 국내 테마는 `반도체`, `자동차` 2개만 남았고, 해외는 `금리/Fed`, `AI/반도체`, `에너지/원유`, `메가캡 기술주` 4개가 남았다.
3. 실제 Discord 반영 결과 `[2026-03-19 트렌드 테마 뉴스]` thread가 `https://discord.com/channels/332110589969039360/1484089919285497967`에 생성됐다.
4. 실제 thread는 starter message + 국내 placeholder message + 해외 theme message 구조로 저장됐고, `trend_briefing` status는 `ok`, detail은 `posted=1 failed=0 missing_forum=0 domestic_themes=2 global_themes=4`였다.
- Next:
1. 국내 recall을 더 올릴지 보고 `전력설비`, `방산`, `건설/원전` probe/score를 한 번 더 조정한다.
2. 해외 `금리/Fed`와 `AI/반도체` 비중이 과하면 theme score balance를 추가 조정한다.
- Status: done

## 2026-03-19
- Context: 뉴스 브리핑을 한 본문에 합치지 않고 국내/해외를 별도 daily thread 2개로 나누는 변경을 마무리했다.
- Change:
1. `bot/features/news/policy.py`에 region별 제목/본문 builder를 추가해 `[YYYY-MM-DD 국내 경제 뉴스 브리핑]`, `[YYYY-MM-DD 해외 경제 뉴스 브리핑]` 형식을 지원했다.
2. `bot/features/intel_scheduler.py`는 `newsbriefing-domestic`, `newsbriefing-global` 두 command key로 각각 upsert하도록 바뀌었고, 국내/해외 제목 날짜도 scheduler 실행 시점 `now`를 기준으로 맞췄다.
3. `bot/forum/service.py`는 기존 thread를 재사용할 때 제목이 달라지면 starter message 수정 전에 thread 이름도 함께 바꾸도록 유지했다.
4. 오늘자 기존 통합 `newsbriefing` thread record는 domestic thread로 migration/reuse되고, global thread는 새로 생성되도록 실제 운영 경로를 검증했다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest tests/unit/test_news_policy.py tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `28 passed`
2. `.\.venv\Scripts\python -B -m pytest` 기준 `61 passed, 2 deselected`
3. 실제 Discord 반영 후 domestic thread는 기존 `https://discord.com/channels/332110589969039360/1484055161600213092`를 재사용하며 제목이 `[2026-03-19 국내 경제 뉴스 브리핑]`로 바뀌었다.
4. 실제 Discord 반영 후 global thread `https://discord.com/channels/332110589969039360/1484079599175336057`가 새로 생성됐고 제목은 `[2026-03-19 해외 경제 뉴스 브리핑]`였다.
5. 실행 후 `news_briefing` status는 `ok`, detail은 `posted=1 failed=0 missing_forum=0 domestic=5 global=7`이었다.
- Next:
1. Discord에서 국내/해외가 분리된 형태가 실제 읽기 경험에서 더 나은지 확인한다.
2. 글로벌 기사 수와 품질이 다시 흔들리면 query 세트와 source weight를 한 번 더 조정한다.
- Status: done

## 2026-03-19
- Context: 사용자가 뉴스 브리핑이 너무 포괄적이라며, 거시 헤드라인은 유지하되 헤드라인급 개별 종목 기사도 포함되길 원했다.
- Change:
1. `bot/intel/providers/news.py`에서 선별 구조를 `거시 query + 종목 query` 2트랙으로 바꾸고, 종목 기사는 실적/가이던스/수주/규제 같은 고영향 이벤트가 제목에 직접 드러날 때만 통과시키도록 조정했다.
2. provider 마지막 단계가 지역별 점수순 결과를 다시 최신순으로 섞던 동작을 제거해, 저품질 최신 기사가 상위로 튀지 않게 했다.
3. scheduler는 `story_key()` 기준으로 국내/해외를 가로지르는 동일 기사 중복을 한 번 더 제거한다.
4. 실제 Discord thread를 새 선별 결과로 다시 갱신했다.
- Verification:
1. 네이버 공식 문서 기준 뉴스 검색 API는 검색 결과를 반환할 뿐 `headline/top story` 같은 직접 플래그는 제공하지 않음을 다시 확인했다.
2. `.\.venv\Scripts\python -B -m pytest` 기준 `58 passed, 2 deselected`
3. 실데이터 샘플 기준 현재 결과는 `domestic=6`, `global=11`, `body_len=1956`이다.
4. Discord API 갱신 결과 `updated_guilds=1`이며 thread는 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 체감 품질을 보고 `개장시황`, 설명형 해설 기사까지 더 줄일지 판단한다.
2. 필요하면 `NAVER_NEWS_*_STOCK_QUERIES`와 stock alias를 한 번 더 튜닝한다.
- Status: done

## 2026-03-19
- Context: 20건 상한과 본문 길이 보완 후, 오늘자 Discord 뉴스 브리핑 thread를 새 본문으로 다시 갱신했다.
- Change:
1. 실제 네이버 fetch 결과로 생성한 새 본문을 Discord starter message에 직접 PATCH해 오늘자 `newsbriefing` thread를 최신 내용으로 갱신했다.
2. 같은 흐름에서 `news_provider` / `news_briefing` 상태도 현재 개수(`domestic=5`, `global=17`) 기준으로 다시 저장했다.
- Verification:
1. Discord API 수정 결과 `updated_guilds=1`, `body_len=1987`, `domestic=5`, `global=17`
2. 갱신 대상 thread는 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 가독성과 기사 밀도를 보고 이 개수 범위를 유지할지 확인한다.
2. 국내 기사 수를 더 늘리고 싶으면 dedup 세분화가 필요한지 검토한다.
- Status: done

## 2026-03-19
- Context: 사용자가 아침/저녁 브리핑의 기사 수를 지역별 최대 20건까지 넓히되, 품질 필터 때문에 정확히 20건을 강제하지는 않길 원했다.
- Change:
1. `bot/app/settings.py`, `bot/features/intel_scheduler.py`, `.env.example`, `README.md`, `docs/specs/external-intel-api-spec.md`를 갱신해 뉴스 브리핑 지역별 상한을 20건 기준으로 맞췄다.
2. `bot/intel/providers/news.py`의 `NaverNewsProvider` 내부 cap도 `10 -> 20`으로 풀고, query 인자 타입 힌트를 실제 구현처럼 `str | Sequence[str]`로 맞췄다.
3. `tests/unit/test_news_provider.py`에 provider가 한 지역에서 최대 20건까지 반환할 수 있는지 검증하는 테스트를 추가했다.
4. `bot/features/news/policy.py`에 Discord 2000자 제한 안에서 본문을 안전하게 자르는 로직을 추가해, 개수 상한을 올려도 게시가 실패하지 않게 했다.
5. `tests/integration/test_intel_scheduler_logic.py`와 `tests/unit/test_news_policy.py`에 scheduler 상한 반영과 본문 길이 제한 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_news_policy.py tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `20 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `53 passed, 2 deselected`
3. 실제 네이버 fetch 샘플 기준 현재 설정으로 `limit=20`, `domestic=5`, `global=17`이었다.
4. 같은 실데이터 기준 실제 게시 본문 길이는 `1987`자라 Discord 2000자 제한 안에 들어간다.
- Next:
1. Discord thread를 다시 갱신할 때 현재 실데이터 기준 최대 20건 범위로 본문이 반영되는지 확인한다.
2. 국내 기사 수가 계속 낮으면 query 세트는 유지한 채 dedup 규칙을 더 세분화할지 검토한다.
- Status: done

## 2026-03-19
- Context: 국내 뉴스 품질 튜닝 후 오늘자 Discord 뉴스 브리핑 thread를 최신 결과로 다시 갱신했다.
- Change:
1. 실제 Discord client로 오늘자 `newsbriefing` thread를 다시 upsert해 최신 필터 결과를 반영했다.
2. 갱신된 본문 기준 국내는 3건, 해외는 4건으로 정리됐다.
- Verification:
1. 갱신 실행 결과 `updated_guilds=1`, `domestic=3`, `global=4`
2. 실제 본문에는 국내 `한은 총재/코스피 급락/국고채 금리`, 해외 `연준/마이크론/S&P500` 축이 반영됐다.
- Next:
1. Discord에서 체감 품질을 다시 확인한다.
2. 필요하면 `global`의 `tokenpost.kr` 같은 소스 패널티를 추가 조정한다.
- Status: done

## 2026-03-19
- Context: 국내 뉴스 브리핑에서 중복 장세 headline과 개별 종목/ETF 기사를 더 강하게 줄이는 품질 튜닝
- Change:
1. `bot/intel/providers/news.py`에 시장 주제 단위 dedup(`코스피`, `환율`, `금리`, `연준` 등)을 넣어 같은 장세 headline이 여러 건 남지 않게 했다.
2. 국내 기본 query 세트를 `국내 증시, 코스피 지수, 코스닥 지수, 원달러 환율, 한국은행 금리`로 좁혔다.
3. 소스 가중치를 조정해 `news.einfomax.co.kr` 같은 시장 소스를 더 우대하고, `tokenpost.kr`, `press9.kr` 등은 더 약하게 반영했다.
4. 국내 제목에 `주가`, `ETF`가 들어가는 개별 종목/상품 headline은 직접 제외하도록 필터를 추가했다.
5. 실제 `.env`에도 같은 query 세트를 반영했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `16 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `49 passed, 2 deselected`
3. 실데이터 샘플 기준 `news_briefing=ok`, `domestic=3`, `global=4`였고, 국내는 코스피/국고채 금리/환율 3건으로 정리됐다.
- Next:
1. 이 3건 중심 결과가 Discord 체감에서 더 낫다고 판단되면 실제 포럼 게시에도 그대로 적용한다.
2. 필요하면 글로벌 소스 패널티도 한 번 더 조정한다.
- Status: done

## 2026-03-19
- Context: 뉴스 브리핑 실데이터를 실제 Discord 포럼에 1회 게시해 결과물 확인 경로를 검증했다.
- Change:
1. 실제 `DISCORD_BOT_TOKEN`으로 Discord client를 login한 뒤 `_run_news_job()`를 수동 1회 실행했다.
2. 오늘 날짜(`2026-03-19`) 기준 `newsbriefing` daily post record가 새로 생성되는지 state와 Discord thread를 함께 확인했다.
- Verification:
1. 실행 전 오늘자 `newsbriefing` record는 비어 있었고, 실행 후 guild `332110589969039360`에 thread record가 생성됐다.
2. 생성된 thread 제목은 `[2026-03-19 아침 경제 뉴스 브리핑]`였다.
3. 실제 thread URL은 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 본문 가독성과 기사 품질을 확인한다.
2. 체감 품질이 부족하면 국내 query/키워드/소스 가중치를 추가 조정한다.
- Status: done

## 2026-03-19
- Context: 네이버 뉴스 브리핑 품질을 "주요뉴스/속보" 쪽으로 끌어올리기 위해 필터링을 강화했다.
- Change:
1. `bot/intel/providers/news.py`에 region별 다중 query 후보 수집, dedup 후 최고 점수 유지, 소스당 최대 2건 제한을 추가했다.
2. region gate 키워드, blocklist, 저신호 패널티(`표창`, `공로`, `행사` 등), 사진/코너형 기사 제외 로직을 넣었다.
3. `bot/app/settings.py`, `bot/features/intel_scheduler.py`, `.env.example`, `README.md`를 갱신해 `NAVER_NEWS_DOMESTIC_QUERIES`, `NAVER_NEWS_GLOBAL_QUERIES` 다중 query 설정을 지원하게 했다.
4. `tests/unit/test_news_provider.py`에 global 오염 억제, 다중 query 점수 선택, 기업 PR 패널티 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `12 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `45 passed, 2 deselected`
3. 실제 네이버 자격증명으로 `_run_news_job()`를 다시 실행해 `news_briefing=ok`, `domestic=5`, `global=5`와 브리핑 본문 렌더링을 재확인했다.
4. 실데이터 기준 `global` 결과는 FOMC/연준/나스닥 중심으로 정리돼 이전보다 purity가 올라갔고, `domestic`은 아직 일부 테마/해설형 기사가 남아 추가 튜닝 여지가 있다.
- Next:
1. `domestic` 쪽에서도 시장영향 기사와 테마/기획 기사 분리를 더 잘하는 키워드나 소스 정책을 조정한다.
2. query 세트를 실운영 결과에 맞게 다듬고, 필요하면 source allowlist/penalty를 더 세분화한다.
- Status: done

## 2026-03-19
- Context: `.env`에 실제 네이버 Client ID/Secret을 넣은 뒤 뉴스 브리핑 실데이터 fetch를 검증했다.
- Change:
1. `NEWS_PROVIDER_KIND=naver` 환경에서 `intel_scheduler._run_news_job()`를 dummy forum state와 fake post writer로 실행해 실제 네이버 API 응답이 현재 scheduler 흐름을 통과하는지 확인했다.
2. provider status, job status, 렌더된 브리핑 본문을 함께 점검했다.
- Verification:
1. 실데이터 실행 결과 `news_briefing` job status는 `ok`, detail은 `posted=1 failed=0 missing_forum=0 domestic=5 global=5`였다.
2. `news_provider` status는 `ok=True`, message는 `fetched=10`이었다.
3. 브리핑 본문은 실제 기사 10건으로 렌더됐고 title/source/time/link 형식이 현재 policy와 호환됐다.
4. 다만 `NAVER_NEWS_GLOBAL_QUERY=미국 증시` 결과에 국내 시장 성격 기사가 일부 섞여, query tuning 필요성이 확인됐다.
- Next:
1. `NAVER_NEWS_GLOBAL_QUERY`를 더 구체적인 해외 시장 키워드 조합으로 조정해 결과 품질을 비교한다.
2. 필요하면 국내/해외 query를 다중 호출 또는 제외 키워드 방식으로 확장한다.
- Status: done

## 2026-03-19
- Context: 네이버 뉴스 검색 API를 아침 뉴스 브리핑의 첫 실제 provider 후보로 붙이는 작업
- Change:
1. `bot/intel/providers/news.py`에 `NaverNewsProvider`와 `ErrorNewsProvider`를 추가했다.
2. 네이버 응답의 title HTML 태그 제거, `pubDate` 파싱, 원문 링크 우선 사용, 원문 도메인 기반 source 추출, 최근 N시간 필터를 adapter에 넣었다.
3. `bot/app/settings.py`, `bot/features/intel_scheduler.py`, `.env.example`, `README.md`를 갱신해 `NEWS_PROVIDER_KIND=naver`와 네이버 Client ID/Secret 기반 opt-in 설정을 추가했다.
4. `tests/unit/test_news_provider.py`를 추가해 정규화/필터링과 인증 실패 매핑을 검증했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile bot\intel\providers\news.py bot\features\intel_scheduler.py bot\app\settings.py` 통과
2. `.\.venv\Scripts\python -m pytest tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 통과
3. `.\.venv\Scripts\python -m pytest` 기준 `42 passed, 2 deselected`
- Next:
1. 실제 네이버 Client ID/Secret을 `.env`에 넣고 `NEWS_PROVIDER_KIND=naver`로 바꿔 실데이터 fetch를 확인한다.
2. `NAVER_NEWS_DOMESTIC_QUERY`, `NAVER_NEWS_GLOBAL_QUERY` 기본값이 브리핑 품질에 맞는지 실운영 결과를 보고 조정한다.
3. 필요하면 `source-status`에 provider kind나 query 품질 관련 힌트를 더 노출한다.
- Status: done

## 2026-03-18
- Context: `ship-develop` Codex review loop을 실제로 마무리해 `develop`에 반영하고, 임시 backup 브랜치도 정리했다.
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`가 PR head SHA가 바뀐 뒤 예전 `clean` review 결과를 재사용하지 않도록 `headRefOid` drift를 `pending`으로 처리하게 했다.
2. PR `#7`을 `@codex review` 재확인 후 squash merge해 `develop`에 반영했다.
3. 로컬 backup 브랜치 `codex/develop-diverged-backup-20260317`, `codex/review-fixes-backup-20260318`를 삭제했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
3. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --codex-review --wait-codex-seconds 300 --wait-seconds 600` 실행으로 PR `#7`이 `clean` 후 merge됨을 확인
4. `git status --short --branch` 기준 현재 로컬은 `develop...origin/develop`이고 작업 트리는 깨끗하다
- Next:
1. `docs/specs/external-intel-api-spec.md` 기준으로 첫 실제 외부 provider 구현 대상을 고른다. 우선순위는 `NewsProvider`다.
2. `.\.venv\Scripts\python -m pytest`와 `python -m bot.main` 기준으로 `develop` 부트와 기본 회귀를 다시 확인한다.
3. Discord 실운영 환경에서 히트맵 게시 흐름과 확장 scheduler 흐름 검증 계획을 구체화한다.
- Status: done

## 2026-03-18
- Context: PR `#7`의 Codex review에서 comment pagination 누락으로 review 상태를 오판할 수 있다는 지적을 반영하는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에 `get_paginated_api_items()`를 추가했다.
2. `get_issue_comments()`와 `get_review_comments()`가 GitHub REST 기본 30개 제한에 묶이지 않도록 `per_page=100` paging 루프를 사용하게 바꿨다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. historical PR 분류 재검증:
   - PR `#4` clean 케이스는 여전히 `clean`
   - PR `#7` findings 케이스는 `findings`로 유지
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 수정 커밋을 PR `#7`에 푸시하고 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-18
- Context: `ship-develop` 기본 동작을 human review gate에서 Codex review loop 중심으로 바꾸는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에 `--codex-review`, `--wait-codex-seconds` 옵션을 추가했다.
2. 스크립트가 `@codex review` 코멘트를 남기고, `chatgpt-codex-connector` issue comment / `chatgpt-codex-connector[bot]` review comment 패턴을 읽어 `clean`, `findings`, `pending`을 판별하도록 구현했다.
3. `.agents/skills/ship-develop/SKILL.md`와 `agents/openai.yaml`을 갱신해 기본 workflow를 "PR -> Codex review -> fix loop -> merge"로 바꾸고, human review gate는 명시 요청 시 옵션으로 남겼다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --codex-review --wait-codex-seconds 300 --dry-run --allow-dirty`로 Codex review 포함 dry-run 출력 확인
3. historical PR 기준 분류 검증:
   - PR `#4` 첫 요청 시 `findings`
   - PR `#4` 두 번째 요청 시 `clean`
   - PR `#5` 요청 시 `findings`
4. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 다음 실제 shipping 요청에서 Codex review loop가 원하는 UX로 동작하는지 실전 확인한다.
2. 필요하면 `codex-review-findings`일 때 PR 댓글/리뷰 스레드 요약까지 자동으로 더 도와주는 보조 스크립트를 추가한다.
- Status: done

## 2026-03-18
- Context: `ship-develop`에 리뷰 승인 대기 단계를 넣는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에 `--require-review`, `--wait-review-seconds` 옵션과 review polling 로직을 추가했다.
2. review decision이 `APPROVED`가 아니면 checks 상태를 요약한 뒤 `done=pending reason=review-required`로 멈추도록 바꿨다.
3. `.agents/skills/ship-develop/SKILL.md`와 `agents/openai.yaml`을 갱신해 reviewed shipping의 기본 경로가 two-pass임을 명시했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --require-review --dry-run --allow-dirty`로 review-gated dry-run 출력 확인
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 다음 실제 shipping 요청에서 첫 실행은 PR 생성 후 `review-required`로 멈추는지 확인한다.
2. 승인 후 같은 스크립트를 다시 실행해 merge 재개 흐름도 검증한다.
- Status: done

## 2026-03-18
- Context: `ship-develop`을 실제로 사용해 `develop` merge를 수행하는 과정에서 local branch cleanup 마지막 단계가 실패한 문제를 보완하는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`의 `cleanup_local_branch()`가 로컬 브랜치가 이미 삭제된 경우 `already-gone`으로 정상 처리하도록 바꿨다.
2. merge 후 출력도 `local_cleanup=deleted|already-gone|kept`처럼 실제 결과를 그대로 남기도록 맞췄다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 이 fix를 별도 브랜치에서 `develop`에 반영해 shipping workflow를 다시 깨끗하게 만든다.
- Status: done

## 2026-03-18
- Context: `develop으로 합쳐` 한 문장으로 GitHub shipping workflow를 처리할 수 있게 만드는 작업
- Change:
1. system-level `gh` 설치 상태와 인증 상태를 확인했고, 현재 계정 `Eulga`로 로그인되어 있음을 확인했다.
2. GitHub repo 설정을 확인해 현재 기본 브랜치가 `master`, 자동 머지가 `false`, merge 후 브랜치 자동 삭제가 `false`임을 확인했다.
3. `.agents/skills/ship-develop/` skill을 추가하고, `.agents/skills/ship-develop/scripts/ship_develop.py`로 push, PR 생성/재사용, check 확인, merge, local branch cleanup 흐름을 구현했다.
4. 새 skill은 `gh`가 `PATH`에 없어도 `C:\Program Files\GitHub CLI\gh.exe`를 fallback으로 사용하도록 만들었다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --dry-run --allow-dirty`로 dry-run 계획 출력 확인
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 다음 실제 merge 요청에서 `$ship-develop`을 사용해 end-to-end 흐름을 한 번 실전 검증한다.
2. 필요하면 pending checks 대기 시간이나 merge 정책 옵션을 실제 사용 패턴에 맞게 조정한다.
- Status: done

## 2026-03-18
- Context: PR `#4`의 Codex Connector 리뷰에서 같은 분 내 반복 tick이 기존 성공 상태를 `skipped`로 덮어쓸 수 있다는 P1 두 건을 반영하는 작업
- Change:
1. `bot/features/intel_scheduler.py`에서 뉴스/장마감 pending guild 계산 시 이미 해당 날짜에 성공 처리된 guild 수를 함께 세도록 바꿨다.
2. `pending_guilds`가 비고 `missing_forum > 0`이어도, 이미 성공 처리된 guild가 있으면 `skipped`로 상태를 덮어쓰지 않고 기존 성공 상태를 유지하도록 수정했다.
3. 같은 분 재실행에서 `news_briefing`과 `eod_summary`의 `ok` 상태가 유지되는 회귀 테스트 두 개를 `tests/integration/test_intel_scheduler_logic.py`에 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_intel_scheduler_logic.py` 통과 (`7 passed`)
2. `.\.venv\Scripts\python.exe -m pytest` 통과 (`40 passed, 2 deselected`)
- Next:
1. 수정 커밋을 PR `#4`에 푸시한다.
2. `@codex review`를 다시 호출해 같은 P1이 닫혔는지 확인한다.
- Status: done

## 2026-03-18
- Context: project-scoped Codex custom agent와 repo skill 최소 골격을 실제로 추가하는 작업
- Change:
1. `.codex/config.toml`에 `[agents]` 설정을 추가해 `max_threads=3`, `max_depth=1`로 시작점을 고정했다.
2. `.codex/agents/repo-explorer.toml`, `.codex/agents/reviewer.toml`, `.codex/agents/docs-researcher.toml`을 추가해 read-only 역할 분업 골격을 만들었다.
3. `.agents/skills/external-intel-provider-rollout/`를 생성하고 `SKILL.md`, `agents/openai.yaml`을 현재 외부 provider 실사용 전환 흐름에 맞게 채웠다.
4. 현재 프로젝트 `.venv`에 `PyYAML 6.0.3`을 설치해 공식 skill validator를 실행할 수 있게 했다. `requirements.txt`는 바꾸지 않았다.
- Verification:
1. `tomllib`로 `.codex/config.toml`과 세 개의 agent TOML 파일이 정상 파싱되는 것을 확인했다.
2. 경량 스크립트로 skill frontmatter, 핵심 섹션, `agents/openai.yaml`의 `$external-intel-provider-rollout` prompt 문자열을 확인했다.
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/external-intel-provider-rollout`가 `Skill is valid!`로 통과했다.
- Next:
1. 다음 실제 provider 전환 작업에서 `repo_explorer`, `reviewer`, `docs_researcher`, `$external-intel-provider-rollout`를 한 번 사용해 trigger와 지침을 다듬는다.
- Status: done

## 2026-03-18
- Context: Codex subagents/custom agents 내용을 현재 저장소 운영 방식에 접목할 수 있는지 검토하는 작업
- Change:
1. `AGENTS.md`, 컨텍스트 허브 문서, 현재 아키텍처와 provider/scheduler 경계를 다시 읽어 병렬 분업에 맞는 지점을 정리했다.
2. 공식 Codex 문서를 기준으로 subagents, custom agents, skills, `AGENTS.md`의 역할 구분을 확인했다.
3. 이 저장소는 `AGENTS.md` 기반 공통 규칙을 유지하고, 필요 시 read-only custom agent와 repo skill을 추가하되 외부 orchestration은 보류하는 방향으로 판단을 정리했다.
- Verification:
1. 현재 저장소에는 project-scoped `.codex/agents/`나 repo `.agents/skills/`가 아직 없다.
2. 로컬 사용자 설정 `C:\\Users\\kin50\\.codex\\config.toml`에는 `[agents]` 설정이 없고 Playwright MCP만 잡혀 있음을 확인했다.
3. 현재 코드 경계상 탐색/리뷰/문서 검증은 역할 분리가 가능하지만, 구현은 공용 파일 충돌을 줄이기 위해 single-writer가 더 안전하다고 대조했다.
- Next:
1. 실제 도입 시 최소 세트로 `reviewer`, `repo_explorer`, `docs_researcher` custom agent부터 고려한다.
2. 외부 provider 실사용 전환 같은 반복 체크리스트는 repo skill로 분리하는 안을 검토한다.
- Status: done

## 2026-03-18
- Context: 어제 리뷰에서 놓친 포인트를 반복하지 않도록 첫 번째 리뷰 운영 규칙을 문서화하는 작업
- Change:
1. `docs/context/review-rules.md`를 추가했다.
2. 첫 번째 룰로 `실패 경로와 운영 정합성까지 리뷰한다`를 정의했다.
3. `AGENTS.md`, `docs/context/README.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`에 이 규칙 문서 진입점을 연결했다.
- Verification:
1. 2026-03-17 리뷰에서 실제로 놓쳤던 사례가 규칙의 `Why`와 `Must` 항목에 반영됐는지 대조했다.
2. 다음 세션 읽기 순서에서 리뷰 작업 시 이 문서를 바로 볼 수 있게 연결했는지 확인했다.
- Next:
1. 다음 리뷰에서 이 1번 룰을 실제로 적용해 보고, 필요하면 표현을 다듬는다.
2. 새로운 누락 유형이 생기면 2번 룰을 추가한다.
- Status: done

## 2026-03-17
- Context: 전체 리뷰에서 나온 intel scheduler/문서 정합성 이슈를 실제 수정으로 반영했다.
- Change:
1. `bot/features/intel_scheduler.py`에서 뉴스 dedup을 fetch 단위 로컬 dedup으로 바꿔 게시 실패 후 같은 날짜 재시도가 비어 버리지 않도록 수정했다.
2. 뉴스/장마감 스케줄은 실제 게시 대상이 없으면 `skipped`, 모든 게시가 실패하면 `failed`, 하나 이상 성공하면 `ok`로 기록하도록 바꿨다.
3. `docker-compose.yml`, `README.md`, `AGENTS.md`, `docs/context/session-handoff.md`, `docs/context/review-log.md`를 갱신해 로그 볼륨, 실행 방법, quick test, 현재 핸드오프 상태를 실제 구현에 맞췄다.
4. 관련 회귀 테스트를 `tests/integration/test_intel_scheduler_logic.py`에 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest` 통과 (`38 passed, 2 deselected`)
- Next:
1. `codex/review-fixes` 브랜치 기준으로 PR을 열고, 리뷰에서 지적된 운영 가시성/문서 정합성 이슈가 닫혔는지 확인한다.
- Status: done

## 2026-03-17
- Context: 현재 브랜치가 `origin/develop`와 병합되면서 `bot/app/bot_client.py`에 충돌이 발생했다.
- Change:
1. `bot/app/bot_client.py`의 충돌을 command sync 상태 기록 로직과 구조화 로깅 설정을 함께 유지하는 방향으로 정리했다.
2. `tree.sync()` 성공 시에는 명령 수를 로거와 상태 파일에 함께 남기고, 실패 시에는 한국어 진단 메시지를 상태 파일과 로거에 함께 남기도록 맞췄다.
3. 충돌 마커를 제거하고 Git 인덱스에 해결 상태를 반영했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `git status --short --branch`에서 `bot/app/bot_client.py`가 더 이상 `UU`가 아닌 일반 수정 상태로 표시되는 것을 확인했다.
- Next:
1. 남은 로컬 변경과 함께 커밋 단위를 정리하고 필요 시 `origin/develop` 최신분을 다시 검토한다.
- Status: done

## 2026-03-17
- Context: 새로 추가한 뉴스/장마감/watch 스케줄을 실사용 단계로 올리기 위한 외부 API 기준 문서가 필요했다.
- Change:
1. `docs/specs/external-intel-api-spec.md`를 추가해 뉴스 브리핑, 장마감 요약, watch quote의 정규화 API 계약을 정의했다.
2. `AGENTS.md`, `docs/context/goals.md`, `docs/context/session-handoff.md`, `docs/context/README.md`, `README.md`를 갱신해 이 작업을 최우선 전환 과제로 반영했다.
3. 다음 세션 TODO를 실제 provider 구현과 운영 검증 중심으로 재정렬했다.
- Verification:
1. `bot/features/intel_scheduler.py`, `bot/intel/providers/news.py`, `bot/intel/providers/market.py`의 현재 인터페이스와 필드 구성을 기준으로 명세를 대조했다.
2. README와 컨텍스트 문서가 같은 명세 경로를 참조하는지 확인했다.
- Next:
1. 외부 벤더 또는 중간 adapter 후보를 정하고 provider 구현을 시작한다.
2. 특히 watch quote는 batch 조회 전략을 먼저 잡는다.
- Status: done

## 2026-03-17
- Context: PR `#3`의 Codex Connector 리뷰 코멘트를 반영하는 작업
- Change:
1. `record_command_sync`를 `bot/app/command_sync.py`로 옮겨 공용 함수로 정리했다.
2. 상태 파일 저장 실패 시 예외를 부트 흐름 밖으로 전파하지 않고 로그만 남기도록 수정했다.
3. 상태 저장 성공/실패 케이스를 검증하는 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `.\.venv\Scripts\python -m pytest` 통과
- Next:
1. 수정 커밋을 PR `#3`에 푸시하고 추가 리뷰 사항이 있는지 확인
- Status: done

## 2026-03-17
- Context: 슬래시 커맨드 동기화 실패를 더 잘 진단할 수 있게 만드는 작업
- Change:
1. `bot/app/command_sync.py`에 Discord 동기화 예외를 사람이 읽기 쉬운 한국어 안내로 바꾸는 헬퍼를 추가했다.
2. `bot/app/bot_client.py`에서 `tree.sync()` 실패를 잡아 `system.job_last_runs.command-sync`에 성공/실패 상태를 저장하도록 연결했다.
3. 관련 단위 테스트 `tests/unit/test_command_sync.py`를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `.\.venv\Scripts\python -m pytest` 통과
- Next:
1. PR 생성 후 Codex Connector 리뷰 코멘트를 확인하고 필요 시 수정 반영
- Status: done

## 2026-03-17
- Context: `codex/context-summary` 브랜치의 PR 흐름을 끝까지 완료한 작업
- Change:
1. PR `#2`를 `develop` 대상으로 생성했다.
2. PR을 squash merge로 반영했다.
3. merge 후 원격 브랜치 `codex/context-summary`를 삭제했다.
- Verification:
1. PR `#2`가 `merged=true` 상태인지 확인했다.
2. 원격 heads 조회에서 `codex/context-summary`가 삭제됐는지 확인했다.
- Next:
1. 남아 있는 로컬 미커밋 변경은 별도 흐름으로 정리한다.
- Status: done

## 2026-03-17
- Context: 현재 브랜치 변경을 재검토하고 `develop` PR 흐름으로 넘기려는 작업
- Change:
1. `codex/context-summary`를 원격에 푸시해 최신 HEAD(`3a5bdfd`)를 반영했다.
2. 원격 compare 기준 실제 PR diff가 `docs/reports/sunday-kheatmap-investigation-2026-03-12.md` 1파일임을 확인했다.
3. GitHub compare 페이지와 로컬 코드를 대조해 문서 리포트의 상태 키와 조사 메모를 재검토했다.
- Verification:
1. 원격 compare 페이지에서 `Able to merge` 상태를 확인했다.
2. `git diff develop HEAD` 기준 현재 트리 차이는 조사 리포트 1파일뿐임을 확인했다.
- Next:
1. GitHub 인증 가능한 환경에서 PR 생성
2. PR 체크 통과 후 merge 및 브랜치 삭제
- Status: done

## 2026-03-17
- Context: 바이브 코딩 규칙 초안을 실제 운영 규칙으로 편입하는 작업
- Change:
1. `AGENTS.md` 읽기 순서에 `docs/prompts/vibe-coding-rule-prompt.md`를 추가했다.
2. `AGENTS.md`에 `바이브 코딩 운영 규칙` 섹션을 신설해 시작, 구현, 검증, 안전, 기록, 완료 조건을 반영했다.
3. 초안 단계로 적혀 있던 컨텍스트 기록을 운영 편입 기준으로 갱신했다.
- Verification:
1. 사용자 제공 규칙의 핵심 항목이 `AGENTS.md` 본문에 모두 반영됐는지 대조 확인했다.
2. 기존 프로젝트 운영 규칙과 충돌하지 않도록 공통 원칙 섹션으로 배치했다.
- Next:
1. 이후 실제 작업에서 이 규칙을 기준으로 로그와 검증 절차가 잘 유지되는지 운영하면서 다듬는다.
- Status: done

## 2026-03-17
- Context: 현재 유행하는 바이브 코딩 규칙을 조사하고, 이 프로젝트에 맞는 단일 프롬프트로 정리하는 작업
- Change:
1. 웹 리서치를 바탕으로 바이브 코딩 규칙의 공통 요소를 정리했다.
2. 속도 중심 예시에서 자주 빠지는 안전장치와 컨텍스트 보존 규칙을 보완했다.
3. 재사용 가능한 초안을 `docs/prompts/vibe-coding-rule-prompt.md`에 저장했다.
- Verification:
1. 프롬프트 안에 컨텍스트 읽기, 작은 변경, 검증, 리뷰, 위험 작업 중단, 로그 갱신 규칙이 모두 포함되도록 점검했다.
- Next:
1. 실제로 이 프롬프트를 `AGENTS.md`나 운영 프롬프트에 반영할지 결정한다.
- Status: done

## 2026-03-17
- Context: 프로젝트 작업 컨텍스트를 검토/개발/설계로 분류 저장하는 기반이 필요했다.
- Change:
1. `docs/context/` 디렉터리를 만들었다.
2. 컨텍스트 허브 문서와 카테고리별 로그 파일을 추가했다.
3. `AGENTS.md` 읽기 순서와 종료 체크 절차를 새 구조 기준으로 갱신했다.
- Verification:
1. 저장 구조가 프로젝트 루트 기준으로 고정되어 다음 세션이 동일 경로를 읽을 수 있다.
2. 기존 코드 파일 변경 없이 문서 계층만 추가해 현재 구현 리스크를 늘리지 않았다.
- Next:
1. 실제 기능 작업 때 이 로그를 누적 사용한다.
- Status: done

## 2026-03-23
- Context: `watch_poll` live rollout과 `.env.example` 주석 보강을 한 번에 정리하는 작업
- Change:
1. `bot/app/settings.py`에 `MARKET_DATA_PROVIDER_KIND`를 추가하고, `bot/features/intel_scheduler.py`에서 `quote_provider`를 `mock|kis` 선택형 builder로 바꿨다.
2. `bot/intel/providers/market.py`에 `ErrorMarketDataProvider`, `KisMarketDataProvider`를 추가했다. KIS adapter는 access token 캐시, 1회 auth refresh retry, registry canonical symbol 해석, KRX/해외 경로 분기, poll-cycle quote cache, optional `warm_quotes()`를 지원한다.
3. watch scheduler는 유효한 watch alert channel이 있는 guild만 먼저 모아 unique symbol warm-up을 수행하고, runtime provider status는 `kis_quote` 키로 기록하게 맞췄다.
4. `.env.example`를 섹션형으로 다시 정리했다.
5. 후속 정리로 `.env.example` 주석은 변수별 설명을 최소화하고 섹션 묶음 설명 중심으로 바꿨다. 개별 주석은 `options:`가 필요한 항목만 남기고, `WATCH_ALERT_CHANNEL_ID` 같은 타입 제약은 섹션 주석으로 올렸다.
6. `README.md` 환경변수 섹션에 `MARKET_DATA_PROVIDER_KIND`와 watch alert channel 타입 메모를 추가했다.
7. `tests/unit/test_market_provider.py`를 새로 추가했고, watch scheduler 통합 테스트도 `kis_quote` 기준과 warm hook 동작에 맞춰 갱신했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py tests\unit\test_status_command.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 통과
3. live smoke는 이번 세션에서 완료하지 못했다. 현재 `.env` 기준 `KIS_APP_KEY`, `KIS_APP_SECRET`, `WATCH_ALERT_CHANNEL_ID`, `ADMIN_STATUS_CHANNEL_ID`가 모두 비어 있어 KIS/Discord 실연동 검증이 blocked 상태다.
- Next:
1. 운영 env에 KIS credential과 text `WATCH_ALERT_CHANNEL_ID`, 접근 가능한 `ADMIN_STATUS_CHANNEL_ID`를 채운 뒤 `watch add -> poll -> alert send -> /source-status` live smoke를 한 번 수행한다.
2. live smoke 후 실제 provider 응답 기준으로 `not-found`, `stale`, rate-limit 메시지가 충분히 운영 친화적인지 한 번 더 점검한다.
- Status: done
