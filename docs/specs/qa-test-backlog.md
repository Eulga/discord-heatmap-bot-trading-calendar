# QA 테스트 백로그

- 이 문서는 QA 테스트 구현 백로그다.
- 현재 이미 존재하는 테스트 커버리지나 canonical runtime truth를 설명하는 문서는 아니다.

## 문서 목적
- 이 문서는 `2026-03-24` principal-level QA 리뷰를 테스트 구현 백로그로 변환한 명세다.
- 기존 [integration-test-cases.md](./integration-test-cases.md), [integration-live-test-cases.md](./integration-live-test-cases.md)가 "현재 이미 있는 테스트가 무엇을 보호하는지"를 설명한다면, 이 문서는 "앞으로 반드시 추가하거나 강화해야 할 테스트가 무엇인지"를 정의한다.
- 대상 리스크는 state 무결성, mock/live 오동작, watch quote freshness/timezone, scheduler catch-up, Discord duplicate upsert, 권한/운영 표면 보호다.

## 우선순위 기준
- `P0`: 잘못된 게시, state 손실, 중복 게시, 잘못된 알림처럼 즉시 운영 리스크가 큰 항목
- `P1`: 제한 운영 전 반드시 막아야 하는 핵심 회귀 항목
- `P2`: 운영 품질, 관측성, 장기 회귀 방지용 보강 항목

## Unit Test

### UT-01 Corrupt state read does not become authoritative empty state
- Title: corrupt state read blocks destructive save
- Target module: `bot/forum/repository.py`
- Setup: `data/state/state.json`이 깨진 JSON이거나 `OSError`를 내는 읽기 경로를 준비하고, 별도의 last-known-good backup fixture를 둔다.
- Input: `load_state()` 호출 후 같은 state snapshot으로 `save_state()` 또는 state mutation save를 시도한다.
- Expected output: repository는 empty state를 authoritative truth로 반환하지 않고, guarded error 또는 backup restore 결과를 반환한다. destructive save는 차단된다.
- Failure condition guarded against: transient read failure나 JSON corruption 뒤 `commands={}`, `guilds={}`가 저장되어 routing, watchlist, dedupe, provider status가 한 번에 사라지는 문제
- Priority: `P0`

### UT-02 Domestic quote freshness uses source timestamp
- Title: domestic quote uses provider timestamp instead of scheduler now
- Target module: `bot/intel/providers/market.py`
- Setup: KRX quote payload에 실제 체결 시각 필드가 있고, 현재 시각은 장 종료 후 또는 stale window 밖인 상황으로 고정한다.
- Input: `KisMarketDataProvider.get_quote("KRX:005930", now)` 또는 quote normalization helper를 호출한다.
- Expected output: 반환 quote의 `asof`는 provider payload 기준 시각을 사용하고, freshness check는 stale/off-hours를 `failed` 또는 `skipped`로 분류한다.
- Failure condition guarded against: 국내 stale quote가 항상 fresh로 판정되어 off-hours alert나 false healthy status가 발생하는 문제
- Priority: `P0`

### UT-03 Overseas quote time normalization uses exchange-local timezone
- Title: overseas quote parsing respects exchange-local timezone and DST
- Target module: `bot/intel/providers/market.py`
- Setup: 미국장 `khms`와 quote date를 가진 payload를 준비하고, DST 경계일과 장 시작/종료 직전 시각 fixture를 만든다.
- Input: overseas quote parse helper 또는 `get_quote("NAS:AAPL", now_kst)`를 호출한다.
- Expected output: `asof`는 미국 거래소 현지 시각 기준으로 해석된 aware datetime이며, freshness 판정이 session boundary와 일치한다.
- Failure condition guarded against: KST 기준 파싱으로 US quote가 미래 시각처럼 보이거나 stale/fresh가 뒤집히는 문제
- Priority: `P0`

### UT-04 Hybrid news preserves healthy region on partial provider failure
- Title: hybrid news analysis degrades by region instead of failing globally
- Target module: `bot/intel/providers/news.py`
- Setup: domestic provider는 정상 `AnalysisResult`를 반환하고 global provider는 timeout 또는 auth error를 던지는 fixture를 준비한다. 반대 조합도 함께 준비한다.
- Input: `HybridNewsProvider.analyze(now)` 호출
- Expected output: healthy region 결과는 유지되고 실패한 region만 degraded detail로 표기된다. 함수 전체가 hard fail하지 않는다.
- Failure condition guarded against: global provider 한쪽 장애가 domestic briefing까지 전부 막아 버리는 문제
- Priority: `P1`

