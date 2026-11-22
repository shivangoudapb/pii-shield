"""FastAPI service for in-memory PII redaction and restoration."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict

from engine.detect import detect
from engine.ner import DEFAULT_MODEL_NAME, GlinerNer, NerDetector
from redactor import _redact_spans, restore as restore_text

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "eval" / "config.json"
WEB_PATH = ROOT / "web"
MAX_TEXT_CHARS = 20_000


class RedactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    mapping: dict[str, str]


def _load_frozen_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def create_app(ner_detector: NerDetector | None = None) -> FastAPI:
    """Create the app; tests can inject FakeNer and avoid model loading."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.model_loaded = False
        if ner_detector is None:
            config = _load_frozen_config()
            detector = GlinerNer(
                model_name=config.get("model_name", DEFAULT_MODEL_NAME),
                labels=config["labels"],
                label_mapping=config.get("label_mapping"),
                threshold=float(config["threshold"]),
            )
            # Use only a fixed, synthetic warm-up string; the global GLiNER
            # cache makes all later requests reuse this startup-loaded model.
            detector.detect("PII Shield startup warm-up.")
            app.state.model_loaded = True
            app.state.ner_score_threshold = float(config["ner_score_threshold"])
            app.state.config = config
            app.state.ner_detector = detector
        else:
            app.state.ner_detector = ner_detector
            app.state.ner_score_threshold = 0.5
            app.state.config = None
        yield

    app = FastAPI(title="PII Shield", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(request, exc: RequestValidationError):
        # Pydantic's default 422 response can echo the submitted input value.
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    @app.get("/health")
    async def health() -> dict[str, bool | str]:
        return {"status": "ok", "model_loaded": bool(app.state.model_loaded)}

    @app.post("/redact")
    async def redact(request: RedactRequest) -> dict[str, Any]:
        if len(request.text) > MAX_TEXT_CHARS:
            raise HTTPException(status_code=413, detail="Text exceeds the 20,000 character limit.")
        spans = detect(
            request.text,
            app.state.ner_detector,
            ner_score_threshold=app.state.ner_score_threshold,
        )
        redacted, mapping = _redact_spans(request.text, spans)
        return {
            "redacted": redacted,
            "spans": [asdict(span) for span in spans],
            "mapping": mapping,
        }

    @app.post("/restore")
    async def restore(request: RestoreRequest) -> dict[str, str]:
        if len(request.text) > MAX_TEXT_CHARS:
            raise HTTPException(status_code=413, detail="Text exceeds the 20,000 character limit.")
        return {"restored": restore_text(request.text, request.mapping)}

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_PATH / "index.html")

    @app.get("/app.js", include_in_schema=False)
    async def app_js() -> FileResponse:
        return FileResponse(WEB_PATH / "app.js", media_type="text/javascript")

    @app.get("/style.css", include_in_schema=False)
    async def stylesheet() -> FileResponse:
        return FileResponse(WEB_PATH / "style.css", media_type="text/css")

    return app


app = create_app()
