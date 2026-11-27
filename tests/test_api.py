"""HTTP boundary tests use FakeNer and never download the model."""

import asyncio
import json
import threading

import httpx
from fastapi.testclient import TestClient

from api.main import create_app
from engine.ner import FakeNer


def test_redact_then_restore_round_trip_with_fake_ner():
    app = create_app(ner_detector=FakeNer({}))
    with TestClient(app) as client:
        response = client.post("/redact", json={"text": "Name: Ananya Rao"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["redacted"] == "Name: [PERSON_1]"
        assert payload["mapping"] == {"[PERSON_1]": "Ananya Rao"}
        assert payload["spans"][0]["text"] == "Ananya Rao"
        restored = client.post(
            "/restore",
            json={"text": payload["redacted"], "mapping": payload["mapping"]},
        )
        assert restored.status_code == 200
        assert restored.json() == {"restored": "Name: Ananya Rao"}


def test_oversized_input_is_rejected():
    app = create_app(ner_detector=FakeNer({}))
    with TestClient(app) as client:
        response = client.post("/redact", json={"text": "x" * 20_001})
    assert response.status_code == 413
    assert response.json() == {"detail": "Text exceeds the 20,000 character limit."}


def test_request_body_and_detected_text_are_not_logged(caplog):
    raw_text = "Name: Synthetic Example; call 9845012345"
    app = create_app(ner_detector=FakeNer({}))
    with caplog.at_level("DEBUG"):
        with TestClient(app) as client:
            response = client.post("/redact", json={"text": raw_text})
    assert response.status_code == 200
    assert raw_text not in caplog.text
    assert "Synthetic Example" not in caplog.text
    assert "9845012345" not in caplog.text


def test_health_reports_status_and_model_readiness_for_injected_detector():
    app = create_app(ner_detector=FakeNer({}))
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "model_loaded": False}


def test_app_serves_the_ui_from_the_same_origin():
    app = create_app(ner_detector=FakeNer({}))
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/app.js")
        stylesheet = client.get("/style.css")
    assert page.status_code == script.status_code == stylesheet.status_code == 200
    assert "PII Shield" in page.text
    assert 'id="session-history"' in page.text
    assert "currentMapping" in script.text
    assert "buildRedactionFromSpans" in script.text
    assert "HISTORY_STORAGE_KEY" in script.text
    assert ".entity-person" in stylesheet.text
    assert ".entity-disabled" in stylesheet.text


def test_redact_runs_detection_off_the_event_loop_thread():
    loop_thread_id = None
    detector_thread_id = None

    class ThreadCheckingNer(FakeNer):
        def detect(self, text: str):
            nonlocal detector_thread_id
            detector_thread_id = threading.get_ident()
            return super().detect(text)

    app = create_app(ner_detector=ThreadCheckingNer({}))

    async def exercise():
        nonlocal loop_thread_id
        loop_thread_id = threading.get_ident()
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.post("/redact", json={"text": "Name: Ananya Rao"})
                assert response.status_code == 200

    asyncio.run(exercise())
    assert detector_thread_id is not None
    assert detector_thread_id != loop_thread_id


def test_rate_limit_blocks_excess_requests_and_recovers():
    now = 100.0
    app = create_app(
        ner_detector=FakeNer({}),
        rate_limit_requests=2,
        rate_limit_window_seconds=60.0,
        clock=lambda: now,
    )
    with TestClient(app) as client:
        assert client.post("/redact", json={"text": "Name: Ananya Rao"}).status_code == 200
        assert client.post("/restore", json={"text": "hi", "mapping": {}}).status_code == 200
        blocked = client.post("/redact", json={"text": "Name: Ananya Rao"})
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
        # Health and static UI routes remain accessible
        assert client.get("/health").status_code == 200
        # Advancing past the window resets the limit
        now += 61.0
        assert client.post("/redact", json={"text": "Name: Ananya Rao"}).status_code == 200


def test_metrics_tracks_aggregate_counts_without_leaking_pii():
    now = 10.0
    app = create_app(
        ner_detector=FakeNer({}),
        rate_limit_requests=3,
        rate_limit_window_seconds=60.0,
        clock=lambda: now,
    )
    raw_text = "Name: Ananya Rao; call 9845012345"
    with TestClient(app) as client:
        initial = client.get("/metrics")
        assert initial.status_code == 200
        assert initial.json()["redact_requests"] == 0

        res = client.post("/redact", json={"text": raw_text})
        assert res.status_code == 200
        payload = res.json()

        assert client.post(
            "/restore",
            json={"text": payload["redacted"], "mapping": payload["mapping"]},
        ).status_code == 200

        # Oversized request -> 413 error counted
        assert client.post("/redact", json={"text": "x" * 20_001}).status_code == 413
        # Rate-limited request -> 429 error counted (3 hits already used on /redact + /restore)
        assert client.post("/redact", json={"text": "Name: Ananya Rao"}).status_code == 429
        # Advance past rate-limit window, then trigger validation error -> 422 error counted
        now += 61.0
        assert client.post("/redact", json={"wrong": 1}).status_code == 422

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        stats = metrics.json()
        assert stats["redact_requests"] == 1
        assert stats["restore_requests"] == 1
        assert stats["spans_detected_total"] == 2
        assert stats["spans_by_label"] == {"PERSON": 1, "PHONE": 1}
        assert stats["errors_by_status"] == {"413": 1, "422": 1, "429": 1}
        assert stats["redact_latency_ms_avg"] >= 0.0
        assert stats["redact_latency_ms_max"] >= 0.0

        serialised = json.dumps(stats)
        assert "Ananya Rao" not in serialised
        assert "9845012345" not in serialised
