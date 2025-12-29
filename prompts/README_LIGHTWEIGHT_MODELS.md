# Lightweight Model Prompts Comparison

Optimized prompts for lightweight models (nano/lite/small variants) following provider-specific best practices.

## Overview

All three prompts achieve the same goal (core sentence selection) but use provider-specific optimization techniques.

## Model Comparison

| Provider | Model | Parameters | Lines | Optimizations |
|----------|-------|-----------|-------|---------------|
| **OpenAI** | gpt-5-nano | ~7B (estimated) | 46 | === delimiters, minimal examples |
| **Mistral** | ministral-3b-2512 | 3B | 84 | ### delimiters, 3 labeled examples |
| **Gemini** | gemini-2.5-flash-lite | ~8B (estimated) | 83 | === delimiters, JSON: prefix, 3 examples |

## Prompt Structure Comparison

### OpenAI Nano (46 lines)

```text
You are an information extraction system...

=== Selection Principles ===
- A core sentence is one that...
- Prefer sentences that contain...

=== Output Rules ===
- Output MUST be valid JSON.

=== JSON Schema ===
{...}

=== Constraints ===
- Select between 1 and 4 core sentences.

Begin analysis internally, but output ONLY the JSON.
```

**Key Features**:
- ✅ Minimal, concise (46 lines)
- ✅ === delimiters
- ✅ English instructions
- ⚠️ No explicit examples (relies on schema)
- ✅ Clear constraints

---

### Mistral (84 lines)

```text
You are an information extraction system...

### Selection Principles ###
- A core sentence is one that...

### JSON Schema ###
{...}

### Example 1: Policy Criticism Article ###
Input: "정부의 새로운 주택 정책..."
Output: {...}

### Output Rules ###
Priority hierarchy (in case of conflicts):
1. Strictly follow the JSON schema
2. Quote sentences verbatim...

Begin analysis internally, but output ONLY the JSON.
```

**Key Features**:
- ✅ ### delimiters (Mistral-specific)
- ✅ 3 labeled few-shot examples
- ✅ English instructions
- ✅ Numbered priority hierarchy
- ✅ Korean examples + Korean output

---

### Gemini (83 lines)

```text
You are an information extraction system...

=== Selection Principles ===
- A core sentence is one that...

=== JSON Schema ===
{...}

=== Example 1 ===
Article: "정부의 새로운 주택 정책..."

JSON:
{...}

=== Output Rules ===
- Output MUST be valid JSON.

Based on the information above, analyze the article and output ONLY the JSON.
```

**Key Features**:
- ✅ === delimiters
- ✅ 3 few-shot examples
- ✅ **JSON:** prefix (Gemini-specific signal)
- ✅ Context-first, instructions-last ordering
- ✅ English instructions with Korean examples

## Provider-Specific Best Practices

### OpenAI

**Source**: GPT-5 Prompting Guide

| Practice | Implementation |
|----------|----------------|
| XML tags for structure | === delimiters |
| Clear constraints | 1-4 sentences specified |
| Explicit rules | MUST/Do NOT commands |
| Minimal verbosity | Concise 46 lines |

**Philosophy**: Less is more for nano models.

---

### Mistral

**Source**: Mistral AI Prompting Documentation

| Practice | Implementation |
|----------|----------------|
| ### or <<<>>> delimiters | ### Section ### |
| "You are X, your task is Y" | Explicit role definition |
| Few-shot examples (3-4) | 3 labeled examples |
| Numbered priority rules | 1순위, 2순위, 3순위 |
| Objective language | No vague terms |

**Philosophy**: Clear hierarchy and examples for 3B models.

---

### Gemini

**Source**: Gemini API Prompting Strategies

| Practice | Implementation |
|----------|----------------|
| Always include few-shot | 3 examples (required) |
| Output prefix signals | "JSON:" before outputs |
| === delimiters | === Section === |
| Context-first ordering | Instructions at end |
| Consistent formatting | All examples identical |

**Philosophy**: Few-shot learning is essential, signal expected format clearly.

## Delimiter Patterns

| Provider | Pattern | Example |
|----------|---------|---------|
| OpenAI | `=== Header ===` | `=== Selection Principles ===` |
| Mistral | `### Header ###` | `### Selection Principles ###` |
| Gemini | `=== Header ===` | `=== Selection Principles ===` |

**Note**: OpenAI and Gemini use the same delimiter pattern.

## Example Format Comparison

### OpenAI
```text
(No explicit examples - relies on schema clarity)
```

