# External Intel API Spec

## 목적
- 새로 추가한 스케줄 기능인 `news_briefing`, `eod_summary`, `watch_poll`을 mock provider에서 실제 운영용 외부 API로 전환하기 위한 표준 계약을 정의한다.
- 특정 벤더 API를 직접 고정하지 않고, 벤더별 응답을 이 문서의 정규화 스키마로 변환하는 adapter 계층을 기준으로 삼는다.
- 현재 코드의 provider 인터페이스와 바로 연결되도록 `NewsItem`, `Quote`, `EodSummary` 타입을 기준으로 명세하되, watch target rollout에서는 current `Quote`를 확장/대체하는 internal `WatchSnapshot` 정규화 레이어를 허용한다.

## 현재 운영 메모 (2026-03-20)
- `eod_summary`는 현재 잠정 중단 상태다. 이 문서의 EOD 섹션은 future reactivation용 참고 계약으로 유지한다.
- watch 종목 검색은 live vendor search API를 직접 치지 않고, `OpenDART + SEC + KRX structured finder(ETF/ETN/ELW/PF)` 기반 local instrument registry로 해석한 뒤 canonical symbol로 저장한다.
- runtime은 bundled snapshot `bot/intel/data/instrument_registry.json`을 기본으로 읽고, optional daily refresh가 성공하면 `data/state/instrument_registry.json` runtime override를 우선 사용한다.
- 현재 canonical symbol 형식은 `KRX:005930`, `NAS:AAPL`, `NYS:KO`, `AMS:SPY`다.

## 적용 대상

| 기능 | 현재 스케줄 | 현재 provider | 실사용 목적 |
| --- | --- | --- | --- |
| 아침 뉴스 브리핑 | KST `07:30` | `NewsProvider.fetch(now)` | 국내/해외 경제 뉴스 요약 포스트 |
| 장마감 요약 | KST `16:20` | `EodSummaryProvider.get_summary(now)` | 한국장 마감 요약 포스트 |
| watchlist 알림 | 기본 60초 간격 | `MarketDataProvider.get_quote(symbol, now)` | 감시 종목 급등락 알림 |

## 공통 원칙
- 모든 외부 호출은 HTTPS를 사용한다.
- 모든 시각 필드는 timezone-aware ISO 8601 문자열이어야 한다.
- provider adapter는 외부 응답을 받아 현재 코드 타입으로 정규화한 뒤 반환한다.
- 타임아웃 기본값은 `5초`, 최대 `10초`를 넘기지 않는다.
- 내부 재시도는 최대 1회까지만 허용한다. 무한 재시도나 장시간 blocking은 금지한다.
- 인증 정보는 환경변수로만 주입하고 로그에 출력하지 않는다.
- 실패 시 scheduler가 `failed` 또는 `skipped`로 기록할 수 있도록 짧고 원인 중심의 예외 메시지를 반환한다.
- watch quote는 호출 빈도가 높으므로, 가능하면 배치 조회를 지원하거나 1 poll cycle 내 캐시를 둔다.

## 권장 환경변수
- `INTEL_API_BASE_URL`
- `INTEL_API_TOKEN`
- `INTEL_API_TIMEOUT_SECONDS=5`
- `INTEL_API_RETRY_COUNT=1`
- `WATCH_QUOTE_BATCH_SIZE=50`

벤더별 키가 따로 필요하면 아래처럼 기능별로 분리할 수 있다.
- `NEWS_API_KEY`
- `EOD_API_KEY`
- `MARKET_DATA_API_KEY`

## 1) 뉴스 브리핑 API

### 용도
- `NewsProvider.fetch(now)`를 대체한다.
- 스케줄러는 국내(`domestic`) 최대 20건, 해외(`global`) 최대 20건까지 사용한다.
- 현재 포럼 게시물은 국내/해외를 하나의 본문에 합치지 않고, region별 daily post 2개로 렌더링할 수 있다.
- 같은 뉴스 fetch 결과의 넓은 후보군으로 별도 `trendbriefing` thread를 만들 수 있으며, 이 thread는 국내/해외 테마 섹션을 하위 message로 분리해 관리할 수 있다.
- dedup 기준은 `region + source + title + link` 조합이므로, 같은 뉴스는 필드가 안정적으로 유지돼야 한다.

### 정규화 엔드포인트
- `GET /v1/news/briefing`

