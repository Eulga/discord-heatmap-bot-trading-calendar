# Session History

## Purpose
- This document is the archive target for older handoff entries after the active handoff file is slimmed down.
- It exists so session-handoff.md can stay short and useful for the next session.

## Cutover Note
- Phase 2 moved older handoff entries out of session-handoff.md.
- 93 archived handoff blocks were moved on 2026-03-24.
- session-handoff.md now keeps only the latest active handoff blocks.
- After that cutover, any older active handoff block displaced by newer work is appended here instead of being kept in `session-handoff.md`.
- Historical entries below preserve the file names and paths that were current when each entry was written.

## Archived Entries
## 2026-03-24
- Context: 사용자가 documentation update policy를 현재 구조에 맞게 AGENTS/operating-rules에 반영하라고 요청했다.
- Current state:
1. `AGENTS.md`의 Documentation Update Rules는 이제 최소 수정 원칙과 문서별 update trigger를 직접 명시한다.
2. `docs/context/operating-rules.md`의 Context Update Rules는 current truth, config/runtime, deep spec, logs, backlog/report 문서 경계를 더 구체적으로 설명한다.
3. 이번 변경은 정책 문구 정리만이며, runtime behavior truth나 QA taxonomy 자체는 바꾸지 않았다.
- Next:
1. 이후 문서 수정 작업은 이 policy를 기준으로 summary/spec/log 문서의 update 범위를 더 좁게 유지하면 된다.
- Status: done

## 2026-03-24
- Context: 사용자가 code verification required 문서 진술을 실제 코드 기준으로 검증하라고 요청했다.
- Current state:
1. `docs/operations/config-reference.md`에는 이제 cache TTL, autoscreenshot/news/watch/EOD/registry/logging 기본값, bootstrap env 동작, provider wiring이 코드 기준으로 정리돼 있다.
2. `docs/operations/runtime-runbook.md`는 route/autoscreenshot admin gate와 watch/status/manual command 경계를 현재 코드 기준으로 요약한다.
3. `docs/context/CURRENT_STATE.md`는 QA report와 current behavior concern의 경계를 더 분명히 하도록 blocker 섹션 제목과 canonical pointer를 정리했다.
- Next:
1. 추가 문서 개편은 없고, 남은 ambiguity는 query-list defaults나 future provider slot처럼 summary 문서에 올릴 필요가 낮은 항목만 남는다.
- Status: done

## 2026-03-24
- Context: 사용자가 문서 migration plan의 Phase 3 실행을 요청했다.
- Current state:
1. QA test backlog 문서는 이제 `docs/specs/qa-test-backlog.md`에 있다.
2. 최신 consolidated QA review report는 이제 `docs/reports/qa-issue-review-2026-03-24.md`에 있다.
3. `CURRENT_STATE.md`와 `operating-rules.md`의 QA 포인터는 새 taxonomy를 기준으로 갱신했고, old path는 historical log/session history 안에만 남는다.
- Next:
1. 문서 taxonomy cleanup phase는 완료됐고, 필요하면 이후에는 code verification required 항목만 코드 대조로 좁혀서 정리한다.
- Status: done

## 2026-03-24
- Context: 사용자가 문서 migration plan의 Phase 2 실행을 요청했다.
- Current state:
1. README.md는 onboarding-only 구조로 줄였고, deeper docs는 새 context/operations/spec 문서로 링크한다.
2. AGENTS.md는 agent rules + canonical document pointers 중심으로 축소했고, 프로젝트 위키 역할은 새 문서로 분산했다.
3. session-handoff.md는 최신 active handoff만 남기고, older entries는 session-history.md로 이동한다.
- Next:
1. Phase 3에서 QA backlog/report 성격 문서를 spec 경로에서 재분류한다.
- Status: open

## 2026-03-24
- Context: 사용자가 문서 migration plan의 Phase 1 실행을 요청했다.
- Current state:
1. 새 문서 `docs/context/CURRENT_STATE.md`, `docs/context/session-history.md`, `docs/context/operating-rules.md`, `docs/operations/runtime-runbook.md`, `docs/operations/config-reference.md`가 추가됐다.
2. 이번 단계에서는 새 구조만 먼저 만들었고, `README.md`, `AGENTS.md`, `docs/context/session-handoff.md`의 trim/split은 아직 시작하지 않았다.
3. `CURRENT_STATE.md`는 짧은 summary만 담고, exact defaults, exact auth, Massive wiring 같은 항목은 code verification required로 승격을 보류했다.
- Next:
1. Phase 2에서 `README.md`를 onboarding-only로 줄이고, `AGENTS.md`를 agent-rules + canonical-doc pointers 중심으로 축소한다.
2. 같은 Phase 2에서 `session-handoff.md`는 최신 1~3개 active block만 남기고 나머지는 `session-history.md`로 이동한다.
- Status: open

## 2026-03-24
- Context: 사용자가 Markdown 문서 체계 개편 방향 제안을 요청했다.
- Current state:
1. 현재 구조의 가장 큰 문제는 `AGENTS.md`의 위키화, `session-handoff.md`의 누적 로그화, `current/as-is/to-be/risk` 기준 문서의 분산이다.
2. 확인된 구체 사례로 `AGENTS.md`는 agent rule 외에 아키텍처 스냅샷, 운영 체크리스트, 트러블슈팅, 다음 세션 TODO까지 품고 있고, `session-handoff.md`는 1k lines를 넘어 즉시 handoff 문서 역할을 약화시키고 있다.
3. `docs/specs/as-is-functional-spec.md`는 현재 코드 기준 deep reference로 적절하지만, `docs/specs/external-intel-api-spec.md`와 함께 읽기 우선순위가 섞이면 future-state contamination 위험이 있다.
- Next:
1. 실제 개편을 시작하면 `CURRENT_STATE.md` 신설 -> `session-handoff/history` 분리 -> `AGENTS.md`와 `README.md` 축소 순으로 진행하는 것이 가장 안전하다.
- Status: open

## 2026-03-24
- Context: 사용자가 As-Is spec + QA test spec 기반 QA issue document를 요청했다.
- Current state:
1. 새 문서 `docs/specs/qa-issue-document.md`가 추가됐다.
2. 현재 문서는 As-Is spec을 source of truth로 두고 consolidated issue 16개, root-cause grouping, release blocker 구분, implementation phase, GitHub issue shortlist를 담고 있다.
3. 최우선 이슈는 `state fail-open`, `unsynchronized state mutation`, `exact-minute scheduler miss`, `forum upsert duplicate on transient Discord failure`, `watch stale/off-hours alert risk`다.
- Next:
1. 실제 작업은 shortlist 순서대로 GitHub issue로 전환하거나, 바로 P0/P1 수정 작업으로 이어가면 된다.
- Status: open

## 2026-03-24
- Context: 사용자가 As-Is spec contamination review를 요청했다.
- Current state:
1. `docs/specs/as-is-functional-spec.md`의 일부 과신 표현이 교정됐다.
2. 현재 문서는 `manual heatmap`, `forum upsert`, `watch poll`, `instrument registry refresh`, `legacy !ping`에서 "보장" 대신 "현재 코드가 실제로 시도/거절/기록하는 동작" 기준으로 다시 적혀 있다.
3. `watch poll`과 `legacy !ping`은 reachability/semantics ambiguity를 반영해 confidence가 더 보수적으로 표시된다.
4. `instrument registry refresh`는 load/search/runtime refresh wiring은 confirmed로, 외부 데이터 완전성은 ambiguous로 다시 분리됐다.
- Next:
1. 이후 As-Is 문서를 추가로 만들 때는 feature 목적도 구현 추정임을 분명히 하고, ambiguous runtime reachability가 있으면 confidence를 낮춘다.
- Status: open

## 2026-03-24
- Context: 사용자가 현재 구현 기준 reverse-spec As-Is functional specification 문서를 요청했다.
- Current state:
1. 새 문서 `docs/specs/as-is-functional-spec.md`가 추가됐다.
2. 문서는 현재 코드 기준으로 startup, manual heatmap, forum upsert, auto scheduler, admin/watch/status commands, news/trend/EOD/watch scheduler, instrument registry, legacy `!ping`까지 정리했다.
3. 구현 사실과 별도로 `ambiguities`, `observed gaps`, `As-Is vs To-Be boundary`를 분리해 미래 설계를 섞지 않도록 정리했다.
- Next:
1. 이후 QA, 리팩터링, To-Be spec 작업은 이 문서를 baseline으로 삼는다.
2. current gaps를 고칠 때는 먼저 As-Is 문서 내용이 실제 코드와 맞는지 다시 대조하고, 바뀌는 동작은 별도 변경 문서에 적는다.
- Status: open

## 2026-03-24
- Context: 사용자가 QA 리뷰를 테스트 구현 백로그로 바꾼 명세 문서를 요청했다.
- Current state:
1. 새 문서 `docs/specs/qa-test-specification.md`가 추가됐다.
2. 이 문서는 기존 `integration-test-cases.md`와 달리 "현재 구현된 테스트 설명"이 아니라 "추가 구현할 QA 테스트 후보"를 `unit/integration/E2E/regression/failure injection` 기준으로 정리한다.
3. 최우선 구현 후보는 `state fail-open 차단`, `watch quote freshness/timezone`, `mock/live fail-closed`, `daily scheduler catch-up`, `forum upsert duplicate 방지`, `concurrent state mutation 보호` 관련 테스트다.
- Next:
1. 다음 테스트 보강 작업은 새 명세 문서를 source of truth로 삼아 P0/P1 케이스부터 실제 `tests/unit` / `tests/integration`에 옮긴다.
2. 문서에 정의된 E2E와 failure-injection 케이스는 live smoke와 non-live harness로 어디까지 분리할지 먼저 결정한다.
- Status: open

## 2026-03-24
- Context: 사용자가 principal-level QA 프롬프트를 적용한 전체 시스템 QA 리뷰를 요청했다.
- Current state:
1. 전체 문서/핵심 코드(`settings`, `bot_client`, `runner`, `auto_scheduler`, `intel_scheduler`, `forum`, `news/market providers`, `tests`)를 기준으로 QA 리뷰를 완료했다.
2. 현재 최상위 리스크는 `state fail-open으로 인한 state wipe`, `mock data가 live처럼 게시될 수 있는 기본값`, `watch quote freshness/timezone 해석 결함`, `shared watchlist/status surface 권한 부족`, `late-start catch-up 부재`, `Discord transient fetch 시 duplicate thread 생성`이다.
3. 회귀 확인으로 `.\.venv\Scripts\python.exe -m pytest -q` 전체는 통과했다.
- Next:
1. 다음 수정 우선순위는 `state fail-open 차단 + state mutation lock`, `mock/live fail-closed`, `watch permission policy`, `daily scheduler catch-up`, `forum upsert transient error 분리`다.
2. watch quote는 `domestic/overseas asof 해석`과 `market-hours gating`을 먼저 바로잡고 나서 live smoke를 다시 보는 편이 안전하다.
- Status: open

## 2026-03-24
- Context: 사용자가 slash command 없이 바로 확인할 수 있게 뉴스/트렌드 게시를 수동 실행해 달라고 요청했다.
- Current state:
1. 오늘자(`2026-03-24`) `newsbriefing-domestic`, `newsbriefing-global`, `trendbriefing` thread가 생성됐다.
2. latest job state는 `news_briefing=ok`, `trend_briefing=ok`다.
3. actual `trendbriefing` content fetch 기준 numbering은 제거된 상태다.
4. current render sample:
   - 국내: `[국내 트렌드 테마] / 바이오 / 근거: ... / 기사: ...`
   - 해외: `[해외 트렌드 테마] / 금리/Fed / 근거: ... / 기사: ...`
- Next:
1. 사용자가 Discord UI에서 실제 가독성을 보고 추가 수정을 결정한다.
2. 다음 후보는 `기사:` 줄의 `| source | time | link` 레이아웃 단순화다.
- Status: done

## 2026-03-24
- Context: 사용자가 Discord에서 직접 확인할 수 있게 봇을 다시 켜 달라고 요청했다.
- Current state:
1. 로컬 봇 프로세스가 현재 실행 중이다.
2. startup 로그 기준 gateway 연결, global commands 11개 sync, auto screenshot scheduler 시작, intel scheduler 시작까지 정상 확인됐다.
3. 첫 scheduler tick은 `watch_poll status=skipped detail=no-watch-symbols`였다.
4. Windows에서는 launcher parent PID `21556` 아래 실제 interpreter child PID `27068`가 떠 있는 구조이며, Discord 연결은 child process가 보유 중이다.
- Next:
1. 사용자가 Discord에서 trend/news 포맷을 직접 확인한다.
2. 확인이 끝난 뒤 stop 요청이 오면 해당 프로세스를 정리한다.
- Status: done

## 2026-03-24
- Context: 사용자가 `trendbriefing` 본문에서 테마 제목 아래 기사 줄의 숫자/기호 표기가 어색하다고 보고해 포맷 정리를 요청했다.
- Current state:
1. `bot/features/news/trend_policy.py`는 이제 theme title을 번호 없이 plain text로 렌더링한다.
2. 대표 기사 줄은 `- ...` 대신 `기사: ...` 형식으로 출력된다.
3. 현재 sample render는 `[국내 트렌드 테마] / 반도체 / 근거: ... / 기사: ...` 순서다.
4. 관련 회귀는 `tests/unit/test_trend_policy.py`에 추가됐고 targeted pytest는 통과했다.
- Next:
1. 실제 Discord 게시글에서 체감 가독성을 보고, 필요하면 다음 단계로 `|` 구분자나 링크 배치를 더 다듬는다.
- Status: done

