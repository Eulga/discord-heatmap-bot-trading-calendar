# Design Decisions

## 2026-03-19
- Context: 사용자가 보수적인 경제 뉴스 브리핑은 유지하되, 따로 읽을 수 있는 `트렌드 테마 뉴스` 게시글을 원했다.
- Decision: 트렌드 테마는 기존 국내/해외 뉴스 브리핑에 섞지 않고, 같은 스케줄에서 별도 `trendbriefing` thread 하나로 생성한다.
- Why:
1. 메인 브리핑은 거시 헤드라인과 고영향 종목 기사 위주의 보수적 선별 품질을 유지해야 했다.
2. 트렌드 테마는 더 넓은 후보군과 curated taxonomy 기반 점수화가 필요해, 같은 본문에 섞으면 메인 브리핑 판단 기준이 흐려질 수 있다.
3. 사용자가 원하는 형태는 국내/해외 브리핑에 붙는 부가 문단보다, 나중에 따로 열어볼 수 있는 독립 thread에 더 가까웠다.
- Impact:
1. 뉴스 스케줄은 같은 tick에서 `국내 브리핑`, `해외 브리핑`, `트렌드 테마 뉴스` 세 갈래를 관리한다.
2. `trendbriefing`은 starter message와 하위 content message를 따로 동기화해야 하므로, forum state의 `DailyPostEntry`에 `content_message_ids`가 추가됐다.
3. 한 지역이 3개 미만이면 그 지역은 placeholder로 처리하고, 두 지역 모두 3개 미만일 때만 thread 자체를 만들지 않는다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑 기사 수를 늘리자 한 본문 안에서 2000자 제한과 국내/해외 혼합 가독성 문제가 다시 드러났다.
- Decision: 뉴스 브리핑은 국내/해외를 하나의 starter message에 합치지 않고, region별 daily thread 2개로 분리한다.
- Why:
1. Discord starter message는 2000자 제한이 있어 기사 수를 늘릴수록 길이 압박 때문에 하위 기사를 잘라야 했다.
2. 사용자는 국내 시장 흐름과 해외 시장 흐름을 따로 읽는 편이 더 명확하다고 판단했고, region별 20건 soft cap도 그 구조에서 더 자연스럽다.
3. 기존 오늘자 통합 thread를 domestic thread로 재사용하고 global thread만 추가 생성하면 포럼 히스토리를 크게 깨지 않고 전환할 수 있다.
- Impact:
1. scheduler는 `newsbriefing-domestic`, `newsbriefing-global` 두 daily post를 관리하고, 완료 판정은 둘 다 존재할 때만 난다.
2. region별 품질/개수 변화가 서로의 본문 길이와 가독성에 영향을 덜 준다.
3. 포럼에는 하루에 뉴스 thread가 2개 생기므로, 운영상 소음이 과한지 관찰이 필요하다.
- Status: accepted

