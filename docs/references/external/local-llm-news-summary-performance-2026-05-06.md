# Local LLM News Summary Performance Reference

- Date: 2026-05-06
- Source: User-provided analysis memo
- Status: Reference material only. This file is not current implementation truth.
- Verification note: External links and vendor-specific claims in this memo were not revalidated while adding this reference document. Reconfirm against current official docs and local measurements before promoting any item into canonical specs or operational runbooks.

## 1. 핵심 결론

현재 구조에서 가장 큰 병목은 **본문 추출이 아니라 로컬 LLM 요약 단계**일 가능성이 큽니다. 지금 측정값인 **기사 1건당 20~40초**를 그대로 100건에 적용하면, 순차 처리 기준 전체 요약에만 **약 33~67분**이 걸립니다. 추출 실패로 `Playwright`까지 타는 기사들이 섞이면 전체 지연은 더 커집니다.

가장 효과가 큰 개선 순서는 다음입니다.

1. **100개 전체를 실시간 요약하지 말고 백그라운드 큐로 처리**
2. **LLM 입력 토큰을 강제로 줄이기**
3. **출력 길이 제한**
4. **Gemma 4의 thinking/reasoning 비활성화 확인**
5. **모델을 매 요청마다 로드하지 않고 persistent LLM server로 운영**
6. **요약 대상 자체를 dedup/ranking으로 줄이기**
7. **Mac mini 16GB에서는 병렬도를 1~2개로 제한**
8. **Playwright는 최후의 fallback으로만 사용**
9. **본문/요약 캐시를 강하게 적용**
10. **긴급 뉴스만 API LLM을 병행**

Gemma 4 E4B는 이름상 4B급처럼 보이지만, 공식 모델 카드 기준 E4B dense 모델은 **4.5B effective parameters / 8B with embeddings** 구조이고, Q4 계열에서도 base weight만 수 GB가 필요합니다. Google 문서의 Q4_0 기준 E4B 메모리 요구량은 약 **5GB**이며, 여기에 KV cache, 런타임, OS, 브라우저, 파이썬 프로세스가 추가됩니다. Mac mini 16GB에서 “100건 전체를 빠르게 병렬 요약”하기에는 구조적으로 빡빡합니다. ([Google AI for Developers][1])

## 2. 현재 병목 분석

| 단계 | 병목 가능성 | 설명 |
| --- | ---: | --- |
| 뉴스 수집 / 키워드 필터링 | 중간 | 키워드 필터링을 러프하게 바꾸면서 LLM 투입량이 증가했습니다. 병목이라기보다 **후단 부하 증폭 요인**입니다. |
| URL fetch / `trafilatura` | 중간 | 일반 HTML이면 빠르지만, 사이트 차단, 느린 응답, 리다이렉트, 쿠키, 봇 차단에서 지연이 생깁니다. |
| `Playwright` fallback | 높음 | 브라우저 렌더링은 HTML fetch보다 훨씬 무겁습니다. 이미지, 폰트, 광고, analytics, iframe, lazy loading 때문에 수 초 이상 걸릴 수 있습니다. |
| 본문 정제 / 토큰화 | 중간 | 본문 전체를 그대로 넣으면 prompt prefill 시간이 급증합니다. |
| 로컬 LLM prompt prefill | 높음 | 기사 본문이 길수록 입력 토큰 처리 시간이 커집니다. |
| 로컬 LLM generation | 매우 높음 | 요약문 출력은 autoregressive라 토큰을 순차 생성합니다. 출력 길이가 길수록 직접적으로 느려집니다. |
| 병렬 처리 | 제한적 | Mac mini 16GB에서 무리하게 병렬 호출하면 처리량이 선형 증가하지 않고 swap, memory bandwidth contention, tail latency가 생길 수 있습니다. |
| Discord 응답 | 낮음 | 실제 병목은 Discord가 아니라 “응답 전에 요약을 끝내려는 구조”입니다. |

