# 통합 테스트 케이스

## 문서 목적
- 이 문서는 `tests/integration`의 현재 non-live 통합 테스트를 기능 계약 단위로 다시 서술한 운영 문서다.
- 테스트 구현자, 리뷰어, QA/운영 검증 담당자, future subagent가 "무엇이 보호되고 무엇이 아직 비어 있는지"를 빠르게 판단할 수 있게 만드는 것이 목적이다.
- 최신 파일별 케이스 수와 기본 실행 포함 여부는 아래 `Suite 개요`와 `pytest --collect-only -q -m "not live"` 결과를 source of truth로 본다.

## 독자
- 개발자: 변경이 어떤 회귀를 깨뜨릴 수 있는지 확인한다.
- 리뷰어: 테스트가 진짜로 보호하는 계약과 아직 빠진 고위험 경로를 구분한다.
- QA/운영 검증 담당: 어떤 시나리오를 로컬 통합 테스트가 이미 대신 보장하는지 판단한다.
- future subagent: `tests/integration` 전체 실행 결과를 단순 pass/fail이 아니라 기능 계약 단위로 해석한다.

## 실행 기준
- 기본 실행 명령:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration
```

- 현재 `pytest.ini` 기본 옵션은 `-m "not live"`다.
- 따라서 `tests/integration`를 그대로 돌려도 live marker가 붙은 캡처 테스트 2건은 deselect되고, 기본 integration suite는 non-live 76건만 실행된다.
- live 캡처 테스트는 별도 문서 [integration-live-test-cases.md](./integration-live-test-cases.md)로 분리한다.

## 문서 읽는 법
- 이 문서는 테스트 파일 순서가 아니라 기능 시나리오 순서로 정리한다.
- 문서에 포함된 각 케이스는 반드시 원본 테스트 함수명을 1회만 매핑한다.
- 상세 섹션은 운영상 의미가 큰 기능 계약을 우선 정리하고, 최신 전체 파일/케이스 inventory는 `Suite 개요`를 기준으로 해석한다.
- 상세 항목은 다음 템플릿을 고정 사용한다.
  - 테스트 ID
  - 기능/보호 계약
  - 원본 테스트 함수명
  - 사전 상태
  - 입력/트리거
  - mock/stub 전제
  - 기대 동작
  - 기대 상태 저장 변화
  - 기대 status/detail/log
  - 회귀 방지 포인트

## Suite 개요

| 기능 영역 | 파일 | 현재 케이스 수 | live 여부 | 기본 실행 포함 여부 | 대표 리스크 |
| --- | --- | ---: | --- | --- | --- |
| Auto scheduler | `tests/integration/test_auto_scheduler_logic.py` | 10 | 아니오 | 포함 | 거래일 판정, 중복 실행 방지, state overwrite |
| Forum upsert / runner | `tests/integration/test_forum_upsert_flow.py` | 9 | 아니오 | 포함 | 기존 thread 수정, content message sync, partial failure body/state |
| Intel scheduler | `tests/integration/test_intel_scheduler_logic.py` | 35 | 아니오 | 포함 | news/trend/eod status truthfulness, guild isolation, retry 가능성 |
| Watch forum flow | `tests/integration/test_watch_forum_flow.py` | 11 | 아니오 | 포함 | thread reuse/recreate, transient fetch failure isolation, forum route gating, remove non-creating contract |
| Watch poll forum scheduler | `tests/integration/test_watch_poll_forum_scheduler.py` | 11 | 아니오 | 포함 | starter/comment update, close finalization, missing forum/provider failure |
| Live capture | `tests/integration/test_capture_korea_live.py`, `tests/integration/test_capture_us_live.py` | 2 | 예 | 제외 | 외부 사이트 렌더, 파일 생성, flaky 네트워크 |

- 기본 문서 범위 합계: 76건
- live 문서 범위 합계: 2건
- 참고: 최초 계획안의 `NB-01~NB-13`, `EO-01~EO-07` 분할은 현재 소스 테스트 수와 1건씩 어긋난다.
- 이 문서의 exact file/count inventory는 위 표와 collect 결과를 source of truth로 삼고, 상세 계약은 기능별 핵심 회귀를 대표하는 케이스 중심으로 정리한다.

## Auto Scheduler

### AS-01 거래일 자동 실행 성공
- 테스트 ID: `AS-01`
- 기능/보호 계약: 거래일로 판정된 시각의 auto tick은 대상 길드에 대해 runner를 정확히 1회 실행하고, 성공 시 `last_auto_runs`를 오늘 날짜로 기록해야 한다.
- 원본 테스트 함수명: `tests/integration/test_auto_scheduler_logic.py::test_scheduler_runs_when_trading_day`
- 사전 상태: `guilds.1.auto_screenshot_enabled=true`, `commands.kheatmap.daily_posts_by_guild={}`, `commands.kheatmap.last_images={}`, 기존 `last_auto_runs.kheatmap` 없음.
- 입력/트리거: `2026-02-13 15:35 KST`에 `_jobs_for_now()`가 `kheatmap` 작업과 거래일 판정 `(True, None)`을 반환한다.
- mock/stub 전제: `execute_heatmap_for_guild()`는 `(True, "ok")`, `load_state()`는 메모리 state를 반환하고 `save_state()`는 정상 저장된 것으로 간주한다.
- 기대 동작: scheduler는 skip 경로 없이 `execute_heatmap_for_guild()`를 1회 호출한다.
- 기대 상태 저장 변화: `guilds.1.last_auto_runs.kheatmap="2026-02-13"`가 추가된다.
- 기대 status/detail/log: holiday 또는 calendar failure 로그가 남지 않는다.
- 회귀 방지 포인트: 거래일 auto run이 실제 게시를 건너뛰거나, 성공 후 실행 흔적을 남기지 않아 같은 날 중복 실행되는 문제를 막는다.

### AS-02 휴장일 자동 스킵
- 테스트 ID: `AS-02`
- 기능/보호 계약: 휴장일에는 runner를 호출하지 않고, skip 사유를 `last_auto_skips`와 로그에 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_auto_scheduler_logic.py::test_scheduler_skips_on_holiday`
- 사전 상태: `guilds.1.auto_screenshot_enabled=true`, `commands.kheatmap`는 비어 있지만 정상 구조를 가진다.
- 입력/트리거: `2026-02-13 15:35 KST` tick에서 거래일 판정 함수가 `(False, None)`을 반환한다.
- mock/stub 전제: runner stub은 호출되면 카운트를 올리지만, 정상 동작에서는 호출되지 않아야 한다. `caplog`는 scheduler logger를 수집한다.
- 기대 동작: scheduler는 길드 실행을 건너뛴다.
- 기대 상태 저장 변화: `guilds.1.last_auto_skips.kheatmap.date="2026-02-13"`가 기록된다.
- 기대 status/detail/log: 로그에 `reason=holiday`가 포함되고, skip reason도 `holiday`로 남는다.
- 회귀 방지 포인트: 휴장일에 실제 캡처/포럼 업서트가 실행되거나, 운영자가 왜 안 돌았는지 추적할 흔적이 사라지는 문제를 막는다.

### AS-03 거래일 판정 실패 시 보수적 스킵
- 테스트 ID: `AS-03`
- 기능/보호 계약: 거래일 여부를 판단할 수 없으면 무리하게 실행하지 말고 경고 로그와 skip reason을 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_auto_scheduler_logic.py::test_scheduler_skips_on_calendar_check_failure`
- 사전 상태: `guilds.1.auto_screenshot_enabled=true`, 대상 명령은 `usheatmap`, 기존 skip 기록은 없다.
- 입력/트리거: `2026-02-13 06:05 KST` tick에서 캘린더 판정이 `(None, "calendar unavailable")`을 반환한다.
- mock/stub 전제: `load_state()`와 `save_state()`는 정상 동작한다. `caplog`가 warning 레벨을 수집한다.
- 기대 동작: scheduler는 `usheatmap` 실행을 시도하지 않는다.
- 기대 상태 저장 변화: `guilds.1.last_auto_skips.usheatmap.reason`이 `calendar-check-failed:` 접두사로 저장된다.
- 기대 status/detail/log: 경고 로그에 `calendar-check-failed: calendar unavailable`가 남는다.
- 회귀 방지 포인트: 거래일 판정 장애 시 잘못된 시장 게시를 올리거나, 장애 원인을 숨긴 채 조용히 무시하는 문제를 막는다.

### AS-04 같은 날짜 재실행 방지
- 테스트 ID: `AS-04`
- 기능/보호 계약: 이미 같은 날짜의 `last_auto_runs`가 있으면 scheduler는 해당 길드를 다시 실행하지 않아야 한다.
- 원본 테스트 함수명: `tests/integration/test_auto_scheduler_logic.py::test_scheduler_respects_existing_last_auto_run`
- 사전 상태: `guilds.1.auto_screenshot_enabled=true`, `guilds.1.last_auto_runs.kheatmap="2026-02-13"`.
- 입력/트리거: 같은 날짜 `2026-02-13 15:35 KST` tick에 거래일 판정은 `(True, None)`이다.
- mock/stub 전제: runner stub은 호출 횟수를 기록한다.
- 기대 동작: scheduler는 runner를 0회 호출한다.
- 기대 상태 저장 변화: 기존 `last_auto_runs.kheatmap` 값이 유지된다.
- 기대 status/detail/log: 추가 실행 성공 흔적이나 skip 사유를 새로 덮어쓰지 않는다.
- 회귀 방지 포인트: 같은 날 auto tick이 중복되어 기존 thread를 불필요하게 다시 수정하거나, 새 게시를 만드는 문제를 막는다.

### AS-05 runner가 먼저 저장한 daily post state 보존
- 테스트 ID: `AS-05`
- 기능/보호 계약: auto runner가 같은 tick 안에서 먼저 저장한 `daily_posts_by_guild`를 scheduler의 후속 save가 덮어쓰면 안 된다.
- 원본 테스트 함수명: `tests/integration/test_auto_scheduler_logic.py::test_scheduler_preserves_runner_saved_daily_post_state`
- 사전 상태: 디스크를 흉내 낸 `disk["value"]`에 빈 `commands.kheatmap.daily_posts_by_guild`와 빈 `guilds.1`이 있다.
- 입력/트리거: 거래일 `2026-02-13 15:35 KST` tick에 `kheatmap` auto job이 실행된다.
- mock/stub 전제: `load_state()`와 `save_state()`는 deep copy 기반 on-disk 시뮬레이션으로 동작한다. runner stub은 내부에서 오늘자 `thread_id=22`, `starter_message_id=11`을 먼저 저장한 뒤 성공을 반환한다.
- 기대 동작: scheduler는 refresh 후 metadata만 보강하고, runner가 남긴 오늘자 forum state를 유지한다.
- 기대 상태 저장 변화: `commands.kheatmap.daily_posts_by_guild.1.2026-02-13`이 그대로 남고, 여기에 더해 `guilds.1.last_auto_runs.kheatmap="2026-02-13"`가 추가된다.
- 기대 status/detail/log: 별도 경고 없이 정상 흐름으로 끝난다.
- 회귀 방지 포인트: auto run 성공 직후 scheduler가 stale snapshot을 다시 저장해 thread/message mapping을 날려버리는 data-loss 버그를 막는다.

### AS-06 refresh read가 empty state면 `last_auto_runs` 저장 생략
- 테스트 ID: `AS-06`
- 기능/보호 계약: success 후 refresh read가 비정상적으로 empty state를 돌려주면 scheduler는 `last_auto_runs`를 다시 저장하지 않고 경고만 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_auto_scheduler_logic.py::test_scheduler_skips_last_auto_run_save_when_refresh_returns_empty`
- 사전 상태: `disk["value"]`에는 runner가 저장할 수 있는 정상 state 구조가 있다.
- 입력/트리거: 세 번째 `load_state()` 호출만 `{commands: {}, guilds: {}}`를 돌려주는 비정상 refresh read 상황을 만든다.
- mock/stub 전제: runner stub은 오늘자 `daily_posts_by_guild`를 먼저 저장한다. `save_state()` 호출 횟수도 함께 센다. `caplog`는 warning을 수집한다.
- 기대 동작: scheduler는 refresh read empty state를 감지하고 추가 save를 포기한다.
- 기대 상태 저장 변화: `commands.kheatmap.daily_posts_by_guild.1.2026-02-13`는 유지되고, `guilds.1.last_auto_runs`는 생기지 않는다. 총 save 횟수는 runner가 수행한 1회뿐이다.
- 기대 status/detail/log: 로그에 `state refresh returned empty` 경고가 남는다.
- 회귀 방지 포인트: transient read failure가 발생했을 때 near-empty state를 디스크에 다시 덮어써 runner 저장분까지 잃는 문제를 막는다.

