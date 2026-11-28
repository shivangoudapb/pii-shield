# AGENTS.md: Spec for coding agents (Codex / Cursor / Claude Code)

## Project
PII Shield: detects Indian personal data in text, replaces it with consistent placeholders, and restores it in an AI's reply.

## Hard rules
1. **Never log, print, or persist raw user text or detected PII.** No request-body logging, no analytics, no disk writes of input. Use in-memory processing only. The placeholder↔value mapping is returned to the client and not stored server-side.
2. Work in small steps. **Write tests before implementation** for validators, merge logic and redactor.
3. Don't tune or look at the locked test set (`eval/test.jsonl`) while developing. Use `eval/dev.jsonl`.
4. Only use synthetic data. No real people's information anywhere in the repo.
5. Keep dependencies minimal. Pin versions in `requirements.txt`.

## Stack
Python 3.11, FastAPI, Pydantic, pytest, Hugging Face Transformers / GLiNER (NER), plain HTML/JS frontend served by FastAPI, Manifest V3 Chrome Extension (`extension/`). Docker for deployment on Google Cloud Run (port 7860) and Modal (`modal_app.py`).

## Structure
```
pii-shield/
  engine/
    validators.py   # verhoeff, aadhaar, pan, phone, upi, pincode, email, dob, passport, voter_id, dl, bank, ip
    regex_layer.py  # structured detection using validators
    rules.py        # titles (Mr/Mrs/Dr/Shri), "Name:" fields, sign-offs, structured Indian addresses
    ner.py          # GLiNER wrapper -> spans + prefix/blocklist/address post-processing
    merge.py        # overlap resolution
    detect.py       # runs all layers -> merged spans
  pii_shield/       # pip-installable library facade
  redactor.py       # redact(text) -> (redacted, mapping); restore(text, mapping)
  api/main.py       # FastAPI app (/redact, /restore, /health, /metrics, /docs, static UI)
  web/              # index.html, app.js, style.css, favicon.png
  extension/        # Manifest V3 Chrome Extension + Node test suite (E12)
  deploy/           # Cloud Run deploy scripts, model cache helper, extension packager
  eval/             # dev.jsonl, test.jsonl, realistic.jsonl, run_eval.py, results.md
  tests/
  Dockerfile
  cloudbuild.yaml
  modal_app.py
  pyproject.toml
  README.md
```

## Span schema (shared by all layers)
```python
{"start": int, "end": int, "label": str, "text": str, "source": "regex|rules|ner", "score": float}
```
Labels (14): `PERSON, LOCATION, PHONE, EMAIL, AADHAAR, PAN, UPI, PINCODE, DOB, PASSPORT, VOTER_ID, DRIVING_LICENSE, BANK_ACCOUNT, IP_ADDRESS`
(`ADDRESS` is merged into `LOCATION` for simplicity. See DATASET.md.)

## Validation rules
- **Aadhaar:** 12 digits, first digit 2-9, passes Verhoeff checksum. May be written with spaces/hyphens in groups of 4.
- **PAN:** `[A-Z]{5}[0-9]{4}[A-Z]`.
- **Phone:** Indian mobile, 10 digits starting 6-9, optional `+91`, `91`, or `0` prefix, optional spaces/hyphens.
- **UPI:** `handle@provider` (e.g. `name@okhdfcbank`). Must not be confused with an email. Check the provider against 80+ NPCI UPI handles.
- **Pincode:** 6 digits, first digit 1-9, only flagged when in an address-like context (to avoid flagging random 6-digit numbers such as OTPs or order numbers).
- **Email:** standard pattern.
- **DOB:** explicit date-of-birth context (`DOB`, `Date of Birth`, `Born on`) + valid calendar date in 1900–2025.
- **Passport:** Indian passport `[A-Z][1-9][0-9]{6}` in passport context.
- **Voter ID (EPIC):** `[A-Z]{3}[0-9]{7}` (not followed by PAN trailing letter).
- **Driving License:** valid Indian RTO state/UT code (`AN`–`WB`) + 2-digit RTO + 4-digit year + 7-digit serial.
- **Bank Account:** 9–18 digits only when preceded by explicit banking context (`A/c No`, `Account No`, `IFSC`, `Beneficiary account`).
- **IP Address:** valid IPv4 (`0–255` octets, non-version context) and IPv6 addresses.

## Merge priority
When spans overlap: **regex (validated) > rules > NER**. If same source, prefer the longer span. Drop NER spans below a configurable score threshold.

## Redactor behaviour
- Placeholder format: `[LABEL_N]` (e.g. `[PERSON_1]`).
- Same entity text (case-insensitive, whitespace-normalised) → same placeholder within one session.
- `restore(text, mapping)` replaces placeholders back, including when the LLM changes surrounding punctuation or case of the placeholder brackets minimally. Unknown placeholders are left untouched.
- Property to test: `restore(*redact(x)) == x` for every dataset item.

## API
- `POST /redact` body `{"text": str}` → `{"redacted": str, "spans": [...], "mapping": {...}}`
- `POST /restore` body `{"text": str, "mapping": {...}}` → `{"restored": str}`
- `GET /health` → `{"status": "ok"}`
- Limit input length (e.g. 20k chars). No request logging of bodies.

## Required tests (minimum)
- Verhoeff: valid and invalid Aadhaar examples; random 12-digit numbers rejected
- PAN, phone, UPI vs email, pincode context
- Same name twice → same placeholder
- Overlap: a phone number inside a longer NER span resolves correctly
- Round trip on the entire dev and test set
- API: redact → restore returns original; oversized input rejected

## Definition of done per phase
Tests pass, no raw text in logs, code is understandable by the project owner (they must be able to explain every layer in an interview).

## Deployment notes
- Google Cloud Run (primary, port 7860 via `Dockerfile` + `cloudbuild.yaml`) and Modal (`modal_app.py` backup).
- Download the NER model during image build (`deploy/download_model.py`), not at runtime.
- Serve static UI from FastAPI so there is a single service.
