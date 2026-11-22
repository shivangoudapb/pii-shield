"""HTTP boundary tests use FakeNer and never download the model."""

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
    assert "currentMapping" in script.text
    assert ".entity-person" in stylesheet.text
