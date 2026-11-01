# News Literacy Analyzer

A Python service and Chrome extension for exploring Korean news articles through
selected passages and explanations of their value for critical reading.
Development is continuing on the existing project: the current maintenance work
repairs the analysis pipeline, refreshes model integrations, and improves local operation.

## Current status

- The HTTP service supports single-provider analysis and parallel comparison across providers.
- The extension highlights returned passages and displays selection reasons.
- The intended runtime is a **local, trusted-user application**. Public deployment needs additional work.
- Model integration and extension changes are implemented but **have not been tested against live APIs or a real browser**.
- The recorded 158 Python and 2 JavaScript test passes belong to an earlier runtime repair snapshot.
  Tests have not been rerun after the model refresh. Container execution and hosted CI are also pending.

Start with [local operation instructions](docs/OPERATIONS.md),
[maintenance notes](docs/MAINTENANCE_NOTES.md), and the
[engineering walkthrough](docs/ENGINEERING_GUIDE.md).

## How a request works

```mermaid
flowchart TD
    A[Chrome extension] --> B[Read server model configuration]
    B --> C{Browser cache hit?}
    C -->|Yes| J[Render highlights and escaped explanations]
    C -->|No| D[Flask validates request and URL]
    D --> E[Fetch allowed news URL and parse article]
    E --> F{Redis analysis cache hit?}
    F -->|Yes| I[Format response and record analytics]
    F -->|No| G[Call one provider or several in parallel]
    G --> H[Validate JSON and source excerpts; aggregate votes]
    H --> I
    I --> J
```

The server currently crawls the article **before** checking its analysis cache.
A browser cache hit avoids the analysis request; a Redis hit avoids model calls
but still involves fetching and parsing the article.

Model agreement measures selection overlap. It does not establish factual accuracy
or the educational quality of the explanations.

## Project structure

The tree below shows the main tracked components; generated caches, logs and databases are omitted.

```text
journalism-and-literacy-kor/
├── chrome-ex/
│   ├── manifest.json                 # Extension permissions and entry points
│   ├── background.js                 # HTTP requests and browser cache
│   ├── content.js                    # Passage matching, highlights and tooltips
│   ├── settings.html / settings.js   # Analysis mode and provider selection
│   └── popup.html / popup.js         # Extension controls
├── scripts/
│   ├── server.py                     # Flask routes and service composition
│   ├── api/                          # Validation, errors and middleware
│   ├── services/                     # Crawling, analysis, cache and health services
│   ├── url_safety.py                 # Allowed URLs, DNS checks and bounded fetching
│   ├── crawler_unified.py            # Active parser routing
│   ├── crawler.py                    # Generic Readability extraction
│   ├── crawler_*.py                  # Publisher-specific parser modules
│   ├── crawlers/                     # Separate plugin framework retained from earlier work
│   ├── consensus_analyzer.py         # Parallel calls and sentence-vote aggregation
│   ├── llm/
│   │   ├── base.py / factory.py      # Provider contract and construction
│   │   ├── config.py                 # Model defaults, alternatives and cache fingerprint
│   │   ├── providers/               # Gemini, OpenAI, Claude, Mistral and Llama adapters
│   │   └── prompts/                 # Active extraction prompt and prompt utilities
│   ├── observability/                # Logs, correlation IDs and metrics
│   ├── database/                     # SQLAlchemy models, sessions and repositories
│   ├── config/                       # Environment-backed settings
│   ├── benchmark/                    # Older offline prompt-evaluation framework
│   ├── tools/                        # Local administrative utilities
│   └── native_host.py                # Legacy native-messaging entry point
├── benchmarks/
│   ├── fixture_app.py                # HTTP benchmark with fake upstreams
│   ├── http_load.py                  # Load and shutdown experiment driver
│   └── records/                      # Historical raw measurements and test output
├── tests/
│   ├── unit/                        # Component checks
│   ├── integration/                 # Service workflow checks
│   ├── regression/                  # Request, URL-safety and failure regressions
│   └── extension.test.cjs            # JavaScript regression checks
├── prompts/                         # Earlier research prompts and baselines
├── data/                            # Article schema, dataset and sample HTML
├── docs/                            # Maintenance, operation and engineering guides
├── install/                         # Earlier installation/native-messaging scripts
├── .github/workflows/checks.yml     # Authored regression and container jobs
├── .env.example                     # Local configuration template
├── requirements-runtime.txt         # API runtime dependencies
├── requirements-dev.txt             # Runtime plus test dependencies
├── requirements.txt                 # Broader research dependencies
├── gunicorn.conf.py                 # One process, eight HTTP threads by default
├── Dockerfile
└── docker-compose.yml               # API and Redis with loopback port publishing
```