## 2026-03-24
- Context: 사용자가 영어 `Marketaux` 해외뉴스 품질 이슈를 보류하고, 당분간 `Naver` 기반 한국 기사만 수집하도록 provider 설정을 되돌리길 원했다.
- Current state:
1. 로컬 `.env`의 `NEWS_PROVIDER_KIND`는 이제 `naver`다.
2. 따라서 현재 runtime news path는 `Marketaux`/`hybrid`가 아니라 `NaverNewsProvider` 단일 경로를 사용한다.
3. 이 상태는 영어 해외기사 수집을 끄는 효과는 있지만, global news thread 자체는 유지된다. 즉 글로벌 섹션은 `Naver` 검색 기반 한국 기사로 계속 채워질 수 있다.
- Next:
1. 사용자가 정말 원하는 것이 "한국 기사만"이면 현재 설정으로 충분하다.
2. 사용자가 원하는 것이 "해외/global 섹션 자체 중단"이면 `naver` 전환과 별도로 global query/게시 경로를 끄는 코드 변경이 필요하다.
- Status: done

## 2026-03-24
- Context: 사용자가 `trendbriefing` 생성 시 `Marketaux` 영어 해외뉴스가 현재 테마 판정에서 제대로 동작하는지 물었다.
- Current state:
1. `NEWS_PROVIDER_KIND=marketaux|hybrid`의 글로벌 trend는 `MarketauxNewsProvider.analyze()`가 briefing items만 모은 뒤 `_fallback_candidates_by_region()`로 만든 후보군에 의존한다.
2. 이 fallback 후보는 `description/entities` 없이 title/source/recency 중심 점수만 써서, 영어 기사에서 company/entity 문맥을 충분히 활용하지 못한다.
3. 로컬 논리 검증 기준 `Fed/Treasury yields`, `Apple/Microsoft`, `Nvidia/AMD` headline 조합은 global theme 0개였고, `AI chip/semiconductor`처럼 explicit theme keyword가 들어간 headline만 `AI/반도체`로 매칭됐다.
4. 글로벌 theme taxonomy의 representative symbol/alias는 일부 영어 ticker를 포함하지만, 상당수 mega-cap/company name이 한국어 중심이라 company-only English headline recall이 낮다.
5. 현재 unit test는 Marketaux normalization만 검증하고, 영어 trend classification 회귀는 없다.
- Next:
1. Marketaux global trend를 계속 운영할 거면 description/entities까지 후보 scoring에 포함하고 글로벌 theme alias를 영어 company name 기준으로 보강한다.
2. `tests/unit/test_news_provider.py`에 Marketaux 영어 headline trend regression을 추가한다.
- Status: open

## 2026-03-23
- Context: 사용자가 두 스레드에서 섞인 수정분이 문제없는지 전체 코드리뷰와 clean 확인을 요청했다.
- Current state:
1. modified 파일 전체를 검토한 결과, 명백한 merge conflict 잔재나 같은 목적의 중복 구현은 보이지 않았다.
2. 유일한 actionable issue는 `watch_alert_latches` 도입 이후 `remove_watch_symbol()`이 runtime watch 메타상태를 남겨 두는 점이었다.
3. 현재는 종목 제거 시 `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`를 함께 지워 재등록이 fresh state로 시작된다.
4. 회귀는 `tests/unit/test_watch_cooldown.py`, `tests/unit/test_watchlist_repository.py`에 추가됐고 `.\.venv\Scripts\python.exe -m pytest -q` 전체가 다시 통과했다.
- Next:
1. 운영 반영이 필요하면 봇 프로세스 또는 Docker Compose 서비스를 재기동한다.
2. 실제 Discord에서 `/watch remove` 후 `/watch add` 재등록 시 첫 same-direction alert가 정상 동작하는지 한 번 확인한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `watch_poll`의 같은 방향 중복 알림을 막아 달라고 요청했다.
- Current state:
1. `bot/features/watch/service.py`는 이제 같은 심볼이 같은 방향 threshold 밖에 계속 있을 때 cooldown이 끝나도 재알림하지 않는다.
2. 재알림은 baseline 대비 threshold 안으로 한 번 복귀해 `watch_alert_latches`가 해제된 뒤 같은 방향으로 다시 이탈할 때만 허용된다.
3. `watch_alert_cooldowns`는 그대로 남아 threshold 근처 출렁임 억제용으로 유지되고, 반대 방향 전환은 계속 별도 알림 가능하다.
4. 회귀는 `tests/unit/test_watch_cooldown.py`, `tests/unit/test_watchlist_repository.py`, `tests/integration/test_intel_scheduler_logic.py`에 추가됐고 targeted pytest는 통과했다.
- Next:
1. 실제 운영 반영이 필요하면 봇 프로세스 또는 Docker Compose 서비스를 재기동한다.
2. 배포 직후 실제 Discord에서 같은 심볼 연속 하락 구간이 재알림 없이 유지되는지 한 번 더 확인한다.
- Status: done

