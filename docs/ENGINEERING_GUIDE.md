# Engineering walkthrough

This guide explains the maintenance work on the existing News Literacy Analyzer.
It describes implemented behavior and remaining limitations; it does not claim that
all integrations have been tested or that the application is ready for public hosting.

## 1. Trace the complete request

Read [the extension HTTP client](../chrome-ex/background.js),
[Flask routes](../scripts/server.py), [crawler service](../scripts/services/crawler_service.py),
[analysis service](../scripts/services/analysis_service.py), and
[the renderer](../chrome-ex/content.js) in that order.

1. The background worker reads settings and the server's configuration fingerprint.
2. A valid browser-cache entry can satisfy the request without calling an analysis route.
3. Otherwise Flask validates the JSON, URL and provider selection before outbound work.
4. The crawler fetches the article and extracts its text. The analysis service then checks Redis.
5. On a cache miss, the service calls a configured provider or creates a parallel consensus analysis.
6. Adapters decode the response and validate the selected excerpts against the article.
7. Consensus groups matching excerpts and counts distinct provider votes.
8. The server records analytics and returns data; the content script renders highlights and reasons.

**Be able to explain:** where data crosses a process or network boundary, what happens
when each dependency fails, and which parts execute even when a cache is hit.

## 2. Abstraction, interfaces and dependency boundaries

Relevant code: [base contract](../scripts/llm/base.py), [factory](../scripts/llm/factory.py),
[adapters](../scripts/llm/providers), [services](../scripts/services).

`LLMFactory` creates an adapter from configuration. The rest of the application works
with `analyze_article(article_text, system_prompt)` and a typed `AnalysisResult`,
instead of each vendor's response format. The Gemini compatibility wrapper now uses
this same configuration path. An earlier caller used `analyze`, which the adapters
do not implement; repairing that mismatch restored the intended contract.

A useful interface standardizes the result while preserving meaningful differences:
OpenAI's completion-token parameter, Gemini's REST envelope, Mistral's JSON mode,
and Claude's content blocks cannot be assumed identical. SDK construction also does
not establish that an account can access a configured model.

**Learn:** abstraction, adapter/factory patterns, dataclasses, exceptions, dependency
injection and contract testing. A factory simplifies selection; it does not itself
provide retries, failover or correctness.

**Exercise:** describe every change needed to add one provider, including configuration,
key lookup, adapter registration, validation, health reporting and extension selection.
This duplication is a future opportunity to centralize provider metadata.

## 3. Data structures and aggregation algorithms

Relevant code: [consensus aggregation](../scripts/consensus_analyzer.py).

A dictionary maps a whitespace-normalized excerpt to its providers and reasons.
A provider contributes at most one vote to a normalized excerpt. The resulting list
is sorted by vote count. If only one provider succeeds, the label is `insufficient`.
The total requested count and failed-provider list remain available to the caller.

Let S be the total number of selections, U the number of unique normalized excerpts,
and P the number of providers. Hash-table operations have expected constant-time
lookup after accounting for string hashing. The small provider list membership
check adds O(P) work per selection. Aggregation and sorting therefore cost approximately
O(S × P + U log U), plus processing the text characters. With P bounded at five,
this is commonly described as O(S + U log U). Stored reasons and selected providers
also consume memory proportional to the input selections and their text lengths.

Source validation uses substring checks after whitespace normalization. This checks
that an excerpt exists; it does not prove full-sentence boundaries, truth or relevance.

**Learn:** hash maps, normalization, deduplication, sorting, asymptotic complexity and
invariants. A core invariant is "one provider, at most one vote per normalized excerpt."

**Exercise:** work through three providers selecting A/B, A/C and A. Explain the labels
and then repeat after one provider fails. Correlated models can agree and still be wrong.

## 4. Concurrency, threads and queueing

Relevant code: [Gunicorn configuration](../gunicorn.conf.py),
[provider executor](../scripts/consensus_analyzer.py), [HTTP experiment](../benchmarks/http_load.py).

There are two levels of concurrency: HTTP threads serve different requests, and a
per-request `ThreadPoolExecutor` overlaps provider calls for one article. Network
I/O can overlap while a Python thread waits; this is different from making a
CPU-heavy Python loop run eight times faster.

