# Benchmark Evaluation System - Quick Start Guide

## ✅ Implementation Complete

All components of the benchmark evaluation system have been successfully implemented:

### 📁 Files Created

**Benchmark System** (`scripts/benchmark/`):
- ✅ `data_loader.py` - Excel loading & URL fetching (200 lines)
- ✅ `metrics.py` - F1/Precision/Recall calculation (250 lines)
- ✅ `experiment_runner.py` - 6-condition orchestration (350 lines)
- ✅ `results_analyzer.py` - PIR/IMA analysis (300 lines)
- ✅ `cli.py` - Command-line interface (200 lines)
- ✅ `README.md` - System documentation

**Baseline Prompts** (`prompts/baseline/`):
- ✅ `base_prompt_ko_openai.txt` - Before condition (23 lines)
- ✅ `base_prompt_ko_gemini.txt` - Before condition (23 lines)
- ✅ `base_prompt_ko_mistral.txt` - Before condition (23 lines)

**Documentation**:
- ✅ `prompts/README.md` - Consolidated optimization guide (500+ lines)
- ✅ `scripts/benchmark/README.md` - Benchmark system docs

**Dependencies**:
- ✅ Updated `requirements.txt` with sentence-transformers, scipy, openpyxl

---

## 🚀 Running the Experiment

### Step 1: Install Dependencies

```bash
pip install sentence-transformers==2.2.2
pip install scipy==1.11.4
pip install openpyxl==3.1.2
```

### Step 2: Prepare Dataset

Fetch all 50 articles from URLs and cache them:

```bash
python -m scripts.benchmark.cli prepare
```

**Output**: `data/benchset/preprocessed_articles.json`

### Step 3: Test Single Condition (Optional)

Test one condition first (50 API calls, ~$0.13, ~10 min):

```bash
python -m scripts.benchmark.cli run --condition A
```

### Step 4: Run Full Experiment

Execute all 6 conditions (300 API calls, ~$0.80, ~60 min):

```bash
python -m scripts.benchmark.cli run --yes
```

**Output**: `data/benchset/experiments/exp_YYYYMMDD_HHMMSS_results.json`

### Step 5: Analyze Results

```bash
# Replace with your experiment ID
python -m scripts.benchmark.cli analyze --experiment-id exp_20250101_120000
```

### Step 6: Generate Report

```bash
python -m scripts.benchmark.cli report --experiment-id exp_20250101_120000 --format markdown
```

**Output**: `data/benchset/experiments/exp_20250101_120000_report.md`

This report will include:
- **Table 10**: Model performance comparison
- **PIR calculations**: Prompt Improvement Rate for each model
- **IMA analysis**: Inter-Model Agreement
- **Hypothesis testing**: H1-H4 results with statistical evidence

---

## 📊 Experimental Design

### 2×3 Matrix (6 Conditions)

| Condition | Prompt | Model | Purpose |
|-----------|--------|-------|---------|
| **A** | Baseline | GPT-5 Nano | Baseline performance |
| **B** | Optimized | GPT-5 Nano | Prompt improvement effect |
| **C** | Baseline | Gemini Flash Lite | Cross-model baseline |
| **D** | Optimized | Gemini Flash Lite | Generalization validation |
| **E** | Baseline | Ministral 3B | Smallest model baseline |
| **F** | Optimized | Ministral 3B | Lightweight model effect |

### Prompts Compared

**Baseline** (Before):
- 23 lines, Korean instructions
- Complex schema: claims, fallacies, quality_scores
- No structure, no examples
- Location: `prompts/baseline/`

**Optimized** (After):
- 46-84 lines, English instructions
- Simple schema: core_sentences only
- Provider-specific optimizations
- Location: `prompts/`

### Metrics Measured

**Per Article**:
- Exact Match F1/Precision/Recall
- Semantic Match F1/Precision/Recall (Ko-SBERT)
- JSON compliance
- Duration, token usage

**Aggregate**:
- PIR (Prompt Improvement Rate): (After_F1 - Before_F1) / Before_F1 × 100%
- IMA (Inter-Model Agreement): Jaccard similarity across models
- Statistical significance: Paired t-test (α=0.05)

---

## 📋 Expected Results (Hypotheses)

Based on methodology Section 3.8.1:

**H1 (Task Clarity)**: Optimized prompts show higher F1
- ✓ Expected: PIR > 0% for all models

**H2 (Model Consistency)**: IMA increases after optimization
- ✓ Expected: IMA_optimized > IMA_baseline

**H3 (Output Stability)**: JSON compliance improves
- ✓ Expected: >90% compliance for optimized prompts

**H4 (Lightweight Effect)**: Smaller models show higher PIR
- ✓ Expected: PIR correlates negatively with model size
- Ministral 3B > Gemini Flash Lite > OpenAI Nano

### Performance Projections

| Model | Baseline F1 | Optimized F1 | Expected PIR |
|-------|-------------|--------------|--------------|
| OpenAI Nano | ~0.55 | ~0.75 | +35-45% |
| Gemini Flash Lite | ~0.50 | ~0.72 | +40-50% |
| Ministral 3B | ~0.45 | ~0.70 | +50-60% |

**JSON Schema Compliance**:
- Baseline: 85-91%
- Optimized: 94-97%
- Improvement: +6-8%p

---

## 💰 Cost & Time Estimates

### API Costs
- GPT-5 Nano: 100 calls × ~2K tokens × $0.15/1M = **$0.30**
- Gemini Flash Lite: 100 calls × ~2K tokens × $0.10/1M = **$0.20**
- Ministral 3B: 100 calls × ~2K tokens × $0.15/1M = **$0.30**
- **Total**: **~$0.80**

### Time
- Sequential: ~60 minutes (6 conditions × 10 min)
- Data preparation: ~5 minutes (one-time, cached)

---

## 🔍 Troubleshooting

### Article Fetch Failures
If some articles fail to fetch (paywalled/deleted):
- System gracefully skips and reports success rate
- Acceptable threshold: >90% success rate

### API Rate Limits
If rate limits are hit:
- Reduce `rate_limit_delay` in ExperimentConfig
- Current default: 0.2s (5 req/sec)

### JSON Parsing Errors
Expected for baseline prompts (less strict):
- Counted in `json_compliance_rate` metric
- Review `raw_response` field in results

### Model Unavailability
If model names have changed:
- Edit `ExperimentConfig.models` in `experiment_runner.py`
- Update to current model names

---

## 📚 Next Steps After Experiment

1. ✅ Run experiment and collect results
2. Fill Table 3 in methodology with actual data
3. Write Results & Discussion section (Section 3.8)
4. Conduct error analysis (mismatched sentences, failure cases)
5. (Optional) Run ablation study:
   - Remove few-shot examples
   - Test different similarity thresholds
   - Test on additional issues beyond the 10 in benchmark

---

## 📖 Documentation

- **Prompts**: See [prompts/README.md](prompts/README.md)
- **Benchmark System**: See [scripts/benchmark/README.md](scripts/benchmark/README.md)
- **Plan**: See plan file at `C:\Users\a\.claude\plans\nifty-stargazing-origami.md`

---

**Status**: ✅ Ready to run
**Last Updated**: 2025-12-30
**Total Implementation**: ~1,800 lines of code + documentation
