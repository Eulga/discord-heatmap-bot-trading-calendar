# QA Issue Review (2026-03-24)

- This is a dated QA review report.
- It is not a canonical runtime behavior spec.

# 1. Review basis
- What was treated as authoritative:
  - `docs/specs/as-is-functional-spec.md` was treated as the source of truth for current runtime behavior, visible gaps, and ambiguity boundaries.
- What was treated as supporting evidence:
  - `docs/specs/qa-test-backlog.md` was used only to validate seriousness, representative failure modes, and missing regression coverage around already-observed weaknesses.
- Limits of confidence:
  - Confidence is high for scheduler trigger semantics, state persistence behavior, Discord posting/upsert flow, route/admin commands, watch/status command surfaces, and EOD mock wiring because those behaviors are directly stated in the As-Is spec.
  - Confidence is lower where the As-Is spec itself marks ambiguity, especially watch market-hours semantics, authorization intent for watch/status commands, hybrid regional failure isolation, and multi-instance deployment support.

# 2. Executive risk summary
- The highest production risks are state integrity loss, missed exact-minute jobs, duplicate same-day forum content on transient Discord failures, stale/off-hours watch alerts, and open shared control/diagnostic surfaces.
- The most incident-prone items are `QAI-01`, `QAI-02`, `QAI-03`, `QAI-05`, and `QAI-10` because they can create directly visible failures: wiped routing/state, silently skipped daily jobs, duplicate threads, and misleading alerts.
- The most likely silent-drift items are `QAI-02`, `QAI-10`, `QAI-11`, `QAI-14`, and `QAI-16` because they can leave the system appearing healthy while state, alert semantics, status rows, or operational assumptions have drifted.
- Authorization and setup validation are secondary but still material risks: `QAI-07` and `QAI-08` can turn misconfiguration or unsafe access into production-side posting failures and operator confusion.
- EOD is a narrower but concrete correctness risk: `QAI-12` only activates when enabled, but in that state the current implementation can publish mock-derived output as if it were operational content.

# 3. Consolidated QA issue list

## Issue QAI-01 — Corrupt or unreadable state can become authoritative empty state

- Type: Defect
- Primary lens: Ops/Runtime
- Summary:
  - The repository layer treats invalid JSON and `OSError` reads as an empty state object, so later writes can persist that empty view as the new source of truth.
- Trigger / Reproduction condition:
  - `data/state/state.json` is truncated, malformed, temporarily unreadable, or otherwise raises `JSONDecodeError` or `OSError`, and a later command or scheduler path saves state.
- Current behavior:
  - `load_state()` returns empty state for invalid JSON, non-dict payload, `JSONDecodeError`, or `OSError`, and the rest of the app continues from that result.
- Why this is risky:
  - A single bad read can turn route loss, watchlist loss, dedupe loss, and job/provider history loss into durable persisted damage.
- Likely impact:
  - Forum routing disappears, watch state resets, job histories vanish, and later runs may skip or duplicate work because prior state is gone.
- Evidence basis:
  - As-Is section(s):
    - `5.5 State persistence behavior`
    - `8. Observed gaps in current implementation` -> `G-01`
  - Supporting test spec section(s), if relevant:
    - `UT-01 Corrupt state read does not become authoritative empty state`
- Root cause hypothesis:
  - State repository logic does not distinguish first-run empty state from unexpected corrupt/unreadable state and therefore fails open.
- Recommended fix:
  - Fail closed on unexpected read failures, separate missing-file initialization from corrupt-read handling, and block destructive saves after an invalid read until recovery or explicit restore succeeds.
- Severity: Critical
- Likelihood: Medium
- Blast radius: System-wide
- Priority: P0

## Issue QAI-02 — Shared JSON state has no serialized mutation boundary

- Type: Defect
- Primary lens: Ops/Runtime
- Summary:
  - Commands, schedulers, and bootstrap flows all use plain load-modify-save behavior without a visible shared lock or transactional merge boundary.
- Trigger / Reproduction condition:
  - Two code paths update different parts of state at roughly the same time, such as watchlist mutation during a scheduler write or bootstrap during startup.
- Current behavior:
  - Multiple modules read the same file into memory, mutate local snapshots, and write back independently.