### UT-05 Production provider factory fails closed when only mock providers are available
- Title: provider mode selection refuses mock-only posting in production
- Target module: `bot/features/intel_scheduler.py`
- Setup: `EOD_SUMMARY_ENABLED=true` 또는 news/watch 기능 활성 상태에서 live credential/provider kind가 비어 있거나 mock-only인 설정 fixture를 준비한다.
- Input: scheduler provider builder 또는 job entrypoint를 호출한다.
- Expected output: runtime mode는 `mock` 또는 `disabled`로 명시되고, production posting path는 실행되지 않는다. operator-visible status는 misconfigured 상태를 기록한다.
- Failure condition guarded against: mock EOD/news/watch output이 live production 콘텐츠처럼 게시되는 문제
- Priority: `P0`

## Integration Test

### IT-01 Daily news scheduler performs same-day catch-up after late start
- Title: daily scheduler catches up once when startup is after schedule
- Target module: `bot/features/intel_scheduler.py`
- Setup: 해당 날짜의 `news_briefing` 성공 기록이 없고, 현재 시각은 configured schedule보다 늦은 상태로 고정한다.
- Input: scheduler tick 또는 `_run_news_job(now)` 진입을 호출한다.
- Expected output: same-day catch-up run이 정확히 1회 실행되고, 성공 시 last-run state가 오늘 날짜로 기록된다. 이후 같은 날짜 추가 tick은 중복 실행하지 않는다.
- Failure condition guarded against: 재배포, reconnect, event loop stall 후 하루치 뉴스가 통째로 누락되는 문제
- Priority: `P1`

### IT-02 Forum upsert does not recreate content on transient Discord fetch failure
- Title: forum upsert distinguishes NotFound from transient fetch failure
- Target module: `bot/forum/service.py`
- Setup: 이미 존재하는 thread/starter/content message state를 준비하고, fetch 경로에서 `HTTPException` 또는 `Forbidden`을 발생시키는 Discord fake를 둔다.
- Input: `upsert_daily_post()` 호출
- Expected output: 함수는 retriable failure를 반환하거나 예외를 상위로 전달하되, 새 thread/message를 만들지 않는다. `NotFound`일 때만 recreate 경로가 열린다.
- Failure condition guarded against: transient Discord 장애 때 same-day duplicate thread나 duplicate trend chunk가 생성되는 문제
- Priority: `P1`

### IT-03 Setup commands reject channels the bot cannot actually use
- Title: setup commands validate effective bot permissions
- Target module: `bot/features/admin/command.py`
- Setup: guild admin interaction fixture와, 타입은 맞지만 bot에 `send_messages`, `create_public_threads`, `send_messages_in_threads`, message cleanup에 필요한 권한 등이 부족한 channel/forum fake를 준비한다.
- Input: `/setforumchannel`, `/setnewsforum`, `/seteodforum`, `/setwatchforum` handler 호출
- Expected output: command는 permission-specific 에러로 실패하고 state를 저장하지 않는다.
- Failure condition guarded against: 설정 단계는 성공처럼 보이지만 실제 스케줄러 게시 시점에만 실패가 드러나는 latent misconfiguration
- Priority: `P1`

### IT-04 Watch poll aggregates provider health per poll instead of last-symbol-wins
- Title: watch provider health is aggregated once per poll
- Target module: `bot/features/intel_scheduler.py`
- Setup: watchlist에 두 심볼을 두고 첫 번째는 quote failure, 두 번째는 정상 quote를 반환하도록 provider stub을 준비한다.
- Input: `_run_watch_poll(now)` 호출
- Expected output: `provider_status.kis_quote` 또는 해당 provider status는 partial degradation을 요약한 단일 결과를 기록한다. 마지막 심볼 결과로 덮어쓰지 않는다.
- Failure condition guarded against: `/source-status`가 degraded poll을 healthy로 잘못 보여 주거나 반대로 healthy poll을 failed처럼 보이게 하는 문제
- Priority: `P2`

