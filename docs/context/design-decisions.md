# Design Decisions

## 2026-03-27
- Context: watch poll band label이 fractional threshold를 쓰더라도 정수 `%` 문구로 보이는 것이 다시 리뷰 finding으로 올라왔고, 사용자는 이 표현을 의도된 운영 규칙으로 유지하길 원했다.
- Decision: watch band comment label의 `%` 숫자는 계속 `int(WATCH_ALERT_THRESHOLD_PCT) * band`를 사용한다. fractional threshold를 써도 label은 정수 step으로 보일 수 있으며, 실제 trigger 판단은 float threshold와 exact `change_pct`를 그대로 사용한다.
- Why:
1. band label은 사용자에게 “대략 몇 % 구간대냐”를 짧게 보여주는 역할이고, 실제 세부 수치는 뒤에 붙는 exact signed percent가 이미 제공한다.
2. 기존 운영 의도는 label을 간결하게 유지하는 것이며, threshold float를 그대로 label에 노출하는 것은 현재 UX 목표가 아니다.
3. 이 동작을 설계 결정으로 명시해 두면, 이후 전체 리뷰에서 intentional behavior를 반복해서 결함으로 해석하는 일을 줄일 수 있다.
- Impact:
1. `WATCH_ALERT_THRESHOLD_PCT=2.5` 같은 설정에서도 label은 `+2%`, `+4%`처럼 보일 수 있다.
2. 실제 alert trigger와 trailing signed percent는 계속 fractional threshold 기준을 따른다.
3. current-truth spec과 functional spec은 이 의도를 같은 표현으로 설명해야 한다.
- Status: accepted

## 2026-03-26
- Context: 사용자가 watch 기능의 목표 동작을 `text alert + first-seen baseline`에서 `forum thread + previous_close basis` 모델로 고정한 뒤, intraday notification을 더 적극적으로 남기되 thread 오염은 장마감 정리로 제어하자고 요청했다.
- Decision: watch rollout의 목표 모델은 `길드 공유 watchlist + guild-symbol persistent forum thread + Discord thread follow 기반 개인 notification`으로 둔다. 기준가는 `전일 종가(previous_close)`로 고정하고, starter message는 regular session open 중 poll마다 현재 상태를 갱신한다. intraday comment는 전일 종가 대비 `3% band ladder`(`+3,+6,+9...`, `-3,-6,-9...`) 기준으로 생성하되, 한 poll에서 여러 단계를 건너뛰면 최고 신규 band 1건만 남긴다. `세션`은 symbol market의 regular-session trading date, 즉 market-local `당일`을 뜻한다. intraday starter edit와 band detection은 regular session open 동안만 허용한다. regular session close 후 off-hours poll은 마지막 unfinalized session에 대한 close finalization만 시도하고, first eligible poll after close 기준으로 정확히 1회만 완료돼야 한다. intraday comment는 close finalization 시 모두 삭제하고, 대신 `날짜/전일 종가/official regular close price/최종 변동률`을 담은 `마감가 알림` comment 1건을 영구 보존한다. `마감가`는 after-hours current price가 아니라 same-session official regular close price를 사용한다. close finalization은 same-session close comment를 재사용할 수 있어야 하며, `close_comment_ids_by_session` checkpoint와 finalization 완료 마킹을 분리해 partial failure retry 뒤에도 duplicate close summary를 만들지 않아야 한다. 또한 `watch_forum_channel_id`가 없으면 `/watch add`를 명시적으로 거절한다. symbol이 mid-session remove되더라도 해당 session이 unfinalized라면 close finalization은 1회 수행한다.
- Why:
1. 종목별 persistent thread는 길드 공유 surface와 개인별 follow UX를 동시에 만족시킨다.
2. 전일 종가 기준은 기존 first-seen baseline보다 intraday 해석이 더 일관되고, 재시작 시점에 따라 기준가가 흔들리는 문제를 줄인다.
3. 3% band ladder는 watch 기능의 본래 목적에 맞게 의미 있는 변동을 더 적극적으로 포착한다.
4. intraday comment를 장마감에 정리하고 close summary만 남기면 notification 빈도와 thread 장기 가독성을 함께 관리할 수 있다.
5. regular-session gate와 close catch-up contract를 명시하면 pre/post-market drift와 restart ambiguity를 줄일 수 있다.
6. add 시점 route gating은 thread 없는 orphan watch state를 막는다.
- Impact:
1. target model의 authoritative watch route는 `watch_forum_channel_id`다.
2. 기존 `watch_alert_channel_id`, `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`는 target model의 최종 authoritative state가 아니다.
3. watch quote adapter는 external `price`를 internal `WatchSnapshot.current_price`로, external `session_close_price`를 internal `WatchSnapshot.session_close_price`로 정규화하고, `previous_close`와 `session_date`를 함께 scheduler에 제공해야 한다.
4. scheduler는 intraday band history, close finalization, close summary persistence, first-eligible-poll catch-up, partial failure retry reconciliation을 관리해야 한다.
- Status: accepted

## 2026-03-24
- Context: 뉴스 포스트가 explicit news forum 설정 없이도 기본 guild forum으로 생성되어, operator 입장에서 hidden fallback처럼 보이는 문제가 확인됐다.
- Decision: 뉴스/트렌드 게시 경로는 explicit `news_forum_channel_id`가 있는 길드만 대상으로 본다. `forum_channel_id`는 뉴스 runtime fallback으로 사용하지 않는다. `NEWS_TARGET_FORUM_ID`는 startup에서 `news_forum_channel_id`를 채우는 bootstrap initializer로만 유지한다.
- Why:
1. operator는 news-specific forum을 따로 설정하지 않았으면 뉴스가 게시되지 않는다고 기대하는 편이 자연스럽다.
2. `forum_channel_id` fallback은 cross-posting과 hidden routing을 만들고, 현재 state만 보고도 “왜 게시됐는지”를 혼동하게 한다.
3. startup bootstrap과 runtime fallback을 분리하면 env default는 유지하면서도 실제 게시 허용 조건은 더 예측 가능해진다.
- Impact:
1. `news_forum_channel_id`가 없는 길드는 `forum_channel_id`만 있어도 뉴스/트렌드 자동 게시 대상이 아니다.
2. `/setnewsforum`으로 explicit route를 넣거나 startup bootstrap이 `news_forum_channel_id`를 채운 경우에만 뉴스/트렌드 게시가 가능하다.
3. heatmap, EOD, watch routing 정책은 이번 결정 범위에 포함되지 않는다.
- Status: accepted