- Why this is risky:
  - The last writer can silently discard unrelated updates from another path with no error or conflict signal.
- Likely impact:
  - Lost watchlist changes, lost route changes, overwritten job/provider status, and inconsistent daily-post metadata.
- Evidence basis:
  - As-Is section(s):
    - `5.5 State persistence behavior`
    - `7. Ambiguities and unverifiable areas` -> `Cross-guild isolation under multiple running bot instances`
    - `8. Observed gaps in current implementation` -> `G-02`
    - `9. Separation of As-Is vs To-Be` -> `State safety`
  - Supporting test spec section(s), if relevant:
    - `FI-03 Concurrent state mutations preserve both updates`
- Root cause hypothesis:
  - State persistence is centered on a single JSON file, but there is no repository-level serialization or compare-and-swap discipline across writers.
- Recommended fix:
  - Route all state mutation through one serialized repository API or equivalent optimistic-concurrency boundary and remove direct unsynchronized load-modify-save call patterns.
- Severity: Critical
- Likelihood: Medium
- Blast radius: System-wide
- Priority: P0

## Issue QAI-03 — Exact-minute schedulers can miss a day’s run after late start or stall

- Type: Operational risk
- Primary lens: Ops/Runtime
- Summary:
  - Auto screenshot, news briefing, and EOD jobs only fire on exact-minute checks and do not show same-day catch-up logic after a missed minute.
- Trigger / Reproduction condition:
  - The bot starts after the scheduled minute, reconnects after a short outage, or the event loop is delayed past the trigger minute.
- Current behavior:
  - Heatmap auto-posting uses exact `15:35` and `06:05` checks, and news/EOD use exact configured `HH:MM`; the As-Is spec only confirms catch-up for instrument registry refresh.
- Why this is risky:
  - A transient outage or redeploy can silently skip an entire day’s content for affected jobs.
- Likely impact:
  - Missing daily heatmap/news/EOD posts with no self-recovery path until the next day.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Auto screenshot scheduler` -> `4.4`, `4.7`, `4.8`
    - `Feature: Scheduled news briefing posting` -> `4.2`, `4.7`
    - `Feature: Scheduled EOD summary posting` -> `4.2`, `4.7`
    - `5.2 Scheduled execution behavior`
    - `8. Observed gaps in current implementation` -> `G-03`
  - Supporting test spec section(s), if relevant:
    - `IT-01 Daily news scheduler performs same-day catch-up after late start`
- Root cause hypothesis:
  - Scheduler semantics were implemented as “fire only on matching minute” without a persisted same-day recovery rule for most daily jobs.
- Recommended fix:
  - Add same-day catch-up logic keyed by scheduled time plus last successful run date, similar in spirit to the registry refresh path but adapted to daily posting jobs.
- Severity: High
- Likelihood: Medium
- Blast radius: Multi-feature
- Priority: P1

## Issue QAI-04 — Bootstrap route save failure is not isolated from startup completion

- Type: Operational risk
- Primary lens: Ops/Runtime
- Summary:
  - Startup bootstrap route writes are performed before scheduler start, and save failure in that path is not explicitly isolated in the documented flow.
- Trigger / Reproduction condition:
  - Env bootstrap IDs resolve successfully, state needs updating, and `save_state()` fails during `_bootstrap_guild_channel_routes_from_env()`.
- Current behavior:
  - Bootstrap fetch errors collapse to `None`, but bootstrap save errors are not explicitly caught in that module and schedulers start after bootstrap.
- Why this is risky:
  - A state-write failure during startup can interfere with a bot instance reaching its intended steady state.
- Likely impact:
  - Partial startup where command sync succeeds but background schedulers may not start reliably.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Bot startup, command sync, and bootstrap routing` -> `4.4`, `4.7`
    - `8. Observed gaps in current implementation` -> `G-11`
  - Supporting test spec section(s), if relevant:
    - `FI-01 Bootstrap state save failure does not block bot startup`
- Root cause hypothesis:
  - Bootstrap seeding and scheduler startup are sequenced in one startup path without explicit failure isolation around the save.
- Recommended fix:
  - Catch and record bootstrap save failures separately, then continue startup unless the failure is intentionally considered fatal.
