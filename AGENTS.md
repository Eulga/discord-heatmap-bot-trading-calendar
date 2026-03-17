# AGENTS.md

## 1) 문서 목적
- 이 문서는 다음 세션에서 프로젝트 컨텍스트를 빠르게 복구하기 위한 단일 진입 문서다.
- 우선 읽기 순서:
1. 이 문서
2. `docs/context/README.md`
3. `docs/context/session-handoff.md`
4. `README.md`
5. `bot/app/settings.py`
6. `bot/features/runner.py`
7. `bot/forum/repository.py`

## 1-1) 컨텍스트 저장 원칙
- 앞으로의 검토, 개발, 설계 대화 결과는 `docs/context/*`에 종류별로 누적 저장한다.
- 목적은 세션/작업 위치가 달라도 같은 프로젝트 판단 기준을 재사용하는 것이다.
- 문서 분류:
1. `docs/context/session-handoff.md`: 현재 활성 컨텍스트, 최근 결정, 다음 액션
2. `docs/context/design-decisions.md`: 설계 결정과 이유, 대안, 영향 범위
3. `docs/context/development-log.md`: 구현 변경, 작업 단위, 검증 결과
4. `docs/context/review-log.md`: 코드 리뷰/버그/리스크/회귀 포인트
- 저장 규칙:
1. 작업 종료 시 관련 문서를 최소 1곳 이상 업데이트한다.
2. 설계 판단이 바뀌면 `design-decisions.md`에 남기고, 실행 결과는 `development-log.md`에도 반영한다.
3. 리뷰에서 나온 이슈는 해결 전후와 상관없이 먼저 `review-log.md`에 남긴다.
4. 다음 세션이 바로 이어받아야 할 내용은 반드시 `session-handoff.md`에 요약한다.
5. 비밀값/토큰/개인정보는 저장하지 않는다.

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
2. 저장 위치: `data/heatmaps/state.json` -> `guilds.{guild_id}.forum_channel_id`

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
- `data/heatmaps/state.json`
- `data/heatmaps/kheatmap/*.png`
- `data/heatmaps/usheatmap/*.png`

## 5) 실행/운영 체크리스트
- 로컬 실행:
```bash
source .venv/Scripts/activate
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
1. `python -m bot.main`으로 봇 기동 확인
2. 대상 서버에서 `/setforumchannel` 매핑 확인
3. `/kheatmap` 1회 실행 후 포럼 포스트 생성/수정 동작 점검
4. `pytest` 실행으로 기본 회귀 확인
5. 로그에서 sync/업서트 오류 유무 확인

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
