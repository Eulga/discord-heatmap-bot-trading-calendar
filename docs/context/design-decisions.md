# Design Decisions

## 2026-03-18
- Context: 반복되는 push -> PR -> merge -> branch cleanup 요청을 한 번의 Codex 요청으로 줄이고 싶었다.
- Decision: 이 저장소는 GitHub shipping workflow를 repo skill `ship-develop`과 보조 스크립트로 캡슐화한다. 구현은 `gh` CLI 기반으로 하고, base branch는 항상 명시적으로 넘긴다.
- Why:
1. 이 저장소의 실사용 브랜치 흐름은 `develop` 중심이지만, GitHub repo 기본 브랜치는 현재 `master`라서 암묵적 기본값에 기대면 잘못 머지할 수 있다.
2. 현재 repo 설정은 `allow_auto_merge=false`, `delete_branch_on_merge=false`라서 GitHub UI 기본 동작만으로는 사용자가 원하는 "머지 후 정리" 흐름을 끝까지 자동화하기 어렵다.
3. skill + script 조합이면 Codex가 한 문장 요청에서도 테스트, 커밋, PR, merge, cleanup 흐름을 일관되게 재사용할 수 있다.
- Impact:
1. 이후 `develop으로 합쳐` 류 요청은 `$ship-develop` skill이 우선 후보가 된다.
2. 머지 자동화는 current branch, worktree 상태, PR 상태, checks 상태를 확인한 뒤 안전할 때만 진행한다.
3. `gh`가 `PATH`에 없더라도 `C:\Program Files\GitHub CLI\gh.exe` fallback 경로를 사용한다.
- Status: accepted

## 2026-03-18
- Context: Codex subagents/custom agents 운영 방식을 이 저장소 작업 흐름에 붙일 수 있는지 검토했다.
- Decision: 이 저장소는 `AGENTS.md`를 공통 규칙 레이어로 유지하고, 필요 시 프로젝트 범위의 read-only custom agent와 repo skill을 소규모로 추가한다. 외부 `Agents SDK + Codex MCP` 오케스트레이션은 당장 도입하지 않는다.
- Why:
1. 현재 구조는 `bot/features/*`, `bot/intel/providers/*`, `bot/forum/*`, `docs/context/*`처럼 경계가 나뉘어 있어 탐색, 리뷰, 문서 검증은 병렬 분업 이점이 있다.
2. 반면 실제 수정은 `bot/features/intel_scheduler.py`, `bot/app/settings.py`, `bot/forum/repository.py`처럼 공용 파일에 집중돼 병렬 writer를 늘리면 충돌과 정합성 비용이 커진다.
3. 현재 최우선 과제는 외부 provider 실사용 전환과 운영 검증이라, 별도 오케스트레이터보다 project-scoped custom agent/skill이 더 저비용이다.
4. 공식 Codex 문서도 subagents는 명시 요청 기반 병렬 작업, `AGENTS.md`는 공통 지침, skills는 재사용 workflow 패키징 용도로 분리한다.
- Impact:
1. 병렬 활용은 코드 탐색, 문서 검증, 리뷰 중심으로 제한한다.
2. 반복 작업은 repo skill 후보로 분리할 수 있고, 구현은 메인 세션 또는 단일 worker가 맡는다.
3. multi-repo 자동화나 상위 orchestration 필요성이 커질 때만 `Agents SDK + Codex MCP`를 다시 검토한다.
- Status: accepted

## 2026-03-18
- Context: 같은 유형의 리뷰 누락이 다시 발생하지 않게, 발견된 실수를 운영 규칙으로 축적할 필요가 생겼다.
- Decision: 리뷰에서 유효했던 지적은 `docs/context/review-log.md`에 기록만 하지 않고, 재발 방지 가치가 있으면 `docs/context/review-rules.md`에 규칙으로 승격한다.
- Why:
1. 리뷰 로그는 과거 사실 기록에는 좋지만, 다음 리뷰 시작 시 바로 적용할 체크리스트 역할은 약하다.
2. 이번 누락은 단일 버그보다 리뷰 범위의 문제였기 때문에 규칙화가 더 효과적이다.
- Impact:
1. 이후 리뷰 세션은 `review-rules.md`를 먼저 보고 체크한다.
2. 규칙은 실제로 놓친 사례가 생길 때마다 한 개씩 추가한다.
- Status: accepted

