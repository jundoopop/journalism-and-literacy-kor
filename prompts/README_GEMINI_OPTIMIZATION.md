# Gemini Prompt Optimization Summary

## Overview

Successfully optimized the Gemini prompt ([base_prompt_ko_gemini.txt](base_prompt_ko_gemini.txt)) following official Google Gemini prompting best practices for **gemini-2.5-flash-lite**.

## What Changed

### Before (23 lines)

```text
시스템 역할: 당신은 한국어 저널리즘 비평가이자 논증 분석가입니다...
- Flat Korean text
- No examples
- Old claims/fallacies/quality_scores schema
- Minimal structure
```

### After (83 lines)

```text
You are an information extraction system for a literacy-support application.

Your task is NOT to summarize or explain the article.
Your task is to SELECT sentences from the article.
- English instructions with === delimiters (Gemini pattern)
- 3 few-shot examples with "JSON:" prefix
- New core_sentences schema
- Context-first, instructions-last structure
```

## Gemini-Specific Optimizations Applied

| Best Practice | Implementation | Source |
|--------------|----------------|--------|
| **Few-Shot Examples** | 3 labeled examples (always recommended) | Gemini docs |
| **Output Prefix** | "JSON:" before each example output | Gemini docs |
| **=== Delimiters** | `=== Section ===` for clear boundaries | Gemini docs |
| **Context First** | Principles → Schema → Examples → Rules | Gemini docs |
| **Instructions Last** | "Based on the information above..." at end | Gemini docs |
| **Consistent Format** | All examples use same structure | Gemini docs |
| **Clear & Specific** | Explicit "Do NOT" commands, no vague terms | Gemini docs |
| **Positive Patterns** | Show what right looks like (not what to avoid) | Gemini docs |

## Schema Migration

### Old Schema (deprecated)

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

### New Schema (current)

```json
{
  "core_sentences": [
    {
      "sentence": "원문 문장 그대로",
      "reason": "한국어로 작성된 선별 이유"
    }
  ]
}
```

**Rationale**: Matches the updated literacy support application schema (same as OpenAI and Mistral).

## Structure Breakdown

```text
Lines 1-6:   Role and Task Definition (clear persona)
Lines 8-14:  === Selection Principles === (what to select)
Lines 16-24: === JSON Schema === (exact format)
Lines 26-29: === Constraints === (selection rules)
Lines 31-42: === Example 1 === (with "JSON:" prefix)
Lines 44-55: === Example 2 === (with "JSON:" prefix)
Lines 57-72: === Example 3 === (with "JSON:" prefix)
Lines 74-83: === Output Rules === + Final instruction
```

## Key Gemini Optimizations

### ✅ Few-Shot Learning Pattern

Gemini documentation emphasizes: **"We recommend to always include few-shot examples in your prompts. Prompts without few-shot examples are likely to be less effective."**

Each example includes:
1. **Article:** prefix showing input
2. **JSON:** prefix signaling expected output format
3. Complete JSON structure demonstrating schema

### ✅ Output Prefix Signal

The "JSON:" prefix before each example output is a Gemini-specific technique:
> "Prefixes as Signals: Add output prefixes like 'JSON:' to signal expected format."

This helps the model recognize the pattern more reliably.

### ✅ Context-First Structure

Following Gemini's recommendation:
> "Long Context Ordering: When providing extensive context, supply all the context first. Place your specific instructions or questions at the very end of the prompt."

Structure: Principles → Schema → Examples → **Final instruction at end**

### ✅ Consistent Formatting

All three examples follow identical structure:
- Same delimiter pattern (=== Example N ===)
- Same prefix pattern (Article: / JSON:)
- Same JSON format
- Same Korean reason field

This consistency helps Gemini learn the pattern more effectively.

## Comparison: Mistral vs Gemini

