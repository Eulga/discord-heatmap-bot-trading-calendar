# Watch Poll Functional Specification

## 1. Scope
- 이 문서는 현재 코드에 구현된 `watch_poll` 기능의 동작을 정리한 전용 기능명세서다.
- 외부 시세 API의 정규화 계약은 이 문서가 아니라 `external-intel-api-spec.md`의 `Watch Quote API` 섹션을 따른다.
- 목표/이상 동작이 아니라, 현재 저장소 코드와 테스트로 확인된 사실을 우선 기록한다.
- live Discord 또는 vendor API smoke는 이번 문서 작업 범위에서 다시 실행하지 않았다.

## 2. Feature Summary
- `watch_poll`은 길드별 watchlist를 주기적으로 조회해, 기준가 대비 현재가 변동률이 임계치를 넘으면 Discord 텍스트 채널로 알림을 보낸다.
- watch 대상은 사용자별이 아니라 길드별 공유 상태로 저장된다.
- 비교 기준은 `현재가 vs 직전가`가 아니라 `현재가 vs 저장된 baseline`이다.
- baseline은 첫 성공 조회 시점의 가격으로 설정되고, 같은 심볼이 watchlist에서 제거되기 전까지 유지된다.
- watch symbol 저장값은 canonical symbol(`KRX:005930`, `NAS:AAPL`) 기준이며, legacy 저장값은 poll/read 시 정규화된다.

## 3. Out Of Scope
- `/watch add`, `/watch remove`, `/watch list` 명령 자체의 상세 UX 명세
- 외부 vendor API 응답 포맷의 상세 계약
- 시장 세션 판정, 휴장일 정책, 또는 운영자 권한 정책의 미래 설계

## 4. Code-Confirmed Inputs and Dependencies

### Config
- `WATCH_POLL_ENABLED`
  - 기본값 `True`
- `WATCH_POLL_INTERVAL_SECONDS`
  - 기본값 `60`
- `WATCH_ALERT_THRESHOLD_PCT`
  - 기본값 `3.0`
- `WATCH_ALERT_COOLDOWN_MINUTES`
  - 기본값 `10`
- `MARKET_DATA_PROVIDER_KIND`
  - 기본값 `"mock"`
- live provider credentials
  - `KIS_APP_KEY`, `KIS_APP_SECRET`
  - optional US fallback: `MASSIVE_API_KEY` 또는 `POLYGON_API_KEY`

### Runtime state
- `guilds.{guild_id}.watchlist`
- `guilds.{guild_id}.watch_alert_channel_id`
- `guilds.{guild_id}.watch_alert_cooldowns`
- `guilds.{guild_id}.watch_alert_latches`
- `system.watch_baselines.{guild_id}.{symbol}`
- `system.job_last_runs.watch_poll`
- `system.provider_status.{provider_key}`

### External/runtime dependencies
- `quote_provider` module singleton
- local instrument registry
  - `data/state/instrument_registry.json` runtime override가 있으면 우선 사용
  - 없으면 bundled registry 사용
- Discord messageable channel
  - 현재 guild에 속한 채널이어야 한다

## 5. Provider Wiring
- `MARKET_DATA_PROVIDER_KIND = "mock"`
  - `MockMarketDataProvider`
- `MARKET_DATA_PROVIDER_KIND = "kis"`
  - KIS credential이 모두 있으면 `KisMarketDataProvider`
  - KIS credential이 비어 있으면 `ErrorMarketDataProvider("kis-credentials-missing")`
- `MARKET_DATA_PROVIDER_KIND = "kis"` 이고 `MASSIVE_API_KEY`가 있으면
  - `RoutedMarketDataProvider(primary=KIS, us_fallback=Massive)`
  - US symbol(`NAS`, `NYS`, `AMS`)만 Massive fallback 대상이다
- 알 수 없는 provider kind는 `ErrorMarketDataProvider("unsupported-market-data-provider:...")`로 fail-closed 된다
- provider가 `warm_quotes(symbols, now)`를 구현하면 pending guild 전체의 unique symbol 집합에 대해 poll cycle당 1회 선행 호출한다
  - warm-up 실패는 로그만 남기고 poll 전체를 중단시키지 않는다

## 6. Trigger and Scheduling
- `intel_scheduler()`는 15초 sleep loop로 동작한다.
- `WATCH_POLL_ENABLED`가 `True`일 때만 watch poll 경로를 평가한다.
- `last_watch_run`이 없거나 `now - last_watch_run >= WATCH_POLL_INTERVAL_SECONDS`이면 `_run_watch_poll(client, now)`를 실행한다.
- 따라서 watch poll은 뉴스/EOD처럼 exact-minute scheduler가 아니라 interval-based scheduler다.
- 실제 실행 해상도는 15초 loop granularity 영향을 받는다.