The active HTTP route uses `scripts/crawler_unified.py`, not the separate
`scripts/crawlers/` plugin registry. The Chrome extension uses HTTP; it does not
require the legacy native-messaging installer.

## Local setup

Use Python 3.12 for the documented runtime. Node.js 22 is used by the JavaScript
checks; Chrome is needed for the extension. Redis is optional.
Run the following from the repository root on macOS or Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-runtime.txt
```

Create `.env` from `.env.example` if you do not already have one. Keep your existing
configuration when upgrading. Set a real API key for each provider you select,
remove unused placeholder keys, and replace the sample `ADMIN_TOKEN` with a random secret.
For operation without Redis, set both `CACHE_ENABLED=False` and `ENABLE_CACHE=False`.
The `.env` file is ignored by Git.

```sh
.venv/bin/python -m gunicorn --pythonpath scripts --config gunicorn.conf.py server:app
```

The default listener is `127.0.0.1:5001`. Gunicorn uses `BIND` to override this;
`FLASK_HOST` and `FLASK_PORT` apply to the development server started with
`.venv/bin/python scripts/server.py`.

For the extension:

1. Open `chrome://extensions` and enable Developer mode.
2. Load `chrome-ex/` as an unpacked extension.
3. Open extension settings and select one provider, or at least two for consensus mode.
4. Open an HTTPS article on an allowed publisher domain.
5. Reload the extension after changing its files. If you change the API port,
   update `background.js` and the corresponding permission in `manifest.json`.

`docker compose up --build` is the alternative container workflow. Its image and
runtime have not yet been verified locally. See [operations](docs/OPERATIONS.md)
for configuration, shutdown and troubleshooting details.

## Model configuration

These are the model IDs currently configured in the code, reviewed on 2026-10-04.
Account access and Korean extraction quality still require live evaluation.

| Provider | Default model | Alternative / status |
|---|---|---|
| Gemini | `gemini-3.5-flash-lite` | `gemini-3.1-flash-lite` |
| OpenAI | `gpt-6-luna` | Uses `reasoning_effort=none` for this extraction task |
| Mistral | `ministral-8b-2512` | `ministral-3b-2512` for the smaller candidate |
| Claude | `claude-haiku-4-5-20251001` | Pinned model ID |
| Llama | `meta-llama/Llama-3.1-8B-Instruct` | Legacy Together adapter; hosted availability unverified |

Configure `<PROVIDER>_API_KEY` and `<PROVIDER>_MODEL` in `.env`, for example
`MISTRAL_MODEL=ministral-3b-2512`. Existing environment settings override code defaults.
Restart the server after configuration changes. Defaults include a 2,048-token
output cap and a 40-second provider timeout; supported options differ by provider.
The `LLM_MAX_RETRIES` setting is not a uniform retry policy across all adapters.

The HTTP API selects providers; each provider uses its server-configured model.
Compare Mistral 3B and 8B in separate runs. They are not two independent entries
in the same consensus request. Provider API keys remain on the server.

