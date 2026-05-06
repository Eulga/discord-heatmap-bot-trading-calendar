# Local LLM News Summary Adoption Scope

- Date: 2026-05-06
- Input reference: `../references/external/local-llm-news-summary-performance-2026-05-06.md`
- Status: Internal analysis report. This is not current runtime truth.
- Supersession note: Later on 2026-05-06 the active news path was reset to collection-only `news_collection` with PostgreSQL article storage. Code references and adoption recommendations below describe the pre-reset news briefing/trend implementation and should be treated as historical analysis only.
- External verification: Not performed for this report. Vendor/version-specific claims in the reference memo still need revalidation before becoming runbook or config truth.

## Executive Summary

현재 코드에 바로 도입 가능한 범위는 **뉴스 본문 100건을 수집해 기사별 요약하는 구조가 아니다**. 현재 뉴스 브리핑은 `NewsItem(title, link, source, published_at, region)` 메타데이터를 provider에서 받아 ranking/dedup 후 Discord 포럼에 게시하는 구조이고, 로컬 LLM은 admin-only `/local ask` 명령에만 연결돼 있다.

따라서 1차 도입 범위는 다음으로 좁히는 것이 맞다.

1. 기존 provider 선별 결과 중 상위 일부만 LLM 입력으로 사용한다.
2. 기사 본문 extraction 없이 제목/출처/시각/link 기반의 **regional digest 요약**부터 붙인다.
3. 로컬 LLM 호출은 optional feature flag 뒤에 두고, 실패하면 기존 metadata-only 브리핑으로 fail-open한다.
4. per-article 100건 요약, `trafilatura`, 뉴스용 `Playwright` fallback, Redis/Celery queue, API LLM hybrid는 2차 이후로 보류한다.

## Code-Confirmed Facts

- `NewsItem`은 현재 제목, 링크, 출처, 발행시각, region만 가진다. 기사 본문, subtitle, provider description, extracted text, content hash는 없다. Evidence: `bot/intel/providers/news.py` lines 391-405.
- 뉴스 provider는 `mock`, `naver`, `marketaux`, `hybrid` 중 하나로 구성된다. Evidence: `bot/features/intel_scheduler.py` lines 139-198.
- `MarketauxNewsProvider`는 API payload를 normalize할 때 title/url/source/published_at만 `NewsItem`으로 보존한다. Evidence: `bot/intel/providers/news.py` lines 493-545.
- `NaverNewsProvider`는 description을 scoring에는 쓰지만 최종 `NewsItem`에는 보존하지 않는다. Evidence: `bot/intel/providers/news.py` lines 621-780.
- 현재 뉴스 scheduler는 provider 분석 결과를 한 번 받아 region별 최대 20건으로 자른 뒤, `build_news_region_body()`로 링크 목록을 게시한다. Evidence: `bot/features/intel_scheduler.py` lines 468-545.
- 기존 news renderer는 Discord 2000자 제한 안에서 item line을 줄이는 deterministic formatter다. Evidence: `bot/features/news/policy.py` lines 20-88.
- 로컬 LLM client는 OpenAI-compatible `/chat/completions`를 호출하지만, 기본 system prompt, `temperature=0.7`, `max_tokens`, non-stream request만 지원한다. Evidence: `bot/features/local_model/client.py` lines 10-123.
- 로컬 LLM 설정은 `/local ask` 중심이고, 기본 `LOCAL_MODEL_MAX_RESPONSE_CHARS=1800`가 그대로 `max_tokens`로 전달된다. Evidence: `bot/app/settings.py` lines 85-92 and `bot/features/local_model/client.py` lines 70-79.
- `requirements.txt`에는 `playwright`는 있지만 `trafilatura`, Redis, Celery, RQ, Dramatiq, arq 계열 dependency는 없다.

## Applicability Matrix