For independent provider calls, sequential time is roughly the sum of their durations.
Parallel completion is closer to the slowest duration plus overhead. The code waits
for provider tasks to finish. A timeout in the browser does not cancel those tasks.
Eight HTTP requests each selecting five providers can create roughly forty simultaneous
provider calls; the current per-request bound is not a global rate or concurrency limit.

**Learn:** threads versus processes, blocking I/O, the GIL, thread pools, queueing,
backpressure, deadlines and cancellation. In a stable system, Little's law relates
average in-flight work L, throughput λ and average latency W: L = λW. It does not
turn a small local measurement into a capacity guarantee.

**Exercise:** identify where to put a global provider semaphore or rate limit and what
HTTP behavior to use when capacity is exhausted. Discuss why more threads can worsen
upstream rate limits and database contention.

## 5. Networking and trust boundaries

Relevant code: [URL fetcher](../scripts/url_safety.py),
[request validation](../scripts/api/validation.py), [tooltips](../chrome-ex/content.js).

A supplied URL is an instruction for the server to make a network request. Without
validation, it could target an internal service: server-side request forgery (SSRF).
The fetcher restricts HTTPS hosts, checks resolved addresses, validates every redirect,
and connects to the checked IP while retaining the original hostname for TLS verification
and the HTTP Host header. This addresses the gap between validating DNS and later
connecting after a second DNS lookup. Redirects and downloaded bytes are bounded too.

Generated model text is untrusted browser input. Escaping a tooltip explanation stops
characters such as `<` and `>` from becoming executable HTML. Restricting browser
origins is separate from authenticating clients; the current extension-origin rule
is not a public authentication system or an allowlist of one installed extension.

**Learn:** URL parsing, DNS, private/public IP ranges, TCP/TLS, certificate hostname
verification, redirects, SSRF, output escaping, XSS, CORS and authentication.

**Exercise:** explain why "the string contains hani.co.kr" is not safe hostname
validation, and why connecting to an IP should not disable hostname verification.

## 6. Caching and consistency

Relevant code: [server cache](../scripts/services/cache_service.py),
[configuration fingerprint](../scripts/llm/config.py), [browser cache](../chrome-ex/background.js).

The Redis key includes a URL hash, sorted providers, analysis mode and a fingerprint
of model IDs, relevant generation settings, endpoint configuration and prompt text.
Different model settings should not return a result produced by an older configuration.
This fingerprint contains no API keys; SHA-256 here creates an identity, not encryption.
The browser fetches a configuration ID before consulting its cache and skips that
cache if it cannot obtain the ID. Configuration changes may invalidate more browser
entries than strictly necessary because its ID covers all providers.

Current gaps matter: the URL is hashed, not the article contents; an edited article at
the same URL can reuse an older analysis until expiry. The server avoids caching partial
consensus failures, but the browser currently caches a successful response even if some
providers failed. Model aliases can change behavior without changing their names.
Redis failure degrades to uncached work; automatic reconnection is limited.

**Learn:** cache keys, deterministic serialization, TTL, invalidation, stale data,
cache-aside patterns, cache stampedes and the difference between availability and freshness.

**Exercise:** design a content-hash key and decide whether simultaneous identical
requests should share one in-flight model call. State the freshness/cost tradeoff.

## 7. Database transactions and shared state

Relevant code: [database sessions](../scripts/database/init_db.py),
[repository](../scripts/database/repository.py), [fixtures](../tests/conftest.py).

SQLite stores request/analysis records and flags. The session context commits on success,
rolls back on exceptions and closes the session. The repository groups database operations.
Threaded HTTP handling increases concurrent access, while SQLite still limits simultaneous
writing. One server process keeps local operation simple; it does not eliminate locking
or make all shared Python state automatically safe.

Earlier tests shared database and global state. Isolated temporary databases and controlled
configuration improve reproducibility. In production code, analytics logging failures can
be logged without necessarily turning a successful analysis into an HTTP failure.

**Learn:** transactions, commit/rollback, connection/session lifetime, isolation, locks,
shared mutable state and the distinction between essential data and optional telemetry.