## 2026-03-23
- Context: 사용자가 `watch_poll`에서 같은 방향으로 이미 한 번 보낸 변동 알림이 10분 cooldown 뒤 다시 오는 것은 원치 않는다고 보고했다.
- Decision: watch 알림은 `cooldown only`가 아니라 `same-direction latch + cooldown` 조합으로 운영한다. 즉 같은 심볼이 같은 방향 임계치 밖에 계속 머무르면 첫 알림만 보내고, 임계치 안으로 한 번 복귀해야 같은 방향 알림을 다시 허용한다.
- Why:
1. 기존 cooldown-only 구조는 연속 하락/상승 구간에서 사용자가 이미 알고 있는 상태를 주기적으로 다시 알려 불필요한 중복 알림을 만든다.
2. 반면 latch만 두고 cooldown을 없애면 threshold 근처에서 안팎으로 출렁일 때 짧은 간격 재알림이 생길 수 있다.
3. `same-direction latch + cooldown`이면 `연속 추세 중복`과 `threshold chatter`를 동시에 줄이면서, 반대 방향 전환은 그대로 포착할 수 있다.
- Impact:
1. guild state에 `watch_alert_latches`가 추가된다.
2. 같은 방향 재알림은 price가 baseline 대비 threshold 안으로 되돌아와 latch가 해제될 때까지 억제된다.
3. 반대 방향 신호는 기존처럼 별도 cooldown key를 사용하므로 계속 알림 가능하다.
- Status: accepted

## 2026-03-23
- Context: 사용자가 앞으로의 최우선 운영 규칙으로 env와 state의 역할을 더 명확히 나누고, 이후 코드리뷰도 이 기준으로 거절할 것은 거절하자고 요청했다.
- Decision: 이 저장소의 설정 원칙은 `민감정보는 env`, `mutable 운영 라우팅은 state`로 고정한다. channel/forum/watch routing 값은 state를 source of truth로 두고, env의 channel/forum IDs는 bootstrap, 개발 초기값, 테스트 기본값으로만 허용한다.
- Why:
1. API 토큰, 시크릿, 자격증명은 배포 환경별 주입과 비노출 관리가 중요하므로 env 계층에 두는 편이 맞다.
2. 반대로 channel/forum ID 같은 Discord 라우팅 값은 시크릿이 아니고 길드별로 바뀌는 운영 상태값이라 state에서 관리해야 멀티 길드 정합성이 맞다.
3. 이 원칙이 약하면 env fallback이 다시 runtime source of truth로 스며들고, 반대로 시크릿이 state/docs로 흘러 들어갈 수 있다.
4. 리뷰 기준을 문서로 고정해 두면 이후 refactor나 신규 기능 구현에서도 같은 종류의 잘못된 저장 위치 선택을 더 빨리 차단할 수 있다.
- Impact:
1. `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`는 bootstrap-only legacy/default 값으로만 취급한다.
2. 새 기능이 길드별 채널/포럼/라우팅 값을 다룰 때는 먼저 state schema를 검토하고, env 우선 설계를 기본안으로 삼지 않는다.
3. 코드리뷰는 이제 `민감정보는 env, mutable routing은 state`를 explicit acceptance gate로 사용한다.
4. 예외적으로 env authoritative가 필요한 경우는 사전 문서화 없이는 허용하지 않는다.
- Status: accepted

## 2026-03-23
- Context: 실운영에서 env에 남아 있던 forum/text channel IDs가 다른 길드에서도 runtime fallback처럼 읽혀, 멀티 길드 heatmap/news/eod/watch 라우팅을 흔들고 있었다.
- Decision: Discord channel routing의 source of truth는 `data/state/state.json`으로 통일한다. env channel IDs는 runtime fallback이 아니라 startup bootstrap 용도로만 유지하고, 실제 실행 경로는 per-guild state만 읽는다.
- Why:
1. channel ID는 시크릿이 아니라 운영 라우팅 데이터라서, 멀티 길드 봇에서는 env보다 state가 더 자연스럽고 변경 이력도 명확하다.
2. 단일 env channel ID는 특정 한 길드의 채널일 가능성이 높은데, 이를 cross-guild fallback으로 쓰면 다른 길드에서 foreign channel로 잘못 라우팅되거나 기능이 실패한다.
3. `/setforumchannel`, `/setnewsforum`, `/seteodforum`, `/setwatchchannel`이 이미 state를 쓰고 있으므로 runtime도 같은 source를 보는 편이 일관된다.
- Impact:
1. `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`는 startup에서 matching guild state가 비어 있을 때만 bootstrap한다.
2. heatmap runner와 intel scheduler는 runtime에 env channel IDs를 직접 fallback으로 읽지 않는다.
3. heatmap 실행은 state에 저장된 forum channel이 삭제됐거나 다른 guild channel이면 명시적으로 재설정을 요구한다.
- Status: accepted

## 2026-03-23
- Context: watch autocomplete coverage를 ELW/PF까지 넓히고, 신규 상장/상장폐지를 더 빨리 반영할 수 있게 bot 내부 daily refresh를 붙이기로 했다.
- Decision: instrument registry는 `bundled snapshot + optional runtime refresh override` 구조로 운영한다. repo에 체크인된 기본 artifact는 유지하고, bot scheduler가 성공적으로 full rebuild 했을 때만 `data/state/instrument_registry.json` runtime override를 교체한다.
- Why:
1. slash command autocomplete hot path는 여전히 local registry snapshot이 가장 안정적이고, 매 입력마다 live search API를 호출하는 구조는 rate limit과 응답 지연 리스크가 크다.
2. Docker 운영에서 `data/state`는 이미 mount돼 있으므로 runtime refresh artifact를 여기에 두면 container recreate 뒤에도 refresh 결과를 보존할 수 있다.
3. refresh가 일부 source 실패 상태에서 partial artifact를 남기면 autocomplete 기준선이 흔들리므로, full rebuild 성공 시에만 atomic replace 하는 fail-closed가 안전하다.
4. KRX coverage는 상장사(OpenDART)만으로 충분하지 않고, 실제 누락분은 ETF/ETN에 더해 ELW/PF 같은 structured product군이어서 KRX finder family를 함께 묶는 편이 맞다.
- Impact:
1. runtime load 순서는 `data/state/instrument_registry.json -> bot/intel/data/instrument_registry.json -> seed`다.
2. 새 env는 `INSTRUMENT_REGISTRY_REFRESH_ENABLED`, `INSTRUMENT_REGISTRY_REFRESH_TIME`이고, 기본값은 disabled다.
3. `/source-status`의 `instrument_registry` row는 현재 active source(`runtime|bundled`)와 loaded counts를 보여주고, `/last-run`은 `instrument_registry_refresh` job row를 노출한다.
4. 이번 단계는 `added/removed` summary까지만 남기며, inactive/delisted marker와 watchlist reconciliation report는 후속 작업으로 남긴다.
- Status: accepted