`trafilatura.extract()`는 `fast=True`, `include_comments`, `include_tables`, `favor_precision/recall` 같은 옵션을 제공하며, `fetch_url()`은 HTML을 다운로드하고 실패 시 `None`을 반환하는 구조입니다. 따라서 추출 단계는 **옵션과 fallback 조건**을 잘못 잡으면 불필요하게 느려질 수 있습니다. ([Trafilatura][2])

`Playwright`는 기본적으로 `page.goto()`가 `load` 이벤트까지 기다리며, 이 이벤트는 stylesheet, script, iframe, image 같은 종속 리소스 로딩까지 포함합니다. 뉴스 본문 추출 목적이라면 대개 `domcontentloaded` 또는 특정 본문 selector 대기만으로 충분합니다. ([Playwright][3])

## 3. 기사 1건당 20~40초가 걸리는 원인 분석

### 추정 원인 1: 입력 본문이 너무 김

뉴스 본문 전체를 그대로 넣는다면 기사당 입력이 쉽게 **1,500~6,000+ tokens**까지 올라갈 수 있습니다. 로컬 LLM에서는 입력 토큰 처리, 즉 prompt evaluation 시간이 무시할 수 없는 비용입니다.

요약 작업에서는 전체 본문이 항상 필요하지 않습니다. 대부분의 경제 뉴스는 다음 정보만으로도 충분히 요약됩니다.

- 제목
- 부제
- 첫 5~10개 문단
- 키워드 주변 문단
- 수치/인용/기관명 포함 문장
- 마지막 결론 문단

즉, **본문 전체 → 요약**이 아니라 **본문 → 중요 문단 추출 → LLM 요약**으로 바꾸는 것이 가장 큽니다.

### 추정 원인 2: 출력 토큰이 많음

로컬 LLM의 generation은 기본적으로 다음 토큰을 하나씩 생성합니다. 따라서 요약문이 길수록 시간이 선형적으로 증가합니다.

예를 들어 현재 요약이 다음처럼 길다면 느릴 수밖에 없습니다.

- 5~8문단 요약
- 배경 설명 포함
- 해외뉴스 번역 + 해설 포함
- 투자 시사점 포함
- 디스코드용 formatting 포함

실서비스용으로는 다음처럼 제한하는 것이 좋습니다.

```text
출력:
- 3줄 요약
- 핵심 수치 1~3개
- 시장 영향 1줄
- 전체 120~180 Korean tokens 이내
```

### 추정 원인 3: Gemma 4 thinking/reasoning이 켜져 있을 가능성

Gemma 4는 thinking mode를 지원합니다. 공식 문서에서도 `enable_thinking=True`일 때 `<|think|>` 토큰이 삽입되고, reasoning block과 final answer가 함께 생성되는 구조를 설명합니다. 요약 작업에서는 thinking이 대부분 불필요하며, 켜져 있으면 내부 reasoning 출력/처리로 시간이 크게 늘 수 있습니다. ([Google AI for Developers][4])

`llama.cpp` 계열 서버를 쓴다면 `--reasoning off`, `--reasoning-budget 0`, `--chat-template-kwargs` 같은 설정을 점검해야 합니다. 최신 `llama-server` 문서에는 reasoning on/off/auto, reasoning budget, chat-template kwargs 옵션이 명시되어 있습니다. ([GitHub][5])

### 추정 원인 4: 모델이 매 기사마다 새로 로드되는 경우

이 부분은 실제 구현을 확인해야 합니다.

만약 기사 1건마다 다음을 반복한다면 치명적입니다.

```text
모델 로드 → 프롬프트 생성 → 추론 → 모델 언로드
```

반드시 다음 구조여야 합니다.

```text
llama.cpp / Ollama / LM Studio server 상시 기동
→ HTTP API로 요청만 전달
→ 모델은 계속 메모리에 유지
```

`llama.cpp` HTTP server는 quantized model inference, OpenAI-compatible routes, parallel decoding, continuous batching, monitoring endpoints를 지원합니다. 서비스형 구조에서는 CLI 단발 실행보다 persistent server가 적합합니다. ([GitHub][5])