### 요청 파라미터
- `as_of`: 기준 시각, ISO 8601
- `regions`: `domestic,global`
- `limit_per_region`: 기본 `20`, 최대 `20`
- `published_within_hours`: 기본 `24`

### 응답 예시
```json
{
  "generated_at": "2026-03-17T07:29:30+09:00",
  "items": [
    {
      "title": "한국 수출지표 개선 기대",
      "link": "https://news.example.com/article/123",
      "source": "Example News",
      "published_at": "2026-03-17T06:58:00+09:00",
      "region": "domestic"
    },
    {
      "title": "Fed 위원 발언에 채권금리 혼조",
      "link": "https://news.example.com/article/456",
      "source": "Example Global",
      "published_at": "2026-03-17T06:41:00+09:00",
      "region": "global"
    }
  ]
}
```

### 필드 규칙
- `title`: 필수, 빈 문자열 금지
- `link`: 필수, 절대 URL
- `source`: 필수, 사람이 읽을 수 있는 소스명
- `published_at`: 필수, timezone-aware
- `region`: 필수, `domestic | global`

### 운영 규칙
- 정렬은 최신순 권장
- 해당 구간 뉴스가 없으면 `items: []`로 반환하고 200 응답을 사용한다
- 일부 필드 누락 데이터는 adapter에서 제외하고 경고 수준 로그만 남긴다
- adapter 내부에서 trend theme 후보 분석을 하더라도, 메인 브리핑용 기사 선별 결과와 분리해 conservative briefing 품질을 우선 유지한다

## 2) 장마감 요약 API

### 용도
- `EodSummaryProvider.get_summary(now)`를 대체한다.
- KRX 거래일 마감 후 한국장 데이터만 다룬다.

### 정규화 엔드포인트
- `GET /v1/markets/kr/eod-summary`

### 요청 파라미터
- `date`: `YYYY-MM-DD`

### 응답 예시
```json
{
  "date_text": "2026-03-17",
  "kospi_change_pct": 0.82,
  "kosdaq_change_pct": -0.27,
  "top_gainers": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "change_pct": 4.2,
      "turnover_billion_krw": 1300.5
    }
  ],
  "top_losers": [
    {
      "symbol": "068270",
      "name": "셀트리온",
      "change_pct": -2.9,
      "turnover_billion_krw": 250.1
    }
  ],
  "top_turnover": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "change_pct": 4.2,
      "turnover_billion_krw": 1300.5
    }
  ]
}
```

### 필드 규칙
- `date_text`: 필수, 장 마감 기준 날짜
- `kospi_change_pct`: 필수, 전일 대비 %
- `kosdaq_change_pct`: 필수, 전일 대비 %
- `top_gainers`, `top_losers`, `top_turnover`: 배열, 데이터가 있으면 최소 5건 권장
- 각 row 필드:
1. `symbol`: 필수, 종목코드 문자열
2. `name`: 필수, 종목명
3. `change_pct`: 필수, 전일 대비 %
4. `turnover_billion_krw`: 필수

### 단위 주의사항
- 현재 코드 필드명은 `turnover_billion_krw`지만, 렌더링은 `억` 단위로 출력한다.
- 실사용 전환 시 이 필드는 우선 `억원` 값으로 정규화해 기존 출력과 맞춘다.
- 추후 타입명을 바꾸더라도, 그 변경은 별도 코드 수정과 함께 진행한다.

### 운영 규칙
- 거래정지/데이터 누락 종목은 응답에서 제외할 수 있다
- 마감 데이터가 아직 확정되지 않았으면 `409` 또는 `425` 대신, adapter에서 재시도 가능한 예외로 변환한다
- 거래일이 아니면 scheduler가 먼저 skip 하므로, API는 일반적으로 거래일 기준 응답만 제공하면 된다

## 3) Watch Quote API

### 용도
- `MarketDataProvider.get_quote(symbol, now)`를 대체한다.
- watch forum-thread rollout 기준으로 scheduler는 `current_price`뿐 아니라 `previous_close`, `session_date`, close finalization용 official regular close price도 필요로 한다.
- slash command 입력은 종목명/코드/티커를 모두 받을 수 있지만, provider adapter에 들어가는 값은 local registry를 거친 canonical symbol이다.

### 정규화 엔드포인트
- `GET /v1/markets/quotes`

### 요청 파라미터
- `symbols`: 쉼표로 구분한 종목코드 목록
- `as_of`: 기준 시각, ISO 8601