## 2026-03-23
- Context: watch autocomplete coverage를 KRX ETF/ETN까지 넓힌 뒤, 사용자가 신규 상장 상품과 상장폐지 상품을 앞으로 어떤 방식으로 추적할지 물었다.
- Decision: instrument registry는 당분간 generated snapshot artifact를 source of truth로 유지한다. 신규 상장/상장폐지 자동 추적이 필요해지면 다음 단계로 `정기 rebuild + 이전 artifact와 diff + inactive/delisted 상태 관리`를 추가한다.
- Why:
1. 현재 autocomplete hot path는 slash command 응답속도와 안정성이 중요해서, 매 입력마다 live symbol search API를 호출하는 방식보다 local registry snapshot이 더 안전하다.
2. KRX 상장/상폐, ETN 조기상환, ticker rename 같은 이벤트는 source 반영 시점 차이가 있어 `이번 build에서 안 보인다`는 이유만으로 기존 watch를 즉시 hard delete하면 운영상 더 위험하다.
3. 이미 guild state에 저장된 canonical symbol은 quote failure와 운영 알림의 근거가 되므로, registry에서 사라졌다고 조용히 제거하지 말고 inactive/delisted로 승격해 사용자 또는 운영자가 정리할 수 있게 해야 한다.
- Impact:
1. 현재 코드 기준 신규 상장과 상장폐지는 registry rebuild 전까지 autocomplete에 반영되지 않는다.
2. 아직 diff artifact, inactive/delisted marker, watchlist reconciliation report는 구현되지 않았다.
3. 자동 추적이 필요해질 때의 우선순위는 live search 전환이 아니라 daily registry refresh job, old/new diff artifact, inactive/delisted marker, watchlist reconciliation report다.
4. `/watch remove`는 registry에서 빠진 항목도 state 기준으로 계속 제거 가능해야 하며, quote path는 missing symbol을 명시적으로 드러내는 방향을 유지한다.
- Status: accepted

## 2026-03-23
- Context: 사용자가 현재 변경분을 커밋한 뒤 `origin/codex/watch-poll-live-quotes` 브랜치에서 가져올 만한 내용을 확인하고 합쳐 달라고 요청했다.
- Decision: 원격 브랜치는 전체 merge하지 않고, `미국 종목 quote fallback routing`만 현재 KIS rollout 구조에 맞게 selective integration 한다.
- Why:
1. 원격 브랜치의 실질적인 신규 가치는 `KIS primary + US fallback provider` 아이디어였다.
2. 반면 그 브랜치의 `day.c`/`prevDay.c`를 현재가 대체값으로 쓰는 방식은 `watch_poll`의 실시간 변동률 알림에 잘못된 alert를 만들 수 있다.
3. 현재 `develop`은 이미 `kis_quote`, `massive_reference`, warm-up, Massive rename, canonical provider status 정리를 끝낸 상태라 전체 merge보다 selective integration이 충돌과 회귀를 줄인다.
- Impact:
1. `MARKET_DATA_PROVIDER_KIND=kis`는 계속 KIS를 primary로 유지한다.
2. 미국 종목(`NAS/NYS/AMS`)은 `MASSIVE_API_KEY`가 있으면 Massive snapshot fallback을 시도한다.
3. Massive fallback은 `lastTrade` 기반 live price + freshness가 확인되는 경우만 허용하고, entitlement 부족은 `massive-entitlement-required`로 명시한다.
- Status: accepted

## 2026-03-23
- Context: 외부 US reference slot 문서와 env 이름이 여전히 `Polygon` 기준으로 남아 있었지만, 공식 브랜드와 최신 예시는 `Massive`를 사용한다.
- Decision: 사용자 노출 문서와 status/env 기본 이름은 `Massive` 기준으로 맞추고, 코드에서는 `POLYGON_API_KEY`와 `polygon_reference`를 legacy alias로만 허용한다.
- Why:
1. 공식 브랜드와 예시가 `Massive`로 이동한 상태에서 새 운영 문서가 `Polygon`만 쓰면 future rollout 때 혼선이 커진다.
2. 그렇다고 즉시 hard rename만 하면 기존 `.env`와 state에서 이미 남아 있을 수 있는 `POLYGON_API_KEY`, `polygon_reference`를 깨뜨릴 수 있다.
3. 아직 Massive adapter가 hot path에 붙지 않은 지금이 user-facing naming만 바로잡고 backward compatibility를 남기기에 가장 저렴한 시점이다.
- Impact:
1. `.env.example`, `README.md`, `AGENTS.md`, context docs, report 문서는 `Massive` 또는 `Massive (formerly Polygon.io)` 표현을 우선 사용한다.
2. settings는 `MASSIVE_API_KEY`를 우선 읽고, legacy `POLYGON_API_KEY`를 fallback으로 허용한다.
3. `/source-status` 기본 row는 `massive_reference`를 사용하되, 과거 state의 `polygon_reference`는 표시 단계에서 canonical key로 승격한다.
- Status: accepted

## 2026-03-22
- Context: 사용자가 `tests/integration` 전체를 기능 계약 중심 테스트 케이스 문서로 풀어 쓰고, live 캡처 테스트는 별도 문서로 분리해 달라고 요청했다.
- Decision: 통합 테스트 문서는 source of truth인 현재 `tests/integration/*.py`와 `pytest.ini`를 기준으로 유지하고, non-live 케이스는 `docs/specs/integration-test-cases.md`, live 케이스는 `docs/specs/integration-live-test-cases.md`로 분리한다.
- Why:
1. 기본 `pytest`가 `-m "not live"`를 쓰는 현재 구조에서는 live 캡처 2건과 나머지 43건의 운영 의미가 다르므로 문서도 분리하는 편이 해석이 명확하다.
2. 테스트 파일 순서 대신 기능 계약 단위로 재서술해야 구현자, 리뷰어, future subagent가 "무엇을 깨뜨렸는지"를 더 빨리 읽을 수 있다.
3. 초안 계획의 뉴스/EOD 케이스 수와 현재 소스 테스트 수가 1건씩 어긋나 있어, 문서 번호 체계도 계획안보다 source truth를 우선하는 편이 맞다.
- Impact:
1. 새 테스트 케이스 문서는 `README.md`, `AGENTS.md`의 테스트 가이드에서 바로 찾을 수 있다.
2. 현재 기준 non-live는 `AS 6 + FU 8 + NB 12 + TR 4 + EO 8 + WP 5 = 43`, live는 2건으로 읽는다.
3. 이후 테스트가 늘거나 재분류되면 먼저 source 테스트와 marker를 갱신하고, 문서는 그 구조를 그대로 따라간다.
- Status: accepted

