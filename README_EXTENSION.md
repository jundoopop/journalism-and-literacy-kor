# Chrome Extension + Gemini API Integration Guide

## Overview

This system integrates a Chrome Extension with a Python Flask server and Gemini API to automatically highlight sentences that improve literacy in news articles.

### Architecture

```
News Article Page Load (0.3s delay)
    ↓
Chrome Extension (content.js)
    ↓
Background Service Worker (background.js)
    ↓
Flask Server (scripts/server.py)
    ↓
Article Crawler (scripts/crawler_unified.py)
    ↓
Gemini API (scripts/gemini_handler.py)
    ↓ (JSON response: sentences + reasons)
Extension highlights sentences on page
```

---

## 1. Installation & Setup

### 1.1 Python Environment Setup

```bash
# Navigate to project directory
cd "/Users/joonhyeokkwon/Library/CloudStorage/OneDrive-Personnel/문서/2025-02/capstone iise/lab"

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Environment Variables

Create a `.env` file and add your Gemini API key:

```bash
# Create .env file
touch .env

# Edit .env file
nano .env
```

`.env` file contents:
```
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_PORT=5000
FLASK_DEBUG=True
```

**How to get a Gemini API key:**
1. Visit https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key and paste it in the `.env` file

### 1.3 Chrome Extension Installation

1. Open Chrome browser and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-ex` folder

---

## 2. Usage

### 2.1 Start Flask Server

Run this command in terminal:

```bash
cd "/Users/joonhyeokkwon/Library/CloudStorage/OneDrive-Personnel/문서/2025-02/capstone iise/lab"
python scripts/server.py
```

When the server starts successfully, you'll see:

```
==================================================
Chrome Extension API Server
==================================================
✓ 서버 시작: http://localhost:5000
✓ Health check: http://localhost:5000/health
✓ Test: http://localhost:5000/test

환경 변수:
  GEMINI_API_KEY: 설정됨 ✓
==================================================
```

### 2.2 Using the Extension

1. **Navigate to a supported news site:**
   - chosun.com (Chosun Ilbo)
   - hani.co.kr (Hankyoreh)
   - hankookilbo.com (Hankook Ilbo)
   - joongang.co.kr (JoongAng Ilbo)
   - khan.co.kr (Kyunghyang Shinmun)

2. **Automatic highlighting:**
   - After page load, analysis and highlighting starts automatically after 0.3s
   - View progress in Console (F12 → Console tab)

3. **Manual controls:**
   - Click the extension icon to open popup
   - **Server status:** Green (✓ Connected) or Red (✗ Disconnected)
   - **Activate:** Enable highlighting (if auto-run failed)
   - **Deactivate:** Remove all highlights
   - **Re-analyze:** Force re-analysis (ignores cache)

---

## 3. How It Works

### 3.1 Highlighting Process

1. **Page Load:** User visits a news article page
2. **Auto Trigger:** Analysis starts automatically after 0.3s delay
3. **URL Sent:** Content script sends current URL to background worker
4. **Cache Check:** Background worker checks cached results (1-hour validity)
5. **Server Request:** If no cache, sends analysis request to Flask server
6. **Crawling:** Server extracts article text (crawler_unified.py)
7. **Gemini Analysis:** Article text sent to Gemini API to extract sentences
8. **Highlighting:** Extension highlights extracted sentences in yellow

### 3.2 Gemini Prompt

The system uses this prompt to select sentences:

```
System Role: You are a critical reading training coach and media analyst.
From the given article text, select **sentences that help improve literacy**,
and explain the **reason** for selecting each sentence.

Output Format (JSON):
{
  "Sentence 1": "Reason for selection",
  "Sentence 2": "Reason for selection"
}

Rules:
- Select 3-7 sentences from the article that contribute to literacy, logical thinking, and critical reading.
- Reasons should be based on one or more of: (1) writing style/clarity, (2) logical structure, (3) inducing critical thinking.
- Output only JSON, no other text.
```

### 3.3 Caching

- **Location:** Chrome's `chrome.storage.local`
- **Validity:** 1 hour
- **Benefits:** Reduced API costs and faster loading when revisiting the same article

---

## 4. File Structure

