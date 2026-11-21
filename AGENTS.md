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
Python 3.11, FastAPI, Pydantic, pytest, Hugging Face Transformers (NER), plain HTML/JS frontend served by FastAPI. Docker for deployment (port 7860).

## Structure
```
pii-shield/
  engine/
    validators.py   # verhoeff, aadhaar, pan, phone, upi, pincode, email
    regex_layer.py  # structured detection using validators
    rules.py        # titles (Mr/Mrs/Dr/Shri), "Name:" fields, sign-offs
    ner.py          # model wrapper -> spans
    merge.py        # overlap resolution
    detect.py       # runs all layers -> merged spans
  redactor.py       # redact(text) -> (redacted, mapping); restore(text, mapping)
  api/main.py       # FastAPI app
  web/              # index.html, app.js, style.css
  eval/             # dev.jsonl, test.jsonl, run_eval.py, results.md
  tests/
  Dockerfile
  README.md
```

## Span schema (shared by all layers)
```python
{"start": int, "end": int, "label": str, "text": str, "source": "regex|rules|ner", "score": float}
```
Labels: `PERSON, LOCATION, PHONE, EMAIL, AADHAAR, PAN, UPI, PINCODE`
(`ADDRESS` may be merged into `LOCATION` for simplicity. See DATASET.md.)

## Validation rules
- **Aadhaar:** 12 digits, first digit 2-9, passes Verhoeff checksum. May be written with spaces/hyphens in groups of 4.
- **PAN:** `[A-Z]{5}[0-9]{4}[A-Z]`.
- **Phone:** Indian mobile, 10 digits starting 6-9, optional `+91`, `91`, or `0` prefix, optional spaces/hyphens.
- **UPI:** `handle@provider` (e.g. `name@okhdfcbank`). Must not be confused with an email. Check the provider against a known list of UPI handles.
- **Pincode:** 6 digits, first digit 1-9, only flagged when in an address-like context (to avoid flagging random 6-digit numbers such as OTPs or order numbers).
- **Email:** standard pattern.

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
- Hugging Face Spaces, Docker SDK, app on port 7860.
- Download the NER model during `docker build`, not at runtime.
- Serve static UI from FastAPI so there is a single service.