## 2026-03-22
- Context: 사용자가 "기능 전체 통합 테스트 전용 subagent"를 하나 따로 두고, 이 agent가 테스트할 때는 항상 전체 integration suite를 돌리길 원했다.
- Decision: project custom agent에 `integration_tester`를 추가하고, 이 agent의 테스트 기본 동작을 `.\.venv\Scripts\python.exe -m pytest tests/integration` 전체 실행으로 고정한다.
- Why:
1. 이 저장소는 단일 파일 회귀만 보면 놓치는 scheduler/forum/state 연동 문제가 자주 나와, 기능 검증용 agent는 부분 테스트보다 전체 integration suite를 기본값으로 가져가는 편이 안전하다.
2. 테스트 전용 역할을 별도로 분리하면 `repo_explorer`/`reviewer`와 책임이 섞이지 않고, 검증 요청 시 기대 동작이 명확해진다.
3. unit/targeted test는 빠르지만 이번 저장소의 운영 리스크를 충분히 대변하지 못하므로, integration_tester는 기본적으로 subset 실행을 허용하지 않는 편이 맞다.
- Impact:
1. `.codex/agents/integration-tester.toml`이 새로 추가되고, `AGENTS.md`의 subagent 역할 목록에도 같은 규칙이 반영된다.
2. 향후 integration_tester를 통한 검증 요청은 전체 `tests/integration` 실행을 먼저 수행한 뒤에만 추가 targeted repro로 내려간다.
3. full integration suite를 돌릴 수 없으면 blocker를 그대로 보고하고, 부분 테스트로 조용히 대체하지 않는다.
- Status: accepted

## 2026-03-22
- Context: Codex app에서 project custom agent 3종이 모두 동작하는 것을 확인한 뒤, 사용자는 앞으로 같은 subagent 패턴을 매번 긴 문장으로 다시 지시하지 않길 원했다.
- Decision: 이 저장소의 Codex 기본 subagent 패턴은 `repo_explorer + reviewer + docs_researcher`로 두고, 새 스레드에서 한 번 명시된 뒤에는 같은 스레드 안에서 축약 표현으로 재사용한다.
- Why:
1. Codex는 subagent를 명시 요청 시에만 spawn하는 쪽이 기본이므로, 완전 자동보다 "새 스레드 1회 명시 후 같은 스레드 재사용" 규칙이 더 예측 가능하다.
2. 이 저장소 작업은 코드 경로 탐색, 리스크 리뷰, 공식 문서 확인이 자주 함께 필요해 3-agent 조합의 재사용성이 높다.
3. 모든 작업에서 문서 조사까지 항상 붙이면 비용과 대기 시간이 늘어나므로, `docs_researcher`는 필요 없는 로컬 코드 작업에서는 생략 가능해야 한다.
- Impact:
1. 새 스레드에서는 subagent 사용 의사를 한 번은 받아야 한다.
2. 같은 스레드에서는 `기본 3-agent 패턴`, `같은 subagent 패턴` 같은 축약 표현만으로도 같은 조합을 재사용할 수 있다.
3. `AGENTS.md`와 `session-handoff.md`에 같은 규칙을 남겨 다음 세션에서도 해석이 흔들리지 않게 한다.
- Status: accepted

## 2026-03-20
- Context: KIS 단독으로는 watch 종목명 검색, 뉴스 링크 품질, 보조 reference 확장성이 부족했고, 사용자는 `watch`를 우선 살리되 `eod_summary`는 잠정 중단하길 원했다.
- Decision: 외부 인텔 스택은 역할 분리형으로 간다. `watch 이름 검색`은 live vendor search 대신 local instrument registry를 쓰고, 시세는 `KIS primary`, 뉴스는 `Naver domestic + Marketaux global`, 보조 정규화는 `Massive`(구 `Polygon.io`)/`Twelve Data`/`OpenFIGI` 슬롯으로 분리한다.
- Why:
1. KIS는 quote에는 강하지만 자유검색형 symbol master와 기사 URL 기반 뉴스 계약이 약해, 모든 역할을 한 벤더에 몰면 command UX와 news 품질이 같이 흔들린다.
2. `watch add`는 slash command에서 빠르고 안정적으로 후보를 보여주는 게 중요하므로, 외부 rate limit과 auth에 직접 걸리는 live search보다 generated registry + autocomplete가 더 운영 친화적이다.
3. 국내 상장사와 미국 상장사의 authoritative source가 다르기 때문에, `OpenDART + SEC`를 symbol master base로 두고 vendor별 mapping은 별도 필드로 보관하는 편이 장기적으로 덜 묶인다.
4. 사용자는 확장형 스택을 원했지만 hot path 복잡도는 낮추길 원했으므로, `Massive`(구 `Polygon.io`), `Twelve Data`, `OpenFIGI`는 즉시 core path에 넣지 않고 optional slot으로 여는 쪽이 균형이 좋다.
5. `eod_summary`는 현재 요구 우선순위에서 밀렸기 때문에, half-built 확장을 이어가기보다 명시적으로 pause 해 두는 편이 운영 판단 기준이 더 선명하다.
- Impact:
1. watch 저장값은 canonical symbol(`KRX:005930`, `NAS:AAPL`)로 통일되고, legacy raw symbol은 점진적으로 canonical로 승격된다.
2. instrument registry는 repo에 체크인된 generated artifact를 runtime이 읽고, raw source는 `docs/references/external/`에만 둔다.
3. global news 실제 운영 전환의 기본선은 `NEWS_PROVIDER_KIND=hybrid`이며, source-status는 configured/disabled/paused semantics를 합성해서 보여준다.
4. `Massive`(구 `Polygon.io`), `Twelve Data`, `OpenFIGI`는 이번 단계에서 hot path fail-open 보조 슬롯으로만 열리고, 다음 단계에서 quote fallback/reconciliation job으로 확장한다.
5. `eod_summary`는 기본 설정상 비활성화되고, spec/상태 화면에도 pause 상태를 드러낸다.
- Status: accepted

