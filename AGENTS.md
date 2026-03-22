# AGENTS.md

## 1) 문서 목적
- 이 문서는 다음 세션에서 프로젝트 컨텍스트를 빠르게 복구하기 위한 단일 진입 문서다.
- 우선 읽기 순서:
1. 이 문서
2. `docs/context/README.md`
3. `docs/context/session-handoff.md`
4. `docs/context/goals.md`
5. 리뷰 작업이면 `docs/context/review-rules.md`
6. `docs/specs/external-intel-api-spec.md`
7. `docs/prompts/vibe-coding-rule-prompt.md`
8. `README.md`
9. `bot/app/settings.py`
10. `bot/features/runner.py`
11. `bot/forum/repository.py`

## 1-1) 컨텍스트 저장 원칙
- 앞으로의 검토, 개발, 설계 대화 결과는 `docs/context/*`에 종류별로 누적 저장한다.
- 목적은 세션/작업 위치가 달라도 같은 프로젝트 판단 기준을 재사용하는 것이다.
- 문서 분류:
1. `docs/context/session-handoff.md`: 현재 활성 컨텍스트, 최근 결정, 다음 액션
2. `docs/context/design-decisions.md`: 설계 결정과 이유, 대안, 영향 범위
3. `docs/context/development-log.md`: 구현 변경, 작업 단위, 검증 결과
4. `docs/context/review-log.md`: 코드 리뷰/버그/리스크/회귀 포인트
5. `docs/context/review-rules.md`: 반복해서 놓친 리뷰 포인트를 규칙화한 체크리스트
- 저장 규칙:
1. 작업 종료 시 관련 문서를 최소 1곳 이상 업데이트한다.
2. 설계 판단이 바뀌면 `design-decisions.md`에 남기고, 실행 결과는 `development-log.md`에도 반영한다.
3. 리뷰에서 나온 이슈는 해결 전후와 상관없이 먼저 `review-log.md`에 남긴다.
4. 다음 세션이 바로 이어받아야 할 내용은 반드시 `session-handoff.md`에 요약한다.
5. 비밀값/토큰/개인정보는 저장하지 않는다.

## 1-2) 바이브 코딩 운영 규칙
- 기준 프롬프트: `docs/prompts/vibe-coding-rule-prompt.md`
- 이 저장소에서의 바이브 코딩은 "빠른 생성"보다 "작은 단위의 정확한 실행과 검증"을 우선한다.
- 시작 규칙:
1. 작업 시작 전 최소한 `AGENTS.md`, `docs/context/README.md`, `docs/context/session-handoff.md`, 관련 코드/문서를 읽는다.
2. 작업 전 아래 4가지를 짧게 정리한다: 목표, 제약사항, 성공 기준, 불확실한 점
3. 요구가 모호해도 질문은 최소화하되, 위험한 오해 가능성이 있을 때만 짧게 확인한다.
4. 질문 없이 진행할 때는 합리적인 가정을 택하고, 결과 보고 시 가정을 명시한다.
- 구현 규칙:
1. 가장 작은 유효 변경부터 진행하고, 한 번에 큰 리라이트를 하지 않는다.
2. 기존 코드 스타일, 구조, 네이밍, 파일 배치를 우선 존중한다.
3. 새 추상화, 새 프레임워크, 새 의존성은 명확한 이유가 있을 때만 추가한다.
4. 원인을 확인하기 전에는 코드를 지우거나 갈아엎지 않는다.
5. 버그 수정 시 재현 조건, 원인 후보, 수정과 원인의 연결을 설명 가능해야 한다.
6. 임시방편보다 재발 방지에 도움이 되는 수정, 테스트, 로그, 문서 갱신을 선호한다.
- 검증 규칙:
1. 구현 후 가능한 범위에서 반드시 검증한다.
2. 최소 하나 이상의 관련 테스트, 린트, 실행 확인, 또는 논리 검증을 수행한다.
3. 검증을 실행하지 못했으면 이유를 분명히 남긴다.
4. 테스트는 변경 위험도에 비례해 추가하거나 갱신하며, 형식적 커버리지보다 회귀 방지를 우선한다.
5. 리뷰 모드에서는 칭찬보다 결함, 회귀 가능성, 누락된 테스트, 운영 리스크를 먼저 본다.
- 안전 규칙:
1. 시크릿, 토큰, 개인정보, 운영 자격증명은 출력하거나 문서에 저장하지 않는다.
2. 대량 삭제, 강제 git reset, 파괴적 스키마 변경, 운영 설정 초기화, 인증/권한/결제 구조 변경 같은 되돌리기 어려운 작업은 사용자 승인 없이 하지 않는다.
3. 인증, 권한, 결제, 보안, 법적/규제 영향, 데이터 손실 가능성이 있는 변경은 위험을 먼저 설명하고 진행한다.
- 기록 규칙:
1. 큰 작업이나 중요한 판단이 있었으면 `docs/context/*.md`의 맞는 문서를 갱신한다.
2. 설계 판단은 `design-decisions.md`, 구현 결과는 `development-log.md`, 리뷰 이슈는 `review-log.md`, 다음 세션 전달사항은 `session-handoff.md`에 남긴다.
3. 답변에서는 사실과 추론을 구분하고, 무엇을 바꿨는지, 무엇을 검증했는지, 남은 리스크가 무엇인지 명확히 적는다.
- 완료 조건:
1. 요구사항의 핵심이 실제로 반영되었다.
2. 변경 범위에 맞는 검증이 수행되었거나, 못 했다면 이유가 기록되었다.
3. 관련 문서와 컨텍스트 로그가 필요한 만큼 갱신되었다.
4. 남은 이슈, 가정, 다음 액션이 있으면 마지막에 짧게 정리한다.

