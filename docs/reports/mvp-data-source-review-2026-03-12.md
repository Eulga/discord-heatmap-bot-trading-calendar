# MVP 데이터 소스 운영 전환 검토 리포트

작성일: 2026-03-12  
대상 프로젝트: `discord-heatmap-bot-trading-calendar`

## 1. 결론 요약

현재 코드 구조와 MVP 범위를 기준으로 보면, 제안하신 방향은 전체적으로 타당하다. 다만 실제 운영 전환 우선순위는 아래처럼 잡는 것이 가장 안전하다.

1. `watch poll`과 `국내 시세`는 가장 먼저 `KIS Open API`로 교체
2. `국내 뉴스 브리핑`은 `네이버 검색 API(뉴스 검색)`로 교체
3. `거래일 판정`은 현재 `exchange_calendars`를 유지하되, 공식 소스 확인 레이어를 추가하는 2중화로 전환
4. `장마감 요약`은 KIS를 1차 후보로 두되, 현재 코드가 요구하는 `상승/하락/거래대금 상위 5`를 한 번에 채우는 API 조합은 구현 전 문서 확인이 더 필요
5. `공시 보강`은 `OpenDART`를 후속 enrichment 레이어로 추가
6. `미국 watch/news`는 `Massive`(구 `Polygon.io`)를 우선 추천하고, Finnhub는 대안으로 보류
7. `한국 heatmap`은 단기적으로 현행 캡처 유지, 중기적으로 자체 렌더 전환

핵심 판단은 다음과 같다.

- 이 저장소에서 가장 먼저 mock을 제거해야 하는 곳은 `bot/features/intel_scheduler.py`의 `quote_provider`다.
- `news_provider`는 네이버 API로 바꾸기 쉽다.
- `eod_provider`는 "지수 + 랭킹 + 거래대금" 요구사항 때문에 시세 API 하나만 붙인다고 끝나지 않는다.
- 거래일 판정은 공식 페이지 단독 파싱보다 현재 라이브러리 기반 fallback을 유지하는 편이 운영 안정성에 유리하다.

## 2. 현재 코드 기준 실제 연결 포인트

현재 저장소에서 외부 데이터 소스가 붙는 지점은 이미 분리되어 있다.

### 2.1 시세 / 장마감

파일: `bot/intel/providers/market.py`

- `MarketDataProvider.get_quote(symbol, now)`
- `EodSummaryProvider.get_summary(now)`

실제 소비 지점:

- `bot/features/intel_scheduler.py`
  - `_run_watch_poll()`에서 `quote_provider.get_quote(...)` 호출
  - `_run_eod_job()`에서 `eod_provider.get_summary(...)` 호출

따라서 운영 전환 시 가장 자연스러운 순서는 아래다.

1. `MockMarketDataProvider`를 실제 `KisMarketDataProvider`로 교체
2. `MockEodSummaryProvider`를 실제 `KisEodSummaryProvider` 또는 `CompositeEodSummaryProvider`로 교체

### 2.2 뉴스

파일: `bot/intel/providers/news.py`

- `NewsProvider.fetch(now) -> list[NewsItem]`

실제 소비 지점:

- `bot/features/intel_scheduler.py`의 `_run_news_job()`

따라서 국내/해외 뉴스를 분리한 뒤 합쳐서 반환하는 구조가 가장 잘 맞는다.

- `DomesticNewsProvider`: 네이버 뉴스 검색 API
- `GlobalNewsProvider`: Massive News 또는 Finnhub 대안
- `CompositeNewsProvider`: 두 결과를 `region=domestic|global`로 표준화

### 2.3 거래일 판정

파일: `bot/markets/trading_calendar.py`

현재:

- `exchange_calendars` 기반
- `safe_check_krx_trading_day`
- `safe_check_nyse_trading_day`

이 구조는 유지하고, 내부 판정 순서를 아래처럼 바꾸는 것이 적합하다.

1. 공식 소스 확인
2. 실패 시 `exchange_calendars` fallback
3. 여전히 실패하면 현재처럼 `calendar-check-failed`

## 3. 소스별 검토 결과

## 3.1 KIS Open API

### 판단

현재 MVP에서 가장 우선 적용해야 할 실제 운영 데이터 소스다.

### 이 프로젝트에 잘 맞는 이유

- 국내주식 REST / WebSocket 모두 공식 제공
- 포털에서 국내주식 API 문서, 종목 정보 파일, 테스트 베드, GitHub 샘플을 함께 제공
- 샘플 저장소에서 국내주식 현재가 시세 조회와 WebSocket 예제가 직접 확인됨
- 현재 코드의 `get_quote()` 모델과 가장 잘 맞음