## 2026-03-20
- Context: runtime 상태 파일이 heatmap 이미지 캐시 디렉터리(`data/heatmaps/`) 안에 섞여 있고, 외부 참고문서도 저장 위치가 분산돼 있어 운영 파일과 참고 자료가 헷갈리기 쉬웠다.
- Decision: runtime state는 `data/state/state.json`으로 분리하고, 외부 벤더 참고문서는 `docs/references/external/` 한 곳에 모은다.
- Why:
1. `state.json`은 이미지 캐시와 성격이 달라서 `data/heatmaps/` 아래에 있으면 캡처 결과물과 운영 상태가 뒤섞여 보인다.
2. 상태 파일을 별도 디렉터리로 분리하면 런타임 상태, 로그, 이미지 캐시를 목적별로 구분해 관리하기 쉬워진다.
3. 외부 참고문서는 내부 설계/리포트 문서와 달리 원문 보관 성격이 강하므로, `docs/context`, `docs/specs`, `docs/reports`와 분리된 단일 보관 위치가 있는 편이 탐색이 쉽다.
- Impact:
1. 앱 state 기본 경로는 `data/state/state.json`이 되고, 기존 `data/heatmaps/state.json`은 레거시 마이그레이션 대상으로 취급한다.
2. 외부 API 벤더 문서, 원문 가이드, 비교용 스프레드시트는 앞으로 `docs/references/external/` 아래에 둔다.
3. 내부 문서(`context/specs/reports`)와 외부 원문 문서가 역할별로 분리된다.
- Status: accepted

## 2026-03-20
- Context: `develop -> master` 릴리스를 별도 release branch로 진행한 뒤 `master`에만 squash merge되면서, 같은 수정이 `develop`에는 다시 sync PR `#10`으로 역반영돼야 했다.
- Decision: 앞으로 `master` 릴리스는 별도 release branch를 만들지 않고, `develop` 브랜치에서 직접 `master` 대상으로 PR을 연다.
- Why:
1. 이번 흐름에서 release branch가 `master`에만 들어가고 `develop`에는 자동 반영되지 않아, 같은 변경을 다시 `develop`으로 되돌려 넣는 추가 작업과 리뷰 루프가 필요했다.
2. 이 저장소의 실질적인 작업 기준선은 `develop`이므로, 릴리스도 `develop` 자신을 source branch로 쓰는 편이 기준선 관리가 단순하다.
3. 별도 release branch는 특별한 release-only patch가 있을 때만 의미가 있고, 평소에는 브랜치 분기와 역동기화 비용이 더 크다.
- Impact:
1. 이후 `develop에서 master로 올려` 류 요청은 `develop -> master` 직접 PR을 기본 경로로 사용한다.
2. `master`로만 먼저 들어간 수정이 생기지 않아, release 후 `develop` 재동기화 작업 빈도가 줄어든다.
3. 예외적으로 release branch가 필요하면, 왜 direct PR로 안 되는지와 release 후 `develop` 정리 계획을 같이 남겨야 한다.
- Status: accepted

## 2026-03-19
- Context: 사용자가 보수적인 경제 뉴스 브리핑은 유지하되, 따로 읽을 수 있는 `트렌드 테마 뉴스` 게시글을 원했다.
- Decision: 트렌드 테마는 기존 국내/해외 뉴스 브리핑에 섞지 않고, 같은 스케줄에서 별도 `trendbriefing` thread 하나로 생성한다.
- Why:
1. 메인 브리핑은 거시 헤드라인과 고영향 종목 기사 위주의 보수적 선별 품질을 유지해야 했다.
2. 트렌드 테마는 더 넓은 후보군과 curated taxonomy 기반 점수화가 필요해, 같은 본문에 섞으면 메인 브리핑 판단 기준이 흐려질 수 있다.
3. 사용자가 원하는 형태는 국내/해외 브리핑에 붙는 부가 문단보다, 나중에 따로 열어볼 수 있는 독립 thread에 더 가까웠다.
- Impact:
1. 뉴스 스케줄은 같은 tick에서 `국내 브리핑`, `해외 브리핑`, `트렌드 테마 뉴스` 세 갈래를 관리한다.
2. `trendbriefing`은 starter message와 하위 content message를 따로 동기화해야 하므로, forum state의 `DailyPostEntry`에 `content_message_ids`가 추가됐다.
3. 한 지역이 3개 미만이면 그 지역은 placeholder로 처리하고, 두 지역 모두 3개 미만일 때만 thread 자체를 만들지 않는다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑 기사 수를 늘리자 한 본문 안에서 2000자 제한과 국내/해외 혼합 가독성 문제가 다시 드러났다.
- Decision: 뉴스 브리핑은 국내/해외를 하나의 starter message에 합치지 않고, region별 daily thread 2개로 분리한다.
- Why:
1. Discord starter message는 2000자 제한이 있어 기사 수를 늘릴수록 길이 압박 때문에 하위 기사를 잘라야 했다.
2. 사용자는 국내 시장 흐름과 해외 시장 흐름을 따로 읽는 편이 더 명확하다고 판단했고, region별 20건 soft cap도 그 구조에서 더 자연스럽다.
3. 기존 오늘자 통합 thread를 domestic thread로 재사용하고 global thread만 추가 생성하면 포럼 히스토리를 크게 깨지 않고 전환할 수 있다.
- Impact:
1. scheduler는 `newsbriefing-domestic`, `newsbriefing-global` 두 daily post를 관리하고, 완료 판정은 둘 다 존재할 때만 난다.
2. region별 품질/개수 변화가 서로의 본문 길이와 가독성에 영향을 덜 준다.
3. 포럼에는 하루에 뉴스 thread가 2개 생기므로, 운영상 소음이 과한지 관찰이 필요하다.
- Status: accepted

