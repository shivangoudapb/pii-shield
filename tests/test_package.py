"""Tests for the pip-installable pii_shield package facade and pyproject metadata."""

from pathlib import Path
import tomllib


def test_pyproject_toml_defines_package_metadata_and_extras():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    assert pyproject_path.exists()
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    project = data["project"]
    assert project["name"] == "pii-shield"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"
    assert "ner" in project["optional-dependencies"]
    assert "api" in project["optional-dependencies"]


def test_pii_shield_public_package_exports_core_api():
    import pii_shield

    assert pii_shield.__version__ == "0.1.0"
    redacted, mapping = pii_shield.redact("Name: Ananya Rao; call 9845012345")
    assert redacted == "Name: [PERSON_1]; call [PHONE_1]"
    assert pii_shield.restore(redacted, mapping) == "Name: Ananya Rao; call 9845012345"

    spans = pii_shield.detect("PAN ABCDE1234F", pii_shield.FakeNer({}))
    assert len(spans) == 1
    assert spans[0].label == "PAN"
    assert pii_shield.is_valid_pan("ABCDE1234F") is True