- Severity: Medium
- Likelihood: Low
- Blast radius: System-wide
- Priority: P2

## Issue QAI-05 — Forum upsert recreates same-day content on transient Discord fetch failures

- Type: Defect
- Primary lens: Discord UX
- Summary:
  - The upsert layer falls back to recreation when existing thread or starter fetches fail with `NotFound`, `Forbidden`, or generic `HTTPException`, even though those cases do not all mean the resource is gone.
- Trigger / Reproduction condition:
  - A same-day record exists in state, but Discord returns a transient fetch/edit error while the thread or message still exists.
- Current behavior:
  - `upsert_daily_post()` treats several fetch failure types as equivalent and falls through to create a new thread/content path.
- Why this is risky:
  - Temporary Discord API instability can turn a normal update attempt into duplicate same-day forum content.
- Likely impact:
  - Duplicate heatmap/news/EOD threads or duplicate trend follow-up messages, plus confusing state records pointing to newly created resources.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Daily forum upsert and content-message sync` -> `4.4`, `4.7`, `4.8`
    - `7. Ambiguities and unverifiable areas` -> `Exact starter-thread reuse safety on transient Discord errors`
    - `8. Observed gaps in current implementation` -> `G-08`
    - `9. Separation of As-Is vs To-Be` -> `Same-day post reuse`
  - Supporting test spec section(s), if relevant:
    - `IT-02 Forum upsert does not recreate content on transient Discord fetch failure`
    - `E2E-02 Restart after partial post resumes without duplicate same-day thread`
- Root cause hypothesis:
  - Missing distinction between “resource truly missing” and “resource temporarily unreachable” in Discord fetch/reuse logic.
- Recommended fix:
  - Recreate only on authoritative `NotFound`, and surface `Forbidden` / transient `HTTPException` as retriable failures rather than replacement signals.
- Severity: High
- Likelihood: Medium
- Blast radius: Multi-feature
- Priority: P1

## Issue QAI-06 — Manual heatmap route resolution misclassifies transient Discord outages as configuration failure

- Type: Defect
- Primary lens: Discord UX
- Summary:
  - Manual heatmap routing collapses any forum-resolution exception to `None`, so temporary Discord failures can be reported as if the route is missing or invalid.
- Trigger / Reproduction condition:
  - A guild has a valid stored forum route, but channel resolution fails transiently during `/kheatmap` or `/usheatmap`.
- Current behavior:
  - `_resolve_guild_forum_channel()` returns `None` on any exception, and the command returns a failure message based on missing or invalid route resolution.
- Why this is risky:
  - Operators can be pushed toward unnecessary reconfiguration when the underlying problem is a temporary Discord/API outage.
- Likely impact:
  - Misleading manual-run feedback and avoidable route churn during transient outages.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Manual heatmap posting` -> `4.4`, `4.7`, `4.8`
  - Supporting test spec section(s), if relevant:
    - `FI-05 Partial Discord API outage does not mislead operators into reconfiguration`
- Root cause hypothesis:
  - Resolution logic intentionally simplifies all exceptions to “not found/invalid” for command handling.
- Recommended fix:
  - Distinguish transient fetch failures from true missing/wrong-channel cases and return a temporary failure response for the transient path.
- Severity: Medium
- Likelihood: Medium
- Blast radius: Feature-level
- Priority: P2

## Issue QAI-07 — Route setup commands can store unusable channels because bot permissions are not prevalidated

- Type: Operational risk
- Primary lens: Discord UX
- Summary:
  - Admin route commands validate guild ownership and channel type but do not visibly validate whether the bot can actually post to the selected target.
- Trigger / Reproduction condition:
  - An authorized user sets a forum or text route that belongs to the guild but lacks needed bot permissions.
- Current behavior:
  - The command saves the route and returns success; later posting paths discover the capability problem only at use time.
- Why this is risky:
  - Misconfiguration is accepted as valid and only surfaces later when a scheduled or manual post fails.