### 추정 원인 5: Mac mini 16GB에서 병렬 추론이 제한됨

16GB 환경에서는 모델, OS, Python, Discord bot, Playwright Chromium, 캐시, KV cache가 같은 메모리를 공유합니다. LLM worker를 3~4개 이상 동시에 돌리면 “처리량 증가”보다 “메모리 압박과 tail latency 증가”가 먼저 올 수 있습니다.

Mac에서는 llama.cpp가 Metal을 통해 GPU 계산을 사용할 수 있습니다. macOS에서 Metal build는 기본 활성화될 수 있고, `--n-gpu-layers 0`으로 GPU inference를 명시적으로 끌 수 있다는 llama.cpp 문서가 있습니다. 즉, 현재 실제로 Metal offload가 되고 있는지 로그로 확인해야 합니다. ([GitHub][6])

## 4. 속도 개선 우선순위 TOP 10

| 우선순위 | 개선안 | 비용 | 예상 효과 | 핵심 설명 |
| ---: | --- | ---: | ---: | --- |
| 1 | **실시간 전체 요약 중단, 백그라운드 큐화** | 무료 | 매우 큼 | Discord 요청은 즉시 응답하고, 요약은 worker가 처리합니다. |
| 2 | **LLM 투입 기사 수 줄이기** | 무료 | 매우 큼 | 100건 전부 요약하지 말고 dedup/ranking 후 상위 20~50건만 우선 요약합니다. |
| 3 | **입력 토큰 hard limit** | 무료 | 매우 큼 | 기사당 입력을 800~1,800 tokens 수준으로 제한합니다. |
| 4 | **출력 토큰 hard limit** | 무료 | 큼 | `max_tokens=120~200` 수준으로 제한합니다. |
| 5 | **Gemma 4 thinking/reasoning off** | 무료 | 큼 | 요약은 reasoning task가 아닙니다. thinking이 켜져 있으면 즉시 끕니다. |
| 6 | **persistent LLM server + Metal offload 확인** | 무료 | 큼 | 모델 재로드 제거, GPU offload, warm 상태 유지. |
| 7 | **작은 모델 tier 도입** | 무료~저비용 | 큼 | E4B 대신 E2B/소형 요약 모델로 1차 요약, 중요 기사만 E4B. |
| 8 | **제한적 병렬 처리 / continuous batching** | 무료 | 중간~큼 | `-np 2`, worker 2개부터 벤치마크. 16GB에서 과도한 병렬은 역효과. |
| 9 | **본문/요약 캐싱** | 무료 | 중간~큼 | URL, 본문 hash, prompt version, model version 기준 캐시. |
| 10 | **API LLM hybrid / 하드웨어 업그레이드** | 유료 | 매우 큼 | 긴급/상위 뉴스는 API, 대량 비실시간은 로컬 또는 Batch API. |

`llama-server`는 `--parallel`로 server slot 수를 설정하고, continuous batching도 지원합니다. 또한 `/metrics`에서 prompt tokens, predicted tokens, prompt/generation tokens-per-second, KV cache 사용률 등을 볼 수 있으므로, 최적화 전후 측정이 가능합니다. ([GitHub][5])

## 5. 요청 항목별 검토

### 5.1 모델 변경

현재 Gemma 4 E4B Q4_K_M은 품질은 좋지만, “경제뉴스 100건 요약”에는 다소 무거울 수 있습니다.

추천 구조는 **단일 모델 고집이 아니라 tiering**입니다.

| 용도 | 추천 |
| --- | --- |
| 전체 뉴스 1차 요약 | 더 작은 모델, 예: Gemma 4 E2B급 |
| 중요 기사 / 사용자 요청 기사 | Gemma 4 E4B |
| 해외뉴스 번역 품질 우선 | E4B 유지 또는 API fallback |
| 단순 제목/리드 요약 | 소형 모델 또는 규칙 기반 요약 |

