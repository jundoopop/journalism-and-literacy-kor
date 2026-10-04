# Local development and operations

This runtime serves the existing news-literacy extension. It is designed for a
local, trusted user, with one process and eight HTTP threads. It is not a public
multi-tenant service. The benchmark application is separate from production.

## Install and run

Use Python 3.12 and Node 22 for the checked workflow.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
# Fill in actual provider keys and a random ADMIN_TOKEN.
# Remove unused provider placeholder keys. Never commit .env.
.venv/bin/python -m gunicorn --pythonpath scripts --config gunicorn.conf.py server:app
```

Set `CACHE_ENABLED=False` and `ENABLE_CACHE=False` to run without Redis. The runtime
requirements omit the large ML packages used only by offline prompt evaluation;
keep using the original requirements file for that separate workflow.
The project-root .env is loaded before nested settings and provider initialization.
Use JSON for lists, for example `CONSENSUS_PROVIDERS=["gemini","mistral"]`.

The default listener is 127.0.0.1:5001, with debug disabled. Only extension origins
are accepted for browser-originated requests. Requests without Origin are allowed
for local scripts. This is not an authentication mechanism for a public deployment.
The single-provider route uses Gemini; the consensus route accepts the supported
provider list. UI health uses the selected providers.

## Containers

```sh
docker compose up --build
docker compose stop
```

Compose publishes API and Redis ports only on loopback. The API runs as a non-root
user, stores SQLite/logs in its volume, and receives SIGTERM with a 95-second stop
grace period. Gunicorn's 90-second graceful timeout lets in-flight work finish.
One worker avoids pretending that in-memory metrics are aggregated across
processes. If scaling to multiple workers, configure Prometheus multiprocess
collection and re-evaluate SQLite concurrency first.

The Docker engine was not running on the development machine. Container build,
Linux runtime and the GitHub Actions jobs must pass before describing this as a
verified Linux/container deployment. The workflow has been authored, not run remotely.

## Health and observability

- `GET /healthz`: process liveness only, always cheap and independent of providers.
- `GET /readyz`: 200 when local prerequisites are ready, 503 otherwise.
  Provider checks validate configuration/initialization, not upstream connectivity.
- `GET /health`: legacy component report for the extension.
- `GET /metrics` with `X-Admin-Token`: Prometheus request counter and duration
  histogram. Disabled admin API returns 404, missing/wrong credentials return 401.
- JSON logs include UTC timestamps and correlation IDs.
- Legacy timing summaries retain the most recent 1,024 samples per label set.
  Prometheus histograms retain cumulative count/sum/buckets, not request samples.

Metric labels use route templates and an unmatched bucket, not arbitrary URL paths.
The metrics endpoint is excluded from HTTP instrumentation so scraping does not
dominate service traffic statistics. Treat analysis requests separately from
health checks in dashboards.

Suggested queries for a future Prometheus deployment:

```promql
sum(rate(news_http_requests_total{route=~"/analyze.*",status=~"5.."}[5m]))
/
sum(rate(news_http_requests_total{route=~"/analyze.*"}[5m]))
```

```promql
histogram_quantile(0.95,
  sum by (le) (rate(news_http_request_duration_seconds_bucket{route=~"/analyze.*"}[5m]))
)
```

These queries and alert thresholds are proposals. No alert delivery or production
SLO has been exercised. Start with an explicitly scoped objective, e.g. 99% successful
valid analysis requests and p95 below a chosen budget, then set the budget from
real provider latency. Do not choose a production budget from the synthetic fixture.

## Reproduce checks

```sh
.venv/bin/python -m pytest tests
node --test tests/extension.test.cjs
.venv/bin/python benchmarks/http_load.py --output benchmarks/records/local-http.json
```

The benchmark launches Gunicorn itself and cleans up its child processes and
temporary databases. It measures the actual HTTP route, generic parser, parallel
consensus, structured middleware and SQLite writes, with two fake providers each
waiting 50 ms. It runs 40 requests per cell, three repeats, and compares 1 vs 8
HTTP threads at 1 vs 8 concurrent clients. Redis is disabled. Startup and three
warm-up requests are excluded. Each response must contain a successful two-provider
result to count as success. Raw samples, environment details and source hashes
are saved in the JSON report.

This is a closed-loop local experiment: the load generator and server share the
machine, and the next request starts after a previous one completes. It measures
controlled I/O overlap, not saturation, internet performance or production capacity.
Short runs have noisy tail estimates. The baseline uses the same repaired code
with one HTTP thread, not the original broken server.

## Triage

| Symptom | First checks | Recovery |
|---|---|---|
| /healthz fails | Process status, startup logs, port 5001 | Restore dependencies/configuration, restart process |
| /healthz is 200 but /readyz is 503 | Provider configuration and DB health | Correct keys or writable data path; use correlation IDs for analysis failures |
| HTTP 400 | URL domain, HTTPS, request JSON/provider list | Correct input; never retry unchanged invalid input |
| One provider fails | failed_providers and provider logs | Return partial results with insufficient agreement; do not cache partial failures |
| High p95, low CPU | Upstream delay, queueing, cache availability | Compare configured timeouts and active clients; bound retries before increasing concurrency |
| Redis unavailable | Cache health and connection logs | Analysis runs uncached; recovery currently requires process restart |
| Shutdown drops requests | Stop grace period, provider duration | Ensure platform stop grace exceeds Gunicorn graceful timeout |

SDK timeouts are explicit; OpenAI/Claude automatic retries are disabled, and Gemini
uses no SDK retry. These are not a universal end-to-end cancellation guarantee.
Blocking DNS and provider SDK behavior still need live/fault-injection validation.
The extension's 90-second timeout cancels its wait, not server execution.

## Remaining boundaries

Live model names/credentials, real news-site HTML and Chrome interaction were not
validated with external services. Tests mock those dependencies. The Docker image
and hosted CI remain pending. Public hosting would additionally need client
authentication, request/cost quotas, overload handling, secret management, and
dependency vulnerability review. These are future work, not claimed deliverables.
