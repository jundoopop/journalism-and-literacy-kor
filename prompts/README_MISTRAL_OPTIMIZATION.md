# Mistral Prompt Optimization Summary

## Overview

Successfully optimized the Mistral prompt ([base_prompt_ko_mistral.txt](base_prompt_ko_mistral.txt)) following official Mistral AI prompting best practices for **ministral-3b-2512**.

## What Changed

### Before (23 lines)

```text
시스템 역할: 당신은 한국어 저널리즘 비평가이자 논증 분석가입니다...
- Flat structure
- No examples
- Old claims/fallacies/quality_scores schema
- Minimal guidance
```

### After (80 lines)

```text
당신은 문해력 향상 지원 시스템입니다.
당신의 임무: 주어진 기사에서 핵심 문장을 선별합니다.
- ### delimited sections (Mistral pattern)
- 3 few-shot examples
- New core_sentences schema
- Explicit JSON requirements
```

## Mistral-Specific Optimizations Applied

| Best Practice | Implementation | Source |
|--------------|----------------|--------|
| **Role + Task Pattern** | "당신은 X입니다. 당신의 임무: Y" | Official docs |
| **### Delimiters** | `### 선별 원칙 ###` for all sections | Official docs |
| **Few-Shot Examples** | 3 labeled examples with ### headers | Official docs |
| **Numbered Priority** | 1순위, 2순위, 3순위 for conflict resolution | Official docs |
| **Objective Language** | Direct Korean, no vague terms | Official docs |
| **Minimal Output** | Only 1-4 sentences requested | Official docs |
| **No Contradictions** | Clear priority hierarchy | Official docs |

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

**Rationale**: Simplified for literacy support application - focus on core sentence selection rather than comprehensive journalism analysis.

## Structure Breakdown

```text
Lines 1-2:   Role and Task Definition (Mistral pattern)
Lines 4-10:  ### 선별 원칙 ### (Selection Principles)
Lines 12-20: ### 출력 JSON 구조 ### (JSON Schema)
Lines 22-25: ### 제약 조건 ### (Constraints)
Lines 27-37: ### 예시 1 ### (Example 1 - Policy criticism)
Lines 39-49: ### 예시 2 ### (Example 2 - Economic forecast)
Lines 51-65: ### 예시 3 ### (Example 3 - Multiple sentences)
Lines 67-80: ### 출력 규칙 ### (Output Rules)
```

## Key Features

### ✅ Mistral-Native Patterns

1. **### Section Delimiters**: All sections use `### Header ###` format
2. **Role-Task Structure**: Clear "You are X, your task is Y" opening
3. **Few-Shot Learning**: 3 comprehensive Korean examples
4. **Priority Hierarchy**: Numbered 1순위, 2순위, 3순위 for conflicts
5. **Explicit Requirements**: Bulleted mandatory requirements

### ✅ Korean Language Optimization

- **All Korean**: Instructions, examples, output schema
- **reason Field**: Enforced Korean-only explanations
- **Korean Examples**: Realistic Korean news scenarios
- **Cultural Context**: Policy, economy, corporate news examples

### ✅ Ministral-3B Optimization

- **Concise**: 80 lines (vs 318 for full enhanced prompts)
- **No Complex Reasoning**: No self-reflection or validation checklists
- **Clear Structure**: Simple hierarchy, not nested complexity
- **Efficient**: Minimal token overhead (~300-400 prompt tokens)

## Comparison: OpenAI Nano vs Mistral

| Feature | OpenAI Nano (46 lines) | Mistral (80 lines) |
|---------|----------------------|-------------------|
| **Delimiters** | === headers === | ### headers ### |
| **Role Pattern** | "You are X" | "당신은 X입니다. 당신의 임무: Y" |
| **Examples** | Minimal/implied | 3 explicit with ### |
| **Priority Rules** | Simple list | Numbered hierarchy (1순위~3순위) |
| **Language** | Mixed (English headers) | Pure Korean |
| **Length** | More compact | More detailed examples |

Both achieve the same goal (core sentence selection) but use provider-specific patterns.

## Testing Checklist

- [ ] Verify ### delimiter consistency (all sections properly marked)
- [ ] Test JSON output with ministral-3b-2512 API
- [ ] Validate Korean reason field enforcement
- [ ] Compare selection quality vs OpenAI nano
- [ ] Monitor JSON compliance rate
- [ ] Measure token usage (~300-400 prompt tokens expected)

## Usage

The prompt is automatically loaded by `scripts/llm/providers/mistral.py` when using the Mistral provider.

**Current Model**: `ministral-3b-2512` (configured in `.env`)

**To Test**:

```bash
# Set Mistral provider in .env
LLM_PROVIDER=mistral
MISTRAL_MODEL=ministral-3b-2512

# Run analysis
python scripts/llm_tuner.py --provider mistral
```

## Performance Expectations

Based on Mistral documentation and ministral-3b characteristics:

| Metric | Expected Value |
|--------|---------------|
| **JSON Reliability** | ⭐⭐⭐⭐ (4/5) |
| **Prompt Tokens** | ~300-400 per request |
| **Latency** | Fast (3B lightweight model) |
| **Cost** | Very low (smallest Mistral model) |
| **Selection Quality** | Good (optimized few-shot examples) |

## Next Steps

1. **Test with Real Articles**: Run 10-20 Korean news articles
2. **Compare Providers**: Benchmark vs OpenAI, Gemini, Claude
3. **Monitor JSON Errors**: Track parsing failures
4. **Optimize Examples**: Refine based on real-world performance
5. **Consider Model Upgrade**: If quality insufficient, test with `mistral-small-2506`

## References

- **Mistral Prompting Guide**: https://docs.mistral.ai/capabilities/completion/prompting_capabilities
- **Mistral Cookbook**: https://docs.mistral.ai/cookbooks/mistral-prompting-prompting_capabilities
- **Template Source**: [prompts/base_prompt_ko_openai_nano.txt](base_prompt_ko_openai_nano.txt)
- **Provider**: [scripts/llm/providers/mistral.py](../scripts/llm/providers/mistral.py)

---

**Created**: 2025-12-29
**Model**: ministral-3b-2512
**Lines**: 80 (optimized for lightweight 3B model)
**Schema**: core_sentences (simplified selection task)