**Exercise:** decide what must remain correct if writing an analytics row fails after a
paid model request succeeds. Explain how you would avoid charging twice on a client retry.

## 8. Observability, failure semantics and operation

Relevant code: [HTTP metrics](../scripts/observability/http_metrics.py),
[logging](../scripts/observability/logging_config.py), [health service](../scripts/services/health_service.py).

Logs explain individual events; correlation IDs connect events from one request.
Counters measure totals and histograms summarize latency distributions. Route-template
labels keep metric cardinality bounded: a separate series for every arbitrary URL would
consume unbounded memory. Older timing summaries retain only the latest 1,024 samples.
Those sliding summaries and cumulative Prometheus histograms answer different questions.

Liveness asks whether the process responds. Readiness checks local prerequisites, including
the database and at least one initialized provider; it does not send a paid upstream probe.
A provider marked "up" may still have an invalid key or unavailable model. HTTP success can
also contain partial provider failure, so HTTP error rate alone misses some degraded analyses.

SIGTERM and a graceful stop period allow in-flight work to finish. A provider timeout, the
Gunicorn configuration and the extension's 90-second wait are distinct mechanisms; they do
not establish a universal request deadline or guaranteed cancellation of paid work.

**Learn:** structured logs, correlation, counters, histograms, p95, label cardinality,
liveness/readiness, graceful shutdown, service objectives and error budgets.

**Exercise:** choose signals that distinguish slow crawling, slow model calls, a missing
cache and SQLite contention. Current per-provider latency/cost records are not all direct
measurements: consensus analytics divide an overall duration, and token costs are estimated.
Do not present those values as actual provider timing or billing.

## 9. Regression testing and controlled experiments

Relevant code: [regressions](../tests/regression), [JavaScript checks](../tests/extension.test.cjs),
[historical records](../benchmarks/records), [CI workflow](../.github/workflows/checks.yml).

A regression check should fail for a particular defect, then pass after its repair.
Mocks isolate external services and make fault cases repeatable. They cannot establish
current vendor compatibility or real-browser behavior. Integration checks exercise real
routing and middleware with controlled dependencies; live checks answer a different question.

The stored HTTP experiment compares one and eight HTTP threads on the same repaired code,
with fake upstream delays, a local client, repeated trials and recorded source hashes.
It demonstrates I/O overlap under those conditions. It does not measure real model quality,
public-network capacity or the performance of this later model-refresh revision.
Short closed-loop runs also provide limited tail-latency and saturation information.

The previous 158 Python and 2 JavaScript passes are historical. The model refresh and
renamed test directory need a fresh verification pass. No application tests or live calls
were run during this documentation task. Existing raw records must not be silently updated
to look like results for code they never exercised.

**Learn:** unit/integration/end-to-end boundaries, fixtures, mocks, regression design,
repeatability, controlled variables, sample size and the difference between hypotheses and results.

**Exercise:** define a representative article set before tuning models. Record failed calls
as well as successes, use actual API usage for cost, and blind-review explanation quality.
The old offline runner still needs its obsolete interface and output assumptions migrated.

## 10. Git and reproducible development

The maintenance branch starts from `d5c7c33`. Earlier project history is preserved.
The initial local commits separate backend work, extension changes, runtime/check tooling,
and documentation. A commit describes a change; it does not certify that the change passed
all checks. Small future changes should carry their own verification record and limitations.

Inspect the work locally:

```sh
git log --reverse --oneline d5c7c33..HEAD
git diff --stat d5c7c33..HEAD
git show 0dc2a22 --stat
```

**Learn:** working tree versus staging area, commits, branches, diffs, reverting, and
local versus remote refs. Creating commits does not push them to GitHub.

## Suggested learning order

1. Trace one single-provider request from browser to response.
2. Explain the adapter contract and repair one deliberately mismatched mock locally.
3. Work through consensus voting and failure cases on paper.
4. Explain the URL fetcher's DNS/TLS steps and the two cache layers.
5. Study transactions, concurrent requests and graceful shutdown together.
6. Reproduce checks when ready, then design the live model evaluation.

You should be able to explain why each change was made, what failure it prevents,
which observation supports it, and what it still cannot guarantee. That is more
useful than memorizing the libraries or treating a passing count as proof of correctness.
