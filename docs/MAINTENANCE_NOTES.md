# Maintenance Notes

## Validation record

This document records what has and has not been verified. It replaces the
earlier maintenance note that hosted workflows had not been run.

### October 4, 2026: PR #2 and hosted CI

- Merged change: [PR #2](https://github.com/jundoopop/journalism-and-literacy-kor/pull/2)
- Hosted workflow: [GitHub Actions run #37233075554](https://github.com/jundoopop/journalism-and-literacy-kor/actions/runs/37233075554)
- Workflow conclusion: **success**

The workflow reported both jobs as successful:

| Job | Automated evidence established by the run |
|---|---|
| `regression` | Python tests passed and JavaScript Chrome extension tests passed. |
| `container` | Docker image build, service startup, health check, and service shutdown all passed. |

Accordingly, statements that the model-related changes had not been followed by
a test rerun, or that hosted CI and container verification had not occurred, are
historical and must not be presented as the current verification state for the
revision exercised by this workflow.

## Interpretation boundaries

A green hosted workflow confirms only the automated steps that the workflow ran.
It does not imply that tests requiring external credentials, mutable third-party
services, or human browser interaction were performed.

### Verified automatically

- Python regression behavior covered by the workflow's Python test command.
- JavaScript extension behavior covered by the workflow's extension test
  command.
- Ability to build the tested Docker image.
- Ability to start the tested service, pass the configured health check, and
  shut it down in the workflow environment.

### Still requires separate verification

- **Live LLM API connectivity:** run provider connection checks using dedicated,
  authorized test credentials.
- **Live analysis quality:** evaluate real provider responses against the
  benchmark and record model IDs, prompt versions, dataset version, date, and
  metrics. A successful mock or contract test is not a quality evaluation.
- **Manual Chrome acceptance:** load `chrome-ex/` as an unpacked extension and
  verify supported-site detection, automatic and manual highlighting, tooltip
  content, popup controls, provider settings, cache/re-analysis behavior, and
  backend-disconnected error states.
- **Live publisher crawling:** verify representative current URLs because page
  structure and anti-automation behavior can change independently of this
  repository.

## Required wording for future status updates

Use scoped statements:

- Good: “Python and JavaScript regression tests passed in GitHub Actions run
  #37233075554.”
- Good: “The container smoke test built, started, passed health checking, and
  stopped successfully in run #37233075554.”
- Good: “Live Gemini analysis was manually checked on YYYY-MM-DD using model X.”
- Avoid: “Everything is fully tested” when only CI regression jobs ran.
- Avoid: “The extension works in Chrome” unless a manual or browser-automation
  acceptance run was completed and recorded.

## Verification checklist for a release

### Automated

- [x] Python regression tests — run #37233075554 (2026-10-04)
- [x] JavaScript extension tests — run #37233075554 (2026-10-04)
- [x] Docker image build — run #37233075554 (2026-10-04)
- [x] Container start/health/stop smoke test — run #37233075554 (2026-10-04)

### External/manual

- [ ] Live provider connectivity with authorized test keys
- [ ] External LLM quality evaluation against the benchmark
- [ ] Manual Chrome extension acceptance on supported news sites
- [ ] Representative live crawler checks

When one of the unchecked items is completed, add the date, environment, exact
command or procedure, model/browser version, result, and a link to retained
evidence. Do not convert a checkbox based on inference from a different test.
# Analysis pipeline maintenance notes

Date: 2026-10-04. Repository: journalism-and-literacy-kor.
Baseline revision: d5c7c33c15bb652d71f43a825832d57e646c183a.

This maintenance pass continues the existing Korean news-literacy project. It
repairs the article analysis path, refreshes lightweight model integrations,
and improves local operation without changing the project's purpose.

## Scope and validation status

The recorded regression and HTTP results below describe the earlier runtime
repair snapshot. Lightweight model and provider-selection changes were made
afterward and have not been tested. The records are historical measurements,
not verification of the current checkout. Live API quality, browser behavior,
and container execution remain unverified.

## Method used

1. Read the real code paths and form a concrete failure hypothesis.
2. Add a test that reproduces the failure without live news sites or paid API calls.
3. Fix the smallest relevant contract, retaining the product's news-highlighting purpose.
4. Exercise routes and failure cases, then repair stale tests against the actual public interfaces.
5. Run a controlled HTTP experiment, record raw samples and limitations, and document reproduction.

The first five Python regression cases and two JavaScript cases all failed before the
fixes. The same seven passed at that snapshot. The recorded suite passed **158 Python tests and 2 Node tests**,
including **47 focused Python reliability cases**. Existing tests were retained and updated
where they called nonexistent repository/metrics methods or used obsolete model fields;
tests now use isolated SQLite databases and the current session contracts.

Raw records: [Python before](../benchmarks/records/python-before.txt),
[extension before](../benchmarks/records/extension-before.txt),
[Python after](../benchmarks/records/python-after.txt),
[extension after](../benchmarks/records/extension-after.txt).
The initial existing suite also could not collect because lxml's HTML cleaner dependency
was missing; that runtime dependency was added. Passing tests are not proof of live model quality.

## Concrete before/after comparison

| Problem / trigger | Before | Implemented after | Verification |
|---|---|---|---|
| Normal API request with INFO logging | Structured kwargs were passed to a standard Logger, raising TypeError in request middleware | LoggerAdapter preserves structured fields and standard logging kwargs; UTC timestamps fixed | Real Flask routing and logging regression tests |
| Crawler import | config.ensure_dir no longer existed after configuration refactoring | Restored the small output-directory helper | Crawler import and parse regression |
| Consensus model call | Called llm.analyze, which providers do not implement | Calls analyze_article and reads the typed sentences result | Provider-contract regression and API integration case |
| Local server defaults | Bound to 0.0.0.0 with debug enabled | Loopback binding, debug off; one Gunicorn worker/eight threads for serving | Settings regression; actual local HTTP experiment |
| Arbitrary crawl URL or redirected internal address | Unrestricted outbound request and automatic redirect | News-domain HTTPS validation, public DNS checks, pinned address, TLS hostname verification, manual redirects, 4 MiB response limit | Invalid URL, private DNS, redirect, size and pinned-TLS unit tests |
| Malformed JSON/providers | Inconsistent exceptions and unnecessary outbound work | JSON object, URL, unique provider list and 16 KiB body validation before outbound work | API cases for 400/405/413/415 and no crawler calls |
| Untrusted browser origin | Permissive CORS on the whole application | Reject unapproved Origin before analysis; allow extension preflight | Browser-origin and preflight tests |
| Admin API set disabled | Disabled flag bypassed authentication and still executed endpoint | Returns 404; enabled endpoints still require admin token | Handler not invoked; metrics auth tests |
| One model unavailable | Missing initialization failures; one survivor labeled high agreement | Retain requested denominator and failed provider names; one survivor shown as insufficient | Initialization-failure, runtime-failure and consensus regressions |
| Reusing failed/ambiguous cache data | Partial failures could persist; single/consensus shared a key shape | Do not cache partial failures; use separate mode namespaces and full SHA-256 URL hash | Cache namespace and partial-failure regression tests |
| Generic article parsing | Downloaded the same page a second time | Parse the HTML already fetched | Test rejects all network calls during parsing |
| Model text containing HTML | Model reason interpolated into innerHTML without escaping | Escape every dynamic reason/provider/score; whitelist styles and labels | Both tooltip modes tested with HTML injection payload |
| Extension cache clear | Cleared all local storage including preferences | Remove only cache-prefixed keys | Saved settings remain after clearing cache |
| Dependencies unavailable | A combined health report did not separate process liveness | /healthz reports process; /readyz returns 503 for unavailable local prerequisites | Dependency-outage API test |
| Growing observability memory | Kept every latency sample; raw paths expanded HTTP labels | Timing window capped at 1,024; bounded HTTP route/method labels; Prometheus counter/histogram endpoint | Sample-retention and unmatched-route metric tests |
| Process shutdown | No repeatable in-flight shutdown evidence | Gunicorn stop grace configured and actual SIGTERM experiment automated | Request completed with HTTP 200; master exited 0 |
| Regression automation | Existing tests had obsolete APIs and shared DB/cwd state | Isolated fixtures; full passing local suite; CI and container smoke workflow authored | 158 Python + 2 Node pass locally; hosted workflow not run |

Implementation entry points: [server](../scripts/server.py), [URL safety](../scripts/url_safety.py),
[consensus](../scripts/consensus_analyzer.py), [HTTP metrics](../scripts/observability/http_metrics.py),
[focused tests](../tests/regression), [extension tests](../tests/extension.test.cjs).

## Measured HTTP comparison

**This compares the repaired application with one HTTP thread against the same application
with eight threads. It does not compare the original broken app against the repaired app.**

The actual HTTP request passes through validation, generic parsing, parallel consensus and
SQLite analytics. News HTML is a fixture and two fake model providers each wait 50 ms.
Redis is disabled. Client and server run on the same macOS machine.

At 8 concurrent clients, medians across three repeats were:

| Measurement | One HTTP thread | Eight HTTP threads |
|---|---:|---:|
| Throughput | 14.91 requests/s | 100.43 requests/s |
| p95 latency | 548.81 ms | 97.21 ms |
| Errors in those runs | 0 / 120 | 0 / 120 |

The measured throughput ratio is 6.73x and p95 reduction is
82.3%. These are **synthetic I/O experiment results**, not live LLM throughput,
production capacity, or a latency guarantee. Across the full 12-cell experiment, all 480
measured requests returned the expected successful response. Warmups were excluded.

| HTTP threads | Clients | Repeat | Requests | Requests/s | p95 ms | Errors |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 40 | 14.80 | 80.62 | 0 |
| 1 | 1 | 2 | 40 | 14.92 | 67.56 | 0 |
| 1 | 1 | 3 | 40 | 14.96 | 67.58 | 0 |
| 1 | 8 | 1 | 40 | 14.99 | 536.59 | 0 |
| 1 | 8 | 2 | 40 | 14.91 | 548.81 | 0 |
| 1 | 8 | 3 | 40 | 14.90 | 568.06 | 0 |
| 8 | 1 | 1 | 40 | 14.81 | 68.60 | 0 |
| 8 | 1 | 2 | 40 | 14.88 | 67.97 | 0 |
| 8 | 1 | 3 | 40 | 14.98 | 67.33 | 0 |
| 8 | 8 | 1 | 40 | 110.35 | 92.45 | 0 |
| 8 | 8 | 2 | 40 | 96.33 | 120.60 | 0 |
| 8 | 8 | 3 | 40 | 100.43 | 97.21 | 0 |

A separate in-flight shutdown trial used a one-second provider delay. SIGTERM was sent only
after the provider began work. The request returned 200 and the process exited 0.
This verifies that scenario, not every possible timeout or forced termination.

[Raw samples, source hashes and environment](../benchmarks/records/local-http.json) ·
[Installed Python dependencies](../benchmarks/records/python-environment.txt) ·
[Reproduction and operational steps](OPERATIONS.md).

## Follow-up work

- Run the regression suite against the refreshed model integrations and update stale fixtures.
- Evaluate the lightweight model candidates on a fixed Korean article set, recording
  output validity, selection quality, provider latency and actual token usage.
- Exercise the extension with each supported publisher and check highlight placement.
- Run the container and shutdown checks on Linux and inspect hosted CI results.
- Measure provider timeouts, Redis outage/recovery and load beyond eight clients.
- Document the scaling limits of the shared SQLite database and single-process server.

See the README for current model configuration and the comparison protocol.