### 실제 적용 대상

- `/watch add/remove/list` 이후 자동 poll의 실시간 시세
- 향후 장 운영 상태 보강
- 장마감 요약에 필요한 기초 가격 데이터

### 이 코드에 어떻게 사용할지

1. 새 provider 클래스 추가
   - `KisMarketDataProvider`
2. 구현 책임
   - `get_quote(symbol, now)`는 KIS 현재가 REST를 1차 사용
   - polling 빈도가 높을 경우 WebSocket subscriber를 별도 캐시 레이어로 확장
3. watch poll 연결
   - `intel_scheduler.py`의 `quote_provider = MockMarketDataProvider()`를 실제 provider로 교체
4. 장애 대응
   - KIS 실패 시 provider status에 실패 기록
   - 단기적으로는 직전 baseline 유지, 알림 미발송

### 주의사항

- 인증, 토큰 발급, WebSocket approval key 관리가 필요
- 초당 호출량과 WebSocket 재연결 정책을 먼저 설계해야 함
- 실시간은 WebSocket이 맞지만, 현재 MVP는 60초 polling 구조이므로 1차는 REST로도 충분할 가능성이 높다

### 문서 확인 결과

- KIS 포털은 국내주식 API 문서와 REST/WebSocket 방식을 안내한다.
- GitHub 샘플 저장소는 국내주식 현재가 조회와 WebSocket 샘플을 제공한다.

## 3.2 OpenDART

### 판단

즉시 1차 필수는 아니지만, 운영 고도화 가치가 매우 높다.

### 이 프로젝트에 잘 맞는 이유

- 금융감독원 공식 공시 데이터 소스
- 오픈API 인증키, 개발 가이드, 주요 공시/재무정보 활용 구조가 공식 제공됨
- 뉴스 브리핑보다 "공시 기반 요약"과 장마감 보강에 적합

### 실제 적용 대상

- 장마감 요약 하단의 "오늘 주요 공시" 섹션
- 특정 watch 종목 급등락 발생 시 최근 공시 링크 보강
- 뉴스 dedup 후 마지막 단계에서 "공시 동반 여부" enrich

### 이 코드에 어떻게 사용할지

1. 별도 provider 계층 추가
   - 예: `DisclosureProvider`
2. 1차 범위
   - `corp_code` 매핑 캐시
   - 최근 공시 조회
3. 적용 위치
   - `_run_eod_job()` 본문 생성 직전
   - `_run_watch_poll()` 알림 직전 optional enrichment

### 주의사항

- 종목코드와 DART 고유번호 매핑 테이블이 필요
- 공시 수집은 시세 API보다 응답 지연 허용 범위가 넓으므로 비동기 후행 enrich가 적합

## 3.3 네이버 뉴스 검색 API

### 판단

국내 뉴스 브리핑의 1순위 후보로 적합하다.

### 이 프로젝트에 잘 맞는 이유

- 공식 검색 API에서 `news` 엔드포인트를 제공
- JSON/XML 반환 가능
- 검색 API 계열은 하루 25,000회 한도가 공개되어 있음
- 현재 `NewsItem` 모델로 매핑하기 쉽다

### 실제 적용 대상

- 아침 뉴스 브리핑의 국내 뉴스 5건
- 특정 키워드 기반 경제/증시 뉴스 집계

### 이 코드에 어떻게 사용할지

1. `NaverDomesticNewsProvider.fetch(now)` 구현
2. 검색어 전략
   - 단일 검색어보다 다중 질의 집합 추천
   - 예: `코스피`, `코스닥`, `증시`, `환율`, `반도체`, `미국 증시`
3. 정제 규칙
   - HTML 태그 제거
   - 언론사/중복 제목 정규화
   - 발행 시각 파싱 실패 항목 제외
4. 반환 모델
   - `NewsItem(title, link, source, published_at, region="domestic")`

### 주의사항

- 검색 API이므로 "편집된 증권 뉴스 피드"가 아니다
- relevance만 믿지 말고, 키워드 세트 + 시간 필터 + 중복 제거를 직접 설계해야 함
- 언론사 쏠림과 비증권 기사 혼입 가능성이 있다

## 3.4 미국 뉴스 / 보조 시세

### 판단

현재 확인된 공식 문서 기준으로는 `Massive`(구 `Polygon.io`) 쪽이 이 저장소 MVP에 더 직접 맞는다. Finnhub는 후보로 유지하되, 이번 리포트에서는 2순위로 둔다.

