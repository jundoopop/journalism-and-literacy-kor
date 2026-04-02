# Chrome Extension + Pipeline Assessment

## Scope
This assessment reviews:
- The Chrome extension architecture and runtime behavior (`chrome-ex/*`)
- The backend/API pipeline (`scripts/server.py`, `scripts/services/*`, `scripts/crawler_unified.py`)
- Cross-component integration quality and operational readiness

## Executive Summary
The repository shows a **strong modular direction** with service-layer separation, observability hooks, caching, and support for both single-provider and consensus analysis modes. The backend architecture is well-positioned for research and production-hardening.

However, there are several integration drifts between extension and backend contracts that reduce reliability in real-world use. The most significant issue is a health-check response mismatch that can make the extension report server disconnection even when the backend is up.

---

## 1) Chrome Extension Assessment

### Strengths
1. **Clean MV3 structure**: service worker (`background.js`), content script (`content.js`), popup and settings separation.
2. **Practical caching** in extension storage with mode/provider-specific cache keys and TTL handling.
3. **Good UX pattern** in content script:
   - Auto-run after load
   - Manual activate/deactivate/reload controls
   - Rich tooltip metadata for consensus insights
4. **Permission footprint is limited** to required domains + localhost API.

### Risks / Issues
1. **Health-check contract mismatch (High)**
   - Extension expects `result.status === 'ok' && result.gemini_ready` in `background.js`.
   - Backend `/health` returns `overall_status` and `components` schema.
   - Result: false-negative health status in popup (`연결 안됨`) despite running backend.

2. **Provider-option mismatch between UI and backend defaults (Medium)**
   - Settings UI only exposes Gemini/OpenAI/Claude.
   - Backend defaults emphasize Gemini + Mistral consensus.
   - This can produce surprising behavior in cross-mode testing and docs drift.

3. **Localization/maintainability friction (Low)**
   - Mixed Korean/English comments and labels are acceptable for team context, but it increases onboarding cost for external contributors.

---

## 2) Backend Pipeline Assessment

### Current Pipeline (as implemented)
1. **Request ingress** at Flask endpoint (`/analyze` or `/analyze_consensus`).
2. **Validation** and request-level logging/metrics context.
3. **Crawling layer** via `CrawlerService` → unified crawler routing.
4. **Analysis layer** via `AnalysisService`:
   - Single provider (Gemini default)
   - Multi-provider consensus aggregation
5. **Caching layer** (Redis-backed service where available).
6. **Observability + analytics persistence**:
   - Metrics instrumentation
   - Request and analysis logging into DB
7. **Structured response** for extension consumption.

### Strengths
1. **Service-oriented refactor is meaningful**:
   - Separation of concerns across crawler, analysis, cache, health, feature flags.
2. **Configuration hygiene** via Pydantic settings and validation.
3. **Operational features present**:
   - Admin endpoints
   - Health aggregation
   - Feature flags
   - DB-backed analytics
4. **Testing footprint exists** across unit and integration paths.

### Risks / Issues
1. **Crawler coverage inconsistency (Medium)**
   - Unified parser mapping explicitly routes only Chosun/Joongang; others are generic fallback.
   - Yet extension claims support across five Korean outlets.
   - This can create variable extraction quality by domain.

2. **Health semantics inconsistency in tests vs implementation (Medium)**
   - Some tests expect statuses like `healthy/unhealthy/not_configured` while provider health methods return `up/down/not_configured`.
   - Indicates potential contract drift and weak schema standardization.

3. **Legacy pathway overlap (Low-Medium)**
   - Native host flow and HTTP server flow coexist.
   - Useful for migration, but increases maintenance surface unless one is declared primary/deprecated.

---

## 3) End-to-End Program Readiness

### Overall Rating
- **Architecture maturity**: 8/10
- **Extension-backend contract stability**: 6/10
- **Production readiness for controlled deployment**: 7/10
- **Research platform flexibility**: 9/10

### Why
The program has strong internals and clear separation, but quality currently depends on eliminating interface drift between frontend extension assumptions and backend responses.

---

## 4) Prioritized Recommendations

### P0 (Immediate)
1. **Unify health response contract**
   - Either update extension `checkServerHealth()` to use `overall_status` semantics, or expose backward-compatible fields in `/health`.
2. **Define and version API response schemas**
   - Especially `/health`, `/analyze`, `/analyze_consensus`.

### P1 (Near-term)
1. **Align provider UX and backend defaults**
   - Add Mistral in extension settings UI or change backend defaults/documentation.
2. **Increase parser routing coverage**
   - Route all claimed supported domains to explicit parser modules where available.

### P2 (Hardening)
1. **Deprecation strategy for native messaging path**
   - Keep dual-path only if required; otherwise reduce code duplication.
2. **Contract tests between extension and API**
   - Add integration tests that validate real JSON schemas consumed by `background.js` and `content.js`.

---

## 5) Detailed Suggested Sprint Plan (6 Sprints)

### Sprint 1 (Week 1): API Contract Stabilization
**Goal:** Remove extension/backend handshake ambiguity and establish versioned response contracts.

**Scope**
1. Define canonical JSON schemas for:
   - `GET /health`
   - `POST /analyze`
   - `POST /analyze_consensus`
2. Decide backward-compatibility approach:
   - Option A: Extension migrates to new schema immediately.
   - Option B: Backend returns compatibility fields for one deprecation window.
3. Introduce API contract version field (e.g., `api_version`).

