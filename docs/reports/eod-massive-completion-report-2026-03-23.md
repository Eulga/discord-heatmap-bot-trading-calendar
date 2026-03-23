# `eod_summary` + Massive fallback completion report

작성일: 2026-03-23

## 1. 목적

이 문서는 현재 저장소 기준으로 아래 두 항목을 "완성" 상태로 올리기 위해 필요한 선행조건, 구현 작업, 검증 작업, 운영 리스크를 정리한다.

1. `eod_summary` live provider 구현 + 실제 Discord forum smoke
2. 미국 종목 `watch_poll`의 Massive fallback live 검증

## 2. 현재 상태 요약

### 2.1 `eod_summary`

- scheduler job, forum upsert, body renderer, failure semantics, integration test는 이미 있다.
- 하지만 실제 provider는 아직 `MockEodSummaryProvider()`에 고정돼 있다.
- `/source-status`에서는 `eod_provider`가 기본적으로 `paused`로 보이도록 되어 있고, `.env.example`도 `EOD_SUMMARY_ENABLED=false`를 기본값으로 둔다.
- 즉 "실행 프레임"은 준비돼 있지만, 실제 데이터 소스 연결과 운영 검증이 비어 있다.

### 2.2 Massive fallback

- `RoutedMarketDataProvider`가 이미 들어가 있고, `MARKET_DATA_PROVIDER_KIND=kis`일 때 KIS를 primary로 사용한다.
- 미국 종목(`NAS/NYS/AMS`)은 `MASSIVE_API_KEY`가 있으면 `MassiveSnapshotMarketDataProvider`를 fallback으로 시도한다.
- 단위/통합 테스트와 국내 KIS live smoke는 이미 통과했다.
- 현재 남은 blocker는 Massive snapshot entitlement와 "실제로 fallback path가 탔다"는 live 증명이다.

## 3. 1번 완료에 필요한 것: `eod_summary` live provider

### 3.1 이미 준비된 것

- 스케줄러 job: `bot/features/intel_scheduler.py`
- 출력 포맷: `bot/features/eod/policy.py`
- EOD 타입: `bot/intel/providers/market.py`의 `EodSummary`, `EodRow`
- partial post failure, holiday skip, forum resolution failure, same-day idempotency 회귀 테스트

즉, provider만 붙이면 되는 수준까지 주변 계약은 이미 정리돼 있다.

### 3.2 반드시 필요한 선행 결정

1. `EOD` 실데이터 소스를 확정해야 한다.
   - 현재 repo 문서 기준 1차 후보는 `KIS Open API`, 보강 후보는 `OpenDART`다.
   - `docs/reports/mvp-data-source-review-2026-03-12.md`도 같은 방향을 추천한다.

2. provider 범위를 먼저 좁혀야 한다.
   - 1차 완료 기준은 `KOSPI/KOSDAQ 등락률 + 상승 상위 5 + 하락 상위 5 + 거래대금 상위 5`만 안정적으로 채우는 것이다.
   - `OpenDART` 공시 enrich는 2차로 미뤄도 된다.

3. 단일 provider인지 composite인지 결정해야 한다.
   - 가장 현실적인 1차안: `KisEodSummaryProvider`
   - 더 확장성 있는 2차안: `CompositeEodSummaryProvider(KIS + OpenDART optional enrich)`

### 3.3 외부 전제조건

1. KIS에서 `EodSummary`를 채울 endpoint 조합을 확정해야 한다.
   - 공식 KIS API 카탈로그에는 국내주식 현재가/순위분석과 `국내주식 등락률 순위`가 노출돼 있다.
   - 다만 현재 코드가 요구하는 `지수 2개 + 상승/하락/거래대금 상위 5`를 한 번에 일관되게 채우는 정확한 endpoint 조합은 repo 문서에서도 아직 "확인 필요"로 남아 있다.

2. 운영 사용 형태를 확인해야 한다.
   - KIS 제휴안내에는 "제3자에게 서비스를 제공하는 법인"과 "시장정보 이용계약" 관련 안내가 있다.
   - 이 봇을 본인용이 아니라 여러 사용자/길드에 제공한다면, 계정/제휴 범위가 사용 형태와 맞는지 먼저 점검해야 한다.

### 3.4 코드 작업

1. `EOD_PROVIDER_KIND` 같은 선택 키를 추가하거나, 최소한 `_build_eod_summary_provider()`를 도입해야 한다.
   - 현재는 `eod_provider = MockEodSummaryProvider()`가 module scope에 고정돼 있다.
   - `watch_poll`과 같은 수준의 builder 구조로 맞춰야 mock/live 전환이 안전해진다.

