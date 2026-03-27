# Review Log

## 2026-03-27
- Context: PR #16 재리뷰에서 watch forum-thread follow-up 결함과 남은 문서 불일치를 재확인했다.
- Finding:
1. `/watch remove`가 기존 thread registry 없이도 새 inactive thread를 만들 수 있었고, remove가 "삭제"가 아니라 새 forum thread 생성으로 보일 수 있었다.
2. 기존 symbol thread를 재사용하는 `/watch add` / `/watch remove` 경로에서 starter가 active/inactive placeholder로 전환되지 않아 사용자에게 stale 상태가 남을 수 있었다.
3. 현재 코드가 이미 hard cut 한 `WATCH_ALERT_CHANNEL_ID` / `watch_alert_channel_id` / `WATCH_ALERT_COOLDOWN_MINUTES`가 `.env.example`과 current-runtime 문서에 남아 있었다.
4. current docs에는 band comment label이 `int(WATCH_ALERT_THRESHOLD_PCT) * band`를 사용한다는 설명이 없어, non-integer threshold 운영 의도를 읽어낼 수 없었다.
5. 후속 reviewer는 `/watch remove`가 stale registry entry를 가진 경우에도 `upsert_watch_thread()` fallback recreate 때문에 새 inactive thread를 만들 수 있다고 지적했다.
6. 전체 reviewer는 `docs/specs/integration-test-cases.md`가 이번 브랜치의 실제 non-live integration coverage와 watch forum-thread 회귀 파일을 반영하지 못한다고 지적했다.
7. 최신 Codex review는 carry-forward finalization이 여러 trading session gap 뒤의 newer snapshot에도 `previous_close` fallback을 허용해 잘못된 close price로 old session을 finalize할 수 있다고 지적했다.
8. 같은 review는 same-session remove/re-add 뒤 기존 `highest_up_band/highest_down_band`가 남아 early band alert가 누락될 수 있다고 지적했다.
9. 같은 review는 malformed persisted symbol 하나가 `get_watch_market_session()` 예외로 전체 `watch_poll` cycle을 중단시킬 수 있다고 지적했다.
10. 같은 review는 KRX post-close snapshot이 `stck_cntg_hour` 기반 stale-quote 판정 때문에 close finalization까지 가지 못할 수 있다고 지적했다.
11. follow-up 전체 리뷰는 `/watch add`의 create-or-recover 표현이 실제 duplicate-add no-op 동작과 어긋나 repair command처럼 읽힌다고 지적했다.
12. 최신 Codex review는 post-close stale snapshot 허용이 `KRX`만 whitelist하고 있어 US close finalization은 여전히 stale-quote에 막힐 수 있다고 지적했다.
13. 같은 review는 fractional threshold에서 band label이 정수 절단되어 보이는 점을 다시 지적했다.
- Resolution:
1. `/watch remove`는 기존 tracked thread가 있을 때만 inactive starter update를 수행하고, registry가 없으면 새 thread를 만들지 않도록 수정했다.
2. `/watch add`는 re-add/recover 시 active placeholder starter를 명시적으로 다시 쓰도록 수정했다.
3. legacy watch route env/settings/type/docs surface를 current code에 맞춰 정리하고, hard cut 이후 watch routing source of truth가 `watch_forum_channel_id`뿐임을 문서에 남겼다.
4. current behavior spec에 band comment label의 정수 절단 의도를 명시했다.
5. `upsert_watch_thread()`에 `allow_create` 제어를 추가하고 `/watch remove`는 update-only로 호출해, stale registry entry가 있어도 새 inactive thread를 만들지 않도록 막았다.
6. `docs/specs/integration-test-cases.md`의 suite summary, totals, watch coverage 섹션을 현재 collect 결과와 watch forum-thread 테스트 파일 기준으로 갱신했다.
7. `bot/features/intel_scheduler.py`의 close-price fallback을 adjacent next trading session으로 제한해 multi-session outage 뒤 잘못된 close finalization을 막았다.
8. `bot/features/watch/command.py`에서 same-session re-add 시 highest band checkpoint를 reset하도록 보강했고, 관련 integration/unit regression을 추가했다.
9. `bot/features/intel_scheduler.py`에서 malformed persisted symbol을 per-symbol snapshot failure로 처리해, bad symbol 하나가 같은 cycle의 다른 guild-symbol 처리까지 막지 않도록 수정했다.
10. `bot/intel/providers/market.py`에서 KRX off-hours close finalization용 snapshot은 `session_close_price`와 current off-hours `session_date`가 맞으면 stale-quote로 reject하지 않도록 완화했다.
11. malformed symbol isolation 가드는 broad `Exception` 대신 `unsupported-market:*` runtime error만 잡도록 좁혀, 예상 못 한 session 계산 결함이 `snapshot_failures`로 묻히지 않게 수정했다.
12. current-truth 문서의 `/watch add` 설명을 duplicate add no-op 기준으로 교정해, stale thread repair는 `/watch add`의 계약이 아니라는 점을 명시했다.
13. `bot/intel/providers/market.py`의 post-close stale snapshot 허용을 market-agnostic off-hours close snapshot으로 넓혀, US close finalization도 stale-quote에 막히지 않도록 수정했다.
14. threshold label 정수 절단은 intentional behavior로 유지하되, `docs/context/design-decisions.md`와 current-truth spec에 rationale까지 명시해 future review가 설계 의도를 직접 확인할 수 있게 했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_market_provider.py -q -x --tb=line -p no:cacheprovider`
2. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_watch_forum_flow.py tests/integration/test_watch_poll_forum_scheduler.py tests/unit/test_market_provider.py tests/unit/test_watch_cooldown.py tests/unit/test_watchlist_repository.py tests/unit/test_bot_client.py -q -x --tb=line -p no:cacheprovider`
3. `.\.venv\Scripts\python.exe -m pytest tests/integration --collect-only -q -m "not live"`
- Status: done