| Reference memo item | Current code fit | Decision | Reason |
| --- | --- | --- | --- |
| 백그라운드 큐화 | Partial | Defer | 뉴스 브리핑은 이미 scheduler background job이다. 단, future manual/on-demand 요약에는 필요하다. |
| LLM 투입 기사 수 줄이기 | High | Adopt now | 현재도 provider별 `limit_per_region <= 20`과 ranking이 있다. LLM 대상은 그중 top 5-10/region으로 더 줄이면 된다. |
| 입력 토큰 hard limit | High | Adopt now | 현재 `NewsItem` metadata만 넣으면 구조적으로 짧다. 본문 도입 전에도 prompt char/token guard를 둘 수 있다. |
| 출력 토큰 hard limit | High | Adopt now | `/local ask` 기본 max가 1800이라 뉴스 요약에는 과하다. 뉴스 전용 `max_tokens`는 160-240 수준으로 별도 설정해야 한다. |
| thinking/reasoning off | Medium | Ops-first | 현재 bot request payload에는 reasoning 옵션이 없다. 우선 local server 실행 옵션/로그 점검 항목으로 두고, 필요하면 request `extra_body` 지원을 별도 검토한다. |
| persistent LLM server | Already aligned | No code change | 현재 bot은 외부 OpenAI-compatible endpoint만 호출하고 서버 lifecycle을 관리하지 않는다. |
| 모델 tiering | Low | Defer | bot code보다 운영/model-server 선택 문제다. 설정 이름/endpoint 분리는 추후 가능하지만 1차 scope는 아니다. |
| 제한적 병렬/continuous batching | Low | Defer | scheduler는 하루 1회 news job이고, 1차 요약은 region digest 1-2회 호출이면 충분하다. per-article worker가 생길 때 재검토한다. |
| 본문/요약 캐시 | Medium | Phase 2 | 기사 본문이 없으므로 content-hash cache는 아직 맞지 않는다. metadata digest cache는 `story_key` set + prompt version으로 가능하지만 1차는 실패해도 fallback 가능하다. |
| API LLM hybrid | Low | Defer | 비용/개인정보/운영정책 결정이 먼저다. 현재 local endpoint 추상화만으로 시작한다. |
| `trafilatura` 최적화 | Low | Defer | 현재 뉴스 경로는 article HTML을 fetch하지 않는다. dependency 추가와 도메인별 실패 정책이 필요한 별도 rollout이다. |
| 뉴스용 `Playwright` fallback | Very low | Defer | 현재 Playwright는 heatmap 캡처용이다. 뉴스 본문 추출까지 확장하면 리소스/차단/법적 운영 이슈가 커진다. |

## Recommended Adoption Scope

### Phase 1: Metadata Digest LLM Overlay

Goal: 기존 뉴스 브리핑의 stable path를 보존하면서, 선택적으로 지역별 LLM 요약 블록을 추가한다.

Scope:

1. 설정 추가
   - `NEWS_LLM_SUMMARY_ENABLED=false`
   - `NEWS_LLM_SUMMARY_MAX_ITEMS_PER_REGION=8`
   - `NEWS_LLM_SUMMARY_MAX_PROMPT_CHARS=2500`
   - `NEWS_LLM_SUMMARY_MAX_TOKENS=200`
   - `NEWS_LLM_SUMMARY_TIMEOUT_SECONDS=30`
   - `NEWS_LLM_SUMMARY_PROMPT_VERSION=v1`
2. 로컬 모델 client 확장
   - `system_prompt`, `temperature`, `max_tokens`를 caller가 지정할 수 있게 한다.
   - 기존 `/local ask` 동작은 유지한다.
   - 뉴스 요약 호출은 `temperature=0.2` 또는 `0.3`, `max_tokens=160-240`로 제한한다.
3. 뉴스 요약 policy 추가
   - 입력은 `region`, `timestamp`, `top NewsItem[]`.
   - prompt는 제목/출처/시간/link만 사용한다.
   - 출력은 “핵심 3줄 + 시장 영향 1줄” 정도의 plain Korean text로 제한한다.
4. scheduler integration
   - `_run_news_job()`에서 `domestic`/`global_items`를 만든 직후 optional summary를 호출한다.
   - summary 성공 시 기존 link list 위에 짧은 요약 블록을 붙인다.
   - timeout/API/invalid response면 기존 `build_news_region_body()` 결과만 게시하고 job 전체는 실패시키지 않는다.