2. live provider를 구현해야 한다.
   - 후보 이름: `KisEodSummaryProvider`
   - 위치는 현재 구조상 `bot/intel/providers/market.py`에 두는 편이 가장 저렴하다.

3. provider가 해결해야 하는 데이터 정규화 항목
   - 날짜 문자열
   - `kospi_change_pct`
   - `kosdaq_change_pct`
   - `top_gainers`
   - `top_losers`
   - `top_turnover`
   - 거래대금 단위 정규화

4. provider 상태키를 현재 status 화면과 맞춰야 한다.
   - 지금은 `eod_provider`라는 일반 키만 있다.
   - live 연결 후에는 `configured`, `ok`, `failed`, `paused`가 분명히 구분돼야 한다.

5. readiness/not-ready 처리 기준이 필요하다.
   - 16:20 KST에 돌릴 때 종가/순위 데이터가 아직 확정 전일 수 있다.
   - 이런 경우 `failed`로 남길지, 재시도 가능한 일시 상태로 남길지 먼저 정해야 한다.

### 3.5 테스트와 smoke

1. provider unit test가 추가돼야 한다.
   - 정상 응답 정규화
   - 일부 랭킹 데이터 누락
   - 비정상 지수 응답
   - 장마감 확정 전 응답
   - rate-limit / auth / unreachable

2. scheduler integration test가 추가돼야 한다.
   - live provider builder
   - credential missing 시 status/detail
   - `EOD_SUMMARY_ENABLED=true`일 때 `/source-status` 반영

3. 실제 Discord smoke가 필요하다.
   - `EOD_TARGET_FORUM_ID` 또는 길드별 `/seteodforum` 준비
   - 실제 KRX 거래일 마감 후 1회 run
   - thread 생성/업데이트 확인
   - `/source-status`와 `/last-run`에서 `eod_summary=ok` 확인

### 3.6 1번의 실제 blocker

`eod_summary`는 코드 양보다 "정확한 데이터 조합 확정"이 blocker다. 지금 부족한 것은 프레임이 아니라 아래 두 가지다.

1. KIS endpoint 조합 확정
2. live smoke를 할 수 있는 실제 운영 시간대 검증

## 4. 2번 완료에 필요한 것: Massive fallback live 검증

### 4.1 이미 준비된 것

- `MassiveSnapshotMarketDataProvider` 구현 완료
- `RoutedMarketDataProvider` 구현 완료
- `massive_reference` status row 반영 완료
- 단위 테스트 완료
- 통합 테스트 완료
- Massive reference fetch는 이미 live 확인 완료

즉, 2번은 "구현 미완성"보다 "계정 entitlement + live 증명 미완성"에 가깝다.

### 4.2 외부 전제조건

1. Massive plan에서 snapshot 경로에 필요한 데이터 권한이 있어야 한다.
   - 2026-03-23 기준 Massive pricing page는 `Stocks Starter`와 `Stocks Developer`가 `15-minute Delayed Data + Snapshot`을, `Stocks Advanced`가 `Real-time Data + Snapshot`을 제공한다고 안내한다.
   - 현재 코드에서 필요한 것은 `lastTrade` 기반 freshness가 살아 있는 snapshot이므로, 실질적으로는 real-time 접근 권한이 필요하다.

2. account classification / usage scope를 확인해야 한다.
   - Massive pricing은 개인용 stocks 플랜을 `Individual use`와 `Non-pros only`로 설명한다.
   - Massive market data terms는 실시간 equities market data에 Nasdaq/NYSE subscriber agreement가 연결된다고 명시한다.
   - 이 봇이 개인용을 넘는 운영 형태라면, business pricing이나 추가 expansion이 필요한지 먼저 확인해야 한다.

3. 현재 계정에서 실제 blocker가 재현돼 있다.
   - 현재 env key 기준 direct snapshot call이 `massive-entitlement-required`로 끝난다.
   - 이 상태에서는 코드 경로가 있어도 live fallback 완료로 볼 수 없다.

### 4.3 코드/검증 작업

1. Massive entitlement가 열린 API key로 다시 확인해야 한다.
   - direct snapshot call에서 `lastTrade.p`, `lastTrade.t`가 정상 응답하는지
   - stale check를 통과하는지

