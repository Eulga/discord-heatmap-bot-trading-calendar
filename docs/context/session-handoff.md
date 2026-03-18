# Session Handoff

## 2026-03-18
- Context: `ship-develop`을 실제 merge에 사용했더니, `gh pr merge --delete-branch` 이후 로컬 브랜치가 이미 지워진 경우 cleanup 단계가 한 번 더 지우려다 실패했다.
- Current state:
1. 현재 작업 브랜치는 `codex/ship-develop-cleanup`이다.
2. `ship_develop.py`는 이제 local branch가 이미 없어도 `already-gone`으로 정상 처리한다.
3. py_compile과 skill validator는 다시 통과했다.
- Next:
1. 이 cleanup fix를 `develop`에 반영한다.
- Status: open

## 2026-03-18
- Context: `develop으로 합쳐` 요청을 한 번의 흐름으로 처리하기 위한 GitHub shipping skill을 추가했다.
- Current state:
1. `.agents/skills/ship-develop/`와 `scripts/ship_develop.py`가 생겼다.
2. 현재 GitHub repo는 default branch=`master`, `develop` 브랜치 별도 운영, `allow_auto_merge=false`, `delete_branch_on_merge=false` 상태다.
3. `gh`는 `C:\Program Files\GitHub CLI\gh.exe`에 설치돼 있고, 계정 `Eulga`로 로그인되어 있다.
4. 새 script는 current branch push, PR create/reuse, checks/review 상태 확인, direct merge, `develop` checkout, local branch 삭제까지 처리한다.
5. dry-run과 공식 skill validator는 통과했다.
- Next:
1. 다음 실제 shipping 요청에서 `$ship-develop`으로 실전 검증한다.
2. 필요하면 wait time이나 merge method 기본값을 조정한다.
- Status: open

## 2026-03-18
- Context: PR `#4`의 Codex Connector P1 두 건을 반영해 같은 분 내 반복 tick이 기존 성공 상태를 `skipped`로 덮어쓰는 문제를 수정했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 뉴스/장마감 모두 `completed_guilds`를 계산해 이미 성공한 tick 결과를 no-target early return이 덮어쓰지 않는다.
2. `tests/integration/test_intel_scheduler_logic.py`에 뉴스/EOD 상태 보존 회귀 테스트가 추가됐다.
3. 전체 기본 테스트는 `.\.venv\Scripts\python.exe -m pytest` 기준 `40 passed, 2 deselected`다.
- Next:
1. 현재 수정 커밋을 PR `#4`에 푸시한다.
2. `@codex review`를 다시 호출해 P1이 닫혔는지 확인한다.
- Status: open

## 2026-03-18
- Context: project-scoped Codex custom agent와 repo skill 최소 골격을 저장소에 추가했다.
- Current state:
1. `.codex/config.toml`에 `[agents] max_threads=3`, `max_depth=1`이 들어가 있다.
2. read-only custom agent `repo_explorer`, `reviewer`, `docs_researcher`가 `.codex/agents/` 아래에 생겼다.
3. repo skill `external-intel-provider-rollout`가 `.agents/skills/` 아래에 생겼고, 외부 provider 실사용 전환용 절차가 들어가 있다.
4. 현재 프로젝트 `.venv`에 `PyYAML 6.0.3`이 설치돼 있고, 공식 `quick_validate.py`도 통과했다.
- Next:
1. 다음 실제 외부 provider 작업에서 새 agent/skill을 직접 써 보고 지침을 조정한다.
- Status: open

