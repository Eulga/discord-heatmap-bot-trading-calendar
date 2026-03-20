# Development Log

## 2026-03-20
- Context: `master -> develop` sync PR `#10` review에서 forum channel resolution API 오류를 `missing_forum`으로 숨기지 말아야 한다는 P1 finding이 나왔다.
- Change:
1. `bot/features/intel_scheduler.py`의 `_resolve_guild_forum_channel_id()`는 이제 `discord.NotFound`만 진짜 missing channel로 취급하고, 다른 `fetch_channel()` 오류는 그대로 상위로 올린다.
2. 뉴스/EOD scheduler는 forum resolution 중 API 오류가 나면 `missing_forum`/`skipped`로 처리하지 않고 `forum-resolution-failed:...` detail과 함께 job status를 `failed`로 기록한다.
3. `tests/integration/test_intel_scheduler_logic.py`에 뉴스/EOD 각각의 forum resolution API failure 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python.exe -m pytest tests/integration/test_intel_scheduler_logic.py -k "forum_resolution or fallback_forum or news_job or eod_job"` 기준 `20 passed, 4 deselected`
- Next:
1. 수정 커밋을 PR `#10`에 푸시하고 `@codex review`를 다시 요청한다.
2. review가 clean이면 `develop`에 merge해 `master` 릴리스 수정과 `develop` 기준선을 다시 일치시킨다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 추가 review 2건에 맞춰 뉴스/트렌드 partial-delivery status false positive를 닫았다.
- Change:
1. `bot/features/intel_scheduler.py`는 `news_briefing`을 `posted > 0`만으로 `ok` 처리하지 않고, 같은 run의 `failed` count가 0일 때만 `ok`를 남기도록 조정했다.
2. 같은 함수는 `trend_briefing`도 `trend_posted > 0 and trend_failed == 0`일 때만 `ok`가 되도록 맞췄다.
3. `tests/integration/test_intel_scheduler_logic.py`에 뉴스 partial-failure, 트렌드 partial-failure 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py -k "news_job or eod_job"` 기준 `18 passed, 4 deselected`
2. `.\.venv\Scripts\python -m pytest` 기준 `82 passed, 2 deselected`
- Next:
1. release branch 최신 커밋을 PR `#9`에 푸시하고 `@codex review`를 다시 요청한다.
2. 새 review가 clean이면 `master`로 squash merge를 진행한다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 마지막 남은 Codex review finding으로 EOD partial-failure status false positive를 닫았다.
- Change:
1. `bot/features/intel_scheduler.py`는 `eod_summary`를 `posted > 0`만으로 `ok` 처리하지 않고, 같은 run의 `failed` count가 0일 때만 `ok`를 남기도록 조정했다.
2. `tests/integration/test_intel_scheduler_logic.py`에 한 guild post 성공 뒤 다른 guild post 실패가 이어지는 mixed-result EOD 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py -k "eod_job"` 기준 `5 passed, 15 deselected`
2. `.\.venv\Scripts\python -m pytest` 기준 `80 passed, 2 deselected`
- Next:
1. release branch 최신 커밋을 PR `#9`에 푸시하고 `@codex review`를 다시 요청한다.
2. 새 review가 clean이면 `master`로 squash merge를 진행한다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 추가 review에 맞춰 mixed watch_poll failure와 forum stale content id 정리를 보강했다.
- Change:
1. `bot/features/intel_scheduler.py`는 이제 `quote_failures`, `channel_failures`, `send_failures`가 하나라도 있으면 `watch_poll=failed`를 기록한다.
2. `tests/integration/test_intel_scheduler_logic.py`에 partial success 뒤 quote failure가 따라오는 mixed-result watch poll 회귀 테스트를 추가했다.
3. `bot/forum/service.py`는 삭제 대상 follow-up message가 이미 `NotFound`면 stale `content_message_ids`를 상태에서 제거하도록 바꿨다.
4. `tests/integration/test_forum_upsert_flow.py`에 missing follow-up message id cleanup 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py tests/integration/test_forum_upsert_flow.py` 기준 `27 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `79 passed, 2 deselected`
- Next:
1. 수정 커밋을 release branch에 푸시하고 PR `#9`에 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: release PR `#9`의 추가 P1 review로 뉴스/EOD 전역 forum fallback의 guild ownership 검증을 보강했다.
- Change:
1. `bot/features/intel_scheduler.py`에 `_resolve_guild_forum_channel_id()` helper를 추가해, 뉴스와 장마감이 resolved forum channel의 guild 소유권을 확인한 뒤에만 pending queue에 넣도록 바꿨다.
2. 다른 guild 소속 global fallback forum은 `missing_forum`으로 처리해 provider fetch와 posting을 시작하지 않게 했다.
3. `tests/integration/test_intel_scheduler_logic.py`에 뉴스/EOD 각각의 cross-guild fallback forum 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 기준 `18 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `77 passed, 2 deselected`
- Next:
1. 수정 커밋을 release branch에 푸시하고 PR `#9`에 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: `develop -> master` release PR `#9` 재검토에서 watch alert delivery failure를 `ok`로 숨기지 않도록 후속 수정했다.
- Change:
1. `bot/features/intel_scheduler.py`는 `watch_poll` detail에 `alert_attempts`를 추가하고, `channel.send(...)` 실패가 한 건이라도 있으면 `watch_poll=failed`로 기록하도록 바꿨다.
2. `tests/integration/test_intel_scheduler_logic.py`에 실제 signal은 발생하지만 Discord delivery가 실패하는 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 기준 `16 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `75 passed, 2 deselected`
- Next:
1. 수정 커밋을 release branch에 푸시하고 PR `#9`에 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: `develop -> master` 릴리스 검토 중 PR `#9` Codex review가 `watch_poll` 운영 정합성 2건을 지적했다.
- Change:
1. `bot/features/intel_scheduler.py`는 watch alert channel을 해석할 때 channel의 guild 소유권을 확인하고, 다른 guild 채널로 fallback 되면 해당 guild를 실패로 처리하도록 보완했다.
2. 같은 함수는 watch poll run별 `processed`, `quote_failures`, `channel_failures`, `missing_channel_guilds`, `send_failures`를 detail에 남기고, 전부 실패했으면 `failed`, 대상이 없으면 `skipped`, 일부라도 처리했으면 `ok`를 기록하도록 바꿨다.
3. `tests/integration/test_intel_scheduler_logic.py`에 cross-guild fallback 차단과 all-quote-failure status 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/integration/test_intel_scheduler_logic.py` 기준 `15 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `74 passed, 2 deselected`
- Next:
1. PR `#9`에 수정 커밋을 푸시하고 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: PR `#8` Codex review 후속 지적 2건을 반영했다.
- Change:
1. `bot/forum/service.py`는 starter thread/message state를 follow-up content sync 전에 먼저 기록하고, content message ids도 sync/deletion 진행에 따라 부분 상태로 갱신하도록 바꿨다.
2. `bot/features/news/trend_policy.py`는 단일 theme block이 너무 길어도 안전하게 분할 또는 truncate되도록 보완해, region message가 Discord 길이 제한을 넘지 않게 했다.
3. `tests/integration/test_forum_upsert_flow.py`, `tests/unit/test_trend_policy.py`에 Codex review 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest` 기준 `72 passed, 2 deselected`
- Next:
1. 같은 PR `#8`에 수정 커밋을 푸시하고 Codex review를 다시 요청한다.
- Status: done