### IT-05 Status commands enforce operator-only diagnostics
- Title: operational diagnostics require operator authorization
- Target module: `bot/features/status/command.py`
- Setup: 동일 guild에서 admin/owner/global-admin/non-admin interaction fixture를 준비하고 provider/job failure detail이 긴 상태 snapshot을 둔다.
- Input: `/health`, `/last-run`, `/source-status` handler 호출
- Expected output: authorized actor만 상세 진단을 받고, unauthorized actor는 거절 또는 public-safe 축약 응답을 받는다.
- Failure condition guarded against: 일반 guild member에게 provider failure, credential-missing, schedule metadata가 그대로 노출되는 문제
- Priority: `P1`

### IT-06 Watch add is route-gated and provisions exactly one symbol thread
- Title: watch add rejects missing forum route and reuses symbol thread
- Target module: `bot/features/watch/command.py`, `bot/features/intel_scheduler.py`, `bot/forum/repository.py`
- Setup: guild state에 `watch_forum_channel_id`가 없는 상태와 있는 상태를 각각 준비하고, 동일 symbol에 대한 existing thread mapping fixture를 둔다.
- Input: route 없는 상태의 `/watch add`, route 설정 후 첫 `/watch add`, 같은 symbol에 대한 재등록 또는 재추가 경로를 순서대로 호출한다.
- Expected output: route가 없으면 `/watch add`는 명시적으로 거절되고 state mutation이나 orphan thread가 생기지 않는다. route가 있으면 symbol thread가 정확히 1개만 생성 또는 재사용된다.
- Failure condition guarded against: forum route 없는 orphan watch state, duplicate symbol thread, broken thread reuse
- Priority: `P1`

### IT-07 First eligible poll after close finalizes the last unfinalized session exactly once
- Title: close finalization catches up once after delayed startup
- Target module: `bot/features/intel_scheduler.py`
- Setup: regular session close를 지난 시각 fixture, intraday comment가 남아 있는 unfinalized session state, regular close price와 after-hours current price가 서로 다른 close snapshot, 그리고 restart 또는 delayed startup 상황을 준비한다.
- Input: close 이후 첫 eligible `_run_watch_poll(now)` 또는 scheduler tick을 호출한 뒤 같은 off-hours tick을 다시 호출한다.
- Expected output: 첫 eligible poll만 intraday comment를 삭제하고 `마감가 알림`을 1건 남긴다. close summary의 `마감가`는 after-hours current price가 아니라 official regular close price를 사용한다. 같은 `session_date`에 대해서는 restart 뒤에도 duplicate close comment가 생기지 않는다.
- Failure condition guarded against: missed close 뒤 intraday comment 영구 잔류, after-hours 가격을 종가로 오인, restart 후 duplicate close summary
- Priority: `P1`

### IT-08 Remove during session still finalizes once and then stops
- Title: removed symbol cleans up intraday state with one last close finalization
- Target module: `bot/features/watch/command.py`, `bot/features/intel_scheduler.py`
- Setup: current session에 intraday comment가 이미 생성된 symbol thread와, mid-session remove가 수행된 상태를 준비한다.
- Input: `/watch remove` 후 close 이후 첫 eligible scheduler tick을 호출한다.
- Expected output: starter는 inactive로 바뀌고 신규 intraday update는 멈춘다. 다만 해당 session의 intraday comment는 정리되고 `마감가 알림`은 정확히 1건 남는다. 이후 추가 tick은 아무것도 다시 만들지 않는다.
- Failure condition guarded against: remove 뒤 intraday comment 방치, close summary 누락, remove 뒤 재가동 시 duplicate finalization
- Priority: `P1`

## E2E Test

### E2E-01 Admin-configured live news run posts only live-configured content
- Title: live news run uses configured forum and real provider mode only
- Target module: `bot/features/admin/command.py`, `bot/features/intel_scheduler.py`, `bot/forum/service.py`
- Setup: test guild, 실제 posting 가능한 forum channel, live news provider credential, `NEWS_PROVIDER_KIND=hybrid|naver|marketaux` 중 운영 설정과 일치하는 환경을 준비한다.
- Input: admin이 `/setnewsforum`을 실행한 뒤 manual run 또는 scheduled news run을 1회 수행한다.
- Expected output: 지정한 guild forum에만 thread가 생성 또는 업데이트되고, status/detail은 live provider mode를 반영한다. mock placeholder는 게시되지 않는다.
- Failure condition guarded against: routing 오설정, mock/live 혼선, guild 간 cross-posting
- Priority: `P1`