Gemma 4는 E2B, E4B, 31B, 26B A4B 크기로 제공되고, 작은 모델은 128K context를 지원합니다. 다만 큰 context가 있다고 해서 전체 기사를 넣는 것이 빠르다는 뜻은 아닙니다. ([Google AI for Developers][7])

해외 뉴스 번역이 중요한 경우에는 별도의 번역 특화 모델도 검토할 수 있습니다. Google은 TranslateGemma를 4B, 12B, 27B 크기로 공개했고 55개 언어 번역을 목표로 한다고 설명합니다. 다만 현재 정책이 “기사당 LLM 1회 호출”이라면 번역 모델을 별도 호출하는 방식은 맞지 않고, **요약+번역을 한 번에 잘하는 모델**을 선택해야 합니다. ([blog.google][8])

### 5.2 양자화 변경

현재 `Q4_K_M`은 보통 품질/용량 균형이 좋은 선택입니다. 다만 속도만 보면 항상 최선은 아닙니다.

검토 순서:

1. 현재 `Q4_K_M` 유지 후 입력/출력 토큰부터 줄이기
2. `Q4_0`, `Q4_K_S`, `IQ4_*` 계열이 있다면 동일 기사 30건으로 벤치마크
3. 품질이 허용되면 `Q3_K_M` 또는 `IQ3_*` 계열 테스트
4. `Q5_K_M`, `Q8_0`은 품질은 좋아질 수 있지만 16GB Mac mini에서는 속도/메모리 측면에서 불리할 가능성이 큼

양자화는 “무조건 낮을수록 빠름”이 아닙니다. backend, dequantization overhead, Metal kernel, memory bandwidth에 따라 달라집니다. 따라서 **동일 기사 세트로 tokens/sec와 summary 품질을 함께 측정**해야 합니다.

### 5.3 프롬프트 축소

현재 프롬프트가 길다면 바로 줄이세요.

비추천:

```text
당신은 최고의 경제 전문 애널리스트입니다...
아래 기사를 매우 자세히 분석하고...
거시경제적 함의와 투자 시사점과 배경을 설명하고...
```

추천:

```text
역할: 경제뉴스 요약기.
작업: 기사 내용을 한국어로 요약한다.
출력:
1) 한줄 제목
2) 핵심 3줄
3) 시장 영향 1줄
제한: 전체 700자 이내. 추측 금지. 기사에 없는 내용 금지.
```

해외뉴스도 “전문 번역 후 요약”이 아니라 다음처럼 처리해야 합니다.

```text
영문/해외 기사를 읽고 한국어 뉴스 요약문만 출력한다.
원문 전체 번역은 하지 않는다.
```

### 5.4 입력 토큰 절감

가장 실무적인 방식은 **LLM 전에 deterministic reducer를 두는 것**입니다.

추천 입력 구성:

```text
[title]
[subtitle]
[published_at/source]
[first 5 paragraphs]
[keyword matched paragraphs ± 1 paragraph]
[numeric/event sentences]
[last 1~2 paragraphs]
```

그리고 다음을 제거합니다.

- 기자 소개
- 저작권 문구
- 관련기사 목록
- 광고/구독 안내
- 이미지 캡션 반복
- 댓글
- SNS 공유 문구
- 표가 필요 없는 경우 table text

`trafilatura.extract()`에서 `include_comments=False`, `include_tables=False`, `fast=True`, `favor_precision=True`를 우선 테스트하세요. `fast=True`는 fallback extraction을 줄여 속도를 얻는 옵션입니다. ([Trafilatura][2])

### 5.5 배치 처리

여기서 “배치”는 두 가지로 나눠야 합니다.

| 방식 | 추천 여부 | 설명 |
| --- | ---: | --- |
| 여러 기사를 하나의 프롬프트에 묶기 | 낮음 | 한 기사 실패 시 전체 retry, JSON 깨짐, 기사 간 내용 섞임 위험 |
| 여러 요청을 LLM server scheduler가 처리 | 높음 | `llama-server` continuous batching / parallel slots 활용 |

