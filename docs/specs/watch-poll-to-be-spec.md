# Watch Poll To-Be Specification

## 1. Scope
- 이 문서는 `watch_poll`의 목표 동작을 정의하는 To-Be 명세서다.
- 현재 구현 사실은 `watch-poll-functional-spec.md`와 `as-is-functional-spec.md`를 기준으로 본다.
- 이 문서는 구현 전 설계 고정안이며, 현재 runtime truth를 대체하지 않는다.

## 2. Fixed Decisions
- watch 대상은 계속 길드 공유 state로 유지한다.
- 개인별 알림/구독 state는 bot이 관리하지 않는다.
- 개인별 notification surface는 Discord thread follow 기능에 위임한다.
- watch route의 기본 출력 surface는 text channel이 아니라 forum thread다.
- 길드와 symbol 조합마다 persistent thread를 1개 유지한다.
- thread는 매일 새로 만들지 않는다.
- `watch_forum_channel_id`가 없으면 `/watch add`는 명시적으로 거절한다.
- 기준가는 `전일 종가(previous_close)`로 고정한다.
- internal watch scheduler는 current `Quote` 대신 richer한 `WatchSnapshot`을 사용한다.
- external quote adapter의 `price` 필드는 internal `WatchSnapshot.current_price`로 정규화된다.
- starter message는 poll마다 `기준가(전일 종가)`, `현재가`, `변동률`, `당일 alert status`, `당일 최고 도달 band`, `마지막 갱신 시각`을 갱신한다.
- `세션`은 symbol market의 regular-session trading date, 즉 market-local 기준의 `당일`을 뜻한다.
- intraday comment 알림 기준은 전일 종가 대비 `3% band ladder`다.
  - `+3%`, `+6%`, `+9%` ...
  - `-3%`, `-6%`, `-9%` ...
- 3% band는 상한 없이 계속 확장된다.
- 한 poll에서 여러 band를 한 번에 건너뛰어도 intraday comment는 최고 신규 band 기준 1건만 남긴다.
- 같은 세션 안에서는 한 번 도달한 방향/band 상태가 이후 threshold 안으로 복귀해도 active history로 유지된다.
- intraday starter edit와 band detection은 symbol market의 regular session이 열려 있을 때만 수행한다.
- regular session이 닫힌 뒤 off-hours poll은 intraday starter edit나 새 band comment를 만들지 않는다.
- off-hours poll은 아직 finalization되지 않은 마지막 세션이 있을 때만 close finalization을 시도한다.
- close finalization은 first eligible poll after close 기준으로 정확히 1회만 완료돼야 하며, restart 또는 delayed startup 뒤에도 idempotent해야 한다.
- intraday comment는 regular session close finalization 시 모두 삭제한다.
- regular session close 후에는 `날짜`, `전일 종가`, `마감가`, `최종 변동률`을 담은 `마감가 알림` comment 1건만 남긴다.
- `마감가`는 after-hours current price가 아니라 해당 `session_date`의 official regular-session close price다.
- `마감가 알림` comment는 영구 보존한다.

## 3. Goals
- 길드 안에서 종목별 watch 정보를 한 곳에 모아 공유한다.
- 사용자는 관심 종목 thread만 follow 해서 개인별 notification을 받는다.
- 가격 상태 확인은 starter message 1개로 빠르게 가능해야 한다.
- 의미 있는 intraday 변동은 댓글로 남겨 thread follower에게 전달된다.
- 기존 `첫 quote를 baseline으로 고정`하는 방식 대신 `전일 종가 기준`으로 더 일관된 intraday 변동률을 보여준다.
- intraday notification noise는 장마감 정리와 `마감가 알림` 영구 보존으로 관리한다.

## 4. Non-Goals
- bot-managed user subscription, mention, DM delivery
- 매 poll마다 새 댓글을 남기는 spam형 브리핑
- daily thread rotation
- 당일 시가를 기준가로 사용하는 정책
- 기존 `watch_alert_channel_id` text alert path의 병행 운영을 기본값으로 두는 것
- intraday comment history를 영구 보존하는 것

