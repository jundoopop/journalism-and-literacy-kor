# Mistral AI Setup Guide

## 🚀 Quick Setup

### Step 1: Get Mistral API Key

1. Visit **Mistral AI Console**: https://console.mistral.ai/
2. Sign up or log in with your account
3. Navigate to **API Keys** section
4. Click **"Create new key"**
5. Copy your API key (starts with something like `5vN...`)

### Step 2: Add API Key to `.env`

Open your `.env` file and add your Mistral API key:

```bash
MISTRAL_API_KEY=your_mistral_api_key_here
```

**Example:**
```bash
MISTRAL_API_KEY=5vN8xYz123AbCdEfGh456IjKlMnOpQr789StUvWxYz
```

### Step 3: Test Connection

Run the test script:

```bash
python scripts/test_api_connection.py
```

You should see:
```
✅ MISTRAL: CONNECTED
```

---

## 📋 Mistral Configuration

### Default Model

The system uses **mistral-small-2506** by default:
- Latest 2025 model (24B parameters)
- Improved accuracy with 2x fewer infinite generations
- Optimized for JSON output
- Cost-effective for production use

### Override Model (Optional)

To use a different Mistral model, add to `.env`:

```bash
MISTRAL_MODEL=mistral-large-2407
```

**Available Models:**
- `mistral-small-2506` (default, recommended)
- `mistral-medium-2312`
- `mistral-large-2407`
- `mistral-7b-instruct-v0.3`

---

## 🔧 Using Mistral in Your System

### Single Mode

Set Mistral as your default provider:

```bash
# .env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here
```

### Consensus Mode

Use Mistral alongside other providers:

```bash
# .env
CONSENSUS_ENABLED=True
CONSENSUS_PROVIDERS=gemini,mistral
# Or with all three:
CONSENSUS_PROVIDERS=gemini,openai,mistral
```

---

## 📊 Pricing (as of 2025)

Mistral offers competitive pricing:

- **mistral-small-2506**: ~$0.10 per 1M input tokens
- **mistral-medium**: ~$0.30 per 1M input tokens
- **mistral-large**: ~$1.00 per 1M input tokens

**Free Tier:**
- $5 free credits on signup
- ~50,000 article analyses with mistral-small

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Mistral API key added to `.env`
- [ ] Test script shows `✅ MISTRAL: CONNECTED`
- [ ] Flask server logs show Mistral initialization success
- [ ] Extension can analyze articles using Mistral

---

## 🐛 Troubleshooting

### Issue: "API key not configured"

**Solution:** Check `.env` file has this line:
```bash
MISTRAL_API_KEY=your_actual_key_here
```

### Issue: "Error code: 401 - Unauthorized"

**Reasons:**
1. API key is invalid or expired
2. API key was regenerated (old one revoked)

**Solution:**
1. Visit https://console.mistral.ai/api-keys
2. Delete old key and create new one
3. Update `.env` with new key

### Issue: "Error code: 429 - Rate limit exceeded"

**Solution:**
1. Mistral has rate limits on free tier
2. Wait a few minutes and retry
3. Or upgrade to paid tier for higher limits

### Issue: "Mistral initialization failed"

**Solution:**
1. Verify `mistralai` package is installed:
   ```bash
   pip install mistralai==1.2.4
   ```
2. Check Python version is 3.10+
3. Restart Flask server after updating `.env`

---

## 📈 Performance Comparison

Based on testing with Korean news articles:

| Provider | Accuracy | Speed | Cost | JSON Reliability |
|----------|----------|-------|------|------------------|
| Gemini | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡⚡ | 💰 | ⭐⭐⭐⭐⭐ |
| Mistral | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 💰💰 | ⭐⭐⭐⭐ |
| OpenAI | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | 💰💰💰 | ⭐⭐⭐⭐⭐ |
| Claude | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 💰💰💰💰 | ⭐⭐⭐⭐⭐ |

**Recommendation**: Use Gemini + Mistral in consensus mode for best cost/quality balance.

---

## 🔗 Useful Links

- **Mistral Console**: https://console.mistral.ai/
- **API Documentation**: https://docs.mistral.ai/
- **Pricing**: https://mistral.ai/technology/#pricing
- **Model Specs**: https://docs.mistral.ai/getting-started/models/

---

**Last Updated**: 2025-12-22