- Likely impact:
  - Missed posts or alerts with delayed, harder-to-diagnose operational failures.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Admin route configuration and autoscreenshot toggle commands` -> `4.4`, `4.7`, `4.8`
    - `8. Observed gaps in current implementation` -> `G-04`
  - Supporting test spec section(s), if relevant:
    - `IT-03 Setup commands reject channels the bot cannot actually use`
- Root cause hypothesis:
  - Setup flow validates structural inputs but assumes posting permissions instead of checking them.
- Recommended fix:
  - Validate effective bot permissions at setup time and reject unusable channels with permission-specific feedback.
- Severity: High
- Likelihood: High
- Blast radius: Multi-feature
- Priority: P1

## Issue QAI-08 — Shared watchlist mutation and diagnostic exposure have no enforced authorization contract

- Type: Incomplete contract
- Primary lens: Security
- Summary:
  - Watchlist mutation and diagnostic commands operate on guild-shared or operator-facing surfaces, but only admin route commands visibly enforce owner/admin/global-admin authorization.
- Trigger / Reproduction condition:
  - Any guild user with command access invokes `/watch add`, `/watch remove`, `/health`, `/last-run`, or `/source-status`.
- Current behavior:
  - Watch add/remove/list require guild context but no admin/owner permission check, and status commands have no explicit authorization gate.
- Why this is risky:
  - Shared configuration can be modified by unintended users, and operational diagnostics can be exposed more broadly than intended.
- Likely impact:
  - Noisy or deleted watch targets, misleading alert behavior, and widened visibility of provider/job status details.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Watchlist management` -> `4.4`, `4.7`, `4.8`
    - `Feature: Status and diagnostic commands` -> `4.4`, `4.7`, `4.8`
    - `5.3 Manual/admin command behavior`
    - `7. Ambiguities and unverifiable areas` -> `Intended authorization scope for watch and status commands`
    - `8. Observed gaps in current implementation` -> `G-05`, `G-06`
    - `9. Separation of As-Is vs To-Be` -> `Watch authorization`, `Status commands`
  - Supporting test spec section(s), if relevant:
    - `IT-05 Status commands enforce operator-only diagnostics`
    - `E2E-03 Shared watchlist mutation stays isolated by guild and role`
    - `RG-04 Watch command authorization does not regress on future refactors`
- Root cause hypothesis:
  - The codebase has a narrow admin authorization helper for route commands only, but no shared permission policy for other guild-scoped mutable or diagnostic commands.
- Recommended fix:
  - Define the intended authorization contract for shared watch surfaces and diagnostics, then enforce it consistently across these command handlers.
- Severity: High
- Likelihood: High
- Blast radius: Multi-feature
- Priority: P1

## Issue QAI-09 — Status and watch responses do not manage Discord message-length limits

- Type: Operational risk
- Primary lens: Discord UX
- Summary:
  - Status and watch-list responses are plain text surfaces with no visible chunking or truncation logic, even though they can grow with state size or failure detail.
- Trigger / Reproduction condition:
  - Many watch symbols, long provider failure details, or accumulated status lines cause a command response to exceed Discord’s message length limit.
- Current behavior:
  - Status commands format rows into plain text and send one ephemeral response; watch list formatting also appears to use a single message with no explicit size management.
- Why this is risky:
  - Exactly when diagnostics are most needed, the command itself can fail to deliver output.
- Likely impact:
  - Failed `/health`, `/source-status`, `/last-run`, or `/watch list` responses during incidents or large configurations.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Watchlist management` -> `4.8`
    - `Feature: Status and diagnostic commands` -> `4.4`, `4.7`, `4.8`
    - `8. Observed gaps in current implementation` -> `G-07`
  - Supporting test spec section(s), if relevant:
    - `RG-02 Status commands stay under Discord message length limits`
- Root cause hypothesis:
  - Command output formatting assumes small payloads and does not enforce Discord text limits on these surfaces.
- Recommended fix:
  - Introduce deterministic chunking or truncation policies for long watch/status responses and test against Discord length limits.
- Severity: Medium
- Likelihood: Medium
- Blast radius: Feature-level
- Priority: P2

## Issue QAI-10 — Watch alerts can evaluate stale or off-hours quotes as live signals

- Type: Defect
- Primary lens: Data/Domain
- Summary:
  - Watch polling has no explicit market-session gate, and the As-Is spec confirms domestic quote freshness uses `now` as `asof`, making stale or off-hours data able to influence alert logic.
- Trigger / Reproduction condition:
  - Polling occurs during closed sessions, holidays, delayed-data windows, or provider responses that do not reflect a truly fresh market timestamp.
- Current behavior:
  - Watch polling runs on interval, not session state; domestic quote freshness is based on `now`; alert logic still evaluates thresholds from the returned quote.
- Why this is risky:
  - The system can emit false alerts, suppress needed alerts, or report misleading job status based on non-live market state.
- Likely impact:
  - Operator confusion, noisy alerts, and reduced trust in watch polling.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Watch poll and threshold alerting` -> `4.4`, `4.7`, `4.8`, `4.9`
    - `7. Ambiguities and unverifiable areas` -> `Watch polling market-hours semantics`
    - `8. Observed gaps in current implementation` -> `G-09`
    - `9. Separation of As-Is vs To-Be` -> `Watch polling`
  - Supporting test spec section(s), if relevant:
    - `UT-02 Domestic quote freshness uses source timestamp`
    - `FI-02 Closed-market watch poll is skipped instead of treated as quote failure`