## 2026-03-19
- Context: 사용자가 "시장 전체 기사만 말고, 헤드라인급 개별 종목 기사도 포함"되길 원했고, 네이버 뉴스 검색 API가 직접 headline 플래그를 주는지도 다시 확인할 필요가 있었다.
- Decision: 네이버 뉴스 브리핑은 `headline API`를 기다리기보다 `거시 헤드라인 query + 종목 헤드라인 query` 2트랙 점수화로 운영한다.
- Why:
1. 네이버 공식 문서 기준 뉴스 검색 API는 검색 결과만 반환하며 `headline`, `top story`, `랭킹` 같은 직접 필드를 주지 않는다.
2. 따라서 "헤드라인 뉴스"는 API 속성이 아니라 adapter가 query 구성, source weight, event keyword, 중복 제거로 근사해야 한다.
3. 사용자가 원하는 결과는 거시 기사만 모아놓은 브리핑이 아니라, 시장 전체 흐름과 함께 중요한 종목 이벤트가 한두 개는 보이는 형태였다.
- Impact:
1. 현재 선별은 거시 기사와 고영향 종목 기사 둘 다 허용하지만, 종목 기사는 제목에 이벤트 신호가 없으면 통과하지 않는다.
2. provider는 지역별 score order를 유지하므로, 단순히 최근 기사라는 이유만으로 저품질 기사가 앞쪽을 차지하기 어렵다.
3. 같은 기사 링크/제목이 국내/해외 양쪽에 동시에 뜨는 경우 scheduler에서 한 번 더 제거한다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑 품질은 괜찮았지만, 아침/저녁 브리핑 특성상 지역별 기사 수를 더 넓게 보여 달라는 요구가 생겼다.
- Decision: 뉴스 브리핑은 지역별 최대 20건까지 허용하되, 품질 필터와 dedup을 통과한 기사만 게시하는 soft cap으로 유지한다.
- Why:
1. 브리핑 성격상 3~5건보다 더 넓은 커버리지가 유용하지만, 품질을 위해 억지로 20건을 채우면 다시 중복/저신호 기사가 섞일 수 있다.
2. 이미 적용한 dedup, blocklist, 소스 가중치 정책은 유지하고 상한만 넓히는 편이 현재 만족한 품질을 해치지 않는다.
3. 실제 실데이터 기준으로도 해외는 17건까지 자연스럽게 늘어났고, 국내는 5건만 남아 soft cap 요구와 잘 맞는다.
4. Discord starter message는 2000자 제한이 있어, 상한을 늘리더라도 본문 길이 안전장치가 함께 필요하다.
- Impact:
1. scheduler와 provider는 이제 20건까지 담을 수 있지만, 실제 게시 수는 지역별 기사 품질과 실데이터 상황에 따라 더 적을 수 있다.
2. 게시 본문은 Discord 2000자 제한을 넘기지 않도록 자동으로 잘리며, 길이 때문에 일부 하위 기사가 빠질 수 있다.
3. 기사 수를 더 늘리고 싶을 때는 상한을 또 올리기보다 dedup 기준과 query 세트 세분화를 먼저 검토한다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑에서 같은 장세 headline 반복과 개별 종목/ETF 기사 유입 때문에 국내 기사 품질이 흐려졌다.
- Decision: 국내 뉴스 브리핑은 개수보다 품질을 우선해, 시장 주제 단위 dedup과 개별 종목/ETF headline 제외 규칙을 적용한다.
- Why:
1. 사용자가 원하는 브리핑은 "주요뉴스/속보"에 가깝고, 같은 코스피 장세 기사가 여러 건 있거나 종목/ETF 기사까지 섞이면 목적과 멀어진다.
2. 네이버 검색 API는 중요도 랭크를 직접 주지 않으므로 adapter에서 주제 대표성과 다양성을 강제해야 한다.
3. 실제 실데이터 샘플에서도 국내 5건보다 국내 3건이 더 읽기 쉬운 결과를 보였다.
- Impact:
1. `domestic`은 `코스피`, `금리`, `환율` 같은 시장 축별 대표 기사 위주로 남는다.
2. 개별 종목 `주가` 기사와 ETF/상품 headline, 같은 장세 반복 headline은 대부분 탈락한다.
3. 기사 수가 5건보다 적어질 수 있지만, 이는 품질 우선 동작으로 허용한다.
- Status: accepted

## 2026-03-19
- Context: 네이버 뉴스 검색 API를 붙인 뒤 단일 query만으로는 `global`에 국내 기사나 코너형 기사까지 섞여, "주요뉴스/속보" 품질이 부족했다.
- Decision: 네이버 뉴스 브리핑은 단일 query 정렬을 그대로 쓰지 않고, 다중 query 후보 수집 후 gate 키워드, blocklist, 중요도 점수, 저신호 패널티를 거쳐 region별 상위 기사만 남긴다.
- Why:
1. 네이버 검색 API는 중요도, 주요뉴스 여부, source rank를 직접 주지 않아 adapter 내부 재정렬이 필요하다.
2. `global`은 미국 시장 직접 신호가 제목에 없으면 국내 시장 기사도 쉽게 섞이므로, region gate가 필요하다.
3. 기업 PR, 사진 기사, 반복 코너형 기사까지 그대로 통과시키면 브리핑 목적과 멀어진다.
- Impact:
1. `NaverNewsProvider`는 region별 다중 query를 호출하고 dedup 후 상위 기사만 반환한다.
2. `global`은 미국 시장 직접 신호가 제목에 있어야 통과 가능성이 높고, 국내 시장 키워드가 더 강하면 탈락한다.
3. 결과 품질은 query 세트와 키워드 사전에 계속 영향을 받으므로, 실데이터를 보며 튜닝을 이어가야 한다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑을 mock에서 실제 데이터로 바꾸기 위해 네이버 뉴스 검색 API를 첫 번째 실사용 소스로 붙이는 작업을 시작했다.
- Decision: 뉴스 provider는 `NEWS_PROVIDER_KIND=naver` 설정으로 명시 전환하고, 네이버 응답의 `query`별 결과를 `domestic`/`global`로 태깅해 현재 `NewsItem` 계약에 맞춘다.
- Why:
1. 네이버 뉴스 검색 API는 국내 뉴스 접근성이 좋고 공식 문서가 안정적이지만, 응답에 `region`과 `source` 필드가 직접 들어 있지 않다.
2. 현재 scheduler/policy는 `domestic`/`global` 구분과 `source` 문자열을 기대하므로, query를 두 번 호출해 지역을 나누고 `originallink` 도메인으로 source를 유추하는 adapter가 필요하다.
3. 기본값을 바로 네이버로 바꾸면 키가 없는 개발 환경에서 부트나 테스트가 흔들릴 수 있으므로, explicit opt-in이 더 안전하다.
- Impact:
1. `.env`에 `NEWS_PROVIDER_KIND=naver`, `NAVER_NEWS_CLIENT_ID`, `NAVER_NEWS_CLIENT_SECRET`를 넣기 전까지는 기존 mock 뉴스가 유지된다.
2. 국내/해외 뉴스 품질은 `NAVER_NEWS_DOMESTIC_QUERY`, `NAVER_NEWS_GLOBAL_QUERY` 선택에 영향을 받으므로 실운영 전에 쿼리 튜닝이 필요하다.
3. title의 `<b>` 태그 제거, `pubDate` 파싱, 원문 링크 우선 사용, 최근 N시간 필터링은 adapter가 책임진다.
- Status: accepted