## Forum Upsert / Runner

### FU-01 기존 thread/starter message 수정 경로
- 테스트 ID: `FU-01`
- 기능/보호 계약: 오늘자 thread가 이미 존재하면 새 thread를 만들지 않고 starter message와 thread title을 수정해야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_upsert_updates_existing`
- 사전 상태: `commands.kheatmap.daily_posts_by_guild.1.<today>`에 `thread_id=22`, `starter_message_id=11`이 저장돼 있고, 채널에는 같은 id의 thread와 starter message가 존재한다.
- 입력/트리거: `service.upsert_daily_post()`를 `title`, `body`, 이미지 1개와 함께 호출한다.
- mock/stub 전제: `FakeForumChannel.get_thread()`는 기존 thread를 반환하고, starter message는 `edit()` 가능하다.
- 기대 동작: 서비스는 create가 아니라 update 경로를 사용한다.
- 기대 상태 저장 변화: 오늘자 daily post record는 유지되고 thread id가 바뀌지 않는다.
- 기대 status/detail/log: 반환 action이 `updated`다.
- 회귀 방지 포인트: 같은 날짜 재실행 때 새 게시글이 늘어나거나, 제목은 바뀌지 않고 starter 본문만 바뀌는 불일치를 막는다.

### FU-02 기존 thread가 없으면 새로 생성
- 테스트 ID: `FU-02`
- 기능/보호 계약: state에 오늘자 record가 없거나 thread를 찾을 수 없으면 새 thread를 생성해야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_upsert_creates_when_missing`
- 사전 상태: `commands.kheatmap.daily_posts_by_guild`는 비어 있고, forum channel은 생성용 `created_thread(id=77, starter=88)`만 준비돼 있다.
- 입력/트리거: `service.upsert_daily_post()`를 호출한다.
- mock/stub 전제: `create_thread()`는 `thread.id=77`, `message.id=88`을 가진 새 thread를 반환한다.
- 기대 동작: 서비스는 create 경로를 타고 신규 thread 객체를 반환한다.
- 기대 상태 저장 변화: 오늘 날짜 record에 새 `thread_id`와 `starter_message_id`가 기록된다.
- 기대 status/detail/log: 반환 action이 `created`다.
- 회귀 방지 포인트: missing thread 상황에서 update를 시도하다 실패하거나, create 후 state를 안 남겨 같은 날 재실행마다 새 게시가 쌓이는 문제를 막는다.

### FU-03 starter + content messages 동기화
- 테스트 ID: `FU-03`
- 기능/보호 계약: `trendbriefing`처럼 follow-up content message를 쓰는 커맨드는 기존 message를 재사용하고 부족한 조각만 추가 생성해야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_upsert_syncs_content_messages`
- 사전 상태: 오늘자 `trendbriefing` record에 `thread_id=22`, `starter_message_id=11`, `content_message_ids=[30]`가 저장돼 있다. 실제 thread에는 starter와 기존 content message `30`이 있다.
- 입력/트리거: `content_texts=["domestic chunk", "global chunk"]`와 함께 `upsert_daily_post()`를 호출한다.
- mock/stub 전제: 기존 content message `30`은 edit 가능하고, thread는 새로운 content message를 send할 수 있다.
- 기대 동작: starter message는 수정되고, 기존 content message는 첫 번째 chunk로 수정되며, 두 번째 chunk용 새 message가 1개 추가 생성된다.
- 기대 상태 저장 변화: `content_message_ids` 길이가 2가 되고, 두 번째 id는 새로 생성된 message id를 가리킨다.
- 기대 status/detail/log: 기존 message 재사용 후 필요한 개수만 추가된다.
- 회귀 방지 포인트: trend/forum 본문이 매번 새 메시지를 누적 생성하거나, 기존 content message를 갱신하지 않아 본문이 엇갈리는 문제를 막는다.

### FU-04 남는 content message 삭제
- 테스트 ID: `FU-04`
- 기능/보호 계약: 새 본문 조각 수가 줄어들면 초과한 content message를 삭제하고 state에서도 제거해야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_upsert_deletes_extra_content_messages`
- 사전 상태: 오늘자 `trendbriefing` record는 `content_message_ids=[30, 31]`이고, 실제 thread에도 두 개의 extra message가 있다.
- 입력/트리거: `content_texts=["only one chunk"]`로 줄어든 상태로 `upsert_daily_post()`를 호출한다.
- mock/stub 전제: 기존 content messages는 `delete()` 가능하다.
- 기대 동작: 첫 번째 content message만 남기고 두 번째 message를 삭제한다.
- 기대 상태 저장 변화: `content_message_ids`가 `[30]`으로 줄어든다.
- 기대 status/detail/log: 삭제 대상 message는 `deleted=True` 상태가 된다.
- 회귀 방지 포인트: thread에 오래된 trend chunk가 남아 실제 본문과 state가 따로 노는 문제를 막는다.

### FU-05 stale missing content id 정리
- 테스트 ID: `FU-05`
- 기능/보호 계약: state에 남아 있지만 실제 Discord에는 이미 사라진 content message id는 자동으로 정리해야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_upsert_removes_stale_missing_content_message_ids`
- 사전 상태: `content_message_ids=[30, 31]`이 저장돼 있지만 실제 thread에는 `30`만 존재하고 `31` fetch는 `discord.NotFound`로 실패한다.
- 입력/트리거: `content_texts=["only one chunk"]`로 `upsert_daily_post()`를 호출한다.
- mock/stub 전제: `FakeThread.fetch_message()`는 없는 content id 조회 시 `FakeNotFound`를 던진다.
- 기대 동작: 존재하는 message만 남기고 stale id는 silently 정리한다.
- 기대 상태 저장 변화: `content_message_ids`가 `[30]`으로 정리된다.
- 기대 status/detail/log: missing content id 때문에 전체 upsert가 실패하지 않는다.
- 회귀 방지 포인트: 삭제된 follow-up message id가 state에 계속 남아 이후 업데이트마다 예외를 유발하는 drift를 막는다.

### FU-06 follow-up content 전송 실패 시에도 thread 기본 state 선기록
- 테스트 ID: `FU-06`
- 기능/보호 계약: 신규 thread 생성 후 follow-up content message 일부가 실패해도, 최소한 생성된 thread/starter/message state는 남겨 재시도 기반을 만들어야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_upsert_persists_thread_state_when_followup_content_fails`
- 사전 상태: 오늘자 `trendbriefing` record가 없다. 새로 만들어질 thread는 두 번째 `send()`에서 실패하도록 설정돼 있다.
- 입력/트리거: `content_texts=["domestic chunk", "global chunk"]`로 신규 upsert를 수행한다.
- mock/stub 전제: `create_thread()`는 `thread_id=77`, `starter_message_id=88`을 가진 새 thread를 만들고, 첫 번째 follow-up send는 성공하지만 두 번째 send는 `RuntimeError("send failed")`를 던진다.
- 기대 동작: 함수 자체는 예외를 다시 올리지만, 실패 전까지 확보한 state는 저장돼 있어야 한다.
- 기대 상태 저장 변화: 오늘자 record에 `thread_id=77`, `starter_message_id=88`, `content_message_ids=[89]`가 남는다.
- 기대 status/detail/log: 호출자는 예외를 보지만, 다음 재시도는 새 thread를 또 만들지 않고 기존 thread를 이어서 복구할 수 있다.
- 회귀 방지 포인트: partial content failure 한 번 때문에 생성된 thread 존재를 state가 잃어버려, 다음 실행마다 중복 thread를 만드는 문제를 막는다.