- Root cause hypothesis:
  - Quote freshness and session policy are left largely to provider internals, while the scheduler itself lacks explicit market-hours control.
- Recommended fix:
  - Parse and honor source timestamps for freshness, add explicit session/holiday gating for watch polling, and classify closed-market intervals separately from genuine quote failures.
- Severity: Critical
- Likelihood: High
- Blast radius: Feature-level
- Priority: P0

## Issue QAI-11 — Watch provider health is recorded per symbol and can misreport the poll

- Type: Defect
- Primary lens: Ops/Runtime
- Summary:
  - Provider status is updated on each individual quote result, so the final provider row can reflect only the last processed symbol rather than the overall poll outcome.
- Trigger / Reproduction condition:
  - One symbol fails and a later symbol succeeds, or vice versa, within the same watch poll run.
- Current behavior:
  - The quote provider status is updated immediately on success or failure per symbol during the loop.
- Why this is risky:
  - `/source-status` can show healthy or failed provider state that does not match the actual mixed outcome of the poll.
- Likely impact:
  - Misleading operator diagnostics and weaker incident triage during partial provider degradation.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Watch poll and threshold alerting` -> `4.4`
  - Supporting test spec section(s), if relevant:
    - `IT-04 Watch poll aggregates provider health per poll instead of last-symbol-wins`
- Root cause hypothesis:
  - Status reporting is written at symbol granularity instead of being aggregated once per provider per poll.
- Recommended fix:
  - Aggregate provider results across the whole poll and publish one provider-health summary after the loop.
- Severity: Medium
- Likelihood: High
- Blast radius: Feature-level
- Priority: P2

## Issue QAI-12 — EOD posting path publishes through a mock provider when enabled

- Type: Defect
- Primary lens: Functional
- Summary:
  - The EOD scheduler path is implemented, but the current provider wiring is explicitly a `MockEodSummaryProvider()`.
- Trigger / Reproduction condition:
  - `EOD_SUMMARY_ENABLED` is turned on in a deployed environment.
- Current behavior:
  - The bot resolves forums, calls the mock provider, renders the result, and can post daily EOD threads.
- Why this is risky:
  - Enabling the feature can produce operator-facing content that is not backed by live market data.
- Likely impact:
  - Incorrect EOD posts that appear operationally real unless an operator already knows the provider is mocked.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Scheduled EOD summary posting` -> `4.3`, `4.4`, `4.8`
    - `7. Ambiguities and unverifiable areas` -> `EOD feature maturity vs operational intent`
    - `8. Observed gaps in current implementation` -> `G-10`
    - `9. Separation of As-Is vs To-Be` -> `EOD summary`
  - Supporting test spec section(s), if relevant:
    - `UT-05 Production provider factory fails closed when only mock providers are available`
- Root cause hypothesis:
  - The runtime job path exists ahead of a live provider rollout, but there is no fail-closed guard when the feature is enabled.
- Recommended fix:
  - Refuse production posting when only mock EOD data is available, or make the mock mode explicitly labeled and isolated from normal runtime enablement.
- Severity: High
- Likelihood: Medium
- Blast radius: Feature-level
- Priority: P1

## Issue QAI-13 — Runtime registry corruption can break direct load paths instead of degrading safely