## 1-3) 브랜치/약속 문서화 규칙
- 운영 약속 문서화 원칙:
1. 세션 중 새로 합의한 운영 약속, 브랜치 전략, merge 방식, shipping 예외 규칙은 말로만 두지 않고 반드시 문서에 남긴다.
2. 공통 규칙으로 계속 써야 하는 약속은 `AGENTS.md`에 반영한다.
3. 왜 그렇게 하기로 했는지와 영향 범위는 `docs/context/design-decisions.md`에 남긴다.
4. 이번 세션에서 실제로 적용했거나 확인한 결과는 `docs/context/development-log.md`에 남긴다.
5. 다음 세션이 바로 알아야 하는 최신 약속 상태는 `docs/context/session-handoff.md`에 남긴다.

- 현재 브랜치 운영 약속:
1. `develop -> master` 릴리스 PR은 앞으로 별도 release 브랜치를 만들지 않고, `develop` 브랜치에서 바로 `master` 대상으로 연다.
2. 이유 없이 `master`에만 먼저 들어가고 `develop`에는 빠지는 흐름을 만들지 않는다.
3. 예외적으로 다른 흐름이 필요하면, 진행 전에 이유와 정리 계획을 먼저 문서화한다.

## 1-4) Codex Subagent 운영 규칙
- 기본 역할:
1. `repo_explorer`: 코드 경로/영향 범위 탐색
2. `reviewer`: 결함/회귀/테스트 리스크 검토
3. `docs_researcher`: 공식 문서/외부 계약 확인

- 호출 약속:
1. 새 스레드에서는 사용자가 subagent 사용 의사를 한 번은 명시해야 한다.
2. 같은 스레드에서 사용자가 `기본 3-agent 패턴`, `같은 subagent 패턴`, `필요한 agent들 써서 진행`처럼 위임 의사를 한 번 밝혔으면, 이후 같은 작업 흐름에서는 매번 agent 이름을 다시 나열하지 않아도 된다.
3. 명시가 없는 새 스레드에서는 Codex가 임의로 subagent를 늘리지 않는다.