**Deliverables**
- Schema file(s) in `docs/` or code-level typed models.
- Updated extension health-check logic.
- Changelog entry documenting new/legacy fields and sunset timeline.

**Acceptance Criteria**
- Popup connection status accurately reflects backend health in all expected states.
- Contract tests pass for all three endpoints.
- No regressions in manual extension flow (activate/deactivate/reload).

---

### Sprint 2 (Week 2): Extension Settings / Provider Alignment
**Goal:** Align user-facing provider choices with backend consensus defaults and capabilities.

**Scope**
1. Reconcile provider list shown in `settings.html/settings.js` with backend-supported providers.
2. Decide product policy:
   - “UI only exposes providers configured with keys”
   - or “UI shows all providers with readiness badges”
3. Update docs so defaults in README and extension behavior match exactly.

**Deliverables**
- Updated settings UX and validation rules.
- Provider readiness indicator (optional but recommended).
- Documentation synchronization pass.

**Acceptance Criteria**
- No mismatch between selectable providers and server-accepted providers.
- Consensus mode validation remains clear to users.
- QA checklist confirms docs and runtime behavior are consistent.

---

### Sprint 3 (Week 3): Crawler Coverage & Extraction Quality
**Goal:** Raise extraction reliability across all claimed supported media domains.

**Scope**
1. Expand explicit parser routing beyond Chosun/Joongang for all listed outlets.
2. Add domain-specific fixtures and parsing tests.
3. Add fallback observability:
   - Track parser chosen per URL
   - Track extraction completeness (headline/body length/basic quality signals)

**Deliverables**
- Updated parser map and parser implementations.
- Test corpus additions for each supported domain.
- Extraction quality dashboard or summary script.

**Acceptance Criteria**
- Parser routing covers every announced domain explicitly.
- Domain parsing tests pass with target extraction thresholds.
- Fallback rate decreases relative to baseline.

---

### Sprint 4 (Week 4): Reliability, Caching, and Failure Behavior
**Goal:** Improve runtime resilience under provider/network faults.

**Scope**
1. Standardize timeout/retry/error taxonomy across providers.
2. Improve cache behavior:
   - Explicit cache metadata in responses (`cache_hit`, `cached_at`, `ttl_remaining`)
   - Distinguish stale/partial responses safely.
3. Add graceful degradation UX in extension:
   - Clear user feedback for partial consensus or provider failures.

**Deliverables**
- Unified error model documentation.
- Enhanced cache telemetry and logs.
- Extension UX updates for degraded states.

**Acceptance Criteria**
- Known failure scenarios produce deterministic, user-readable outcomes.
- No uncaught promise/exception noise in extension console during simulated outages.
- Error-rate and timeout metrics visible in health/admin output.

---

### Sprint 5 (Week 5): Test Hardening & CI Gates
**Goal:** Prevent contract drift and regression through enforceable automated checks.

**Scope**
1. Add end-to-end contract tests that exercise extension-expected payload shapes.
2. Resolve health status naming inconsistency (`up/down` vs `healthy/unhealthy`) with one canonical enum and mapping.
3. Add CI quality gates:
   - Unit + integration tests
   - Schema validation tests
   - Lint/type checks where applicable

**Deliverables**
- New contract test suite.
- Health status normalization utilities + migration notes.
- CI pipeline updates and required checks policy.

**Acceptance Criteria**
- CI blocks PRs on contract/schema regressions.
- Health semantics are consistent in code, tests, and docs.
- Test flakiness trend improves over baseline.

---

### Sprint 6 (Week 6): Runtime Simplification & Release Readiness
**Goal:** Reduce maintenance overhead and prepare for a stable release train.

**Scope**
1. Decide primary runtime mode (HTTP server vs native messaging host).
2. If dual-path remains:
   - Formal support matrix and ownership model.
   - Shared abstractions to reduce duplication.
3. Release process hardening:
   - Versioning policy
   - Migration guide
   - Rollback checklist

**Deliverables**
- Architecture decision record (ADR) for runtime mode.
- Deprecation or coexistence plan with timeline.
- Release readiness checklist and runbook.

**Acceptance Criteria**
- Team-aligned runtime strategy documented and approved.
- Operational runbook tested in a dry run.
- Candidate release tagged with clear upgrade notes.

---

## 6) Sprint Governance & Metrics

### Cadence and Roles
- **Cadence:** 1-week sprints, demo + retro at end of each sprint.
- **Suggested ownership model:**
  - Extension owner
  - Backend/API owner
  - Data/Crawler owner
  - QA/Platform owner (can be shared role in small teams)

### Core Metrics to Track Weekly
1. Extension-to-backend contract test pass rate.
2. Health-check false-negative rate in popup.
3. Domain parsing success rate and fallback ratio.
4. Median + p95 analysis latency (`/analyze`, `/analyze_consensus`).
5. Cache hit rate and error-rate by provider.
6. Escaped defect count after merge (regression indicator).

### Definition of Done (Program-Level)
- No known P0 contract mismatch remains.
- All supported domains have validated extraction coverage.
- CI enforces contract/schema and integration behavior.
- Runtime mode strategy is documented, communicated, and operationalized.

---

## 7) Sprint Execution Update

### Sprint 1 (In Progress)
- [x] Backward-compatible `/health` response introduced (`api_version`, `status`, `gemini_ready` compatibility fields).
- [x] Extension health check updated to support both legacy and v2+ health schemas.
- [ ] Add endpoint contract tests for `/health`, `/analyze`, `/analyze_consensus`.
- [ ] Publish migration/deprecation notice for legacy health fields.