## 5. Target User Flow

### 5.1 Watch forum setup
- 운영자는 guild별로 `/setwatchforum` 같은 admin command를 사용해 watch forum route를 지정한다.
- watch forum route는 state에 저장되며 env는 bootstrap/default 역할만 가진다.

### 5.2 Add watch symbol
1. 사용자가 `/watch add <symbol>`을 실행한다.
2. symbol은 현재처럼 canonical symbol로 정규화한다.
3. 길드 watch forum이 설정되지 않았으면 요청을 거절한다.
4. 길드 watchlist에 symbol이 없으면 추가한다.
5. symbol 전용 thread를 보장한다.
6. thread가 없으면 새 thread를 생성한다.
7. thread가 이미 있으면 재사용한다.
8. starter message는 초기 상태(`현재가 조회 전` 또는 첫 snapshot 기준)로 생성/복구된다.

### 5.3 Intraday poll update
1. scheduler는 기존 watch poll interval 기반 cadence를 유지한다.
2. regular session이 열려 있는 active symbol만 intraday update 대상으로 본다.
3. 각 active symbol에 대해 최신 `WatchSnapshot`을 조회한다.
4. starter message를 갱신한다.
5. 세션 기준 최고 신규 `3% band`가 감지되면 intraday comment를 남긴다.
6. band는 `+3%`, `+6%`, `+9%` 및 `-3%`, `-6%`, `-9%` 식으로 상한 없이 확장된다.
7. 한 poll에서 여러 band를 건너뛰면 최고 신규 band 기준 intraday comment 1건만 남긴다.

### 5.4 Close finalization
1. regular session close가 확인되면 마지막 unfinalized session을 close finalization 대상으로 본다.
2. close finalization은 대상 session의 official regular-session close price를 확보할 수 있을 때만 진행한다.
3. first eligible poll after close는 해당 session의 intraday comment들을 idempotent하게 삭제한다.
4. 같은 thread에 `마감가 알림` comment 1건을 생성하거나, retry 시 이미 존재하는 same-session close comment를 재사용한다.
5. `마감가 알림`에는 `날짜`, `전일 종가`, `마감가`, `최종 변동률`이 포함되며, `마감가`는 official regular-session close price를 사용한다.
6. close comment 생성 또는 재사용 직후 `close_comment_ids_by_session[session_date]`를 checkpoint한 뒤 finalization 완료 상태를 저장한다.
7. close snapshot, comment delete/create, checkpoint save, finalization write 중 하나라도 실패하면 session은 unfinalized로 남고, 이후 off-hours poll은 intraday update 없이 finalization만 재시도할 수 있다.
8. retry 시 이미 삭제된 intraday comment의 `NotFound`는 허용적으로 처리하고, existing same-session close comment가 발견되면 duplicate close comment를 만들지 않는다.

### 5.5 Remove watch symbol
- `/watch remove <symbol>` 시 해당 symbol은 길드 active watchlist에서 제거된다.
- 기존 thread는 삭제하지 않고 history로 남긴다.
- bot은 해당 thread의 starter message를 `inactive` 상태로 갱신하고 신규 intraday update는 더 이상 하지 않는다.
- 다만 remove 시점에 current session의 intraday state가 아직 unfinalized이면, scheduler는 그 session에 한해 close finalization을 1회 수행해 intraday comment를 정리하고 `마감가 알림`을 남긴 뒤 완전히 중지한다.
- 같은 symbol을 다시 add 할 때 기존 thread와 starter message가 접근 가능하면 재사용한다.

## 6. Thread Model

### 6.1 One thread per guild-symbol
- logical key는 `(guild_id, canonical_symbol)`이다.
- thread title 기본 형식:
  - `{friendly_display_name} ({canonical_symbol})`
- 예:
  - `삼성전자 (KRX:005930)`
  - `Apple Inc. (NAS:AAPL)`