### E2E-02 Restart after partial post resumes without duplicate same-day thread
- Title: restart recovery reuses partially created thread
- Target module: `bot/features/intel_scheduler.py`, `bot/forum/service.py`, `bot/forum/repository.py`
- Setup: 첫 실행에서 same-day news 또는 trend thread는 생성됐지만 follow-up content 또는 job-final save 전에 프로세스가 중단된 상태를 만든다.
- Input: 프로세스 재시작 후 같은 날짜 job을 다시 실행한다.
- Expected output: 기존 thread를 재사용하고 빠진 starter/content/state만 복구한다. duplicate same-day thread는 생기지 않는다.
- Failure condition guarded against: 재시작이나 redeploy 직후 partial post가 duplicate posting으로 증폭되는 문제
- Priority: `P1`

### E2E-03 Watch route gating and guild-scoped symbol threads stay isolated end to end
- Title: watch add is route-gated and thread posting stays inside the configured guild forum
- Target module: `bot/features/watch/command.py`, `bot/features/intel_scheduler.py`, `bot/forum/repository.py`
- Setup: guild A와 guild B를 준비하고, guild A에는 regular user와 admin을 둔다. guild별 watch forum route는 서로 다르게 설정한다.
- Input: guild A regular user의 route 없는 `/watch add`, admin의 `/setwatchforum`, 이후 같은 user의 `/watch add`, poll 1회를 순서대로 수행한다.
- Expected output: route 없는 첫 add는 거절된다. route 설정 후 add는 guild A forum 안에만 symbol thread를 만들고 starter/comment도 같은 guild thread에만 남는다. guild B state와 forum은 변하지 않는다.
- Failure condition guarded against: orphan watch state, cross-guild thread leakage, 잘못된 forum route 해석
- Priority: `P1`

## Regression Test

### RG-01 Empty regional briefing must not report plain ok
- Title: empty region yields partial or empty-region status
- Target module: `bot/features/intel_scheduler.py`
- Setup: domestic 결과는 비어 있고 global 결과만 정상인 분석 결과 fixture를 준비한다. 반대 조합도 포함한다.
- Input: `_run_news_job(now)` 호출
- Expected output: thread가 생성되더라도 최종 `job_last_runs.news_briefing.status`는 `partial` 또는 `failed-empty-region` 계열이다. plain `ok`는 아니다.
- Failure condition guarded against: `(데이터 없음)` placeholder thread가 올라갔는데도 운영자가 healthy post로 오판하는 문제
- Priority: `P1`

### RG-02 Status commands stay under Discord message length limits
- Title: long diagnostics are chunked or truncated deterministically
- Target module: `bot/features/status/command.py`
- Setup: provider failure detail, job history, warning string을 길게 늘린 state snapshot을 준비한다.
- Input: `/health`, `/source-status`, `/last-run` handler 호출
- Expected output: 응답은 Discord 메시지 길이 제한을 넘지 않고, chunk 또는 truncation 정책이 deterministic하게 적용된다.
- Failure condition guarded against: 장애가 커질수록 status command 자체가 2000자 제한에 걸려 실패하는 문제
- Priority: `P2`

### RG-03 Runtime registry corruption falls back to bundled snapshot
- Title: invalid runtime registry falls back safely to bundled registry
- Target module: `bot/intel/instrument_registry.py`
- Setup: `data/state/instrument_registry.json`을 invalid JSON으로 만들고, bundled registry는 정상 fixture를 둔다.
- Input: registry load와 symbol resolution 호출
- Expected output: runtime registry는 폐기되고 bundled registry가 active source로 로드된다. degraded status는 기록되지만 symbol resolution은 계속 동작한다.
- Failure condition guarded against: runtime artifact corruption이 전체 symbol lookup 실패로 번지는 문제
- Priority: `P2`

### RG-04 Watch add remains route-gated and symbol thread reuse stays deterministic
- Title: watch add rejects missing forum route and does not duplicate symbol threads
- Target module: `bot/features/watch/command.py`, `bot/features/intel_scheduler.py`
- Setup: route 미설정 guild, route 설정 guild, existing symbol thread mapping, stale thread mapping 복구 fixture를 준비한다.
- Input: `/watch add`와 subsequent poll/recovery 경로를 호출한다.
- Expected output: route 없이는 add가 거절되고, route가 있으면 동일 guild-symbol은 thread를 하나만 유지한다. stale mapping 복구 후에도 duplicate thread가 생기지 않는다.
- Failure condition guarded against: route gating 회귀, duplicate symbol thread, broken recreate semantics
- Priority: `P1`

