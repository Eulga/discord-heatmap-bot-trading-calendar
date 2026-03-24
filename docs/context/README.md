# Context Hub

이 디렉터리는 세션별 흔들림을 줄이기 위한 프로젝트 작업 메모 허브다.

## 읽기 순서
1. `CURRENT_STATE.md`
2. `session-handoff.md`
3. `goals.md`
4. 리뷰 작업이면 `review-rules.md`
5. 현재 구현 세부 확인이 필요하면 `../specs/as-is-functional-spec.md`
6. 확장 스케줄 목표 계약이 필요하면 `../specs/external-intel-api-spec.md`
7. 필요 시 `operating-rules.md`
8. 필요 시 `design-decisions.md`
9. 필요 시 `development-log.md`
10. 필요 시 `review-log.md`
11. 오래된 handoff가 필요하면 `session-history.md`

## 문서 역할
- `CURRENT_STATE.md`: 짧은 현재 상태 요약과 canonical doc map
- `session-handoff.md`: 최신 active handoff
- `session-history.md`: 오래된 handoff archive
- `goals.md`: 현재 프로젝트 목표와 우선순위
- `operating-rules.md`: 프로젝트 운영/문서 경계 규칙
- `review-rules.md`: 반복 실수를 막기 위한 리뷰 규칙
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
- 2026-03-17: 뉴스/장마감/watch의 현재 구현 확인은 `../specs/as-is-functional-spec.md`를, 향후 목표 계약 확인은 `../specs/external-intel-api-spec.md`를 본다.
- 2026-03-18: 리뷰 작업은 `docs/context/review-rules.md`를 기준으로 누적 강화한다.
