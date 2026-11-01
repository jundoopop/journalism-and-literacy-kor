# Backend Technology Recommendations

## Executive recommendation

The project already has a credible Python backend foundation: Flask, Pydantic settings, SQLAlchemy/Alembic, Redis, multiple model-provider adapters, retries/circuit breaking, structured logging, and tests. The highest-value enhancement is **not** to add every popular AI framework. It is to strengthen deployment, persistence, security, and asynchronous execution around the pipeline that already exists.

Recommended order:

1. **Dockerize the API and add PostgreSQL** to the existing Compose environment.
2. **Add a background job queue** for crawl + multi-model analysis work.
3. **Harden URL fetching, API authentication, rate limiting, and CORS** before exposing the service beyond localhost.
4. **Keep the existing provider abstraction** and modernize provider SDKs incrementally.
5. **Consider FastAPI only as a measured migration**, primarily for typed API contracts and generated OpenAPI documentation.
6. **Do not add LangChain, LlamaIndex, or a vector database yet** unless a concrete retrieval or durable-agent requirement is approved.

---

## Current baseline

| Concern | Current implementation | Assessment |
|---|---|---|
| Language | Python | Keep |
| HTTP API | Flask + Flask-CORS | Adequate now; contract typing is the main gap |
| Model access | Gemini, OpenAI, Anthropic, Mistral, Llama adapters | Strong abstraction; keep provider-neutral design |
| Persistence | SQLAlchemy + Alembic, default SQLite file | Good development baseline; migrate production to PostgreSQL |
| Cache | Redis | Keep |
| Long-running work | Synchronous request path | Add a job queue |
| Deployment | Compose runs Redis only | Add API, worker, PostgreSQL, and health checks |
| Retrieval/vector search | Sentence Transformers used for benchmarks; no product RAG requirement | Do not add a vector store yet |
| Observability | Structured logs, correlation IDs, in-process metrics | Add standards-based exported metrics/traces later |

---

## Technology-by-technology decision

### 1. Python — keep and standardize

**Decision: Adopt more rigor, not a new language.**

Python is appropriate because crawling, NLP, model SDKs, benchmark tooling, and the API already share one ecosystem. A language rewrite would add operational cost without solving the current bottlenecks.

Recommended improvements:

- Establish one supported Python version in `.python-version` or project metadata.
- Replace the single flat runtime/test dependency file with a package definition and lock file (`pyproject.toml` plus a chosen lock workflow).
- Add Ruff for formatting/linting and mypy or Pyright for type checking.
- Separate runtime, development, benchmark, and optional-provider dependencies.
- Add a dependency update and vulnerability-scanning policy.

**Priority: P1.**

### 2. FastAPI — useful, but migration should be incremental

**Decision: Consider after API contract tests are stable.**

FastAPI would be useful for this project because Pydantic is already present and the extension/backend integration needs explicit request/response contracts. It can provide typed validation and generated OpenAPI schemas. However, replacing Flask does not by itself improve crawling or model latency, and a large rewrite would risk destabilizing working service and middleware layers.

Recommended approach:

1. First define Pydantic request/response models independently of Flask.
2. Generate or validate a checked-in OpenAPI/JSON Schema contract.
3. Measure whether Flask causes a real maintenance or concurrency constraint.
4. If migration is justified, preserve the existing service layer and replace only the transport layer endpoint by endpoint.

**Do not** run Flask and FastAPI as indefinitely duplicated production APIs.

**Priority: P2 / conditional.**

### 3. OpenAI and other model providers — keep multi-provider architecture

**Decision: Keep provider abstraction; avoid making one SDK the domain model.**

The repository already supports several providers behind a factory. This is more valuable for consensus research than replacing everything with a single-provider implementation. The enhancement should be a normalized internal analysis contract, not another direct SDK call in endpoint code.

Recommended improvements:

- Define a provider-independent structured result model for selected sentence, reason, usage, latency, model ID, and finish/error state.
- Validate model output against JSON Schema or Pydantic before consensus aggregation.
- Capture provider-reported token usage where available; label estimates separately.
- Pin model IDs through configuration rather than source constants.
- Add per-provider timeout, retry, concurrency, and cost budgets.
- Upgrade SDKs in isolated changes with provider contract tests.

