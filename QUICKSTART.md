# Highright - Quick Start Guide

Get up and running in 5 minutes!

---

## Prerequisites

- ✅ Chrome browser
- ✅ Python 3.7+ installed
- ✅ Gemini API key (get free at https://aistudio.google.com/app/apikey)

---

## Installation (3 Steps)

### 1️⃣ Install Chrome Extension

```bash
# Open Chrome
chrome://extensions/

# Enable "Developer mode" (top right toggle)
# Click "Load unpacked"
# Select the "chrome-ex" folder
# Copy the Extension ID (save it!)
```

### 2️⃣ Install Dependencies

```bash
cd "/path/to/lab"
pip install -r requirements.txt
```

### 3️⃣ Run Installer

**macOS:**
```bash
cd install
./mac_install.sh
```

**Windows:**
```cmd
cd install
windows_install.bat
```

**When prompted:**
1. Enter your Gemini API key
2. Enter your Extension ID (from Step 1)

---

## Usage

1. **Visit a Korean news article** on:
   - chosun.com
   - hani.co.kr
   - hankookilbo.com
   - joongang.co.kr
   - khan.co.kr

2. **Wait 0.3 seconds** - highlighting happens automatically!

3. **Check status** - Click extension icon:
   - ✓ 네이티브 호스트 연결됨 = Working!
   - ✗ 설치 프로그램을 실행하세요 = Need to run installer

---

## Troubleshooting

### Extension not working?

**Check console (F12):**
```javascript
// Should see:
[Background] ✓ Native host is healthy and ready
[Highlighter] Auto-trigger timer started
```

**Check native host:**
```bash
# macOS/Linux
tail ~/.highright/native_host.log

# Windows
type %USERPROFILE%\.highright\native_host.log
```

### Still not working?

1. **Reload extension** (chrome://extensions/ → Reload)
2. **Verify Extension ID** in manifest:
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/com.highright.analyzer.json

   # Check "allowed_origins" has correct ID
   ```

3. **Re-run installer** with correct Extension ID

---

## Uninstall

```bash
cd install
python uninstall.py  # or python3 on macOS/Linux
```

---

## Getting Help

- 📖 Full docs: [install/README_INSTALL.md](install/README_INSTALL.md)
- 📝 Migration notes: [NATIVE_MESSAGING_MIGRATION.md](NATIVE_MESSAGING_MIGRATION.md)
- 🐛 Check logs: `~/.highright/native_host.log`

---

**That's it! Happy reading!** 📚✨
