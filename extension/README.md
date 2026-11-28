# PII Shield — Chrome Extension (Manifest V3)

Inline Indian PII redaction and AI-reply restoration directly inside **ChatGPT**, **Google Gemini**, and **Claude**, plus a toolbar **Quick Redact / Restore** popup that works on any website.

## Install in 30 Seconds (Chrome / Brave / Edge — Free, Unpacked)

1. Open `chrome://extensions` (or `brave://extensions` / `edge://extensions`).
2. Toggle **Developer mode** ON in the top-right corner.
3. Click **Load unpacked** and select this `extension/` folder (or unzip `pii-shield-extension.zip` from GitHub Releases and select the extracted `pii-shield-extension` folder).

## How to Use

1. Open **ChatGPT (`chatgpt.com`)**, **Gemini (`gemini.google.com`)**, or **Claude (`claude.ai`)** — a compact **Shield Prompt** pill appears in the bottom-right corner.
2. Type or paste your prompt containing personal details (names, phones, PAN, Aadhaar, UPI, passport, Voter ID, DL, DOB, bank account, IP, address) and click **Shield Prompt**.
3. Review the highlighted spans (click any span to keep it unredacted) and click **Replace in Chat**.
4. Send your redacted prompt (`[PERSON_1]`, `[PAN_1]`, etc.) to the AI. The placeholder mapping stays strictly in `chrome.storage.session` (browser RAM, cleared when the browser closes).
5. When the AI replies using placeholders, click the inline **Restore placeholders** chip on the AI message (or **Restore** on the bottom-right pill) to swap your original details back in-place.

## Backend Endpoints & Automatic Failover

Click the **PII Shield** icon in your browser toolbar → **Backend & Preferences** to choose:
- **Google Cloud Run (Primary)** — defaults to the hosted Cloud Run instance with automatic failover to the Modal backup server if Cloud Run is sleeping/paused.
- **Modal Cloud (Backup)** — uses the Modal deployment directly.
- **Local Server (`http://127.0.0.1:7860`)** — keeps all detection 100% on your own machine when running `uvicorn api.main:app --port 7860`.

## Running Extension Tests (`E12`)

```powershell
node --test extension/tests/extension.test.js
```

## Building a Release `.zip`

```powershell
python deploy/package_extension.py
# Outputs dist/pii-shield-extension.zip
```