Mac mini 16GB에서는 처음부터 4~8개 병렬을 잡지 말고 다음 순서로 측정하세요.

```text
concurrency 1 → 2 → 3
```

대부분은 2에서 최적점이 나오거나, 3부터 tail latency가 나빠질 가능성이 큽니다.

### 5.6 병렬 처리

권장 구조:

```text
본문 추출 worker: 5~20개 비동기 가능
Playwright worker: 1~3개 제한
LLM worker: 1~2개 제한
Discord 응답: 즉시
```

본문 fetch는 I/O bound라 병렬화 효과가 큽니다. 반면 LLM 추론은 memory/compute bound라 병렬화 효과가 제한적입니다.

즉, 병렬도는 다음처럼 비대칭으로 둬야 합니다.

```text
fetch/extract 병렬도  >>  LLM 병렬도
```

### 5.7 캐싱 전략

반드시 넣어야 합니다.

| 캐시 | key | value |
| --- | --- | --- |
| URL 캐시 | canonical_url | fetch status, final_url |
| HTML 캐시 | final_url + etag/date | raw html |
| 본문 캐시 | content_hash | extracted_text |
| 요약 캐시 | model_id + prompt_version + content_hash | summary |
| 실패 캐시 | domain + failure_type | fallback rule |
| 중복 기사 캐시 | simhash/minhash | 대표 기사 ID |

특히 요약 캐시 key는 다음처럼 잡는 것이 좋습니다.

```text
summary_cache_key =
sha256(model_id + quant + prompt_version + output_schema_version + content_hash + target_lang)
```

이렇게 해야 프롬프트나 모델을 바꿨을 때 재요약 여부를 통제할 수 있습니다.

`llama-server` 자체도 `cache_prompt` 옵션으로 이전 요청과 공통 prefix를 재사용할 수 있습니다. 다만 기사마다 본문이 다르기 때문에 효과는 시스템 프롬프트가 긴 경우에만 큽니다. ([GitHub][5])

## 6. `trafilatura` / `Playwright` 본문 추출 개선

### 6.1 `trafilatura` 최적화

추천 설정 방향:

```python
trafilatura.extract(
    html,
    url=url,
    fast=True,
    include_comments=False,
    include_tables=False,
    include_images=False,
    include_links=False,
    favor_precision=True,
    deduplicate=True,
)
```

실무 기준으로는 다음 순서를 권장합니다.

1. RSS/검색 결과에서 URL 수집
2. URL canonicalize
3. raw HTML fetch
4. `trafilatura.extract(fast=True)`
5. 본문 길이/품질 검사
6. 실패 시 `baseline()` 또는 `html2txt()` 빠른 fallback
7. 그래도 실패한 도메인만 `Playwright`

`trafilatura` 문서는 threaded parallel downloads와 domain-aware throttling을 제공하며, 여러 도메인의 페이지를 병렬로 가져올 때 효율적이라고 설명합니다. 또한 `sleep_time`으로 같은 도메인 요청 간격을 조절할 수 있습니다. ([Trafilatura][9])

설정 파일에서는 `DOWNLOAD_TIMEOUT`, `SLEEP_TIME`, `MIN_EXTRACTED_SIZE`, `MIN_OUTPUT_SIZE`, `EXTRACTION_TIMEOUT` 같은 값을 조정할 수 있습니다. ([Trafilatura][10])

### 6.2 `Playwright` 최적화

`Playwright`는 최후의 수단으로만 써야 합니다.

추천 방식:

```text
- browser는 한 번만 launch
- context/page pool 재사용
- image/media/font/stylesheet 차단
- service worker block
- wait_until="domcontentloaded"
- networkidle 사용 자제
- timeout 5~10초
- page.content() 후 다시 trafilatura.extract()
```

Playwright는 `browserContext.route()`로 네트워크 요청을 가로채고, 이미지 요청 같은 리소스를 abort할 수 있습니다. 또한 라우팅을 켜면 HTTP cache가 비활성화된다는 점도 고려해야 합니다. ([Playwright][11])