### FU-07 모든 캡처 실패 시 runner는 업서트하지 않고 사용자에게 실패를 알림
- 테스트 ID: `FU-07`
- 기능/보호 계약: heatmap capture가 전부 실패하면 forum upsert를 시도하지 않고 follow-up 메시지로 실패를 알려야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_runner_includes_partial_failure_in_body`
- 사전 상태: `kheatmap` state 구조는 존재하고, interaction은 defer/followup을 기록할 수 있다.
- 입력/트리거: runner가 `targets={"kospi": "x"}`로 실행되지만 `get_or_capture_images()`가 `image_paths=[]`, `failed=["kospi: timed out while rendering"]`를 반환한다.
- mock/stub 전제: `upsert_daily_post()` stub은 body를 캡처하도록 준비돼 있지만 정상 경로에서는 호출되면 안 된다.
- 기대 동작: runner는 forum upsert를 건너뛰고 interaction follow-up에 실패 안내를 보낸다.
- 기대 상태 저장 변화: daily post state는 새로 생기지 않는다.
- 기대 status/detail/log: 사용자 메시지에 `업데이트하지 못했습니다`가 포함된다.
- 회귀 방지 포인트: 캡처 결과가 0장인데도 빈 게시글을 올리거나, 사용자는 성공처럼 보이는데 실제론 아무 것도 안 올라간 상태를 막는다.

### FU-08 일부 캡처 실패가 있어도 남은 결과로 업서트
- 테스트 ID: `FU-08`
- 기능/보호 계약: 최소 1개 이미지가 성공했으면 runner는 실패 목록을 본문에 포함한 채 forum upsert를 계속 수행해야 한다.
- 원본 테스트 함수명: `tests/integration/test_forum_upsert_flow.py::test_runner_upserts_with_partial_failure`
- 사전 상태: interaction과 빈 `kheatmap` state가 준비돼 있다.
- 입력/트리거: `targets={"kospi": "x", "kosdaq": "y"}` 실행에서 `get_or_capture_images()`가 성공 이미지 1장과 실패 목록 `["kosdaq: timed out while rendering"]`를 반환한다.
- mock/stub 전제: `upsert_daily_post()`는 전달된 `body_text`를 캡처하고 성공으로 응답한다.
- 기대 동작: runner는 upsert를 호출하고, body에 `Failed:` 섹션과 실패 사유를 함께 넣는다.
- 기대 상태 저장 변화: 업서트 성공 경로를 탈 수 있는 입력이므로 thread state 저장이 허용된다.
- 기대 status/detail/log: 사용자 follow-up에는 `포스트 수정 완료`가 포함된다.
- 회귀 방지 포인트: 일부 마켓 렌더 실패가 전체 게시를 불필요하게 막거나, partial failure 정보가 본문에서 사라져 운영자가 결함을 놓치는 문제를 막는다.

## News Briefing Core

### NB-01 provider 예외는 즉시 failed로 기록
- 테스트 ID: `NB-01`
- 기능/보호 계약: 뉴스 provider 자체가 예외를 던지면 scheduler는 조용히 skip하지 말고 `news_briefing=failed`를 기록해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_records_provider_failure`
- 사전 상태: `guilds.1.forum_channel_id=123`, `system.job_last_runs`는 비어 있다.
- 입력/트리거: `_run_news_job()` 실행 시 `news_provider.fetch()`가 `RuntimeError("boom")`을 던진다.
- mock/stub 전제: state 저장은 메모리 no-op이다.
- 기대 동작: scheduler는 provider failure를 run result에 반영한다.
- 기대 상태 저장 변화: `system.job_last_runs.news_briefing.status="failed"`가 생긴다.
- 기대 status/detail/log: 실패 상세는 provider failure 성격을 반영해야 한다.
- 회귀 방지 포인트: 외부 뉴스 공급 장애가 `skipped`처럼 보이거나 건강한 상태로 오해되는 문제를 막는다.

### NB-02 타깃 포럼이 하나도 없으면 fetch 자체를 건너뜀
- 테스트 ID: `NB-02`
- 기능/보호 계약: 게시 대상 포럼이 없으면 provider 호출을 시작하지 말고 `no-target-forums`로 스킵해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_skips_when_no_target_forum`
- 사전 상태: `guilds.1`에는 forum 설정이 없고, 전역 `NEWS_TARGET_FORUM_ID`도 `None`이다.
- 입력/트리거: `_run_news_job()`를 정상 시각에 실행한다.
- mock/stub 전제: provider stub은 호출 횟수만 센다.
- 기대 동작: provider `fetch()`는 0회 호출된다.
- 기대 상태 저장 변화: `system.job_last_runs.news_briefing.status="skipped"`가 저장된다.
- 기대 status/detail/log: detail에 `no-target-forums`가 포함된다.
- 회귀 방지 포인트: 포럼 설정이 빠진 길드 때문에 외부 API 호출만 낭비하거나, 실패 원인이 게시 대상 부재인지 공급자 장애인지 구분이 안 되는 문제를 막는다.

### NB-03 다른 길드 소속 fallback forum 차단
- 테스트 ID: `NB-03`
- 기능/보호 계약: 전역 fallback forum이 현재 길드 소속이 아니면 해당 길드는 게시 대상으로 쓰면 안 된다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_skips_global_fallback_forum_from_other_guild`
- 사전 상태: 길드 `1`은 개별 forum 설정이 없고, 전역 `NEWS_TARGET_FORUM_ID=999`만 있다.
- 입력/트리거: `fetch_channel(999)`가 `guild_id=2`인 forum channel을 반환한다.
- mock/stub 전제: provider fetch는 호출 횟수를 기록한다.
- 기대 동작: scheduler는 cross-guild fallback을 invalid target으로 간주하고 fetch를 시작하지 않는다.
- 기대 상태 저장 변화: `news_briefing`과 `trend_briefing` 모두 job result가 남는다.
- 기대 status/detail/log: `news_briefing.status="skipped"`, detail에 `missing_forum=1`; `trend_briefing.status="skipped"`가 남는다.
- 회귀 방지 포인트: 한 길드의 전역 fallback forum이 다른 길드 채널로 새어 뉴스/트렌드가 잘못 게시되는 보안성 문제를 막는다.

### NB-04 forum resolution API 오류는 failed로 표면화
- 테스트 ID: `NB-04`
- 기능/보호 계약: Discord forum channel 조회 중 API 오류가 나면 이를 `missing_forum`으로 숨기지 말고 실패로 드러내야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_fails_when_forum_resolution_api_errors`
- 사전 상태: 길드 `1`은 전역 fallback `NEWS_TARGET_FORUM_ID=999`를 사용하려고 한다.
- 입력/트리거: `fetch_channel(999)`가 `RuntimeError("discord api down")`을 던진다.
- mock/stub 전제: provider fetch는 호출되면 안 된다.
- 기대 동작: scheduler는 forum resolution 단계에서 바로 failed 처리한다.
- 기대 상태 저장 변화: `news_briefing`과 `trend_briefing`의 failed 결과가 `system.job_last_runs`에 기록된다.
- 기대 status/detail/log: `news_briefing.detail == "forum-resolution-failed count=1 missing_forum=0"`.
- 회귀 방지 포인트: 실제 Discord API 장애를 설정 누락처럼 오진해 운영자가 잘못 대응하는 문제를 막는다.

### NB-05 휴장일이면 forum resolution 오류보다 holiday가 우선
- 테스트 ID: `NB-05`
- 기능/보호 계약: 거래일 제한이 켜진 뉴스 job은 휴장일이면 포럼 조회 실패보다 먼저 `holiday`로 스킵해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_skips_holiday_before_forum_resolution_errors`
- 사전 상태: `NEWS_BRIEFING_TRADING_DAYS_ONLY=true`, 길드 `1`은 forum id `999`를 갖고 있지만 Discord 조회는 실패할 수 있다.
- 입력/트리거: `safe_check_krx_trading_day()`가 `(False, None)`을 반환하는 휴장일 `2026-02-14 07:30 KST`.
- mock/stub 전제: `FailingFetchForumClient`는 channel 조회 시 예외를 던지지만 정상 경로에서는 호출되면 안 된다.
- 기대 동작: scheduler는 holiday 판단 후 바로 종료한다.
- 기대 상태 저장 변화: `news_briefing`과 `trend_briefing`에 skipped run이 저장된다.
- 기대 status/detail/log: `news_briefing.status="skipped"`, `detail="holiday"`.
- 회귀 방지 포인트: 휴장일 스킵 의미가 Discord 장애로 덮여 운영 힌트가 왜곡되는 문제를 막는다.