5. Observability
   - provider fetch time, summary time, summary status를 log/job detail에 짧게 남긴다.
   - provider status와 model status를 섞지 않는다.

Suggested output shape:

```text
[AI 요약]
- ...
- ...
- ...
시장 영향: ...

[기사 목록]
- title | source | HH:MM | link
```

Why this is the smallest useful cut:

- 새 크롤러나 새 dependency 없이 가능하다.
- 기존 Naver/Marketaux ranking을 재사용한다.
- Discord posting/idempotency 경로를 거의 건드리지 않는다.
- LLM 실패가 브리핑 게시 실패로 번지지 않는다.

### Phase 1 Tests

- `bot/features/local_model/client.py`
  - caller-specific system prompt/temperature/max_tokens payload test
  - existing `/local ask` payload compatibility test
- new `bot/features/news/summary_policy.py`
  - prompt char limit
  - max item selection
  - Korean output instruction/schema presence
- `bot/features/intel_scheduler.py`
  - summary enabled and local model success prepends summary
  - summary timeout falls back to metadata-only body and records non-fatal detail
  - summary disabled preserves current output

Recommended local validation:

```bash
python3 scripts/run_repo_checks.py unit -- tests/unit/test_local_model_client.py tests/unit/test_news_policy.py
python3 scripts/run_repo_checks.py integration -- tests/integration/test_intel_scheduler_logic.py
git diff --check
```

## Phase 2: Summary Cache And Better Metadata

Goal: LLM calls become idempotent and avoid repeated work when the selected story set has not changed.

Scope:

1. Summary cache key
   - `sha256(model_id + prompt_version + output_schema_version + region + story_key list)`
   - Use `NewsItem.story_key()` because there is no body/content hash yet.
2. State storage
   - Add a PostgreSQL split table only if repeated calls are expected across restarts or manual refreshes.
   - Otherwise, keep an in-process TTL cache first to avoid state-table churn.
3. Provider metadata improvement
   - Consider extending `NewsItem` with optional `description`.
   - For Naver, keep cleaned `description` already available during normalization.
   - For Marketaux, preserve `description` or entities if present.
   - This improves trend and LLM input quality without article-body fetch.

Defer until after Phase 1 metrics show repeated calls or poor title-only summary quality.

## Phase 3: Article Body Extraction

Goal: Support higher-quality per-article summaries only when metadata digest is insufficient.

Scope should remain deliberately narrow:

1. Add a new article extraction module, not inside provider ranking code.
2. Start with HTTP fetch + deterministic extraction for allowlisted domains.
3. Add `trafilatura` only after approving dependency and measuring against representative URLs.
4. Use Playwright only for allowlisted JS-required domains, with browser reuse and resource blocking.
5. Store extraction status and extracted text hash separately from daily-post state.
6. Summarize only top N articles, not all provider results.

This should not be part of the first PR. It changes dependency surface, network behavior, latency, and operational risk.

## Explicitly Out Of Initial Scope

- 100 article per-run LLM summarization.
- Per-article local LLM calls in the scheduler hot path.
- News article `Playwright` fallback.
- Redis/Celery/RQ/Dramatiq queue.
- API LLM hybrid path.
- model tiering or quantization experiments inside bot code.
- Bot-managed `llama-server` lifecycle.
- Promoting Gemma-specific `reasoning` flags into canonical config before current `llama-server` support is verified locally.

## Recommended First PR Boundary

Implement **Phase 1 only**.

Files likely touched:

- `bot/app/settings.py`
- `.env.example`
- `bot/features/local_model/client.py`
- `bot/features/news/summary_policy.py` (new)
- `bot/features/intel_scheduler.py`
- `tests/unit/test_local_model_client.py`
- `tests/unit/test_news_summary_policy.py` (new)
- `tests/integration/test_intel_scheduler_logic.py`
- `docs/operations/config-reference.md`
- `docs/specs/as-is-functional-spec.md`
- `docs/context/development-log.md`

Risk notes:

- Use fail-open behavior for summary failures.
- Keep existing metadata-only renderer as the source of truth for article links.
- Do not change provider ranking in the same PR.
- Do not add article body fetching in the same PR.