## 2026-03-19
- Context: 기존 국내/해외 뉴스 브리핑과 별도로 `트렌드 테마 뉴스` thread를 추가했다.
- Change:
1. `bot/intel/providers/news.py`에 `NewsAnalysis`, `ThemeDefinition`, `ThemeBrief`, `TrendThemeReport`를 추가하고, conservative briefing items와 wider trend candidates를 분리해 계산하도록 바꿨다.
2. 국내/해외 curated theme taxonomy와 probe query를 넣고, 반복 노출 + 소스 다양성 + 대표 종목/이벤트 신호 기반으로 region별 3~5개 테마를 점수화하도록 구현했다.
3. `bot/forum/service.py`와 `bot/app/types.py`는 starter message 외에 `content_message_ids`를 저장하고, thread 하위 message를 edit/create/delete할 수 있게 확장했다.
4. `bot/features/news/trend_policy.py`를 추가해 `[YYYY-MM-DD 트렌드 테마 뉴스]` starter message와 국내/해외 section message 렌더링을 분리했다.
5. `bot/features/intel_scheduler.py`는 같은 뉴스 tick에서 `trendbriefing` thread를 추가 생성 또는 갱신하며, 한 지역이 3개 미만이면 placeholder로 처리하고 두 지역 모두 3개 미만일 때만 `trend_briefing`을 `skipped`로 남긴다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest` 기준 `69 passed, 2 deselected`
2. 실제 네이버 실데이터 분석 기준 국내 테마는 `반도체`, `자동차` 2개만 남았고, 해외는 `금리/Fed`, `AI/반도체`, `에너지/원유`, `메가캡 기술주` 4개가 남았다.
3. 실제 Discord 반영 결과 `[2026-03-19 트렌드 테마 뉴스]` thread가 `https://discord.com/channels/332110589969039360/1484089919285497967`에 생성됐다.
4. 실제 thread는 starter message + 국내 placeholder message + 해외 theme message 구조로 저장됐고, `trend_briefing` status는 `ok`, detail은 `posted=1 failed=0 missing_forum=0 domestic_themes=2 global_themes=4`였다.
- Next:
1. 국내 recall을 더 올릴지 보고 `전력설비`, `방산`, `건설/원전` probe/score를 한 번 더 조정한다.
2. 해외 `금리/Fed`와 `AI/반도체` 비중이 과하면 theme score balance를 추가 조정한다.
- Status: done

