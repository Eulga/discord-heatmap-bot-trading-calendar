# Development Log

## 2026-03-18
- Context: PR `#4`의 Codex Connector 리뷰에서 같은 분 내 반복 tick이 기존 성공 상태를 `skipped`로 덮어쓸 수 있다는 P1 두 건을 반영하는 작업
- Change:
1. `bot/features/intel_scheduler.py`에서 뉴스/장마감 pending guild 계산 시 이미 해당 날짜에 성공 처리된 guild 수를 함께 세도록 바꿨다.
2. `pending_guilds`가 비고 `missing_forum > 0`이어도, 이미 성공 처리된 guild가 있으면 `skipped`로 상태를 덮어쓰지 않고 기존 성공 상태를 유지하도록 수정했다.
3. 같은 분 재실행에서 `news_briefing`과 `eod_summary`의 `ok` 상태가 유지되는 회귀 테스트 두 개를 `tests/integration/test_intel_scheduler_logic.py`에 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_intel_scheduler_logic.py` 통과 (`7 passed`)
2. `.\.venv\Scripts\python.exe -m pytest` 통과 (`40 passed, 2 deselected`)
- Next:
1. 수정 커밋을 PR `#4`에 푸시한다.
2. `@codex review`를 다시 호출해 같은 P1이 닫혔는지 확인한다.
- Status: done

## 2026-03-18
- Context: project-scoped Codex custom agent와 repo skill 최소 골격을 실제로 추가하는 작업
- Change:
1. `.codex/config.toml`에 `[agents]` 설정을 추가해 `max_threads=3`, `max_depth=1`로 시작점을 고정했다.
2. `.codex/agents/repo-explorer.toml`, `.codex/agents/reviewer.toml`, `.codex/agents/docs-researcher.toml`을 추가해 read-only 역할 분업 골격을 만들었다.
3. `.agents/skills/external-intel-provider-rollout/`를 생성하고 `SKILL.md`, `agents/openai.yaml`을 현재 외부 provider 실사용 전환 흐름에 맞게 채웠다.
4. 현재 프로젝트 `.venv`에 `PyYAML 6.0.3`을 설치해 공식 skill validator를 실행할 수 있게 했다. `requirements.txt`는 바꾸지 않았다.
- Verification:
1. `tomllib`로 `.codex/config.toml`과 세 개의 agent TOML 파일이 정상 파싱되는 것을 확인했다.
2. 경량 스크립트로 skill frontmatter, 핵심 섹션, `agents/openai.yaml`의 `$external-intel-provider-rollout` prompt 문자열을 확인했다.
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/external-intel-provider-rollout`가 `Skill is valid!`로 통과했다.
- Next:
1. 다음 실제 provider 전환 작업에서 `repo_explorer`, `reviewer`, `docs_researcher`, `$external-intel-provider-rollout`를 한 번 사용해 trigger와 지침을 다듬는다.
- Status: done

## 2026-03-18
- Context: Codex subagents/custom agents 내용을 현재 저장소 운영 방식에 접목할 수 있는지 검토하는 작업
- Change:
1. `AGENTS.md`, 컨텍스트 허브 문서, 현재 아키텍처와 provider/scheduler 경계를 다시 읽어 병렬 분업에 맞는 지점을 정리했다.
2. 공식 Codex 문서를 기준으로 subagents, custom agents, skills, `AGENTS.md`의 역할 구분을 확인했다.
3. 이 저장소는 `AGENTS.md` 기반 공통 규칙을 유지하고, 필요 시 read-only custom agent와 repo skill을 추가하되 외부 orchestration은 보류하는 방향으로 판단을 정리했다.
- Verification:
1. 현재 저장소에는 project-scoped `.codex/agents/`나 repo `.agents/skills/`가 아직 없다.
2. 로컬 사용자 설정 `C:\\Users\\kin50\\.codex\\config.toml`에는 `[agents]` 설정이 없고 Playwright MCP만 잡혀 있음을 확인했다.
3. 현재 코드 경계상 탐색/리뷰/문서 검증은 역할 분리가 가능하지만, 구현은 공용 파일 충돌을 줄이기 위해 single-writer가 더 안전하다고 대조했다.
- Next:
1. 실제 도입 시 최소 세트로 `reviewer`, `repo_explorer`, `docs_researcher` custom agent부터 고려한다.
2. 외부 provider 실사용 전환 같은 반복 체크리스트는 repo skill로 분리하는 안을 검토한다.
- Status: done

## 2026-03-18
- Context: 어제 리뷰에서 놓친 포인트를 반복하지 않도록 첫 번째 리뷰 운영 규칙을 문서화하는 작업
- Change:
1. `docs/context/review-rules.md`를 추가했다.
2. 첫 번째 룰로 `실패 경로와 운영 정합성까지 리뷰한다`를 정의했다.
3. `AGENTS.md`, `docs/context/README.md`, `docs/context/design-decisions.md`, `docs/context/session-handoff.md`에 이 규칙 문서 진입점을 연결했다.
- Verification:
1. 2026-03-17 리뷰에서 실제로 놓쳤던 사례가 규칙의 `Why`와 `Must` 항목에 반영됐는지 대조했다.
2. 다음 세션 읽기 순서에서 리뷰 작업 시 이 문서를 바로 볼 수 있게 연결했는지 확인했다.
- Next:
1. 다음 리뷰에서 이 1번 룰을 실제로 적용해 보고, 필요하면 표현을 다듬는다.
2. 새로운 누락 유형이 생기면 2번 룰을 추가한다.
- Status: done

## 2026-03-17
- Context: 전체 리뷰에서 나온 intel scheduler/문서 정합성 이슈를 실제 수정으로 반영했다.
- Change:
1. `bot/features/intel_scheduler.py`에서 뉴스 dedup을 fetch 단위 로컬 dedup으로 바꿔 게시 실패 후 같은 날짜 재시도가 비어 버리지 않도록 수정했다.
2. 뉴스/장마감 스케줄은 실제 게시 대상이 없으면 `skipped`, 모든 게시가 실패하면 `failed`, 하나 이상 성공하면 `ok`로 기록하도록 바꿨다.
3. `docker-compose.yml`, `README.md`, `AGENTS.md`, `docs/context/session-handoff.md`, `docs/context/review-log.md`를 갱신해 로그 볼륨, 실행 방법, quick test, 현재 핸드오프 상태를 실제 구현에 맞췄다.
4. 관련 회귀 테스트를 `tests/integration/test_intel_scheduler_logic.py`에 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest` 통과 (`38 passed, 2 deselected`)
- Next:
1. `codex/review-fixes` 브랜치 기준으로 PR을 열고, 리뷰에서 지적된 운영 가시성/문서 정합성 이슈가 닫혔는지 확인한다.
- Status: done