### 6.2 Starter message contract
- starter message는 symbol의 current state summary surface다.
- regular session open 중 poll 성공 시 갱신되는 필수 항목:
  - 종목명 / canonical symbol
  - 기준가: 전일 종가
  - 현재가
  - 변동률: `((현재가 - 전일 종가) / 전일 종가) * 100`
  - 당일 alert status
  - 당일 최고 도달 상승/하락 band
  - 마지막 갱신 시각
  - 기준 세션 날짜
- regular session close 후에는 close finalization 완료 전까지 intraday starter edit를 더 이상 수행하지 않는다.
- 당일 alert status enum:
  - `idle`
  - `up-active`
  - `down-active`
  - `both-active`
  - `inactive`

### 6.3 Comment contract
- 댓글은 notification event surface다.
- intraday comment는 `3% band` 신규 돌파 이벤트에서만 남긴다.
- band 예시:
  - `+3%`, `+6%`, `+9%` ...
  - `-3%`, `-6%`, `-9%` ...
- 한 poll에서 여러 단계가 동시에 새로 열려도 intraday comment는 최고 신규 band 1건만 남긴다.
- regular session close 뒤에는 intraday comment를 정리하고 `마감가 알림` comment 1건을 남긴다.
- starter message edit만으로는 개인 notify를 기대하지 않는다.
- thread follower notification은 댓글 발생에 의존한다.

## 7. Reference Price and Session Model

### 7.1 Reference price
- 기준가는 항상 `previous_close`다.
- 현재가가 임시로 이상치여도 기준가는 intraday 동안 바뀌지 않는다.
- 세션이 바뀌면 새로운 `previous_close` 기준으로 reference snapshot을 교체한다.

### 7.2 Session date
- `당일`의 기준은 bot local clock이 아니라 symbol market의 regular-session trading date다.
- provider는 snapshot마다 `session_date`를 함께 제공해야 한다.
- KRX symbol은 KRX trading date를 사용한다.
- US symbol은 US market trading date를 사용한다.
- session reset은 `session_date`가 바뀔 때만 발생한다.

### 7.3 Alert persistence rule
- `change_pct`에서 방향별 최고 도달 band를 계산한다.
  - 예: `+7.4%` -> `up_band=2`
  - 예: `-10.2%` -> `down_band=3`
- 세션 내 최고 도달 `up_band`와 `down_band`를 각각 유지한다.
- 이후 price가 threshold 안으로 복귀해도 이미 도달한 최고 band 기록은 세션 종료 전까지 유지된다.
- 따라서 intraday 상태가 `both-active`가 되는 것도 허용한다.
- 기존 As-Is의 `cooldown + threshold inside rearm + same-direction latch reset` 규칙은 target model에서 사용하지 않는다.

## 8. Scheduler and Posting Rules

### 8.1 Scheduler cadence
- watch poll은 interval-based scheduler를 유지한다.
- 기본 poll interval은 현재 기본값과 같은 60초를 유지한다.

### 8.2 Regular-session gate
- intraday starter edit와 band detection은 symbol market의 regular session이 열려 있을 때만 수행한다.
- pre-market과 post-market에서는 intraday update를 수행하지 않는다.
- off-hours poll은 close finalization 대상이 있는지 확인하는 no-op/passive tick으로 동작한다.

### 8.3 Per-poll processing
1. active guild-symbol 집합을 모은다.
2. forum route와 symbol thread가 유효한지 확인한다.
3. symbol market의 regular session open 여부를 확인한다.
4. open session이면 `WatchSnapshot`을 조회하고 starter message를 edit 한다.
5. 최고 신규 `3% band`가 감지되면 intraday comment를 append 한다.
6. forum/thread/message write 실패는 watch job failure로 기록한다.