## 2026-03-19
- Context: 뉴스 브리핑을 한 본문에 합치지 않고 국내/해외를 별도 daily thread 2개로 나누는 변경을 마무리했다.
- Change:
1. `bot/features/news/policy.py`에 region별 제목/본문 builder를 추가해 `[YYYY-MM-DD 국내 경제 뉴스 브리핑]`, `[YYYY-MM-DD 해외 경제 뉴스 브리핑]` 형식을 지원했다.
2. `bot/features/intel_scheduler.py`는 `newsbriefing-domestic`, `newsbriefing-global` 두 command key로 각각 upsert하도록 바뀌었고, 국내/해외 제목 날짜도 scheduler 실행 시점 `now`를 기준으로 맞췄다.
3. `bot/forum/service.py`는 기존 thread를 재사용할 때 제목이 달라지면 starter message 수정 전에 thread 이름도 함께 바꾸도록 유지했다.
4. 오늘자 기존 통합 `newsbriefing` thread record는 domestic thread로 migration/reuse되고, global thread는 새로 생성되도록 실제 운영 경로를 검증했다.
- Verification:
1. `.\.venv\Scripts\python -B -m pytest tests/unit/test_news_policy.py tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `28 passed`
2. `.\.venv\Scripts\python -B -m pytest` 기준 `61 passed, 2 deselected`
3. 실제 Discord 반영 후 domestic thread는 기존 `https://discord.com/channels/332110589969039360/1484055161600213092`를 재사용하며 제목이 `[2026-03-19 국내 경제 뉴스 브리핑]`로 바뀌었다.
4. 실제 Discord 반영 후 global thread `https://discord.com/channels/332110589969039360/1484079599175336057`가 새로 생성됐고 제목은 `[2026-03-19 해외 경제 뉴스 브리핑]`였다.
5. 실행 후 `news_briefing` status는 `ok`, detail은 `posted=1 failed=0 missing_forum=0 domestic=5 global=7`이었다.
- Next:
1. Discord에서 국내/해외가 분리된 형태가 실제 읽기 경험에서 더 나은지 확인한다.
2. 글로벌 기사 수와 품질이 다시 흔들리면 query 세트와 source weight를 한 번 더 조정한다.
- Status: done