## 2026-03-18
- Context: Codex subagents/custom agents 운영 방식을 이 저장소에 접목할 수 있는지 검토했다.
- Current state:
1. 공식 문서 기준으로 subagents는 명시 요청형 병렬 작업, `AGENTS.md`는 공통 지침, skills는 재사용 workflow 패키징으로 역할이 분리된다는 점을 확인했다.
2. 현재 저장소에는 project-scoped `.codex/agents/`와 repo `.agents/skills/`가 아직 없다.
3. 이 프로젝트는 외부 provider 조사, 리뷰, 문서 검증처럼 read-heavy 작업은 분업 이점이 있지만, 실제 코드 수정은 single-writer가 더 안전하다는 판단을 정리했다.
- Next:
1. 도입 시 최소 세트로 `reviewer`, `repo_explorer`, `docs_researcher` 같은 read-only custom agent부터 추가한다.
2. 구현은 메인 세션 또는 단일 worker가 맡고, 반복 체크리스트는 skill로 분리한다.
3. `Agents SDK + Codex MCP`는 multi-repo 자동화나 상위 orchestration 필요가 생길 때 다시 검토한다.
- Status: open

## 2026-03-18
- Context: 리뷰 실수를 반복하지 않도록 첫 번째 리뷰 운영 규칙을 추가했다.
- Current state:
1. `docs/context/review-rules.md`가 새로 생겼다.
2. Rule 1은 `실패 경로와 운영 정합성까지 리뷰한다`이며, scheduler/status/doc/docker 정합성을 함께 보도록 고정했다.
3. `AGENTS.md`와 `docs/context/README.md`도 리뷰 작업 시 이 문서를 먼저 읽도록 연결됐다.
- Next:
1. 다음 리뷰부터 `review-rules.md`를 기준으로 체크한다.
2. 새 누락 유형이 확인되면 같은 문서에 Rule 2를 추가한다.
- Status: open

## 2026-03-17
- Context: 최신 리뷰에서 나온 운영 가시성과 문서 정합성 이슈를 `codex/review-fixes` 브랜치에서 정리했다.
- Current state:
1. `bot/features/intel_scheduler.py`는 뉴스 dedup을 fetch 단위로만 처리하고, 뉴스/장마감 job status를 실제 게시 결과 기준으로 `skipped`/`failed`/`ok`로 구분한다.
2. `docker-compose.yml`은 `data/logs`도 볼륨 마운트해 런타임 로그 파일이 컨테이너 재생성 후에도 남는다.
3. `README.md`와 `AGENTS.md`는 `python -m bot.main`, `/health` 중심 quick test, PowerShell 활성화 경로로 갱신됐다.
4. 관련 회귀를 포함한 전체 기본 테스트는 `.\.venv\Scripts\python -m pytest` 기준 `38 passed, 2 deselected`다.
- Next:
1. `codex/review-fixes` 브랜치로 PR을 열어 리뷰에서 지적된 이슈가 모두 닫혔는지 확인한다.
- Status: open

## 2026-03-17
- Context: 현재 브랜치의 `bot/app/bot_client.py` 병합 충돌을 정리했다.
- Current state:
1. 충돌은 command sync 상태 기록 변경과 로깅 전환 변경이 같은 구간을 건드리면서 발생했다.
2. 현재 구현은 command sync 성공/실패 상태 기록을 유지하면서 콘솔 출력을 `logger` 기반으로 통일했다.
3. `.\.venv\Scripts\python -m pytest tests/unit/test_command_sync.py`는 통과했고, 충돌 파일은 더 이상 `UU` 상태가 아니다.
- Next:
1. 남은 변경 묶음을 기준으로 커밋 또는 추가 병합 정리를 진행한다.
2. 필요 시 전체 `pytest` 또는 봇 실행으로 부트 경로를 한 번 더 확인한다.
- Status: open

