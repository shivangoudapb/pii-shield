# PII Shield

[![CI](https://github.com/shivangoudapb/pii-shield/actions/workflows/ci.yml/badge.svg)](https://github.com/shivangoudapb/pii-shield/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-2866d8.svg)](https://www.python.org/downloads/)
[![Chrome MV3](https://img.shields.io/badge/chrome_extension-Manifest_V3-168a84.svg)](extension/README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-slate.svg)](LICENSE)

**India-aware, reversible personal-data redaction for AI workflows** — available as a **Web App**, a **Manifest V3 Chrome Extension** for ChatGPT, Google Gemini, and Claude, a **FastAPI service**, and a **pip-installable Python library**.

- **Primary Live Demo (Google Cloud Run):** [https://pii-shield-ql5licjz5a-uc.a.run.app](https://pii-shield-ql5licjz5a-uc.a.run.app)
- **Backup Live Demo (Modal Cloud):** [https://bhavihalshivu--pii-shield-web-app.us-east.modal.run](https://bhavihalshivu--pii-shield-web-app.us-east.modal.run)
- **Interactive OpenAPI Docs:** [`/docs`](https://pii-shield-ql5licjz5a-uc.a.run.app/docs) · **1-Click Extension Download:** [`/pii-shield-extension.zip`](https://pii-shield-ql5licjz5a-uc.a.run.app/pii-shield-extension.zip)

> **Cold-start note:** Hosted instances scale to zero when idle. The first request after inactivity can take ~15–30 seconds while a container boots and warms GLiNER in memory.

---

## Why PII Shield?

People routinely paste resumes, KYC records, invoices, and WhatsApp chats into AI assistants. Generic PII scrubbers miss Indian identifiers (Aadhaar Verhoeff checksums, PAN, NPCI UPI handles, Voter IDs, Indian RTO Driving Licenses, Indian street addresses) and permanently strip context so the AI's reply becomes unusable.

**PII Shield fixes both:**
1. **Detects 14 PII categories** using a 3-layer hybrid engine (**Regex + Mathematical Validators > Contextual Indian Rules > GLiNER Neural NER**).
2. **Replaces entities with consistent, reversible placeholders** (`[PERSON_1]`, `[PAN_1]`, `[UPI_1]`) so repeated mentions (`"Ananya Rao"` and `"ananya rao"`) map to the same token.
3. **Restores real values inside the AI's reply** in one click—using a mapping held strictly in your browser (`chrome.storage.session` / tab memory) and **never stored or logged server-side**.

---

## Architecture

```text
Input prompt
   │
   ├──► Layer 1: Regex + Validators (Verhoeff Aadhaar, PAN, UPI, Phone, Passport, DL, EPIC, ...) ──┐
   ├──► Layer 2: Contextual Indian Rules (Honorifics, sign-offs, "Surname, First", Indian addrs) ──┼──► Priority Merge
   └──► Layer 3: GLiNER Neural NER + Indian Prefix/Blocklist/Address-Assembly Post-Processing ─────┘    (regex > rules > ner)
                                                                                                               │
                                                                                                               ▼
                                                                                                    Reversible Redactor
                                                                                                       │             │
                                                                                       [LABEL_N] prompt│             │mapping (client-only)
                                                                                                       ▼             ▼
                                                                                       ChatGPT / Gemini / Claude ──► Restore in AI reply
```

### Privacy Guarantees
- **Zero raw-text logging or persistence:** Uvicorn runs with `--no-access-log`, FastAPI overrides 422 validation errors so input bodies are never echoed, and all inference happens strictly in RAM.
- **Client-held mappings:** The server returns `{redacted, spans, mapping}` and forgets everything immediately. Only the client holds the mapping to restore AI replies.
- **Selective redaction:** Click any highlighted span in the Web UI or Chrome Extension popover to keep public names or cities unredacted before sending.

---

## Supported PII Categories (14 Labels)

| Label | Detection & Validation Logic | False-Alarm Safeguards |
|---|---|---|
| `PERSON` | GLiNER NER + Indian honorifics (`Shri`, `Smt`, `Dr`), sign-offs, `"Last, First"`, roster cues, Hinglish prefix trimming | Corporate suffix (`Pvt Ltd`, `Technologies`) & role-word blocklists |
| `LOCATION` | Structured Indian street/plot/flat/sector rules + GLiNER + comma-joined locality/city assembly (100+ Indian cities) | Generic words (`home`, `office`, `address`) & quoted titles filtered |
| `PHONE` | 10-digit Indian mobile starting `6–9` with optional `+91`, `91`, or `0` prefix and space/hyphen separators | Rejects 10-digit order IDs starting `0–5` or embedded in longer digits |
| `EMAIL` | Standard RFC-style email pattern | Separated cleanly from UPI handles via NPCI provider check |
| `AADHAAR` | 12 digits starting `2–9` (contiguous or `4-4-4` space/hyphen groups) + **full Verhoeff checksum** | Rejects random 12-digit reference/account numbers failing Verhoeff |
| `PAN` | `[A-Z]{5}[0-9]{4}[A-Z]` Income Tax Permanent Account Number | Word-boundary anchored |
| `UPI` | `handle@provider` checked against **80+ official NPCI UPI handles** (`okhdfcbank`, `ybl`, `ibl`, `axl`, `sbi`, etc.) | Never flags standard email domains (`gmail.com`, company domains) |
| `PINCODE` | 6 digits (`[1-9][0-9]{5}`) **only** within an Indian city/address context window | Ignores 6-digit OTPs, invoice numbers, and verification codes |
| `DOB` | Calendar-validated date (`1900–2025`, numeric or `14 Aug 1998`) preceded by explicit birth-date cues (`DOB:`, `Born on`) | Ignores invoice dates, meeting dates, and deadlines |
| `PASSPORT` | Indian passport `[A-Z][1-9][0-9]{6}` preceded by explicit passport context | Ignores generic 8-character product/serial codes |
| `VOTER_ID` | Indian EPIC Voter ID `[A-Z]{3}[0-9]{7}` | Negative lookahead prevents partial matches on PAN numbers |
| `DRIVING_LICENSE` | Valid Indian State/UT RTO code (`AN`–`WB`, `DL`, `KA`, `MH`, etc.) + 2-digit RTO + 4-digit year + 7-digit serial | Rejects non-existent state prefixes and out-of-range years |
| `BANK_ACCOUNT` | 9–18 digits preceded by explicit banking cues (`A/c No`, `Account No`, `IFSC`, `Beneficiary account`) | Never flags bare long numbers without banking context |
| `IP_ADDRESS` | Validated IPv4 (`0–255` octets) and IPv6 addresses | Rejects version strings (`v1.2.3.4`) |

---

## Chrome Extension (Manifest V3) — ChatGPT, Gemini & Claude

Eliminate copy-pasting between tabs. The extension injects a lightweight, dark-mode-aware **Shield Prompt** dock directly into **ChatGPT (`chatgpt.com`)**, **Google Gemini (`gemini.google.com`)**, and **Claude (`claude.ai`)**, plus a toolbar **Quick Redact / Restore** popup that works on any webpage.

### Install in 30 Seconds (Free, Unpacked — Chrome / Brave / Edge)
1. Download [`pii-shield-extension.zip`](https://pii-shield-ql5licjz5a-uc.a.run.app/pii-shield-extension.zip) (or from **GitHub Releases**) and unzip it—or clone this repo and use the [`extension/`](extension/) folder directly.
2. Open `chrome://extensions` (or `brave://extensions` / `edge://extensions`) and toggle **Developer mode** ON (top-right).
3. Click **Load unpacked** and select the unzipped `pii-shield-extension` (or `extension/`) folder.

### How It Works
1. Type or paste your prompt in **Gemini**, **Claude**, or **ChatGPT** and click **Shield Prompt** (bottom-right).
2. Review detected spans (click any span to skip redacting it) → click **Replace in Chat**.
3. Send the redacted prompt. Multi-turn conversations reuse existing placeholders (`[PERSON_1]`) and assign collision-free indices (`[PERSON_2]`) to new people, stored strictly in `chrome.storage.session` (RAM-only, cleared when the browser closes).
4. When the AI replies, click the inline **`Restore N placeholders`** button below the reply (or **`Restore (N)`** on the bottom-right dock / toolbar popup for editor canvases) to swap real details back in place.
5. **Automatic Cloud Failover:** Uses Google Cloud Run by default and automatically fails over to Modal if Cloud Run is unreachable, or can point to `http://127.0.0.1:7860` for 100% local processing.

---

## Evaluation Results

Three detector configurations are compared across synthetic splits (**A:** Regex + Rules only, **B:** GLiNER NER only, **C:** Full Hybrid Pipeline). Full per-split tables are in [`eval/results.md`](eval/results.md).

### 1. Realistic Multi-Domain Benchmark (`eval/realistic.jsonl` — 540 items, 2,432 spans, all 14 labels)

Generated deterministically (`seed=9407`) across 6 domains (`email_thread`, `whatsapp_chat`, `support_ticket`, `resume_profile`, `financial_kyc`, `institutional_notice`), 84 multi-sentence/multi-paragraph templates, 10% no-PII items, and 383 items containing inline lookalike negatives (invalid-Verhoeff 12-digit numbers, 6-digit OTPs, 10-digit order IDs, non-DOB dates, version strings, and Indian corporate names).

| Label | A: Regex + Rules (P / R / F1) | B: GLiNER Only (P / R / F1) | C: Hybrid Exact (P / R / F1) | C: Hybrid Relaxed (P / R / F1) |
|---|---:|---:|---:|---:|
| `PERSON` | 0.997 / 0.693 / 0.818 | 0.885 / 0.786 / 0.832 | **0.948 / 0.914 / 0.931** | **0.961 / 0.925 / 0.943** |
| `LOCATION` | 1.000 / 1.000 / 1.000 | 0.070 / 0.086 / 0.077 | **0.976 / 1.000 / 0.988** | **0.976 / 1.000 / 0.988** |
| All 12 Structured Labels (`PHONE`, `EMAIL`, `AADHAAR`, `PAN`, `UPI`, `PINCODE`, `DOB`, `PASSPORT`, `VOTER_ID`, `DRIVING_LICENSE`, `BANK_ACCOUNT`, `IP_ADDRESS`) | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | **1.000 / 1.000 / 1.000** | **1.000 / 1.000 / 1.000** |
| **Overall (Micro, 2,432 spans)** | **0.999 / 0.894 / 0.943** | **0.653 / 0.281 / 0.393** | **0.980 / 0.970 / 0.975** | **0.984 / 0.974 / 0.979** |

- **Round-trip restoration rate (`restore(*redact(x)) == x`):** **`1.000` (540 / 540 items)**
- **Latency (CPU, post-warmup):** median **361.5 ms/item**, p95 **528.1 ms/item** · Peak RAM: **2,725.7 MiB**

### 2. Development Split (`eval/dev.jsonl` — 60 items) & Locked Phase-3 Test Baseline (`eval/test.jsonl` — 100 items)

- **`eval/dev.jsonl` (current engine):** Overall Hybrid Micro Exact F1 improved from **`0.845` → `0.959`** (`PERSON` Exact F1 `0.764 → 0.931`, `LOCATION` Exact F1 `0.348 → 0.857`, No-PII false-alarm rate `0.000`, Round-trip rate `1.000`).
- **`eval/test.jsonl` (locked one-time Phase-3 baseline, SHA-256 `2A60BFF3746E66AFA37947F0FFFDDC631E468E10BF13D01E47BECD0F6D417F88`):** Evaluated once prior to post-Phase-3 rule/label expansions and never re-opened or tuned against (`Overall Exact F1: 0.864`, `Overall Relaxed F1: 0.905`, `No-PII false-alarm rate: 0.000`, `Round-trip rate: 1.000`; see [`eval/results.md`](eval/results.md) and [`eval/errors.md`](eval/errors.md)).

### Honest Limitations & Privacy Notes
- **Detection is not 100%:** Uncued single-token lowercase nicknames in casual Hinglish chats can still be missed (`PERSON` recall `0.914` on `realistic`), and on adversarial lookalike-heavy paragraphs GLiNER occasionally flags unfamiliar Indian corporate/place nouns (selective click-to-skip in the UI/extension lets users toggle any false alarm off in one click).
- **Script coverage:** Evaluated on English and Roman-script Hinglish text; native Indic scripts (Devanagari, Kannada, Tamil, etc.) are not yet benchmarked.
- **Synthetic benchmarks:** All evaluation datasets are 100% synthetic (`eval/DATASET_NOTES.md`); real-world formatting can vary. Always review redacted output before sharing sensitive documents.
- **Cloud vs. Local trust boundary:** Hosted demos on Cloud Run (US Central) and Modal (US East) process text strictly in memory without logging, but text still traverses HTTPS to the container. For air-gapped local privacy, run the Docker container or `uvicorn` locally and switch the Chrome Extension backend to `Local Server (127.0.0.1:7860)`.

---

## Quick Start

### 1. Run Locally (Web App + API)

Requires **Python 3.11**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 7860 --no-access-log
```

Open `http://127.0.0.1:7860` (Swagger API docs at `http://127.0.0.1:7860/docs`). On first startup, GLiNER and its tokenizer are cached locally from Hugging Face.

### 2. Use as a Python Library (`pip install`)

```powershell
python -m pip install -e .          # Lightweight regex + rules + validators only (zero heavy ML deps)
python -m pip install -e ".[ner]"   # Includes PyTorch + GLiNER neural NER
```

```python
from pii_shield import redact, restore, is_valid_aadhaar

text = "Applicant: Dr. Ananya Rao | PAN: ABCDE1234F | UPI: ananya@okhdfcbank"
redacted, mapping = redact(text)
# redacted -> "Applicant: [PERSON_1] | PAN: [PAN_1] | UPI: [UPI_1]"

ai_reply = "Approved KYC for [PERSON_1] (PAN [PAN_1])."
print(restore(ai_reply, mapping))
# -> "Approved KYC for Dr. Ananya Rao (PAN ABCDE1234F)."
```

### 3. Run with Docker

```powershell
docker build -t pii-shield .
docker run --rm -p 7860:7860 pii-shield
```

Uses CPU-only PyTorch, pre-caches GLiNER + tokenizer at image build time, runs as non-root user `piishield` (`UID 10001`), and enforces `HF_HUB_OFFLINE=1` at runtime.

### 4. Run Test Suites

```powershell
# Python unit, validator, merge, dataset, package, extension-bridge, and FastAPI tests (257 tests)
python -m pytest -q

# Chrome Extension Manifest V3, failover, multi-turn mapping, and DOM suite (Node.js 18+)
node --test extension/tests/extension.test.js

# Validate synthetic dataset span offsets and schema integrity
python -m eval.validate_dataset --split dev
python -m eval.validate_dataset --split realistic
```

---

## API Reference

| Method & Path | Description |
|---|---|
| `POST /redact` | Body: `{"text": "..."}` (max 20,000 chars) → returns `{"redacted": "...", "spans": [...], "mapping": {...}}`. Runs NER off the event loop via `asyncio.to_thread`. |
| `POST /restore` | Body: `{"text": "...", "mapping": {...}}` → returns `{"restored": "..."}`. Handles case/whitespace placeholder mutations from LLMs. |
| `GET /health` | Returns `{"status": "ok", "model_loaded": true}`. |
| `GET /metrics` | Returns anonymous in-memory aggregate counters (`redact_requests`, `spans_by_label`, latency ms, HTTP error counts—never text or PII). |
| `GET /docs` | Interactive OpenAPI 3.1 / Swagger documentation. |

Per-client sliding-window rate limiting returns `HTTP 429` with a `Retry-After` header when exceeded.

---

## Cloud Deployment

### Google Cloud Run (Primary)

Uses [`Dockerfile`](Dockerfile), [`cloudbuild.yaml`](cloudbuild.yaml), and [`deploy/cloud_run_deploy.ps1`](deploy/cloud_run_deploy.ps1) (or `.sh` on Linux/macOS):

```powershell
.\deploy\cloud_run_deploy.ps1 -ProjectId "your-gcp-project-id" -Region "us-central1"
```

### Modal (Serverless Backup)

Uses [`modal_app.py`](modal_app.py) in an isolated `.venv-modal` environment so both Cloud Run and Modal can stay live simultaneously:

```powershell
python -m venv .venv-modal
.\.venv-modal\Scripts\Activate.ps1
python -m pip install modal
$env:PYTHONUTF8 = "1"
python -m modal setup
python -m modal deploy modal_app.py
```

---

## Project Structure

```text
pii-shield/
├── api/
│   └── main.py                 # FastAPI app (/redact, /restore, /health, /metrics, /docs, UI & .zip)
├── engine/
│   ├── constants.py            # 80+ NPCI UPI handles, 100+ Indian cities, RTO codes, NER blocklists
│   ├── validators.py           # Verhoeff Aadhaar, PAN, Phone, UPI, Pincode, DOB, Passport, EPIC, DL, Bank, IP
│   ├── regex_layer.py          # Context-aware structured detector across 12 identifier types
│   ├── rules.py                # Honorifics, sign-offs, "Surname, First", Indian street/plot/sector addresses
│   ├── ner.py                  # GLiNER wrapper + prefix trimming, false-alarm filter & address assembly
│   ├── merge.py                # Priority overlap resolution (regex > rules > ner)
│   └── detect.py               # Unified hybrid detection pipeline
├── extension/                  # Manifest V3 Chrome Extension (ChatGPT, Gemini, Claude + toolbar popup)
│   ├── manifest.json
│   ├── background.js           # Service worker: Cloud Run -> Modal failover + chrome.storage.session
│   ├── shared.js               # Site adapters, selective redaction, multi-turn mapping & DOM restorer
│   ├── content.js / content.css# Floating Shield dock, inline review popover & safe reply restore chips
│   ├── popup.html / .js / .css # Toolbar Quick Redact/Restore & backend selector
│   └── tests/extension.test.js # Node.js test suite (E12)
├── pii_shield/                 # pip-installable library facade (`import pii_shield`)
├── web/                        # Responsive dark-mode Web UI (selective spans, confidence scores, history)
├── eval/                       # dev.jsonl, locked test.jsonl, 540-item realistic.jsonl, run_eval.py, results.md
├── deploy/                     # Build-time HF model cacher, Cloud Run scripts & extension .zip packager
├── docs/                       # Architecture plan, dataset/eval specs, demo script & improvement log
├── tests/                      # 257 pytest unit, property, API, dataset & extension tests
├── .github/workflows/ci.yml    # Automated CI for Python 3.11 + Node.js MV3 extension tests
├── redactor.py                 # Consistent [LABEL_N] placeholder assignment & resilient restoration
├── Dockerfile                  # Offline-ready non-root CPU container (port 7860)
├── cloudbuild.yaml             # Layer-cached Artifact Registry + Cloud Run pipeline
├── modal_app.py                # Serverless Modal ASGI deployment
└── pyproject.toml              # Package metadata & optional dependency extras
```
