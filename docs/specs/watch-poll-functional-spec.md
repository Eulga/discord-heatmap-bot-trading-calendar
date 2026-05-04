# Watch Poll Functional Specification

## 1. Scope
- 이 문서는 현재 코드에 구현된 `watch_poll` 기능의 현재 동작을 정리한 전용 기능명세서다.
- 목표/설계 문서는 `watch-poll-to-be-spec.md`와 `external-intel-api-spec.md`를 본다.
- 이 문서는 현재 저장소 코드와 테스트로 확인된 사실만 기록한다.

## 2. Feature Summary
- `watch_poll`은 길드 공유 watchlist를 기반으로 종목별 status(`active`/`inactive`)와 persistent forum thread를 유지한다.
- authoritative route는 길드 state의 `watch_forum_channel_id`다.
- `/watch add`는 watch forum route가 없으면 거절되고, 새 symbol에 대해서만 symbol thread와 blank starter message를 즉시 만든다.
- `/watch start`는 stopped symbol을 다시 active로 전환하고, `/watch stop`은 symbol을 watchlist에 남긴 채 실시간 감시만 중단한다.
- `/watch delete`는 admin command로 동작하며 symbol을 watchlist와 thread/state에서 완전히 제거한다.
- poll은 regular session open 중 active symbol의 현재가 전용 comment를 갱신하고, `previous_close` 기준 `3% band ladder` 최고 신규 구간에 대해서만 intraday comment를 남긴다.
- band comment가 새로 생긴 poll에서는 현재가 comment를 삭제 후 다시 보내 thread 하단에 유지한다.
- regular session close 후 close finalization은 KST exact-minute due time에만 시도한다.
  - KRX symbol은 KST `16:00` minute에만 시도한다.
  - NAS/NYS/AMS symbol은 KST `07:00` minute에만 시도한다.
  - due minute을 놓치면 close finalization만 pending으로 남고, 이후 정규장 current-price comment와 band alert는 계속 수행한다.
  - pending close target이 바로 다음 trading session을 지나 더 이상 `previous_close` fallback으로 해소될 수 없으면 retry state에서 제거한다.
- close finalization은 현재가 comment와 intraday comment를 삭제하고 same-session `마감가 알림` comment 1건을 남긴다.
- 과거 text watch route (`WATCH_ALERT_CHANNEL_ID` / `watch_alert_channel_id`)는 hard cut 되었고, `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`만 legacy cleanup/read 호환 대상으로 남아 있다.

## 3. Runtime Inputs and Dependencies

### Config
- `WATCH_POLL_ENABLED`
- `WATCH_POLL_INTERVAL_SECONDS`
- `WATCH_ALERT_THRESHOLD_PCT`
- `MARKET_DATA_PROVIDER_KIND`
- live provider credentials
  - `KIS_APP_KEY`, `KIS_APP_SECRET`
  - optional US fallback: `MASSIVE_API_KEY` or `POLYGON_API_KEY`

### Runtime state
- `guilds.{guild_id}.watch_forum_channel_id`
- `guilds.{guild_id}.watchlist`
- `commands.watchpoll.symbol_threads_by_guild.{guild_id}.{symbol}`
- `system.watch_reference_snapshots.{guild_id}.{symbol}`
- `system.watch_session_alerts.{guild_id}.{symbol}`
- `system.job_last_runs.watch_poll`
- `system.provider_status.{provider_key}`

### Discord resources
- watch forum channel per guild
- symbol-specific forum thread and blank starter message
- current-price, intraday band, and close-summary comments

### Provider contract
- scheduler는 `quote_provider.get_watch_snapshot(symbol, now)`를 사용한다
- optional batch warm-up은 `warm_watch_snapshots(symbols, now)`다
- normalized snapshot 필드:
  - `symbol`
  - `current_price`
  - `previous_close`
  - `session_close_price`
  - `asof`
  - `session_date`
  - `provider`

## 4. State Model

### Guild config
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