## 2026-03-19
- Context: 사용자가 "시장 전체 기사만 말고, 헤드라인급 개별 종목 기사도 포함"되길 원했고, 네이버 뉴스 검색 API가 직접 headline 플래그를 주는지도 다시 확인할 필요가 있었다.
- Decision: 네이버 뉴스 브리핑은 `headline API`를 기다리기보다 `거시 헤드라인 query + 종목 헤드라인 query` 2트랙 점수화로 운영한다.
- Why:
1. 네이버 공식 문서 기준 뉴스 검색 API는 검색 결과만 반환하며 `headline`, `top story`, `랭킹` 같은 직접 필드를 주지 않는다.
2. 따라서 "헤드라인 뉴스"는 API 속성이 아니라 adapter가 query 구성, source weight, event keyword, 중복 제거로 근사해야 한다.
3. 사용자가 원하는 결과는 거시 기사만 모아놓은 브리핑이 아니라, 시장 전체 흐름과 함께 중요한 종목 이벤트가 한두 개는 보이는 형태였다.
- Impact:
1. 현재 선별은 거시 기사와 고영향 종목 기사 둘 다 허용하지만, 종목 기사는 제목에 이벤트 신호가 없으면 통과하지 않는다.
2. provider는 지역별 score order를 유지하므로, 단순히 최근 기사라는 이유만으로 저품질 기사가 앞쪽을 차지하기 어렵다.
3. 같은 기사 링크/제목이 국내/해외 양쪽에 동시에 뜨는 경우 scheduler에서 한 번 더 제거한다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑 품질은 괜찮았지만, 아침/저녁 브리핑 특성상 지역별 기사 수를 더 넓게 보여 달라는 요구가 생겼다.
- Decision: 뉴스 브리핑은 지역별 최대 20건까지 허용하되, 품질 필터와 dedup을 통과한 기사만 게시하는 soft cap으로 유지한다.
- Why:
1. 브리핑 성격상 3~5건보다 더 넓은 커버리지가 유용하지만, 품질을 위해 억지로 20건을 채우면 다시 중복/저신호 기사가 섞일 수 있다.
2. 이미 적용한 dedup, blocklist, 소스 가중치 정책은 유지하고 상한만 넓히는 편이 현재 만족한 품질을 해치지 않는다.
3. 실제 실데이터 기준으로도 해외는 17건까지 자연스럽게 늘어났고, 국내는 5건만 남아 soft cap 요구와 잘 맞는다.
4. Discord starter message는 2000자 제한이 있어, 상한을 늘리더라도 본문 길이 안전장치가 함께 필요하다.
- Impact:
1. scheduler와 provider는 이제 20건까지 담을 수 있지만, 실제 게시 수는 지역별 기사 품질과 실데이터 상황에 따라 더 적을 수 있다.
2. 게시 본문은 Discord 2000자 제한을 넘기지 않도록 자동으로 잘리며, 길이 때문에 일부 하위 기사가 빠질 수 있다.
3. 기사 수를 더 늘리고 싶을 때는 상한을 또 올리기보다 dedup 기준과 query 세트 세분화를 먼저 검토한다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑에서 같은 장세 headline 반복과 개별 종목/ETF 기사 유입 때문에 국내 기사 품질이 흐려졌다.
- Decision: 국내 뉴스 브리핑은 개수보다 품질을 우선해, 시장 주제 단위 dedup과 개별 종목/ETF headline 제외 규칙을 적용한다.
- Why:
1. 사용자가 원하는 브리핑은 "주요뉴스/속보"에 가깝고, 같은 코스피 장세 기사가 여러 건 있거나 종목/ETF 기사까지 섞이면 목적과 멀어진다.
2. 네이버 검색 API는 중요도 랭크를 직접 주지 않으므로 adapter에서 주제 대표성과 다양성을 강제해야 한다.
3. 실제 실데이터 샘플에서도 국내 5건보다 국내 3건이 더 읽기 쉬운 결과를 보였다.
- Impact:
1. `domestic`은 `코스피`, `금리`, `환율` 같은 시장 축별 대표 기사 위주로 남는다.
2. 개별 종목 `주가` 기사와 ETF/상품 headline, 같은 장세 반복 headline은 대부분 탈락한다.
3. 기사 수가 5건보다 적어질 수 있지만, 이는 품질 우선 동작으로 허용한다.
- Status: accepted

## 2026-03-19
- Context: 네이버 뉴스 검색 API를 붙인 뒤 단일 query만으로는 `global`에 국내 기사나 코너형 기사까지 섞여, "주요뉴스/속보" 품질이 부족했다.
- Decision: 네이버 뉴스 브리핑은 단일 query 정렬을 그대로 쓰지 않고, 다중 query 후보 수집 후 gate 키워드, blocklist, 중요도 점수, 저신호 패널티를 거쳐 region별 상위 기사만 남긴다.
- Why:
1. 네이버 검색 API는 중요도, 주요뉴스 여부, source rank를 직접 주지 않아 adapter 내부 재정렬이 필요하다.
2. `global`은 미국 시장 직접 신호가 제목에 없으면 국내 시장 기사도 쉽게 섞이므로, region gate가 필요하다.
3. 기업 PR, 사진 기사, 반복 코너형 기사까지 그대로 통과시키면 브리핑 목적과 멀어진다.
- Impact:
1. `NaverNewsProvider`는 region별 다중 query를 호출하고 dedup 후 상위 기사만 반환한다.
2. `global`은 미국 시장 직접 신호가 제목에 있어야 통과 가능성이 높고, 국내 시장 키워드가 더 강하면 탈락한다.
3. 결과 품질은 query 세트와 키워드 사전에 계속 영향을 받으므로, 실데이터를 보며 튜닝을 이어가야 한다.
- Status: accepted