## 2026-03-17
- Context: 현재 브랜치가 `origin/develop`와 병합되면서 `bot/app/bot_client.py`에 충돌이 발생했다.
- Change:
1. `bot/app/bot_client.py`의 충돌을 command sync 상태 기록 로직과 구조화 로깅 설정을 함께 유지하는 방향으로 정리했다.
2. `tree.sync()` 성공 시에는 명령 수를 로거와 상태 파일에 함께 남기고, 실패 시에는 한국어 진단 메시지를 상태 파일과 로거에 함께 남기도록 맞췄다.
3. 충돌 마커를 제거하고 Git 인덱스에 해결 상태를 반영했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `git status --short --branch`에서 `bot/app/bot_client.py`가 더 이상 `UU`가 아닌 일반 수정 상태로 표시되는 것을 확인했다.
- Next:
1. 남은 로컬 변경과 함께 커밋 단위를 정리하고 필요 시 `origin/develop` 최신분을 다시 검토한다.
- Status: done

## 2026-03-17
- Context: 새로 추가한 뉴스/장마감/watch 스케줄을 실사용 단계로 올리기 위한 외부 API 기준 문서가 필요했다.
- Change:
1. `docs/specs/external-intel-api-spec.md`를 추가해 뉴스 브리핑, 장마감 요약, watch quote의 정규화 API 계약을 정의했다.
2. `AGENTS.md`, `docs/context/goals.md`, `docs/context/session-handoff.md`, `docs/context/README.md`, `README.md`를 갱신해 이 작업을 최우선 전환 과제로 반영했다.
3. 다음 세션 TODO를 실제 provider 구현과 운영 검증 중심으로 재정렬했다.
- Verification:
1. `bot/features/intel_scheduler.py`, `bot/intel/providers/news.py`, `bot/intel/providers/market.py`의 현재 인터페이스와 필드 구성을 기준으로 명세를 대조했다.
2. README와 컨텍스트 문서가 같은 명세 경로를 참조하는지 확인했다.
- Next:
1. 외부 벤더 또는 중간 adapter 후보를 정하고 provider 구현을 시작한다.
2. 특히 watch quote는 batch 조회 전략을 먼저 잡는다.
- Status: done

## 2026-03-17
- Context: PR `#3`의 Codex Connector 리뷰 코멘트를 반영하는 작업
- Change:
1. `record_command_sync`를 `bot/app/command_sync.py`로 옮겨 공용 함수로 정리했다.
2. 상태 파일 저장 실패 시 예외를 부트 흐름 밖으로 전파하지 않고 로그만 남기도록 수정했다.
3. 상태 저장 성공/실패 케이스를 검증하는 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `.\.venv\Scripts\python -m pytest` 통과
- Next:
1. 수정 커밋을 PR `#3`에 푸시하고 추가 리뷰 사항이 있는지 확인
- Status: done