### RG-05 Marketaux trend classification uses wider metadata than title-only fallback
- Title: global trend analysis uses description and entities in theme matching
- Target module: `bot/intel/providers/news.py`
- Setup: headline만 보면 약하지만 description/entities에는 `Fed`, `Treasury yields`, `Apple`, `Nvidia` 같은 강한 시그널이 있는 Marketaux article fixture를 준비한다.
- Input: global trend analyze path를 호출한다.
- Expected output: relevant theme가 최소 1개 이상 선택되고, briefing title-only fallback보다 recall이 높다.
- Failure condition guarded against: 영어 글로벌 기사에서 title-only fallback 때문에 real theme가 누락되는 문제
- Priority: `P2`

### RG-06 Watch 3% ladder edge transitions remain stable
- Title: multi-band jump, retrace, reversal, and restart do not re-emit old bands
- Target module: `bot/features/intel_scheduler.py`
- Setup: `highest_up_band/highest_down_band` state와 thread fixtures를 준비하고, `+2.9 -> +9.2`, `+9.2 -> +4.0`, `+9.2 -> -6.4`, mid-session restart 시나리오를 순차적으로 재현한다.
- Input: 해당 quote sequence로 poll을 여러 번 호출한다.
- Expected output: `+9.2`에서는 최고 신규 `+9%` comment 1건만 생성되고 `highest_up_band=3`이 된다. retrace에서는 새 comment가 없고, reversal에서는 `-6%` comment 1건만 추가된다. restart 뒤에도 이미 지난 band는 재발송되지 않는다.
- Failure condition guarded against: ladder jump flood, retrace duplicate comment, reversal semantics drift, restart 후 band 재발송
- Priority: `P1`

### RG-07 Close history persists across sessions without duplicate finalization
- Title: close comments accumulate by session and are never cleaned by next-day rollover
- Target module: `bot/features/intel_scheduler.py`, `bot/forum/repository.py`
- Setup: 이틀 연속으로 symbol thread가 close finalization까지 수행된 상태와 next-day startup fixture를 준비한다.
- Input: 두 연속 session의 close finalization과 다음날 off-hours tick을 호출한다.
- Expected output: `마감가 알림` comment는 session별로 distinct하게 보존되고, next-day cleanup은 이전 session close comment를 삭제하지 않는다. 이미 finalized된 session에는 duplicate close comment가 생기지 않는다.
- Failure condition guarded against: close history 유실, next-day cleanup 오작동, duplicate close summary
- Priority: `P1`

## Failure Injection Test

### FI-01 Bootstrap state save failure does not block bot startup
- Title: bootstrap save failure is isolated from bot startup
- Target module: `bot/app/bot_client.py`
- Setup: startup bootstrap에서 env bootstrap channel을 state에 복사하려는 상황을 만들고, repository save가 `OSError`를 던지게 한다.
- Input: bot startup bootstrap path 실행
- Expected output: bootstrap failure는 warning/error로만 기록되고, command sync와 scheduler startup은 계속 진행된다.
- Failure condition guarded against: 단순 state save 실패가 bot 전체 부트를 깨뜨리는 문제
- Priority: `P1`

### FI-02 Off-hours watch poll only finalizes once and never reopens intraday updates
- Title: first poll after close finalizes once, later off-hours polls no-op
- Target module: `bot/features/intel_scheduler.py`
- Setup: KRX/US watch symbols가 등록된 상태에서 close 직후 poll, 이후 off-hours poll, pre-market poll fixture를 준비하고 unfinalized intraday state를 둔다.
- Input: `_run_watch_poll(now)`를 close 직후, late off-hours, next pre-market 순서로 호출한다.
- Expected output: 첫 eligible close 이후 poll만 finalization을 수행한다. 이후 off-hours와 pre-market poll은 intraday starter edit나 신규 band comment를 만들지 않는다. 이미 finalized된 session에 duplicate close comment도 생기지 않는다.
- Failure condition guarded against: after-hours comment 재개, duplicate close finalization, pre-market overwrite, off-hours를 quote failure로 오분류하는 문제
- Priority: `P1`