추천 fallback 조건:

```text
Playwright 실행 조건:
- trafilatura 결과가 None
- 추출 본문 길이 < 500자
- 제목은 있는데 본문이 비어 있음
- known_js_required_domain 목록에 포함
```

비추천 조건:

```text
- 모든 기사에 Playwright 사용
- networkidle 대기
- 페이지마다 browser launch/close
- 이미지/폰트/광고 리소스 허용
```

`trafilatura` troubleshooting 문서도 raw HTML 다운로드/처리가 더 빠르지만, JavaScript가 본문을 주입하는 페이지는 Playwright 같은 browser automation이 필요할 수 있다고 설명합니다. ([Dokk][12])

## 7. 추천 아키텍처

### 7.1 현재 구조 개선안

```text
[Discord Bot]
    |
    | 즉시 응답: 캐시된 요약 / 처리 상태 / 원문 링크
    v

[News Collector]
    |
    v
[URL Canonicalizer + Deduper]
    |
    v
[Article Fetch Queue]
    |
    +--> [HTTP Fetch Worker]
    |         |
    |         v
    |    [trafilatura fast extraction]
    |         |
    |         +--> success --> [Raw HTML/Text Cache]
    |         |
    |         +--> fail --> [Playwright Fallback Queue]
    |
    +--> [Playwright Pool: 1~3 workers]
              |
              v
        [page.content() → trafilatura]

                |
                v

[Text Normalizer / Token Reducer]
    |
    v
[Ranking / Priority Scorer]
    |
    +--> low priority: 저장만
    |
    +--> high priority:
          |
          v
    [Summary Queue]
          |
          +--> [Local LLM Server: Gemma E2B/E4B, concurrency 1~2]
          |
          +--> [Optional API LLM fallback for urgent/high-value]
          |
          v
    [Summary Cache / DB]
          |
          v
    [Discord Delivery]
```

### 7.2 핵심 설계 원칙

#### 원칙 1: Discord 요청과 LLM 처리를 분리

Discord 명령어가 들어왔을 때 100개 요약이 끝날 때까지 기다리면 안 됩니다.

응답 방식:

```text
사용자 요청
→ 즉시 “최근 경제뉴스 수집 중 / 요약 준비 중” 응답
→ 캐시된 요약 먼저 표시
→ 신규 요약은 완료되는 순서대로 업데이트
```

#### 원칙 2: 모든 뉴스가 LLM 요약 대상은 아님

100개 뉴스가 들어오면 다음처럼 줄이는 것이 현실적입니다.

```text
100개 수집
→ URL/content dedup 후 60개
→ 키워드/출처/신선도/중요도 ranking 후 30개
→ 상위 30개만 즉시 요약
→ 나머지는 사용자가 클릭하거나 요청할 때 요약
```

#### 원칙 3: Local LLM과 API LLM을 역할 분리

| 구분 | Local LLM | API LLM |
| --- | --- | --- |
| 비용 | 호출당 무료, 전기/하드웨어 비용 | 호출당 과금 |
| 속도 | Mac mini 16GB에서는 제한적 | 대개 빠름 |
| 개인정보 | 유리 | 외부 전송 필요 |
| 안정성 | 직접 운영 필요 | provider 의존 |
| 추천 용도 | 백그라운드 대량 요약, 캐시 생성 | 긴급 뉴스, 사용자 요청, 중요 뉴스 |

API를 쓴다면 “모든 기사 API 요약”보다는 다음이 좋습니다.

```text
Local: 일반 뉴스 백그라운드 요약
API: 사용자가 지금 요청한 뉴스, 긴급 속보, 로컬 큐가 밀린 경우
```

OpenAI Batch API는 동기 API 대비 50% 비용 할인과 24시간 내 비동기 처리 window를 제공한다고 공식 문서가 설명합니다. 따라서 실시간 Discord 응답용보다는 일일/시간별 대량 digest 생성에 적합합니다. ([OpenAI Developers][13])