## 2026-03-24
- Context: 사용자가 이전 QA 리뷰에서 P0/P1만 추려 GitHub issue draft와 주차별 구현 순서를 요청했다.
- Finding:
1. P0 묶음은 `state fail-open 차단`, `mock/live fail-closed`, `watch quote freshness + market-session gating`이다.
2. P1 묶음은 `shared watchlist 권한`, `state mutation serialization`, `daily scheduler catch-up`, `transient Discord fetch 시 duplicate post 방지`, `hybrid news partial-region 허용`, `empty-region briefing status 재정의`다.
3. 구현 순서는 `Week 1=P0`, `Week 2=state/scheduler/Discord idempotency`, `Week 3=news functional degradation + status semantics`로 정리하는 것이 가장 자연스럽다.
- Status: open

## 2026-03-24
- Context: 사용자가 principal-level QA 아키텍트 프롬프트를 적용한 전체 QA 리뷰를 요청했다.
- Finding:
1. `bot/forum/repository.py`의 `load_state()`는 `JSONDecodeError`/`OSError`에서 빈 state를 정상값처럼 반환하고, 여러 command/scheduler path가 그 값을 다시 저장해 guild routing, watchlist, daily post dedupe state를 통째로 지울 수 있다.
2. `bot/features/intel_scheduler.py`의 `news/watch`는 기본값이 `enabled + mock provider` 조합이라 운영자가 env를 충분히 채우지 않았을 때도 synthetic data를 실제 브리핑/알림처럼 게시할 수 있다. `eod_summary`도 활성화 시 여전히 `MockEodSummaryProvider`를 사용한다.
3. `bot/intel/providers/market.py`는 국내 quote를 `asof=now`로 기록해 stale/off-hours domestic quote를 fresh처럼 통과시킬 수 있고, 해외 quote의 `khms`도 scheduler timezone 기준으로 파싱해 미국장 시각 해석이 어긋날 가능성이 있다.
4. `bot/features/watch/command.py`는 shared guild watchlist를 아무 길드 멤버나 수정할 수 있고, `bot/features/status/command.py`는 `/health`, `/last-run`, `/source-status`를 모든 멤버에게 공개한다.
5. `bot/features/auto_scheduler.py`와 `bot/features/intel_scheduler.py`의 daily jobs는 exact-minute trigger만 있고 catch-up path가 없어, 늦은 시작/재배포/짧은 stall 뒤에는 그날 run을 조용히 놓칠 수 있다.
6. `bot/forum/service.py`는 기존 thread/message fetch의 transient `HTTPException`/`Forbidden`을 `NotFound`와 같이 취급해 same-day duplicate thread 또는 trend follow-up duplicate message를 만들 수 있다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest -q` 전체 통과.
- Status: open

## 2026-03-24
- Context: 사용자가 `trendbriefing` 생성 시 `Marketaux`로 수집한 영어 해외뉴스가 현재 테마 판정에서 제대로 동작하는지 확인을 요청했다.
- Finding:
1. `bot/intel/providers/news.py`의 `MarketauxNewsProvider.analyze()`는 글로벌 trend 후보를 `NaverNewsProvider`처럼 theme probe query로 넓게 모으지 않고, briefing에 남은 기사만 `_fallback_candidates_by_region()`으로 점수화해 사용한다.
2. 이 fallback 경로는 `title`, `source`, `published_at`만 사실상 쓰고 `description`을 빈 문자열로 둬 영어 기사 본문/요약/엔터티 신호를 trend 매칭에 반영하지 못한다.
3. `_match_theme_candidate()`는 curated keyword/symbol hit와 최소 score를 동시에 요구하는데, 글로벌 taxonomy의 `representative_symbols`와 alias가 상당수 한국어 중심이라 `Apple`, `Microsoft`, `Nvidia`, `Tesla`, `Amazon`, `Meta`, `Alphabet`, `Powell` 같은 영어 company-only headline recall이 낮다.
4. 로컬 논리 검증에서 `Fed/Treasury yields`, `Apple/Microsoft`, `Nvidia/AMD` headline 조합은 global theme 0개였고, `AI chip/semiconductor`처럼 explicit theme keyword가 제목에 들어간 경우만 `AI/반도체`로 매칭됐다.
5. 현재 테스트 커버리지는 `tests/unit/test_news_provider.py`의 `test_marketaux_news_provider_normalizes_payload()` 수준이라, Marketaux 영어 trend 판정 회귀를 직접 잡는 테스트가 없다.
- Status: open

## 2026-03-23
- Context: 사용자가 두 스레드에서 진행한 수정이 겹쳤는지 불확실하다며 전체 modified 파일 리뷰와 clean 확인을 요청했다.
- Finding:
1. 명백한 merge conflict 잔재나 같은 목적의 이중 구현은 보이지 않았다. 변경 축은 `watch` 재알림 제어, command/status 로깅, KIS 해외 quote fallback으로 비교적 분리돼 있었다.
2. 다만 `watch_alert_latches` 도입 뒤 `bot/forum/repository.py`의 `remove_watch_symbol()`이 runtime watch 메타상태를 지우지 않아, 종목을 제거 후 다시 등록해도 이전 `latch/cooldown/baseline`이 남아 첫 same-direction 알림이 막힐 수 있었다.
- Resolution:
1. 제거 시 해당 symbol의 `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`를 함께 정리하도록 보강했다.
2. `tests/unit/test_watchlist_repository.py`, `tests/unit/test_watch_cooldown.py`에 remove/re-add reset 회귀를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_watch_cooldown.py tests\unit\test_watchlist_repository.py tests\integration\test_intel_scheduler_logic.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀 통과
- Status: done

## 2026-03-23
- Context: 사용자가 기능별 로그 누락 검토 후 바로 보강 패치를 진행했다.
- Finding: 기존 지적은 유효했고, `intel_scheduler` success/skip와 주요 slash command 실행 흔적이 파일 로그에 거의 남지 않아 `bot.log`만으로 운영 흐름을 추적하기 어려웠다.
- Resolution:
1. `bot/features/intel_scheduler.py`는 각 job의 최종 `status/detail`을 파일 로그에도 기록한다.
2. `bot/features/watch/command.py`, `bot/features/admin/command.py`, `bot/features/runner.py`, `bot/features/status/command.py`는 command audit log를 남긴다.
3. `bot/app/command_sync.py`의 fail-open 경로는 `print(...)` 대신 logger를 사용한다.
4. logging 보강 과정에서 `interaction.user`가 없는 테스트 더블 회귀가 드러나, 관련 command logger는 모두 fail-safe helper를 사용하도록 보강했다.
5. reviewer follow-up으로 `bot/intel/providers/market.py`의 exchange alias retry가 request-stage `not-found`에서도 계속되도록 추가 수정했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_command_sync.py tests\unit\test_watch_command.py tests\unit\test_status_command.py tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q` 통과
2. `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀 통과
3. `docker compose up -d --build` 후 `data/logs/bot.log`에 `watch_poll status=ok` 라인이 실제로 추가되는 것을 확인했다.
- Status: done

## 2026-03-23
- Context: 사용자가 "기능별 로그가 제대로 안 찍히는 것 같다"고 보고해 현재 로깅 경로를 점검했다.
- Finding:
1. 파일 로깅 자체는 동작하지만, `bot/features/intel_scheduler.py`는 `news_briefing`, `eod_summary`, `watch_poll`, `instrument_registry_refresh`의 성공/skip 결과를 state에만 기록하고 파일 로그에는 남기지 않는다. 실제로 `data/state/state.json`의 최신 `watch_poll=ok`가 갱신된 뒤에도 `data/logs/bot.log`에는 startup 로그만 있고 해당 tick 로그는 없다.
2. 수동 기능도 feature-level 로그가 거의 없다. `bot/features/watch/command.py`, `bot/features/admin/command.py`, `bot/features/runner.py`는 slash command 호출/성공/실패를 logger로 남기지 않아 `/watch add`, `/setwatchchannel`, 수동 `kheatmap/usheatmap` 실행 흐름을 파일 로그만으로 추적하기 어렵다.
3. `bot/app/command_sync.py`의 state 저장 실패 경로는 logger가 아니라 `print(...)`를 사용해, 로그 형식/파일 핸들러를 우회한다.
- Why:
1. `bot/features/auto_scheduler.py`만 success/skip/failure를 구조적으로 로그로 남기고 있어 기능별 가시성 편차가 크다.
2. 운영자가 `job_last_runs` state를 직접 열지 않는 한, 로그 파일만 보고는 어떤 기능이 성공했는지와 어느 guild/channel에서 돌았는지 판단하기 어렵다.
- Status: done

## 2026-03-23
- Context: `bot/intel/providers/market.py`의 overseas warm-up batch failure가 same-poll single-symbol fallback까지 막는 reviewer P2 후속 수정
- Finding: 기존 지적은 유효했고, `_warm_overseas_chunk()`가 batch failure를 chunk 전체 `_quote_errors`로 저장해 버려 `get_quote()`가 개별 `price` endpoint fallback을 시도하지 못하고 즉시 실패할 수 있었다.
- Resolution:
1. batch request failure와 batch payload-shape failure는 best-effort warm-up failure로만 취급하고, per-symbol `_quote_errors`를 남기지 않게 바꿨다.
2. 따라서 같은 poll cycle에서도 `get_quote()`가 single-symbol endpoint를 직접 호출해 회복할 수 있다.
3. `tests/unit/test_market_provider.py`에 batch warm-up failure 후 single fetch fallback 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q` 통과
- Status: done

