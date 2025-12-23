# Quick Installation Guide

## Step 1: Get Your Extension ID

1. Open Chrome and go to: `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Find "Highright" or your extension name
4. Copy the **Extension ID** (looks like: `abcdefghijklmnopqrstuvwxyz123456`)

## Step 2: Run the Installer

Open Terminal and run:

```bash
cd "/Users/joonhyeokkwon/Library/CloudStorage/OneDrive-Personnel/문서/2025-02/capstone iise/lab/install"
python3 install.py
```

When prompted:
- **Gemini API Key**: Press Enter to skip (already set in .env)
- **Extension ID**: Paste the ID from Step 1

## Step 3: Reload Extension

1. Go back to `chrome://extensions/`
2. Click the reload button on your extension
3. Click the extension icon - you should now see "✓ 네이티브 호스트 연결됨"

## Troubleshooting

If it still doesn't work, check:
1. The manifest file was created at: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.highright.analyzer.json`
2. Restart Chrome completely