### Mistral
```text
### Example 1: Policy Criticism Article ###
Input: "정부의 새로운 주택 정책은..."
Output:
{
  "core_sentences": [...]
}
```

### Gemini
```text
=== Example 1 ===
Article: "정부의 새로운 주택 정책은..."

JSON:
{
  "core_sentences": [...]
}
```

**Key Difference**: Gemini uses "JSON:" prefix as an output signal (recommended by Gemini docs).

## JSON Schema (Identical)

All three prompts use the **exact same schema** for consistency:

```json
{
  "core_sentences": [
    {
      "sentence": "string (exact quote from article)",
      "reason": "string (MUST be written in Korean)"
    }
  ]
}
```

**Constraints**:
- Select 1-4 core sentences
- `sentence`: Verbatim quote from article
- `reason`: Korean explanation of why it's central

## Performance Characteristics

### Token Usage (Estimated)

| Provider | Prompt Tokens | Cost Efficiency |
|----------|--------------|-----------------|
| OpenAI nano | ~200-250 | Lowest (smallest prompt) |
| Mistral 3B | ~350-400 | Medium (examples add tokens) |
| Gemini flash-lite | ~350-450 | Medium (examples + prefix) |

### JSON Reliability (from testing)

| Provider | Reliability | Notes |
|----------|------------|-------|
| OpenAI nano | ⭐⭐⭐⭐⭐ | JSON mode enforced via API |
| Mistral 3B | ⭐⭐⭐⭐ | Good with examples |
| Gemini flash-lite | ⭐⭐⭐⭐⭐ | Excellent with JSON: prefix |

### Speed (Relative)

| Provider | Speed | Notes |
|----------|-------|-------|
| OpenAI nano | Fast | Optimized for nano |
| Mistral 3B | Very Fast | Smallest model (3B) |
| Gemini flash-lite | Very Fast | Flash series optimization |

## When to Use Which Model

### Use OpenAI Nano When:
- ✅ Maximum JSON reliability needed
- ✅ Cost is primary concern
- ✅ Simple, straightforward tasks
- ✅ You want minimal prompt tokens

### Use Mistral 3B When:
- ✅ Lowest cost is critical (smallest model)
- ✅ You need fast inference
- ✅ Volume processing (millions of requests)
- ✅ You want provider diversity

### Use Gemini Flash-Lite When:
- ✅ You're using Google ecosystem
- ✅ Speed is important (flash series)
- ✅ Good balance of cost/performance
- ✅ You want Gemini-specific features

## Migration Path

If migrating between providers, the schema is identical:

```python
# All providers return the same format
{
    "core_sentences": [
        {"sentence": "...", "reason": "..."},
        ...
    ]
}
```

**No code changes needed** - just swap the provider name:

```python
# Option 1: OpenAI
result = LLMFactory.create(provider='openai', model_name='gpt-5-nano')

# Option 2: Mistral
result = LLMFactory.create(provider='mistral', model_name='ministral-3b-2512')

# Option 3: Gemini
result = LLMFactory.create(provider='gemini', model_name='gemini-2.5-flash-lite')
```

## Recommendations

### Development/Testing
**Use**: OpenAI Nano
- Most reliable JSON output
- Fastest to iterate

### Production (High Volume)
**Use**: Mistral 3B
- Lowest cost per request
- Smallest model = fastest inference

### Production (Balanced)
**Use**: Gemini Flash-Lite
- Good cost/performance ratio
- Fast inference (flash series)
- Reliable JSON with few-shot examples

### Ensemble Approach
**Use**: All three with consensus voting
```python
CONSENSUS_ENABLED=True
CONSENSUS_PROVIDERS=["openai","mistral","gemini"]
```

Benefits:
- Higher accuracy via cross-validation
- Provider redundancy
- Best of all models

## Files

| Provider | Prompt File | Config |
|----------|-------------|--------|
| OpenAI | [base_prompt_ko_openai_nano.txt](base_prompt_ko_openai_nano.txt) | 46 lines |
| Mistral | [base_prompt_ko_mistral.txt](base_prompt_ko_mistral.txt) | 84 lines |
| Gemini | [base_prompt_ko_gemini.txt](base_prompt_ko_gemini.txt) | 83 lines |

## Model Configuration

```python
# In scripts/llm/config.py
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-5-nano",
    LLMProvider.MISTRAL: "ministral-3b-2512",
    LLMProvider.GEMINI: "gemini-2.5-flash-lite"
}
```

All configured for lightweight, cost-effective operation!

---

**Summary**: Three optimized prompts following provider-specific best practices, all producing identical JSON output for seamless provider switching.