### 8.4 Close finalization processing
1. scheduler는 symbol market의 regular session close를 감지한다.
2. close finalization이 아직 수행되지 않은 마지막 session만 처리한다.
3. finalization 대상 session의 official regular-session close price를 포함한 close snapshot을 확보한다.
4. first eligible poll after close는 해당 session의 intraday comment를 idempotent하게 삭제한다.
5. `마감가 알림` comment를 1건 생성하거나 existing same-session close comment를 재사용한다.
6. `close_comment_ids_by_session[session_date]`를 즉시 checkpoint하고, 그 뒤 finalization 완료 상태를 저장해 중복 close comment를 막는다.
7. restart 또는 delayed startup 뒤에도 같은 session은 한 번만 finalize되어야 한다.
8. retry 시 이미 삭제된 intraday comment의 `NotFound`는 fatal로 취급하지 않는다.

### 8.5 Edit policy
- starter message는 regular session open 중 성공 poll마다 현재 값을 반영해야 한다.
- 다만 API 호출량 완화를 위해 구현에서는 `렌더 결과가 직전과 동일하면 edit 생략` 최적화를 둘 수 있다.
- 이 최적화는 기능 의미를 바꾸지 않아야 한다.

### 8.6 Missing thread recovery
- state에 thread ID가 있어도 실제 thread/starter message fetch가 실패하면 recreate 경로를 탄다.
- recreate는 같은 guild-symbol logical key를 유지하는 복구 동작으로 본다.
- 새 thread 생성 후 state mapping을 교체한다.

## 9. Target State Model

### 9.1 Guild config
```json
{
  "guilds": {
    "123": {
      "watch_forum_channel_id": 456,
      "watchlist": ["KRX:005930", "NAS:AAPL"]
    }
  }
}
```

### 9.2 Command-scoped thread registry
```json
{
  "commands": {
    "watchpoll": {
      "symbol_threads_by_guild": {
        "123": {
          "KRX:005930": {
            "thread_id": 1001,
            "starter_message_id": 1002,
            "status": "active"
          }
        }
      }
    }
  }
}
```

### 9.3 System-scoped watch runtime state
```json
{
  "system": {
    "watch_reference_snapshots": {
      "123": {
        "KRX:005930": {
          "basis": "previous_close",
          "reference_price": 73100.0,
          "session_date": "2026-03-26",
          "checked_at": "2026-03-26T09:01:00+09:00"
        }
      }
    },
    "watch_session_alerts": {
      "123": {
        "KRX:005930": {
          "active_session_date": "2026-03-26",
          "highest_up_band": 3,
          "highest_down_band": 0,
          "intraday_comment_ids": [2001, 2002, 2003],
          "close_comment_ids_by_session": {
            "2026-03-24": 1801,
            "2026-03-25": 1901
          },
          "last_finalized_session_date": "2026-03-25",
          "updated_at": "2026-03-26T10:11:00+09:00"
        }
      }
    }
  }
}
```

## 10. Provider Contract Needed By This Design

### 10.1 Internal watch snapshot type
- target scheduler는 current `Quote`보다 richer한 internal `WatchSnapshot`을 사용한다.
- `WatchSnapshot`은 watch scheduler path에서 current `Quote`를 확장 또는 대체하는 internal normalized type으로 본다.

### 10.2 Required normalized watch snapshot
- 필요한 필드:
  - `symbol`
  - `current_price`
  - `previous_close`
  - `session_close_price`
  - `asof`
  - `session_date`
  - `provider`

### 10.3 External-to-internal mapping
- external quote contract의 `price` 필드는 internal `WatchSnapshot.current_price`로 정규화된다.
- `symbol`은 canonical symbol이어야 한다.
- `session_date`는 symbol market의 regular-session trading date여야 한다.
- external `session_close_price`가 있으면 internal `WatchSnapshot.session_close_price`로 정규화된다.

### 10.4 Required field rules
- `current_price > 0`
- `previous_close > 0`
- `session_close_price` is nullable while regular session is open, but required for close finalization after regular session close
- `asof` is timezone-aware
- `session_date` is `YYYY-MM-DD`
- `symbol` is canonical symbol