## 8. 단기 / 중기 / 장기 개선 로드맵

### 단기 개선안: 바로 적용

| 작업 | 비용 | 기대 효과 |
| --- | ---: | ---: |
| 기사당 LLM 입력 1,500 tokens 이하로 제한 | 무료 | 매우 큼 |
| `max_tokens` 120~200으로 제한 | 무료 | 큼 |
| Gemma 4 reasoning/thinking off 확인 | 무료 | 큼 |
| LLM server persistent 실행 | 무료 | 큼 |
| 모델 재로드 여부 점검 | 무료 | 큼 |
| URL/content/summary 캐시 추가 | 무료 | 큼 |
| Playwright fallback 조건 강화 | 무료 | 중간~큼 |
| 추출/요약 단계별 latency logging | 무료 | 필수 |

추천 `llama-server` 시작 예시:

```bash
./llama-server \
  -m /models/gemma-4-e4b-it-Q4_K_M.gguf \
  -c 4096 \
  -n 180 \
  -ngl all \
  -fa auto \
  -b 2048 \
  -ub 512 \
  -t 6 \
  -tb 8 \
  -np 2 \
  -cb \
  --reasoning off \
  --reasoning-budget 0 \
  --cache-prompt \
  --metrics \
  --slots
```

위 값은 출발점입니다. 실제 최적값은 Mac mini 세대, Metal 동작 여부, 모델 GGUF 구현에 따라 달라집니다.

### 중기 개선안: 구조 개선

| 작업 | 비용 | 기대 효과 |
| --- | ---: | ---: |
| Redis/RQ, Celery, arq, Dramatiq 등 queue 도입 | 무료~저비용 | 매우 큼 |
| 뉴스 ranking scorer 도입 | 무료 | 매우 큼 |
| LLM worker concurrency 자동 조절 | 무료 | 큼 |
| Gemma E2B/E4B 2-tier 모델 운영 | 무료 | 큼 |
| 도메인별 extraction rule 저장 | 무료 | 중간 |
| Playwright page pool 운영 | 무료 | 중간 |
| 요약 품질 평가셋 50~100건 구축 | 무료 | 큼 |
| prompt versioning / schema versioning | 무료 | 중간 |

중기 목표는 다음입니다.

```text
“100건을 모두 요약”이 아니라
“사용자에게 가치 있는 20~40건을 빠르게 요약하고,
나머지는 캐시/요청 기반으로 처리”
```

### 장기 개선안: 성능 한계 돌파

| 작업 | 비용 | 기대 효과 |
| --- | ---: | ---: |
| Mac mini 32GB/64GB 이상 또는 Mac Studio급 업그레이드 | 유료 | 큼 |
| NVIDIA GPU 서버 도입 | 유료 | 매우 큼 |
| API LLM hybrid 운영 | 유료 | 매우 큼 |
| 요약 전용 소형 모델 fine-tuning / distillation | 유료 가능 | 큼 |
| 뉴스 제공 API / 제휴 데이터 소스 사용 | 유료 가능 | 큼 |
| MTP/speculative decoding 지원 모델/런타임 적용 | 무료~유료 | 중간~큼 |

Gemma 4는 Multi-Token Prediction을 통해 speculative decoding을 지원하며, Google은 이를 표준 autoregressive generation 대비 decoding speedup을 위한 구조로 설명합니다. 단, GGUF/llama.cpp 환경에서 실제 지원 여부와 효과는 사용하는 모델 파일과 runtime 옵션에 따라 벤치마크해야 합니다. ([Google AI for Developers][14])

## 9. 현재 Mac mini 16GB 기준 현실적인 기대 성능

아래는 **추정치**입니다. 실제 수치는 Mac mini 세대, Metal 사용 여부, 기사 길이, 출력 길이, Playwright 비율에 따라 달라집니다.

