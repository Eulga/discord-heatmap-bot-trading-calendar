# Context Hub

이 디렉터리는 세션별 흔들림을 줄이기 위한 프로젝트 작업 메모 허브다.

## 읽기 순서
1. `session-handoff.md`
2. `goals.md`
3. 확장 스케줄 작업이면 `../specs/external-intel-api-spec.md`
4. 필요 시 `design-decisions.md`
5. 필요 시 `development-log.md`
6. 필요 시 `review-log.md`

## 문서 역할
- `session-handoff.md`: 지금 당장 알아야 하는 현재 상태
- `goals.md`: 현재 프로젝트 목표와 우선순위
- `design-decisions.md`: 왜 이렇게 설계했는지에 대한 기준
- `development-log.md`: 무엇을 구현했고 무엇을 검증했는지
- `review-log.md`: 어떤 리스크와 결함이 있었는지

## 기록 규칙
- 항목은 최신순으로 추가한다.
- 날짜는 `YYYY-MM-DD` 형식으로 쓴다.
- 가능한 한 다음 필드를 유지한다:
1. `Context`
2. `Decision` 또는 `Finding`
3. `Why`
4. `Next`
5. `Status`
- 작업 사실과 판단을 구분해서 쓴다.
- 민감 정보는 기록하지 않는다.

## 현재 운용 메모
- 2026-03-17: 컨텍스트 분류 저장 체계를 신설했다.
- 2026-03-17: 뉴스/장마감/watch 실사용 전환은 `docs/specs/external-intel-api-spec.md`를 우선 기준으로 삼는다.