**Priority: P0–P1.**

### 4. LangChain or LlamaIndex — not currently justified

**Decision: Do not add now.**

The present pipeline is deterministic: fetch article, parse it, invoke one or more providers, aggregate results, cache, and return highlights. The existing service and provider abstractions already cover this orchestration without a framework dependency.

Introduce an orchestration framework only if at least one of these requirements appears:

- Durable, resumable, multi-step workflows with human approval.
- Complex tool-calling agents with branching state.
- A substantial retrieval ingestion/query pipeline with many connector types.
- A demonstrated maintenance reduction after a small proof of concept.

If durable workflow execution becomes necessary, compare a workflow engine or a graph-based orchestrator against a conventional task queue; do not assume an “AI framework” is automatically the best job runner.

**Priority: Not planned / requirement-triggered.**

### 5. ChromaDB, FAISS, Qdrant, Pinecone — avoid until retrieval is a product feature

**Decision: No dedicated vector database yet.**

Current analysis operates on one fetched article and does not need semantic retrieval over a corpus. Adding a vector database now would introduce embedding lifecycle, indexing, backup, schema-version, and data-deletion obligations without improving the main request path.

If future requirements include “find similar coverage,” source comparison across a corpus, claim/evidence retrieval, or RAG over archived articles, use this progression:

1. Start with **PostgreSQL + pgvector** so article metadata, permissions, analytics, and vectors share transactional storage.
2. Benchmark exact search first, then HNSW/IVFFlat only when corpus size and latency require it.
3. Evaluate Qdrant/Pinecone only when measured scale, tenancy, filtering, or operations exceed the PostgreSQL design.
4. Use FAISS only for offline/local experiments where persistence and multi-user service guarantees are unnecessary.
5. Use ChromaDB only for prototypes, not as an automatic production default.

