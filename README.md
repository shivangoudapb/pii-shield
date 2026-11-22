# PII Shield

PII Shield detects common Indian personal details in text, replaces them with consistent placeholders, and restores them in a reply. Detection combines validated patterns, simple text rules, and GLiNER.

## Privacy model

Requests are processed in memory by the server and are not written to disk or included in application logs. The placeholder mapping is returned to the browser and is kept only in that browser tab until a reply is restored. A hosted deployment receives the text you submit; run PII Shield on your own computer if you want the text to stay on your device.

## Run locally

Use Python 3.11. Install dependencies and start the app:

```sh
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 7860 --no-access-log
```

The first local startup downloads the configured GLiNER model and tokenizer from Hugging Face. The API loads the model during application startup. Open `http://127.0.0.1:7860` in a browser.

## API

- `POST /redact` with `{"text": "..."}` returns redacted text, detected spans, and a call-local mapping.
- `POST /restore` with `{"text": "...", "mapping": {...}}` restores known placeholders.
- `GET /health` reports service and model readiness.

Input text is limited to 20,000 characters. The service disables Uvicorn access logs.

## Evaluation

See [eval/results.md](eval/results.md) for the frozen synthetic evaluation and [eval/errors.md](eval/errors.md) for hybrid test-set error analysis. The small synthetic dataset is indicative only and is not a guarantee of performance on real text.

## Docker

Build and run with Docker:

```sh
docker build -t pii-shield .
docker run --rm -p 7860:7860 pii-shield
```

The image downloads model files at build time, then runs with Hugging Face offline mode enabled. `PORT` defaults to `7860` and can be changed by the hosting platform.

## Deploy on Modal

Create and activate the separate Modal environment, install the Modal CLI, authenticate, and deploy:

```powershell
python -m venv .venv-modal
.\.venv-modal\Scripts\Activate.ps1
python -m pip install modal
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
python -m modal setup
python -m modal deploy modal_app.py
```

The Modal image installs the pinned project dependencies with CPU-only PyTorch and caches GLiNER plus its tokenizer during the image build. Containers run with Hugging Face offline mode enabled. With scale-to-zero enabled, the first request after an idle period is slower while a container starts and loads the model.