### NB-06 한 길드 forum resolution 실패가 있어도 다른 길드는 계속 처리
- 테스트 ID: `NB-06`
- 기능/보호 계약: 여러 길드 중 일부의 forum resolution만 실패하면 나머지 길드는 계속 게시하고, 전체 run은 mixed failure를 truthfully 기록해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_continues_after_one_forum_resolution_api_error`
- 사전 상태: 길드 `1`은 `forum_channel_id=123`, 길드 `2`는 `forum_channel_id=999`다.
- 입력/트리거: 길드 `1`의 forum lookup은 성공하고 길드 `2`의 lookup만 `discord api down`으로 실패한다. provider는 국내/해외 기사와 trend report를 모두 반환한다.
- mock/stub 전제: `upsert_daily_post()`는 성공으로 응답한다.
- 기대 동작: 길드 `1`은 뉴스/트렌드 게시를 완료하고, 길드 `2`만 실패 집계된다.
- 기대 상태 저장 변화: `guilds.1.last_auto_runs.newsbriefing="2026-02-13"`, `guilds.1.last_auto_runs.trendbriefing="2026-02-13"`가 기록되고 길드 `2`에는 `last_auto_runs`가 생기지 않는다.
- 기대 status/detail/log: `news_briefing.status="failed"`와 `trend_briefing.status="failed"`이며 detail에 `posted=1 failed=1`과 `forum_resolution_failures=1`이 함께 들어간다.
- 회귀 방지 포인트: 일부 길드의 Discord 장애 때문에 모든 길드가 중단되거나, 반대로 일부 실패가 `ok`로 숨는 문제를 막는다.

### NB-07 posting 실패 후 같은 아이템으로 재시도 가능해야 함
- 테스트 ID: `NB-07`
- 기능/보호 계약: 뉴스 게시가 실패해도 provider 결과를 영구 dedup 처리해 버리면 안 되며, 같은 날짜 재실행에서 동일 아이템을 다시 게시할 수 있어야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_retries_same_items_after_post_failure`
- 사전 상태: 길드 `1`은 forum 설정이 있고, provider는 동일 기사 2건을 중복 반환한다.
- 입력/트리거: 첫 번째 실행에서는 `upsert_daily_post()`가 `discord unavailable` 예외를 던지고, 두 번째 실행에서는 정상 성공한다.
- mock/stub 전제: 성공 시 stub은 `body_text`를 캡처한다.
- 기대 동작: 첫 번째 실행 후 `news_briefing=failed`지만 `last_auto_runs.newsbriefing`는 기록되지 않는다. 두 번째 실행에서는 같은 기사 제목이 본문에 1회만 포함된 채 재게시된다.
- 기대 상태 저장 변화: 재시도 성공 후에만 `guilds.1.last_auto_runs.newsbriefing="2026-02-13"`가 생긴다.
- 기대 status/detail/log: 첫 실행은 failed, 두 번째 실행은 `news_briefing.status="ok"`. 글로벌 기사 부재 시 body에는 `(데이터 없음)` placeholder가 포함된다.
- 회귀 방지 포인트: 첫 실패 후 재시도가 비어 버리거나, dedup 때문에 같은 날짜 재게시가 불가능해지는 문제를 막는다.

### NB-08 나중 tick의 missing forum이 기존 ok를 덮어쓰면 안 됨
- 테스트 ID: `NB-08`
- 기능/보호 계약: 같은 날짜에 이미 성공한 길드가 있으면, 이후 tick에서 다른 길드가 `missing forum`이어도 기존 `ok` 상태를 `skipped`로 덮어쓰면 안 된다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_keeps_ok_status_when_later_tick_has_only_missing_forums`
- 사전 상태: 길드 `1`은 forum 설정이 있고 길드 `2`는 없다.
- 입력/트리거: 같은 `2026-02-13 07:30 KST` news job을 두 번 연속 실행한다.
- mock/stub 전제: provider는 국내 기사 1건을 반환하고 `upsert_daily_post()`는 성공한다.
- 기대 동작: 첫 실행에서 길드 `1` 성공, 두 번째 실행도 기존 성공 상태를 유지한다.
- 기대 상태 저장 변화: 첫 실행의 성공 흔적이 그대로 유지된다.
- 기대 status/detail/log: 첫 번째와 두 번째 모두 `news_briefing.status="ok"`이며, 두 번째 detail에 `no-target-forums`가 새로 들어가지 않는다.
- 회귀 방지 포인트: 이미 성공한 아침 브리핑이 후속 tick 하나로 `skipped`처럼 보이는 false negative를 막는다.

### NB-09 region별 게시 수 제한 적용
- 테스트 ID: `NB-09`
- 기능/보호 계약: 지역별 뉴스 상한은 `NAVER_NEWS_LIMIT_PER_REGION`을 따르며, 국내/해외 본문도 서로 섞이지 않아야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_uses_configured_limit_per_region`
- 사전 상태: 길드 `1`은 forum 설정이 있고, provider는 국내 25건과 해외 23건을 반환한다.
- 입력/트리거: `NAVER_NEWS_LIMIT_PER_REGION=20`으로 `_run_news_job()`를 실행한다.
- mock/stub 전제: `upsert_daily_post()`는 `command_key`별 body를 캡처한다.
- 기대 동작: 국내/해외 각각 최대 20건까지만 사용해 별도 thread 본문을 만든다.
- 기대 상태 저장 변화: `news_briefing` run result는 성공으로 기록된다.
- 기대 status/detail/log: detail에 `domestic=20 global=20`이 포함된다. 국내 body에는 `[국내]`만, 해외 body에는 `[해외]`만 들어간다.
- 회귀 방지 포인트: provider가 많은 기사를 반환할 때 Discord 길이 제한 이전에 지역 상한이 깨지거나, 국내/해외 레이블이 섞이는 문제를 막는다.

### NB-10 같은 기사 cross-region 중복 제거
- 테스트 ID: `NB-10`
- 기능/보호 계약: 같은 기사 링크/제목이 국내와 해외 후보에 동시에 있으면 최종 게시 본문에는 한 번만 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_dedups_same_story_across_regions`
- 사전 상태: 길드 `1`은 forum 설정이 있다.
- 입력/트리거: provider가 동일한 제목/URL의 기사를 `domestic`과 `global` 각각 1건씩 반환한다.
- mock/stub 전제: `upsert_daily_post()`는 지역별 body를 캡처한다.
- 기대 동작: 최종 domestic/global body 합본에서 같은 제목이 1회만 나타난다.
- 기대 상태 저장 변화: 정상 성공 run이 저장된다.
- 기대 status/detail/log: dedup 이후에도 게시 성공 status는 유지된다.
- 회귀 방지 포인트: 같은 헤드라인이 국내/해외 thread 양쪽에 반복 노출되어 브리핑 품질이 떨어지는 문제를 막는다.

### NB-11 국내/해외 뉴스 thread 분리 게시
- 테스트 ID: `NB-11`
- 기능/보호 계약: 뉴스 브리핑은 국내/해외를 하나의 starter message에 합치지 않고 서로 다른 `command_key`와 제목으로 분리 게시해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_posts_domestic_and_global_threads_separately`
- 사전 상태: 길드 `1`은 forum 설정이 있고, provider는 국내 기사 1건과 해외 기사 1건을 반환한다.
- 입력/트리거: `_run_news_job()`를 실행한다.
- mock/stub 전제: `upsert_daily_post()`는 호출 순서와 제목/본문을 기록한다.
- 기대 동작: 호출 순서는 `newsbriefing-domestic`, `newsbriefing-global`이며 두 thread는 별도 제목을 갖는다.
- 기대 상태 저장 변화: 두 daily post key가 각자 독립적으로 관리될 수 있는 호출이 발생한다.
- 기대 status/detail/log: 국내 제목은 `[2026-02-13 국내 경제 뉴스 브리핑]`, 해외 제목은 `[2026-02-13 해외 경제 뉴스 브리핑]`이다.
- 회귀 방지 포인트: 국내/해외 본문을 한 thread에 억지로 합쳐 길이와 가독성을 망치거나, region별 상태 관리가 섞이는 문제를 막는다.

### NB-12 일부 길드 게시 실패는 failed로 정직하게 남겨야 함
- 테스트 ID: `NB-12`
- 기능/보호 계약: 여러 길드 중 한 곳이라도 뉴스 thread 게시가 실패하면 전체 `news_briefing` run status는 `failed`여야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_marks_failed_when_any_guild_post_fails`
- 사전 상태: 길드 `1`, `2` 모두 forum 설정이 있고 provider는 국내/해외 기사 1건씩 반환한다.
- 입력/트리거: `guild_id == 2`일 때만 `upsert_daily_post()`가 `forum write failed`를 던진다.
- mock/stub 전제: 길드 `1` 게시만 성공한다.
- 기대 동작: 길드 `1`은 성공 처리되지만 전체 뉴스 run은 mixed failure로 마감된다.
- 기대 상태 저장 변화: `guilds.1.last_auto_runs.newsbriefing="2026-02-13"`만 생기고 길드 `2`에는 `last_auto_runs`가 없다.
- 기대 status/detail/log: `news_briefing.status="failed"`, detail에 `posted=1 failed=1`. 같은 조건에서 `trend_briefing.status="skipped"`다.
- 회귀 방지 포인트: 일부 길드 delivery failure가 `ok`로 숨겨져 운영자가 실패 길드를 놓치는 문제를 막는다.

## Trend Briefing

### TR-01 trend thread는 starter + 2개 content message 구조로 게시
- 테스트 ID: `TR-01`
- 기능/보호 계약: trend briefing은 뉴스 thread와 분리된 별도 `trendbriefing` thread를 만들고, 국내/해외 섹션을 `content_texts` 두 조각으로 전달해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_posts_trendbriefing_with_content_messages`
- 사전 상태: 길드 `1`은 forum 설정이 있고, provider는 국내/해외 뉴스 1건씩과 각 region 3개 theme를 담은 `TrendThemeReport`를 반환한다.
- 입력/트리거: `_run_news_job()`를 실행한다.
- mock/stub 전제: `upsert_daily_post()`는 모든 호출 인자를 `calls`에 저장한다.
- 기대 동작: 호출 순서는 `newsbriefing-domestic`, `newsbriefing-global`, `trendbriefing`이다.
- 기대 상태 저장 변화: `trend_briefing` run이 성공으로 기록된다.
- 기대 status/detail/log: trend thread 제목은 `[2026-02-13 트렌드 테마 뉴스]`, starter body에는 `국내 테마 3개 | 해외 테마 3개`, `content_texts` 길이는 2이고 각 요소는 `[국내 트렌드 테마]`, `[해외 트렌드 테마]`로 시작한다.
- 회귀 방지 포인트: trend 요약이 뉴스 본문에 섞이거나, content message 분할 계약이 깨져 forum upsert 계층과 맞지 않게 되는 문제를 막는다.

