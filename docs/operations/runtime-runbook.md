# 운영 런북

## 실행

로컬:

```bash
python -m bot.main
```

Docker:

```bash
docker compose up -d --build discord-bot
docker compose logs -f discord-bot
```

## 검증

```bash
python scripts/run_repo_checks.py
```

맥미니에서 재기동:

```bash
docker compose up -d --build discord-bot
docker compose logs --tail=100 discord-bot
```

## 자주 보는 문제

### 메시지가 안 감

1. 채널 ID가 맞는지 확인한다.
2. 봇 role에 채널 보기, 메시지 보내기, 스레드 만들기, embed 링크 권한이 있는지 확인한다.
3. 대시보드 delivery API 호출 실패 로그를 확인한다.
4. 전송 실패 로그가 운영 화면에 남는지 확인한다.

### 로그인 링크가 이상함

1. `STOCK_DASHBOARD_BASE_URL` 값을 확인한다.
2. 공개 URL이 바뀌었으면 bot을 재기동한다.
3. 토큰 만료 시간이 지나지 않았는지 확인한다.

### 역할 부여가 안 됨

1. 봇 role에 역할 관리 권한이 있는지 확인한다.
2. 봇 role이 지급하려는 종목 role보다 위에 있는지 확인한다.
3. 역할 선택 메시지를 다시 동기화한다.

### 관심종목 알림 스레드가 여러 개 생김

같은 일자 스레드를 재사용해야 한다.
채널/스레드 검색 권한 또는 상태 저장 실패를 먼저 확인한다.