## 7. Functional Flow

### 7.1 Target discovery
1. `_run_watch_poll()`이 state를 로드한다.
2. 모든 guild를 순회하면서 `list_watch_symbols(state, guild_id)`를 호출한다.
3. `list_watch_symbols()`는 watchlist를 canonical symbol 기준으로 정규화하고, 필요하면 baseline/cooldown/latch key도 같이 migrate 한다.
4. watchlist가 비어 있는 guild는 즉시 제외한다.
5. `watch_alert_channel_id`가 없는 guild는 `missing_channel_guilds`로 집계하고 제외한다.
6. channel은 `client.get_channel()` 우선, 없으면 `client.fetch_channel()`로 조회한다.
7. channel 조회가 실패하거나, messageable이 아니거나, 다른 guild 소속이면 `channel_failures`로 집계하고 제외한다.
8. 유효한 guild만 `pending_guilds`로 모으고, 모든 symbol을 `warm_symbols` 집합에 추가한다.

### 7.2 Quote warm-up
1. `quote_provider`가 `warm_quotes()`를 제공하면 `sorted(warm_symbols)`로 1회 호출한다.
2. warm-up은 best-effort다.
3. warm-up 실패는 exception log만 남기고, 이후 개별 `get_quote()` 경로는 계속 진행된다.

### 7.3 Per-symbol evaluation
1. 각 `pending_guild`의 각 symbol마다 `quote_provider.get_quote(symbol, now)`를 호출한다.
2. quote 성공 시:
   - `quote.provider`가 있으면 그 값을 provider status key로 사용한다.
   - 값이 없으면 기본 key는 `kis_quote`다.
   - `set_provider_status(..., ok=True, message=f"quote:{symbol}")`를 기록한다.
3. quote 실패 시:
   - exception의 `provider_key`가 있으면 그 값을 사용하고, 없으면 `kis_quote`를 사용한다.
   - `set_provider_status(..., ok=False, message=str(exc))`를 기록한다.
   - `quote_failures += 1` 후 다음 symbol로 넘어간다.
4. baseline은 `get_watch_baseline(state, guild_id, symbol)` 결과가 있으면 그 값을 사용하고, 없으면 이번 quote의 `price`를 baseline으로 삼는다.
5. `evaluate_watch_signal()`이 `base_price`, `current_price`를 받아 `(should_send, direction, change_pct)`를 계산한다.
6. baseline은 alert 여부와 무관하게 `set_watch_baseline(state, guild_id, symbol, baseline, now.isoformat())`로 다시 저장된다.
   - 현재 구현상 `price`는 유지되고 `checked_at`만 최신 poll 시각으로 덮어쓴다.
7. `should_send=True`면 채널에 plain text alert를 전송한다.
8. 전송 성공 시 `sent += 1`, 실패 시 `send_failures += 1`이다.

### 7.4 Job finalization
- detail 문자열에는 아래 집계가 들어간다.
  - `alerts`
  - `alert_attempts`
  - `processed`
  - `watched_symbols`
  - `quote_failures`
  - `channel_failures`
  - `missing_channel_guilds`
  - `send_failures`
- 최종 status 규칙:
  - `watched_symbols == 0` -> `skipped`, detail=`no-watch-symbols`
  - `quote_failures > 0` 또는 `channel_failures > 0` 또는 `send_failures > 0` -> `failed`
  - 그 외 `processed > 0` -> `ok`
  - 그 외 -> `skipped`, detail prefix=`no-target-channels`
- 마지막에 `set_job_last_run(state, "watch_poll", status, detail)` 후 `save_state(state)`를 수행한다.
- 동일 결과는 `[intel] watch_poll status=... detail=...` 형식으로 파일 로그에도 남는다.

## 8. Alert Decision Rules
- 변동률 계산식:
  - `change_pct = ((current_price - base_price) / base_price) * 100`
  - `base_price <= 0`이면 `0.0`으로 처리한다
- 방향 판정:
  - `change_pct >= WATCH_ALERT_THRESHOLD_PCT` -> `up`
  - `change_pct <= -WATCH_ALERT_THRESHOLD_PCT` -> `down`
  - 그 사이 구간 -> no signal
- no signal일 때:
  - 해당 symbol의 same-direction latch를 해제한다
  - 알림은 보내지 않는다
- same-direction latch:
  - 현재 direction이 이미 latch와 같으면 cooldown이 끝났더라도 재알림하지 않는다
  - 한 번 threshold 안으로 복귀해 latch가 해제된 뒤에만 같은 방향 재알림이 가능하다
- cooldown key:
  - `"{SYMBOL}:{direction}"`
  - 방향별로 분리되므로 같은 symbol이라도 `up`과 `down`은 별도 cooldown을 가진다
