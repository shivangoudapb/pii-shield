"""Runs the Chrome Extension (C1/E12) Node.js test suite inside pytest."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXT_DIR = ROOT / "extension"


def test_extension_manifest_v3_structure():
    manifest = json.loads((EXT_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert "storage" in manifest["permissions"]
    matches = manifest["content_scripts"][0]["matches"]
    assert "https://chatgpt.com/*" in matches
    assert "https://gemini.google.com/*" in matches
    assert "https://claude.ai/*" in matches


def test_chrome_extension_node_suite_passes():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js runtime not found on PATH")
    result = subprocess.run(
        [node, "--test", str(EXT_DIR / "tests" / "extension.test.js")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Node extension tests failed:\n{result.stdout}\n{result.stderr}"
