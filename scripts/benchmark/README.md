# Benchmark Evaluation System

Comprehensive evaluation framework for testing optimized prompts against baseline prompts across three lightweight LLM models.

## Overview

This system implements the experimental design described in Section IV of the research methodology:
- **6 conditions** (2 prompts × 3 models)
- **50 articles** from Korean news benchmark dataset
- **300 total API calls**
- **Metrics**: Exact Match, Semantic Match, F1/Precision/Recall, PIR, IMA

## Architecture

```
scripts/benchmark/
├── __init__.py
├── data_loader.py          # Load Excel, fetch articles from URLs
├── metrics.py              # F1/Precision/Recall calculation
├── experiment_runner.py    # Orchestrate 6 conditions × 50 articles
├── results_analyzer.py     # PIR, IMA, statistical tests
├── cli.py                  # Command-line interface
└── README.md               # This file
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Required packages:
# - sentence-transformers==2.2.2  (Korean embeddings)
# - scipy==1.11.4                  (statistical tests)
# - openpyxl==3.1.2                (Excel reading)
```

## Quick Start

### 1. Prepare Dataset

Fetch all 50 articles from URLs and cache them:

```bash
python -m scripts.benchmark.cli prepare
```

**Output**: `data/benchset/preprocessed_articles.json`

### 2. Run Full Experiment

Execute all 6 conditions (300 API calls, ~$0.80, ~60 min):

```bash
python -m scripts.benchmark.cli run --yes
```

**Output**: `data/benchset/experiments/exp_YYYYMMDD_HHMMSS_results.json`

### 3. Analyze Results

```bash
python -m scripts.benchmark.cli analyze --experiment-id exp_20250101_120000
```

### 4. Generate Report

```bash
python -m scripts.benchmark.cli report --experiment-id exp_20250101_120000 --format markdown
```

**Output**: `data/benchset/experiments/exp_20250101_120000_report.md`

## Experimental Design

### 2×3 Matrix

| Condition | Prompt | Model | Purpose |
|-----------|--------|-------|---------|
| **A** | Baseline | GPT-5 Nano | Baseline performance |
| **B** | Optimized | GPT-5 Nano | Prompt improvement effect |
| **C** | Baseline | Gemini Flash Lite | Cross-model baseline |
| **D** | Optimized | Gemini Flash Lite | Generalization validation |
| **E** | Baseline | Ministral 3B | Smallest model baseline |
| **F** | Optimized | Ministral 3B | Lightweight model effect |

### Prompt Configurations

**Baseline Prompts** (`prompts/baseline/`):
- 23 lines, Korean instructions
- Complex schema: claims, fallacies, quality_scores
- Represents "Before" condition

**Optimized Prompts** (`prompts/`):
- 46-84 lines, English instructions
- Simple schema: core_sentences only
- Provider-specific optimizations:
  - OpenAI Nano: Minimal structure (46 lines)
  - Gemini Flash Lite: Few-shot + JSON prefix (83 lines)
  - Ministral 3B: ### delimiters + priorities (84 lines)

## Evaluation Metrics

### Core Metrics (Section 2.2-2.3)

**Exact Match**:
- Returns 1.0 if normalized strings identical
- Normalization: whitespace, quotes, numbers, punctuation

**Semantic Match**:
- Uses Ko-SBERT embeddings (`jhgan/ko-sbert-multitask`)
- Thresholds:
  - ≥0.85: Perfect match (1.0)
  - ≥0.70: Partial match (0.5)
  - <0.70: No match (0.0)

**F1 Score**:
```
Precision = Σscore(predicted) / |predicted|
Recall = Σscore(predicted) / |gold|
F1 = 2 × P × R / (P + R)
```

### Analysis Metrics

**PIR (Prompt Improvement Rate)**:
```
PIR = (Optimized_F1 - Baseline_F1) / Baseline_F1 × 100%
```

**IMA (Inter-Model Agreement)**:
- Jaccard similarity of sentence sets across models
- Higher IMA = more constrained task definition

**Statistical Significance**:
- Paired t-test (α=0.05)
- Tests null hypothesis: no F1 difference

## CLI Commands

### Full Command Reference

```bash
# Prepare dataset
python -m scripts.benchmark.cli prepare [--no-cache]

# Run experiments
python -m scripts.benchmark.cli run [--condition A|B|C|D|E|F] [--yes] [--no-cache]

# Analyze results
python -m scripts.benchmark.cli analyze --experiment-id <id>

# Generate report
python -m scripts.benchmark.cli report --experiment-id <id> [--format markdown|json]
```

### Example Workflows

**Run single condition** (50 API calls, ~$0.13, ~10 min):
```bash
python -m scripts.benchmark.cli run --condition A
```

**Run without cache** (force re-fetch articles):
```bash
python -m scripts.benchmark.cli run --no-cache --yes
```