### TR-02 일부 길드 trend 게시 실패는 trend만 failed
- 테스트 ID: `TR-02`
- 기능/보호 계약: trend thread만 일부 길드에서 실패하면 `news_briefing`은 `ok`를 유지하되 `trend_briefing`만 `failed`가 되어야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_marks_trend_failed_when_any_guild_trend_post_fails`
- 사전 상태: 길드 `1`, `2` 모두 forum 설정이 있고 provider는 뉴스와 trend report를 모두 반환한다.
- 입력/트리거: `command_key=="trendbriefing"`이면서 `guild_id==2`인 경우만 `upsert_daily_post()`가 `trend write failed`를 던진다.
- mock/stub 전제: 뉴스 thread와 길드 `1`의 trend thread는 성공한다.
- 기대 동작: 뉴스 브리핑 성공과 trend 실패가 분리 기록된다.
- 기대 상태 저장 변화: `guilds.1.last_auto_runs.trendbriefing="2026-02-13"`만 생기고 길드 `2`의 `last_auto_runs.trendbriefing`는 생기지 않는다.
- 기대 status/detail/log: `news_briefing.status="ok"`, `trend_briefing.status="failed"`, detail에 `posted=1 failed=1`.
- 회귀 방지 포인트: trend partial failure가 전체 뉴스 run을 불필요하게 실패로 만들거나, 반대로 trend 실패가 `ok`로 숨는 문제를 막는다.

### TR-03 양 지역 모두 minimum 미달이면 thread 자체를 만들지 않음
- 테스트 ID: `TR-03`
- 기능/보호 계약: 국내와 해외 테마 수가 모두 minimum 미만이면 trend thread 생성은 생략하고 skip 흔적만 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_skips_trendbriefing_when_both_regions_are_below_minimum`
- 사전 상태: 길드 `1`은 forum 설정이 있고, trend report는 국내 2개·해외 1개 theme만 포함한다.
- 입력/트리거: `_run_news_job()`를 실행한다.
- mock/stub 전제: `upsert_daily_post()`는 호출 인자를 기록한다.
- 기대 동작: 뉴스 thread 2개만 게시하고 `trendbriefing` 호출은 없다.
- 기대 상태 저장 변화: `guilds.1.last_auto_skips.trendbriefing.date="2026-02-13"`가 기록된다.
- 기대 status/detail/log: `trend_briefing.status="skipped"`.
- 회귀 방지 포인트: 의미 있는 theme가 부족한 날에도 빈 trend thread를 억지로 만들어 운영 소음을 늘리는 문제를 막는다.

### TR-04 한 지역만 minimum 미달이면 placeholder로 보완
- 테스트 ID: `TR-04`
- 기능/보호 계약: 한 지역만 minimum 미달이면 trend thread는 유지하되 부족한 지역은 placeholder 문구로 채워야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_news_job_uses_placeholder_for_region_below_minimum_when_other_region_qualifies`
- 사전 상태: 길드 `1`은 forum 설정이 있고, trend report는 국내 2개·해외 3개 theme를 반환한다.
- 입력/트리거: `_run_news_job()`를 실행한다.
- mock/stub 전제: `upsert_daily_post()`는 trend call 인자를 기록한다.
- 기대 동작: trend thread는 생성되며 국내 섹션만 placeholder를 사용한다.
- 기대 상태 저장 변화: trend thread 게시 경로가 유지된다.
- 기대 status/detail/log: trend starter body에는 `국내 테마 0개 | 해외 테마 3개`가 포함되고, 첫 번째 `content_texts`는 정확히 `[국내 트렌드 테마]\n- (유의미한 테마 부족)`이어야 한다.
- 회귀 방지 포인트: 한 지역이 약하다고 전체 trend를 skip해 버리거나, 반대로 빈 섹션을 그대로 노출해 품질이 떨어지는 문제를 막는다.

## EOD Summary

### EO-01 비거래일 장마감 스킵
- 테스트 ID: `EO-01`
- 기능/보호 계약: 장마감 요약은 비거래일에 provider 호출 없이 `skipped`로 끝나야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_skips_non_trading_day`
- 사전 상태: 길드 `1`은 forum 설정이 있고 EOD job 실행 흔적은 없다.
- 입력/트리거: `2026-02-14 16:20 KST`에 `safe_check_krx_trading_day()`가 `(False, None)`을 반환한다.
- mock/stub 전제: state 저장은 no-op이다.
- 기대 동작: `_run_eod_job()`는 provider 호출 없이 종료한다.
- 기대 상태 저장 변화: `system.job_last_runs.eod_summary.status="skipped"`가 기록된다.
- 기대 status/detail/log: 비거래일 스킵 의미가 유지된다.
- 회귀 방지 포인트: 휴장일에 장마감 요약을 잘못 게시하거나, 거래일 판단이 깨져 불필요한 외부 호출을 하는 문제를 막는다.

### EO-02 모든 게시가 실패하면 failed
- 테스트 ID: `EO-02`
- 기능/보호 계약: EOD summary 본문 생성이 성공해도 forum posting이 전부 실패하면 결과는 `failed`여야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_marks_failed_when_all_posts_fail`
- 사전 상태: 길드 `1`은 forum 설정이 있고 provider는 정상 `EodSummary`를 반환한다.
- 입력/트리거: `upsert_daily_post()`가 항상 `forum write failed`를 던진다.
- mock/stub 전제: 거래일 판정은 `(True, None)`이다.
- 기대 동작: scheduler는 posting failure를 집계하고 성공으로 처리하지 않는다.
- 기대 상태 저장 변화: `system.job_last_runs.eod_summary.status="failed"`가 저장된다.
- 기대 status/detail/log: detail에 `posted=0`이 포함된다.
- 회귀 방지 포인트: 본문 생성 성공만으로 job 전체를 `ok`로 오판하는 문제를 막는다.

### EO-03 일부 길드 실패도 failed
- 테스트 ID: `EO-03`
- 기능/보호 계약: 여러 길드 중 하나라도 EOD posting에 실패하면 전체 run status는 `failed`여야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_marks_failed_when_any_guild_post_fails`
- 사전 상태: 길드 `1`, `2` 모두 forum 설정이 있고 provider는 정상 summary를 반환한다.
- 입력/트리거: `guild_id==2`에서만 `upsert_daily_post()`가 `forum write failed`를 던진다.
- mock/stub 전제: 거래일 판정은 성공이다.
- 기대 동작: 길드 `1`은 게시되지만 전체 EOD run은 mixed failure로 닫힌다.
- 기대 상태 저장 변화: `guilds.1.last_auto_runs.eodsummary="2026-02-13"`만 생기고 길드 `2`에는 `last_auto_runs`가 없다.
- 기대 status/detail/log: `eod_summary.status="failed"`, detail에 `posted=1 failed=1`.
- 회귀 방지 포인트: 일부 길드 포럼 write failure가 장마감 job 성공으로 숨는 문제를 막는다.

### EO-04 후속 tick의 missing forum이 기존 ok를 덮지 않음
- 테스트 ID: `EO-04`
- 기능/보호 계약: 같은 날짜에 이미 성공한 EOD 결과가 있으면, 이후 tick에서 다른 길드가 missing forum이어도 기존 `ok` 상태를 유지해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_keeps_ok_status_when_later_tick_has_only_missing_forums`
- 사전 상태: 길드 `1`은 forum 설정이 있고 길드 `2`는 없다.
- 입력/트리거: 같은 `2026-02-13 16:20 KST` EOD job을 두 번 실행한다.
- mock/stub 전제: provider summary와 posting은 모두 성공한다.
- 기대 동작: 두 번째 실행도 전체 status를 `ok`로 유지한다.
- 기대 상태 저장 변화: 첫 실행 성공 흔적이 그대로 남는다.
- 기대 status/detail/log: 두 번째 `detail`에 `no-target-forums`가 새로 들어가지 않는다.
- 회귀 방지 포인트: 이미 게시된 장마감 요약이 같은 분의 후속 tick 하나 때문에 `skipped`처럼 보이는 false negative를 막는다.

### EO-05 다른 길드 fallback forum 차단
- 테스트 ID: `EO-05`
- 기능/보호 계약: 전역 `EOD_TARGET_FORUM_ID`가 다른 길드의 forum이면 게시 대상이 아니며 provider summary 조회도 시작하면 안 된다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_skips_global_fallback_forum_from_other_guild`
- 사전 상태: 길드 `1`은 개별 forum 설정이 없고 `EOD_TARGET_FORUM_ID=999`만 있다.
- 입력/트리거: `fetch_channel(999)`가 `guild_id=2`인 forum을 반환한다.
- mock/stub 전제: provider는 호출 횟수를 센다.
- 기대 동작: summary provider는 0회 호출된다.
- 기대 상태 저장 변화: `system.job_last_runs.eod_summary`가 남는다.
- 기대 status/detail/log: `status="skipped"`, detail에 `missing_forum=1`.
- 회귀 방지 포인트: 장마감 요약이 다른 길드 채널로 새거나, 잘못된 fallback 때문에 외부 provider 호출만 낭비하는 문제를 막는다.

### EO-06 forum resolution API 오류는 failed
- 테스트 ID: `EO-06`
- 기능/보호 계약: EOD forum resolution 단계의 Discord API 오류는 설정 누락으로 숨기지 말고 `failed`로 기록해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_fails_when_forum_resolution_api_errors`
- 사전 상태: 길드 `1`은 전역 `EOD_TARGET_FORUM_ID=999`를 사용하려고 한다.
- 입력/트리거: `fetch_channel(999)`가 `RuntimeError("discord api down")`을 던진다.
- mock/stub 전제: 거래일 판정은 성공, provider는 호출되면 안 된다.
- 기대 동작: forum resolution 단계에서 run이 failed 처리된다.
- 기대 상태 저장 변화: `eod_summary.status="failed"`가 저장된다.
- 기대 status/detail/log: `detail == "forum-resolution-failed count=1 missing_forum=0"`.
- 회귀 방지 포인트: Discord API 장애를 `missing forum`처럼 눙쳐 운영 진단을 잘못 유도하는 문제를 막는다.

### EO-07 휴장일 우선 의미 보존
- 테스트 ID: `EO-07`
- 기능/보호 계약: 비거래일이면 forum resolution 오류 가능성이 있어도 `holiday`로 먼저 스킵해야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_skips_holiday_before_forum_resolution_errors`
- 사전 상태: 길드 `1`은 `forum_channel_id=999`를 갖고 있지만 Discord 조회는 실패할 수 있다.
- 입력/트리거: `safe_check_krx_trading_day()`가 `(False, None)`을 반환하는 휴장일에 EOD job을 실행한다.
- mock/stub 전제: `FailingFetchForumClient`는 조회 시 예외를 던질 준비가 돼 있지만 정상 경로에서는 호출되지 않아야 한다.
- 기대 동작: scheduler는 holiday로 바로 종료한다.
- 기대 상태 저장 변화: `system.job_last_runs.eod_summary.status="skipped"`가 저장된다.
- 기대 status/detail/log: `detail == "holiday"`.
- 회귀 방지 포인트: 거래일 스킵 의미가 Discord 장애로 오염되는 문제를 막는다.