### FI-03 Missing session close price defers close finalization until retry
- Title: same-session off-hours snapshot without session close price stays unfinalized
- Target module: `bot/features/intel_scheduler.py`
- Setup: close 직후 off-hours snapshot의 `current_price`는 존재하지만 `session_close_price`가 `null`인 상태와, 다음 poll에서는 same-session official regular close price가 채워지는 fixture를 준비한다.
- Input: `session_close_price`가 비어 있는 첫 off-hours `_run_watch_poll(now)` 뒤에 값이 채워진 다음 off-hours poll을 다시 호출한다.
- Expected output: 첫 poll은 `마감가 알림`을 만들지 않고 session을 unfinalized 상태로 유지한다. 다음 poll에서 `session_close_price`가 들어오면 close finalization이 정확히 1회 수행된다.
- Failure condition guarded against: official close 미도착 상태에서 after-hours current price를 종가로 오인, null close price를 가진 성급한 finalization, retry 누락
- Priority: `P1`

### FI-04 Partial close finalization retry does not duplicate close summary
- Title: delete/create/save mid-failure is recovered idempotently on next off-hours poll
- Target module: `bot/features/intel_scheduler.py`, `bot/forum/repository.py`
- Setup: unfinalized session에 intraday comment 여러 개와 close snapshot을 준비하고, 첫 close finalization 시도에서 `intraday comment delete 일부 성공 후 failure`, `close comment create 성공 후 state save failure`, `checkpoint save 성공 후 finalization flag save failure`를 각각 강제로 발생시킨다.
- Input: 실패를 유발한 첫 off-hours `_run_watch_poll(now)` 뒤에 다음 off-hours poll을 다시 호출한다.
- Expected output: retry는 이미 삭제된 intraday comment의 `NotFound`를 허용적으로 처리하고, same-session `마감가 알림`을 중복 생성하지 않는다. 최종 state는 `close_comment_ids_by_session`와 finalized marker가 실제 Discord 상태와 일치한다.
- Failure condition guarded against: partial side-effect 뒤 duplicate close summary, delete retry crash, state/Discord 불일치 영구 잔류
- Priority: `P1`

### FI-05 Concurrent state mutations preserve both updates
- Title: concurrent command and scheduler writes do not drop unrelated state
- Target module: `bot/forum/repository.py`, `bot/features/intel_scheduler.py`, `bot/features/watch/command.py`
- Setup: command path는 watchlist 변경을, scheduler path는 job/provider status 변경을 각각 수행하도록 하고 두 save가 겹치게 만든다.
- Input: 두 mutation을 동시에 실행한다.
- Expected output: 저장 결과에는 watchlist 변경과 scheduler state 변경이 모두 살아 있다. mutation ordering은 deterministic하거나 serialization lock으로 보호된다.
- Failure condition guarded against: load-modify-save race로 마지막 writer만 살아남아 routing, watchlist, job state가 조용히 유실되는 문제
- Priority: `P0`

### FI-06 Crash after first guild post checkpoints progress before rerun
- Title: crash mid-loop does not duplicate first guild on rerun
- Target module: `bot/features/intel_scheduler.py`
- Setup: 두 guild를 대상으로 한 news 또는 EOD loop를 준비하고, 첫 guild posting 성공 직후 프로세스가 종료되는 failure hook을 건다.
- Input: 첫 실행에서 crash를 유도한 뒤, 재시작 후 같은 job을 다시 실행한다.
- Expected output: 첫 guild는 이미 완료된 post를 재사용하거나 skip하고, 두 번째 guild만 이어서 처리한다. duplicate post는 생기지 않는다.
- Failure condition guarded against: job-end save만 믿다가 mid-loop crash 후 이미 처리한 guild를 다시 게시하는 문제
- Priority: `P1`

### FI-07 Partial Discord API outage does not mislead operators into reconfiguration
- Title: transient forum fetch outage returns temporary failure instead of config advice
- Target module: `bot/features/runner.py`
- Setup: guild state의 forum channel mapping은 정상이지만 `fetch_channel()`이 transient error를 내는 fake client를 준비한다.
- Input: `/kheatmap` 또는 `/usheatmap` manual run handler 호출
- Expected output: 사용자 메시지는 temporary Discord/API failure를 안내하고, `/setforumchannel` 재설정을 요구하지 않는다.
- Failure condition guarded against: transient Discord outage를 bad configuration으로 오진해 운영자가 잘못된 재설정을 하게 되는 문제
- Priority: `P2`