## 2026-03-18
- Context: 사용자는 `develop에 합쳐` 한 번으로 PR 생성부터 Codex Connector 리뷰 반영, 재검토, merge까지 이어지는 흐름을 원했다.
- Decision: `ship-develop`의 기본 reviewed shipping은 human approval gate가 아니라 Codex review loop로 둔다. 사람 승인 대기는 명시 요청일 때만 `--require-review`로 켠다.
- Why:
1. 이 저장소에서는 이미 `@codex review` -> feedback 확인 -> 수정 -> 재검토 -> merge 흐름을 실제로 사용해 왔다.
2. Codex review는 수 분 단위로 끝나는 자동 루프라서 한 세션 안에서 끝까지 처리하기 좋지만, 사람 리뷰는 대기 시간이 길어 one-shot workflow 기본값으로는 맞지 않는다.
3. 사용자가 원하는 UX는 "한 번 말하면 내가 끝까지 처리"에 가깝고, 그 요구는 Codex review loop가 더 잘 맞는다.
- Impact:
1. 기본 `develop으로 합쳐`는 PR 생성 후 `@codex review`를 요청하고, findings가 있으면 수정/재검토를 반복한다.
2. `사람 리뷰 받고 develop에 합쳐` 같은 요청일 때만 human review gate를 추가로 사용한다.
3. `ship_develop.py`는 Codex review 결과를 `clean`, `findings`, `pending`으로 판별해 merge 여부를 결정한다.
- Status: accepted

## 2026-03-18
- Context: `ship-develop`이 PR 생성 직후 바로 merge해서, 사용자가 원한 "리뷰 확인 후 merge" 흐름과 맞지 않았다.
- Decision: `ship-develop`은 review gate를 지원하고, `develop` shipping의 기본 흐름은 two-pass로 운영한다. 첫 실행은 PR 생성 또는 갱신 후 `review-required` 상태로 멈추고, 승인 후 같은 스크립트를 다시 실행해 merge한다.
- Why:
1. 이 저장소의 `develop` 브랜치는 현재 GitHub branch protection이 없어서, review 강제는 repo 설정이 아니라 shipping workflow 내부에서 처리해야 한다.
2. 사람 리뷰는 수분에서 수시간이 걸릴 수 있어 한 세션에서 오래 기다리는 것보다 "같은 도구를 다시 실행하는 2단계"가 현실적이다.
3. 도구를 둘로 나누지 않고 review gate 옵션을 추가하면 PR 생성과 merge 재개가 같은 인터페이스 안에서 유지된다.
- Impact:
1. 이후 `develop으로 합쳐` 류 요청은 기본적으로 리뷰 대기 상태를 존중한다.
2. 첫 실행에서 merge가 되지 않아도 정상일 수 있고, `review-required`는 실패가 아니라 대기 상태다.
3. 긴 대기 대신 승인 후 같은 branch에서 `ship-develop`을 다시 실행하면 된다.
- Status: accepted

## 2026-03-18
- Context: 반복되는 push -> PR -> merge -> branch cleanup 요청을 한 번의 Codex 요청으로 줄이고 싶었다.
- Decision: 이 저장소는 GitHub shipping workflow를 repo skill `ship-develop`과 보조 스크립트로 캡슐화한다. 구현은 `gh` CLI 기반으로 하고, base branch는 항상 명시적으로 넘긴다.
- Why:
1. 이 저장소의 실사용 브랜치 흐름은 `develop` 중심이지만, GitHub repo 기본 브랜치는 현재 `master`라서 암묵적 기본값에 기대면 잘못 머지할 수 있다.
2. 현재 repo 설정은 `allow_auto_merge=false`, `delete_branch_on_merge=false`라서 GitHub UI 기본 동작만으로는 사용자가 원하는 "머지 후 정리" 흐름을 끝까지 자동화하기 어렵다.
3. skill + script 조합이면 Codex가 한 문장 요청에서도 테스트, 커밋, PR, merge, cleanup 흐름을 일관되게 재사용할 수 있다.
- Impact:
1. 이후 `develop으로 합쳐` 류 요청은 `$ship-develop` skill이 우선 후보가 된다.
2. 머지 자동화는 current branch, worktree 상태, PR 상태, checks 상태를 확인한 뒤 안전할 때만 진행한다.
3. `gh`가 `PATH`에 없더라도 `C:\Program Files\GitHub CLI\gh.exe` fallback 경로를 사용한다.
- Status: accepted

## 2026-03-18
- Context: Codex subagents/custom agents 운영 방식을 이 저장소 작업 흐름에 붙일 수 있는지 검토했다.
- Decision: 이 저장소는 `AGENTS.md`를 공통 규칙 레이어로 유지하고, 필요 시 프로젝트 범위의 read-only custom agent와 repo skill을 소규모로 추가한다. 외부 `Agents SDK + Codex MCP` 오케스트레이션은 당장 도입하지 않는다.
- Why:
1. 현재 구조는 `bot/features/*`, `bot/intel/providers/*`, `bot/forum/*`, `docs/context/*`처럼 경계가 나뉘어 있어 탐색, 리뷰, 문서 검증은 병렬 분업 이점이 있다.
2. 반면 실제 수정은 `bot/features/intel_scheduler.py`, `bot/app/settings.py`, `bot/forum/repository.py`처럼 공용 파일에 집중돼 병렬 writer를 늘리면 충돌과 정합성 비용이 커진다.
3. 현재 최우선 과제는 외부 provider 실사용 전환과 운영 검증이라, 별도 오케스트레이터보다 project-scoped custom agent/skill이 더 저비용이다.
4. 공식 Codex 문서도 subagents는 명시 요청 기반 병렬 작업, `AGENTS.md`는 공통 지침, skills는 재사용 workflow 패키징 용도로 분리한다.
- Impact:
1. 병렬 활용은 코드 탐색, 문서 검증, 리뷰 중심으로 제한한다.
2. 반복 작업은 repo skill 후보로 분리할 수 있고, 구현은 메인 세션 또는 단일 worker가 맡는다.
3. multi-repo 자동화나 상위 orchestration 필요성이 커질 때만 `Agents SDK + Codex MCP`를 다시 검토한다.
- Status: accepted

## 2026-03-18
- Context: 같은 유형의 리뷰 누락이 다시 발생하지 않게, 발견된 실수를 운영 규칙으로 축적할 필요가 생겼다.
- Decision: 리뷰에서 유효했던 지적은 `docs/context/review-log.md`에 기록만 하지 않고, 재발 방지 가치가 있으면 `docs/context/review-rules.md`에 규칙으로 승격한다.
- Why:
1. 리뷰 로그는 과거 사실 기록에는 좋지만, 다음 리뷰 시작 시 바로 적용할 체크리스트 역할은 약하다.
2. 이번 누락은 단일 버그보다 리뷰 범위의 문제였기 때문에 규칙화가 더 효과적이다.
- Impact:
1. 이후 리뷰 세션은 `review-rules.md`를 먼저 보고 체크한다.
2. 규칙은 실제로 놓친 사례가 생길 때마다 한 개씩 추가한다.
- Status: accepted