### EO-08 일부 길드 forum resolution 실패 후 다른 길드 계속 진행
- 테스트 ID: `EO-08`
- 기능/보호 계약: EOD job도 뉴스와 마찬가지로 일부 길드의 forum resolution만 실패하면 나머지 길드 게시를 계속하고 mixed failure를 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_intel_scheduler_logic.py::test_eod_job_continues_after_one_forum_resolution_api_error`
- 사전 상태: 길드 `1`은 `forum_channel_id=123`, 길드 `2`는 `forum_channel_id=999`다.
- 입력/트리거: 길드 `1`의 forum lookup은 성공하고 길드 `2`의 lookup만 `discord api down`으로 실패한다.
- mock/stub 전제: 거래일 판정은 성공, provider는 정상 summary를 반환하고 `upsert_daily_post()`도 성공한다.
- 기대 동작: 길드 `1`은 게시되고 길드 `2`만 failure로 집계된다.
- 기대 상태 저장 변화: `guilds.1.last_auto_runs.eodsummary="2026-02-13"`만 기록된다.
- 기대 status/detail/log: `eod_summary.status="failed"`, detail에 `posted=1 failed=1`과 `forum_resolution_failures=1`이 포함된다.
- 회귀 방지 포인트: 일부 길드 장애가 전체 job 중단이나 false `ok`로 왜곡되는 문제를 막는다.

## Watch Forum Flow

### WF-01 새 symbol thread 생성 후 같은 logical key 재사용
- 테스트 ID: `WF-01`
- 기능/보호 계약: 같은 `(guild, symbol)` key의 watch thread는 최초 1회 생성되고, 이후 starter update는 기존 thread/starter를 재사용해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_upsert_watch_thread_creates_and_reuses_existing_thread`
- 사전 상태: guild `1`에 빈 watch thread registry와 watch forum `456`이 있다.
- 입력/트리거: 같은 symbol에 대해 `upsert_watch_thread()`를 두 번 호출한다.
- mock/stub 전제: fake forum/thread/message는 starter edit와 thread rename을 지원한다.
- 기대 동작: 첫 호출은 `created`, 두 번째 호출은 `updated`다.
- 기대 상태 저장 변화: `commands.watchpoll.symbol_threads_by_guild.1.KRX:005930.thread_id`는 생성된 thread ID를 유지한다.
- 기대 status/detail/log: 두 번째 호출 뒤 starter content는 최신 값으로 바뀐다.
- 회귀 방지 포인트: 같은 symbol마다 thread가 중복 생성되거나, 기존 starter 복구가 깨지는 문제를 막는다.

### WF-02 starter message가 사라졌으면 새 thread로 복구
- 테스트 ID: `WF-02`
- 기능/보호 계약: registry는 남아 있어도 starter message fetch가 실패하면 watch thread는 새로 recreate되어야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_upsert_watch_thread_recreates_when_starter_message_is_missing`
- 사전 상태: 기존 registry는 thread `2001` / starter `3001`을 가리키지만 starter fetch는 `NotFound`로 실패한다.
- 입력/트리거: 같은 symbol에 대해 `upsert_watch_thread()`를 다시 호출한다.
- mock/stub 전제: forum은 새 thread `2002`를 만들 수 있다.
- 기대 동작: 호출 결과는 `created`다.
- 기대 상태 저장 변화: registry thread ID가 `2002`로 교체된다.
- 기대 status/detail/log: 새 starter content는 최신 text로 기록된다.
- 회귀 방지 포인트: stale starter handle 때문에 update가 조용히 실패하거나 잘못된 state가 유지되는 문제를 막는다.

### WF-03 기존 thread가 다른 forum에 속하면 새 forum 아래로 재생성
- 테스트 ID: `WF-03`
- 기능/보호 계약: 저장된 thread가 현재 configured watch forum의 child가 아니면 재사용하지 않고 현재 forum 아래에서 다시 만들어야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_upsert_watch_thread_recreates_when_existing_thread_belongs_to_other_forum`
- 사전 상태: registry는 thread `2001`을 가리키지만 parent forum ID는 현재 route와 다르다.
- 입력/트리거: `upsert_watch_thread()`를 현재 forum ID로 호출한다.
- mock/stub 전제: current forum은 새 thread `2002`를 생성할 수 있다.
- 기대 동작: 결과는 `created`다.
- 기대 상태 저장 변화: registry가 새 forum 쪽 thread ID로 갱신된다.
- 기대 status/detail/log: 새 starter는 현재 요청 text를 사용한다.
- 회귀 방지 포인트: `/setwatchforum` 이후에도 옛 forum thread를 잘못 재사용하는 문제를 막는다.

### WF-04 create 금지 모드에서는 stale handle이어도 recreate하지 않음
- 테스트 ID: `WF-04`
- 기능/보호 계약: `allow_create=False`인 update-only 경로는 stored thread/starter handle이 stale이면 `None`으로 빠지고 새 thread를 만들지 않아야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_upsert_watch_thread_does_not_recreate_when_creation_disallowed`
- 사전 상태: inactive registry가 thread `2001`을 가리키지만 starter fetch는 실패한다.
- 입력/트리거: `allow_create=False`로 `upsert_watch_thread()`를 호출한다.
- mock/stub 전제: forum은 필요하면 새 thread `2002`를 만들 수 있지만, 이 케이스에서는 호출되면 안 된다.
- 기대 동작: 함수 결과는 `None`이다.
- 기대 상태 저장 변화: registry는 기존 thread ID `2001`을 유지한다.
- 기대 status/detail/log: forum `create_thread()` 호출 횟수는 0이다.
- 회귀 방지 포인트: `/watch remove` 같은 update-only 경로가 stale registry 때문에 새 inactive thread를 만드는 문제를 막는다.

### WF-05 `/setwatchforum`은 성공/무권한/타 guild forum을 구분
- 테스트 ID: `WF-05`
- 기능/보호 계약: watch forum 설정 명령은 authorized same-guild forum만 저장하고, 무권한 사용자와 foreign forum은 거절해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_setwatchforum_command_handles_success_unauthorized_and_foreign_forum`
- 사전 상태: 빈 guild state, global admin set `{10}`.
- 입력/트리거: authorized success, unauthorized user, foreign forum의 3개 입력을 순서대로 호출한다.
- mock/stub 전제: interaction response는 ephemral text를 수집한다.
- 기대 동작: 성공 케이스만 forum ID를 저장한다.
- 기대 상태 저장 변화: `guilds.1.watch_forum_channel_id=456`만 기록된다.
- 기대 status/detail/log: 사용자별 응답 문구가 success / 권한 없음 / 다른 서버 forum 거절로 구분된다.
- 회귀 방지 포인트: watch routing 설정 권한이 무너져 잘못된 guild forum이 저장되는 문제를 막는다.

### WF-06 `/watch add`는 watch forum route가 없으면 거절
- 테스트 ID: `WF-06`
- 기능/보호 계약: watch forum route가 없는 guild에서는 `/watch add`가 thread 생성 전에 명시적으로 실패해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_watch_add_rejects_when_watch_forum_is_missing`
- 사전 상태: guild `1` state에는 watch forum route가 없다.
- 입력/트리거: `/watch add 005930`.
- mock/stub 전제: state save는 no-op이다.
- 기대 동작: 명령은 실패 응답을 보낸다.
- 기대 상태 저장 변화: watchlist와 thread registry는 바뀌지 않는다.
- 기대 status/detail/log: 응답에는 `/setwatchforum` 설정 요청 안내가 포함된다.
- 회귀 방지 포인트: forum route 없이 watchlist만 먼저 저장되어 scheduler가 나중에 실패하는 문제를 막는다.

### WF-07 `/watch add`는 re-add 시 active placeholder를 강제로 다시 씀
- 테스트 ID: `WF-07`
- 기능/보호 계약: inactive historical thread를 `/watch add`로 복구할 때 starter는 이전 content를 재사용하지 않고 active placeholder로 덮어써야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_watch_add_uses_active_placeholder_when_upserting_thread`
- 사전 상태: guild `1`의 registry에는 inactive thread entry가 남아 있고 watchlist는 비어 있다.
- 입력/트리거: `/watch add 005930`.
- mock/stub 전제: `upsert_watch_thread()`는 호출 인자를 기록만 한다.
- 기대 동작: symbol은 watchlist에 다시 추가된다.
- 기대 상태 저장 변화: `guilds.1.watchlist=["KRX:005930"]`.
- 기대 status/detail/log: `starter_text` 인자로 active placeholder가 전달된다.
- 회귀 방지 포인트: re-add 후 첫 poll 전까지 stale starter가 그대로 노출되는 문제를 막는다.

