# Review Rules

이 문서는 반복해서 놓친 리뷰 포인트를 운영 규칙으로 고정하는 문서다.

## 사용 원칙
- 항목은 최신순으로 추가한다.
- 각 규칙은 `Rule`, `Why`, `Must`, `Done when`을 포함한다.
- 규칙은 가능한 한 실제로 놓친 사례에서만 추가한다.
- 리뷰 중에는 칭찬보다 이 문서 규칙 충족 여부를 먼저 본다.

## Rule 1) 실패 경로와 운영 정합성까지 리뷰한다
- Added: 2026-03-18
- Why:
1. 2026-03-17 `develop` 리뷰에서 `intel_scheduler`의 성공 경로는 봤지만, 게시 실패 재시도와 job status 거짓 양성, Docker 로그 영속성, README/hand-off 오차는 놓쳤다.
2. 이 프로젝트는 Discord 명령, background job, Docker 운영, 컨텍스트 문서가 함께 움직여서 코드만 맞아도 운영은 틀릴 수 있다.
- Must:
1. background job, scheduler, sync, health/status 관련 코드는 반드시 `success`, `skipped`, `failed`, `no-target` 경로를 모두 확인한다.
2. 상태 기록(`job_last_runs`, provider status, health 응답)은 실제 부수효과와 일치하는지 확인한다. 실제 게시/전송/저장이 없으면 `ok`를 의심한다.
3. 실행 방법이나 운영 결과가 바뀌는 변경이면 `README.md`, `AGENTS.md`, `docs/context/session-handoff.md`, `docker-compose.yml` 또는 관련 런북을 함께 대조한다.
4. 실패 경로에서 재시도 가능성이 있는 로직은 "실패 후 같은 입력으로 재실행해도 회복 가능한지"를 본다.
5. 위 범주의 결함을 찾았으면 관련 회귀 테스트가 있는지 확인하고, 없으면 추가 필요를 명시한다.
- Done when:
1. 리뷰 메모에 실패 경로 확인 여부가 남아 있다.
2. 운영 문서와 실제 실행 경로가 어긋나지 않는다.
3. 상태/헬스 신호가 실제 동작 결과와 일치한다.
