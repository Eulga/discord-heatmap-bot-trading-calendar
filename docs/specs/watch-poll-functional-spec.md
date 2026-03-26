# Watch Poll Functional Specification

## 1. Scope
- 이 문서는 현재 코드에 구현된 `watch_poll` 기능의 현재 동작을 정리한 전용 기능명세서다.
- 목표/설계 문서는 `watch-poll-to-be-spec.md`와 `external-intel-api-spec.md`를 본다.
- 이 문서는 현재 저장소 코드와 테스트로 확인된 사실만 기록한다.

## 2. Feature Summary
- `watch_poll`은 길드 공유 watchlist를 기반으로 종목별 persistent forum thread를 유지한다.
- authoritative route는 길드 state의 `watch_forum_channel_id`다.
- `/watch add`는 watch forum route가 없으면 거절되고, 성공 시 symbol thread와 starter message를 즉시 보장한다.
- poll은 regular session open 중 starter message를 갱신하고, `previous_close` 기준 `3% band ladder` 최고 신규 구간에 대해서만 intraday comment를 남긴다.
- regular session close 후 off-hours poll은 intraday starter edit 없이 close finalization만 시도한다.
- close finalization은 intraday comment를 삭제하고 same-session `마감가 알림` comment 1건을 남긴다.
- 기존 `watch_alert_channel_id`, `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`는 legacy read/cleanup 대상으로만 남아 있고, 현재 poll semantics의 authoritative 입력은 아니다.

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
- symbol-specific forum thread and starter message
- intraday band comments and close-summary comments

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
          "intraday_comment_ids": [2001, 2002],
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
- watchlist에 symbol을 추가하고, 같은 guild-symbol logical key에 대한 thread/starter를 즉시 create or recover 한다.
- 기존 symbol thread가 현재 configured watch forum에 속하지 않으면 재사용하지 않고 새 forum 아래에서 다시 만든다.
- starter 내용은 초기 placeholder 또는 현재 snapshot summary다.

### `/watch remove`
- active watchlist에서만 제거한다.
- legacy cooldown/latch/baseline state는 cleanup된다.
- symbol thread registry status는 `inactive`로 바뀐다.
- starter message는 사용자용 `감시가 중지되었습니다` placeholder로 갱신하려고 시도한다.
- 현재 session이 아직 finalization되지 않았으면 scheduler가 off-hours poll에서 1회 close finalization을 끝낸 뒤 완전히 중지한다.

### `/watch list`
- active watchlist만 보여준다.
- inactive historical thread는 목록에 나오지 않는다.

## 6. Polling Semantics

### Session gate
- KRX symbol은 `XKRX`, `Asia/Seoul`, `09:00-15:30` regular session을 사용한다.
- `NAS`, `NYS`, `AMS` symbol은 `XNYS`, `America/New_York`, `09:30-16:00` regular session을 사용한다.
- open session일 때만 starter edit와 intraday band detection을 수행한다.
- off-hours poll은 starter edit나 신규 intraday comment를 만들지 않는다.

### Target discovery
- active watchlist symbol은 항상 poll 대상 후보가 된다.
- inactive symbol이라도 `watch_session_alerts`에 unfinalized session이 남아 있으면 off-hours finalization 후보로 유지된다.
- watch forum route가 없는 guild는 `missing_forum_guilds`로 집계된다.

### Warm-up
- provider가 `warm_watch_snapshots()`를 구현하면 target symbol의 unique canonical set에 대해 poll cycle당 1회 호출한다.
- warm-up 실패는 로그만 남기고 poll 전체를 중단시키지 않는다.

### Open-session update
1. scheduler가 snapshot을 조회한다.
2. `previous_close`와 `session_date`가 같지 않으면 provider failure로 본다.
3. 이전 session이 아직 finalization되지 않은 상태에서 더 늦은 `session_date` snapshot이 오면, current session starter로 넘어가기 전에 prior session close finalization을 먼저 시도한다.
3. session이 바뀌면 `watch_reference_snapshots`를 새 `previous_close/session_date`로 교체한다.
4. session change 시 `highest_up_band`, `highest_down_band`, `intraday_comment_ids`는 reset된다.
5. starter message는 아래 정보를 포함해 매 성공 poll마다 edit된다.
   - 종목명 / canonical symbol
   - 전일 종가 (`KRX=₩`, `NAS/NYS/AMS=$`)
   - 현재가 (`KRX=₩`, `NAS/NYS/AMS=$`)
   - 변동률
   - 마지막 갱신 시각
6. `change_pct = ((current_price - previous_close) / previous_close) * 100`를 계산한다.
7. `3% band ladder` 규칙:
   - `+3`, `+6`, `+9` ...
   - `-3`, `-6`, `-9` ...
8. 한 poll에서 여러 band를 건너뛰어도 intraday comment는 최고 신규 band 1건만 남긴다.
   - format: `{symbol} +3% 이상 상승 : +3.80% · {timestamp}`
   - down case도 같은 형식으로 `-3% 이상 하락`을 사용한다.
9. 같은 session 안에서는 한번 도달한 band를 내리지 않는다.
10. 반대 방향 ladder는 독립적으로 진행되어 `both-active`가 될 수 있다.

### Off-hours close finalization
1. unfinalized session이 있는 symbol만 대상이다.
2. `session_close_price`가 아직 없으면 session은 그대로 unfinalized로 남는다.
3. finalization 순서:
   - intraday comment delete
   - same-session close comment reuse or create
   - `close_comment_ids_by_session[session_date]` checkpoint save
   - `last_finalized_session_date` save
4. close comment는 아래 내용을 담는다.
   - marker: `[watch-close:{symbol}:{session_date}]`
   - 날짜
   - 전일 종가
   - 마감가
   - 최종 변동률
5. 기존 close comment ID가 state에 없더라도 thread history에서 같은 marker를 찾으면 재사용한다.
6. delete/create/checkpoint/finalization 중간 실패가 있으면 session은 unfinalized 상태로 남고 이후 off-hours poll에서 재시도된다.

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
- `WATCH_ALERT_CHANNEL_ID`는 settings에 남아 있어도 startup/runtime에서 watch route로 bootstrap하지 않는다.
- `watch_alert_channel_id`는 과거 state를 읽을 수는 있지만 현재 watch poll routing source of truth가 아니다.
- `watch_alert_cooldowns`, `watch_alert_latches`, `system.watch_baselines`는 remove cleanup과 legacy read 호환만 남아 있다.
- 새 alert/session state는 legacy state를 seed하지 않고 첫 성공 snapshot부터 채운다.

## 9. Job Status and Provider Status
- job detail에는 아래 집계가 들어간다.
  - `active_symbols`
  - `updated_threads`
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