### Massive를 우선 추천하는 이유

- snapshot REST가 현재 watch 구조와 잘 맞음
- stocks WebSocket docs가 명확함
- 실시간/지연 데이터 플랜 차이가 문서상 명확함
- 뉴스와 시세를 같은 공급자에서 가져가는 운영 단순화 이점이 있음

### 실제 적용 대상

- 미국 watch 확장
- 미국 뉴스 브리핑
- 미국 보조 시세

### 이 코드에 어떻게 사용할지

1. `MassiveUsMarketDataProvider`
   - 미국 종목 `get_quote()` 구현
2. `MassiveGlobalNewsProvider`
   - 미국/해외 뉴스 -> `region="global"`
3. watch 확장 시
   - 한국 종목은 KIS
   - 미국 종목은 Massive
   - 심볼 규칙과 시장 식별자 분리 필요

### 주의사항

- 무료/저가 플랜에서는 일부 데이터가 지연될 수 있다
- 현재 MVP는 국내 중심이므로 미국 watch는 2단계가 적절하다

## 3.5 거래일 캘린더

### 판단

공식 기준 + 라이브러리 fallback 2중화는 맞는 방향이다. 다만 한국장은 "공식, 안정적, 기계친화적 holiday API"를 이번 조사에서 확인하지 못했다.

### 확인된 사실

- NYSE는 공식 휴장/거래 시간 페이지를 제공하고 2026년 휴장일을 명시한다.
- KRX Global 페이지는 거래일/휴장 원칙을 제공한다.
- `pandas_market_calendars`는 NYSE 캘린더 사용 예시를 문서화한다.

### 권장 구조

1. 미국장
   - 1차: NYSE 공식 휴장표 기반 정적 캘린더 또는 주기적 동기화
   - 2차: `exchange_calendars` 또는 `pandas_market_calendars`
2. 한국장
   - 1차: KRX 공식 휴장 규칙 + 연간 휴장일 수기/배치 등록
   - 2차: 현재 `exchange_calendars`

### 이 코드에 어떻게 사용할지

- `bot/markets/trading_calendar.py`를 provider화
- 예:
  - `OfficialNyseCalendarChecker`
  - `OfficialKrxCalendarChecker`
  - `FallbackExchangeCalendarChecker`
- 최종 함수는 합성 결과만 반환

### 주의사항

- 한국장은 규칙 페이지는 확인되지만, 이 MVP에 바로 붙일 수 있는 안정적 기계형 API는 이번 검토에서 확인하지 못함
- 따라서 당장 공식 페이지 파싱을 1차로 올리기보다, 현재 라이브러리 기반을 유지하면서 별도 검증 테이블을 병행하는 편이 안전하다

## 3.6 Heatmap 소스

### 미국장

현재 운영상 가장 실용적인 방향은 "당분간 현행 유지"다.

- 지금 구조는 캡처 검증 로직이 이미 들어가 있다.
- 미국 heatmap은 외부 시각화 서비스 캡처를 유지해도 단기 운영은 가능하다.

### 한국장

중기적으로는 자체 렌더 전환이 맞다.

이유:

- 현재 한국 heatmap은 외부 DOM 구조 변경에 취약하다
- 렌더 readiness 조건을 촘촘히 써도 근본적으로 사이트 변경 리스크가 남는다
- 한국장은 시총/등락률/섹터 데이터만 확보하면 자체 treemap이 더 안정적이다

### 현재 MVP 기준 권장

- 단기: 현행 캡처 유지
- 중기: 자체 heatmap renderer 전환

## 4. 기능별 최종 권장 매핑

### 4.1 watch poll

권장:

- 국내: `KIS Open API`
- 미국 확장 시: `Massive`

실행 우선순위:

1. 최우선 교체

이유:

- 현재 mock 제거 효과가 가장 큼
- 사용자 체감이 가장 큼
- 인터페이스가 이미 `get_quote()` 하나로 단순함

### 4.2 뉴스 브리핑

권장:

- 국내: `네이버 뉴스 검색 API`
- 해외: `Massive News` 우선, Finnhub는 대안

실행 우선순위:

2순위

이유:

- `NewsProvider.fetch()`가 단순해서 교체 난이도가 낮음
- dedup 로직이 이미 있어서 소스 교체 수혜가 큼

### 4.3 장마감 요약

권장:

- 1차 후보: `KIS Open API`
- 보강: `OpenDART`

실행 우선순위:

3순위

이유:

- 단순 현재가보다 필요한 필드가 많다
- "상승/하락/거래대금 상위"가 API 하나로 닫히는지 구현 전 재확인 필요

### 4.4 거래일 판정

권장:

- 미국: NYSE 공식 + fallback 라이브러리
- 한국: 현재 `exchange_calendars` 유지 + KRX 공식 검증 레이어 추가

실행 우선순위:

4순위

이유:

- 현재 구조도 이미 충분히 안정적임
- 성급한 공식 페이지 파싱 전환은 오히려 운영 리스크가 될 수 있음

### 4.5 공시 보강

권장:

- `OpenDART`

실행 우선순위:

5순위

이유:

- 부가가치가 높지만, MVP 필수 운영 전환 1차는 아님
- 시세/뉴스 안정화 후 들어가는 것이 맞음

## 5. 실제 추진 순서 제안

### Phase 1

- `KisMarketDataProvider` 도입
- watch poll 실데이터 전환
- provider 상태/오류 로그 보강

### Phase 2

- `NaverDomesticNewsProvider` 도입
- 뉴스 브리핑 실데이터 전환
- 검색어 세트와 정제 규칙 확정

### Phase 3

- 장마감 요약에 필요한 KIS endpoint 세부 검증
- 필요 시 `CompositeEodSummaryProvider` 설계
- OpenDART 공시 enrich 추가

### Phase 4

- 미국 뉴스/시세를 Massive로 확장
- 미국 watch 지원 여부 결정

### Phase 5

- 한국 heatmap 자체 렌더 전환 검토

## 6. 최종 의사결정 제안

현재 MVP 운영 전환 기준 최종 추천 조합은 아래다.

- 국내 시세 / watch: `KIS Open API`
- 국내 뉴스: `네이버 뉴스 검색 API`
- 장마감 보강: `KIS + OpenDART`
- 미국 보조 시세 / 해외 뉴스: `Massive`
- 거래일 판정: `공식 기준 확인 + exchange_calendars fallback`
- 미국 heatmap: 현행 유지
- 한국 heatmap: 단기 캡처 유지, 중기 자체 렌더

## 7. 이번 검토에서 직접 확인한 공식/1차 문서

- KIS Developers 포털: 국내주식 API 문서, 테스트 베드, 종목 정보 파일, REST/WebSocket 방식 안내  
  <https://apiportal.koreainvestment.com/intro>
- KIS 공식 샘플 저장소: 국내주식 현재가 조회 예시, WebSocket 샘플  
  <https://github.com/koreainvestment/open-trading-api>
- OPEN DART 메인: 오픈API, XBRL, EXCEL, TXT 제공 및 인증키/개발가이드 안내  
  <https://opendart.fss.or.kr/>
- OPEN DART 개발가이드  
  <https://opendart.fss.or.kr/guide/main.do>
- NAVER Open API 종류: 뉴스 검색 endpoint 확인  
  <https://developers.naver.com/docs/common/openapiguide/apilist.md>
- NAVER Search API 계열: 검색 API 하루 25,000회 한도 확인  
  <https://developers.naver.com/docs/serviceapi/search/local/local.md>
- NYSE 공식 거래시간/휴장일  
  <https://www.nyse.com/trade/hours-calendars>
- KRX Global: 거래일/휴장 원칙  
  <https://global.krx.co.kr/contents/GLB/06/0606/0606030101/GLB0606030101T3.jsp>
- Massive docs 메인  
  <https://massive.com/docs>
- Massive Python examples / client naming (`massive`, `MASSIVE_API_KEY`)  
  <https://massive.com/blog/polygon-io-with-python-for-stock-market-data>
- Massive WebSocket + REST Python example  
  <https://massive.com/blog/pattern-for-non-blocking-websocket-and-rest-calls-in-python>
- pandas_market_calendars 문서  
  <https://pandas-market-calendars.readthedocs.io/>

## 8. 확인했지만 아직 부족한 점

아래 항목은 이번 검토에서 "후보로는 타당하지만, 이 프로젝트 구현에 바로 필요한 세부 수준까지는 확인하지 못했다."

- KIS에서 현재 `EodSummary` 구조를 바로 채울 수 있는 정확한 endpoint 조합
- KRX의 연간 휴장일을 기계적으로 안정 수집할 공식 API 또는 고정 포맷 피드
- Finnhub의 현재 공식 docs에서 Market News/quote/websocket 세부 페이지 접근성

따라서 위 3개는 구현 착수 전에 endpoint-level 확인이 한 번 더 필요하다.