## 2026-03-17
- Context: 새로 추가한 뉴스/장마감/watch 스케줄을 mock 단계에서 실제 운영 단계로 올리려면 외부 데이터 소스 기준이 먼저 필요하다.
- Decision: 벤더를 먼저 고정하지 않고, 현재 scheduler/provider 인터페이스에 맞는 벤더 중립 정규화 계약을 `docs/specs/external-intel-api-spec.md`로 먼저 확정한다.
- Why:
1. 지금 코드의 진짜 의존성은 특정 API가 아니라 `NewsItem`, `Quote`, `EodSummary` 형태의 정규화된 데이터다.
2. 계약이 먼저 있어야 벤더 교체, fallback, rate limit 대응, 테스트 fixture 구성이 한 기준으로 정리된다.
3. watchlist 폴링은 호출 빈도가 높아 구현 전에 timeout, batch, 오류 처리 규칙이 선행돼야 한다.
- Impact:
1. 이후 외부 API 연동은 이 명세를 만족하는 adapter 구현으로 진행한다.
2. goals와 handoff의 최우선 항목은 확장 스케줄 실사용 전환으로 유지한다.
- Status: accepted

## 2026-03-17
- Context: 프로젝트용 바이브 코딩 규칙 초안을 실제 운영 문서에 편입했다.
- Decision: 바이브 코딩 규칙을 별도 초안 파일에만 두지 않고 `AGENTS.md` 상단 공통 운영 규칙으로 승격한다.
- Why:
1. 세션이 시작될 때 가장 먼저 읽는 문서가 `AGENTS.md`이므로, 핵심 규칙은 참조 문서보다 본문에 있어야 실행 편차가 줄어든다.
2. 프로젝트 특화 규칙인 컨텍스트 로그 갱신, 검증, 위험 작업 통제는 항상 적용돼야 한다.
- Impact:
1. 이후 세션은 바이브 코딩 규칙을 기본 운영 규칙으로 따른다.
2. `docs/prompts/vibe-coding-rule-prompt.md`는 상세 원문과 재사용 프롬프트 저장소 역할로 유지한다.
- Status: accepted

## 2026-03-17
- Context: 앞으로 AI 협업 규칙에 "바이브 코딩" 스타일을 추가하려고 한다.
- Decision: 속도 중심 규칙만 복제하지 않고, 검증과 컨텍스트 유지가 포함된 보호형 프롬프트로 정리한다.
- Why:
1. 최근 유행하는 바이브 코딩 예시는 실행 속도와 반복 루프에는 강하지만, 파괴적 변경 통제와 맥락 보존 규칙이 약한 경우가 많다.
2. 이 프로젝트는 여러 세션과 여러 작업 위치에서 이어지므로 작업 로그와 핸드오프 규칙이 빠지면 판단이 쉽게 흔들린다.
3. 테스트, 리뷰, 문서 갱신을 완료 조건에 넣어야 결과 품질을 일정하게 유지할 수 있다.
- Impact:
1. 이후 바이브 코딩 규칙을 도입할 때는 단일 프롬프트 안에 속도 규칙과 안전 규칙을 함께 둔다.
2. 프롬프트 초안은 `docs/prompts/vibe-coding-rule-prompt.md`에 보관한다.
- Status: accepted

## 2026-03-17
- Context: Codex를 여러 세션과 위치에서 병행 사용할 때 프로젝트 컨텍스트가 일관되게 유지되어야 한다.
- Decision: 단일 문서 의존 대신 카테고리별 문서 집합으로 컨텍스트를 관리한다.
- Why:
1. 활성 상태와 장기 설계 근거를 한 문서에 섞으면 필요한 정보를 빠르게 찾기 어렵다.
2. 리뷰 이슈와 구현 로그는 수명이 다르므로 분리해야 추적성이 좋아진다.
3. 이후 자동화나 템플릿화가 필요할 때도 카테고리 구조가 더 확장성이 높다.
- Alternatives considered:
1. `AGENTS.md` 하나에 계속 누적: 검색은 쉽지만 문서 비대화와 혼선 위험이 크다.
2. 날짜별 일지만 운영: 세션 회고에는 좋지만 설계 기준 복원이 느리다.
- Impact:
1. 다음 세션은 `session-handoff.md`로 즉시 현재 상태를 복구한다.
2. 설계 변경은 `design-decisions.md`에 먼저 남기는 습관이 필요하다.
- Status: accepted