- cooldown 판정:
  - 마지막 hit 시각으로부터 `WATCH_ALERT_COOLDOWN_MINUTES` 이내면 재알림하지 않는다
  - timestamp parse 실패는 무시하고 새 hit로 갱신한다
- 첫 성공 quote:
  - baseline이 없으면 현재 price가 baseline이 되므로 첫 poll에서는 `change_pct=0`이다
  - 따라서 첫 성공 quote만으로는 alert가 발생하지 않는다
- symbol 제거/재등록:
  - `/watch remove`는 baseline, cooldown, latch를 함께 지운다
  - 같은 symbol을 다시 추가하면 fresh baseline lifecycle로 시작한다

## 9. State Model

### 9.1 Guild-scoped state
```json
{
  "guilds": {
    "123": {
      "watch_alert_channel_id": 456,
      "watchlist": ["KRX:005930", "NAS:AAPL"],
      "watch_alert_cooldowns": {
        "KRX:005930:up": "2026-03-26T09:10:00+09:00"
      },
      "watch_alert_latches": {
        "KRX:005930": "up"
      }
    }
  }
}
```

### 9.2 System-scoped runtime state
```json
{
  "system": {
    "watch_baselines": {
      "123": {
        "KRX:005930": {
          "price": 73100.0,
          "checked_at": "2026-03-26T09:12:00+09:00"
        }
      }
    },
    "job_last_runs": {
      "watch_poll": {
        "status": "ok",
        "detail": "alerts=1 alert_attempts=1 processed=2 watched_symbols=2 quote_failures=0 channel_failures=0 missing_channel_guilds=0 send_failures=0",
        "run_at": "2026-03-26T09:12:00+09:00"
      }
    },
    "provider_status": {
      "kis_quote": {
        "ok": true,
        "message": "quote:KRX:005930",
        "updated_at": "2026-03-26T09:12:00+09:00"
      }
    }
  }
}
```

## 10. User-Visible Output
- alert message format:
  - 상승: `📈 {friendly_symbol} 변동 알림: 기준가 {baseline} → 현재가 {price} ({change_pct:+.2f}%)`
  - 하락: `📉 {friendly_symbol} 변동 알림: 기준가 {baseline} → 현재가 {price} ({change_pct:+.2f}%)`
- `friendly_symbol`은 registry display name을 우선 사용한다.
  - 예: `삼성전자 (KRX:005930)`

## 11. Current Constraints and Known Gaps
- watchlist는 길드 공유 상태이며 user-scoped isolation이 없다.
- runtime routing source of truth는 env가 아니라 guild state의 `watch_alert_channel_id`다.
  - env `WATCH_ALERT_CHANNEL_ID`는 startup bootstrap 용도다.
- market session / trading day gating은 현재 `_run_watch_poll()`에 없다.
- quote freshness는 provider별로 다르게 보장된다.
  - KIS overseas와 Massive fallback은 source timestamp 기반 freshness 검사(`2분`)가 있다.
  - KIS domestic은 현재 poll 시각 `now`를 `asof`로 사용하므로 source timestamp freshness를 직접 검증하지 않는다.
- channel ID가 아예 없는 guild는 `missing_channel_guilds`로만 집계되어, 전체 run status가 `skipped`가 될 수 있다.
- 반면 channel lookup 실패, foreign guild channel, send 실패는 모두 `failed`를 만든다.
- 기본 provider kind가 현재도 `"mock"`이므로, env를 명시적으로 바꾸지 않으면 watch poll은 mock quote 경로를 사용한다.

## 12. Rollout Alignment Notes
- `external-intel-api-spec.md`의 목표 계약은 watch quote adapter가 canonical symbol과 stale quote 제어를 제공하는 것을 요구한다.
- 현재 구현은 canonical symbol 저장, provider/job status 기록, optional warm-up, US fallback routing까지는 반영되어 있다.
- 아직 target contract와 완전히 일치한다고 보기 어려운 지점:
  - market-hours / closed-market skip semantics 부재
  - domestic quote freshness의 source timestamp 검증 부재
  - provider batch contract가 runtime interface의 필수 요구사항은 아님

## 13. Verification Basis
- 코드 확인:
  - `bot/features/intel_scheduler.py`
  - `bot/features/watch/service.py`
  - `bot/forum/repository.py`
  - `bot/intel/providers/market.py`
  - `bot/intel/instrument_registry.py`
  - `bot/app/settings.py`
- 테스트 확인:
  - `tests/integration/test_intel_scheduler_logic.py`
  - `tests/unit/test_watch_cooldown.py`
  - `tests/unit/test_watchlist_repository.py`
- 문서 경계 확인:
  - `docs/specs/as-is-functional-spec.md`
  - `docs/specs/external-intel-api-spec.md`
  - `docs/operations/config-reference.md`