## 2026-03-19
- Context: 사용자가 뉴스 브리핑이 너무 포괄적이라며, 거시 헤드라인은 유지하되 헤드라인급 개별 종목 기사도 포함되길 원했다.
- Change:
1. `bot/intel/providers/news.py`에서 선별 구조를 `거시 query + 종목 query` 2트랙으로 바꾸고, 종목 기사는 실적/가이던스/수주/규제 같은 고영향 이벤트가 제목에 직접 드러날 때만 통과시키도록 조정했다.
2. provider 마지막 단계가 지역별 점수순 결과를 다시 최신순으로 섞던 동작을 제거해, 저품질 최신 기사가 상위로 튀지 않게 했다.
3. scheduler는 `story_key()` 기준으로 국내/해외를 가로지르는 동일 기사 중복을 한 번 더 제거한다.
4. 실제 Discord thread를 새 선별 결과로 다시 갱신했다.
- Verification:
1. 네이버 공식 문서 기준 뉴스 검색 API는 검색 결과를 반환할 뿐 `headline/top story` 같은 직접 플래그는 제공하지 않음을 다시 확인했다.
2. `.\.venv\Scripts\python -B -m pytest` 기준 `58 passed, 2 deselected`
3. 실데이터 샘플 기준 현재 결과는 `domestic=6`, `global=11`, `body_len=1956`이다.
4. Discord API 갱신 결과 `updated_guilds=1`이며 thread는 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 체감 품질을 보고 `개장시황`, 설명형 해설 기사까지 더 줄일지 판단한다.
2. 필요하면 `NAVER_NEWS_*_STOCK_QUERIES`와 stock alias를 한 번 더 튜닝한다.
- Status: done

## 2026-03-19
- Context: 20건 상한과 본문 길이 보완 후, 오늘자 Discord 뉴스 브리핑 thread를 새 본문으로 다시 갱신했다.
- Change:
1. 실제 네이버 fetch 결과로 생성한 새 본문을 Discord starter message에 직접 PATCH해 오늘자 `newsbriefing` thread를 최신 내용으로 갱신했다.
2. 같은 흐름에서 `news_provider` / `news_briefing` 상태도 현재 개수(`domestic=5`, `global=17`) 기준으로 다시 저장했다.
- Verification:
1. Discord API 수정 결과 `updated_guilds=1`, `body_len=1987`, `domestic=5`, `global=17`
2. 갱신 대상 thread는 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 가독성과 기사 밀도를 보고 이 개수 범위를 유지할지 확인한다.
2. 국내 기사 수를 더 늘리고 싶으면 dedup 세분화가 필요한지 검토한다.
- Status: done

