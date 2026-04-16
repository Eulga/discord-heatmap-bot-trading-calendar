# Live 통합 테스트 케이스

## 문서 목적
- 이 문서는 네트워크와 실사이트 호출을 포함하는 live integration만 별도로 관리한다.
- 기본 integration 문서인 [integration-test-cases.md](./integration-test-cases.md)와 중복 서술하지 않고, flaky 해석 규칙과 운영 전제만 따로 명시한다.

## 실행 명령

```bash
# Windows: py -3 scripts/run_repo_checks.py --include-live
# macOS/Linux: python3 scripts/run_repo_checks.py --include-live
```

## 전제조건
- Playwright Chromium이 설치돼 있어야 한다.
- 외부 사이트 접근이 가능한 네트워크여야 한다.
- 실사이트 DOM, anti-bot, 응답 속도에 따라 flaky할 수 있다.
- 실패 시 즉시 코드 결함으로 단정하지 말고 1~2회 재시도 후 판정한다.

## 해석 규칙
- 이 문서의 두 케이스는 `pytest.ini` 기본 옵션 `-m "not live"`에서는 제외된다.
- 따라서 기본 integration suite pass만으로는 live capture 건강성이 보장되지 않는다.
- 반대로 live 실패 1회만으로 즉시 회귀라고 판단하지 말고, 같은 시점의 네트워크/사이트 차단/렌더 타임아웃 가능성을 먼저 확인한다.

## LIV-KR-01 한국장 live 캡처
- 테스트 ID: `LIV-KR-01`
- 원본 테스트 함수명: `tests/integration/test_capture_korea_live.py::test_capture_korea_live`
- 목적: 한국 시장 캡처 provider가 실사이트를 열고 이미지 파일을 실제로 생성하는지 확인한다.
- 대상 URL/시장: `KOREA_MARKET_URLS["kospi"]`, 한국장 `kospi`.
- 전제조건: Chromium 브라우저 설치, 외부 네트워크 허용, 대상 사이트 접근 가능.
- 성공 기준:
  - `capture()`가 경로를 반환한다.
  - 반환 경로의 파일이 실제로 존재한다.
  - 파일 크기가 `120000` bytes보다 크다.
  - 비정상적으로 작은 placeholder/빈 이미지가 아니다.
- 대표 실패 원인:
  - 네트워크 단절 또는 DNS 실패
  - 대상 사이트 차단 또는 anti-bot 응답
  - DOM 변경으로 렌더 완료 조건이 깨짐
  - 렌더 타임아웃 또는 브라우저 실행 실패
- 운영 해석 규칙:
  - 1회 실패만으로 코드 결함이라고 단정하지 않는다.
  - 같은 환경에서 1~2회 재시도 후에도 반복 실패하면 캡처 로직 또는 대상 사이트 DOM drift를 우선 의심한다.

## LIV-US-01 미국장 live 캡처
- 테스트 ID: `LIV-US-01`
- 원본 테스트 함수명: `tests/integration/test_capture_us_live.py::test_capture_us_live`
- 목적: 미국 시장 캡처 provider가 실사이트를 열고 이미지 파일을 실제로 생성하는지 확인한다.
- 대상 URL/시장: `US_MARKET_URLS["sp500"]`, 미국장 `sp500`.
- 전제조건: Chromium 브라우저 설치, 외부 네트워크 허용, 대상 사이트 접근 가능.
- 성공 기준:
  - `capture()`가 경로를 반환한다.
  - 반환 경로의 파일이 실제로 존재한다.
  - 파일 크기가 `70000` bytes보다 크다.
  - 비정상적으로 작은 placeholder/빈 이미지가 아니다.
- 대표 실패 원인:
  - 네트워크 단절 또는 해외 사이트 응답 지연
  - 대상 사이트 차단 또는 anti-bot 응답
  - DOM 변경으로 렌더 완료 신호가 사라짐
  - 렌더 타임아웃 또는 브라우저 프로세스 실패
- 운영 해석 규칙:
  - 한국장보다 사이트 응답 시간이 더 흔들릴 수 있으므로 재시도 관찰이 특히 중요하다.
  - 반복 실패가 이어지면 실사이트 구조 변경과 캡처 selector/완료 조건 drift를 먼저 확인한다.
