"""FastAPI service for in-memory PII redaction and restoration."""

from __future__ import annotations

import asyncio
import json
import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
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


class SlidingWindowRateLimiter:
    """In-memory per-client sliding-window rate limiter."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        """Record a hit or return whole seconds to wait if rate-limited."""
        if self.max_requests <= 0:
            return None
        now = self.clock()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._hits[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.max_requests:
                retry_after = max(1, math.ceil(self.window_seconds - (now - timestamps[0])))
                return retry_after
            timestamps.append(now)
        return None


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class InMemoryMetrics:
    """Privacy-safe aggregate counters kept strictly in memory (never raw text or PII)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._redact_requests = 0
        self._restore_requests = 0
        self._spans_total = 0
        self._spans_by_label: dict[str, int] = defaultdict(int)
        self._errors_by_status: dict[str, int] = defaultdict(int)
        self._redact_latency_ms_sum = 0.0
        self._redact_latency_ms_max = 0.0

    def record_redact(self, spans: list[Any], elapsed_ms: float) -> None:
        with self._lock:
            self._redact_requests += 1
            self._spans_total += len(spans)
            for span in spans:
                self._spans_by_label[span.label] += 1
            self._redact_latency_ms_sum += elapsed_ms
            if elapsed_ms > self._redact_latency_ms_max:
                self._redact_latency_ms_max = elapsed_ms

    def record_restore(self) -> None:
        with self._lock:
            self._restore_requests += 1

    def record_error(self, status_code: int) -> None:
        with self._lock:
            self._errors_by_status[str(status_code)] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_ms = (
                round(self._redact_latency_ms_sum / self._redact_requests, 2)
                if self._redact_requests
                else 0.0
            )
            return {
                "redact_requests": self._redact_requests,
                "restore_requests": self._restore_requests,
                "spans_detected_total": self._spans_total,
                "spans_by_label": dict(sorted(self._spans_by_label.items())),
                "errors_by_status": dict(sorted(self._errors_by_status.items())),
                "redact_latency_ms_avg": avg_ms,
                "redact_latency_ms_max": round(self._redact_latency_ms_max, 2),
            }


def create_app(
    ner_detector: NerDetector | None = None,
    *,
    rate_limit_requests: int = 30,
    rate_limit_window_seconds: float = 60.0,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    """Create the app; tests can inject FakeNer and avoid model loading."""

    limiter = SlidingWindowRateLimiter(
        max_requests=rate_limit_requests,
        window_seconds=rate_limit_window_seconds,
        clock=clock,
    )
    metrics = InMemoryMetrics()

    def enforce_rate_limit(request: Request) -> None:
        retry_after = limiter.check(_client_key(request))
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait before trying again.",
                headers={"Retry-After": str(retry_after)},
            )

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

    @app.middleware("http")
    async def track_api_errors(request: Request, call_next):
        response = await call_next(request)
        if request.url.path in {"/redact", "/restore"} and response.status_code >= 400:
            metrics.record_error(response.status_code)
        return response

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(request, exc: RequestValidationError):
        # Pydantic's default 422 response can echo the submitted input value.
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    @app.get("/health")
    async def health() -> dict[str, bool | str]:
        return {"status": "ok", "model_loaded": bool(app.state.model_loaded)}

    @app.get("/metrics")
    async def get_metrics() -> dict[str, Any]:
        return metrics.snapshot()

    @app.post("/redact", dependencies=[Depends(enforce_rate_limit)])
    async def redact(request: RedactRequest) -> dict[str, Any]:
        if len(request.text) > MAX_TEXT_CHARS:
            raise HTTPException(status_code=413, detail="Text exceeds the 20,000 character limit.")
        started = time.perf_counter()
        spans = await asyncio.to_thread(
            detect,
            request.text,
            app.state.ner_detector,
            ner_score_threshold=app.state.ner_score_threshold,
        )
        redacted, mapping = _redact_spans(request.text, spans)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        metrics.record_redact(spans, elapsed_ms)
        return {
            "redacted": redacted,
            "spans": [asdict(span) for span in spans],
            "mapping": mapping,
        }

    @app.post("/restore", dependencies=[Depends(enforce_rate_limit)])
    async def restore(request: RestoreRequest) -> dict[str, str]:
        if len(request.text) > MAX_TEXT_CHARS:
            raise HTTPException(status_code=413, detail="Text exceeds the 20,000 character limit.")
        restored = restore_text(request.text, request.mapping)
        metrics.record_restore()
        return {"restored": restored}

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
