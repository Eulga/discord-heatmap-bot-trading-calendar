# Review Log

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