### WF-08 `/watch add`는 같은 세션 재활성화 시 band checkpoint를 리셋
- 테스트 ID: `WF-08`
- 기능/보호 계약: same-session inactive symbol을 다시 add하면 old `highest_up_band/highest_down_band` checkpoint를 0으로 되돌려 early band alert를 fresh state로 다시 시작해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_watch_add_resets_same_session_band_checkpoints_for_reactivated_symbol`
- 사전 상태: guild `1`의 registry에는 inactive thread entry가 있고, `watch_session_alerts`에는 같은 session의 highest band와 intraday comment id가 남아 있다.
- 입력/트리거: regular session open 중 `/watch add 005930`.
- mock/stub 전제: `upsert_watch_thread()`는 성공으로 응답하고 현재 시각은 same-session 장중으로 고정한다.
- 기대 동작: symbol은 watchlist에 다시 추가되고 starter 복구 경로도 유지된다.
- 기대 상태 저장 변화: `highest_up_band`와 `highest_down_band`는 `0`으로 reset되지만, close cleanup용 `intraday_comment_ids`와 `close_comment_ids_by_session`은 유지된다.
- 기대 status/detail/log: reset은 inactive historical thread의 same-session reactivation일 때만 적용된다.
- 회귀 방지 포인트: remove 후 같은 세션 안에 다시 등록했을 때 stale highest band 때문에 초반 band comment가 누락되는 문제를 막는다.

### WF-09 `/watch remove`는 inactive placeholder update를 update-only로 시도
- 테스트 ID: `WF-09`
- 기능/보호 계약: tracked thread가 있는 경우 `/watch remove`는 registry status를 inactive로 바꾸고, 새 thread를 만들지 않는 모드로 inactive placeholder update를 시도해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_watch_remove_marks_thread_inactive_and_updates_placeholder`
- 사전 상태: guild `1` watchlist와 active thread registry entry가 존재한다.
- 입력/트리거: `/watch remove 005930`.
- mock/stub 전제: `upsert_watch_thread()`는 인자만 기록하고 성공으로 응답한다.
- 기대 동작: symbol은 watchlist에서 제거된다.
- 기대 상태 저장 변화: registry status는 `inactive`로 바뀐다.
- 기대 status/detail/log: `starter_text`는 inactive placeholder이고 `allow_create=False`가 전달된다.
- 회귀 방지 포인트: remove가 stale registry를 핑계로 새 inactive thread를 만들거나, starter를 옛 상태로 남기는 문제를 막는다.

### WF-10 `/watch remove`는 registry entry 자체가 없으면 아무 thread도 만들지 않음
- 테스트 ID: `WF-10`
- 기능/보호 계약: watchlist에 symbol이 있어도 tracked thread registry entry가 없으면 `/watch remove`는 state 정리만 하고 thread service를 호출하지 않아야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_watch_remove_does_not_create_thread_when_no_registry_entry_exists`
- 사전 상태: guild `1` watchlist에는 symbol이 있지만 thread registry map은 비어 있다.
- 입력/트리거: `/watch remove 005930`.
- mock/stub 전제: `upsert_watch_thread()`가 호출되면 symbol을 기록하게 만든다.
- 기대 동작: symbol은 watchlist에서 제거된다.
- 기대 상태 저장 변화: watchlist만 비워지고 thread registry에는 새 entry가 생기지 않는다.
- 기대 status/detail/log: thread service 호출 횟수는 0이다.
- 회귀 방지 포인트: pre-forum legacy state를 제거하는 것만으로 새 inactive forum thread가 생기는 문제를 막는다.

### WF-11 transient Discord fetch 오류는 duplicate thread recreate로 이어지지 않음
- 테스트 ID: `WF-11`
- 기능/보호 계약: 기존 thread/starter resolve 중 `Forbidden` 같은 transient Discord fetch 오류가 나면 `upsert_watch_thread()`는 새 thread를 만들지 말고 그대로 실패를 surface해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_forum_flow.py::test_upsert_watch_thread_does_not_recreate_on_transient_fetch_error`
- 사전 상태: registry는 thread `2001` / starter `3001`을 가리키고, 기존 thread는 현재 forum의 child다.
- 입력/트리거: 같은 symbol에 대해 `upsert_watch_thread()`를 다시 호출한다.
- mock/stub 전제: starter fetch는 `FakeForbidden`을 던지고, forum은 필요하면 새 thread `2002`를 만들 수 있다.
- 기대 동작: 함수는 transient fetch 오류를 그대로 raise한다.
- 기대 상태 저장 변화: registry thread ID는 `2001`을 유지한다.
- 기대 status/detail/log: forum `create_thread()` 호출 횟수는 0이다.
- 회귀 방지 포인트: 일시적인 Discord API/권한 오류가 symbol thread를 조용히 fork해 duplicate thread를 만드는 문제를 막는다.

## Watch Poll Forum Scheduler

### WP-01 장중 poll은 starter를 갱신하고 최고 신규 band comment 1건만 남김
- 테스트 ID: `WP-01`
- 기능/보호 계약: 장중 watch poll은 starter를 snapshot 기준으로 갱신하고, 같은 tick에서 최고 신규 band comment 1건만 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_updates_starter_and_posts_highest_new_band_comment`
- 사전 상태: guild `1`은 watch forum `456`과 active watchlist `["KRX:005930"]`를 가진다.
- 입력/트리거: 장중 snapshot이 `previous_close=100.0`, `current_price=107.1`로 반환된다.
- mock/stub 전제: provider는 warm-up을 지원하고 forum/thread fake는 starter edit와 comment send를 지원한다.
- 기대 동작: thread starter는 `전일 종가/현재가/변동률/마지막 갱신`을 포함하도록 갱신된다.
- 기대 상태 저장 변화: provider status와 `watch_poll` job status가 `ok`로 저장된다.
- 기대 status/detail/log: comment는 `+6% 이상 상승 : +7.10%` 한 건만 남는다.
- 회귀 방지 포인트: 장중 starter가 갱신되지 않거나 한 tick에서 여러 band comment가 flood되는 문제를 막는다.

### WP-02 같은 세션에서는 최고 band만 유지하고 양방향 ladder를 독립 추적
- 테스트 ID: `WP-02`
- 기능/보호 계약: 같은 세션에서는 이미 지난 band를 재발송하지 않고, 반대 방향 ladder는 별개로 추적해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_keeps_same_session_highest_band_and_supports_both_active`
- 사전 상태: 같은 guild/symbol에 대해 3개의 장중 snapshot이 순차적으로 들어온다.
- 입력/트리거: `+4.0%`, `+4.5%`, `-6.2%` 순서의 snapshot을 연속 poll한다.
- mock/stub 전제: provider는 iterator 기반 snapshot sequence를 반환한다.
- 기대 동작: comment는 첫 상승 band와 이후 반대 방향 하락 band만 남는다.
- 기대 상태 저장 변화: 같은 세션의 highest band state가 재발송 없이 누적된다.
- 기대 status/detail/log: starter에는 내부 `당일 alert status` 같은 개발용 문구가 드러나지 않는다.
- 회귀 방지 포인트: retrace나 same-session 재poll이 지난 band를 다시 보내는 문제를 막는다.

### WP-03 `session_close_price`가 생길 때까지 close finalization을 미룸
- 테스트 ID: `WP-03`
- 기능/보호 계약: off-hours poll은 `session_close_price`가 없으면 intraday comment를 지우지 않고 finalization을 보류해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_defers_close_finalization_until_session_close_price_is_available`
- 사전 상태: unfinalized session state와 intraday comments 2건이 존재한다.
- 입력/트리거: 첫 off-hours snapshot은 `session_close_price=None`, 두 번째는 `session_close_price=98.0`을 반환한다.
- mock/stub 전제: 같은 forum/thread를 두 번 재사용한다.
- 기대 동작: 첫 poll에서는 아무 comment도 지우지 않고, 둘째 poll에서만 intraday comment를 정리하고 close comment 1건을 남긴다.
- 기대 상태 저장 변화: `last_finalized_session_date`는 두 번째 poll 후에만 기록된다.
- 기대 status/detail/log: thread history의 `마감가 알림` comment는 1건이다.
- 회귀 방지 포인트: close price가 없는데도 session을 성급히 finalize해 close summary가 비거나 intraday history가 사라지는 문제를 막는다.

### WP-04 inactive symbol도 unfinalized session이 있으면 1회 finalization 후 중지
- 테스트 ID: `WP-04`
- 기능/보호 계약: watchlist에서 제거된 inactive symbol이라도 unfinalized session이 남아 있으면 off-hours poll에서 정확히 1회 finalization을 수행해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_finalizes_inactive_symbol_once_before_stopping`
- 사전 상태: watchlist는 비어 있지만 thread registry status는 `inactive`이고 intraday comment 1건이 남아 있다.
- 입력/트리거: off-hours snapshot이 `session_close_price=98.0`과 함께 들어온다.
- mock/stub 전제: provider는 항상 같은 close snapshot을 반환한다.
- 기대 동작: intraday comment는 삭제되고 session은 finalized 된다.
- 기대 상태 저장 변화: `last_finalized_session_date="2026-03-26"`가 기록된다.
- 기대 status/detail/log: 추가 poll 없이도 first eligible close poll에서 정리가 끝난다.
- 회귀 방지 포인트: remove 직후 남은 same-session 정리가 영원히 누락되거나, inactive symbol이 즉시 완전히 무시되는 문제를 막는다.

### WP-05 새 장 시작 전 prior session close를 먼저 마무리
- 테스트 ID: `WP-05`
- 기능/보호 계약: 이전 session이 unfinalized인 상태에서 더 늦은 `session_date`의 장중 snapshot이 오면, current session starter로 넘어가기 전에 prior session close finalization을 먼저 해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_finalizes_prior_session_before_rotating_to_new_open_session`
- 사전 상태: reference/session state는 `2026-03-26`, intraday comment 1건이 남아 있다.
- 입력/트리거: 다음 거래일 장중 snapshot이 `session_date="2026-03-27"`로 들어온다.
- mock/stub 전제: provider는 새 세션 snapshot 1개를 반환한다.
- 기대 동작: 이전 세션 close comment가 먼저 남고, 이후 reference/session state가 새 session으로 넘어간다.
- 기대 상태 저장 변화: `last_finalized_session_date="2026-03-26"`와 새 `active_session_date="2026-03-27"`가 함께 기록된다.
- 기대 status/detail/log: close comment는 1건, starter는 새 세션 `전일 종가`를 반영한다.
- 회귀 방지 포인트: carry-forward finalization이 빠져 전날 intraday comment가 다음날까지 남거나 새 세션 state reset이 잘못되는 문제를 막는다.

### WP-06 watch forum route가 하나도 없으면 poll을 skip
- 테스트 ID: `WP-06`
- 기능/보호 계약: watchlist는 있지만 eligible guild 중 watch forum route가 하나도 없으면 quote fetch 없이 `no-target-forums`로 skip해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_skips_when_only_missing_watch_forum_routes_exist`
- 사전 상태: guild `1`은 watchlist만 있고 `watch_forum_channel_id`는 없다.
- 입력/트리거: 장중 scheduler tick.
- mock/stub 전제: provider는 호출 횟수를 셀 수 있다.
- 기대 동작: provider snapshot fetch는 0회다.
- 기대 상태 저장 변화: `system.job_last_runs.watch_poll.status="skipped"`가 저장된다.
- 기대 status/detail/log: detail에는 `missing_forum_guilds=1`과 `no-target-forums`가 포함된다.
- 회귀 방지 포인트: route가 없는 길드에서도 무의미한 quote 조회를 계속하거나 misleading failure/ok를 남기는 문제를 막는다.

