# Implementation Plan (Sat 21 Nov → Mon 23 Nov 2026)

Submission = deployed URL + GitHub URL + 2-minute demo recording.
Priority order if time runs short: **evaluation > working deployed demo > UI polish > browser/ONNX version.**

## Phase 0: Feasibility spike (Sat, ~2h). GO / NO-GO
- [ ] Write 20 realistic Indian sentences (names, addresses, phones)
- [ ] Run `dslim/bert-base-NER` and GLiNER (a PII/multi-label variant) on them in Colab or locally
- [ ] Eyeball results: does at least one catch most names?
- [ ] Check model size and RAM use (matters for deployment)
- **Decision:** if both fail badly → rules-heavy approach + light fine-tune, or rethink idea tonight

## Phase 1: Dataset + structured layer (Sat evening)
- [ ] Create repo, folder structure, `AGENTS.md` (see AGENTS.md)
- [ ] Build labelled dataset ~150-200 sentences (see DATASET.md)
- [ ] Split: dev (~60) and locked test (~100). Do not tune on test.
- [ ] Validators with unit tests FIRST: Verhoeff/Aadhaar, PAN, phone, email, UPI, pincode
- [ ] Regex layer passing tests

## Phase 2: Engine core (Sun morning)
- [ ] NER wrapper (returns spans in the shared span schema)
- [ ] Rules layer (titles, "Name:" fields, sign-offs)
- [ ] Merge logic (overlap resolution, structured > rules > NER)
- [ ] Redactor/restorer with consistent placeholders
- [ ] Tests: same entity twice → same placeholder; invalid Aadhaar not flagged; `restore(redact(x)) == x` on entire dataset; overlap cases

## Phase 3: Evaluation (Sun afternoon): the core of the submission
- [ ] `eval/run_eval.py` computes precision/recall/F1 per entity type on test set
- [ ] Compare three setups: regex-only, NER-only, hybrid
- [ ] Error analysis: collect real misses/false alarms, group them (see EVAL.md)
- [ ] Optional, only if NER is clearly weak and time remains: light fine-tune on Colab

## Phase 4: API + UI (Sun evening)
- [ ] FastAPI: `POST /redact`, `POST /restore`, `GET /health`
- [ ] Single-page UI: input box → highlighted spans + redacted output; second box for restore
- [ ] Guard: raw text is never logged or persisted; mapping returned to client, not stored server-side
- [ ] Example buttons ("Load sample resume", "Load sample chat") for the demo

## Phase 5: Deployment (Sun night, do NOT leave for Monday)
Recommended: **Hugging Face Spaces (Docker SDK)**, since a free CPU Space has far more RAM than typical free web-service tiers. Verify current limits on their pricing page.
- [ ] Dockerfile: install deps, download model **at build time** so there is no cold-start download
- [ ] App listens on port 7860 and serves both API and static UI
- [ ] Test the deployed URL from a different device
- [ ] Fallback if model is too heavy: quantised ONNX via `onnxruntime`, or a smaller model
- [ ] Note free Spaces may sleep when idle. Open the URL shortly before submitting to wake it, and mention this in the README.

## Phase 6: README, demo, submit (Mon morning)
- [ ] README: problem, architecture diagram (simple), results table, limitations, how to run locally, deployed URL
- [ ] Record 2-minute demo (script below)
- [ ] Final check: repo public, URL works, video link opens
- [ ] Submit, ideally with a few hours to spare before deadline

## Stretch (only if everything above is done)
- [ ] In-browser inference (ONNX + Transformers.js) so nothing leaves the device
- [ ] Light fine-tune and before/after comparison

## 2-minute demo script
- **0:00-0:20:** The problem. "People paste resumes and customer chats into AI tools. That data leaves their control. Here's a tool that fixes it."
- **0:20-1:15:** Live demo. Paste a realistic sample → show highlighted detections → copy redacted text → paste a (pre-prepared) AI reply → restore. Show that an invalid Aadhaar-lookalike number is NOT flagged.
- **1:15-1:45:** Results. Show the table: regex-only vs NER-only vs hybrid. Name one honest failure case.
- **1:45-2:00:** Limitations and what's next (in-browser mode, more languages).