- Type: Operational risk
- Primary lens: Data/Domain
- Summary:
  - The As-Is spec confirms that invalid runtime registry payloads can raise on direct load, while only the status path is explicitly described as converting load failure into a failed row.
- Trigger / Reproduction condition:
  - `data/state/instrument_registry.json` exists but contains invalid or unreadable payload.
- Current behavior:
  - `registry_status()` handles load failure gracefully for status reporting, but direct runtime registry loads may raise.
- Why this is risky:
  - A corrupted runtime artifact can turn lookup or quote-resolution paths into hard failures rather than a controlled fallback.
- Likely impact:
  - Watch symbol resolution or provider lookup failures until the runtime registry artifact is repaired or removed.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Instrument registry load/search/runtime refresh` -> `4.4`, `4.7`, `4.8`
  - Supporting test spec section(s), if relevant:
    - `RG-03 Runtime registry corruption falls back to bundled snapshot`
- Root cause hypothesis:
  - Runtime registry loading prioritizes file order and local artifacts but does not consistently degrade to bundled artifacts across all call paths.
- Recommended fix:
  - Apply the same safe-fallback behavior to direct runtime loads that already exists in the status-reporting surface, or explicitly mark the runtime artifact unusable and continue with bundled data.
- Severity: Medium
- Likelihood: Medium
- Blast radius: Feature-level
- Priority: P2

## Issue QAI-14 — News and trend success semantics for partial or empty regional output are undefined

- Type: Incomplete contract
- Primary lens: Functional
- Summary:
  - The system posts separate domestic/global news threads and optional trend placeholders, but the As-Is spec does not define whether empty-region output or placeholder content should be considered healthy success.
- Trigger / Reproduction condition:
  - One region has no meaningful briefing content, or trend posting renders a placeholder for a non-qualifying region while still creating a thread.
- Current behavior:
  - News job status is based on posted/failure counts, trend can render placeholder region content, and the As-Is boundary table explicitly says partial-region success should not be assumed robustly defined.
- Why this is risky:
  - Operators may interpret empty or placeholder-backed posts as healthy delivery when the content is actually partial.
- Likely impact:
  - Silent content-quality drift and weaker incident detection for degraded news coverage.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Scheduled news briefing posting` -> `4.4`, `4.7`, `4.8`
    - `Feature: Scheduled trend briefing posting` -> `4.4`, `4.7`
    - `9. Separation of As-Is vs To-Be` -> `News posting`, `Trend posting`
  - Supporting test spec section(s), if relevant:
    - `RG-01 Empty regional briefing must not report plain ok`
- Root cause hypothesis:
  - Posting success is tracked operationally, but content sufficiency rules were not formalized into job-health semantics.
- Recommended fix:
  - Define explicit success/degradation rules for empty-region news and placeholder trend outputs, then encode those rules into job status computation.
- Severity: Medium
- Likelihood: Medium
- Blast radius: Feature-level
- Priority: P2

## Issue QAI-15 — Regional failure isolation in scheduled news is weaker than the output model suggests

- Type: Operational risk
- Primary lens: Functional
- Summary:
  - The job posts domestic and global threads separately, but provider failure is treated as a whole-job failure and the As-Is spec explicitly warns not to assume robust regional failure isolation.
- Trigger / Reproduction condition:
  - A configured news provider path fails while another region’s output could still be usable, especially under `NEWS_PROVIDER_KIND=hybrid`.
- Current behavior:
  - Provider failure marks both `news_briefing` and `trend_briefing` failed and returns early; separate domestic/global posting only occurs after a successful analysis path.
- Why this is risky:
  - One upstream failure can suppress all regional outputs even when part of the data path might still be usable.
- Likely impact:
  - Lost domestic/global briefings and avoidable all-or-nothing failures during partial provider degradation.
- Evidence basis:
  - As-Is section(s):
    - `Feature: Scheduled news briefing posting` -> `4.3`, `4.4`, `4.7`
    - `9. Separation of As-Is vs To-Be` -> `News posting`
  - Supporting test spec section(s), if relevant:
    - `UT-04 Hybrid news preserves healthy region on partial provider failure`
- Root cause hypothesis:
  - Scheduler/job status logic is organized around one analysis success path, not explicit region-level degradation handling.
