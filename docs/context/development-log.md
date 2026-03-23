# Development Log

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