| Feature | Mistral (84 lines) | Gemini (83 lines) |
|---------|-------------------|-------------------|
| **Delimiters** | ### Section ### | === Section === |
| **Role Pattern** | "당신은..." pattern | "You are..." pattern |
| **Examples** | 3 with ### headers | 3 with === headers + JSON: prefix |
| **Output Signal** | No prefix | "JSON:" prefix before outputs |
| **Final Instruction** | "내부적으로 분석하되..." | "Based on the information above..." |
| **Structure** | Numbered priorities | Context-first ordering |

Both achieve the same goal but use provider-specific best practices.

## Gemini Flash-Lite Characteristics

**Model**: `gemini-2.5-flash-lite` (configured in `scripts/llm/config.py`)

**Characteristics**:
- **Lightweight**: Optimized for speed and cost
- **Flash Series**: Fast inference, lower latency
- **Lite Variant**: Most cost-effective option
- **Temperature**: Currently 0.2 (good for deterministic JSON output)

**Performance Expectations**:
- **Speed**: Very fast (flash series optimization)
- **Cost**: Very low (lite variant)
- **JSON Quality**: Good with few-shot examples
- **Prompt Tokens**: ~350-450 per request

## Testing Checklist

- [ ] Verify === delimiter consistency
- [ ] Test JSON output with gemini-2.5-flash-lite API
- [ ] Validate Korean reason field enforcement
- [ ] Compare vs Mistral and OpenAI versions
- [ ] Monitor JSON compliance rate
- [ ] Check for markdown code block issues
- [ ] Measure token usage

## Usage

The prompt is automatically loaded by `scripts/llm/providers/gemini.py`.

**Current Model**: `gemini-2.5-flash-lite` (default in config)

**To Test**:

```bash
# Set Gemini provider in .env or runtime
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash-lite

# Run analysis
python scripts/llm_tuner.py --provider gemini
```

## Performance Recommendations

### Current Configuration (Good)

```python
# In config.py
DEFAULT_MODELS = {
    LLMProvider.GEMINI: "gemini-2.5-flash-lite"
}

# Environment variables
LLM_TEMPERATURE=0.2  # Deterministic output
LLM_TIMEOUT=40       # Sufficient for flash-lite
```

### Potential Optimizations

1. **JSON Mode** (if supported by Gemini API):
   ```python
   generation_config = {
       "response_mime_type": "application/json"
   }
   ```

2. **Max Tokens Limit**:
   ```bash
   LLM_MAX_TOKENS_PER_PROVIDER='{"gemini": 500}'
   ```
   Flash-lite is optimized for shorter outputs.

3. **Temperature Adjustment**:
   - Current: 0.2 (good)
   - For even more deterministic: 0.1
   - **Note**: Gemini 3 models recommend keeping temperature at 1.0, but flash-lite is fine with lower values

## Key Differences from Other Providers

### vs OpenAI Nano
- **Similar**: English instructions, === delimiters, 3 examples
- **Different**: Gemini uses "JSON:" prefix, context-first ordering

### vs Mistral
- **Similar**: English instructions, same schema, 3 examples
- **Different**: === vs ###, JSON: prefix, final instruction phrasing

### vs Original (Korean)
- **Improvement**: English instructions (better model understanding)
- **Improvement**: Few-shot examples (essential for Gemini)
- **Improvement**: Output prefix signals (Gemini-specific technique)
- **Improvement**: Consistent formatting (pattern recognition)

## References

- **Gemini Prompting Guide**: https://ai.google.dev/gemini-api/docs/prompting-strategies
- **Gemini Workspace Guide**: https://services.google.com/fh/files/misc/gemini-for-google-workspace-prompting-guide-101.pdf
- **Template Sources**:
  - [prompts/base_prompt_ko_openai_nano.txt](base_prompt_ko_openai_nano.txt) (structure)
  - [prompts/base_prompt_ko_mistral.txt](base_prompt_ko_mistral.txt) (comparison)
- **Provider**: [scripts/llm/providers/gemini.py](../scripts/llm/providers/gemini.py)

---

**Created**: 2025-12-29
**Model**: gemini-2.5-flash-lite
**Lines**: 83 (optimized for lightweight flash-lite model)
**Schema**: core_sentences (simplified selection task)
