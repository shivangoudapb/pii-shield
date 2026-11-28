# PII Shield — 2-Minute Demo & GIF Recording Guide

Use this script to record either a crisp **2-minute walkthrough video** (for hackathon/portfolio submissions) or a **30-second README GIF**.

---

## Pre-Recording Setup (30 seconds)
1. Open your live **Google Cloud Run** Web UI (`https://pii-shield-ql5licjz5a-uc.a.run.app`) in Tab 1 so the container is warm.
2. Open **Claude (`claude.ai`)** or **Google Gemini (`gemini.google.com`)** in Tab 2 with the **PII Shield Chrome Extension** loaded.
3. Have a sample prompt ready on your clipboard (synthetic data only):
   ```text
   Draft a crisp KYC verification confirmation email for this applicant:
   Name: Dr. Ananya Rao
   DOB: 14 Aug 1998
   Phone: +91 98450 12345
   PAN: ABCDE1234F
   Passport: J8364921
   UPI: ananya@okhdfcbank
   Reference ID (not Aadhaar): 234567890123
   Address: 18 Cedar Cross, Sample Nagar, Bengaluru 560001
   ```

---

## 2-Minute Video Script

### 0:00 – 0:20 · The Problem
> *"Every day people paste resumes, KYC forms, invoices, and WhatsApp chats into ChatGPT, Gemini, and Claude. Most generic PII scrubbers miss Indian identifiers like Aadhaar Verhoeff checksums, PAN, UPI handles, Voter IDs, or Indian street addresses—and manually editing prompts breaks the AI's reply. **PII Shield** solves both."*

### 0:20 – 0:55 · Web App + Smart Validation + Selective Redaction (Tab 1)
1. Click the **Invoice** or paste the synthetic KYC sample above, then click **Redact →**.
2. Point out three details in the highlighted box:
   - **14 Indian PII categories** detected (`PERSON`, `DOB`, `PHONE`, `PAN`, `PASSPORT`, `UPI`, `LOCATION`, `PINCODE`) with confidence scores.
   - Notice `234567890123` is **not flagged** because it fails the **Verhoeff Aadhaar checksum**—avoiding false alarms on random 12-digit reference numbers.
   - **Click** one highlighted span (e.g., `Bengaluru`) to show **selective redaction**: it strikes through and stays unredacted in `[LABEL_N]` output!

### 0:55 – 1:35 · Zero-Copy-Paste Chrome Extension in Gemini / Claude (Tab 2)
1. Switch to **Claude** or **Gemini** and paste the same prompt directly into the AI chat box.
2. Click the floating **Shield Prompt** pill in the bottom-right corner → click **Replace in Chat**.
3. Show how the prompt inside the chat box is instantly rewritten to `[PERSON_1]`, `[PAN_1]`, `[PASSPORT_1]`, `[UPI_1]` while the mapping stays strictly in browser RAM (`chrome.storage.session`—never stored server-side).
4. Hit **Send** and let Claude/Gemini generate the email using `[PERSON_1]`, `[PAN_1]`, etc.
5. Click the inline **`Restore N placeholders`** button directly below the AI reply—watch every placeholder swap back to `Dr. Ananya Rao`, `ABCDE1234F`, `J8364921`, and `+91 98450 12345` in place!

### 1:35 – 2:00 · Architecture, Benchmarks & Privacy
1. Briefly flash the **README** benchmark table:
   - **Hybrid 3-layer engine:** Regex + mathematical validators > Contextual Indian rules > GLiNER neural NER.
   - **0.975 Exact F1** (`1.000` across all 12 structured Indian ID types, `0.000` false-alarm rate on no-PII messages) on the 540-item multi-domain benchmark, plus honest failure analysis on the locked test split.
   - Deployed on **Google Cloud Run** with automatic **Modal** failover, zero request-body logging, and runnable 100% locally via Docker or `pip install -e .`.
