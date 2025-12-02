# Highright Installation Guide

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation Steps](#installation-steps)
4. [Getting Your Extension ID](#getting-your-extension-id)
5. [Troubleshooting](#troubleshooting)
6. [Uninstallation](#uninstallation)

---

## Overview

Highright is a Chrome extension that automatically highlights literacy-enhancing sentences in Korean news articles using Google's Gemini API.

The extension uses **Native Messaging** to communicate with a Python backend. This requires a one-time installation of the native messaging host on your system.

---

## System Requirements

### All Platforms
- **Chrome/Chromium Browser** (version 88+)
- **Python 3.7 or higher**
- **Gemini API Key** (free at https://aistudio.google.com/app/apikey)

### Windows
- Windows 10 or higher
- Administrator privileges (for registry write)

### macOS
- macOS 10.13 or higher
- No special privileges required

### Linux
- Any modern Linux distribution
- No special privileges required

---

## Installation Steps

### Step 1: Install Chrome Extension

1. **Load the extension in Chrome:**
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable **Developer mode** (toggle in top right corner)
   - Click **"Load unpacked"**
   - Select the `chrome-ex` folder from this project

2. **Get your Extension ID:**
   - After loading, you'll see the extension in the list
   - Copy the **Extension ID** (32-character alphanumeric string)
   - **Save this ID** - you'll need it in the next step!

   Example: `abcdefghijklmnopqrstuvwxyz123456`

3. **Pin the extension (optional):**
   - Click the puzzle icon in Chrome toolbar
   - Find "Highright" and click the pin icon

---

### Step 2: Install Native Messaging Host

Choose your operating system:

#### **Windows Installation**

1. **Open Command Prompt or PowerShell**

2. **Navigate to the install folder:**
   ```cmd
   cd "path\to\lab\install"
   ```

3. **Run the installer:**
   ```cmd
   windows_install.bat
   ```

   Or directly:
   ```cmd
   python install.py
   ```

4. **Follow the prompts:**
   - Enter your **Gemini API Key** when prompted
   - Enter your **Chrome Extension ID** (from Step 1)

5. **Verify installation:**
   - The installer will create registry entry at:
     `HKEY_CURRENT_USER\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.highright.analyzer`
   - Files installed to: `%LOCALAPPDATA%\Highright\`

#### **macOS Installation**

1. **Open Terminal**

2. **Navigate to the install folder:**
   ```bash
   cd "/path/to/lab/install"
   ```

3. **Run the installer:**
   ```bash
   ./mac_install.sh
   ```

   Or directly:
   ```bash
   python3 install.py
   ```

4. **Follow the prompts:**
   - Enter your **Gemini API Key** when prompted
   - Enter your **Chrome Extension ID** (from Step 1)

5. **Verify installation:**
   - Manifest created at:
     `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.highright.analyzer.json`
   - Files installed to: `~/Library/Application Support/Highright/`

#### **Linux Installation**

1. **Open Terminal**

2. **Navigate to the install folder:**
   ```bash
   cd "/path/to/lab/install"
   ```

3. **Run the installer:**
   ```bash
   python3 install.py
   ```

4. **Follow the prompts:**
   - Enter your **Gemini API Key** when prompted
   - Enter your **Chrome Extension ID** (from Step 1)

5. **Verify installation:**
   - Manifest created at:
     `~/.config/google-chrome/NativeMessagingHosts/com.highright.analyzer.json`
   - Files installed to: `~/.local/share/highright/`

---

## Getting Your Extension ID

### Method 1: From chrome://extensions/

1. Open `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Find "Highright" extension
4. Copy the ID shown below the extension name

### Method 2: From the installation folder

After installing the extension:
```bash
# In the chrome-ex folder
ls -la
# Look for a folder with a long alphanumeric name - that's your ID
```

---

## Post-Installation Verification

### 1. Check Extension Popup

1. Click the Highright extension icon in your Chrome toolbar
2. You should see: **"✓ 네이티브 호스트 연결됨"** (Native host connected)
3. If you see **"✗ 설치 프로그램을 실행하세요"**, the installation failed

### 2. Check Console Logs

1. Open a supported news site (e.g., https://www.chosun.com)
2. Open Chrome DevTools (F12)
3. Go to **Console** tab
4. Look for `[Highlighter] Content script loaded` and `[Highlighter] Auto-trigger timer started`
5. Check for `[Background] ✓ Native host is healthy and ready`

### 3. Test Highlighting

1. Visit a Korean news article on a supported site:
   - chosun.com (Chosun Ilbo)
   - hani.co.kr (Hankyoreh)
   - hankookilbo.com (Hankook Ilbo)
   - joongang.co.kr (JoongAng Ilbo)
   - khan.co.kr (Kyunghyang Shinmun)

2. Wait 0.3 seconds - highlighting should happen automatically
3. Sentences should be highlighted in yellow

---

## Troubleshooting

### Issue: "Native host not found"

**Symptoms:**
- Extension popup shows: "✗ 설치 프로그램을 실행하세요"
- Console error: `Failed to connect to native host`

**Solutions:**

1. **Verify Extension ID matches manifest:**
   - Open the manifest file:
     - Windows: `%LOCALAPPDATA%\Highright\com.highright.analyzer.json`
     - macOS: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.highright.analyzer.json`
     - Linux: `~/.config/google-chrome/NativeMessagingHosts/com.highright.analyzer.json`
   - Check that `allowed_origins` contains your correct extension ID
   - If not, run the installer again with the correct ID

2. **Verify Python path in manifest:**
   - Open the manifest file
   - Check that the `path` points to a valid executable
   - Test manually:
     ```bash
     # The path from the manifest
     python /path/to/Highright/native_host.py
     ```

3. **Re-run the installer:**
   ```bash
   python install.py
   ```

---

### Issue: "Gemini API not initialized"

**Symptoms:**
- Extension works but no sentences are highlighted
- Console shows: "Gemini API not initialized"

**Solutions:**

1. **Check API key storage:**
   - The installer should have saved your API key to the system keychain
   - Test manually:
     ```bash
     python3 -c "import keyring; print(keyring.get_password('highright', 'gemini_api_key'))"
     ```

2. **Set API key manually:**
   ```bash
   python3 -c "import keyring; keyring.set_password('highright', 'gemini_api_key', 'YOUR_API_KEY_HERE')"
   ```

3. **Use environment variable (alternative):**
   - Create `.env` file in the Highright installation directory
   - Add: `GEMINI_API_KEY=your_key_here`

---

### Issue: "Request timeout"

**Symptoms:**
- Extension hangs with "분석 중..." (Analyzing...)
- Console shows: "Request timeout"

**Solutions:**

1. **Check network connection**
2. **Verify Gemini API quota:**
   - Visit https://aistudio.google.com/app/apikey
   - Check if you've exceeded the free tier limits
3. **Check native host logs:**
   - Windows: `%USERPROFILE%\.highright\native_host.log`
   - macOS/Linux: `~/.highright/native_host.log`

---

### Issue: Windows SmartScreen Warning

**Symptoms:**
- "Windows protected your PC" message when running installer

**Solution:**
- This is normal for unsigned applications
- Click **"More info"**
- Click **"Run anyway"**
- This is safe - you can review the source code in `install/install.py`

---

### Issue: macOS Gatekeeper Warning

**Symptoms:**
- "Cannot open because it is from an unidentified developer"

**Solution:**
- Right-click the installer script
- Select **"Open"**
- Click **"Open"** again in the dialog
- Or: System Settings → Privacy & Security → Allow installer

---

## Uninstallation

### Quick Uninstall

Run the uninstaller:

```bash
# Windows
cd install
python uninstall.py

# macOS/Linux
cd install
python3 uninstall.py
```

The uninstaller will:
- Remove native messaging host files
- Remove registry entry (Windows) or manifest (macOS/Linux)
- Remove API key from keychain
- Remove log files

### Manual Uninstall

If the uninstaller doesn't work:

#### Windows:
1. Delete folder: `%LOCALAPPDATA%\Highright`
2. Delete registry key: `HKEY_CURRENT_USER\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.highright.analyzer`
3. Delete logs: `%USERPROFILE%\.highright`

#### macOS:
1. Delete folder: `~/Library/Application Support/Highright`
2. Delete manifest: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.highright.analyzer.json`
3. Delete logs: `~/.highright`
4. Remove from keychain: Open "Keychain Access" app → Search "highright" → Delete

#### Linux:
1. Delete folder: `~/.local/share/highright`
2. Delete manifest: `~/.config/google-chrome/NativeMessagingHosts/com.highright.analyzer.json`
3. Delete logs: `~/.highright`

### Remove Chrome Extension

1. Go to `chrome://extensions/`
2. Find "Highright"
3. Click **"Remove"**

---

## Advanced Configuration

### Change Native Host Logging Level

Edit `native_host.py` and change:
```python
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,  # Change to DEBUG for verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Use Custom Gemini Model

Edit `native_host.py` and modify the GeminiAnalyzer initialization:
```python
self.analyzer = GeminiAnalyzer(api_key=api_key, model_name='gemini-1.5-pro')
```

---

## Getting Help

### Check Logs

**Native Host Logs:**
- Windows: `%USERPROFILE%\.highright\native_host.log`
- macOS/Linux: `~/.highright/native_host.log`

**Chrome Extension Logs:**
1. Open Chrome DevTools (F12)
2. Go to Console tab
3. Look for `[Background]` and `[Highlighter]` prefixed messages

### Report Issues

When reporting issues, include:
1. Operating system and version
2. Python version (`python --version`)
3. Chrome version (`chrome://version`)
4. Native host log file
5. Chrome console errors
6. Steps to reproduce

---

## Frequently Asked Questions

### Q: Do I need to start the server manually?

**A:** No! Native messaging automatically starts the Python host when Chrome extension needs it.

### Q: Can I use this on multiple computers?

**A:** Yes, but you need to install the native host on each computer separately.

### Q: Does this work offline?

**A:** No, it requires internet connection to call the Gemini API.

### Q: How much does the Gemini API cost?

**A:** Gemini API offers a free tier with 15 requests/minute and 1,500 requests/day. Check https://ai.google.dev/pricing

### Q: What data is sent to Google?

**A:** Only the article text you're viewing is sent to Gemini API for analysis. The extension doesn't collect or store any personal data.

### Q: Can I modify the prompt?

**A:** Yes! Edit `scripts/gemini_handler.py` and modify the `SYSTEM_PROMPT` variable.

---

## License & Credits

- **Project:** Highright - Literacy Enhancement Tool
- **Author:** [Your Name]
- **License:** [Your License]
- **Gemini API:** Google Generative AI

---

**Happy Reading!** 📚✨