## 2026-03-23
- Context: `/source-status`가 legacy `market_data_provider`와 신규 `kis_quote`를 함께 보여 줄 수 있다는 review finding 후속 수정
- Finding: 기존 지적은 유효했고, persisted provider state가 append-only인 상황에서 status view merge가 legacy key를 정리하지 않아 health 출력이 ambiguous해질 수 있었다.
- Resolution:
1. `bot/features/status/command.py`는 이제 shared alias map으로 `market_data_provider -> kis_quote`, `polygon_reference -> massive_reference`를 canonical key로 합친다.
2. actual state에 legacy key와 canonical key가 동시에 있을 때는 canonical row를 우선해 stale legacy row가 현재 provider status를 덮어쓰지 않게 했다.
3. `tests/unit/test_status_command.py`에 legacy key normalization과 canonical-precedence 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests\unit\test_status_command.py -q` 통과 (`6 passed`)
- Status: done

## 2026-03-23
- Context: 사용자가 현재 uncommitted KIS watch rollout 변경분에 대해 `integration_tester`와 `reviewer` subagent 병렬 검증을 요청했다.
- Finding:
1. `bot/intel/providers/market.py`의 overseas batch warm-up 실패는 chunk 안의 모든 symbol을 `_quote_errors`에 기록하고, 같은 poll cycle의 `get_quote()`는 single-symbol fetch 전에 `_quote_errors`를 먼저 확인한다. 그래서 `multprice`의 일시 실패가 있어도 개별 `price` API로 회복할 기회를 잃고, 전체 `watch_poll` quote failure로 굳어질 수 있다.
2. `bot/features/status/command.py`는 기본 provider row를 `kis_quote`로 바꿨지만, 기존 state 파일의 `market_data_provider`는 정리하지 않는다. 현재 `_merge_defaults()`는 legacy key를 제거하지 않으므로 `/source-status`와 `/health`가 rollout 직후 한동안 두 quote-provider row를 함께 보여 줄 수 있다.
- Evidence:
1. `bot/intel/providers/market.py`의 `_warm_overseas_chunk()`는 batch fetch 실패 시 chunk 전체 symbol에 error를 저장하고, `get_quote()`는 cached error가 있으면 single-symbol fetch로 내려가기 전에 바로 예외를 던진다.
2. `bot/features/status/command.py`의 `source-status`/`health`는 persisted provider state에 defaults를 `setdefault()`로만 합치므로, 기존 `market_data_provider` row가 남아 있으면 그대로 렌더된다.
- Residual risk:
1. non-live 테스트는 통과했지만, 실제 KIS upstream payload shape와 rate-limit/auth failure wording은 live smoke로 아직 검증하지 못했다.
- Status: open

## 2026-03-22
- Context: PR `#12`의 Codex review가 auto screenshot state 보존 fix에 추가 data-loss 경로가 남아 있다고 지적했다.
- Finding:
1. `bot/features/auto_scheduler.py`는 `execute_heatmap_for_guild()` 성공 후 `load_state()`를 다시 읽도록 바뀌었지만, 이 코드베이스의 `load_state()`는 `OSError`/`JSONDecodeError`에서 empty state를 반환한다.
2. 따라서 refresh read가 transient failure로 empty state를 돌려주면, 직후 `save_state(state)`가 `last_auto_runs`만 있는 near-empty state를 디스크에 써서 runner가 저장한 forum/cache state를 다시 잃게 만들 수 있었다.
- Resolution:
1. refresh read 결과가 guild/command state가 비어 있는 suspicious empty state면 `last_auto_runs` 저장을 건너뛰고 warning만 남기도록 가드를 추가했다.
2. refresh read empty-state 회귀 테스트를 추가해 scheduler가 추가 save를 하지 않는지 검증했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_auto_scheduler_logic.py -q` 통과 (`6 passed`)
- Status: done

## 2026-03-22
- Context: 프로젝트의 [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml) 내용을 점검해 subagent 전역 설정이 현재 Codex 규약과 맞는지 확인했다.
- Finding: 블로킹 이슈는 찾지 못했다.
- Residual risk:
1. 현재 `[agents]`의 `max_threads = 4`는 유효한 설정이지만, Codex 기본값 `6`보다 더 보수적이라 여러 custom agent를 병렬로 붙이는 작업에서는 의도보다 빨리 concurrency cap에 걸릴 수 있다.
2. `max_depth = 1`은 현재 프로젝트 목적에는 적절하지만, child agent가 다시 agent를 fan-out해야 하는 workflow는 막는다. 이 제약이 의도된 운영 정책인지 정도만 팀 내에서 유지하면 된다.
- Evidence:
1. `tomllib`로 [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml) 파싱 성공을 확인했고, 현재 `[agents]`에는 `max_threads = 4`, `max_depth = 1`, `job_max_runtime_seconds = 1800`이 반영돼 있다.
2. OpenAI Codex 공식 문서 기준 `[agents]` 아래 `max_threads`와 `max_depth`는 유효한 전역 subagent 설정 키이며, `max_threads` 기본값은 `6`, `max_depth` 기본값은 `1`이다.
- Status: done

## 2026-03-20
- Context: 운영 중이던 15:35 자동 `kheatmap` 글이 코스닥 렌더 타임아웃으로 코스피만 게시된 뒤, 같은 날 수동 `/kheatmap`이 기존 thread 수정 대신 새 글을 만든 원인을 조사했다.
- Finding:
1. 현재 코드 기준 수동/자동 `kheatmap`은 모두 `command_key="kheatmap"`로 같은 일자 state를 읽고, 오늘자 `thread_id`/`starter_message_id`가 있으면 기존 글을 수정하고 없거나 fetch가 실패할 때만 새 thread를 만든다.
2. partial render 자체는 새 글 생성 원인이 아니다. `execute_heatmap_for_guild()`는 성공 이미지가 1개라도 있으면 계속 `upsert_daily_post()`를 호출하고, 관련 통합 테스트도 `kosdaq` timeout이 있어도 기존 글 update 경로를 타는 계약을 검증한다.
3. 실제 런타임은 `2026-03-20 09:14`에 시작됐고, state 파일을 `data/state/state.json`으로 옮긴 커밋은 `2026-03-20 10:37`에 들어갔다. 즉 운영 중이던 봇은 state 경로 변경 이전 코드를 메모리에 들고 계속 실행 중이었다.
4. 로컬 최신 state인 `data/state/state.json`에는 오늘자 `kheatmap` post record가 없고 `auto_screenshot_enabled`도 `false`라서, 15:35 자동 게시를 만든 state로 볼 수 없다.
5. 반대로 레거시 경로 `data/heatmaps/state.json`은 조사 시점에 새로 재생성돼 있었고 내용도 거의 비어 있었다. 이건 아직 레거시 state 경로를 바라보는 런타임이 존재하거나, 운영 중 파일/브랜치 전환으로 state 연속성이 깨졌다는 강한 신호다.
- Conclusion:
1. 새 글 생성의 직접 조건은 `오늘자 daily post record를 못 찾았거나 thread/message fetch가 실패한 것`이고, 증거상 더 가능성 높은 쪽은 `스케줄러가 글을 만든 런타임/state와 수동 커맨드가 참조한 state 관점이 갈라진 것`이다.
2. 특히 봇을 내리지 않은 채 같은 워크스페이스에서 브랜치 checkout/커밋/상태 파일 경로 변경을 진행한 것이 이번 drift를 만든 핵심 운영 리스크로 보인다.
- Evidence:
1. `Get-CimInstance Win32_Process` 기준 운영 봇 프로세스 start time은 `2026-03-20 09:14:36`이었다.
2. `git log --format="%h %ad %s" --date=iso-strict -n 20` 기준 state 경로 이동 커밋 `9e4b428 Reorganize state storage and reference docs`는 `2026-03-20T10:37:55+09:00`였다.
3. `data/state/state.json`에는 `commands.kheatmap.daily_posts_by_guild["332110589969039360"]`가 `2026-03-16`까지만 있고, guild config의 `auto_screenshot_enabled`는 `false`였다.
4. `data/heatmaps/state.json`은 조사 시점에 creation/last write가 최신 시각으로 갱신돼 있었고, `watch_poll=no-watch-symbols`만 들어 있는 빈 state였다.
- Status: done

## 2026-03-20
- Context: `master -> develop` sync PR `#10`의 Codex review가 forum resolution helper의 예외 처리 경계를 지적했다.
- Finding:
1. `bot/features/intel_scheduler.py`의 `_resolve_guild_forum_channel_id()`는 `client.fetch_channel()` 실패를 전부 `None`으로 바꿔, transient Discord API 장애도 `missing_forum`/`no-target-forums`로 오인할 수 있었다.
2. 그 결과 `_run_news_job()`와 `_run_eod_job()`는 운영 장애를 `skipped`처럼 보이게 만들어 `/health`와 run log에서 실제 outage를 숨길 수 있었다.
- 3. 첫 번째 guild의 forum resolution 오류에서 job 전체를 바로 `return`하면, 다른 guild까지 같은 tick에서 함께 막히는 cross-guild outage가 생길 수 있었다.
- 4. trading-day skip보다 forum resolution failure를 먼저 처리하면, 휴장일에도 `holiday` 대신 `failed`가 기록되는 false failure가 생길 수 있었다.
- Resolution:
1. `discord.NotFound`만 missing channel로 처리하고, 다른 fetch 오류는 job 레벨까지 전파하도록 helper를 좁혔다.
2. 뉴스/EOD job은 거래일 skip 판정을 forum resolution보다 먼저 수행하도록 순서를 조정했다.
3. forum resolution API 오류는 길드별 failure로 집계하면서, 다른 guild는 계속 처리하도록 바꿨다.
4. 같은 run detail에 `forum_resolution_failures`를 남기고 `failed` status를 기록하도록 맞췄다.
5. 뉴스/EOD 각각에 forum resolution API failure, mixed guild continuation, holiday-precedence 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_intel_scheduler_logic.py -k "forum_resolution or fallback_forum or news_job or eod_job"` 통과 (`24 passed, 4 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#9`의 여섯 번째 Codex review가 `news_briefing`과 `trend_briefing`도 partial guild post failure를 `ok`로 숨기고 있다고 지적했다.
- Finding:
1. `bot/features/intel_scheduler.py`는 `news_briefing` run에서 일부 guild posting이 실패해도, 다른 guild가 성공해 `posted > 0`이면 `news_briefing=ok`를 기록할 수 있었다.
2. 같은 함수는 `trendbriefing`이 일부 guild에서 실패해도 `trend_posted > 0`이면 `trend_briefing=ok`를 남겨 partial outage를 가릴 수 있었다.
- Resolution:
1. `news_briefing`은 이제 `posted > 0 and failed == 0`일 때만 `ok`를 기록한다.
2. `trend_briefing`도 `trend_posted > 0 and trend_failed == 0`일 때만 `ok`를 기록하도록 맞췄다.
3. `tests/integration/test_intel_scheduler_logic.py`에 뉴스 partial post failure, 트렌드 partial post failure 회귀 테스트를 각각 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py -k "news_job or eod_job"` 통과 (`18 passed, 4 deselected`)
2. `.\.venv\Scripts\python -m pytest` 통과 (`82 passed, 2 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#9`의 다섯 번째 Codex review가 `eod_summary`가 일부 guild 실패를 `ok`로 숨길 수 있다고 지적했다.
- Finding:
1. `bot/features/intel_scheduler.py`는 같은 run 안에서 일부 guild EOD post가 실패해도, 다른 guild가 성공해 `posted > 0`이면 `eod_summary=ok`를 남겨 false healthy signal을 만들 수 있었다.
- Resolution:
1. `eod_summary` status는 이제 `posted > 0 and failed == 0`일 때만 `ok`가 되고, 같은 run 안에 실패 guild가 하나라도 있으면 `failed`를 기록하도록 바꿨다.
2. `tests/integration/test_intel_scheduler_logic.py`에 2개 guild 중 1개만 posting 실패하는 partial-failure 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py -k "eod_job"` 통과 (`5 passed, 15 deselected`)
2. `.\.venv\Scripts\python -m pytest` 통과 (`80 passed, 2 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#9`의 네 번째 Codex review가 mixed watch_poll failure 가시성과 forum content state drift를 추가로 지적했다.
- Finding:
1. `bot/features/intel_scheduler.py`는 일부 symbol/guild가 성공해 `processed > 0`이면, 같은 run 안의 `quote_failures`나 `channel_failures`가 있어도 `watch_poll=ok`로 기록할 수 있었다.
2. `bot/forum/service.py`는 삭제 대상 follow-up message가 이미 사라진 경우 `content_message_ids`에서 stale id를 지우지 않아 상태 드리프트가 남을 수 있었다.
- Resolution:
1. `watch_poll`은 `quote_failures`, `channel_failures`, `send_failures` 중 하나라도 있으면 `failed`로 기록하도록 보수적으로 조정했다.
2. 성공 후 quote failure가 뒤따르는 mixed-result watch poll 회귀 테스트를 추가했다.
3. follow-up deletion 루프는 `discord.NotFound`일 때 stale content id를 상태에서 제거하도록 바꿨다.
4. 이미 삭제된 follow-up message id가 state에서 정리되는 forum upsert 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py tests/integration/test_forum_upsert_flow.py` 통과 (`27 passed`)
2. `.\.venv\Scripts\python -m pytest` 통과 (`79 passed, 2 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#9`의 세 번째 Codex review에서 뉴스/EOD 전역 forum fallback의 cross-guild leak 가능성이 지적됐다.
- Finding:
1. `bot/features/intel_scheduler.py`는 `NEWS_TARGET_FORUM_ID`와 `EOD_TARGET_FORUM_ID` fallback을 사용할 때, 해당 forum channel이 현재 `guild_id` 소속인지 검증하지 않아 다른 서버 포럼으로 자동 게시가 새어 나갈 수 있었다.
- Resolution:
1. 뉴스/EOD가 공통으로 쓰는 `_resolve_guild_forum_channel_id()` helper를 추가해 resolved forum channel이 `discord.ForumChannel`이면서 현재 guild 소속일 때만 pending guild로 넣도록 바꿨다.
2. 다른 guild 소속 global fallback forum은 `missing_forum`으로 처리해 provider fetch/posting을 시작하지 않게 했다.
3. 뉴스/EOD 각각에 cross-guild global fallback forum 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 통과 (`18 passed`)
2. `.\.venv\Scripts\python -m pytest` 통과 (`77 passed, 2 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#9`의 두 번째 Codex review가 `watch_poll` delivery failure를 여전히 `ok`로 숨길 수 있다고 지적했다.
- Finding:
1. `bot/features/intel_scheduler.py`는 `channel.send(...)`가 실패해도 `processed > 0`이면 `watch_poll=ok`를 남겨, 실제 알림 delivery 실패가 `/health`에 드러나지 않을 수 있었다.
- Resolution:
1. watch poll run detail에 `alert_attempts`를 추가했다.
2. 알림 전송이 한 건이라도 실패하면 `watch_poll` status를 `failed`로 기록해 false positive를 없앴다.
3. 실제 alert signal은 발생했지만 `channel.send(...)`가 실패하는 회귀 테스트를 `tests/integration/test_intel_scheduler_logic.py`에 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 통과 (`16 passed`)
2. `.\.venv\Scripts\python -m pytest` 통과 (`75 passed, 2 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#9`의 Codex review에서 `watch_poll` 운영 정합성 관련 2건이 나왔다.
- Finding:
1. `bot/features/intel_scheduler.py`는 guild별 watch alert channel이 비어 있을 때 전역 `WATCH_ALERT_CHANNEL_ID` fallback 채널이 다른 guild 소속이어도 그대로 사용해, 멀티 guild 환경에서 다른 서버 채널로 watch alert가 새어 나갈 수 있었다.
2. 같은 함수는 quote fetch나 channel resolution이 전부 실패해도 마지막에 `watch_poll=ok`로 기록해 `/health`가 장애를 숨길 수 있었다.
- Resolution:
1. resolved watch channel은 `discord.abc.Messageable`이면서 현재 `guild_id`와 동일한 guild 소속인지 검증하고, 아니면 해당 guild를 실패로 처리하도록 바꿨다.
2. `watch_poll`은 이번 run의 `processed`, `quote_failures`, `channel_failures`, `missing_channel_guilds`, `send_failures`를 집계해 전부 실패하면 `failed`, 대상이 없으면 `skipped`, 일부라도 처리되면 `ok`로 남기도록 수정했다.
3. 다른 guild fallback 채널 차단과 all-quote-failure status 회귀 테스트를 `tests/integration/test_intel_scheduler_logic.py`에 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 통과 (`15 passed`)
2. `.\.venv\Scripts\python -m pytest` 통과 (`74 passed, 2 deselected`)
- Status: done

## 2026-03-19
- Context: PR `#8`의 Codex review에서 `trendbriefing` 멀티-message upsert와 trend chunking 쪽으로 2건의 후속 이슈가 나왔다.
- Finding:
1. `bot/forum/service.py`는 starter thread 생성 후 follow-up content sync 중 예외가 나면 `daily_posts[today]`가 기록되기 전에 함수가 끝나, 다음 재시도에서 같은 날짜 thread를 새로 만들 수 있었다.
2. `bot/features/news/trend_policy.py`는 첫 번째 theme block 하나만으로 `max_chars`를 넘는 경우에도 안전하게 잘라내지 않아, Discord 2000자 제한을 넘어 게시 실패할 수 있었다.
- Resolution:
1. thread/starter message state는 follow-up content sync 전에 먼저 기록하고, content message ids도 sync 진행 상황에 맞춰 부분적으로 갱신하도록 바꿨다.
2. trend theme block은 line truncation과 oversize block 분할 로직을 추가해, 단일 block이 너무 길어도 region message가 항상 `max_chars` 이내로 나오게 했다.
3. partial-state persistence와 oversized single-block 회귀 테스트를 각각 추가했다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest` 통과 (`72 passed, 2 deselected`)
- Status: done

## 2026-03-18
- Context: PR `#4`의 Codex Connector 재리뷰에서 `news_briefing`/`eod_summary` 상태가 같은 분 내 후속 tick에서 `skipped`로 덮어써질 수 있다는 P1 두 건이 나왔다.
- Finding: 지적은 유효했고, 혼합 설정에서 일부 guild만 성공한 뒤 같은 분의 다음 tick에서 `pending_guilds`가 비고 `missing_forum > 0`이면 이전 성공 상태가 `skipped`로 바뀔 수 있었다.
- Resolution:
1. 뉴스/장마감 모두 pending guild 계산 시 `completed_guilds`를 세어, 이미 당일 성공 처리된 guild가 있으면 no-target early return에서 상태를 덮어쓰지 않도록 수정했다.
2. 같은 분 재실행에서 `ok` 상태가 유지되는 회귀 테스트를 뉴스/EOD 각각 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_intel_scheduler_logic.py` 통과 (`7 passed`)
2. `.\.venv\Scripts\python.exe -m pytest` 통과 (`40 passed, 2 deselected`)
- Status: done

## 2026-03-17
- Context: 최신 `develop` 리뷰에서 나온 intel scheduler/문서 정합성 이슈를 후속 수정으로 반영했다.
- Finding: 이전 리뷰에서 지적한 뉴스 dedup 선소비, job status 거짓 양성, Docker 로그 비영속, README/handoff 부정확성은 모두 유효했고 수정됐다.
- Resolution:
1. 뉴스 브리핑은 fetch 단위에서만 dedup하고, 게시 성공 전에는 전역 dedup 상태를 소비하지 않도록 변경했다.
2. `news_briefing`/`eod_summary`는 실제 게시 결과에 따라 `skipped`/`failed`/`ok`를 구분해 기록하도록 바꿨다.
3. Docker에 `data/logs` 볼륨을 추가했고, README/AGENTS/Session Handoff를 현재 동작과 현재 저장소 상태에 맞게 고쳤다.
4. 재시도 가능성과 status 기록을 검증하는 통합 테스트를 보강했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest` 통과 (`38 passed, 2 deselected`)
- Status: done

## 2026-03-17
- Context: 원격과 동기화된 최신 `develop` 기준으로 새로 추가된 코드/문서를 전체 리뷰했고, 특히 `md` 문서와 실제 구현의 정합성을 대조했다.
- Finding:
1. `bot/features/intel_scheduler.py`의 뉴스 dedup 키를 포스트 성공 전에 먼저 기록해, 포럼 미설정이나 Discord posting 실패가 난 날에는 같은 날짜 재시도에서 뉴스 항목이 영구히 빠질 수 있다.
2. `bot/features/intel_scheduler.py`의 `news_briefing`/`eod_summary`는 실제 게시가 하나도 되지 않아도 `job_last_runs`를 `ok`로 기록해 `/health`와 `/last-run`이 거짓 양성을 낼 수 있다.
3. `docker-compose.yml`은 `data/heatmaps`만 볼륨 마운트하고 있어 새로 추가한 `data/logs/bot.log`가 컨테이너 재생성 시 보존되지 않는다.
4. `README.md`는 `python bot/main.py` 실행과 `!ping` quick test를 안내하지만, 현재 패키지 import 구조와 `message_content=False` 설정 기준으로 둘 다 실제 기본 실행 경로와 맞지 않는다.
5. `docs/context/session-handoff.md` 최상단 엔트리들은 merge/push 이전 상태를 그대로 유지해, 다음 세션 시작 문서로는 현재 저장소 상태를 잘못 안내한다.
- Evidence:
1. 뉴스 dedup은 `mark_news_dedup_seen(...)`가 `upsert_daily_post(...)`보다 먼저 호출된다.
2. 뉴스/장마감 job은 guild loop 결과와 무관하게 마지막에 `set_job_last_run(..., "ok", ...)`를 호출한다.
3. Docker 설정의 볼륨은 `./data/heatmaps:/app/data/heatmaps` 하나뿐이다.
4. `sys.path`를 `python bot/main.py`와 같은 형태로 맞춰 `bot/main.py`를 실행하면 `ModuleNotFoundError: No module named 'bot'`가 재현된다.
5. 현재 HEAD는 merge/push까지 끝난 상태인데 handoff는 여전히 "커밋", "PR 생성", "push"를 다음 액션으로 적고 있다.
- Status: done

## 2026-03-17
- Context: PR `#3`에서 `chatgpt-codex-connector[bot]` 리뷰 코멘트를 반영하는 작업
- Finding: `record_command_sync`가 상태 저장 실패를 그대로 전파해 부트 흐름을 깨뜨릴 수 있다는 지적은 유효했고 수정했다.
- Resolution:
1. 상태 기록을 `bot/app/command_sync.py` 공용 함수로 이동했다.
2. 상태 파일 I/O 실패는 로그만 남기고 삼키도록 fail-open 처리했다.
3. 상태 저장 성공/실패 동작을 검증하는 단위 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `.\.venv\Scripts\python -m pytest` 통과
- Status: done

## 2026-03-17
- Context: 슬래시 커맨드 동기화 실패 시 원인 메시지와 상태 기록을 추가하는 변경 검토
- Finding: 블로킹 이슈는 찾지 못했다.
- Residual risk:
1. 현재 테스트는 에러 메시지 포맷팅 중심이라 `on_ready` 이벤트에서 실제 상태 저장까지는 통합 테스트로 커버하지 않는다.
2. Discord API가 돌려주는 실제 예외 문구가 달라지면 힌트 문구 품질은 일부 흔들릴 수 있다.
- Evidence:
1. `format_command_sync_error()`가 인증/권한/설치/스키마 오류에 대해 사용자 안내 문구를 제공하는지 단위 테스트로 확인했다.
2. 전체 기본 테스트가 `29 passed, 2 deselected`로 통과했다.
- Status: done

## 2026-03-17
- Context: `codex/context-summary` PR 생성, merge, 원격 브랜치 삭제까지 완료한 후 결과를 정리하는 작업
- Finding: PR `#2`는 `develop`에 정상 반영됐고, 원격 브랜치 `codex/context-summary`도 삭제됐다.
- Residual risk:
1. 문서 변경이라 자동 테스트는 별도로 수행하지 않았다.
2. 현재 로컬 작업 디렉터리에는 이 흐름과 무관한 미커밋 변경이 남아 있어 로컬 브랜치는 유지 중이다.
- Evidence:
1. PR `#2`는 `merged=true`, `merge_commit_sha=7f68147a518bf566ef8a2242343ce63db0b0fbb2` 상태를 확인했다.
2. 원격 heads 조회에서 `develop`만 남고 `codex/context-summary`는 사라진 것을 확인했다.
- Status: done

## 2026-03-17
- Context: `codex/context-summary` 브랜치를 `develop` 기준으로 재검토하고 PR 준비 상태를 확인하는 작업
- Finding: 현재 GitHub compare 기준 PR diff는 `docs/reports/sunday-kheatmap-investigation-2026-03-12.md` 1파일, 1커밋이며 막을 만한 문서 정확도 문제는 찾지 못했다.
- Residual risk:
1. 문서 리포트는 운영 조사 메모이므로 자동 테스트 대상이 아니다.
2. PR 생성과 머지는 GitHub 인증이 필요한데, 현재 세션은 `gh` CLI가 없고 브라우저도 로그인되지 않아 자동 완료가 막혀 있다.
- Evidence:
1. compare 화면 기준 `develop...codex/context-summary`는 1 commit / 1 file changed / able to merge 상태였다.
2. 로컬 검토에서 문서가 참조하는 상태 키(`last_run_at`, `last_auto_runs`, `last_auto_skips`, `last_images`)는 현재 코드에 존재함을 확인했다.
- Status: done

## 2026-03-17
- Context: 분류형 컨텍스트 저장 체계를 도입하는 초기 작업
- Finding: 현재 코드 결함 리뷰를 수행한 작업은 아니며, 이번 변경은 작업 메모 구조 추가에 한정됐다.
- Risk:
1. 이후 세션에서 문서를 읽기만 하고 갱신하지 않으면 체계가 빠르게 낡을 수 있다.
2. 구현과 문서가 분리되므로 종료 시점 기록 습관이 중요하다.
- Mitigation:
1. `AGENTS.md`에 세션 종료 체크를 추가해 문서 갱신을 기본 절차로 올렸다.
- Status: open