### 응답 예시
```json
{
  "quotes": [
    {
      "symbol": "KRX:005930",
      "price": 73100.0,
      "previous_close": 70900.0,
      "session_close_price": null,
      "session_date": "2026-03-17",
      "asof": "2026-03-17T10:05:00+09:00"
    },
    {
      "symbol": "NAS:AAPL",
      "price": 214.37,
      "previous_close": 208.52,
      "session_close_price": null,
      "session_date": "2026-03-16",
      "asof": "2026-03-16T15:55:00-04:00"
    }
  ]
}
```

### 필드 규칙
- `symbol`: 필수, canonical symbol 문자열 권장 (`KRX:005930`, `NAS:AAPL`)
- `price`: 필수, `> 0`
- `previous_close`: 필수, `> 0`
- `session_close_price`: nullable number. regular session open 중에는 `null` 또는 생략 가능하지만, close finalization용 same-session off-hours snapshot에서는 official regular-session close price로 제공돼야 한다
- `session_date`: 필수, market-local trading session date (`YYYY-MM-DD`)
- `asof`: 필수, timezone-aware

### 운영 규칙
- 현재 구현은 종목별 단건 호출 구조지만, 실사용에서는 batch 조회 adapter를 우선 권장한다
- command 레이어는 live vendor search를 호출하지 않고 local registry 검색 + autocomplete로 후보를 좁힌다
- 미국 상장사 master의 authoritative base는 `SEC company_tickers_exchange.json`, 국내 상장사 master는 `OpenDART corpCode.xml`을 우선한다
- 국내 structured product master는 KRX finder(`ETF`, `ETN`, `ELW`, `PF`)를 함께 사용한다
- daily refresh는 live source를 직접 다시 fetch한 full rebuild가 성공했을 때만 runtime override artifact를 교체한다
- 응답에 없는 종목은 adapter에서 `not-found:<symbol>` 형태 예외로 변환한다
- quote 지연이 길면 잘못된 알림이 나갈 수 있으므로 허용 지연은 2분 이내를 권장한다
- `previous_close`와 `session_date`는 같은 snapshot 기준으로 일관되게 제공돼야 한다
- watch forum-thread rollout에서는 intraday 기준가를 `previous_close`로 고정한다
- `session_date`는 symbol market의 regular-session trading date를 뜻하며, watch band ladder 및 close finalization reset 기준으로 사용한다
- target watch forum-thread model에서는 `+3%`, `+6%`, `+9%` 및 `-3%`, `-6%`, `-9%` 같은 `3% band` ladder를 계산한다
- external payload의 `price`는 internal watch scheduler의 `WatchSnapshot.current_price`로 정규화된다
- external payload의 `session_close_price`는 internal watch scheduler의 `WatchSnapshot.session_close_price`로 정규화된다
- close finalization에 사용되는 `마감가`는 after-hours `price`가 아니라 `session_close_price`여야 한다
- provider가 quote payload에 official close를 직접 싣지 못하면 adapter는 별도 종가 endpoint 또는 추가 조회를 통해 `session_close_price`를 보강해야 한다

## 오류 응답 규칙

### HTTP 상태 코드
- `400`: 잘못된 파라미터
- `401` 또는 `403`: 인증 실패
- `404`: 존재하지 않는 리소스 또는 종목
- `429`: rate limit
- `500` 이상: 외부 공급자 또는 adapter 내부 오류

### 오류 응답 예시
```json
{
  "error": {
    "code": "rate_limit",
    "message": "quote provider limit exceeded",
    "retry_after_seconds": 30
  }
}
```

### adapter 처리 원칙
- `429`: 짧은 예외 메시지로 변환하고 provider status에 남긴다
- `5xx`: 일시 장애로 간주하고 최대 1회 재시도 후 실패 처리한다
- 영구 오류(`401`, `403`, 잘못된 symbol`)는 즉시 실패 처리한다

## 구현 순서 제안
1. `MarketDataProvider`: 호출 빈도가 가장 높아 운영 리스크가 크므로 batch quote부터 구현
2. `EodSummaryProvider`: 한국장 종가 기준 데이터 확보 후 포럼 업서트 검증
3. `NewsProvider`: 소스 다양성과 dedup 품질을 맞추며 운영 적용

## 완료 기준
- 적어도 한 개의 실제 외부 provider 또는 중간 adapter가 이 계약을 만족한다
- `/source-status`에서 각 provider의 성공/실패 상태가 의미 있게 드러난다
- 뉴스/장마감/watch 스케줄이 mock 없이 1회 이상 실운영 검증된다