- Recommended fix:
  - Isolate regional/provider failures so healthy regional output can still post with degraded status when the current provider mix supports partial results.
- Severity: High
- Likelihood: Medium
- Blast radius: Feature-level
- Priority: P1

## Issue QAI-16 — Multi-instance deployment assumptions are undocumented despite lock-free shared state

- Type: Documentation gap
- Primary lens: Architecture
- Summary:
  - The As-Is spec does not confirm whether multiple bot instances are supported, yet the persistence model is a single shared JSON file without visible inter-process locking.
- Trigger / Reproduction condition:
  - Operators run multiple instances for failover, redeploy overlap, or accidental duplicate launches.
- Current behavior:
  - The current documentation baseline only says multi-instance support cannot be confirmed and single-process operation seems likely.
- Why this is risky:
  - Operations teams can make unsupported deployment assumptions that amplify state races and duplicate execution.
- Likely impact:
  - Conflicting writes, inconsistent state, or duplicate posting when multiple processes operate on the same state directory.
- Evidence basis:
  - As-Is section(s):
    - `7. Ambiguities and unverifiable areas` -> `Cross-guild isolation under multiple running bot instances`
    - `9. Separation of As-Is vs To-Be` -> `State safety`
  - Supporting test spec section(s), if relevant:
    - None directly
- Root cause hypothesis:
  - Operational topology assumptions were never made explicit even though the implementation strongly resembles a single-writer local-process design.
- Recommended fix:
  - Document the supported deployment topology explicitly and, if multi-instance operation is intended, pair that with real state-coordination changes.
- Severity: Medium
- Likelihood: Low
- Blast radius: System-wide
- Priority: P3

# 4. Root-cause grouping table

| Root Cause Group | Related Issues | Why it matters | Priority |
|---|---|---|---|
| Persistence/state integrity | QAI-01, QAI-02, QAI-04, QAI-13, QAI-16 | The system’s mutable truth lives in local JSON files; fail-open reads, lost writes, or unclear deployment assumptions can corrupt many features at once. | P0 |
| Scheduling semantics and recovery | QAI-03 | Daily jobs can silently disappear from production output after ordinary restarts or short stalls. | P1 |
| Discord resource lifecycle handling | QAI-05, QAI-06 | Transient Discord failures can create duplicates or mislead operators into reconfiguration instead of safe retry behavior. | P1 |
| Permission and setup validation | QAI-07, QAI-08 | Unsafe or unusable operational surfaces can be accepted and then fail later or be used by the wrong audience. | P1 |
| Provider/data-quality signaling | QAI-10, QAI-11, QAI-12, QAI-14, QAI-15 | The system can publish or signal data that is stale, mock, partial, or operationally misrepresented. | P0 |
| Response-surface resilience | QAI-09 | Diagnostic commands can fail exactly when state detail grows and operators most need them. | P2 |

# 5. Release blocking assessment

- Release blockers
  - `QAI-01`, `QAI-02`, `QAI-03`, `QAI-05`, `QAI-10`
  - These are blockers because they can cause durable state loss, silent skipped schedules, duplicate forum content, or false watch alerts without requiring unusual operator mistakes.
- High-risk but shippable with mitigation
  - `QAI-07`, `QAI-08`, `QAI-12`, `QAI-14`, `QAI-15`
  - These are serious but can be partially contained if operators limit who uses certain commands, validate channels manually, keep EOD disabled, and accept degraded news semantics temporarily.
- Can be deferred
  - `QAI-04`, `QAI-06`, `QAI-09`, `QAI-11`, `QAI-13`, `QAI-16`
  - These still matter, but they are either narrower in blast radius, lower in likelihood, or manageable through operator awareness until core stability/correctness issues are resolved first.

# 6. Suggested implementation order

- Phase 1: immediate stabilization
  - `QAI-01`, `QAI-02`, `QAI-03`, `QAI-05`, `QAI-10`
  - Sequencing logic:
    - Protect authoritative state first, because every other fix depends on state not being lost or overwritten.
    - Then fix duplicate-posting and missed-run scheduler semantics so the bot stops creating visible production incidents.
    - Close with watch data-quality controls because false alerts are a direct trust-breaker once scheduling is stable enough to run regularly.
