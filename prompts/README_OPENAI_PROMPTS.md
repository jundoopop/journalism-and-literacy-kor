# OpenAI Prompt Variants

This directory contains two optimized prompts for OpenAI models, automatically selected based on the model being used.

## Prompt Variants

### 1. Enhanced Prompt (GPT-5/GPT-4 Full Models)
**File**: `base_prompt_ko_openai.txt`
**Lines**: 318
**Target Models**: `gpt-5`, `gpt-4-turbo`, `gpt-4`, etc.

**Features**:
- ✅ Full GPT-5 optimization with 8 XML sections
- ✅ 10 comprehensive examples covering all field types
- ✅ Self-reflection prompts for internal rubric creation
- ✅ 10-step systematic analysis procedure
- ✅ Detailed validation checklist (5 categories)
- ✅ Priority hierarchy for conflict resolution
- ✅ Metaprompting for goal alignment
- ✅ Enhanced schema documentation

**Use Cases**:
- High-accuracy analysis requirements
- Production systems with quality focus
- Research and benchmarking
- When token cost is not a primary concern

**Estimated Token Cost**: ~1,500-2,000 prompt tokens per request

---

### 2. Nano-Optimized Prompt (Lightweight Models)
**File**: `base_prompt_ko_openai_nano.txt`
**Lines**: 59
**Target Models**: `gpt-5-nano`, `gpt-4o-mini`, etc.

**Features**:
- ✅ Streamlined XML structure (4 sections)
- ✅ 3 essential examples
- ✅ Condensed 6-step analysis procedure
- ✅ Core rules and constraints
- ✅ Optimized for nano's efficiency
- ✅ Maintains backward-compatible schema

**Use Cases**:
- High-volume processing
- Cost-sensitive applications
- Real-time analysis
- Development and testing

**Estimated Token Cost**: ~200-300 prompt tokens per request

---

## Automatic Selection

The system automatically selects the appropriate prompt based on the model name:

```python
# In llm_tuner.py
def _resolve_prompt_path(provider: str, model_name: str = "") -> Path:
    # For nano models
    if provider == "openai" and "nano" in model_name.lower():
        return "base_prompt_ko_openai_nano.txt"  # 59 lines

    # For full models
    return "base_prompt_ko_openai.txt"  # 318 lines
```

**Current Configuration** (from `scripts/llm/config.py`):
- Model: `gpt-5-nano`
- Active Prompt: `base_prompt_ko_openai_nano.txt` ✓

---

## Comparison

| Feature | Enhanced (318 lines) | Nano (59 lines) |
|---------|---------------------|-----------------|
| **XML Sections** | 8 detailed sections | 4 essential sections |
| **Examples** | 10 comprehensive | 3 core examples |
| **Analysis Steps** | 10-step procedure | 6-step condensed |
| **Self-Reflection** | Full rubric creation | Minimal |
| **Validation Checklist** | 5 categories | Inline rules |
| **Prompt Tokens** | ~1,500-2,000 | ~200-300 |
| **Cost** | Higher | 7-10x cheaper |
| **Accuracy** | Maximum | Good (nano-optimized) |
| **Target Use** | Quality-focused | Volume/cost-focused |

---

## Schema Compatibility

Both prompts produce **identical JSON schema**:

```json
{
  "claims": [...],
  "fallacies": [...],
  "quality_scores": {...},
  "headline_features": {...},
  "highlight_spans": [...],
  "study_tips": [...]
}
```

This ensures **zero breaking changes** across different models.

---

## Performance Recommendations

### Use Enhanced Prompt When:
- Running GPT-5, GPT-4 Turbo, or full-sized models
- Quality is more important than cost
- Processing critical articles requiring high accuracy
- Benchmarking or research

### Use Nano Prompt When:
- Running GPT-5-nano or GPT-4o-mini
- Processing high volumes (1000+ articles)
- Real-time or latency-sensitive applications
- Development, testing, or prototyping
- Cost optimization is a priority

---

## Migration Notes

**Before** (single prompt for all models):
- `base_prompt_ko_openai.txt` (23 lines) → Always used
- Token cost: ~150-200 per request

**After** (model-aware selection):
- **Nano models**: `base_prompt_ko_openai_nano.txt` (59 lines) → ~200-300 tokens
- **Full models**: `base_prompt_ko_openai.txt` (318 lines) → ~1,500-2,000 tokens

**Result**:
- Nano: Slight increase (50-100 tokens) for better structure
- Full models: Significant quality improvement with GPT-5 optimizations

---

## Testing

To test prompt selection:

```bash
# Check which prompt is being used
cd "c:\Users\a\OneDrive\문서\2025-02\capstone iise\lab"
python scripts/llm_tuner.py --provider openai

# Output will show:
# Using prompt: base_prompt_ko_openai_nano.txt for provider=openai, model=gpt-5-nano
```

To override model (in `.env`):
```env
OPENAI_MODEL=gpt-5  # Will use enhanced prompt
# or
OPENAI_MODEL=gpt-5-nano  # Will use nano prompt
```

---

## Future Enhancements

Consider creating similar variants for other providers:
- `base_prompt_ko_gemini_flash.txt` (for gemini-2.5-flash-lite)
- `base_prompt_ko_claude_haiku.txt` (for claude-4.5-haiku)

This allows per-model optimization across all LLM providers.