## 2026-03-19
- Context: 사용자가 아침/저녁 브리핑의 기사 수를 지역별 최대 20건까지 넓히되, 품질 필터 때문에 정확히 20건을 강제하지는 않길 원했다.
- Change:
1. `bot/app/settings.py`, `bot/features/intel_scheduler.py`, `.env.example`, `README.md`, `docs/specs/external-intel-api-spec.md`를 갱신해 뉴스 브리핑 지역별 상한을 20건 기준으로 맞췄다.
2. `bot/intel/providers/news.py`의 `NaverNewsProvider` 내부 cap도 `10 -> 20`으로 풀고, query 인자 타입 힌트를 실제 구현처럼 `str | Sequence[str]`로 맞췄다.
3. `tests/unit/test_news_provider.py`에 provider가 한 지역에서 최대 20건까지 반환할 수 있는지 검증하는 테스트를 추가했다.
4. `bot/features/news/policy.py`에 Discord 2000자 제한 안에서 본문을 안전하게 자르는 로직을 추가해, 개수 상한을 올려도 게시가 실패하지 않게 했다.
5. `tests/integration/test_intel_scheduler_logic.py`와 `tests/unit/test_news_policy.py`에 scheduler 상한 반영과 본문 길이 제한 회귀 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_news_policy.py tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `20 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `53 passed, 2 deselected`
3. 실제 네이버 fetch 샘플 기준 현재 설정으로 `limit=20`, `domestic=5`, `global=17`이었다.
4. 같은 실데이터 기준 실제 게시 본문 길이는 `1987`자라 Discord 2000자 제한 안에 들어간다.
- Next:
1. Discord thread를 다시 갱신할 때 현재 실데이터 기준 최대 20건 범위로 본문이 반영되는지 확인한다.
2. 국내 기사 수가 계속 낮으면 query 세트는 유지한 채 dedup 규칙을 더 세분화할지 검토한다.
- Status: done

## 2026-03-19
- Context: 국내 뉴스 품질 튜닝 후 오늘자 Discord 뉴스 브리핑 thread를 최신 결과로 다시 갱신했다.
- Change:
1. 실제 Discord client로 오늘자 `newsbriefing` thread를 다시 upsert해 최신 필터 결과를 반영했다.
2. 갱신된 본문 기준 국내는 3건, 해외는 4건으로 정리됐다.
- Verification:
1. 갱신 실행 결과 `updated_guilds=1`, `domestic=3`, `global=4`
2. 실제 본문에는 국내 `한은 총재/코스피 급락/국고채 금리`, 해외 `연준/마이크론/S&P500` 축이 반영됐다.
- Next:
1. Discord에서 체감 품질을 다시 확인한다.
2. 필요하면 `global`의 `tokenpost.kr` 같은 소스 패널티를 추가 조정한다.
- Status: done

## 2026-03-19
- Context: 국내 뉴스 브리핑에서 중복 장세 headline과 개별 종목/ETF 기사를 더 강하게 줄이는 품질 튜닝
- Change:
1. `bot/intel/providers/news.py`에 시장 주제 단위 dedup(`코스피`, `환율`, `금리`, `연준` 등)을 넣어 같은 장세 headline이 여러 건 남지 않게 했다.
2. 국내 기본 query 세트를 `국내 증시, 코스피 지수, 코스닥 지수, 원달러 환율, 한국은행 금리`로 좁혔다.
3. 소스 가중치를 조정해 `news.einfomax.co.kr` 같은 시장 소스를 더 우대하고, `tokenpost.kr`, `press9.kr` 등은 더 약하게 반영했다.
4. 국내 제목에 `주가`, `ETF`가 들어가는 개별 종목/상품 headline은 직접 제외하도록 필터를 추가했다.
5. 실제 `.env`에도 같은 query 세트를 반영했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `16 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `49 passed, 2 deselected`
3. 실데이터 샘플 기준 `news_briefing=ok`, `domestic=3`, `global=4`였고, 국내는 코스피/국고채 금리/환율 3건으로 정리됐다.
- Next:
1. 이 3건 중심 결과가 Discord 체감에서 더 낫다고 판단되면 실제 포럼 게시에도 그대로 적용한다.
2. 필요하면 글로벌 소스 패널티도 한 번 더 조정한다.
- Status: done

## 2026-03-19
- Context: 뉴스 브리핑 실데이터를 실제 Discord 포럼에 1회 게시해 결과물 확인 경로를 검증했다.
- Change:
1. 실제 `DISCORD_BOT_TOKEN`으로 Discord client를 login한 뒤 `_run_news_job()`를 수동 1회 실행했다.
2. 오늘 날짜(`2026-03-19`) 기준 `newsbriefing` daily post record가 새로 생성되는지 state와 Discord thread를 함께 확인했다.
- Verification:
1. 실행 전 오늘자 `newsbriefing` record는 비어 있었고, 실행 후 guild `332110589969039360`에 thread record가 생성됐다.
2. 생성된 thread 제목은 `[2026-03-19 아침 경제 뉴스 브리핑]`였다.
3. 실제 thread URL은 `https://discord.com/channels/332110589969039360/1484055161600213092`다.
- Next:
1. Discord에서 실제 본문 가독성과 기사 품질을 확인한다.
2. 체감 품질이 부족하면 국내 query/키워드/소스 가중치를 추가 조정한다.
- Status: done