### WP-07 snapshot provider 예외는 failed와 provider status 실패로 기록
- 테스트 ID: `WP-07`
- 기능/보호 계약: `get_watch_snapshot()` 예외는 `watch_poll` failure와 provider status failure를 동시에 남겨야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_records_snapshot_provider_failure`
- 사전 상태: guild `1`은 watch forum과 active watchlist를 가진다.
- 입력/트리거: provider가 `MarketDataProviderError(\"quote provider down\")`을 던진다.
- mock/stub 전제: forum은 정상이고 오류에는 `provider_key=\"kis_quote\"`가 붙어 있다.
- 기대 동작: 해당 symbol의 thread update는 건너뛴다.
- 기대 상태 저장 변화: `system.provider_status.kis_quote.ok=False`, `message=\"quote provider down\"`가 저장된다.
- 기대 status/detail/log: `watch_poll.status=\"failed\"`, detail에 `snapshot_failures=1`이 포함된다.
- 회귀 방지 포인트: provider 장애가 thread/forum 문제처럼 오인되거나 run status가 `ok`로 남는 문제를 막는다.

### WP-08 warm-up은 guild별 중복 symbol을 합쳐 poll cycle당 1회만 호출
- 테스트 ID: `WP-08`
- 기능/보호 계약: 여러 guild가 같은 canonical symbol을 보더라도 `warm_watch_snapshots()`는 poll cycle당 unique symbol set으로 한 번만 호출되어야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_warms_unique_symbols_once`
- 사전 상태: 두 guild가 각각 다른 forum route를 가지지만 watchlist는 같은 `KRX:005930`을 가진다.
- 입력/트리거: 장중 scheduler tick 1회.
- mock/stub 전제: provider는 warm symbols와 개별 snapshot fetch symbol을 모두 기록한다.
- 기대 동작: warm-up은 `(\"KRX:005930\",)` 한 번만 호출된다.
- 기대 상태 저장 변화: 각 guild의 개별 snapshot fetch는 계속 수행된다.
- 기대 status/detail/log: snapshot fetch 호출은 symbol별이 아니라 guild-symbol 처리 수만큼 남는다.
- 회귀 방지 포인트: 같은 symbol을 guild 수만큼 warm-up 해 외부 API와 warm cache를 과도하게 소모하는 문제를 막는다.

### WP-09 인접하지 않은 더 늦은 snapshot만 있을 때 old session은 finalize하지 않음
- 테스트 ID: `WP-09`
- 기능/보호 계약: 여러 trading session을 건너뛴 더 늦은 snapshot만 있는 경우 `snapshot.previous_close`를 old session close로 오인해 finalize하면 안 된다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_keeps_non_adjacent_unfinalized_session_open`
- 사전 상태: reference/session state는 `2026-03-24`에 고정돼 있고 intraday comment 1건이 남아 있다.
- 입력/트리거: 장중 snapshot은 `session_date="2026-03-27"`, `previous_close=98.0`, `session_close_price=None`을 반환한다.
- mock/stub 전제: provider는 이 non-adjacent newer snapshot만 반환한다.
- 기대 동작: old session close finalization은 수행되지 않고 intraday comment도 그대로 남는다.
- 기대 상태 저장 변화: `last_finalized_session_date`와 current `watch_reference_snapshots`는 기존 old session 값 그대로 유지된다.
- 기대 status/detail/log: `watch_poll.status="failed"`이며 detail에 `comment_failures=1`이 포함된다.
- 회귀 방지 포인트: multi-session outage 뒤 복귀했을 때 잘못된 close price로 old session을 finalize하고, 이후 올바른 보정 기회를 영구히 잃는 문제를 막는다.

### WP-10 malformed symbol은 다른 watch symbol 처리를 중단시키지 않음
- 테스트 ID: `WP-10`
- 기능/보호 계약: persisted watchlist에 malformed/unsupported symbol이 섞여 있어도 scheduler는 해당 symbol만 `snapshot_failures`로 집계하고, 다른 정상 symbol은 계속 처리해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_invalid_symbol_does_not_abort_other_symbols`
- 사전 상태: guild `1`의 watchlist는 `BAD:123`, `KRX:005930`을 함께 포함하고 watch forum route는 정상이다.
- 입력/트리거: 장중 `watch_poll` 실행.
- mock/stub 전제: provider는 warm symbols와 개별 snapshot fetch symbol을 기록하고, 정상 symbol `KRX:005930`에 대해서만 snapshot을 반환한다.
- 기대 동작: malformed symbol은 provider fetch 전에 건너뛰고, 정상 symbol thread는 그대로 갱신된다.
- 기대 상태 저장 변화: valid symbol의 starter는 최신 snapshot으로 갱신된다.
- 기대 status/detail/log: `watch_poll.status="failed"`이며 detail에 `snapshot_failures=1`, `updated_threads=1`이 포함된다.
- 회귀 방지 포인트: persisted state의 bad symbol 하나 때문에 해당 cycle의 나머지 guild-symbol 처리까지 모두 누락되는 scheduler-wide outage를 막는다.

### WP-11 예상 밖 market session 계산 오류는 per-symbol failure로 숨기지 않음
- 테스트 ID: `WP-11`
- 기능/보호 계약: unsupported symbol guard는 예상된 malformed-symbol 경로만 격리하고, 정상 symbol에서 발생한 unexpected market-session 계산 오류는 그대로 re-raise해야 한다.
- 원본 테스트 함수명: `tests/integration/test_watch_poll_forum_scheduler.py::test_watch_poll_re_raises_unexpected_market_session_failure`
- 사전 상태: guild `1`은 watch forum과 active watchlist `["KRX:005930"]`를 가진다.
- 입력/트리거: `get_watch_market_session()`이 정상 symbol `KRX:005930`에 대해 `RuntimeError("calendar-broken")`을 던진다.
- mock/stub 전제: provider warm-up은 성공하고 Discord forum도 정상이다.
- 기대 동작: `_run_watch_poll()`은 예외를 그대로 re-raise한다.
- 기대 상태 저장 변화: 해당 tick을 `snapshot_failures`로 삼켜 저장하지 않는다.
- 기대 status/detail/log: caller는 `calendar-broken` 예외를 직접 본다.
- 회귀 방지 포인트: 실제 session/calendar 결함이 malformed-symbol noise에 묻혀 scheduler 진단이 어려워지는 문제를 막는다.

## 현재 누락된 고위험 케이스

### Missing-01 `usheatmap` auto scheduler success path state 보존
- 현재 테스트 없음
- 위험 이유: 현재 auto scheduler state 보존 회귀는 `kheatmap` 기준으로만 검증돼 있고, `usheatmap`의 뉴욕 거래일 기준 날짜 계산과 함께 같은 보존 계약이 깨질 가능성이 남아 있다.
- 추천 추가 위치: `tests/integration/test_auto_scheduler_logic.py`

### Missing-02 multi-guild auto screenshot mixed success/failure
- 현재 테스트 없음
- 위험 이유: auto screenshot은 길드별로 forum 설정, 게시 성공, 거래일 스킵이 섞일 수 있는데 현재는 단일 길드 중심 검증만 있다.
- 추천 추가 위치: `tests/integration/test_auto_scheduler_logic.py`

### Missing-03 stored thread/message fetch failure 후 recreate 경로
- 현재 테스트 없음
- 위험 이유: forum state에 오늘자 `thread_id`와 `starter_message_id`가 남아 있어도 Discord fetch가 실패하면 recreate/update 어느 경로를 타야 하는지 현재 통합 테스트가 직접 보장하지 않는다.
- 추천 추가 위치: `tests/integration/test_forum_upsert_flow.py`

### Missing-04 runner의 forum 권한/`Forbidden` 경로
- 현재 테스트 없음
- 위험 이유: capture는 성공했지만 Discord forum write 권한이 없을 때 사용자 메시지, state 보존, 재시도 가능성이 어떻게 남는지 현재 문서화된 통합 보장이 없다.
- 추천 추가 위치: `tests/integration/test_forum_upsert_flow.py`

### Missing-05 capture cache reuse + state write 상호작용
- 현재 테스트 없음
- 위험 이유: 캐시 hit 시 이미지 재사용과 today post state update가 같이 일어나는 경로는 state overwrite와 cache metadata drift를 만들기 쉽다.
- 추천 추가 위치: `tests/integration/test_forum_upsert_flow.py` 또는 `tests/integration/test_auto_scheduler_logic.py`

### Missing-06 news/eod/watch multi-guild mixed result detail 정합성
- 현재 테스트 없음
- 위험 이유: 현재는 각 기능별 대표 mixed failure 한두 가지를 보지만, 여러 길드에서 `success + missing target + post failure + forum resolution failure`가 동시에 섞인 detail 카운트 정합성은 직접 검증하지 않는다.
- 추천 추가 위치: `tests/integration/test_intel_scheduler_logic.py`

### Missing-07 live capture와 file size/render completion 동시 검증
- 현재 테스트 없음
- 위험 이유: 현재 live 테스트는 파일 존재와 최소 크기만 보며, 렌더 완료 조건이 실제로 충족됐는지까지는 간접 검증에 머문다.
- 추천 추가 위치: `tests/integration/test_capture_korea_live.py`, `tests/integration/test_capture_us_live.py`

### Missing-08 real state file I/O 기반 end-to-end command rerun
- 현재 테스트 없음
- 위험 이유: 실제 `state.json` 파일을 쓰고 다시 읽는 end-to-end rerun 시나리오가 없어서, 메모리 monkeypatch 환경에선 안 보이는 파일 I/O 경합과 날짜별 재실행 문제를 놓칠 수 있다.
- 추천 추가 위치: 새 통합 테스트 파일 또는 `tests/integration/test_forum_upsert_flow.py`