| 시나리오 | 기사 수 | 기사당 시간 | 전체 소요 추정 |
| --- | ---: | ---: | ---: |
| 현재 구조 순차 처리 | 100 | 20~40초 | 33~67분 |
| 입력/출력 축소 후 E4B 순차 | 100 | 8~20초 | 13~33분 |
| E4B + concurrency 2 | 100 | 처리량 1.2~1.8배 개선 추정 | 8~25분 |
| E2B급 1차 요약 모델 | 100 | 4~12초 추정 | 7~20분 |
| dedup/ranking 후 30건만 요약 | 30 | 4~15초 추정 | 2~8분 |
| 긴급 상위 10~20건만 API | 10~20 | provider/rate limit 의존 | 수십 초~수 분 가능 |

현실적으로 Mac mini 16GB에서 기대할 수 있는 최적 지점은 다음입니다.

```text
100건 전체 즉시 요약: 비추천
상위 20~40건 백그라운드 요약: 현실적
모든 기사 캐시 기반 점진 요약: 현실적
사용자 요청 기사만 즉시 고품질 요약: API 병행 시 현실적
```

## 10. 최종 추천안

가장 추천하는 운영 구조는 **로컬 LLM 유지 + API 선택적 병행 + 백그라운드 큐**입니다.

### 최종 구조

```text
1. 수집은 넓게 한다.
2. dedup/ranking으로 LLM 투입 대상을 줄인다.
3. 본문 전체가 아니라 압축된 article digest만 LLM에 넣는다.
4. Discord에는 즉시 캐시/상태를 반환한다.
5. 요약은 백그라운드에서 priority queue로 처리한다.
6. Mac mini에서는 LLM worker를 1~2개만 둔다.
7. 긴급/사용자 요청/상위 뉴스는 API fallback을 둔다.
```

### 가장 먼저 바꿀 5개

1. **기사 입력을 1,500 tokens 이하로 자르기**
2. **출력 `max_tokens`를 120~200으로 제한**
3. **Gemma 4 reasoning/thinking off 확인**
4. **요약 결과 cache key 설계**
5. **Discord 실시간 응답과 LLM 요약 처리 분리**

이 5개만 적용해도 현재 20~40초/article 구조는 상당히 줄어들 가능성이 큽니다. 다만 Mac mini 16GB에서 100개 이상 기사를 모두 빠르게 로컬 요약하는 것은 한계가 있으므로, 실서비스 기준으로는 **“100건 전체 요약”이 아니라 “중요도 기반 요약 + 캐시 + 요청 시 요약”** 구조가 맞습니다.

## References

[1]: https://ai.google.dev/gemma/docs/core/model_card_4 "Gemma 4 model card | Google AI for Developers"
[2]: https://trafilatura.readthedocs.io/en/latest/corefunctions.html "Core functions | Trafilatura documentation"
[3]: https://playwright.dev/docs/navigations "Navigations | Playwright"
[4]: https://ai.google.dev/gemma/docs/capabilities/thinking "Thinking mode in Gemma | Google AI for Developers"
[5]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md "llama.cpp server README | GitHub"
[6]: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md "llama.cpp build docs | GitHub"
[7]: https://ai.google.dev/gemma/docs/core "Gemma model overview | Google AI for Developers"
[8]: https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/ "TranslateGemma | Google Blog"
[9]: https://trafilatura.readthedocs.io/en/latest/downloads.html "Download web pages | Trafilatura documentation"
[10]: https://trafilatura.readthedocs.io/en/latest/settings.html "Settings and customization | Trafilatura documentation"
[11]: https://playwright.dev/docs/api/class-browsercontext "BrowserContext | Playwright"
[12]: https://dokk.org/documentation/trafilatura/v1.5.0/troubleshooting/ "Troubleshooting | Trafilatura documentation"
[13]: https://developers.openai.com/api/docs/guides/batch "Batch API | OpenAI Developers"
[14]: https://ai.google.dev/gemma/docs/mtp/overview "Speed-up Gemma with Multi-Token Prediction | Google AI for Developers"