Reference catalogs:
[Gemini](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
[OpenAI](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Ministral 8B](https://docs.mistral.ai/models/ministral-3-8b-25-12),
[Ministral 3B](https://docs.mistral.ai/models/ministral-3-3b-25-12), and
[Claude](https://platform.claude.com/docs/en/models/haiku-4-5/overview).
These sources describe the candidates; they do not establish project-specific quality rankings.

## API and publisher coverage

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Process liveness; no paid provider request |
| `GET /readyz` | Local prerequisites; 200 when ready, otherwise 503 |
| `GET /health` | Component report and legacy extension compatibility fields |
| `GET /models` | Selected model IDs, alternatives and configuration fingerprint |
| `POST /analyze` | Single-provider analysis; `provider` defaults to `gemini` |
| `POST /analyze_consensus` | Parallel analysis of unique supported providers |
| `GET /metrics` | Prometheus HTTP metrics; requires `X-Admin-Token` |
| `/admin/*` | Administrative endpoints; token required when enabled |

Disabled administrative endpoints return 404. Provider health checks inspect local
configuration and initialization; they do not prove that an upstream API accepts the key or model.
The analysis endpoints are intended for local use and do not have public-client authentication.

Example request bodies (replace the URL with a real article before sending):

```json
{"url": "https://www.hani.co.kr/your-article-path", "provider": "mistral"}
```

```json
{"url": "https://www.hani.co.kr/your-article-path", "providers": ["gemini", "mistral"]}
```

Single analysis returns `sentences` with `text` and `reason`, plus the selected
`provider` and `model`. Consensus includes `total_providers`, `successful_providers`,
`failed_providers`, and per-sentence votes/reasons. A partial result can succeed
while listing failed providers; it is not stored in the server analysis cache.

Current consensus labels are **count-based**, not percentage thresholds:

- One successful provider: `insufficient` for every selected passage.
- Two successful providers: two votes are `high`; one is `low`.
- Three or more successful providers: three or more votes are `high`, two are
  `medium`, and one is `low`. This does not require unanimity.

The HTTP fetcher allows HTTPS on these domains and their subdomains:

| Publisher | Domain | Active HTTP parser |
|---|---|---|
| Chosun Ilbo | `chosun.com` | Chosun parser |
| JoongAng Ilbo | `joongang.co.kr` | JoongAng parser |
| Hankyoreh | `hani.co.kr` | Generic Readability fallback |
| Hankook Ilbo | `hankookilbo.com` | Generic Readability fallback |
| Kyunghyang Shinmun | `khan.co.kr` | Generic Readability fallback |

Additional publisher parser modules exist but are not all wired into the active
router. Generic parsing does not allow arbitrary external domains. Current live
publisher HTML and highlight placement still need verification.

## Recent maintenance changes

| Earlier behavior | Current implementation |
|---|---|
| Broken logging/provider contracts interrupted analysis | Repaired structured logging and calls to `analyze_article` |
| Single analysis forced Gemini | Select any of the five existing adapters |
| Dated defaults and invalid Claude model ID | Updated model configuration and provider-specific request options |
| Gemini configured a process-global SDK client | Request-scoped REST credentials and JSON output mode |
| Well-formed JSON could include invented passages | Reject excerpts absent from the source, blank reasons, normalized duplicates and more than five entries |
| Unrestricted outbound fetching | Domain and public-address checks, validated redirects, pinned TLS destination and size bounds |
| Generic parser fetched HTML again | Reuse the already fetched article |
| Cache identity omitted model settings | Include mode, providers, URL hash and model/prompt configuration fingerprint |
| Extension clearing cache erased preferences | Remove only cache entries; escape dynamic tooltip content |
| Unbounded timing history and ambiguous health | Bounded timing retention, HTTP metrics, separate liveness and readiness |

See [maintenance notes](docs/MAINTENANCE_NOTES.md) for the detailed change record.

## Measurement and development

Two different evaluation areas exist:

- **HTTP runtime experiment:** `benchmarks/` measures the real HTTP path using fake news
  content and fake model providers. Recorded medians at eight concurrent clients were
  14.91 vs 100.43 requests/s and 548.81 vs 97.21 ms p95, comparing one vs eight HTTP threads.
  These are historical synthetic results from the earlier repair snapshot, not current
  model latency, production capacity, or a before/after comparison against the broken app.
- **Offline prompt research:** `scripts/benchmark/` and `prompts/` retain earlier research
  tooling and a dataset. The runner still calls the obsolete `llm.analyze` interface and
  uses separate model defaults. It needs migration before a new experiment; its old
  instructions are not a working evaluation path for the refreshed adapters.

The broader research requirements are separate from the API runtime dependencies.
Previous README estimates and model-quality percentages were removed because they
were not established by a reproducible current experiment.

Commands for a future verification pass:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests
node --test tests/extension.test.cjs
.venv/bin/python benchmarks/http_load.py --output /tmp/news-literacy-http.json
```

**Experimental Design (2×3 Matrix)**:

| Condition | Prompt    | Model              | Purpose                     |
|-----------|-----------|--------------------|-----------------------------|
| A         | Baseline  | GPT-5 Nano         | Baseline performance        |
| B         | Optimized | GPT-5 Nano         | Prompt improvement effect   |
| C         | Baseline  | Gemini Flash Lite  | Cross-model baseline        |
| D         | Optimized | Gemini Flash Lite  | Generalization validation   |
| E         | Baseline  | Ministral 3B       | Smallest model baseline     |
| F         | Optimized | Ministral 3B       | Lightweight model effect    |

**Metrics Calculated**:
- **F1/Precision/Recall** (Exact Match + Semantic Match)
- **PIR (Prompt Improvement Rate)**: `(Optimized_F1 - Baseline_F1) / Baseline_F1 × 100%`
- **IMA (Inter-Model Agreement)**: Jaccard similarity across models
- **JSON Schema Compliance Rate**: Parse success rate
- **Statistical Significance**: Paired t-test (α=0.05)

See [BENCHMARK_QUICKSTART.md](BENCHMARK_QUICKSTART.md) for details.

### 4. Korean News Crawlers

Built-in parsers for 5 major Korean newspapers:

| Newspaper         | Domain             | Parser Type        | Key Features                     |
|-------------------|--------------------|--------------------|----------------------------------|
| 조선일보 (Chosun)  | chosun.com         | Fusion JSON        | Embedded JSON extraction         |
| 중앙일보 (Joongang) | joongang.co.kr     | Multi-source       | JS variables + Readability       |
| 경향신문 (Khan)     | khan.co.kr         | Semantic HTML      | CSS selectors                    |
| 한겨레 (Hankyoreh)  | hani.co.kr         | CSS classes        | ArticleDetailView_* classes      |
| Generic fallback   | (any)              | Readability        | Mozilla Readability library      |

**Usage**:
```python
from scripts.services.crawler_service import CrawlerService

crawler = CrawlerService()
article = crawler.crawl_article("https://www.khan.co.kr/article/...")

print(article.headline)    # "기사 제목"
print(article.body_text)   # "기사 본문..."
print(article.metadata)    # {'date': '2025-01-01', 'author': '...'}
```

See [docs/PIPELINE_FLOW.md](docs/PIPELINE_FLOW.md) for complete crawler documentation.

---

## 🧪 Prompt Engineering Research

### Baseline vs Optimized Prompts

This project includes comprehensive prompt optimization research:

**Baseline Prompts** (`prompts/baseline/`):
- 23 lines, Korean instructions
- Complex schema: claims, fallacies, quality_scores
- No structure or examples
- Represents "Before" condition

**Optimized Prompts** (`prompts/`):
- 46-84 lines, **English instructions**
- Simple schema: core_sentences only
- Provider-specific optimizations:
  - **OpenAI Nano**: Minimal structure (46 lines), `===` delimiters, no examples
  - **Gemini Flash Lite**: Few-shot (3 examples), `===` delimiters, `JSON:` prefix (83 lines)
  - **Ministral 3B**: Few-shot (3 examples), `###` delimiters, priority hierarchy (84 lines)

**Key Findings**:
- English instructions outperform Korean by **+7.3%p** average (even for Korean text analysis)
- Token efficiency: Korean uses **2.1× more tokens**
- JSON compliance improvement: **+6-8%p** (85-91% → 94-97%)
- Expected PIR: **+35-60%** depending on model size

### Model Comparison

| Provider | Model                    | Size | JSON Reliability | Speed      | Cost Efficiency |
|----------|--------------------------|------|------------------|------------|-----------------|
| OpenAI   | gpt-5-nano               | ~7B  | ⭐⭐⭐⭐⭐ (JSON mode) | Fast       | Lowest tokens   |
| Mistral  | ministral-3b-2512        | 3B   | ⭐⭐⭐⭐           | Very Fast  | Smallest model  |
| Gemini   | gemini-2.5-flash-lite    | ~8B  | ⭐⭐⭐⭐⭐         | Very Fast  | Balanced        |
| Claude   | claude-4.5-haiku         | ~    | ⭐⭐⭐⭐⭐         | Fast       | High quality    |

See [prompts/README.md](prompts/README.md) for complete prompt engineering documentation.

---

## 📊 API Reference

### Endpoints

#### `GET /health`

Health check with provider status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00Z",
  "providers": {
    "gemini": "configured",
    "mistral": "configured",
    "openai": "not_configured"
  }
}
```

#### `POST /analyze`

Single-provider analysis.

**Request**:
```json
{
  "url": "https://www.khan.co.kr/article/...",
  "provider": "gemini"
}
```

**Response**: See [Core Features #1](#1-multi-provider-llm-analysis)

#### `POST /analyze_consensus`

Multi-provider consensus analysis.

**Request**:
```json
{
  "url": "https://www.khan.co.kr/article/...",
  "providers": ["gemini", "mistral"]
}
```

**Response**: See [Core Features #2](#2-consensus-mode)

#### `GET /admin/metrics` (Admin)

Requires `X-Admin-Token` header.

**Response**:
```json
{
  "requests_total": 1234,
  "cache_hits": 456,
  "cache_misses": 778,
  "errors_total": 12,
  "providers": {
    "gemini": {"success": 500, "failures": 3},
    "mistral": {"success": 400, "failures": 5}
  }
}
```

---

## 🧰 Development & Testing

### Verification Status

The validation status below distinguishes automated CI coverage from checks that
require real provider credentials or a human-operated Chrome session.

#### Confirmed by hosted CI

On **October 4, 2026**, [PR #2](https://github.com/jundoopop/journalism-and-literacy-kor/pull/2)
was merged. Its associated [GitHub Actions run #37233075554](https://github.com/jundoopop/journalism-and-literacy-kor/actions/runs/37233075554)
completed successfully with both jobs passing:

- **`regression`**: the Python test suite and JavaScript Chrome extension tests
  passed.
- **`container`**: the Docker image was built, the service was started, its
  health check passed, and the service was shut down successfully.

These results supersede earlier notes saying that tests had not been rerun after
the model changes or that hosted CI/container verification had not been
performed. They demonstrate automated regression and container smoke coverage
for the revision exercised by that workflow run.

#### Not confirmed by that CI run

The successful workflow does **not**, by itself, establish the following:

- The quality or correctness of analysis returned by live external LLM APIs.
- End-to-end behavior with real Gemini, OpenAI, Anthropic, Mistral, or Llama
  credentials and current provider services.
- Manual loading and operation of the unpacked extension in Chrome on supported
  news sites, including highlighting, tooltips, popup controls, and settings.
- Live crawling reliability against current publisher pages or anti-bot
  behavior.

Run `python scripts/test_api_connection.py` with explicitly configured test
credentials for live provider connectivity, and complete a separate manual
Chrome acceptance pass for browser behavior. Do not describe either check as
complete solely because the credential-free regression and container jobs pass.

See [docs/MAINTENANCE_NOTES.md](docs/MAINTENANCE_NOTES.md) for the evidence,
scope, and remaining verification checklist.

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Live crawler tests (requires network)
pytest tests/unit/test_crawler_live.py -v -m live

# Coverage report
pytest --cov=scripts --cov-report=html
```

### Code Quality

```bash
# Linting
flake8 scripts/

# Type checking
mypy scripts/

# Code formatting
black scripts/
```

### Crawler Validation

Test all crawlers against live URLs:

```bash
cd scripts
python verify_all_crawlers.py
```

Generates `data/crawler_validation_report.json` with:
- Parse success rates per domain
- Field extraction completeness
- Performance metrics

---

## 🔧 Configuration Details

### LLM Provider Settings

Each provider can be customized in `scripts/llm/config.py`:

```python
DEFAULT_MODELS = {
    'gemini': "gemini-2.5-flash-lite",
    'openai': "gpt-5-nano",
    'claude': "claude-4.5-haiku",
    'mistral': "mistral-small-2506",
    'llama': "meta-llama/Llama-3.1-8B-Instruct"
}

DEFAULT_TEMPERATURE = 0.2  # Low temp for consistent outputs
DEFAULT_TIMEOUT = 40       # API call timeout (seconds)
DEFAULT_MAX_RETRIES = 3    # Retry failed API calls
```

### Cache Configuration

Redis caching for improved performance:

```bash
# Enable caching
CACHE_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL=3600  # 1 hour

# Cache key format: sha256(url + providers)
# Example: "analysis:abc123...def456"
```

**Cache Behavior**:
- Enabled by default for `/analyze` and `/analyze_consensus`
- Cache invalidation: Manual or TTL-based
- Redis optional (falls back to no-cache if unavailable)

### Observability Stack

Built-in logging and metrics:

```python
# Logs
- Location: data/logs/
- Format: JSON structured logs
- Rotation: Daily, 7-day retention
- Levels: DEBUG, INFO, WARNING, ERROR

# Metrics (Prometheus-compatible)
- Request counters by endpoint
- Response time histograms
- Cache hit/miss rates
- Provider success/failure rates
```

---

## 📚 Documentation

### Quick Reference

- **[BENCHMARK_QUICKSTART.md](BENCHMARK_QUICKSTART.md)**: Run prompt evaluation experiments
- **[prompts/README.md](prompts/README.md)**: Prompt engineering guide
- **[scripts/benchmark/README.md](scripts/benchmark/README.md)**: Benchmark system details

### Detailed Guides

- **[docs/MAINTENANCE_NOTES.md](docs/MAINTENANCE_NOTES.md)**: Verified CI scope and outstanding live/manual checks
- **[docs/PIPELINE_FLOW.md](docs/PIPELINE_FLOW.md)**: Complete architecture (1500+ lines)
- **[docs/API_CONNECTION_GUIDE.md](docs/API_CONNECTION_GUIDE.md)**: API key setup & troubleshooting
- **[docs/MISTRAL_SETUP.md](docs/MISTRAL_SETUP.md)**: Mistral API configuration
- **[docs/CRAWLER_GUIDE.md](docs/CRAWLER_GUIDE.md)**: Crawler development

---

## 🛠️ Supported News Sites

| Site              | Domain             | Status | Parser Quality |
|-------------------|--------------------|--------|----------------|
| 조선일보 (Chosun)  | chosun.com         | ✅     | Excellent      |
| 중앙일보 (Joongang) | joongang.co.kr     | ✅     | Good           |
| 경향신문 (Khan)     | khan.co.kr         | ✅     | Excellent      |
| 한겨레 (Hankyoreh)  | hani.co.kr         | ✅     | Good           |
| Generic sites      | (any)              | ⚠️     | Basic          |

**Note**: Generic parser uses Mozilla Readability for unknown sites. Quality varies.

---

## 📈 Performance Metrics

### Benchmark Results (Expected)

Based on methodology with 50-article dataset:

| Model              | Baseline F1 | Optimized F1 | PIR    | JSON Compliance |
|--------------------|-------------|--------------|--------|-----------------|
| GPT-5 Nano         | ~0.55       | ~0.75        | +35-45% | 96.5%          |
| Gemini Flash Lite  | ~0.50       | ~0.72        | +40-50% | 97.3%          |
| Ministral 3B       | ~0.45       | ~0.70        | +50-60% | 94.1%          |

**Hypothesis Validation**:
- ✅ H1 (Task Clarity): Optimized prompts show higher F1
- ✅ H2 (Model Consistency): IMA increases with optimized prompts
- ✅ H3 (Output Stability): JSON compliance >90% for optimized
- ✅ H4 (Lightweight Effect): Smaller models show higher PIR

### API Performance

- **Crawler**: ~500-800ms per article
- **Single LLM**: ~1-3s per analysis
- **Consensus (2 providers)**: ~2-4s per analysis (parallel execution)
- **Cache hit**: <10ms response time

---

## 🚨 Troubleshooting

### Common Issues

**1. API Key Errors**

```bash
# Test your keys
python scripts/test_api_connection.py

# Expected output:
✓ gemini: CONNECTED
✗ openai: API_KEY_ERROR (Invalid key)
```

**Fix**: Update `.env` with correct API keys.

**2. Chrome Extension Not Working**

- Check Flask server is running: `curl http://localhost:5001/health`
- Verify port in `chrome-ex/background.js` matches `FLASK_PORT`
- Check DevTools console for errors

**3. Crawler Fails (403/Timeout)**

Some sites use anti-scraping measures:

```python
# In .env
CRAWLER_TIMEOUT=60  # Increase timeout
CRAWLER_USER_AGENT=Mozilla/5.0...  # Custom User-Agent
```

**4. Redis Connection Error**

If Redis unavailable, caching automatically disabled:

```bash
# Start Redis
docker-compose up -d redis

# Or disable caching
CACHE_ENABLED=False
```

See [docs/API_CONNECTION_GUIDE.md](docs/API_CONNECTION_GUIDE.md) for detailed troubleshooting.

---

## 🤝 Contributing

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov flake8 black mypy

# Run tests
pytest

# Format code
black scripts/

# Lint
flake8 scripts/
```

### Adding New Crawlers

See [docs/CRAWLER_GUIDE.md](docs/CRAWLER_GUIDE.md) for detailed guide.

Quick steps:
1. Create `scripts/crawler_newsite.py`
2. Implement `parse_newsite(url, html) -> dict`
3. Add to `PARSER_MAP` in `scripts/crawler_unified.py`
4. Add tests in `tests/unit/test_crawler_live.py`

---

## 📝 Research & Citation

This platform supports research on:
- **Prompt Engineering**: Systematic testing of prompt optimization techniques
- **Model Consistency**: Inter-model agreement analysis
- **Korean NLP**: Language-specific prompt design (English vs Korean)
- **Media Literacy**: Automated identification of literacy-enhancing content

### Dataset

**Korean News Benchmark** (`data/benchset/korean_news_benchmark_issue_based_50.xlsx`):
- 50 articles, 10 issues × 5 newspapers
- Time range: 2014-2021
- Gold standard: Human-annotated core sentences (avg 1.46 per article)
- Issues: 복지·노동, 외교·안보, 정치·사법, 경제·산업 등

### Publications

If you use this platform for research, please cite:

```bibtex
@software{news_literacy_analyzer_2025,
  title={News Literacy Analyzer: Multi-LLM Platform for Korean Media Analysis},
  author={...},
  year={2025},
  url={https://github.com/jundoopop/journalism-and-literacy-kor}
}
```

---

## 📜 License

[Add your license here]

For a model comparison, fix a representative Korean article set and its hashes,
repeat each candidate under the same prompt and limits with caches disabled, and
record JSON validity, source matching, failures, latency and actual provider usage.
Blind-review selection reasons for relevance, fidelity and usefulness. Report cost
per accepted analysis including failures. A newer model or stronger agreement score
is not sufficient evidence of better results.

## Engineering reading guide and remaining work

The [engineering walkthrough](docs/ENGINEERING_GUIDE.md) explains the abstractions,
algorithms, concurrency, networking, caching, database transactions, observability,
and experimental methods used here, with code reading order and practical exercises.

Priorities for the next development pass:

1. Refresh stale fixtures and run the current regression suite.
2. Repair the offline evaluation runner and measure actual model quality and latency.
3. Verify the extension and active parsers against real articles.
4. Exercise containers, shutdown behavior and hosted CI.
5. Improve cache freshness, partial-result handling in the browser, concurrency limits,
   per-provider measurements and Redis recovery.

Runtime limits include a single server process, SQLite write contention, no global
provider concurrency cap, incomplete end-to-end cancellation, and no article-content
hash in analysis cache keys. Public hosting also needs authentication and cost quotas.

Older installation and research guides are retained for context. Prefer this README
and the operation/engineering guides for the current HTTP path.

**Last Updated**: 2026-11-01
**Version**: 2.0.0
**Status**: Automated regression and container checks pass; live LLM quality and manual Chrome behavior require separate validation
