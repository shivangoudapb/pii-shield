# PII Shield

India-aware, reversible redaction for personal details in AI chats.

**Live demo:** [https://bhavihalshivu--pii-shield-web-app.us-east.modal.run](https://bhavihalshivu--pii-shield-web-app.us-east.modal.run)

The first visit after idle can take up to a minute while a container starts and loads the model; one cold health request measured about 17 seconds.

## Problem and solution

People often paste resumes, customer chats, and forms into AI tools. PII Shield detects selected Indian personal details, replaces them with consistent placeholders, and restores them in the AI reply using a mapping kept in the browser tab.

## How it works

```text
Input text
   |
   +--> Regex + validators ----+
   +--> Name/address rules ----+--> Merge by source priority --> Redactor --> Placeholder text
   +--> GLiNER ----------------+
                                                               |                |
                                                               +--> mapping -----+

Placeholder text --> LLM (outside this app) --> reply with placeholders
                                              --> /restore with mapping --> restored reply
```

The redactor sends text to the selected detector layers, applies the shared span priorities, then creates placeholders. The mapping is returned to the browser; it is not stored server-side. In the browser flow, the text goes to `/redact`, and the mapping is sent back only with `/restore`.

## Test-set results

Evaluation used 100 synthetic test items. **A** is regex + rules, **B** is GLiNER only, and **C** is the hybrid pipeline. Each cell shows precision / recall / F1.

### Exact match

| Label | A: regex + rules | B: GLiNER only | C: hybrid |
|---|---:|---:|---:|
| PERSON | 0.750 / 0.078 / 0.141 | 0.860 / 0.741 / 0.796 | 0.860 / 0.741 / 0.796 |
| LOCATION | 0.000 / 0.000 / 0.000 | 0.258 / 0.444 / 0.327 | 0.400 / 0.444 / 0.421 |
| PHONE | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| EMAIL | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| AADHAAR | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| PAN | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| UPI | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| PINCODE | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| **Overall (micro)** | **0.977 / 0.500 / 0.661** | **0.718 / 0.376 / 0.493** | **0.890 / 0.840 / 0.864** |

### Relaxed match

Relaxed matches require the same label and overlap of at least 50% of the longer span.

| Label | A: regex + rules | B: GLiNER only | C: hybrid |
|---|---:|---:|---:|
| PERSON | 0.750 / 0.078 / 0.141 | 0.930 / 0.802 / 0.861 | 0.930 / 0.802 / 0.861 |
| LOCATION | 0.000 / 0.000 / 0.000 | 0.484 / 0.833 / 0.612 | 0.550 / 0.611 / 0.579 |
| PHONE | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| EMAIL | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| AADHAAR | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| PAN | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| UPI | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| PINCODE | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 |
| **Overall (micro)** | **0.977 / 0.500 / 0.661** | **0.824 / 0.432 / 0.567** | **0.932 / 0.880 / 0.905** |

GLiNER-only micro scores are not directly comparable with A and C: GLiNER only predicts PERSON and LOCATION, while the structured layer also detects phone, email, Aadhaar, PAN, UPI, and pincode. The full report is in [eval/results.md](eval/results.md).

The test set contains 116 PERSON, 18 LOCATION, 29 PHONE, 34 EMAIL, 9 AADHAAR, 17 PAN, 15 UPI, and 12 PINCODE spans. Hybrid false-alarm rate on no-PII items was 0.000; hybrid round-trip rate was 1.000.

Test-set hybrid PERSON recall is **0.741**: about one in four expected names was missed. LOCATION exact recall is **0.444**. Test-set hybrid latency in the evaluation process was median **212.45 ms/item** and p95 **253.86 ms/item**; peak process RAM with the model loaded was **2729.2 MiB**. These measurements are from the evaluation run, not a promise about hosted response time.

## Limitations and privacy

- Detection is imperfect. The test-set PERSON recall was 0.741, and location/address detection is weak: street and locality spans are often missed or only partly detected.
- The error report shows common-word name misses, misses for surnames following initials, lower-case name boundary errors, partial address/name boundaries, and some location-like words flagged outside address contexts. Some company-lookalike-tagged items have neighboring name-boundary errors; the report has no separate regional-name errors. See [eval/errors.md](eval/errors.md) for the grouped cases.
- The data is synthetic, generated from a small set of templates, and the locked test set has only 100 items. Scores are indicative, not a guarantee of results on real text.
- The dataset and evaluation cover English and Roman-script text only; native-script text is not evaluated.
- The hosted demo sends submitted text to a Modal server in the US East region. The app processes it in memory and does not store or log it. The placeholder mapping is returned to the browser and is not saved server-side. This reduces exposure; it does not guarantee privacy or legal compliance. Review the redacted result before sharing it with an AI.
- To keep processing on your own machine, run the app locally. A first local start downloads the model and tokenizer; subsequent processing happens on the local server.

## Dataset

`eval/generate_dataset.py` deterministically generates synthetic names, identifiers, addresses, and template-based messages. Dataset v2 expanded the name pools and contexts, added varied casing and formatting, repeated-name cases, lookalike negatives, and eight templates per context. There are 60 development items and 100 test items, with 10% no-PII items in each split.

The v1 templates were too narrow, so both splits were regenerated once on 2026-11-22 with explicit authorization. The test split is locked and must not be changed or used for tuning. Its SHA-256 is:

```text
2A60BFF3746E66AFA37947F0FFFDDC631E468E10BF13D01E47BECD0F6D417F88
```

The regeneration and lock are recorded in [eval/DATASET_NOTES.md](eval/DATASET_NOTES.md). The validator checks annotation offsets and overlap without running a detector: `python -m eval.validate_dataset --split all`.

## Run locally

Use Python 3.11. Install dependencies and start the app:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 7860 --no-access-log
```

Open `http://127.0.0.1:7860`. On its first start, GLiNER and its tokenizer are downloaded from Hugging Face. Text is then processed by the local server.

### Run with Docker

```powershell
docker build -t pii-shield .
docker run --rm -p 7860:7860 pii-shield
```

The image uses CPU-only PyTorch, downloads the model during the build, runs as a non-root user, and starts offline. Open `http://localhost:7860`.

### Run tests

```powershell
python -m pytest -q
```

The default run skips the model integration test marked `slow`.

## Deploy on Modal

Create and activate the separate Modal environment, install the CLI, authenticate, and deploy:

```powershell
python -m venv .venv-modal
.\.venv-modal\Scripts\Activate.ps1
python -m pip install modal
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
python -m modal setup
python -m modal deploy modal_app.py
```

Modal uses CPU-only PyTorch, downloads GLiNER and its tokenizer while building the image, and runs with Hugging Face offline mode enabled. The app scales to zero after idle time, so the next request starts a container and loads the model. Hugging Face Spaces and Cloud Run were considered but are not used deployment routes for this project.

## Project structure

```text
api/                  FastAPI endpoints and static UI serving
engine/               Validators, regex/rules/NER detection, span merge
web/                  Single-page HTML, CSS, and browser-side flow
eval/                 Synthetic data, frozen config, evaluation, reports
deploy/               Build-time model/tokenizer download helper
tests/                Unit, integration, metric, and API tests
redactor.py           Placeholder creation and restoration
modal_app.py          Modal image and ASGI deployment wrapper
Dockerfile            Local/container deployment image
```

## What I’d do next

- Fine-tune or adapt NER using more Indian names and varied Roman-script writing.
- Improve street- and locality-level address detection.
- Explore in-browser inference so text need not go to a hosted server.
- Add native-script support and evaluate it with a larger, independently reviewed dataset.