- 기본 해석:
1. 사용자가 `기본 3-agent 패턴`이라고 하면 `repo_explorer + reviewer + docs_researcher` 조합으로 해석한다.
2. 문서 확인이 필요 없는 로컬 코드 작업이면 `docs_researcher`는 생략할 수 있다.
3. 구현이 급한 blocking 작업은 메인 세션이 직접 처리하고, 탐색/리뷰/문서확인은 sidecar로 subagent에 나눈다.

## 2) 현재 아키텍처 스냅샷
- 엔트리포인트: `bot/main.py`
- 부트스트랩/커맨드 등록: `bot/app/bot_client.py`
- 설정/환경: `bot/app/settings.py`
- 공통 유틸: `bot/common/*`
- 포럼 상태 저장/업서트: `bot/forum/*`
- 캡처/캐시: `bot/markets/*`
- 기능 커맨드: `bot/features/*`
- 테스트: `tests/unit/*`, `tests/integration/*`

핵심 흐름:
1. 슬래시 커맨드 (`/kheatmap`, `/usheatmap`) 실행
2. 길드별 포럼 채널 조회 (`state.json` -> guild mapping)
3. 1시간 캐시 확인 후 필요 시 캡처
4. 포럼 포스트 upsert (당일 1개 포스트, 최초 메시지 수정)
5. 상태 저장

## 3) 운영 규칙 (Rules)
- 서버별 포럼 채널 매핑:
1. `/setforumchannel`로 길드별 채널 ID 저장
2. 저장 위치: `data/state/state.json` -> `guilds.{guild_id}.forum_channel_id`

- 히트맵 게시 규칙:
1. `kheatmap/usheatmap`는 명령어별로 하루 1포스트 유지
2. 같은 날 재실행 시 기존 포스트 최초 메시지 수정
3. 제목 규칙:
- `kheatmap`: `[YYYY-MM-DD 한국장 히트맵]`
- `usheatmap`: `[YYYY-MM-DD 미국장 히트맵]`

- 캐시 규칙:
1. 캡처 이미지는 로컬 저장 (`data/heatmaps/...`)
2. 1시간 이내 동일 마켓 이미지가 있으면 재사용

- 자동스크린샷 거래일 규칙:
1. KST 15:35 `kheatmap`은 KRX(`XKRX`) 거래일에만 실행
2. KST 06:05 `usheatmap`은 NYSE(`XNYS`) 거래일에만 실행 (뉴욕 현지 날짜 기준)
3. 거래일 판정 실패 시 로그를 남기고 스킵

- 렌더 안정성 규칙:
1. 렌더 완료 조건 확인 후 캡처
2. 파일 사이즈 검증
3. 실패 시 재시도

- 권한 규칙:
1. `/setforumchannel`: 서버 소유자/관리자 또는 전역 허용 사용자(`DISCORD_GLOBAL_ADMIN_USER_IDS`)
2. `kheatmap/usheatmap`: 서버 채널에서만 실행

## 4) 설정 키/환경변수 (민감값 마스킹)
- `DISCORD_BOT_TOKEN=<MASKED>`
- `DEFAULT_FORUM_CHANNEL_ID=<OPTIONAL_CHANNEL_ID_OR_EMPTY>`
- `DISCORD_GLOBAL_ADMIN_USER_IDS=<OPTIONAL_USER_ID_LIST>`

데이터 경로:
- `data/state/state.json`
- `data/heatmaps/kheatmap/*.png`
- `data/heatmaps/usheatmap/*.png`
- `docs/references/external/*` (외부 원문 참고문서 보관 위치)

## 5) 실행/운영 체크리스트
- 로컬 실행:
```powershell
.\.venv\Scripts\Activate.ps1
python -m bot.main
```

- 커맨드 등록 확인:
1. 콘솔 `Synced ... global commands` 로그 확인
2. 디스코드 `/kheatmap`, `/usheatmap`, `/setforumchannel` 노출 확인

- 서버 초기 설정:
1. 각 서버에서 `/setforumchannel` 1회 실행
2. 이후 히트맵 커맨드 실행

