# Current Goals

## North Star
- 길드별 포럼에 한국장/미국장 히트맵을 안정적으로 자동 게시하고, 운영자가 상태를 빠르게 파악할 수 있는 Discord 봇으로 운영한다.

## Current Goals

### 1) 확장 스케줄 실사용 전환
- Goal: 뉴스 브리핑, 장마감 요약, watchlist 알림 스케줄을 mock 단계에서 실제 외부 API 기반 운영 단계로 전환한다.
- Why:
1. 새로 추가된 스케줄 기능은 이미 사용자 가치가 있지만, 현재 provider가 mock 구현이라 실제 운영 데이터가 아니다.
2. 벤더 선택 전에 공통 계약을 먼저 고정해야 구현 방향과 장애 대응 기준이 세션마다 흔들리지 않는다.
3. watchlist 폴링은 반복 호출 특성이 있어 인증, 응답 스키마, 타임아웃, rate limit 기준이 선행돼야 한다.
- Done when:
1. `docs/specs/external-intel-api-spec.md` 기준 외부 API 계약이 확정된다.
2. `NewsProvider`, `EodSummaryProvider`, `MarketDataProvider` 중 최소 1개 이상이 실제 API로 대체된다.
3. 실패/지연/rate limit 대응 정책과 운영용 환경변수 구성이 문서 및 구현에 반영된다.
- Status: active

### 2) 운영 안정화
- Goal: 봇이 실제 운영 환경에서 안정적으로 기동되고 슬래시 커맨드가 정상 동기화된다.
- Why:
1. 최근 커맨드 동기화 실패 원인 안내와 상태 기록을 추가했지만, 실제 봇 기동 확인이 아직 남아 있다.
2. 자동 스케줄과 포럼 업서트는 부트 성공 여부에 직접 의존한다.
- Done when:
1. `python -m bot.main` 기준 부트 성공
2. `/kheatmap`, `/usheatmap`, `/setforumchannel` 노출 확인
3. `/last-run` 또는 `/health`에서 `command-sync` 상태 확인 가능
- Status: active

### 3) 히트맵 게시 흐름 실운영 검증
- Goal: 길드별 포럼 매핑, 캐시 재사용, 일일 포스트 upsert 흐름을 실제 서버에서 검증한다.
- Why:
1. 현재 핵심 가치가 히트맵 게시 자동화에 있다.
2. 명령어는 구현돼 있어도 운영 권한/채널 설정/캐시 동작은 실제 서버에서 확인해야 한다.
- Done when:
1. `/setforumchannel` 매핑이 저장된다.
2. `/kheatmap` 1회 실행으로 포스트 생성
3. 같은 날 재실행 시 기존 포스트 수정 확인
- Status: active

### 4) 자동 스케줄 신뢰도 확보
- Goal: 거래일 판정과 자동 스크린샷 스케줄이 기대한 날짜/시간에만 동작하는지 확신을 높인다.
- Why:
1. 일요일 `kheatmap` 조사 리포트가 있었고, 다중 런타임/배포 불일치 가능성이 확인됐다.
2. 운영 신뢰도는 스케줄 정확성에 크게 좌우된다.
- Done when:
1. 로그로 `reason=holiday` / `reason=calendar-check-failed` / success 흐름을 구분 가능
2. 동일 토큰 다중 실행 여부와 배포 이미지 상태를 점검
3. 필요 시 `data/state/state.json`과 런타임 로그로 마지막 실행 상태를 추적 가능
- Status: active

### 5) 운영 가시성 강화
- Goal: 운영자가 Discord 안에서 마지막 작업 상태와 소스 상태를 빠르게 확인할 수 있게 한다.
- Why:
1. `/health`, `/last-run`, `/source-status`가 이미 생겼고, 최근 `command-sync` 상태 기록도 추가됐다.
2. 문제 발생 시 서버 콘솔 없이도 1차 진단이 가능해야 한다.
- Done when:
1. 주요 background job 결과가 `system.job_last_runs`에 남는다.
2. 운영자가 Discord 명령만으로 최근 실패 원인을 확인할 수 있다.
- Status: active

## Secondary Goals

### 6) 세션 간 판단 일관성 유지
- Goal: 여러 Codex 세션에서도 같은 기준으로 검토, 개발, 설계를 이어간다.
- Why:
1. 이미 컨텍스트 허브와 바이브 코딩 운영 규칙을 도입했다.
2. 목표가 문서화되지 않으면 우선순위가 세션마다 흔들릴 수 있다.
- Done when:
1. 큰 작업 후 `docs/context/*`가 계속 갱신된다.
2. 다음 세션이 `session-handoff.md`와 이 문서만 읽어도 우선순위를 복구할 수 있다.
- Status: active

## Not In Scope Right Now
- 배포 인프라 대수술
- 월간/연간 스케줄 체계 확장
- 대규모 UI 작업