```
lab/
├── chrome-ex/
│   ├── manifest.json          # Extension configuration
│   ├── background.js          # Service worker (Flask communication)
│   ├── content.js             # Page highlighting logic
│   ├── popup.html             # Extension popup UI
│   ├── popup.js               # Popup event handlers
│   └── icon*.png              # Extension icons
│
├── scripts/
│   ├── server.py              # Flask API server
│   ├── gemini_handler.py      # Gemini API handler
│   ├── crawler_unified.py     # Unified crawler
│   ├── crawler_chosun.py      # Chosun Ilbo parser
│   └── crawler_joongang.py    # JoongAng Ilbo parser
│
├── config.py                  # Environment configuration
├── requirements.txt           # Python dependencies
└── .env                       # API keys (you need to create this)
```

---

## 5. API Endpoints

### 5.1 Health Check
```
GET http://localhost:5000/health
```
Response:
```json
{
  "status": "ok",
  "gemini_ready": true
}
```

### 5.2 Analyze Article
```
POST http://localhost:5000/analyze
Content-Type: application/json

{
  "url": "https://www.chosun.com/..."
}
```
Response:
```json
{
  "success": true,
  "url": "...",
  "headline": "Article title",
  "sentences": ["Sentence 1", "Sentence 2", "Sentence 3"],
  "count": 3
}
```

### 5.3 Test
```
GET http://localhost:5000/test
```

---

## 6. Debugging

### 6.1 Chrome Extension Debugging

1. **Content Script Logs:**
   - F12 → Console tab
   - Look for logs with `[하이라이터]` prefix

2. **Background Worker Logs:**
   - Go to `chrome://extensions/` → Extension details → Click "Service Worker"
   - Look for logs with `[Background]` prefix

3. **Popup Debugging:**
   - Right-click on extension popup → "Inspect"

### 6.2 Flask Server Debugging

View real-time logs in server terminal:
```
[요청] URL: https://www.chosun.com/...
[1/3] 기사 크롤링 중...
✓ 크롤링 완료: ...
[2/3] Gemini API 분석 중...
✓ 분석 완료: 5개 문장 추출
[3/3] 응답 전송
```

### 6.3 Common Issues

**Issue: "Server disconnected" message**
- Solution: Verify `python scripts/server.py` is running

**Issue: "Gemini API initialization failed"**
- Solution: Check `GEMINI_API_KEY` in `.env` file

**Issue: No highlighting**
- Solution: Check F12 console for errors
- Verify you're on a supported site

**Issue: Cache preventing updates**
- Solution: Click "Re-analyze" button in extension popup

---

## 7. Development & Customization

### 7.1 Change Highlight Color

Edit `chrome-ex/content.js`:
```javascript
const CONFIG = {
  target_color: "#ffff00",  // Yellow → change to desired color
  opacity: 0.5              // Adjust transparency (0.0 ~ 1.0)
};
```

### 7.2 Change Auto-run Delay

Edit bottom of `chrome-ex/content.js`:
```javascript
setTimeout(() => {
  autoLoadAndHighlight();
}, 300);  // 300ms → change to desired value
```

### 7.3 Modify Prompt

Edit the `SYSTEM_PROMPT` variable in `scripts/gemini_handler.py`

### 7.4 Add Supported Sites

1. Add domain to `matches` and `host_permissions` in `chrome-ex/manifest.json`
2. Add domain to `SUPPORTED_DOMAINS` in `chrome-ex/popup.js`
3. If needed, add dedicated parser to `scripts/crawler_unified.py`

---

## 8. Testing

### 8.1 CLI Testing (Gemini API)

```bash
python scripts/gemini_handler.py --text "Article text to test..."
```

Or from file:
```bash
python scripts/gemini_handler.py --file article.txt
```

### 8.2 Flask Server Testing

```bash
# After starting server, in another terminal:
curl http://localhost:5000/test
```

---

## 9. License & Notes

- Check Gemini API usage limits: https://ai.google.dev/pricing
- Free tier: 15 requests per minute, 1,500 per day
- When crawling news, comply with each site's robots.txt and terms of service

---

## 10. Support

When reporting issues, include:
1. Error messages (console logs)
2. Flask server logs
3. Steps to reproduce

---

**Post-Installation Checklist:**
- [ ] Python dependencies installed
- [ ] GEMINI_API_KEY configured in `.env`
- [ ] Flask server started successfully (see "✓ 서버 시작" message)
- [ ] Chrome extension loaded
- [ ] Extension popup shows "✓ 서버 연결됨"
- [ ] Auto-highlighting works on news articles