## 2026-03-19
- Context: 네이버 뉴스 브리핑 품질을 "주요뉴스/속보" 쪽으로 끌어올리기 위해 필터링을 강화했다.
- Change:
1. `bot/intel/providers/news.py`에 region별 다중 query 후보 수집, dedup 후 최고 점수 유지, 소스당 최대 2건 제한을 추가했다.
2. region gate 키워드, blocklist, 저신호 패널티(`표창`, `공로`, `행사` 등), 사진/코너형 기사 제외 로직을 넣었다.
3. `bot/app/settings.py`, `bot/features/intel_scheduler.py`, `.env.example`, `README.md`를 갱신해 `NAVER_NEWS_DOMESTIC_QUERIES`, `NAVER_NEWS_GLOBAL_QUERIES` 다중 query 설정을 지원하게 했다.
4. `tests/unit/test_news_provider.py`에 global 오염 억제, 다중 query 점수 선택, 기업 PR 패널티 테스트를 추가했다.
- Verification:
1. `.\.venv\Scripts\python -m pytest tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 기준 `12 passed`
2. `.\.venv\Scripts\python -m pytest` 기준 `45 passed, 2 deselected`
3. 실제 네이버 자격증명으로 `_run_news_job()`를 다시 실행해 `news_briefing=ok`, `domestic=5`, `global=5`와 브리핑 본문 렌더링을 재확인했다.
4. 실데이터 기준 `global` 결과는 FOMC/연준/나스닥 중심으로 정리돼 이전보다 purity가 올라갔고, `domestic`은 아직 일부 테마/해설형 기사가 남아 추가 튜닝 여지가 있다.
- Next:
1. `domestic` 쪽에서도 시장영향 기사와 테마/기획 기사 분리를 더 잘하는 키워드나 소스 정책을 조정한다.
2. query 세트를 실운영 결과에 맞게 다듬고, 필요하면 source allowlist/penalty를 더 세분화한다.
- Status: done

## 2026-03-19
- Context: `.env`에 실제 네이버 Client ID/Secret을 넣은 뒤 뉴스 브리핑 실데이터 fetch를 검증했다.
- Change:
1. `NEWS_PROVIDER_KIND=naver` 환경에서 `intel_scheduler._run_news_job()`를 dummy forum state와 fake post writer로 실행해 실제 네이버 API 응답이 현재 scheduler 흐름을 통과하는지 확인했다.
2. provider status, job status, 렌더된 브리핑 본문을 함께 점검했다.
- Verification:
1. 실데이터 실행 결과 `news_briefing` job status는 `ok`, detail은 `posted=1 failed=0 missing_forum=0 domestic=5 global=5`였다.
2. `news_provider` status는 `ok=True`, message는 `fetched=10`이었다.
3. 브리핑 본문은 실제 기사 10건으로 렌더됐고 title/source/time/link 형식이 현재 policy와 호환됐다.
4. 다만 `NAVER_NEWS_GLOBAL_QUERY=미국 증시` 결과에 국내 시장 성격 기사가 일부 섞여, query tuning 필요성이 확인됐다.
- Next:
1. `NAVER_NEWS_GLOBAL_QUERY`를 더 구체적인 해외 시장 키워드 조합으로 조정해 결과 품질을 비교한다.
2. 필요하면 국내/해외 query를 다중 호출 또는 제외 키워드 방식으로 확장한다.
- Status: done

## 2026-03-19
- Context: 네이버 뉴스 검색 API를 아침 뉴스 브리핑의 첫 실제 provider 후보로 붙이는 작업
- Change:
1. `bot/intel/providers/news.py`에 `NaverNewsProvider`와 `ErrorNewsProvider`를 추가했다.
2. 네이버 응답의 title HTML 태그 제거, `pubDate` 파싱, 원문 링크 우선 사용, 원문 도메인 기반 source 추출, 최근 N시간 필터를 adapter에 넣었다.
3. `bot/app/settings.py`, `bot/features/intel_scheduler.py`, `.env.example`, `README.md`를 갱신해 `NEWS_PROVIDER_KIND=naver`와 네이버 Client ID/Secret 기반 opt-in 설정을 추가했다.
4. `tests/unit/test_news_provider.py`를 추가해 정규화/필터링과 인증 실패 매핑을 검증했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile bot\intel\providers\news.py bot\features\intel_scheduler.py bot\app\settings.py` 통과
2. `.\.venv\Scripts\python -m pytest tests/unit/test_news_provider.py tests/integration/test_intel_scheduler_logic.py` 통과
3. `.\.venv\Scripts\python -m pytest` 기준 `42 passed, 2 deselected`
- Next:
1. 실제 네이버 Client ID/Secret을 `.env`에 넣고 `NEWS_PROVIDER_KIND=naver`로 바꿔 실데이터 fetch를 확인한다.
2. `NAVER_NEWS_DOMESTIC_QUERY`, `NAVER_NEWS_GLOBAL_QUERY` 기본값이 브리핑 품질에 맞는지 실운영 결과를 보고 조정한다.
3. 필요하면 `source-status`에 provider kind나 query 품질 관련 힌트를 더 노출한다.
- Status: done