2. fallback path를 의도적으로 태우는 smoke 방법이 필요하다.
   - 현재 `RoutedMarketDataProvider`는 KIS primary가 성공하면 Massive를 호출하지 않는다.
   - 따라서 단순히 미국 종목 watch를 등록하는 것만으로는 fallback이 검증되지 않는다.
   - live 검증은 아래 둘을 분리해야 한다.
     1. `MassiveSnapshotMarketDataProvider` direct smoke
     2. failing primary를 둔 routed smoke 또는 controlled fallback harness

3. fallback 결과가 실제 watch 상태에 반영되는지 확인해야 한다.
   - provider status가 `massive_reference`로 남는지
   - alert message가 실제로 발송되는지
   - failure detail이 `kis_quote:... | massive_reference:...` 형식으로 운영자가 읽을 수 있는지

### 4.4 추가로 필요한 운영 준비

1. 미국 종목 smoke symbol을 하나 고정해야 한다.
   - 예: `NAS:AAPL`
   - registry에 이미 있고 Massive snapshot 응답이 안정적인 종목이 적합하다.

2. alert 경로는 이미 국내 watch smoke에서 검증됐지만, 미국 fallback 전용 smoke는 따로 남겨야 한다.
   - watch 추가
   - baseline 강제 조정 또는 controlled threshold breach
   - send 확인 후 cleanup

3. Massive 429/403 운영 메시지를 마지막으로 점검해야 한다.
   - entitlement 부족
   - auth failure
   - rate limit
   - stale quote

### 4.5 2번의 실제 blocker

2번은 현재 사실상 외부 blocker 하나가 핵심이다.

1. Massive snapshot real-time entitlement가 붙은 key 확보

그 다음 blocker는 기술 구현이 아니라 검증 설계다.

2. fallback이 "우연히" 아니라 "의도적으로" 발동됐다는 live 증명 절차 확보

## 5. 권장 실행 순서

1. `eod_summary` 1차 범위를 `KIS only`로 고정
2. KIS endpoint 조합 확정
3. `_build_eod_summary_provider()` + `KisEodSummaryProvider` 구현
4. unit/integration test 추가
5. 실제 EOD forum smoke
6. Massive entitlement가 붙은 key 확보
7. direct Massive snapshot smoke
8. controlled fallback smoke
9. `/source-status`, `/last-run`, Discord alert까지 운영 증적 남기기

## 6. 우선순위 판단

완성 난이도는 1번이 더 높다.

- 1번 `eod_summary`: 중간 이상 구현 작업이 남아 있다.
- 2번 Massive fallback: 코드보다 계정 권한과 live 검증 절차가 핵심이다.

따라서 순서는 아래가 맞다.

1. 지금 당장 팀이 통제 가능한 작업: `eod_summary` 구현
2. 외부 계정 상태에 의존하는 작업: Massive fallback live 완료

## 7. 완료 기준

### 7.1 `eod_summary`

아래가 모두 충족되면 완료로 본다.

1. mock provider 제거 또는 builder 뒤로 격리
2. live EOD provider가 `EodSummary`를 안정적으로 채움
3. `/source-status`에서 provider가 configured/ok로 보임
4. 실제 거래일 1회 forum post smoke 성공
5. 관련 실패/partial failure 회귀 테스트 통과

### 7.2 Massive fallback

아래가 모두 충족되면 완료로 본다.

1. direct Massive snapshot live fetch 성공
2. routed fallback이 controlled 방식으로 실제 발동
3. `massive_reference` status가 runtime에 기록
4. 미국 종목 watch alert smoke 성공
5. cleanup 후 state/channel이 원복

## 8. 참고 소스

로컬 소스:

- `bot/features/intel_scheduler.py`
- `bot/intel/providers/market.py`
- `bot/features/eod/policy.py`
- `docs/specs/external-intel-api-spec.md`
- `docs/reports/mvp-data-source-review-2026-03-12.md`

공식 소스:

- KIS Developers API 포털: <https://apiportal.koreainvestment.com/>
- KIS API 서비스 카탈로그: <https://apiportal.koreainvestment.com/apiservice>
- KIS 제휴안내: <https://apiportal.koreainvestment.com/provider>
- Massive pricing: <https://massive.com/pricing?product=stocks>
- Massive single ticker snapshot docs: <https://massive.com/docs/rest/stocks/snapshots/single-ticker-snapshot>
- Massive business pricing: <https://massive.com/business>
- Massive market data terms: <https://massive.com/terms/market_data_terms.pdf>