**Generate both reports**:
```bash
python -m scripts.benchmark.cli report --experiment-id exp_20250101_120000 --format markdown
python -m scripts.benchmark.cli report --experiment-id exp_20250101_120000 --format json
```

## Output Files

### Results JSON Structure

```json
{
  "experiment_id": "exp_20250101_120000",
  "timestamp": "2025-01-01T12:00:00",
  "config": {...},
  "conditions": [
    {
      "condition_id": "A",
      "prompt_type": "baseline",
      "provider": "openai",
      "model": "gpt-5-nano",
      "articles": [
        {
          "article_id": "A001",
          "predicted_sentences": ["문장1", "문장2"],
          "gold_sentences": ["문장1", "문장3"],
          "exact_metrics": {"precision": 0.5, "recall": 0.5, "f1": 0.5},
          "semantic_metrics": {"precision": 0.75, "recall": 0.75, "f1": 0.75},
          "duration_ms": 1234,
          "tokens_used": 456
        }
      ],
      "aggregate_exact": {"f1": 0.62, "precision": 0.65, "recall": 0.59},
      "aggregate_semantic": {"f1": 0.71, "precision": 0.73, "recall": 0.69},
      "json_compliance_rate": 0.96
    }
  ]
}
```

### Markdown Report Includes

- **Table 10**: Model performance comparison
- **PIR calculations**: Per-model improvement rates
- **IMA analysis**: Inter-model agreement
- **Hypothesis testing**: H1-H4 results with statistical evidence
- **Detailed condition results**: Full metrics table

## Cost & Time Estimates

### API Costs (estimated)

- GPT-5 Nano: 100 calls × ~2K tokens × $0.15/1M = **$0.30**
- Gemini Flash Lite: 100 calls × ~2K tokens × $0.10/1M = **$0.20**
- Ministral 3B: 100 calls × ~2K tokens × $0.15/1M = **$0.30**
- **Total**: **~$0.80** for full experiment

### Time Estimates

- Sequential: ~60 minutes (6 conditions × 10 min)
- With rate limiting (5 req/sec): ~10 minutes per condition
- Data preparation: ~5 minutes (one-time, cached)

## Hypothesis Testing

The system validates four hypotheses from the methodology:

**H1 (Task Clarity)**: Optimized prompts show higher F1
- ✓ Validated if PIR > 0% for all models

**H2 (Model Consistency)**: IMA increases after optimization
- ✓ Validated if IMA_optimized > IMA_baseline

**H3 (Output Stability)**: JSON compliance improves
- ✓ Validated if compliance >90% for optimized prompts

**H4 (Lightweight Effect)**: Smaller models show higher PIR
- ✓ Validated if PIR correlates negatively with model size

## Troubleshooting

### Common Issues

**1. Article fetch failures**
```
Error: Failed to fetch article from URL
```
- Some articles may be paywalled or deleted
- System gracefully skips and reports success rate
- Acceptable threshold: >90% success rate

**2. API rate limits**
```
Error: Rate limit exceeded
```
- Reduce `rate_limit_delay` in ExperimentConfig
- Current default: 0.2s (5 req/sec)

**3. JSON parsing errors**
```
Error: JSON parse error
```
- Expected for baseline prompts (less strict)
- Counted in `json_compliance_rate` metric
- Review `raw_response` field in results

**4. sentence-transformers download**
```
Downloading Ko-SBERT model...
```
- First run downloads ~400MB model
- Cached in `~/.cache/torch/sentence_transformers/`
- One-time download per machine

### Debugging

**Enable debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Test individual components**:
```bash
# Test data loader
python scripts/benchmark/data_loader.py

# Test metrics
python scripts/benchmark/metrics.py

# Test analyzer
python scripts/benchmark/results_analyzer.py <results_file.json>
```

## Development

### Adding New Metrics

Edit `scripts/benchmark/metrics.py`:

```python
def my_new_metric(predicted: List[str], gold: List[str]) -> float:
    """Custom metric implementation"""
    # Your logic here
    return score
```

### Adding New Models

Edit `experiment_runner.py`:

```python
config.models['claude'] = 'claude-4.5-haiku'

# Add conditions G, H
conditions_spec.append(
    ('G', 'baseline', 'claude', config.models['claude'])
)
```

### Customizing Prompts

1. Create new prompt file in `prompts/baseline/` or `prompts/`
2. Update `experiment_runner.py::load_prompt()` mapping
3. Run experiment

## References

- **Methodology**: See research proposal Section IV
- **Ko-SBERT**: https://github.com/jhgan00/ko-sentence-transformers
- **OpenAI Guide**: https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide
- **Gemini Guide**: https://ai.google.dev/gemini-api/docs/prompting-strategies
- **Mistral Guide**: https://docs.mistral.ai/capabilities/completion/prompting_capabilities

---

**Version**: 1.0
**Last Updated**: 2025-01-01
**Maintainer**: Research Team