## 2026-03-17
- Context: 새로 추가한 뉴스/장마감/watch 스케줄을 실사용 단계로 전환하기 위한 외부 API 명세를 우선 과제로 추가했다.
- Current state:
1. `docs/specs/external-intel-api-spec.md`가 추가됐고, 뉴스 브리핑, 장마감 요약, watch quote에 필요한 정규화 계약이 정의됐다.
2. `docs/context/goals.md`의 최우선 목표는 확장 스케줄 실사용 전환으로 올라갔다.
3. `AGENTS.md`와 `README.md`도 같은 명세 경로를 기준으로 읽도록 맞췄다.
- Next:
1. 실제 외부 API 또는 중간 adapter 후보를 선택한다.
2. `NewsProvider`, `EodSummaryProvider`, `MarketDataProvider`를 이 명세 기준으로 구현한다.
3. Discord 실운영 환경에서 스케줄 포스트/알림을 검증한다.
- Status: open

## 2026-03-17
- Context: PR `#3`에서 Codex Connector 리뷰 1건을 반영했다.
- Current state:
1. 지적 내용은 command sync 상태 저장 실패가 봇 시작을 깨뜨릴 수 있다는 점이었다.
2. 현재 구현은 상태 저장 실패를 fail-open으로 바꿨고, 관련 테스트도 추가됐다.
3. 수정 후 전체 기본 테스트는 다시 통과했다.
- Next:
1. 수정 커밋을 PR `#3`에 푸시
2. 추가 리뷰가 없으면 머지 및 원격 브랜치 삭제
- Status: open

## 2026-03-17
- Context: 슬래시 커맨드 동기화 실패 진단 메시지와 상태 기록 기능을 브랜치에서 정리 중이다.
- Current state:
1. `bot/app/bot_client.py`는 command sync 실패를 잡아 상태 파일에 `command-sync` 마지막 실행 결과를 기록한다.
2. `bot/app/command_sync.py`는 설치/권한/토큰/스키마 오류에 대한 한국어 힌트를 만든다.
3. 관련 테스트와 전체 기본 테스트는 모두 통과했다.
- Next:
1. 이 변경을 커밋하고 `origin/develop` 기준으로 PR diff를 정리한다.
2. PR 생성 후 Codex Connector 리뷰를 확인한다.
- Status: open

## 2026-03-17
- Context: `codex/context-summary` 브랜치의 PR 생성부터 merge, 원격 브랜치 삭제까지 완료했다.
- Current state:
1. PR `#2`는 `develop`에 squash merge 됐다.
2. 원격 브랜치 `codex/context-summary`는 삭제됐다.
3. 현재 로컬 작업 디렉터리에는 이번 흐름과 별개의 미커밋 변경이 남아 있다.
- Next:
1. 필요 시 로컬에서 `develop` 최신 상태를 fetch/pull 한다.
2. 남은 로컬 변경은 별도 브랜치 또는 커밋으로 정리한다.
- Status: done

## 2026-03-17
- Context: `codex/context-summary` 브랜치를 `develop`로 보내기 위한 PR 준비를 진행했다.
- Current state:
1. 원격 브랜치 `codex/context-summary`는 최신 로컬 HEAD(`3a5bdfd`)까지 푸시됐다.
2. GitHub compare 기준 `develop...codex/context-summary`는 1 commit / 1 file changed / able to merge 상태다.
3. 현재 세션에는 `gh` CLI가 없고 GitHub 브라우저 세션도 로그인되지 않아 PR 생성 API 호출을 끝내지 못했다.
- Next:
1. GitHub 인증 가능한 환경에서 PR 생성
2. 체크 통과 확인 후 merge
3. merge 후 원격 브랜치 삭제
- Status: done

## 2026-03-17
- Context: 현재 프로젝트 목표를 다음 세션에서도 바로 복구할 수 있게 goals 문서를 추가했다.
- Current state:
1. 현재 우선 목표는 운영 안정화, 히트맵 게시 실운영 검증, 자동 스케줄 신뢰도 확보다.
2. 운영 가시성 강화와 확장 기능 운영화는 그 다음 레이어로 정리했다.
3. 목표 문서는 `docs/context/goals.md`에 따로 분리했다.
- Next:
1. 다음 작업 시작 전 `session-handoff.md`와 `goals.md`를 함께 확인한다.
- Status: done

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