## 2026-03-19
- Context: 뉴스 브리핑을 mock에서 실제 데이터로 바꾸기 위해 네이버 뉴스 검색 API를 첫 번째 실사용 소스로 붙이는 작업을 시작했다.
- Decision: 뉴스 provider는 `NEWS_PROVIDER_KIND=naver` 설정으로 명시 전환하고, 네이버 응답의 `query`별 결과를 `domestic`/`global`로 태깅해 현재 `NewsItem` 계약에 맞춘다.
- Why:
1. 네이버 뉴스 검색 API는 국내 뉴스 접근성이 좋고 공식 문서가 안정적이지만, 응답에 `region`과 `source` 필드가 직접 들어 있지 않다.
2. 현재 scheduler/policy는 `domestic`/`global` 구분과 `source` 문자열을 기대하므로, query를 두 번 호출해 지역을 나누고 `originallink` 도메인으로 source를 유추하는 adapter가 필요하다.
3. 기본값을 바로 네이버로 바꾸면 키가 없는 개발 환경에서 부트나 테스트가 흔들릴 수 있으므로, explicit opt-in이 더 안전하다.
- Impact:
1. `.env`에 `NEWS_PROVIDER_KIND=naver`, `NAVER_NEWS_CLIENT_ID`, `NAVER_NEWS_CLIENT_SECRET`를 넣기 전까지는 기존 mock 뉴스가 유지된다.
2. 국내/해외 뉴스 품질은 `NAVER_NEWS_DOMESTIC_QUERY`, `NAVER_NEWS_GLOBAL_QUERY` 선택에 영향을 받으므로 실운영 전에 쿼리 튜닝이 필요하다.
3. title의 `<b>` 태그 제거, `pubDate` 파싱, 원문 링크 우선 사용, 최근 N시간 필터링은 adapter가 책임진다.
- Status: accepted

## 2026-03-18
- Context: 사용자는 `develop에 합쳐` 한 번으로 PR 생성부터 Codex Connector 리뷰 반영, 재검토, merge까지 이어지는 흐름을 원했다.
- Decision: `ship-develop`의 기본 reviewed shipping은 human approval gate가 아니라 Codex review loop로 둔다. 사람 승인 대기는 명시 요청일 때만 `--require-review`로 켠다.
- Why:
1. 이 저장소에서는 이미 `@codex review` -> feedback 확인 -> 수정 -> 재검토 -> merge 흐름을 실제로 사용해 왔다.
2. Codex review는 수 분 단위로 끝나는 자동 루프라서 한 세션 안에서 끝까지 처리하기 좋지만, 사람 리뷰는 대기 시간이 길어 one-shot workflow 기본값으로는 맞지 않는다.
3. 사용자가 원하는 UX는 "한 번 말하면 내가 끝까지 처리"에 가깝고, 그 요구는 Codex review loop가 더 잘 맞는다.
- Impact:
1. 기본 `develop으로 합쳐`는 PR 생성 후 `@codex review`를 요청하고, findings가 있으면 수정/재검토를 반복한다.
2. `사람 리뷰 받고 develop에 합쳐` 같은 요청일 때만 human review gate를 추가로 사용한다.
3. `ship_develop.py`는 Codex review 결과를 `clean`, `findings`, `pending`으로 판별해 merge 여부를 결정한다.
- Status: accepted

## 2026-03-18
- Context: `ship-develop`이 PR 생성 직후 바로 merge해서, 사용자가 원한 "리뷰 확인 후 merge" 흐름과 맞지 않았다.
- Decision: `ship-develop`은 review gate를 지원하고, `develop` shipping의 기본 흐름은 two-pass로 운영한다. 첫 실행은 PR 생성 또는 갱신 후 `review-required` 상태로 멈추고, 승인 후 같은 스크립트를 다시 실행해 merge한다.
- Why:
1. 이 저장소의 `develop` 브랜치는 현재 GitHub branch protection이 없어서, review 강제는 repo 설정이 아니라 shipping workflow 내부에서 처리해야 한다.
2. 사람 리뷰는 수분에서 수시간이 걸릴 수 있어 한 세션에서 오래 기다리는 것보다 "같은 도구를 다시 실행하는 2단계"가 현실적이다.
3. 도구를 둘로 나누지 않고 review gate 옵션을 추가하면 PR 생성과 merge 재개가 같은 인터페이스 안에서 유지된다.
- Impact:
1. 이후 `develop으로 합쳐` 류 요청은 기본적으로 리뷰 대기 상태를 존중한다.
2. 첫 실행에서 merge가 되지 않아도 정상일 수 있고, `review-required`는 실패가 아니라 대기 상태다.
3. 긴 대기 대신 승인 후 같은 branch에서 `ship-develop`을 다시 실행하면 된다.
- Status: accepted

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