## 2026-03-23
- Context: 사용자가 기능별 로그 누락을 고쳐 달라고 요청했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 `watch_poll`, `news_briefing`, `trend_briefing`, `eod_summary`, `instrument_registry_refresh`의 최종 `status/detail`을 파일 로그로도 남긴다.
2. `bot/features/watch/command.py`, `bot/features/admin/command.py`, `bot/features/runner.py`, `bot/features/status/command.py`에 command audit log가 들어갔다.
3. `bot/app/command_sync.py`의 state 저장 실패 경로는 `print(...)` 대신 logger를 사용한다.
4. logging 보강 직후 전체 `pytest`에서 `interaction.user`가 없는 테스트 더블 회귀가 드러나, command logger는 모두 fail-safe helper 경로로 보강했다.
5. reviewer follow-up으로 `bot/intel/providers/market.py`의 `NYS -> AMS` exchange alias retry가 request-stage `not-found`에서도 이어지도록 추가 수정했다.
6. `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀는 다시 통과했다.
7. `docker compose up -d --build` 후 `data/logs/bot.log`와 `docker compose logs` 양쪽에서 `bot.features.intel_scheduler [intel] watch_poll status=ok ...` 라인이 실제로 찍히는 것을 확인했다.
- Next:
1. 필요하면 다음 단계로 `news/eod` 로그 detail에 guild/forum 대상 수를 더 풍부하게 남긴다.
2. command audit log가 길어지면 detail truncation이나 log level 재조정을 검토한다.
- Status: done

## 2026-03-23
- Context: 사용자가 기능별 로그가 제대로 안 찍히는지 확인해 달라고 요청했다.
- Current state:
1. `bot/common/logging.py`의 파일/콘솔 핸들러 설정은 정상이고 `data/logs/bot.log`에도 startup 로그는 기록된다.
2. 문제는 기능별 로그 호출 범위다. `bot/features/intel_scheduler.py`는 실패 시 `logger.exception(...)`만 남기고, 성공/skip 결과는 `job_last_runs` state에만 저장한다.
3. `bot/features/watch/command.py`, `bot/features/admin/command.py`, `bot/features/runner.py`는 slash command 호출과 결과를 logger로 남기지 않아 수동 기능 실행 흔적이 로그 파일에 거의 없다.
4. `bot/app/command_sync.py`는 state 저장 실패를 `print(...)`로만 남겨 logger/file handler 경로를 우회한다.
- Next:
1. 필요하면 다음 작업으로 `intel_scheduler` success/skip log, slash command audit log, `command_sync` print -> logger 치환을 묶어 관측성 보강 패치를 진행한다.
2. 로그 정책을 정할 때는 guild_id, command_key, result, provider/message 정도만 남기고 시크릿이나 민감한 payload는 제외한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `/watch add UCO` 뒤 `massive_reference ok=false`가 되는 버그를 수정하라고 요청했다.
- Current state:
1. 원인은 registry가 `UCO`를 `NYS:UCO`로 저장한 상태에서 KIS `EXCD=NYS` 조회가 빈 quote를 돌리고, 그 뒤 Massive fallback이 entitlement 부족으로 실패하던 흐름이었다.
2. `bot/intel/providers/market.py`는 이제 해외 단건 조회에서 `NYS` 빈 quote를 받으면 `AMS`를 한 번 더 재시도하고, 반대 방향(`AMS -> NYS`)도 같은 규칙으로 처리한다.
3. 회귀 테스트 `tests/unit/test_market_provider.py`가 추가됐고, `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py -q`는 통과했다.
4. live spot check에서도 `KisMarketDataProvider.get_quote("NYS:UCO", now_kst())`가 `kis_quote` 가격을 반환했다.
5. `docker compose up -d --build` 후 실제 다음 `watch_poll` tick은 `status=ok`, `processed=2`, `quote_failures=0`으로 회복됐다.
6. 다만 `provider_status.massive_reference=false`는 이전 fallback 실패(`massive-entitlement-required`)가 state에 남은 것이다. 이번 UCO bug fix와는 별개로, Massive entitlement나 status reset UX를 손보지 않으면 `/source-status`에는 계속 historical failure로 보일 수 있다.
- Next:
1. 별도 후속 과제로 SEC exchange -> KIS exchange 매핑을 registry build 단계에서 더 정확히 보강할지 검토한다.
2. 필요하면 `/source-status`의 historical provider failure 표시 정책을 조정할지 검토한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `develop`를 `master`에 반영하고 버전 태그까지 달라고 요청했다.
- Current state:
1. release PR [#15](https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/15)는 `squash merge`로 닫혔고, `origin/master` 최신 릴리스 커밋은 `426a7f6 release: merge develop into master (2026-03-23) (#15)`다.
2. git 태그 `v1.0.2`는 `426a7f6`에 push됐다.
3. release 직전 로컬 검증으로 `.\.venv\Scripts\python.exe -m pytest -q` 전체가 통과했다.
4. 현재 `origin/master`와 `origin/develop`의 차이는 release 기록용 [development-log.md](C:/Users/kin50/Documents/test/docs/context/development-log.md)와 [session-handoff.md](C:/Users/kin50/Documents/test/docs/context/session-handoff.md) 두 파일뿐이다. 코드/런타임 파일 기준 tree diff는 없다.
5. 이번 릴리스는 squash merge라 branch history는 다르고, `origin/develop` head는 `b58bb61 docs: record master release v1.0.2`다.
- Next:
1. 다음 릴리스 준비 전에는 commit history보다 tree diff 기준으로 `develop -> master` 차이를 먼저 확인한다.
2. 필요하면 Discord 운영 smoke를 `v1.0.2` 기준으로 한 번 더 수행한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `develop` 최신 상태를 반영한 뒤 Docker Compose 서비스를 새로 올려 달라고 요청했다.
- Current state:
1. 워크스페이스는 `develop@66d9b6c`까지 fast-forward 동기화된 상태에서 `docker compose up -d --build`를 실행했다.
2. `discord-heatmap-bot` 컨테이너는 recreate 후 `Up` 상태다.
3. 재기동 직후 컨테이너 로그에는 Gateway 연결, global commands 11개 sync, `Auto screenshot scheduler started`, `Intel scheduler started`, `Logged in as Drumstick#9496`가 남았다.
4. startup bootstrap 로그 기준 `DEFAULT_FORUM_CHANNEL_ID`와 `EOD_TARGET_FORUM_ID`가 guild `332110589969039360` state로 다시 반영됐다.
- Next:
1. 운영 smoke가 필요하면 Discord에서 `/health`, `/source-status`, `/kheatmap` 중 최소 1개를 눌러 interaction ingress까지 확인한다.
- Status: done

## 2026-03-23
- Context: 사용자가 reviewer subagent clean + integration subagent pass를 확인한 뒤 현재 변경분을 커밋/푸시하라고 요청했다.
- Current state:
1. instrument registry refresh scheduler는 review 후속 수정까지 반영됐다. refresh task는 background에서 live rebuild만 수행하고, `job_last_runs`/`provider_status` 반영은 메인 scheduler loop가 task 완료 후 기록한다.
2. 이 구조로 detached refresh의 stale state overwrite race를 막았고, configured minute를 놓친 late start도 같은 날 catch-up refresh를 시작한다.
3. same-day retry는 허용하되, `dart-api-key-missing` 같은 static config failure는 분 단위 재시도를 막는다.
4. reviewer subagent 최신 결과는 `No actionable issues found.`였고, integration subagent는 `.\.venv\Scripts\python.exe -m pytest tests/integration` 기준 `55 passed, 2 deselected`를 보고했다.
- Next:
1. 현재 작업 트리를 커밋하고 원격에 push한다.
2. 다음 scheduler 변경에서도 background task가 state 파일을 직접 저장하는지부터 먼저 점검한다.
- Status: open

## 2026-03-23
- Context: 사용자가 env와 state의 역할을 프로젝트 최우선 운영 규칙으로 고정하고, 이후 코드리뷰도 이 기준으로 판단하자고 요청했다.
- Current state:
1. 이제 이 저장소의 기본 원칙은 `민감정보는 env`, `mutable 운영 라우팅은 state`다.
2. `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`는 bootstrap/default/dev-test 용도로만 해석한다.
3. 길드별 channel/forum/watch routing 값은 `data/state/state.json`이 source of truth고, 새 기능도 이 전제를 깨지 않는 방향으로 설계해야 한다.
4. `docs/context/review-rules.md` Rule 2가 이 원칙을 리뷰 acceptance gate로 고정했다. env를 runtime authoritative source로 다시 끌어오는 변경은 문서화된 예외가 없으면 reject 대상이다.
- Next:
1. 다음 리뷰 세션부터 관련 변경은 먼저 Rule 2 기준으로 점검한다.
2. 새 설정 키를 추가할 때는 이 값이 시크릿인지, bootstrap default인지, mutable state인지 먼저 분류한다.
- Status: open

## 2026-03-23
- Context: 사용자가 env channel IDs가 runtime fallback처럼 읽혀 다른 길드 heatmap이 깨진다고 보고했고, channel routing 기준을 state 중심으로 정리해 달라고 요청했다.
- Current state:
1. Discord channel routing의 source of truth는 이제 `data/state/state.json`이다. heatmap은 `forum_channel_id`, 뉴스는 `news_forum_channel_id -> forum_channel_id`, EOD는 `eod_forum_channel_id -> forum_channel_id`, watch는 `watch_alert_channel_id`를 guild state에서 읽는다.
2. `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`, `WATCH_ALERT_CHANNEL_ID`는 runtime cross-guild fallback이 아니라 startup bootstrap 용도다. bot 시작 시 channel 접근이 가능하면 matching guild state가 비어 있을 때만 1회 복사한다.
3. heatmap runner는 state에 저장된 forum channel이 다른 guild channel이거나 삭제된 경우 명시적으로 `/setforumchannel` 재설정을 요구한다.
4. 관련 회귀는 `tests/unit/test_bot_client.py`, `tests/integration/test_forum_upsert_flow.py`, `tests/integration/test_intel_scheduler_logic.py`에 반영됐고 targeted suite는 통과했다.
- Next:
1. 봇을 재시작해 startup bootstrap이 현재 `.env`의 forum/watch channel IDs를 state에 옮기는지 실제 state 파일로 확인한다.
2. 그 뒤 `/kheatmap`, `/usheatmap`, `/source-status`를 길드별로 직접 눌러 env가 아니라 state 기반으로 라우팅되는지 검증한다.
3. 운영에서 문제 없으면 channel ID env는 장기적으로 bootstrap-only legacy로 남길지, 완전히 제거할지 결정한다.
- Status: open

## 2026-03-23
- Context: 사용자가 instrument registry coverage를 ELW/PF까지 넓히고, bot scheduler로 daily refresh를 붙여 달라고 요청했다.
- Current state:
1. bundled registry는 이제 OpenDART 상장사 + SEC 미국 상장사 + KRX ETF/ETN/ELW/PF finder rows를 포함한다. 최신 build 기준 counts는 `KRX=8131`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `15649`건이다.
2. `bot/intel/instrument_registry.py`의 load 순서는 `data/state/instrument_registry.json -> bot/intel/data/instrument_registry.json -> seed`다. runtime refresh가 성공하면 같은 프로세스부터 runtime artifact가 우선 사용된다.
3. 새 env는 `INSTRUMENT_REGISTRY_REFRESH_ENABLED=false|true`, `INSTRUMENT_REGISTRY_REFRESH_TIME=06:20`이다. refresh는 live OpenDART/SEC/KRX source를 직접 다시 fetch한 full rebuild가 성공했을 때만 runtime artifact를 atomic replace 한다.
4. `/source-status`의 `instrument_registry` row는 active source(`runtime|bundled`)와 loaded counts를 보여주고, `/last-run`은 `instrument_registry_refresh` row를 기본으로 노출한다.
5. 검색 회귀 기준은 현재 `삼성전자 -> KRX:005930`, `KBL002삼성전자콜 -> KRX:58L002`, `대신 KOSPI200인덱스 X클래스 -> KRX:0106J0`까지 확인됐다.
6. 관련 테스트는 `tests/unit/test_instrument_registry.py`, `tests/unit/test_watch_command.py`, `tests/unit/test_status_command.py`, `tests/integration/test_intel_scheduler_logic.py`에 추가됐고 targeted suite는 통과했다.
- Next:
1. 운영에서 daily refresh를 켜려면 `.env`에 `INSTRUMENT_REGISTRY_REFRESH_ENABLED=true`와 원하는 `INSTRUMENT_REGISTRY_REFRESH_TIME`을 넣고, `DART_API_KEY`가 비어 있지 않은지 확인한다.
2. 다음 단계는 inactive/delisted marker와 watchlist reconciliation report다. 현재 refresh는 `added/removed` summary만 남긴다.
3. 마지막 검증으로 `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀를 다시 한 번 돌리고, 필요하면 봇 재시작 후 `/source-status`, `/last-run` 표시를 직접 확인한다.
- Status: open

## 2026-03-23
- Context: `codex/live-watch-rollout-20260323 -> develop` shipping 중 GitHub Codex review가 watch quote warm-up 경로에 P2 3건을 남겼다.
- Current state:
1. `bot/intel/providers/market.py`의 warm-up은 이제 best-effort다.
2. 국내 warm-up failure는 `_quote_errors`를 남기지 않아 same-poll `get_quote()`가 단건 domestic quote를 다시 시도할 수 있다.
3. 해외 `multprice` warm-up도 row omission/stale row를 hard error로 캐시하지 않아 single-symbol fallback path가 살아 있다.
4. 관련 회귀 테스트는 `tests/unit/test_market_provider.py`에 추가됐고, `tests\unit\test_market_provider.py + tests\integration\test_intel_scheduler_logic.py`가 통과했다.
5. 다음 shipping 재시도 대상 PR은 `#14`다.
- Next:
1. 현재 head를 push한 뒤 `@codex review`를 다시 요청한다.
2. review가 clean이면 `develop`으로 merge하고 local branch cleanup을 진행한다.
- Status: open

## 2026-03-23
- Context: 사용자가 신규 상장 상품과 상장폐지 상품을 현재 watch autocomplete 구조에서 어떻게 추적할지 물었다.
- Current state:
1. 현재 autocomplete source of truth는 live search API가 아니라 generated `instrument_registry.json` snapshot이다.
2. 따라서 신규 상장/상장폐지는 registry rebuild 전까지 autocomplete에 반영되지 않는다.
3. 이미 guild state에 저장된 watch symbol은 registry에서 사라져도 즉시 삭제되지 않고, remove/list는 state 기준으로 계속 다룬다.
4. `정기 rebuild + old/new diff + inactive/delisted 상태 관리 + watchlist reconciliation report`는 다음 단계 설계안일 뿐, 아직 구현되지는 않았다.
- Next:
1. 실제 자동 추적이 필요해지면 registry refresh job과 diff artifact를 먼저 구현한다.
2. 그 뒤 inactive/delisted marker를 `/source-status` 또는 admin report와 연결한다.
- Status: open

## 2026-03-23
- Context: 사용자가 `KB 천연가스 선물 ETN(H)` 같은 ETN 상품도 `/watch add` autocomplete에서 검색되지 않는다고 보고했다.
- Current state:
1. 국내 registry는 이제 OpenDART 상장사 master + KRX 공식 ETF finder + KRX 공식 ETN finder(`dbms/comm/finder/finder_secuprodisu`) rows를 함께 포함한다.
2. regenerated artifact 기준 counts는 `KRX=5382`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `12900`건이다.
3. 실제 resolution 기준 `KB 천연가스 선물 ETN(H) -> KRX:580020`이 된다.
4. `tests/unit/test_instrument_registry.py`와 `tests/unit/test_watch_command.py`에 ETN 회귀가 추가됐고 통과했다.
5. KRX structured finder fetch는 `mktsel`별 동적 `Referer`를 사용하도록 정리돼 ETF/ETN 공통 경로로 유지된다.
- Next:
1. 사용자가 Discord에서 직접 `/watch add` autocomplete로 ETN을 실테스트하면 된다.
2. 필요하면 같은 KRX finder family로 ELW/PF도 추가 확장한다.
- Status: done

## 2026-03-23
- Context: 사용자가 ETF가 검색되지 않는다고 보고했고, KRX ETF까지 autocomplete에 포함되게 하라고 요청했다.
- Current state:
1. 국내 registry는 이제 OpenDART 상장사 master에 더해 KRX 공식 ETF finder(`dbms/comm/finder/finder_secuprodisu`) 기반 ETF rows도 포함한다.
2. regenerated artifact 기준 counts는 `KRX=4994`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `12512`건이다.
3. 실제 resolution 기준 `삼성전자 -> KRX:005930`, `제주반도체 -> KRX:080220`, `KODEX 200 -> KRX:069500`, `TIGER 200 -> KRX:102110`이 된다.
4. ETF 유입 후 stock exact query가 ambiguity로 깨지는 회귀는 `watch.command.resolve_watch_add_symbol()`에서 exact match score 우선 규칙으로 보정했다.
5. 관련 회귀 테스트는 `tests/unit/test_instrument_registry.py`, `tests/unit/test_watch_command.py`에 추가됐고 통과했다.
- Next:
1. 사용자가 Discord에서 직접 `/watch add` autocomplete를 실테스트하면 된다.
2. 필요하면 같은 KRX finder 계열로 ETN/ELW/PF도 추가 확장한다.
- Status: done

## 2026-03-23
- Context: 사용자가 `제주반도체` 수준의 비주류 코스닥 종목도 `/watch add` autocomplete에서 검색되게 만들라고 요청했다.
- Current state:
1. 원인은 registry build 경로였다. `scripts/build_instrument_registry.py`가 repo `.env`를 읽지 않아 `DART_API_KEY`가 있어도 OpenDART corpCode를 반영하지 못하고 있었다.
2. 스크립트는 이제 `.env`를 자동으로 로드한다.
3. generated registry artifact를 다시 빌드한 현재 기준 counts는 `KRX=3914`, `NAS=4248`, `NYS=3270`, `AMS=0`, 총 `11432`건이다.
4. 실제 검색 검증에서 `load_registry().search("제주반도체", limit=5)`는 `KRX:080220`을 반환한다.
5. `tests/unit/test_instrument_registry.py`에는 `제주반도체` 검색 회귀가 추가됐고, `tests/unit/test_watch_command.py`와 함께 통과했다.
- Next:
1. watch autocomplete 기준선은 이제 OpenDART corpCode가 반영된 full KRX artifact로 본다.
2. registry가 오래되면 같은 스크립트로 다시 빌드하거나, 필요 시 scheduled refresh를 붙인다.
- Status: done

## 2026-03-23
- Context: 사용자가 남은 핵심 과제인 `eod_summary` live 구현과 Massive fallback live 완료에 필요한 조건을 정리한 보고서를 요청했다.
- Current state:
1. 보고서는 `docs/reports/eod-massive-completion-report-2026-03-23.md`에 정리돼 있다.
2. `eod_summary` 쪽은 scheduler/forum/test 프레임은 준비돼 있지만, 실제 blocker는 `KIS endpoint 조합 확정 + live provider 구현 + 실거래일 smoke`다.
3. Massive fallback 쪽은 코드/테스트는 거의 끝났고, 실제 blocker는 `snapshot entitlement가 붙은 Massive key 확보`와 `fallback이 의도적으로 발동됐음을 증명하는 controlled live smoke`다.
4. 현재 순서상 먼저 처리할 일은 `eod_summary` live provider 구현이다. Massive는 외부 entitlement가 열리기 전까지 완결할 수 없다.
- Next:
1. `eod_summary` 1차 범위를 `KIS only`로 고정하고 `_build_eod_summary_provider()`와 live provider 구현 작업으로 들어간다.
2. Massive entitlement가 준비되면 direct snapshot smoke와 routed fallback smoke를 분리해서 실행한다.
- Status: open

## 2026-03-23
- Context: 사용자가 현재 변경분을 커밋한 뒤 `origin/codex/watch-poll-live-quotes` 브랜치의 유효한 내용을 확인해서 현재 `develop`에 합쳐 달라고 요청했다.
- Current state:
1. 현재 rollout 기준선은 `eaeaa7d Roll out live watch quotes and provider docs`로 먼저 커밋해 고정했다.
2. `origin/codex/watch-poll-live-quotes`는 단일 커밋 `153e491 feat: use live quotes for watch poll`만 있었고, 전체 merge 대신 `US fallback routing`만 selective integration 했다.
3. 현재 `quote_provider`는 `RoutedMarketDataProvider`고, `MARKET_DATA_PROVIDER_KIND=kis`일 때 KIS를 primary로 유지하면서 미국 종목은 `MASSIVE_API_KEY`가 있으면 Massive snapshot fallback을 시도한다.
4. Massive fallback은 `lastTrade` 기반 live price + freshness가 있을 때만 허용하고, 원격 브랜치의 `day/prevDay` 가격 fallback은 alert 정확도 문제로 가져오지 않았다.
5. 현재 env key로 Massive snapshot direct call을 해 보면 `massive-entitlement-required`가 돌아온다. 즉 코드 경로는 열렸지만 현 plan entitlement로는 US fallback live 사용은 아직 불가다.
6. KIS primary + Discord `watch_poll` controlled smoke는 현재 통합본에서도 다시 성공했다 (`watch_poll=ok`, alert send 1건 후 delete 1건).
- Next:
1. Massive entitlement가 준비되면 `NAS/NYS/AMS` 종목으로 fallback live smoke를 별도로 한 번 더 수행한다.
2. 그 전까지 운영상 watch live path는 KIS primary 기준으로 본다.
- Status: done

## 2026-03-23
- Context: 사용자가 `.env` 값을 실제로 채운 뒤 `openfigi`를 제외한 나머지 API와 `watch_poll` live smoke를 실행해 달라고 요청했다.
- Current state:
1. `.\.venv\Scripts\python.exe -m pytest -q` 전체 회귀는 다시 통과했다.
2. live smoke 중 KIS token endpoint는 `접근토큰 발급 잠시 후 다시 시도하세요(1분당 1회)`로 403을 돌릴 수 있고, 기존 `bot/intel/providers/market.py`는 이를 `kis-auth-failed`로 오분류하고 있었다.
3. 이 문제를 수정해 HTTP 403 body의 `EGW00133`/rate-limit 메시지를 `kis-rate-limited`로 분리했고, 관련 unit test를 추가했다.
4. env/live 검증 결과는 현재 모두 성공이다:
   - DART corpCode zip fetch 성공
   - Massive reference ticker fetch 성공
   - TwelveData quote fetch 성공
   - Naver provider / Marketaux provider / runtime hybrid news analyze 성공
   - KIS domestic quote fetch 성공
   - Discord `watch_poll` smoke 성공 (`watch_poll=ok`, `kis_quote.ok=True`, alert send 1건 후 delete 1건)
5. Discord 채널 타입도 현재 적합하다: `WATCH_ALERT_CHANNEL_ID`와 `ADMIN_STATUS_CHANNEL_ID`는 `TextChannel`, `NEWS_TARGET_FORUM_ID`와 `EOD_TARGET_FORUM_ID`는 `ForumChannel`이다.
6. 다만 실제 guild `332110589969039360`의 watch route는 env fallback `WATCH_ALERT_CHANNEL_ID=1483007026023108739`가 아니라 state의 `watch_alert_channel_id=460011902043553792` override를 우선 사용한다.
- Next:
1. 운영에서 watch alert 채널을 env fallback으로 통일하려면 guild-level `watch_alert_channel_id` override를 정리하거나 `/setwatchchannel`로 원하는 채널로 다시 맞춘다.
2. 이후 KIS 관련 smoke나 운영 진단은 provider instance를 불필요하게 여러 개 만들지 않는다. token issuance는 분당 1회 제한이 있고, 현재 코드는 rate-limit을 명시적으로 기록한다.
- Status: done

## 2026-03-23
- Context: 최신 reviewer finding 중 남아 있던 KIS warm-up fallback P2도 후속 수정했다.
- Current state:
1. `bot/intel/providers/market.py`의 overseas batch warm-up failure는 이제 chunk 전체 symbol을 `_quote_errors`로 오염시키지 않는다.
2. 그래서 `warm_quotes()`가 실패해도 같은 poll cycle의 `get_quote()`는 single-symbol `price` endpoint로 fallback할 수 있다.
3. 관련 회귀 테스트를 추가했고, `.\.venv\Scripts\python.exe -m pytest tests\unit\test_market_provider.py tests\integration\test_intel_scheduler_logic.py -q`는 통과했다.
4. 최신 subagent review에서 나온 P2/P3는 모두 닫혔다. 현재 남은 큰 리스크는 live KIS/Discord smoke 미실행이다.
- Next:
1. 운영 env에 credential/channel을 채운 뒤 `watch add -> poll -> alert send -> /source-status` live smoke를 수행한다.
2. 실제 응답 기준으로 `not-found`, `stale`, rate-limit 메시지의 운영 가독성을 마지막 점검한다.
- Status: done

## 2026-03-23
- Context: review finding이던 `/source-status` legacy quote-provider drift를 후속 수정했다.
- Current state:
1. `bot/features/status/command.py`는 이제 `market_data_provider -> kis_quote`, `polygon_reference -> massive_reference`를 canonical key로 정규화한다.
2. 기존 state에 legacy key와 canonical key가 동시에 있어도 canonical row가 우선해 `/source-status`와 `/health`에 quote-provider row가 하나만 남는다.
3. 관련 회귀 테스트는 `tests/unit/test_status_command.py`에 추가됐고, 결과는 `6 passed`였다.
4. 현재 reviewer finding 중 남은 open 항목은 `bot/intel/providers/market.py`의 warm-up failure가 same-poll single-symbol fallback까지 막는 P2 하나다.
- Next:
1. 필요하면 다음 작업으로 `bot/intel/providers/market.py`의 `_quote_errors`/fallback 경로를 보정한다.
2. 그 뒤 integration 재실행과 live KIS smoke 순서로 이어간다.
- Status: done

## 2026-03-23
- Context: `Polygon.io -> Massive` rename을 user-facing 문서, env, `/source-status` naming에 backward-compatible하게 반영했다.
- Current state:
1. `bot/app/settings.py`는 `MASSIVE_API_KEY`를 우선 읽고, legacy `POLYGON_API_KEY`를 fallback으로 허용한다.
2. `/source-status` 기본 row key는 이제 `massive_reference`고, 과거 state의 `polygon_reference`는 표시 단계에서 같은 key로 정규화된다.
3. `.env.example`, `README.md`, `AGENTS.md`, context docs, `docs/reports/mvp-data-source-review-2026-03-12.md`는 `Massive` 또는 `Massive (구 Polygon.io)` 표현으로 맞춰졌다.
4. `.\.venv\Scripts\python.exe -m pytest -q`까지 다시 통과했다.
5. 내부 `instrument_registry`의 `polygon_primary_exchange` 필드는 아직 live adapter에 묶이지 않아 이번 작업에서는 그대로 뒀다.
- Next:
1. 실제 Massive adapter를 붙일 때 env 문서는 `MASSIVE_API_KEY`만 안내하고, code fallback으로만 `POLYGON_API_KEY`를 유지한다.
2. 필요하면 이후 별도 작업에서 `polygon_primary_exchange` 같은 내부 필드명을 일괄 정리한다.
- Status: open

## 2026-03-23
- Context: 현재 KIS watch rollout 변경분을 `integration_tester`와 `reviewer` subagent로 다시 검증했다.
- Current state:
1. full integration suite는 `.\.venv\Scripts\python.exe -m pytest tests/integration` 기준 `45 passed, 2 deselected`로 깨지지 않았다.
2. reviewer는 `bot/intel/providers/market.py`에서 overseas `warm_quotes()` batch failure가 같은 poll cycle의 per-symbol fallback까지 막는 회복성 결함을 찾았다. 현재 `_quote_errors`가 먼저 소비돼 `get_quote()`가 single-symbol fetch를 시도하지 못한다.
3. reviewer는 `bot/features/status/command.py`에서도 기존 state의 legacy `market_data_provider` key가 남아 있으면 `/source-status`와 `/health`가 `kis_quote`와 함께 둘 다 보여 줄 수 있는 drift를 지적했다.
4. targeted KIS/watch tests는 통과했지만, 실제 KIS/Discord live smoke는 여전히 env credential/channel 부재로 막혀 있다.
- Next:
1. `bot/intel/providers/market.py`에서 batch warm-up 실패 후 single-symbol fetch fallback이 살아 있게 보정한다.
2. status view나 state migration에서 legacy `market_data_provider` row 정리 방식을 결정한다.
3. 수정 후 integration 재실행, 가능하면 credential 준비 뒤 live smoke까지 이어간다.
- Status: open

## 2026-03-23
- Context: `watch_poll`을 KIS live provider 경로로 연결하고 `.env.example`를 복사-사용 가능한 주석형 템플릿으로 다시 정리했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 `MARKET_DATA_PROVIDER_KIND=mock|kis`를 읽어 `quote_provider`를 builder로 생성한다. `kis` 선택 시 credential이 비어 있으면 `kis-credentials-missing`을 내는 `ErrorMarketDataProvider`로 실패가 드러난다.
2. `bot/intel/providers/market.py`에는 `KisMarketDataProvider`가 추가됐고, access token 캐시, 1회 auth refresh retry, registry 기반 canonical symbol 해석, KRX/해외 경로 분기, poll-cycle quote cache, optional `warm_quotes()`를 지원한다.
3. watch scheduler는 유효한 guild/channel만 먼저 수집한 뒤 unique symbol warm-up을 수행하고, runtime provider status를 `kis_quote`에 기록한다. 기존 `watch_poll` 실패 의미는 그대로라 quote/channel/send failure가 하나라도 있으면 최종 status는 `failed`다.
4. `.env.example`는 섹션형으로 재정리됐고, 주석은 섹션 묶음 설명 중심으로 정리됐다. 개별 주석은 `options:`가 필요한 항목만 남기고, `WATCH_ALERT_CHANNEL_ID`의 text/messageable 채널 제약은 섹션 주석으로 남겼다.
5. 테스트는 `.\.venv\Scripts\python.exe -m pytest -q`까지 모두 통과했다.
6. 다만 live smoke는 아직 막혀 있다. 현재 `.env` 기준 `KIS_APP_KEY`, `KIS_APP_SECRET`, `WATCH_ALERT_CHANNEL_ID`, `ADMIN_STATUS_CHANNEL_ID`가 모두 비어 있어 KIS/Discord 실연동 검증은 이번 세션에서 수행하지 못했다.
- Next:
1. 운영 env에 KIS credential, text `WATCH_ALERT_CHANNEL_ID`, 접근 가능한 `ADMIN_STATUS_CHANNEL_ID`를 채운다.
2. 그다음 `watch add -> poll -> alert send -> /source-status` 순서로 live smoke를 한 번 수행해 `kis_quote=ok`와 실제 Discord alert message를 확인한다.
3. live 응답 기준으로 `not-found`, `stale`, rate-limit 메시지와 alert body가 운영에 충분히 읽기 쉬운지 마지막 점검을 한다.
- Status: open

## 2026-03-23
- Context: 로컬 `develop`을 최신 원격과 다시 맞춘 뒤, 지금 기준의 다음 작업 우선순위를 재정리했다.
- Current state:
1. 로컬 `develop`은 `origin/develop`의 최신 11커밋을 반영한 상태로 정리됐고, sync 직후 기본 회귀는 `107 passed, 2 deselected`였다.
2. 뉴스 경로는 [bot/features/intel_scheduler.py](C:/Users/kin50/Documents/New%20project/discord-heatmap-bot-trading-calendar/bot/features/intel_scheduler.py)에서 `NEWS_PROVIDER_KIND=mock|naver|marketaux|hybrid`를 지원한다.
3. 반면 같은 파일의 `eod_provider`, `quote_provider`는 아직 `MockEodSummaryProvider()`, `MockMarketDataProvider()`로 직접 고정돼 있어, 실사용 전환이 덜 끝난 쪽은 현재 `watch_poll`과 `eod_summary`다.
4. 설계 기준으로는 `watch`가 우선이고 `eod_summary`는 pause 상태다. 최신 Discord smoke 기준 `WATCH_ALERT_CHANNEL_ID`는 forum 채널을 가리키고, `ADMIN_STATUS_CHANNEL_ID`는 `403 Missing Access`라 운영 env 보정도 남아 있다.
- Next:
1. 먼저 운영 env를 바로잡는다: `WATCH_ALERT_CHANNEL_ID`를 일반 text channel로 바꾸고, `ADMIN_STATUS_CHANNEL_ID` 접근 권한을 복구한다.
2. 그다음 구현/검증 우선순위는 live `MarketDataProvider`를 붙여 `watch add -> poll -> alert send` 전체 경로를 실사용 데이터로 검증하는 것이다.
3. `eod_summary`는 다시 우선순위가 올라오기 전까지 pause 유지가 맞고, 재개할 때 별도 live provider 작업으로 분리한다.
- Status: open

## 2026-03-22
- Context: 사용자가 `master` 반영 후 Docker 배포까지 요청했다.
- Current state:
1. [docker-compose.yml](C:/Users/kin50/Documents/test/docker-compose.yml)은 이제 `data/heatmaps`, `data/state`, `data/logs`를 모두 bind mount 한다.
2. Docker Desktop daemon을 올린 뒤 `docker compose up -d --build`로 `discord-heatmap-bot`을 recreate 했고, 현재 컨테이너는 `Up` 상태다.
3. [data/logs/bot.log](C:/Users/kin50/Documents/test/data/logs/bot.log)에는 `2026-03-22 22:26:43` 기준 `11 commands synced`, `Auto screenshot scheduler started`, `Intel scheduler started`, `Logged in as Drumstick#9496`가 남아 있다.
4. [data/state/state.json](C:/Users/kin50/Documents/test/data/state/state.json)도 새 컨테이너 기동 직후 시각으로 갱신돼 state mount가 실제로 동작한다.
- Next:
1. 운영 env의 `WATCH_ALERT_CHANNEL_ID`와 `ADMIN_STATUS_CHANNEL_ID` 적합성은 앞선 Discord smoke 결과를 기준으로 다시 정리한다.
- Status: done

## 2026-03-22
- Context: 사용자가 env의 채널/포럼 ID를 갱신한 뒤 실제 Discord 검증을 다시 요청했다.
- Current state:
1. `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`는 현재 모두 같은 forum 채널(`1471842980787917005`)을 가리키며, 이 forum에서 create/update smoke thread가 다시 성공했다.
2. smoke thread는 [default/news/eod forum smoke](https://discord.com/channels/332110589969039360/1485250008847614035)다.
3. `WATCH_ALERT_CHANNEL_ID`도 같은 forum 채널이라 현재 코드의 watch poll fallback 용도에는 맞지 않는다. `discord.ForumChannel`은 이 경로에서 기대하는 messageable text 채널이 아니다.
4. `ADMIN_STATUS_CHANNEL_ID=1483007026023108739`는 `fetch_channel()` 시 `403 Missing Access`로 실패한다.
5. 봇 login/Gateway/slash command 11개 sync 자체는 여전히 정상이다.
- Next:
1. watch alert fallback을 실제로 쓰려면 `WATCH_ALERT_CHANNEL_ID`를 text channel 계열로 바꾼 뒤 다시 send smoke를 한다.
2. admin status 채널을 쓸 계획이면 해당 채널 권한을 먼저 열고 다시 fetch/send smoke를 한다.
- Status: done

## 2026-03-22
- Context: 사용자가 실제 Discord 네트워크까지 포함한 live 실행 검증을 요청했다.
- Current state:
1. `.env`의 실제 bot token과 `DEFAULT_FORUM_CHANNEL_ID`로 봇 로그인, Gateway 연결, 글로벌 slash command 11개 sync까지 성공했다.
2. 기본 포럼 채널 fetch와 posting 권한 확인 후, `discord_live_smoke` key로 실제 forum thread를 생성하고 같은 thread를 다시 update해 Discord write path를 실서버에서 검증했다.
3. smoke posting에는 실제 `kospi` live capture PNG(`207749` bytes)를 첨부해 Discord attachment 경로도 함께 확인했다.
4. 추가로 `.\.venv\Scripts\python.exe -m pytest -m live -q` 결과는 `2 passed`였다.
5. 현재 `data/state/state.json`에는 `system.job_last_runs.command-sync=ok`와 `commands.discord_live_smoke.daily_posts_by_guild` 오늘자 record가 남아 있다.
- Next:
1. slash interaction 자체(`/kheatmap`, `/health`)를 사용자 클라이언트에서 직접 누르는 운영 smoke가 필요하면 Discord 앱에서 한 번 더 실행해 interaction ingress까지 닫는다.
2. `discord_live_smoke` thread/state를 유지할지 정리할지 결정한다.
- Status: done

## 2026-03-22
- Context: 통합 테스트 케이스를 실행/리뷰/운영 해석용 문서로 분리 정리했다.
- Current state:
1. [docs/specs/integration-test-cases.md](C:/Users/kin50/Documents/test/docs/specs/integration-test-cases.md)에 현재 non-live 통합 테스트 43건이 기능 계약 단위로 정리돼 있다.
2. [docs/specs/integration-live-test-cases.md](C:/Users/kin50/Documents/test/docs/specs/integration-live-test-cases.md)에 live 캡처 2건과 flaky 해석 규칙이 별도로 정리돼 있다.
3. [README.md](C:/Users/kin50/Documents/test/README.md)와 [AGENTS.md](C:/Users/kin50/Documents/test/AGENTS.md) 테스트 가이드에서 두 문서를 바로 찾을 수 있다.
4. 초안 계획의 `NB-01~NB-13`, `EO-01~EO-07`와 달리 현재 source suite는 news core 12건, EOD 8건이라 문서 번호는 source truth에 맞춰 `NB-01~NB-12`, `EO-01~EO-08`을 사용한다.
- Next:
1. integration 테스트가 늘면 먼저 source 테스트와 marker를 수정하고, 같은 변경에서 두 문서를 같이 갱신한다.
2. 누락 고위험 케이스 섹션의 항목을 우선순위 후보로 삼아 다음 회귀 테스트 추가 작업을 잡는다.
- Status: done

## 2026-03-22
- Context: 기능 전체 통합 테스트 전용 subagent를 추가하고, 실제로 같은 역할 지침으로 integration suite를 실행했다.
- Current state:
1. [`.codex/agents/integration-tester.toml`](C:/Users/kin50/Documents/test/.codex/agents/integration-tester.toml)이 추가돼 `integration_tester` custom agent가 정의됐다.
2. 이 agent는 테스트 시 기본적으로 `.\.venv\Scripts\python.exe -m pytest tests/integration` 전체 suite를 먼저 실행하도록 고정돼 있다.
3. 이번 세션에서 같은 역할의 worker subagent로 full integration suite를 실행했고 결과는 `43 passed, 2 deselected`였다.
- Next:
1. 이후 검증 요청에서는 `integration_tester`를 먼저 쓰고, targeted test는 full integration 이후 필요할 때만 추가한다.
- Status: done

## 2026-03-22
- Context: PR `#12` review finding으로 auto screenshot state 보존 fix를 한 번 더 보강했다.
- Current state:
1. `bot/features/auto_scheduler.py`는 이제 success 후 refresh read가 empty state로 돌아오면 `last_auto_runs`를 다시 저장하지 않고 warning만 남긴다.
2. 즉 `load_state()`가 transient read/parse failure로 empty state를 돌려줘도, runner가 이미 저장한 `daily_posts_by_guild`/`last_images`를 near-empty save로 덮어쓰지 않는다.
3. `tests/integration/test_auto_scheduler_logic.py`에는 refresh read empty-state guard 회귀 테스트가 추가됐다.
- Next:
1. PR `#12`에 이 수정 커밋을 올리고 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-22
- Context: auto screenshot state 유실 fix가 테스트뿐 아니라 실제 파일 저장 흐름에서도 유지되는지 로컬에서 다시 검증했다.
- Current state:
1. 임시 `state.json` 기준 `process_auto_screenshot_tick()` 실행 후 `daily_posts_by_guild`, `last_images`, `last_auto_runs`가 함께 남는 것을 확인했다.
2. 즉 현재 수정은 "runner가 먼저 저장한 오늘자 post/cache state를 scheduler가 마지막 save에서 덮어쓰는 문제"를 on-disk 재현에서도 막는다.
3. 이번 검증은 isolated local state 파일과 fake runner로 수행했고, 실 Discord API 호출이나 운영 포럼 posting은 하지 않았다.
- Next:
1. live 확인이 필요하면 운영 봇 재기동 후 실제 auto run 직후 `data/state/state.json`과 auto-screenshot 로그를 함께 본다.
- Status: done

## 2026-03-22
- Context: project custom agent 3종이 app UI에서 모두 정상 생성되는 기준선이 확보됐고, subagent 호출 약속도 문서화했다.
- Current state:
1. `repo_explorer`, `reviewer`, `docs_researcher`는 현재 app UI에서 모두 생성 가능하다.
2. `docs_researcher`는 [`.codex/agents/docs-researcher.toml`](C:/Users/kin50/Documents/test/.codex/agents/docs-researcher.toml)에서 `web_search = "live"`를 제거한 뒤 정상 등록됐다.
3. 이 저장소의 기본 subagent 패턴은 `repo_explorer + reviewer + docs_researcher`이며, 새 스레드에서 한 번 명시한 뒤에는 같은 스레드 안에서 `기본 3-agent 패턴` 같은 축약 표현으로 재사용한다.
4. 위 약속은 [AGENTS.md](C:/Users/kin50/Documents/test/AGENTS.md)와 [docs/context/design-decisions.md](C:/Users/kin50/Documents/test/docs/context/design-decisions.md)에 반영돼 있다.
- Next:
1. 다음 subagent 작업에서는 문서 확인이 필요 없는 순수 로컬 코드 작업인지 먼저 보고 `docs_researcher` 생략 여부를 판단한다.
- Status: done

## 2026-03-22
- Context: Codex app 재시작 및 새 desktop thread 이후 project custom agent smoke test를 다시 시도했다.
- Current state:
1. [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml)과 `.codex/agents/*.toml`은 그대로 유지했고, 이번 세션에서는 검증만 다시 수행했다.
2. `Get-Command codex`/`where.exe codex` 기준 desktop 번들 실행 파일 경로 해석은 정상이다.
3. 하지만 `codex --version`, `codex --help`는 여전히 `Access is denied`로 실패해 shell에서 custom agent runtime을 직접 올릴 수 없었다.
4. developer `spawn_agent`는 `repo_explorer`, `reviewer`, `docs_researcher`를 여전히 `unknown agent_type`로 반환했다.
5. control로 built-in `explorer` subagent는 정상 응답했으므로, 현재 문제 범위는 "subagent 전체 장애"가 아니라 "project custom agent가 이 runtime/tool surface에 노출되지 않음" 쪽으로 더 좁혀졌다.
6. Codex app 로컬 로그 [`codex-desktop-1c769110-b0a4-4a47-8779-b5a6f2f5ca94-12756-t0-i1-034007-0.log`](C:/Users/kin50/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/Codex/Logs/2026/03/22/codex-desktop-1c769110-b0a4-4a47-8779-b5a6f2f5ca94-12756-t0-i1-034007-0.log)에는 bundled `codex.exe` stdio spawn과 `Codex CLI initialized`가 남아 있어, app 내부 app-server 초기화 자체는 성공한 상태다.
- Next:
1. 실제 custom agent smoke test는 Codex app UI에서 custom agent 선택 후 각각 한 번씩 실행해 결과를 확인한다.
2. 필요하면 desktop app UI 노출과 developer `spawn_agent` 노출 범위 차이를 별도로 조사한다.
- Status: done

## 2026-03-22
- Context: project-scoped Codex 설정을 현재 저장소 작업 패턴에 맞게 보수적으로 정리했다.
- Current state:
1. [`.codex/config.toml`](C:/Users/kin50/Documents/test/.codex/config.toml)은 이제 `gpt-5.3-codex` 기본 모델, `model_reasoning_effort=medium`, `model_verbosity=low`, `personality=pragmatic`, `plan_mode_reasoning_effort=high`, `web_search=cached`, `project_doc_max_bytes=16384`를 명시한다.
2. subagent 전역 설정은 `max_threads=4`, `max_depth=1`, `job_max_runtime_seconds=1800`으로 맞춰져 있다.
3. `repo_explorer`, `reviewer`, `docs_researcher` custom agent는 각각 역할별 모델과 reasoning 강도가 명시돼 있고, 이후 호환성 보정으로 `docs_researcher`의 `web_search=live` override는 제거됐다.
4. `review_model` 같은 별도 리뷰 전용 top-level 키는 공식 `config-reference`에서 확인되지 않아 넣지 않았다.
5. 현재 desktop thread에서 built-in `explorer` subagent 생성은 성공해 multi-agent 경로 자체는 정상이다.
6. 반면 developer `spawn_agent`는 project custom agent 이름을 인식하지 않았고, shell에서 `codex` 실행도 `Access is denied`라 실제 custom-agent runtime smoke test는 완료하지 못했다.
- Next:
1. Codex app 재시작 후 custom agent 선택 경로에서 `repo_explorer`, `reviewer`, `docs_researcher`를 한 번씩 실행해 runtime smoke test를 다시 확인한다.
2. 병렬성이 부족하면 `max_threads` 상향 여부를 다시 검토한다.
- Status: done

## 2026-03-20
- Context: 원격 최신 상태를 fetch한 뒤 로컬 `develop`를 fast-forward 하고, auto screenshot state 유실 fix 필요 여부를 바로 점검했다.
- Current state:
1. 로컬 `develop`는 이제 `origin/develop` 최신 `2a69fcd codex/watch registry hybrid news (#11)`까지 반영된 상태다.
2. `origin/codex/fix-auto-screenshot-state`의 핵심 수정은 최신 `develop`에도 여전히 유효했고, 로컬 `develop`에 같은 보완을 적용했다.
3. `bot/features/auto_scheduler.py`는 성공 후 `load_state()`를 다시 읽고 `last_auto_runs`만 기록해, runner가 저장한 오늘자 `daily_posts_by_guild`/cache state를 덮어쓰지 않는다.
4. `tests/integration/test_auto_scheduler_logic.py`에는 runner 저장 state 보존 회귀 테스트가 추가됐다.
5. 로컬 `scheduler -> manual` 재현에서도 `CREATE_CALLS=1`, `kheatmap 포스트 수정 완료`로 확인돼 같은 날 수동 `/kheatmap`은 기존 thread 수정 경로를 사용한다.
- Next:
1. 필요하면 이 fix를 기준으로 별도 브랜치/PR 정리를 진행한다.
2. 운영 봇 재기동 후 auto screenshot 실행에서 오늘자 state entry와 `last_auto_runs`가 함께 남는지 확인한다.
- Status: open

## 2026-03-20
- Context: 운영 Discord 서버에서 15:35 자동 `kheatmap` thread가 코스닥 timeout으로 코스피만 올린 뒤, 같은 날 수동 `/kheatmap`이 기존 글 수정이 아니라 새 글을 만든 이유를 조사했다.
- Current state:
1. 코드 계약상 이 현상은 `오늘자 kheatmap state record 부재` 또는 `기존 thread/message fetch 실패`일 때만 생긴다.
2. `kosdaq` render timeout 자체는 원인이 아니다. 성공 이미지가 하나라도 있으면 heatmap runner는 그대로 forum upsert를 수행한다.
3. 운영 봇 프로세스는 `2026-03-20 09:14`에 시작됐고, state 경로를 `data/state/state.json`으로 옮긴 커밋은 `2026-03-20 10:37`에 들어갔다. 즉 실제 런타임은 state 경로 변경 전 코드를 계속 들고 있었을 가능성이 높다.
4. 로컬 최신 `data/state/state.json`에는 오늘자 `kheatmap` record가 없고 `auto_screenshot_enabled=false`라서, 15:35 자동 게시를 만든 state로 설명되지 않는다.
5. 레거시 `data/heatmaps/state.json`은 조사 시점에 비어 있는 형태로 다시 생성돼 있었고, 아직 레거시 state 경로를 바라보는 런타임/state drift가 있음을 시사한다.
- Next:
1. 운영 배포 시에는 봇 프로세스를 완전히 내린 뒤 브랜치 checkout/코드 변경/상태 마이그레이션을 수행한다.
2. 실제 운영 재기동 후에는 `STATE_FILE` 경로와 오늘자 `kheatmap` state entry 기록을 로그로 남기도록 운영 체크를 추가하는 편이 안전하다.
3. 같은 Discord 토큰으로 다른 호스트/세션이 동시에 떠 있는지도 한 번 점검한다.
- Status: open

## 2026-03-20
- Context: KIS 단독 전략 보완을 위해 watch/name 중심의 local instrument registry, hybrid news, paused EOD 기준선을 구현했다.
- Current state:
1. `bot/intel/data/instrument_registry.json` generated artifact가 추가됐고, 현재 registry는 국내 seed 20종목 + SEC 미국 상장사 7,518건으로 총 7,538건이다.
2. `/watch add`, `/watch remove`는 이제 종목명/코드/티커를 모두 받고 autocomplete를 지원하며, 저장값은 canonical symbol(`KRX:005930`, `NAS:AAPL`)이다.
3. `bot/forum/repository.py`는 legacy watchlist/baseline/cooldown 키를 읽을 때 canonical symbol로 자동 승격한다.
4. watch alert 메시지와 `/watch list`는 `이름 + canonical symbol` 형식으로 보여준다.
5. news provider는 `NEWS_PROVIDER_KIND=marketaux|hybrid`를 지원하고, `hybrid`는 국내 Naver + 해외 Marketaux 조합이다.
6. `/source-status`는 `instrument_registry`, `kis_quote`, `naver_news`, `marketaux_news`, `massive_reference`, `twelvedata_reference`, `openfigi_mapping`, `eod_provider`의 configured/disabled/paused 상태를 합성해 보여준다.
7. `EOD_SUMMARY_ENABLED` 기본값은 이제 `false`고, EOD는 문서/상태상 pause 기준으로 정리됐다.
8. 전체 테스트는 `.\.venv\Scripts\python.exe -m pytest -q` 기준 전부 통과했다.
- Next:
1. 국내 종목명 커버리지를 full master로 넓히려면 `DART_API_KEY`를 넣고 `scripts/build_instrument_registry.py`를 다시 실행한다.
2. `NEWS_PROVIDER_KIND=hybrid`와 `MARKETAUX_API_TOKEN`을 실제 값으로 넣고 global news fetch 품질을 한 번 실반영으로 점검한다.
3. `Massive`(구 `Polygon.io`)를 US fallback quote/reference로 붙이고, `OpenFIGI`/`Twelve Data`는 reconciliation/future EOD slot으로 이어 붙인다.
- Status: open

## 2026-03-20
- Context: runtime state 파일과 외부 참고문서 위치를 정리하는 구조 변경을 반영했다.
- Current state:
1. 앱 state 기본 경로는 이제 `data/state/state.json`이다.
2. `bot/forum/repository.py`는 기존 `data/heatmaps/state.json`이 남아 있으면 새 경로로 자동 마이그레이션한다.
3. 외부 벤더 문서/스프레드시트/PDF는 앞으로 `docs/references/external/` 아래에 모아 둔다.
4. 워크스페이스에 남아 있던 기존 `data/heatmaps/state.json`과 외부 참고 xlsx도 각각 새 위치 기준으로 정리했다.
5. 관련 문서 기준도 `AGENTS.md`, `README.md`, `docs/context/goals.md`까지 새 경로로 맞췄고, 전체 테스트는 `89 passed, 2 deselected`다.
- Next:
1. 새 외부 참고문서가 생기면 `docs/references/external/` 아래에만 보관한다.
- Status: done

## 2026-03-20
- Context: `master -> develop` sync PR `#10`까지 마무리한 뒤, 앞으로의 릴리스/약속 문서화 규칙을 정리했다.
- Current state:
1. `PR #10`은 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/10`에서 `develop`으로 squash merge 완료됐고, 현재 로컬 기준 브랜치는 `develop`이다.
2. `develop` 최신 상태는 `master` 릴리스 수정과 후속 scheduler 보정까지 포함하며, 전체 테스트는 `88 passed, 2 deselected`다.
3. 앞으로 `develop -> master` 릴리스는 별도 release branch를 만들지 않고 `develop` 브랜치에서 직접 `master` 대상으로 PR을 연다.
4. 새 운영 약속이나 브랜치 전략 변경은 앞으로 `AGENTS.md`와 `docs/context/*`에 함께 남기는 것을 기본 규칙으로 삼는다.
- Next:
1. 다음 릴리스 요청이 오면 `develop`에서 바로 `master`로 direct PR을 연다.
2. 다음 세션에서도 새 약속이 생기면 공통 규칙은 `AGENTS.md`, 이유는 `design-decisions.md`, 실행 결과는 `development-log.md`, 최신 상태는 `session-handoff.md`에 남긴다.
- Status: open

## 2026-03-20
- Context: runtime state 파일과 외부 참고문서 위치를 정리하는 구조 변경을 반영했다.
- Current state:
1. 앱 state 기본 경로는 이제 `data/state/state.json`이다.
2. `bot/forum/repository.py`는 기존 `data/heatmaps/state.json`이 남아 있으면 새 경로로 자동 마이그레이션한다.
3. 외부 벤더 문서/스프레드시트/PDF는 앞으로 `docs/references/external/` 아래에 모아 둔다.
4. 워크스페이스에 남아 있던 기존 `data/heatmaps/state.json`과 외부 참고 xlsx도 각각 새 위치 기준으로 정리했다.
5. 관련 문서 기준도 `AGENTS.md`, `README.md`, `docs/context/goals.md`까지 새 경로로 맞췄고, 전체 테스트는 `89 passed, 2 deselected`다.
- Next:
1. 새 외부 참고문서가 생기면 `docs/references/external/` 아래에만 보관한다.
- Status: done

## 2026-03-20
- Context: `master -> develop` sync PR `#10`까지 마무리한 뒤, 앞으로의 릴리스/약속 문서화 규칙을 정리했다.
- Current state:
1. `PR #10`은 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/10`에서 `develop`으로 squash merge 완료됐고, 현재 로컬 기준 브랜치는 `develop`이다.
2. `develop` 최신 상태는 `master` 릴리스 수정과 후속 scheduler 보정까지 포함하며, 전체 테스트는 `88 passed, 2 deselected`다.
3. 앞으로 `develop -> master` 릴리스는 별도 release branch를 만들지 않고 `develop` 브랜치에서 직접 `master` 대상으로 PR을 연다.
4. 새 운영 약속이나 브랜치 전략 변경은 앞으로 `AGENTS.md`와 `docs/context/*`에 함께 남기는 것을 기본 규칙으로 삼는다.
- Next:
1. 다음 릴리스 요청이 오면 `develop`에서 바로 `master`로 direct PR을 연다.
2. 다음 세션에서도 새 약속이 생기면 공통 규칙은 `AGENTS.md`, 이유는 `design-decisions.md`, 실행 결과는 `development-log.md`, 최신 상태는 `session-handoff.md`에 남긴다.
- Status: open

## 2026-03-20
- Context: `master`의 release fix를 `develop`에 되돌려 넣기 위한 sync PR `#10`에서 Codex review finding 1건을 반영했다.
- Current state:
1. sync branch/PR은 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/10`이다.
2. `bot/features/intel_scheduler.py`는 trading-day skip을 forum resolution보다 먼저 처리해, 휴장일에는 forum lookup 장애가 있어도 `holiday` semantics를 유지한다.
3. forum channel resolution 중 `fetch_channel()` API 오류는 더 이상 `missing_forum`으로 숨기지 않고, 해당 guild만 failure로 집계한 채 다른 guild 처리를 계속한다.
4. 뉴스/EOD run detail은 `forum_resolution_failures`를 남기고, 같은 run에 resolution 오류가 있으면 `failed`를 기록한다.
5. `tests/integration/test_intel_scheduler_logic.py`는 뉴스/EOD forum resolution API failure, mixed guild continuation, holiday-precedence 회귀를 포함한다.
6. 관련 타깃 테스트는 `24 passed, 4 deselected`다.
- Next:
1. PR `#10`에 현재 수정 커밋을 푸시하고 `@codex review`를 다시 요청한다.
2. review가 clean이면 `develop`에 merge하고 sync branch를 정리한다.
- Status: open

## 2026-03-19
- Context: release PR `#9`의 여섯 번째 review까지 반영해 `news_briefing`과 `trend_briefing` partial guild failure false positive도 닫았다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 `news_briefing`, `trend_briefing`, `eod_summary`, `watch_poll` 모두 partial delivery failure를 `ok`로 숨기지 않는다.
2. `tests/integration/test_intel_scheduler_logic.py`는 뉴스 partial failure, 트렌드 partial failure, EOD partial failure, watch mixed failure 회귀를 모두 포함한다.
3. 전체 기본 테스트는 `82 passed, 2 deselected`다.
4. release PR은 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/9`이며, 최신 수정이 반영된 fresh Codex review 결과만 남아 있다.
- Next:
1. PR `#9`에 현재 수정 커밋을 푸시하고 `@codex review`를 다시 요청한다.
2. review가 clean이면 `master`로 squash merge하고 release branch를 정리한다.
- Status: open

## 2026-03-19
- Context: release PR `#9`의 다섯 번째 Codex review까지 반영해 `eod_summary` partial guild failure false positive도 닫았다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 EOD summary posting이 일부 guild에서만 성공한 경우에도 `failed > 0`이면 `eod_summary=failed`를 기록한다.
2. `tests/integration/test_intel_scheduler_logic.py`는 one-success/one-failure mixed-result EOD 회귀를 포함한다.
3. 전체 기본 테스트는 `80 passed, 2 deselected`다.
4. release PR은 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/9`이며, 최신 수정이 반영된 fresh Codex review가 끝나면 `master` merge를 진행하면 된다.
- Next:
1. PR `#9`에 현재 수정 커밋을 푸시하고 `@codex review`를 다시 요청한다.
2. review가 clean이면 `master`로 squash merge하고 release branch를 정리한다.
- Status: open

## 2026-03-19
- Context: release PR `#9`의 네 번째 review까지 반영해 watch_poll mixed failure와 forum stale content id drift도 막았다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 partial success가 있어도 quote/channel/send failure가 한 건이라도 있으면 `watch_poll=failed`를 남긴다.
2. `bot/forum/service.py`는 삭제된 follow-up message id가 남아 있을 때 stale `content_message_ids`를 state에서 정리한다.
3. 관련 회귀를 포함한 전체 기본 테스트는 `79 passed, 2 deselected`다.
4. release PR은 여전히 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/9`이고, 다음 단계는 이 수정 커밋 푸시 후 `@codex review` 재요청이다.
- Next:
1. PR `#9` 수정 커밋을 푸시한다.
2. `@codex review`를 다시 요청하고 clean이면 `master`에 merge한다.
- Status: open

## 2026-03-19
- Context: release PR `#9`의 추가 P1 review까지 반영해 뉴스/EOD 전역 forum fallback cross-guild leak도 막았다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 뉴스/EOD/watch 모두 resolved target channel의 guild ownership을 검증한다.
2. 뉴스/EOD는 다른 guild 소속 global fallback forum이면 provider fetch/posting을 시작하지 않고 `missing_forum`으로 건너뛴다.
3. 관련 회귀 테스트를 포함한 전체 기본 테스트는 `77 passed, 2 deselected`다.
4. release PR은 여전히 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/9`이고, 다음 단계는 이 수정 커밋 푸시 후 `@codex review` 재요청이다.
- Next:
1. PR `#9` 수정 커밋을 푸시한다.
2. `@codex review`를 다시 요청하고 clean이면 `master`에 merge한다.
- Status: open

## 2026-03-19
- Context: release PR `#9`의 추가 Codex review까지 반영해 `watch_poll` delivery failure false positive를 닫았다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 `alert_attempts`를 detail에 남기고, `channel.send(...)` 실패가 한 건이라도 있으면 `watch_poll=failed`를 기록한다.
2. watch poll 관련 회귀 테스트는 cross-guild fallback, all-quote-failure, alert-delivery-failure까지 포함한다.
3. 전체 기본 테스트는 `75 passed, 2 deselected`다.
4. release PR은 여전히 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/9`이고, 다음 단계는 이 수정 커밋 푸시 후 `@codex review` 재요청이다.
- Next:
1. PR `#9` 수정 커밋을 푸시한다.
2. `@codex review`를 다시 요청하고 clean이면 `master`에 merge한다.
- Status: open

## 2026-03-19
- Context: `develop` 내용을 `master`로 보내는 release branch PR `#9`에서 Codex review 후속 수정 2건을 반영했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 이제 watch alert channel이 현재 guild 소속인지 검증해, 전역 fallback channel이 다른 guild 채널로 새는 경우 해당 guild를 실패로 처리한다.
2. `watch_poll` 마지막 status는 더 이상 무조건 `ok`가 아니고, `processed/quote_failures/channel_failures/missing_channel_guilds/send_failures`를 바탕으로 `ok|failed|skipped`를 기록한다.
3. 관련 회귀를 포함한 전체 기본 테스트는 `74 passed, 2 deselected`다.
4. release PR은 `https://github.com/Eulga/discord-heatmap-bot-trading-calendar/pull/9`이고, 현재 다음 단계는 수정 커밋 푸시 후 Codex review 재요청이다.
- Next:
1. PR `#9` 수정 커밋을 푸시한다.
2. `@codex review`를 다시 요청하고 clean이면 `master`에 merge한다.
- Status: open

## 2026-03-19
- Context: 오래된 원격 작업 브랜치를 `origin/develop` 기준으로 다시 점검했다.
- Current state:
1. 원격 `origin/codex/file-logging`은 이미 `develop`에 patch-equivalent가 들어간 상태라 삭제했다.
2. 원격 `origin/codex/docs`에서는 `docs/reports/mvp-data-source-review-2026-03-12.md`만 현재 브랜치로 가져왔고, 나머지 변경은 이식하지 않았다.
3. `.gitignore`에 `.obsidian/`를 추가해 로컬 메모 폴더가 작업 트리에 다시 뜨지 않게 했다.
4. `origin/codex/docs`도 정리 완료라, 오래된 원격 작업 브랜치는 더 이상 남아 있지 않다.
- Next:
1. 로컬 검증 스크립트가 필요해지면 현재 뉴스/trend/forum upsert 테스트 구조에 맞춰 새로 설계한다.
- Status: open

## 2026-03-19
- Context: PR `#8` Codex review findings 2건을 반영했다.
- Current state:
1. `bot/forum/service.py`는 이제 starter thread/message state를 follow-up content sync 전에 먼저 기록해, sync 중 예외가 나도 같은 날짜 thread를 재사용할 수 있다.
2. `bot/features/news/trend_policy.py`는 oversized single theme block도 안전하게 분할 또는 truncate해서 region message 길이 제한을 넘지 않는다.
3. 관련 회귀를 포함한 전체 기본 테스트는 `72 passed, 2 deselected`다.
- Next:
1. PR `#8`에 수정 커밋을 푸시한다.
2. `@codex review`를 다시 요청하고 clean이면 `develop`에 merge한다.
- Status: open

## 2026-03-19
- Context: `trendbriefing` 전용 thread와 멀티-message forum upsert까지 포함한 트렌드 테마 뉴스 기능을 붙였다.
- Current state:
1. 뉴스 provider는 이제 `NewsAnalysis`를 만들고, conservative briefing items와 trend theme candidates를 분리해서 계산한다.
2. `trendbriefing`은 같은 뉴스 스케줄 tick에서 생성되며, thread 구조는 starter message + 국내 section message + 해외 section message다.
3. forum state의 `DailyPostEntry`에는 optional `content_message_ids`가 들어가고, rerun 시 하위 message들도 edit/create/delete된다.
4. 실데이터 기준 오늘은 국내 테마가 `반도체`, `자동차` 2개라 국내 section은 placeholder가 들어가고, 해외는 `금리/Fed`, `AI/반도체`, `에너지/원유`, `메가캡 기술주` 4개가 게시됐다.
5. 실제 thread URL은 `https://discord.com/channels/332110589969039360/1484089919285497967`다.
6. 전체 기본 테스트는 `69 passed, 2 deselected`다.
- Next:
1. 국내 실데이터 recall을 더 올릴지 보고 `전력설비`, `방산`, `건설/원전` probe/score를 추가 튜닝한다.
2. 실제 Discord에서 트렌드 테마 thread의 읽기 경험이 괜찮은지 확인하고, 필요하면 국내/해외 메시지를 더 잘게 나눌지 판단한다.
- Status: open

## 2026-03-19
- Context: 뉴스 브리핑을 국내/해외 별도 daily thread 2개로 분리했고, 실제 Discord 포럼에도 오늘자 split 결과를 반영했다.
- Current state:
1. 뉴스 스케줄러는 이제 `newsbriefing-domestic`, `newsbriefing-global` 두 thread를 upsert한다.
2. 오늘자 기존 통합 thread `https://discord.com/channels/332110589969039360/1484055161600213092`는 domestic thread로 재사용되며 제목이 `[2026-03-19 국내 경제 뉴스 브리핑]`로 바뀌었다.
3. 오늘자 global thread는 `https://discord.com/channels/332110589969039360/1484079599175336057`로 새 생성됐다.
4. 최신 실반영 기준 `news_briefing` detail은 `posted=1 failed=0 missing_forum=0 domestic=5 global=7`이고, `news_provider`는 `fetched=12`였다.
5. 관련 회귀를 포함한 전체 기본 테스트는 `61 passed, 2 deselected`다.
- Next:
1. Discord에서 split thread UX가 실제로 더 읽기 좋은지 확인한다.
2. global 기사 밀도가 다시 높아 보이면 query 세트 또는 source weight를 한 번 더 조정한다.
- Status: open

## 2026-03-19
- Context: 뉴스 브리핑을 `거시 헤드라인 + 헤드라인급 종목 기사` 구조로 다시 조정하고 오늘자 Discord thread도 갱신했다.
- Current state:
1. 네이버 뉴스 검색 API는 직접 `headline/top story` 플래그를 주지 않으므로, 현재는 query 구성과 score 기반 선별로 헤드라인을 근사한다.
2. `NaverNewsProvider`는 거시 query와 종목 query를 분리하고, 종목 기사는 제목에 고영향 이벤트 신호가 있을 때만 통과시킨다.
3. provider는 region별 score order를 유지하고, scheduler는 `story_key()`로 국내/해외 중복 기사를 한 번 더 제거한다.
4. 실제 Discord thread는 현재 `domestic=6`, `global=11`, `body_len=1956` 본문으로 갱신됐다.
- Next:
1. Discord에서 실제 체감 품질을 보고 `개장시황`, 설명형 해설 기사도 더 줄일지 판단한다.
2. 필요하면 `NAVER_NEWS_*_STOCK_QUERIES`와 stock alias를 한 번 더 튜닝한다.
- Status: open

## 2026-03-19
- Context: 20건 상한과 Discord 본문 길이 보완 후 오늘자 뉴스 브리핑 thread를 실제로 다시 갱신했다.
- Current state:
1. 오늘자 Discord thread는 현재 실데이터 기준 `domestic=5`, `global=17` 본문으로 갱신됐다.
2. 같은 본문 길이는 `1987`자로 Discord 2000자 제한 안에 들어간다.
3. thread URL은 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 가독성과 기사 밀도를 확인한다.
2. 국내 기사 수가 여전히 부족하면 dedup 세분화 여부를 검토한다.
- Status: open

## 2026-03-19
- Context: 사용자가 뉴스 브리핑을 지역별 최대 20건까지 넓히되, 품질이 부족하면 정확히 20건을 채우지는 않길 원했다.
- Current state:
1. `NAVER_NEWS_LIMIT_PER_REGION` 기준 상한은 scheduler와 provider 모두 20건으로 맞춰졌다.
2. `bot/features/news/policy.py`는 Discord 2000자 제한 안에서 본문을 안전하게 줄이도록 보완됐다.
3. 관련 회귀 테스트를 추가한 뒤 전체 `pytest`는 `53 passed, 2 deselected`다.
4. 실제 네이버 fetch 샘플 기준 현재 결과는 `domestic=5`, `global=17`이며, 같은 본문 길이는 `1987`자다.
- Next:
1. 실제 Discord thread를 다시 갱신할 때 본문이 최대 20건 기준으로 늘어났는지 확인한다.
2. 국내 기사 수가 계속 낮으면 query 세트는 유지한 채 dedup 정책을 더 세분화할지 판단한다.
- Status: open

## 2026-03-19
- Context: 국내 품질 튜닝 결과를 오늘자 Discord 뉴스 브리핑 thread에도 실제 반영했다.
- Current state:
1. 오늘자 브리핑 thread는 최신 필터 결과로 갱신됐다.
2. 현재 실제 게시 결과는 국내 3건, 해외 4건이다.
3. 국내는 `한은 총재/코스피 급락/국고채 금리` 축으로 정리됐고, 개별 종목/ETF headline은 빠졌다.
- Next:
1. Discord에서 결과물을 보고 이 방향을 유지할지 판단한다.
2. 글로벌도 더 다듬고 싶으면 `tokenpost.kr` 같은 소스 패널티를 추가 조정한다.
- Status: open

## 2026-03-19
- Context: 국내 뉴스 브리핑은 중복/잡음을 더 줄이기 위해 주제 dedup과 국내 query 세트 재조정을 적용했다.
- Current state:
1. 국내 기본 query는 `국내 증시, 코스피 지수, 코스닥 지수, 원달러 환율, 한국은행 금리`다.
2. 같은 코스피 장세 headline은 topic 단위로 1건만 남고, 개별 종목 `주가` 기사와 ETF headline은 제외된다.
3. 실데이터 샘플 기준 현재 국내 브리핑은 `코스피`, `국고채 금리`, `환율` 중심 3건으로 정리된다.
4. 전체 테스트는 `49 passed, 2 deselected`다.
- Next:
1. 이 품질을 실제 Discord 포럼에서 다시 확인하고, 괜찮으면 현재 query/weight를 기준선으로 고정한다.
2. 필요하면 글로벌 소스 패널티를 한 번 더 조정한다.
- Status: open

## 2026-03-19
- Context: 뉴스 브리핑을 실제 Discord 포럼에 1회 게시해 결과물 확인 경로까지 검증했다.
- Current state:
1. 오늘자(`2026-03-19`) 뉴스 브리핑 thread가 실제 guild forum에 생성됐다.
2. 생성된 thread 제목은 `[2026-03-19 아침 경제 뉴스 브리핑]`이다.
3. 실데이터 fetch -> scheduler -> forum upsert 전체 경로가 한 번 실제 운영 환경에서 검증됐다.
- Next:
1. Discord에서 본문 품질을 확인하고, 필요 시 국내 기사 필터링을 더 다듬는다.
2. 뉴스 브리핑 품질이 충분하면 다음 provider 후보로 넘어간다.
- Status: open

## 2026-03-19
- Context: 뉴스 브리핑을 "주요뉴스/속보" 쪽으로 더 가깝게 만들기 위해 네이버 필터링을 한 단계 더 강화했다.
- Current state:
1. `NaverNewsProvider`는 이제 다중 query 후보 수집 -> dedup -> gate 키워드 -> 중요도 점수 -> 저신호 패널티 순서로 기사 선별을 한다.
2. `global`은 미국 시장 직접 신호가 제목에 있어야 통과 가능성이 높아졌고, 실제 샘플에서도 FOMC/연준/나스닥 중심으로 정리됐다.
3. `domestic`은 이전보다 나아졌지만 아직 일부 테마/해설형 기사가 남을 수 있어 추가 튜닝 여지가 있다.
4. 관련 테스트는 전체 `pytest`까지 통과했다.
- Next:
1. `domestic`의 query/키워드/소스 정책을 한 번 더 조정해 시장 영향도가 낮은 기사 비중을 줄인다.
2. Discord 실운영 forum에 실제 브리핑을 붙여 사용자 체감 품질을 확인한다.
3. 뉴스 브리핑 품질이 안정되면 다음 provider 후보로 `EodSummaryProvider` 또는 `MarketDataProvider`를 진행한다.
- Status: open

## 2026-03-19
- Context: 네이버 뉴스 브리핑을 실제 자격증명으로 호출해 scheduler 경로까지 검증했다.
- Current state:
1. `NEWS_PROVIDER_KIND=naver`와 실제 네이버 Client ID/Secret으로 `_run_news_job()`가 성공했고 `news_briefing` status는 `ok`였다.
2. 현재 기본 query 기준으로 `domestic=5`, `global=5`는 채워지지만, `global` 결과에 국내 시장 기사도 일부 섞인다.
3. 즉, 인증/호출/렌더링 경로는 살아 있고 다음 이슈는 query 품질 튜닝이다.
- Next:
1. `NAVER_NEWS_GLOBAL_QUERY`를 조정해 해외 기사 purity를 높인다.
2. 필요하면 `NAVER_NEWS_DOMESTIC_QUERY`도 국내 증시/코스피/코스닥 중심으로 좁혀 비교한다.
3. query가 안정되면 Discord 실운영 forum에 실제 아침 브리핑 포스트를 한 번 검증한다.
- Status: open

## 2026-03-19
- Context: 뉴스 브리핑에 네이버 뉴스 검색 API adapter를 붙일 수 있는 코드 경로를 추가했다.
- Current state:
1. `bot/intel/providers/news.py`는 `NaverNewsProvider`를 지원하고, `NEWS_PROVIDER_KIND=naver`일 때만 실제 API를 사용한다.
2. 네이버 응답은 `domestic`/`global` 쿼리를 별도로 호출해 지역을 나누고, `originallink` 도메인으로 source를 채운다.
3. 키가 없거나 provider 종류가 잘못됐으면 부트 대신 fetch 시점에 provider failure로 기록되도록 `ErrorNewsProvider`가 들어 있다.
4. 관련 테스트는 `test_news_provider.py` 추가 후 전체 `pytest`까지 통과했다.
- Next:
1. `.env`에 네이버 Client ID/Secret을 넣고 `NEWS_PROVIDER_KIND=naver`로 바꾼 뒤 실제 fetch 결과를 확인한다.
2. `NAVER_NEWS_DOMESTIC_QUERY`, `NAVER_NEWS_GLOBAL_QUERY`가 브리핑 품질에 맞는지 샘플 결과를 보고 조정한다.
3. 실데이터가 안정적이면 다음 provider 후보인 `EodSummaryProvider` 또는 `MarketDataProvider` 작업으로 넘어간다.
- Status: open

## 2026-03-18
- Context: `ship-develop` review loop 검증과 `develop` merge를 끝냈고, 임시 backup 브랜치도 정리했다.
- Current state:
1. PR `#7`은 `@codex review`가 `clean`으로 끝난 뒤 squash merge됐고, 최종 merge commit은 `596871d`다.
2. `ship_develop.py`는 review comment pagination과 `headRefOid` drift 보호를 포함한 상태다.
3. 현재 로컬 브랜치는 `develop`, `master`, `release/v1`, `codex/docs`, `codex/file-logging`만 남아 있고 작업 트리는 깨끗하다.
4. shipping 자동화는 이제 실제 merge까지 한 번 검증된 상태다.
- Next:
1. `docs/specs/external-intel-api-spec.md` 기준으로 첫 실사용 외부 provider 구현 범위를 고른다. 권장 시작점은 `NewsProvider`다.
2. `.\.venv\Scripts\python -m pytest`와 `python -m bot.main`으로 `develop` 기준 기본 회귀와 부트를 다시 확인한다.
3. Discord 실운영에서 `/setforumchannel`, `/kheatmap`, `/usheatmap`, 확장 scheduler 흐름 검증 순서를 정리한다.
- Status: open

## 2026-03-18
- Context: PR `#7` Codex review에서 pagination 누락이 지적돼 `ship-develop` comment 조회를 보강했다.
- Current state:
1. `ship_develop.py`는 issue/review comments를 single page가 아니라 paging으로 읽는다.
2. py_compile, historical PR 분류 재검증, skill validator는 다시 통과했다.
3. 현재 해야 할 일은 이 fix를 PR `#7`에 푸시하고 `@codex review`를 다시 돌린 뒤 findings가 닫혔는지 확인하는 것이다.
- Next:
1. PR `#7`에 pagination fix를 푸시
2. `@codex review` 재요청
3. findings가 없으면 merge
- Status: open

## 2026-03-18
- Context: `ship-develop` 기본 동작을 Codex review loop 중심으로 바꿨다.
- Current state:
1. `ship_develop.py`는 `--codex-review`와 `--wait-codex-seconds`를 지원한다.
2. 스크립트는 `@codex review`를 요청한 뒤 `chatgpt-codex-connector` / `chatgpt-codex-connector[bot]` 응답 패턴으로 `clean`, `findings`, `pending`을 판별한다.
3. 기본 shipping UX는 "PR 생성 또는 갱신 -> Codex review -> findings 수정 -> 재검토 -> clean이면 merge"다.
4. human review gate는 여전히 가능하지만, 명시 요청 시 `--require-review`로만 켠다.
5. py_compile, dry-run, historical PR 분류 검증, skill validator는 통과했다.
- Next:
1. 다음 실제 `develop에 합쳐` 요청에서 Codex review loop 기본 경로를 실전 검증한다.
- Status: open

## 2026-03-18
- Context: `ship-develop`이 리뷰 없이 바로 merge하지 않도록 review gate를 추가했다.
- Current state:
1. `ship_develop.py`는 `--require-review`와 `--wait-review-seconds`를 지원한다.
2. review가 승인되지 않았으면 PR URL과 함께 `review-required` 상태로 멈춘다.
3. `develop` shipping 기본 흐름은 같은 스크립트를 두 번 쓰는 two-pass다. 첫 실행은 PR 생성 또는 갱신, 두 번째 실행은 승인 후 merge다.
4. py_compile, dry-run, skill validator는 통과했다.
- Next:
1. 다음 실제 shipping 요청에서 review gate가 원하는 UX로 동작하는지 실전 확인한다.
- Status: open

## 2026-03-18
- Context: `ship-develop`을 실제 merge에 사용했더니, `gh pr merge --delete-branch` 이후 로컬 브랜치가 이미 지워진 경우 cleanup 단계가 한 번 더 지우려다 실패했다.
- Current state:
1. 현재 작업 브랜치는 `codex/ship-develop-cleanup`이다.
2. `ship_develop.py`는 이제 local branch가 이미 없어도 `already-gone`으로 정상 처리한다.
3. py_compile과 skill validator는 다시 통과했다.
- Next:
1. 이 cleanup fix를 `develop`에 반영한다.
- Status: open

## 2026-03-18
- Context: `develop으로 합쳐` 요청을 한 번의 흐름으로 처리하기 위한 GitHub shipping skill을 추가했다.
- Current state:
1. `.agents/skills/ship-develop/`와 `scripts/ship_develop.py`가 생겼다.
2. 현재 GitHub repo는 default branch=`master`, `develop` 브랜치 별도 운영, `allow_auto_merge=false`, `delete_branch_on_merge=false` 상태다.
3. `gh`는 `C:\Program Files\GitHub CLI\gh.exe`에 설치돼 있고, 계정 `Eulga`로 로그인되어 있다.
4. 새 script는 current branch push, PR create/reuse, checks/review 상태 확인, direct merge, `develop` checkout, local branch 삭제까지 처리한다.
5. dry-run과 공식 skill validator는 통과했다.
- Next:
1. 다음 실제 shipping 요청에서 `$ship-develop`으로 실전 검증한다.
2. 필요하면 wait time이나 merge method 기본값을 조정한다.
- Status: open

## 2026-03-18
- Context: PR `#4`의 Codex Connector P1 두 건을 반영해 같은 분 내 반복 tick이 기존 성공 상태를 `skipped`로 덮어쓰는 문제를 수정했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 뉴스/장마감 모두 `completed_guilds`를 계산해 이미 성공한 tick 결과를 no-target early return이 덮어쓰지 않는다.
2. `tests/integration/test_intel_scheduler_logic.py`에 뉴스/EOD 상태 보존 회귀 테스트가 추가됐다.
3. 전체 기본 테스트는 `.\.venv\Scripts\python.exe -m pytest` 기준 `40 passed, 2 deselected`다.
- Next:
1. 현재 수정 커밋을 PR `#4`에 푸시한다.
2. `@codex review`를 다시 호출해 P1이 닫혔는지 확인한다.
- Status: open

## 2026-03-18
- Context: project-scoped Codex custom agent와 repo skill 최소 골격을 저장소에 추가했다.
- Current state:
1. `.codex/config.toml`에 `[agents] max_threads=3`, `max_depth=1`이 들어가 있다.
2. read-only custom agent `repo_explorer`, `reviewer`, `docs_researcher`가 `.codex/agents/` 아래에 생겼다.
3. repo skill `external-intel-provider-rollout`가 `.agents/skills/` 아래에 생겼고, 외부 provider 실사용 전환용 절차가 들어가 있다.
4. 현재 프로젝트 `.venv`에 `PyYAML 6.0.3`이 설치돼 있고, 공식 `quick_validate.py`도 통과했다.
- Next:
1. 다음 실제 외부 provider 작업에서 새 agent/skill을 직접 써 보고 지침을 조정한다.
- Status: open

## 2026-03-18
- Context: Codex subagents/custom agents 운영 방식을 이 저장소에 접목할 수 있는지 검토했다.
- Current state:
1. 공식 문서 기준으로 subagents는 명시 요청형 병렬 작업, `AGENTS.md`는 공통 지침, skills는 재사용 workflow 패키징으로 역할이 분리된다는 점을 확인했다.
2. 현재 저장소에는 project-scoped `.codex/agents/`와 repo `.agents/skills/`가 아직 없다.
3. 이 프로젝트는 외부 provider 조사, 리뷰, 문서 검증처럼 read-heavy 작업은 분업 이점이 있지만, 실제 코드 수정은 single-writer가 더 안전하다는 판단을 정리했다.
- Next:
1. 도입 시 최소 세트로 `reviewer`, `repo_explorer`, `docs_researcher` 같은 read-only custom agent부터 추가한다.
2. 구현은 메인 세션 또는 단일 worker가 맡고, 반복 체크리스트는 skill로 분리한다.
3. `Agents SDK + Codex MCP`는 multi-repo 자동화나 상위 orchestration 필요가 생길 때 다시 검토한다.
- Status: open

## 2026-03-18
- Context: 리뷰 실수를 반복하지 않도록 첫 번째 리뷰 운영 규칙을 추가했다.
- Current state:
1. `docs/context/review-rules.md`가 새로 생겼다.
2. Rule 1은 `실패 경로와 운영 정합성까지 리뷰한다`이며, scheduler/status/doc/docker 정합성을 함께 보도록 고정했다.
3. `AGENTS.md`와 `docs/context/README.md`도 리뷰 작업 시 이 문서를 먼저 읽도록 연결됐다.
- Next:
1. 다음 리뷰부터 `review-rules.md`를 기준으로 체크한다.
2. 새 누락 유형이 확인되면 같은 문서에 Rule 2를 추가한다.
- Status: open

## 2026-03-17
- Context: 최신 리뷰에서 나온 운영 가시성과 문서 정합성 이슈를 `codex/review-fixes` 브랜치에서 정리했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 뉴스 dedup을 fetch 단위로만 처리하고, 뉴스/장마감 job status를 실제 게시 결과 기준으로 `skipped`/`failed`/`ok`로 구분한다.
2. `docker-compose.yml`은 `data/logs`도 볼륨 마운트해 런타임 로그 파일이 컨테이너 재생성 후에도 남는다.
3. `README.md`와 `AGENTS.md`는 `python -m bot.main`, `/health` 중심 quick test, PowerShell 활성화 경로로 갱신됐다.
4. 관련 회귀를 포함한 전체 기본 테스트는 `.\.venv\Scripts\python -m pytest` 기준 `38 passed, 2 deselected`다.
- Next:
1. `codex/review-fixes` 브랜치로 PR을 열어 리뷰에서 지적된 이슈가 모두 닫혔는지 확인한다.
- Status: open

## 2026-03-17
- Context: 현재 브랜치의 `bot/app/bot_client.py` 병합 충돌을 정리했다.
- Current state:
1. 충돌은 command sync 상태 기록 변경과 로깅 전환 변경이 같은 구간을 건드리면서 발생했다.
2. 현재 구현은 command sync 성공/실패 상태 기록을 유지하면서 콘솔 출력을 `logger` 기반으로 통일했다.
3. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py`는 통과했고, 충돌 파일은 더 이상 `UU` 상태가 아니다.
- Next:
1. 남은 변경 묶음을 기준으로 커밋 또는 추가 병합 정리를 진행한다.
2. 필요 시 전체 `pytest` 또는 봇 실행으로 부트 경로를 한 번 더 확인한다.
- Status: open

## 2026-03-17
- Context: 새로 추가한 뉴스/장마감/watch 스케줄을 실사용 단계로 전환하기 위한 외부 API 명세를 우선 과제로 추가했다.
- Current state:
1. `docs/specs/external-intel-api-spec.md`가 추가됐고, 뉴스 브리핑, 장마감 요약, watch quote에 필요한 정규화 계약이 정의됐다.
2. `docs/context/goals.md`의 최우선 목표는 확장 스케줄 실사용 전환으로 올라갔다.
3. `AGENTS.md`와 `README.md`도 같은 명세 경로를 기준으로 읽도록 맞췄다.
- Next:
1. 실제 외부 API 또는 중간 adapter 후보를 선택한다.
2. `NewsProvider`, `EodSummaryProvider`, `MarketDataProvider`를 이 명세 기준으로 구현한다.
3. Discord 실운영 환경에서 스케줄 포스트/알림을 검증한다.
- Status: open

## 2026-03-17
- Context: PR `#3`에서 Codex Connector 리뷰 1건을 반영했다.
- Current state:
1. 지적 내용은 command sync 상태 저장 실패가 봇 시작을 깨뜨릴 수 있다는 점이었다.
2. 현재 구현은 상태 저장 실패를 fail-open으로 바꿨고, 관련 테스트도 추가됐다.
3. 수정 후 전체 기본 테스트는 다시 통과했다.
- Next:
1. 수정 커밋을 PR `#3`에 푸시
2. 추가 리뷰가 없으면 머지 및 원격 브랜치 삭제
- Status: open

## 2026-03-17
- Context: 슬래시 커맨드 동기화 실패 진단 메시지와 상태 기록 기능을 브랜치에서 정리 중이다.
- Current state:
1. `bot/app/bot_client.py`는 command sync 실패를 잡아 상태 파일에 `command-sync` 마지막 실행 결과를 기록한다.
2. `bot/app/command_sync.py`는 설치/권한/토큰/스키마 오류에 대한 한국어 힌트를 만든다.
3. 관련 테스트와 전체 기본 테스트는 모두 통과했다.
- Next:
1. 이 변경을 커밋하고 `origin/develop` 기준으로 PR diff를 정리한다.
2. PR 생성 후 Codex Connector 리뷰를 확인한다.
- Status: open

## 2026-03-17
- Context: `codex/context-summary` 브랜치의 PR 생성부터 merge, 원격 브랜치 삭제까지 완료했다.
- Current state:
1. PR `#2`는 `develop`에 squash merge 됐다.
2. 원격 브랜치 `codex/context-summary`는 삭제됐다.
3. 현재 로컬 작업 디렉터리에는 이번 흐름과 별개의 미커밋 변경이 남아 있다.
- Next:
1. 필요 시 로컬에서 `develop` 최신 상태를 fetch/pull 한다.
2. 남은 로컬 변경은 별도 브랜치 또는 커밋으로 정리한다.
- Status: done

## 2026-03-17
- Context: `codex/context-summary` 브랜치를 `develop`로 보내기 위한 PR 준비를 진행했다.
- Current state:
1. 원격 브랜치 `codex/context-summary`는 최신 로컬 HEAD(`3a5bdfd`)까지 푸시됐다.
2. GitHub compare 기준 `develop...codex/context-summary`는 1 commit / 1 file changed / able to merge 상태다.
3. 현재 세션에는 `gh` CLI가 없고 GitHub 브라우저 세션도 로그인되지 않아 PR 생성 API 호출을 끝내지 못했다.
- Next:
1. GitHub 인증 가능한 환경에서 PR 생성
2. 체크 통과 확인 후 merge
3. merge 후 원격 브랜치 삭제
- Status: done

## 2026-03-17
- Context: 현재 프로젝트 목표를 다음 세션에서도 바로 복구할 수 있게 goals 문서를 추가했다.
- Current state:
1. 현재 우선 목표는 운영 안정화, 히트맵 게시 실운영 검증, 자동 스케줄 신뢰도 확보다.
2. 운영 가시성 강화와 확장 기능 운영화는 그 다음 레이어로 정리했다.
3. 목표 문서는 `docs/context/goals.md`에 따로 분리했다.
- Next:
1. 다음 작업 시작 전 `session-handoff.md`와 `goals.md`를 함께 확인한다.
- Status: done

## 2026-03-17
- Context: 바이브 코딩 규칙을 `AGENTS.md`에 직접 녹여 운영 규칙으로 편입했다.
- Current state:
1. `AGENTS.md` 상단에 `바이브 코딩 운영 규칙` 섹션이 추가됐다.
2. `docs/prompts/vibe-coding-rule-prompt.md`는 상세 원문 보관용으로 유지된다.
3. 이후 세션은 `AGENTS.md`만 읽어도 바이브 코딩 규칙을 바로 적용할 수 있다.
- Next:
1. 실제 작업 중 규칙이 과하거나 빠진 부분이 보이면 `AGENTS.md`와 프롬프트 원문을 함께 조정한다.
- Status: done

## 2026-03-17
- Context: 현재 유행하는 바이브 코딩 규칙을 조사해 프로젝트용 단일 프롬프트 초안을 만들었다.
- Current state:
1. 프롬프트 초안은 `docs/prompts/vibe-coding-rule-prompt.md`에 저장돼 있다.
2. 초안은 속도 규칙뿐 아니라 검증, 위험 작업 통제, 컨텍스트 로그 갱신까지 포함한다.
3. 이후 운영 편입을 위한 기준 문서로 사용한다.
- Next:
1. 운영 중 표현이나 우선순위가 맞지 않으면 원문과 `AGENTS.md`를 함께 수정한다.
- Status: done

## 2026-03-17
- Context: 여러 위치에서 Codex를 사용할 때 프로젝트 판단 기준이 흔들리지 않도록 분류형 컨텍스트 저장 체계를 도입했다.
- Current state:
1. `AGENTS.md`가 `docs/context/*`를 먼저 읽도록 갱신됐다.
2. 검토, 개발, 설계 메모를 별도 파일에 누적하는 구조를 만들었다.
3. 아직 이 구조를 실제 기능 작업 로그로 채우기 시작한 단계는 아니다.
- Next:
1. 다음 작업부터 결과를 해당 카테고리 문서에 바로 누적한다.
2. 기능 변경이 있으면 `development-log.md`와 `session-handoff.md`를 함께 갱신한다.
3. 설계 판단이 생기면 `design-decisions.md`에 이유까지 적는다.
- Status: open