## 2026-03-17
- Context: 새로 추가한 뉴스/장마감/watch 스케줄을 mock 단계에서 실제 운영 단계로 올리려면 외부 데이터 소스 기준이 먼저 필요하다.
- Decision: 벤더를 먼저 고정하지 않고, 현재 scheduler/provider 인터페이스에 맞는 벤더 중립 정규화 계약을 `docs/specs/external-intel-api-spec.md`로 먼저 확정한다.
- Why:
1. 지금 코드의 진짜 의존성은 특정 API가 아니라 `NewsItem`, `Quote`, `EodSummary` 형태의 정규화된 데이터다.
2. 계약이 먼저 있어야 벤더 교체, fallback, rate limit 대응, 테스트 fixture 구성이 한 기준으로 정리된다.
3. watchlist 폴링은 호출 빈도가 높아 구현 전에 timeout, batch, 오류 처리 규칙이 선행돼야 한다.
- Impact:
1. 이후 외부 API 연동은 이 명세를 만족하는 adapter 구현으로 진행한다.
2. goals와 handoff의 최우선 항목은 확장 스케줄 실사용 전환으로 유지한다.
- Status: accepted

## 2026-03-17
- Context: 프로젝트용 바이브 코딩 규칙 초안을 실제 운영 문서에 편입했다.
- Decision: 바이브 코딩 규칙을 별도 초안 파일에만 두지 않고 `AGENTS.md` 상단 공통 운영 규칙으로 승격한다.
- Why:
1. 세션이 시작될 때 가장 먼저 읽는 문서가 `AGENTS.md`이므로, 핵심 규칙은 참조 문서보다 본문에 있어야 실행 편차가 줄어든다.
2. 프로젝트 특화 규칙인 컨텍스트 로그 갱신, 검증, 위험 작업 통제는 항상 적용돼야 한다.
- Impact:
1. 이후 세션은 바이브 코딩 규칙을 기본 운영 규칙으로 따른다.
2. `docs/prompts/vibe-coding-rule-prompt.md`는 상세 원문과 재사용 프롬프트 저장소 역할로 유지한다.
- Status: accepted

## 2026-03-17
- Context: 앞으로 AI 협업 규칙에 "바이브 코딩" 스타일을 추가하려고 한다.
- Decision: 속도 중심 규칙만 복제하지 않고, 검증과 컨텍스트 유지가 포함된 보호형 프롬프트로 정리한다.
- Why:
1. 최근 유행하는 바이브 코딩 예시는 실행 속도와 반복 루프에는 강하지만, 파괴적 변경 통제와 맥락 보존 규칙이 약한 경우가 많다.
2. 이 프로젝트는 여러 세션과 여러 작업 위치에서 이어지므로 작업 로그와 핸드오프 규칙이 빠지면 판단이 쉽게 흔들린다.
3. 테스트, 리뷰, 문서 갱신을 완료 조건에 넣어야 결과 품질을 일정하게 유지할 수 있다.
- Impact:
1. 이후 바이브 코딩 규칙을 도입할 때는 단일 프롬프트 안에 속도 규칙과 안전 규칙을 함께 둔다.
2. 프롬프트 초안은 `docs/prompts/vibe-coding-rule-prompt.md`에 보관한다.
- Status: accepted

## 2026-03-17
- Context: Codex를 여러 세션과 위치에서 병행 사용할 때 프로젝트 컨텍스트가 일관되게 유지되어야 한다.
- Decision: 단일 문서 의존 대신 카테고리별 문서 집합으로 컨텍스트를 관리한다.
- Why:
1. 활성 상태와 장기 설계 근거를 한 문서에 섞으면 필요한 정보를 빠르게 찾기 어렵다.
2. 리뷰 이슈와 구현 로그는 수명이 다르므로 분리해야 추적성이 좋아진다.
3. 이후 자동화나 템플릿화가 필요할 때도 카테고리 구조가 더 확장성이 높다.
- Alternatives considered:
1. `AGENTS.md` 하나에 계속 누적: 검색은 쉽지만 문서 비대화와 혼선 위험이 크다.
2. 날짜별 일지만 운영: 세션 회고에는 좋지만 설계 기준 복원이 느리다.
- Impact:
1. 다음 세션은 `session-handoff.md`로 즉시 현재 상태를 복구한다.
2. 설계 변경은 `design-decisions.md`에 먼저 남기는 습관이 필요하다.
- Status: accepted

## 2026-03-23
- Context: `watch_poll`을 mock 시세에서 live KIS 경로로 옮기면서, scheduler와 `/source-status`가 같은 운영 진실을 보도록 정리할 필요가 있었다.
- Decision: watch quote provider는 `MARKET_DATA_PROVIDER_KIND=mock|kis`로 명시 선택하고, scheduler는 quote 성공/실패를 `market_data_provider`가 아니라 `kis_quote` 상태 키에 기록한다. live provider는 public `get_quote(symbol, now)` 계약을 유지한 채 optional `warm_quotes(symbols, now)`로 poll-cycle 예열만 추가한다.
- Why:
1. 기존 `watch_poll`은 `MockMarketDataProvider()`가 하드코딩돼 있어 운영 env를 넣어도 live 전환이 불가능했다.
2. `/source-status` 기본 row는 이미 `kis_quote`를 보여주는데 runtime write key가 따로 있으면 설정 상태와 실행 상태가 분리돼 운영 해석이 흔들린다.
3. scheduler 계약을 batch로 바꾸면 영향 범위가 커지므로, 단건 계약은 유지하고 provider 내부 warm/cache로 중복 호출만 줄이는 쪽이 더 안전하다.
- Impact:
1. `MARKET_DATA_PROVIDER_KIND=kis`인데 KIS credential이 비어 있으면 mock fallback 없이 `kis-credentials-missing`으로 실패가 드러난다.
2. watch poll은 유효한 guild/channel만 먼저 추려 unique symbol을 모으고, live provider가 지원할 때만 `warm_quotes`를 한 번 호출한다.
3. KIS adapter는 registry canonical symbol과 `provider_ids.kis_exchange_code`를 기준으로 국내/해외 경로를 나누고, 동일 poll cycle에서는 같은 symbol을 한 번만 외부 조회한다.
- Status: accepted
