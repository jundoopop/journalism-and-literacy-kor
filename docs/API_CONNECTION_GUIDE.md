# API Connection Testing Guide

## Quick Test

Run this command to check all API connections:

```bash
python scripts/test_api_connection.py
```

---

## Understanding the Logs

### 1. **Provider Registration**
```
INFO: Registered 5 providers
```
✅ **Meaning**: All LLM provider classes loaded successfully
🔍 **What it checks**: Factory pattern initialization

---

### 2. **API Key Detection**

#### ✅ API Key Found
```
INFO: --- Testing GEMINI ---
INFO: Creating gemini provider with model gemini-2.5-flash-lite
```
**Meaning**: API key loaded from `.env` file

#### ⚠️ API Key Missing
```
WARNING: ⚠️  CLAUDE: API key not configured (skipping)
```
**Meaning**: `CLAUDE_API_KEY` is empty or not set in `.env`
**Action**: Add API key to `.env` file if you want to use this provider

---

### 3. **Provider Initialization**

#### ✅ Successful Initialization
```
INFO: Gemini initialized with model: gemini-2.5-flash-lite
INFO: Successfully created gemini provider with model: gemini-2.5-flash-lite
```
**Meaning**: Provider configured correctly with default model

#### ❌ Initialization Failed
```
ERROR: Failed to initialize gemini: API key validation failed
```
**Meaning**: API key format is invalid or provider configuration error

---

### 4. **API Call Testing**

#### ✅ Successful API Call (Gemini Example)
```
INFO: Sending test request...
INFO: Successfully extracted 2 sentences
INFO: Success! Response: {'status': 'ok', 'message': 'Hello from gemini'}
```
**Meaning**:
- API call succeeded
- JSON parsing worked
- Provider is fully operational

#### ❌ Quota Exceeded (OpenAI Example)
```
INFO: HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
INFO: Retrying request to /chat/completions in 0.450585 seconds
ERROR: OpenAI API call failed: Error code: 429 - {'error': {..., 'type': 'insufficient_quota', ...}}
```
**Meaning**:
- HTTP 429 = Rate limit or quota exceeded
- System automatically retries (up to MAX_RETRIES from .env)
- `insufficient_quota` = Need to add credits to OpenAI account

**Actions**:
1. Check billing at https://platform.openai.com/account/billing
2. Add payment method or wait for quota reset
3. Or use a different provider (Gemini, Claude)

#### ❌ Invalid API Key
```
ERROR: OpenAI API call failed: Error code: 401 - Unauthorized
```
**Meaning**: API key is invalid or revoked
**Action**: Generate new API key from provider dashboard

#### ❌ Network Error
```
ERROR: Failed to test gemini: Connection timeout
```
**Meaning**: Network connectivity issue or API endpoint unreachable
**Actions**:
1. Check internet connection
2. Verify firewall/proxy settings
3. Check if API endpoint is accessible

---

## Test Summary Interpretation

### ✅ All Working
```
============================================================
TEST SUMMARY
============================================================
✅ GEMINI: CONNECTED
✅ OPENAI: CONNECTED
✅ CLAUDE: CONNECTED

✓ Working providers: gemini, openai, claude
```
**Meaning**: All configured APIs are working perfectly!