## 2026-03-18
- Context: `ship-develop` Codex review loop을 실제로 마무리해 `develop`에 반영하고, 임시 backup 브랜치도 정리했다.
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`가 PR head SHA가 바뀐 뒤 예전 `clean` review 결과를 재사용하지 않도록 `headRefOid` drift를 `pending`으로 처리하게 했다.
2. PR `#7`을 `@codex review` 재확인 후 squash merge해 `develop`에 반영했다.
3. 로컬 backup 브랜치 `codex/develop-diverged-backup-20260317`, `codex/review-fixes-backup-20260318`를 삭제했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
3. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --codex-review --wait-codex-seconds 300 --wait-seconds 600` 실행으로 PR `#7`이 `clean` 후 merge됨을 확인
4. `git status --short --branch` 기준 현재 로컬은 `develop...origin/develop`이고 작업 트리는 깨끗하다
- Next:
1. `docs/specs/external-intel-api-spec.md` 기준으로 첫 실제 외부 provider 구현 대상을 고른다. 우선순위는 `NewsProvider`다.
2. `.\.venv\Scripts\python -m pytest`와 `python -m bot.main` 기준으로 `develop` 부트와 기본 회귀를 다시 확인한다.
3. Discord 실운영 환경에서 히트맵 게시 흐름과 확장 scheduler 흐름 검증 계획을 구체화한다.
- Status: done

## 2026-03-18
- Context: PR `#7`의 Codex review에서 comment pagination 누락으로 review 상태를 오판할 수 있다는 지적을 반영하는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에 `get_paginated_api_items()`를 추가했다.
2. `get_issue_comments()`와 `get_review_comments()`가 GitHub REST 기본 30개 제한에 묶이지 않도록 `per_page=100` paging 루프를 사용하게 바꿨다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. historical PR 분류 재검증:
   - PR `#4` clean 케이스는 여전히 `clean`
   - PR `#7` findings 케이스는 `findings`로 유지
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 수정 커밋을 PR `#7`에 푸시하고 `@codex review`를 다시 요청한다.
- Status: done

## 2026-03-18
- Context: `ship-develop` 기본 동작을 human review gate에서 Codex review loop 중심으로 바꾸는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에 `--codex-review`, `--wait-codex-seconds` 옵션을 추가했다.
2. 스크립트가 `@codex review` 코멘트를 남기고, `chatgpt-codex-connector` issue comment / `chatgpt-codex-connector[bot]` review comment 패턴을 읽어 `clean`, `findings`, `pending`을 판별하도록 구현했다.
3. `.agents/skills/ship-develop/SKILL.md`와 `agents/openai.yaml`을 갱신해 기본 workflow를 "PR -> Codex review -> fix loop -> merge"로 바꾸고, human review gate는 명시 요청 시 옵션으로 남겼다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --codex-review --wait-codex-seconds 300 --dry-run --allow-dirty`로 Codex review 포함 dry-run 출력 확인
3. historical PR 기준 분류 검증:
   - PR `#4` 첫 요청 시 `findings`
   - PR `#4` 두 번째 요청 시 `clean`
   - PR `#5` 요청 시 `findings`
4. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 다음 실제 shipping 요청에서 Codex review loop가 원하는 UX로 동작하는지 실전 확인한다.
2. 필요하면 `codex-review-findings`일 때 PR 댓글/리뷰 스레드 요약까지 자동으로 더 도와주는 보조 스크립트를 추가한다.
- Status: done

## 2026-03-18
- Context: `ship-develop`에 리뷰 승인 대기 단계를 넣는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`에 `--require-review`, `--wait-review-seconds` 옵션과 review polling 로직을 추가했다.
2. review decision이 `APPROVED`가 아니면 checks 상태를 요약한 뒤 `done=pending reason=review-required`로 멈추도록 바꿨다.
3. `.agents/skills/ship-develop/SKILL.md`와 `agents/openai.yaml`을 갱신해 reviewed shipping의 기본 경로가 two-pass임을 명시했다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --require-review --dry-run --allow-dirty`로 review-gated dry-run 출력 확인
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 다음 실제 shipping 요청에서 첫 실행은 PR 생성 후 `review-required`로 멈추는지 확인한다.
2. 승인 후 같은 스크립트를 다시 실행해 merge 재개 흐름도 검증한다.
- Status: done

## 2026-03-18
- Context: `ship-develop`을 실제로 사용해 `develop` merge를 수행하는 과정에서 local branch cleanup 마지막 단계가 실패한 문제를 보완하는 작업
- Change:
1. `.agents/skills/ship-develop/scripts/ship_develop.py`의 `cleanup_local_branch()`가 로컬 브랜치가 이미 삭제된 경우 `already-gone`으로 정상 처리하도록 바꿨다.
2. merge 후 출력도 `local_cleanup=deleted|already-gone|kept`처럼 실제 결과를 그대로 남기도록 맞췄다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 이 fix를 별도 브랜치에서 `develop`에 반영해 shipping workflow를 다시 깨끗하게 만든다.
- Status: done

## 2026-03-18
- Context: `develop으로 합쳐` 한 문장으로 GitHub shipping workflow를 처리할 수 있게 만드는 작업
- Change:
1. system-level `gh` 설치 상태와 인증 상태를 확인했고, 현재 계정 `Eulga`로 로그인되어 있음을 확인했다.
2. GitHub repo 설정을 확인해 현재 기본 브랜치가 `master`, 자동 머지가 `false`, merge 후 브랜치 자동 삭제가 `false`임을 확인했다.
3. `.agents/skills/ship-develop/` skill을 추가하고, `.agents/skills/ship-develop/scripts/ship_develop.py`로 push, PR 생성/재사용, check 확인, merge, local branch cleanup 흐름을 구현했다.
4. 새 skill은 `gh`가 `PATH`에 없어도 `C:\Program Files\GitHub CLI\gh.exe`를 fallback으로 사용하도록 만들었다.
- Verification:
1. `.\.venv\Scripts\python -m py_compile .agents/skills/ship-develop/scripts/ship_develop.py` 통과
2. `.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --dry-run --allow-dirty`로 dry-run 계획 출력 확인
3. `.\.venv\Scripts\python C:\Users\kin50\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/ship-develop`가 `Skill is valid!`로 통과
- Next:
1. 다음 실제 merge 요청에서 `$ship-develop`을 사용해 end-to-end 흐름을 한 번 실전 검증한다.
2. 필요하면 pending checks 대기 시간이나 merge 정책 옵션을 실제 사용 패턴에 맞게 조정한다.
- Status: done

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