- Phase 2: correctness hardening
  - `QAI-07`, `QAI-08`, `QAI-12`, `QAI-14`, `QAI-15`
  - Sequencing logic:
    - After core runtime stability is improved, tighten operational correctness at the edges: valid routes, defined authorization surfaces, fail-closed EOD behavior, and clearer regional/news success semantics.
- Phase 3: operability and maintainability
  - `QAI-04`, `QAI-06`, `QAI-09`, `QAI-11`, `QAI-13`, `QAI-16`
  - Sequencing logic:
    - These items improve startup resilience, operator feedback quality, status accuracy, registry degradation behavior, and deployment clarity once the main incident drivers are under control.

# 7. GitHub issue conversion shortlist

| Ticket order | Issue ID | Proposed GitHub issue title | Why first |
|---|---|---|---|
| 1 | QAI-01 | Prevent corrupt or unreadable state from being saved back as authoritative empty state | One bad read can wipe routing, watchlists, and job history across the whole bot. |
| 2 | QAI-02 | Serialize JSON state mutations across commands, schedulers, and startup bootstrap | Silent lost writes undermine every stateful feature and complicate all later debugging. |
| 3 | QAI-05 | Distinguish transient Discord fetch failures from true NotFound in forum upsert | Duplicate same-day threads are visible operator-facing incidents across multiple posting features. |
| 4 | QAI-03 | Add same-day catch-up rules for exact-minute daily schedulers | Ordinary restarts currently risk losing an entire day of scheduled output. |
| 5 | QAI-10 | Add watch session gating and trustworthy quote freshness handling | False or stale watch alerts directly damage confidence in the bot’s market signals. |
| 6 | QAI-07 | Validate effective bot permissions in route setup commands before saving routes | Prevents latent misconfiguration from reaching production posting paths. |
| 7 | QAI-08 | Define and enforce authorization policy for shared watchlist mutation and diagnostic commands | Shared state mutation and operational diagnostics are too open to leave implicit. |
| 8 | QAI-12 | Fail closed when EOD is enabled without a live provider | Keeps a paused/mock feature from publishing misleading operator-facing content. |

# 8. Explicit non-issues

- Item
  - Legacy `!ping` handler presence
- Why it is not currently an issue
  - The As-Is spec confirms the handler exists, but also marks practical reachability as ambiguous because `message_content` is disabled in the inspected configuration.
- What would need to change before it becomes one
  - If message content intent is intentionally enabled or the path is confirmed live in production, it becomes a concrete command-surface governance issue.

- Item
  - Trend thread suppression when both regions have fewer than 3 themes
- Why it is not currently an issue
  - The As-Is spec documents this as the implemented rule for current trend posting behavior, not as a broken path by itself.
- What would need to change before it becomes one
  - A product or operational contract would need to state that trend posts must still publish below that threshold.

- Item
  - Instrument registry refresh catch-up support
- Why it is not currently an issue
  - The As-Is spec explicitly confirms that registry refresh is the one scheduler path that already has same-day-after-scheduled-time catch-up behavior.
- What would need to change before it becomes one
  - Only if the implementation diverges from that documented behavior or the catch-up path proves incomplete in code/tests.

- Item
  - Runtime heatmap routing reading state instead of env after bootstrap
- Why it is not currently an issue
  - The As-Is spec and project operating rules consistently treat `data/state/state.json` as the mutable source of truth for per-guild routing.
- What would need to change before it becomes one
  - It would only become an issue if runtime routing silently preferred env over state or if bootstrap overwrote state repeatedly.

- Item
  - Trend message length handling
- Why it is not currently an issue
  - The As-Is spec explicitly notes that trend message splitting/truncation is handled inside `trend_policy.py` with a 2000-character limit.
- What would need to change before it becomes one
  - It would become an issue if trend rendering bypassed that policy or live output demonstrated over-limit failures.

- Item
  - EOD being disabled by default
- Why it is not currently an issue
  - Disabled-by-default is an operational posture, not a defect; the actual issue is that the provider is mock-backed if someone enables the feature.
- What would need to change before it becomes one
  - It becomes a correctness issue when EOD is enabled without a live/fail-closed provider path.