## 2026-03-17
- Context: 슬래시 커맨드 동기화 실패를 더 잘 진단할 수 있게 만드는 작업
- Change:
1. `bot/app/command_sync.py`에 Discord 동기화 예외를 사람이 읽기 쉬운 한국어 안내로 바꾸는 헬퍼를 추가했다.
2. `bot/app/bot_client.py`에서 `tree.sync()` 실패를 잡아 `system.job_last_runs.command-sync`에 성공/실패 상태를 저장하도록 연결했다.
3. 관련 단위 테스트 `tests/unit/test_command_sync.py`를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py` 통과
2. `.\.venv\Scripts\python -m pytest` 통과
- Next:
1. PR 생성 후 Codex Connector 리뷰 코멘트를 확인하고 필요 시 수정 반영
- Status: done

## 2026-03-17
- Context: `codex/context-summary` 브랜치의 PR 흐름을 끝까지 완료한 작업
- Change:
1. PR `#2`를 `develop` 대상으로 생성했다.
2. PR을 squash merge로 반영했다.
3. merge 후 원격 브랜치 `codex/context-summary`를 삭제했다.
- Verification:
1. PR `#2`가 `merged=true` 상태인지 확인했다.
2. 원격 heads 조회에서 `codex/context-summary`가 삭제됐는지 확인했다.
- Next:
1. 남아 있는 로컬 미커밋 변경은 별도 흐름으로 정리한다.
- Status: done

## 2026-03-17
- Context: 현재 브랜치 변경을 재검토하고 `develop` PR 흐름으로 넘기려는 작업
- Change:
1. `codex/context-summary`를 원격에 푸시해 최신 HEAD(`3a5bdfd`)를 반영했다.
2. 원격 compare 기준 실제 PR diff가 `docs/reports/sunday-kheatmap-investigation-2026-03-12.md` 1파일임을 확인했다.
3. GitHub compare 페이지와 로컬 코드를 대조해 문서 리포트의 상태 키와 조사 메모를 재검토했다.
- Verification:
1. 원격 compare 페이지에서 `Able to merge` 상태를 확인했다.
2. `git diff develop HEAD` 기준 현재 트리 차이는 조사 리포트 1파일뿐임을 확인했다.
- Next:
1. GitHub 인증 가능한 환경에서 PR 생성
2. PR 체크 통과 후 merge 및 브랜치 삭제
- Status: done

## 2026-03-17
- Context: 바이브 코딩 규칙 초안을 실제 운영 규칙으로 편입하는 작업
- Change:
1. `AGENTS.md` 읽기 순서에 `docs/prompts/vibe-coding-rule-prompt.md`를 추가했다.
2. `AGENTS.md`에 `바이브 코딩 운영 규칙` 섹션을 신설해 시작, 구현, 검증, 안전, 기록, 완료 조건을 반영했다.
3. 초안 단계로 적혀 있던 컨텍스트 기록을 운영 편입 기준으로 갱신했다.
- Verification:
1. 사용자 제공 규칙의 핵심 항목이 `AGENTS.md` 본문에 모두 반영됐는지 대조 확인했다.
2. 기존 프로젝트 운영 규칙과 충돌하지 않도록 공통 원칙 섹션으로 배치했다.
- Next:
1. 이후 실제 작업에서 이 규칙을 기준으로 로그와 검증 절차가 잘 유지되는지 운영하면서 다듬는다.
- Status: done

## 2026-03-17
- Context: 현재 유행하는 바이브 코딩 규칙을 조사하고, 이 프로젝트에 맞는 단일 프롬프트로 정리하는 작업
- Change:
1. 웹 리서치를 바탕으로 바이브 코딩 규칙의 공통 요소를 정리했다.
2. 속도 중심 예시에서 자주 빠지는 안전장치와 컨텍스트 보존 규칙을 보완했다.
3. 재사용 가능한 초안을 `docs/prompts/vibe-coding-rule-prompt.md`에 저장했다.
- Verification:
1. 프롬프트 안에 컨텍스트 읽기, 작은 변경, 검증, 리뷰, 위험 작업 중단, 로그 갱신 규칙이 모두 포함되도록 점검했다.
- Next:
1. 실제로 이 프롬프트를 `AGENTS.md`나 운영 프롬프트에 반영할지 결정한다.
- Status: done

## 2026-03-17
- Context: 프로젝트 작업 컨텍스트를 검토/개발/설계로 분류 저장하는 기반이 필요했다.
- Change:
1. `docs/context/` 디렉터리를 만들었다.
2. 컨텍스트 허브 문서와 카테고리별 로그 파일을 추가했다.
3. `AGENTS.md` 읽기 순서와 종료 체크 절차를 새 구조 기준으로 갱신했다.
- Verification:
1. 저장 구조가 프로젝트 루트 기준으로 고정되어 다음 세션이 동일 경로를 읽을 수 있다.
2. 기존 코드 파일 변경 없이 문서 계층만 추가해 현재 구현 리스크를 늘리지 않았다.
- Next:
1. 실제 기능 작업 때 이 로그를 누적 사용한다.
- Status: done