### ⚠️ Mixed Results (Current Status)
```
============================================================
TEST SUMMARY
============================================================
✅ GEMINI: CONNECTED
❌ OPENAI: FAILED (check logs above)
⚠️  CLAUDE: NOT CONFIGURED

✓ Working providers: gemini
✗ Failed providers: openai
⚠ Not configured: claude
```
**Meaning**:
- **Gemini**: Working (use this for production)
- **OpenAI**: Configured but quota exceeded (can't use right now)
- **Claude**: Not configured yet (optional)

---

## Flask Server Logs

When running `python scripts/server.py`, watch for these logs:

### ✅ Successful Startup
```
==================================================
Chrome Extension API Server
==================================================
✓ Server: http://localhost:5001
✓ Health check: http://localhost:5001/health

Environment:
  GEMINI_API_KEY: 설정됨 ✓
  Analyzer Status: 정상 ✓
==================================================
INFO: ✓ Gemini API initialized successfully
```

### ❌ Failed Startup
```
ERROR: ✗ Gemini API initialization failed: API key not found
  Analyzer Status: 실패 ✗
```
**Action**: Check `.env` file has valid `GEMINI_API_KEY`

---

## Consensus Mode Logs

When using multi-LLM consensus (`/analyze_consensus` endpoint):

### ✅ Multi-Provider Success
```
INFO: [Consensus Request] URL: ..., Providers: ['gemini', 'openai']
INFO: [2/3] Analyzing with 2 providers...
INFO: [gemini] Analyzing article...
INFO: [gemini] ✓ Found 5 sentences
INFO: [openai] Analyzing article...
INFO: [openai] ✓ Found 4 sentences
INFO: ✓ Consensus calculated: 7 unique sentences from 2 providers
```
**Meaning**: Both providers analyzed successfully, consensus merged

### ⚠️ Partial Success
```
INFO: [Consensus Request] URL: ..., Providers: ['gemini', 'openai', 'claude']
INFO: [gemini] ✓ Found 5 sentences
INFO: [openai] ✗ Analysis failed: insufficient_quota
INFO: [claude] ✗ Analysis failed: API key not configured
INFO: ✓ Consensus calculated: 5 unique sentences from 1 providers
```
**Meaning**: Only Gemini succeeded, but system continues with available data

### ❌ Complete Failure
```
ERROR: No successful provider results
```
**Meaning**: All providers failed
**Action**: Check API keys and quotas

---

## Common Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| **401** | Invalid API key | Regenerate API key |
| **403** | API access forbidden | Check account permissions |
| **429** | Rate limit/quota exceeded | Wait or upgrade plan |
| **500** | Provider server error | Retry later |
| **503** | Service unavailable | Provider maintenance, try later |

---

## Monitoring During Production

### Chrome Extension Logs

1. **Content Script** (F12 → Console):
```
[Highlighter] Auto-loading started...
[Highlighter] Sentences loaded: 5 items
[Highlighter] Highlighting complete! (234.56ms)
[Highlighter] Highlighted 5 sentences
```

2. **Background Worker** (chrome://extensions/ → Service Worker):
```
[Background] Analysis request: https://www.chosun.com/...
[Background] Using consensus mode with providers: gemini, openai
[Background] Calling http://localhost:5001/analyze_consensus
[Background] Analysis complete: 7 sentences
[Background] Cache saved: https://www.chosun.com/...
```

### Flask Server Real-time Logs

```
[Request] URL: https://www.chosun.com/...
[1/3] Crawling article from: ...
✓ Crawling complete: 윤석열 탄핵 소추안...
[2/3] Analyzing with Gemini API...
✓ Analysis complete: 5 sentences extracted
[3/3] Sending response
```

---

## Troubleshooting Checklist

### Before Testing:
- [ ] `.env` file exists in project root
- [ ] API keys are set (not empty strings)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)

### If Test Fails:
- [ ] Check exact error message in logs
- [ ] Verify API key is valid (not expired/revoked)
- [ ] Check account billing/quota on provider dashboard
- [ ] Test internet connection
- [ ] Try a different provider

### If Flask Server Fails:
- [ ] Port 5001 not in use (`lsof -i :5001`)
- [ ] Environment variables loaded (`python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"`)

---

## Recommended Configuration

For **single LLM mode** (default):
```bash
# .env
GEMINI_API_KEY=your_key_here
```

For **consensus mode**:
```bash
# .env
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
CLAUDE_API_KEY=your_key_here  # optional
CONSENSUS_ENABLED=True
CONSENSUS_PROVIDERS=gemini,openai
```

---

## Quick Diagnosis Commands

```bash
# 1. Test all APIs
python scripts/test_api_connection.py

# 2. Check environment variables
cat .env

# 3. Test Flask server health
curl http://localhost:5001/health

# 4. Test single analysis (requires running server)
curl -X POST http://localhost:5001/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.chosun.com/..."}'

# 5. Test consensus analysis
curl -X POST http://localhost:5001/analyze_consensus \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.chosun.com/...", "providers": ["gemini"]}'
```

---

## Provider Dashboard Links

- **Gemini**: https://aistudio.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Claude**: https://console.anthropic.com/settings/keys

---

**Last Updated**: 2025-12-22
