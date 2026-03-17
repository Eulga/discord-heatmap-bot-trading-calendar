# Session Handoff

## 2026-03-17
- Context: 바이브 코딩 규칙을 `AGENTS.md`에 직접 녹여 운영 규칙으로 편입했다.
- Current state:
1. `AGENTS.md` 상단에 `바이브 코딩 운영 규칙` 섹션이 추가됐다.
2. `docs/prompts/vibe-coding-rule-prompt.md`는 상세 원문 보관용으로 유지된다.
3. 이후 세션은 `AGENTS.md`만 읽어도 바이브 코딩 규칙을 바로 적용할 수 있다.
- Next:
1. 실제 작업 중 규칙이 과하거나 빠진 부분이 보이면 `AGENTS.md`와 프롬프트 원문을 함께 조정한다.
- Status: done

## 2026-03-17
- Context: 현재 유행하는 바이브 코딩 규칙을 조사해 프로젝트용 단일 프롬프트 초안을 만들었다.
- Current state:
1. 프롬프트 초안은 `docs/prompts/vibe-coding-rule-prompt.md`에 저장돼 있다.
2. 초안은 속도 규칙뿐 아니라 검증, 위험 작업 통제, 컨텍스트 로그 갱신까지 포함한다.
3. 이후 운영 편입을 위한 기준 문서로 사용한다.
- Next:
1. 운영 중 표현이나 우선순위가 맞지 않으면 원문과 `AGENTS.md`를 함께 수정한다.
- Status: done

## 2026-03-17
- Context: 여러 위치에서 Codex를 사용할 때 프로젝트 판단 기준이 흔들리지 않도록 분류형 컨텍스트 저장 체계를 도입했다.
- Current state:
1. `AGENTS.md`가 `docs/context/*`를 먼저 읽도록 갱신됐다.
2. 검토, 개발, 설계 메모를 별도 파일에 누적하는 구조를 만들었다.
3. 아직 이 구조를 실제 기능 작업 로그로 채우기 시작한 단계는 아니다.
- Next:
1. 다음 작업부터 결과를 해당 카테고리 문서에 바로 누적한다.
2. 기능 변경이 있으면 `development-log.md`와 `session-handoff.md`를 함께 갱신한다.
3. 설계 판단이 생기면 `design-decisions.md`에 이유까지 적는다.
- Status: open