### 10.5 Failure policy
- snapshot에 `previous_close` 또는 `session_date`가 없으면 scheduler는 해당 symbol을 실패로 기록하고 starter/comment를 갱신하지 않는다.
- stale quote 정책은 계속 유지하되, `previous_close`와 `session_date`도 같은 snapshot 기준으로 신뢰 가능해야 한다.
- close finalization 시점 판정은 quote payload가 아니라 scheduler의 market calendar 기준으로 수행할 수 있다.
- close finalization 시점에 `session_close_price`를 확보하지 못하면 scheduler는 same-session `마감가 알림`을 만들지 않고 unfinalized 상태로 남겨 다음 off-hours poll에서 재시도한다.

## 11. Alert Rules

### 11.1 Threshold constants
- `WATCH_ALERT_THRESHOLD_PCT = 3.0`

### 11.2 Event detection
- `up_band = floor(change_pct / 3.0)` for `change_pct >= +3.0`
- `down_band = floor(abs(change_pct) / 3.0)` for `change_pct <= -3.0`
- `up_band > highest_up_band`
  - starter status를 `up-active` 또는 `both-active`로 반영
  - 최고 신규 상승 band comment 1회 작성
  - `highest_up_band = up_band`
- `down_band > highest_down_band`
  - starter status를 `down-active` 또는 `both-active`로 반영
  - 최고 신규 하락 band comment 1회 작성
  - `highest_down_band = down_band`

### 11.3 No rearm inside same session
- 같은 세션 안에서는 price가 다시 threshold 안으로 들어와도 `highest_up_band/highest_down_band`를 줄이지 않는다.
- 따라서 이미 지난 band에 대한 comment 재발송은 없다.
- 더 높은 band로 확장된 경우에만 새 comment가 생긴다.
- 반대 방향 band ladder는 독립적으로 진행한다.

### 11.4 Close summary comment
- regular session close가 확인되면 해당 세션의 intraday comment를 삭제한다.
- 이후 아래 내용을 담은 `마감가 알림` comment 1건을 남긴다.
  - 날짜
  - 전일 종가
  - 마감가: official regular-session close price
  - 최종 변동률
- `마감가 알림`은 삭제하지 않는다.
- 과거 session의 `마감가 알림` comment는 이후 cleanup 대상이 아니다.
- retry 중 same-session close comment가 이미 있으면 이를 재사용하고 중복 생성하지 않는다.

## 12. Migration Guidance
- 기존 guild `watchlist`는 유지한다.
- 기존 `watch_alert_channel_id`는 target model에서 authoritative route가 아니다.
- target model의 authoritative route는 `watch_forum_channel_id`다.
- 기존 `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`는 target model에서 authoritative state가 아니다.
- rollout 시 첫 성공 snapshot부터 `watch_reference_snapshots`와 `watch_session_alerts`를 새로 채운다.
- 기존 first-seen baseline state를 previous-close basis로 직접 변환하지 않는다.
- 기존 text alert history는 forum thread intraday comment history로 직접 변환하지 않는다.

## 13. Operational Notes
- forum route가 없으면 `/watch add`를 명시적으로 거절한다.
- thread가 follower 기반 notification surface이므로, 운영 안내에는 `관심 종목 thread를 follow해야 comment 알림을 받는다`는 점이 포함돼야 한다.
- 매분 starter edit는 text alert보다 API write 빈도가 높으므로, `content unchanged` edit skip 최적화를 기본으로 고려한다.
- intraday comment는 close finalization에서 삭제되므로 long-lived thread의 comment 오염을 줄일 수 있다.
- close finalization은 first eligible poll after close 기준의 catch-up contract를 포함하므로, delayed startup 뒤에도 stale intraday comment가 영구 잔류하면 안 된다.

## 14. Not Current Behavior
- 현재 구현은 text channel alert 기반이다.
- 현재 구현은 first-seen baseline, cooldown, latch, threshold rearm 모델이다.
- 현재 구현은 `previous_close`와 `session_date`를 필수로 요구하지 않는다.
- 현재 구현은 persistent symbol forum thread를 만들지 않는다.

## 15. Related Docs
- Current behavior:
  - `watch-poll-functional-spec.md`
  - `as-is-functional-spec.md`
- Target external adapter contract:
  - `external-intel-api-spec.md`