pgvector supports exact and approximate nearest-neighbor search, including HNSW and IVFFlat, while retaining PostgreSQL joins and transactional behavior. See the [official pgvector documentation](https://github.com/pgvector/pgvector).

**Priority: P3 / feature-triggered.**

### 6. PostgreSQL — recommended for production

**Decision: Add as the production database; retain SQLite for lightweight local development/tests.**

The analytics schema already uses SQLAlchemy and Alembic, so PostgreSQL is a relatively natural evolution. It improves concurrent writes, operational tooling, backups, constraints, indexing, and future vector support.

Migration plan:

1. Make `DATABASE_URL` the canonical setting while preserving a SQLite default for local use.
2. Test all models and migrations against PostgreSQL in CI.
3. Replace SQLite-specific assumptions and add connection-pool configuration.
4. Add PostgreSQL to Compose with a persistent volume and health check.
5. Define backup, restore, retention, and migration rollback procedures before production use.

**Priority: P0 for hosted/multi-user deployment; P2 for localhost-only research.**

### 7. Docker — expand the existing Compose setup

**Decision: Strongly recommended.**

Docker Compose currently provisions Redis but not the application or its database. A reproducible stack should include:

- `api`: the HTTP service, running as a non-root user.
- `worker`: background crawl/analysis jobs using the same application image.
- `redis`: cache and/or queue broker, not publicly exposed in production.
- `postgres`: durable relational storage.
- Optional development-only profiles for admin/observability tools.

Required hardening:

- Multi-stage image build and pinned base image.
- Container health checks and dependency readiness checks.
- Read-only filesystem where feasible, explicit writable data paths, and no baked-in secrets.
- Resource limits, graceful shutdown, and restart policy.
- Separate development overrides from production settings.

**Priority: P0–P1.**

---

## More important missing essentials

### Background jobs and idempotency

Consensus analysis can exceed normal browser/API timeouts because crawling and multiple provider calls happen synchronously. Add a job API:

1. `POST /analyses` validates input and returns `202 Accepted` with a job ID.
2. A worker crawls and analyzes the article.
3. `GET /analyses/{id}` returns queued/running/succeeded/partial/failed state.
4. The extension polls with backoff or receives updates through server-sent events.

Use an idempotency key derived from canonical URL + analysis mode + providers + prompt/model versions. A simple Redis-backed queue (RQ, Dramatiq, or Celery where its broader feature set is genuinely needed) is more appropriate than LangChain for this responsibility.

### Security boundary

The server accepts a URL and fetches it. Before remote deployment, add SSRF protection:

- Allow only `http`/`https` and approved news domains, or enforce a configurable allowlist.
- Resolve hostnames and reject loopback, link-local, private, multicast, and reserved address ranges.
- Revalidate every redirect destination.
- Apply response-size, content-type, redirect-count, and download-time limits.
- Add authentication and rate limiting to analysis endpoints.
- Restrict CORS to the extension origin and configured development origins rather than enabling all origins.
- Never return provider secrets or raw sensitive exception details.

This security work has higher priority than introducing a vector store or AI orchestration framework.

### API contracts and testing

- Add Pydantic models for every request and response.
- Add contract tests for `/health`, `/analyze`, and `/analyze_consensus`.
- Test partial provider failure, timeout, invalid output, cache hit, and unsupported URL paths.
- Add JavaScript tests for extension settings serialization and health-response parsing.
- Run PostgreSQL and Redis integration tests in CI.

### Observability

Keep correlation IDs and structured logs, then add:

- Prometheus-compatible metrics export.
- OpenTelemetry traces spanning API → crawler → provider(s) → database/cache.
- Per-provider latency, timeout, token, estimated/actual cost, and failure metrics.
- Queue depth, job age, cache hit rate, crawler extraction quality, and partial-consensus metrics.

---

## Recommended target architecture

```text
Chrome Extension
      |
      v
API (Flask now; optionally FastAPI later)
  |-- validates/authenticates/rate-limits
  |-- creates idempotent analysis job
  |
  +--> PostgreSQL (jobs, articles, results, analytics)
  +--> Redis (cache, rate limits, queue broker)
  +--> Worker
         |-- SSRF-safe crawler + parser registry
         |-- provider-neutral LLM adapters
         |-- structured output validation
         |-- consensus aggregation
         +-- persists result and metrics
```

Optional later:

```text
PostgreSQL + pgvector
  only when corpus retrieval / similar-article search / RAG is approved
```

---

## Suggested implementation sequence

### Phase A — production essentials

- Add SSRF-safe URL validation and redirect enforcement.
- Add request/response models and contract tests.
- Add API authentication, rate limiting, and restricted CORS.
- Containerize the API and run the full test suite in CI.

### Phase B — durable execution and data

- Add PostgreSQL and migration tests.
- Add background worker/job status API and idempotency.
- Expand Compose to API + worker + Redis + PostgreSQL.
- Add backup/restore and deployment runbooks.

### Phase C — quality and operations

- Export metrics and traces.
- Add provider cost/concurrency budgets and structured-output validation.
- Add browser-side contract tests and end-to-end extension tests.
- Benchmark p50/p95 latency, partial success rate, and extraction quality.

### Phase D — only after evidence of need

- Evaluate FastAPI transport migration.
- Add pgvector for corpus retrieval.
- Evaluate a workflow/agent framework for genuinely stateful multi-step use cases.

---

## Final selection

| Technology | Recommendation | Why |
|---|---|---|
| Python | **Keep** | Best fit for current crawling/NLP/model ecosystem |
| FastAPI | **Consider later** | Useful typed contracts/OpenAPI, but not worth an immediate rewrite |
| OpenAI/other providers | **Keep multi-provider abstraction** | Consensus and provider flexibility are core strengths |
| LangChain/LlamaIndex | **Do not add now** | Existing workflow is simple and deterministic |
| ChromaDB/FAISS/Qdrant/Pinecone | **Do not add now** | No current corpus-retrieval requirement |
| PostgreSQL | **Add for production** | Concurrency, durability, operations, and future pgvector path |
| Docker | **Expand now** | Reproducible API/worker/database deployment |
| Job queue | **Add now for production** | Long-running consensus work should not live in one HTTP request |
| Security controls | **Highest priority** | URL-fetching service creates a serious remote-deployment boundary |