- 종료 시 점검:
1. 백그라운드 봇 프로세스 종료 여부 확인
2. 중복 실행 세션 여부 확인

## 6) 테스트 실행 가이드
- 기본 테스트 (live 제외):
```bash
pytest
```

- 라이브 테스트:
```bash
pytest -m live
```

- flaky 대응:
1. 네트워크/사이트 차단 이슈 가능
2. 라이브 실패 시 1~2회 재시도 후 판정

## 7) 트러블슈팅 플레이북
- 명령어가 안 보일 때:
1. 봇이 해당 서버에 있는지 확인
2. 권한(Use Application Commands) 확인
3. global sync 전파 지연(수분~최대 1시간) 확인

- 포럼 게시 실패:
1. 길드별 포럼 채널 설정 여부 확인 (`/setforumchannel`)
2. 봇 권한 확인 (메시지/첨부/포럼 작성)

- 렌더 미완성 이미지:
1. 캐시 만료 후 재실행
2. live 테스트로 캡처 경로 검증

- 오프라인/중복 실행 이슈:
1. 로컬 프로세스 확인 후 종료
2. 동일 토큰 다른 호스트 실행 여부 점검

- 자동스크린샷이 안 도는 것처럼 보일 때:
1. 휴장일이면 정상 스킵인지 로그 확인 (`reason=holiday`)
2. 캘린더 판정 실패 로그 확인 (`reason=calendar-check-failed: ...`)

## 8) Skills 섹션 (전체 나열)
- `skill-creator` (indirect)
- 경로: `C:/Users/kin50/.codex/skills/.system/skill-creator/SKILL.md`
- 목적: 새로운 skill 생성/업데이트 절차 가이드
- 사용 시점: 반복 워크플로우를 스킬화할 때

- `skill-installer` (indirect)
- 경로: `C:/Users/kin50/.codex/skills/.system/skill-installer/SKILL.md`
- 목적: curated/GitHub 스킬 설치
- 사용 시점: 새 스킬을 세션에 추가할 때

참고: 현재 프로젝트 작업 자체는 위 두 스킬 없이도 수행 가능하며, 필요 시에만 사용한다.

## 9) 다음 세션 즉시 실행 TODO (5개)
1. `DART_API_KEY`를 확보해 `scripts/build_instrument_registry.py`로 국내 종목 master를 seed 기반이 아니라 full master로 재생성
2. `NEWS_PROVIDER_KIND=hybrid` + `MARKETAUX_API_TOKEN` 기준으로 해외 뉴스 fetch와 `/setnewsforum` 게시 흐름 실반영 검증
3. `Polygon` US fallback quote/reference adapter를 실제 `watch_poll` 보조 경로에 연결
4. `OpenFIGI` reconciliation job 또는 offline 보강 스크립트로 provider 간 symbol mapping 정합성 보강
5. `eod_summary`는 현재 pause 상태를 유지하고, 재개 요청이 생길 때만 `Twelve Data`/기타 매크로 소스로 재설계

## 10) 세션 종료 체크
1. 이번 작업이 검토/개발/설계 중 어디에 속하는지 판단
2. 해당 문서(`docs/context/*.md`)에 결과와 이유를 기록
3. 다음 세션이 바로 써야 할 사실만 `docs/context/session-handoff.md`에 업데이트
4. 미해결 이슈가 있으면 상태를 `open`, `blocked`, `done` 중 하나로 명시

## 인터페이스/타입 메모
- 상태 스키마:
1. `commands`
2. `guilds`
3. `commands.{command}.daily_posts_by_guild.{guild_id}.{date}`
4. `commands.{command}.last_images.{market}`

- 서버별 포럼 매핑 API 개념:
1. `set_guild_forum_channel_id(state, guild_id, channel_id)`
2. `get_guild_forum_channel_id(state, guild_id)`
3. `upsert_daily_post(... guild_id, forum_channel_id, ...)`