### Command-scoped thread registry
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
          },
          "NAS:AAPL": {
            "status": "inactive"
          }
        }
      }
    }
  }
}
```

### System-scoped watch runtime state
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
          "highest_up_band": 2,
          "highest_down_band": 1,
          "current_comment_id": 2003,
          "intraday_comment_ids": [2001, 2002],
          "pending_close_sessions": {
            "2026-03-25": {
              "reference_price": 72000.0,
              "intraday_comment_ids": [1900]
            }
          },
          "close_comment_ids_by_session": {
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

## 5. Command and Thread Behavior

### `/setwatchforum`
- admin command다.
- guild owner, guild admin, 또는 `DISCORD_GLOBAL_ADMIN_USER_IDS`에 있는 사용자만 실행할 수 있다.
- 같은 guild의 `ForumChannel`만 허용한다.
- 성공 시 `watch_forum_channel_id`를 저장한다.

### `/watch add`
- guild context가 필요하다.
- symbol은 local instrument registry 기준 canonical symbol로 정규화한다.
- `watch_forum_channel_id`가 없으면 명시적으로 거절한다.
- 이미 watchlist에 있는 symbol을 다시 add하면 no-op으로 거절한다.
  - inactive symbol이면 `/watch start`를 사용하라는 안내를 준다.
- 새 symbol이 watchlist에 추가되면 같은 guild-symbol logical key에 대한 thread/starter를 즉시 create 한다.
- starter 내용은 사용자에게 보이는 본문 없이 blank placeholder로 유지되고, 첫 성공 poll 뒤부터 현재 snapshot summary는 전용 comment에 기록된다.
- 기존 thread/starter recreate는 authoritative `NotFound`일 때만 허용되고, `Forbidden` 또는 generic `HTTPException`은 transient/thread failure로 surface된다.

### `/watch start`
- guild context가 필요하다.
- 현재 guild watchlist에 이미 들어 있고 `inactive` status인 symbol만 대상으로 한다.
- `watch_forum_channel_id`가 없으면 명시적으로 거절한다.
- 같은 regular session 안에 stopped 상태였다면 `highest_up_band` / `highest_down_band` checkpoint는 reset되어 early band alert를 다시 시작할 수 있다.
- thread/starter는 blank starter로 update-or-create 한다.

### `/watch stop`
- guild context가 필요하다.
- 현재 guild watchlist에 이미 들어 있고 `active` status인 symbol만 대상으로 한다.
- symbol은 watchlist에서 제거하지 않는다.
- legacy cooldown/latch/baseline state는 cleanup된다.
- symbol thread registry entry가 이미 있으면 status는 `inactive`로 바뀌고, entry가 없어도 status-only inactive entry를 남길 수 있다.
- 기존 tracked thread/starter가 현재 watch forum에서 resolve될 때만 starter message를 blank 상태로 갱신하려고 시도한다.
- 저장된 현재가 comment가 있으면 삭제하고 `current_comment_id`를 제거한다.
- thread registry가 없거나 stored thread handle이 stale이면 `/watch stop`은 새 inactive thread를 만들지 않는다.
- tracked thread/starter가 있는 경우 blank starter update가 성공한 뒤에만 stop state를 저장한다.
- 기존 thread status 갱신에 실패하면 command는 실패 응답을 반환하고, symbol status와 runtime state는 active 상태로 유지된다.
- 현재 session이 아직 finalization되지 않았으면 scheduler가 off-hours poll에서 1회 close finalization을 끝낸 뒤 완전히 중지한다.

### `/watch delete`
- admin command다.
- guild owner, guild admin, 또는 `DISCORD_GLOBAL_ADMIN_USER_IDS`에 있는 사용자만 실행할 수 있다.
- 현재 guild watchlist에 들어 있는 tracked symbol만 대상으로 한다.
- 기존 thread를 먼저 delete 시도한 뒤, watchlist / thread registry / reference snapshot / session alert state를 함께 제거한다.
- thread handle이 이미 없으면 state cleanup만 진행할 수 있다.

### `/watch list`
- 현재 guild watchlist 전체를 보여준다.
- 각 row는 registry display name과 canonical symbol, 그리고 `실시간 감시중` 또는 `감시 중단됨` status를 함께 보여준다.

## 6. Polling Semantics

### Session gate
- KRX symbol은 `XKRX`, `Asia/Seoul`, `09:00-15:30` regular session을 사용한다.
- `NAS`, `NYS`, `AMS` symbol은 `XNYS`, `America/New_York`, `09:30-16:00` regular session을 사용한다.
- open session일 때만 현재가 comment 갱신과 intraday band detection을 수행한다.
- off-hours poll은 현재가 갱신이나 신규 intraday comment를 만들지 않는다.
- close finalization은 한국시간 기준 exact-minute gate를 통과해야 한다.
  - `KRX:*`: KST `16:00`
  - `NAS:*`, `NYS:*`, `AMS:*`: KST `07:00`
  - 초 단위 exact match가 아니라 해당 KST minute 안의 poll tick이면 due로 본다.

### Target discovery
- active tracked symbol은 항상 poll 대상 후보가 된다.
- inactive tracked symbol이라도 `watch_session_alerts`에 unfinalized session이 남아 있으면 off-hours finalization 후보로 유지된다.
- watch forum route가 없는 guild는 `missing_forum_guilds`로 집계된다.

### Warm-up
- provider가 `warm_watch_snapshots()`를 구현하면 regular-session update 대상과 close-finalization due 대상의 unique canonical set에 대해 poll cycle당 1회 호출한다.
- active regular-session symbol은 prior session close가 pending이어도 warm-up과 snapshot fetch 대상에 계속 포함된다.
- off-hours unfinalized symbol은 due minute이 아니면 warm-up과 snapshot fetch 대상에서 제외된다.
- warm-up 실패는 로그만 남기고 poll 전체를 중단시키지 않는다.
- malformed/unsupported persisted symbol은 warm-up에서 건너뛰고, 개별 symbol 처리 단계에서 `snapshot_failures`로 집계된다.

### Open-session update
1. scheduler가 snapshot을 조회한다.
2. `previous_close`와 `session_date`가 같지 않으면 provider failure로 본다.
3. 이전 session이 아직 finalization되지 않은 상태에서 더 늦은 `session_date` snapshot이 오면, due minute일 때만 current session 현재가 comment로 넘어가기 전에 prior session close finalization을 먼저 시도한다.
   - `snapshot.previous_close` fallback으로 close를 확정하는 경우는 새 snapshot이 target session의 바로 다음 trading session일 때만 허용한다.
   - 여러 trading session을 건너뛴 더 늦은 snapshot만 있는 경우 old session은 그대로 unfinalized로 남는다.
   - due minute이 아니면 old session close target을 `pending_close_sessions`에 보존하고, current session reference/session state로 rotate해 current-price comment와 band alert를 계속 처리한다.
4. session이 바뀌면 `watch_reference_snapshots`를 새 `previous_close/session_date`로 교체한다.
5. session change 시 `highest_up_band`, `highest_down_band`, `intraday_comment_ids`는 reset된다.
6. starter message는 blank 상태로 유지되고, 현재가 comment는 아래 정보를 포함해 매 성공 poll마다 edit된다.
   - 종목명 / canonical symbol
   - 상태: `실시간 감시중`
   - 전일 종가 (`KRX=₩`, `NAS/NYS/AMS=$`)
   - 현재가 (`KRX=₩`, `NAS/NYS/AMS=$`)
   - 변동률
   - 마지막 갱신 시각
   - 저장된 `current_comment_id`가 없거나 메시지가 없으면 새로 만들고, 있으면 같은 comment를 edit한다.
   - 같은 poll에서 band comment를 새로 남기면 기존 현재가 comment를 삭제 후 다시 보내 현재가 comment가 thread 하단에 오도록 한다.
   - 이 recreate 단계의 기존 현재가 comment delete가 `Forbidden`/`HTTPException`으로 실패해도 cleanup failure로 로그만 남기고 새 현재가 comment 생성을 계속 시도한다. 실패한 old comment id는 더 이상 authoritative current display로 보지 않는다.
   - band comment 전송에 실패해도 current-price comment 갱신은 계속 시도하고, 실패한 band checkpoint는 다음 poll에서 재시도될 수 있게 advance하지 않는다.
7. `change_pct = ((current_price - previous_close) / previous_close) * 100`를 계산한다.
8. `3% band ladder` 규칙:
   - `+3`, `+6`, `+9` ...
   - `-3`, `-6`, `-9` ...
9. 한 poll에서 여러 band를 건너뛰어도 intraday comment는 최고 신규 band 1건만 남긴다.
   - format: `{symbol} +3% 이상 상승 : +3.80% · {timestamp}`
   - label의 `%` 숫자는 effective threshold `max(0.1, WATCH_ALERT_THRESHOLD_PCT) * band`를 trailing zero 없이 표시하고, 뒤의 signed percent는 실제 `change_pct` 그대로 표시된다.
   - 즉 threshold가 `2.5`면 label은 `+2.5%`, `+5%`처럼 보이고, threshold가 `0.5`면 `+0.5%`, `+1%`처럼 보인다.
   - down case도 같은 형식으로 `-3% 이상 하락`을 사용한다.
10. 같은 session 안에서는 한번 도달한 band를 내리지 않는다.
11. 반대 방향 ladder는 독립적으로 진행되어 `both-active`가 될 수 있다.

### Off-hours close finalization
1. unfinalized session이 있는 symbol만 대상이다.
2. KST exact-minute due gate를 통과한 poll tick에서만 warm-up, snapshot fetch, close comment 생성/수정을 시도한다.
   - `KRX:*`: KST `16:00`
   - `NAS:*`, `NYS:*`, `AMS:*`: KST `07:00`
   - due minute이 아니면 off-hours session은 그대로 unfinalized로 남고 provider/Discord 호출을 하지 않는다.
3. `session_close_price`가 아직 없으면 session은 그대로 unfinalized로 남는다.
   - market 구분 없이 off-hours poll에서 `session_close_price`가 있고 `session_date`가 현재 off-hours session과 맞으면, last-trade 기반 old `asof`만으로 stale-quote 실패 처리하지 않는다.
   - missed due 뒤 다음 regular session이 시작된 경우, old session의 reference price와 intraday comment IDs는 `pending_close_sessions`에 보존되고 다음 due minute에 close finalization을 재시도한다.
   - 같은 due minute에 pending old session과 current active session이 모두 close 가능한 경우, scheduler는 pending old session close comment를 먼저 만들고 current session close comment를 이어서 만든다.
   - pending old session이 현재 snapshot의 바로 이전 trading session이 아니면 close comment를 만들지 않고 해당 pending entry를 retry state에서 제거한다.
4. finalization 순서:
   - current-price comment delete
   - intraday comment delete
   - same-session close comment reuse or create
   - `close_comment_ids_by_session[session_date]` checkpoint save
   - `last_finalized_session_date` save
   - current-price comment delete의 `Forbidden`/`HTTPException`은 best-effort cleanup failure로 보고 finalization을 계속 진행한다.
5. close comment는 아래 내용을 담는다.
   - marker: `[watch-close:{symbol}:{session_date}]`
   - 날짜
   - 전일 종가
   - 마감가
   - 최종 변동률
6. 기존 close comment ID가 state에 없더라도 thread history에서 같은 marker를 찾으면 재사용한다.
7. delete/create/checkpoint/finalization 중간 실패가 있으면 session은 unfinalized 상태로 남고 이후 due minute poll에서 재시도된다.

## 7. Provider Wiring
- `MARKET_DATA_PROVIDER_KIND = "mock"`
  - `MockMarketDataProvider`
- `MARKET_DATA_PROVIDER_KIND = "kis"`
  - credential이 있으면 `KisMarketDataProvider`
  - credential이 없으면 `ErrorMarketDataProvider("kis-credentials-missing")`
  - 국내 quote freshness는 payload의 체결 시각이 있으면 그 시각을 `asof`로 사용해 stale check를 수행한다.
- `MARKET_DATA_PROVIDER_KIND = "kis"`이고 `MASSIVE_API_KEY` 또는 `POLYGON_API_KEY`가 있으면
  - `RoutedMarketDataProvider(primary=KIS, us_fallback=Massive)`
- provider status message는 watch path에서 `snapshot:{symbol}` 형식을 쓴다.

## 8. Legacy Compatibility
- `WATCH_ALERT_CHANNEL_ID`는 현재 settings/env surface에서 제거됐고 startup/runtime watch route bootstrap이 없다.
- persisted `watch_alert_channel_id`는 남아 있어도 현재 inspected code가 lookup하지 않는다.
- `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`는 stop/delete cleanup과 legacy read/migration 호환만 남아 있다.
- 새 alert/session state는 legacy state를 seed하지 않고 첫 성공 snapshot부터 채운다.

## 9. Job Status and Provider Status
- job detail에는 아래 집계가 들어간다.
  - `active_symbols`
  - `updated_threads`
  - `updated_current_comments`
  - `finalized_sessions`
  - `missing_forum_guilds`
  - `thread_failures`
  - `snapshot_failures`
  - `comment_failures`
- status 규칙:
  - target symbol이 없으면 `skipped` + `no-watch-symbols`
  - forum route가 전혀 없으면 `skipped` + `no-target-forums ...`
  - snapshot/thread/comment failure가 하나라도 있으면 `failed`
  - 그 외는 `ok`

## 10. Verification Basis
- 코드 확인:
  - `bot/features/intel_scheduler.py`
  - `bot/features/watch/command.py`
  - `bot/features/watch/service.py`
  - `bot/features/watch/session.py`
  - `bot/features/watch/thread_service.py`
  - `bot/forum/repository.py`
  - `bot/intel/providers/market.py`
  - `bot/app/bot_client.py`
- 테스트 확인:
  - `tests/integration/test_watch_forum_flow.py`
  - `tests/integration/test_watch_poll_forum_scheduler.py`
  - `tests/unit/test_watch_cooldown.py`
  - `tests/unit/test_watchlist_repository.py`
  - `tests/unit/test_market_provider.py`
