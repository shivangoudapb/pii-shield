import json
import re
from pathlib import Path

from engine.regex_layer import detect_structured_pii
from redactor import redact, restore

DEV_PATH = Path(__file__).parents[1] / "eval" / "dev.jsonl"
REALISTIC_PATH = Path(__file__).parents[1] / "eval" / "realistic.jsonl"
STRUCTURED = {"PHONE", "EMAIL", "AADHAAR", "PAN", "UPI", "PINCODE"}
REALISTIC_STRUCTURED = STRUCTURED | {
    "DOB",
    "PASSPORT",
    "VOTER_ID",
    "DRIVING_LICENSE",
    "BANK_ACCOUNT",
    "IP_ADDRESS",
}


def load_dev():
    return [json.loads(line) for line in DEV_PATH.read_text(encoding="utf-8").splitlines()]


def test_dev_dataset_has_expected_size_unique_ids_and_valid_offsets():
    items = load_dev()
    assert len(items) == 60
    assert len({item["id"] for item in items}) == len(items)

    for item in items:
        for span in item["spans"]:
            assert span["label"] in {
                "PERSON", "LOCATION", "PHONE", "EMAIL", "AADHAAR", "PAN", "UPI", "PINCODE"
            }
            assert 0 <= span["start"] < span["end"] <= len(item["text"])
            assert item["text"][span["start"] : span["end"]] == span["text"]


def test_dev_has_all_structured_labels_and_synthetic_no_pii_items():
    items = load_dev()
    labels = {span["label"] for item in items for span in item["spans"]}
    assert STRUCTURED <= labels
    assert sum(not item["spans"] for item in items) == 6


def test_regex_layer_finds_all_structured_dev_annotations():
    for item in load_dev():
        expected = {
            (span["start"], span["end"], span["label"])
            for span in item["spans"] if span["label"] in STRUCTURED
        }
        actual = {
            (span.start, span.end, span.label)
            for span in detect_structured_pii(item["text"])
        }
        assert expected <= actual, item["id"]


def test_dev_negative_cases_do_not_flag_structured_lookalikes():
    negatives = [item for item in load_dev() if any(tag.startswith("lookalike_") for tag in item["tags"])]
    assert negatives
    for item in negatives:
        tags = set(item["tags"])
        detected = detect_structured_pii(item["text"])
        if "lookalike_invalid_aadhaar" in tags:
            value = re.search(r"(?<!\d)\d{12}(?!\d)", item["text"]).group(0)
            assert not any(span.label == "AADHAAR" and span.text == value for span in detected), item["id"]
        if "lookalike_six_digit_code" in tags:
            value = re.search(r"locker reference (\d{6})", item["text"]).group(1)
            assert not any(span.label == "PINCODE" and span.text == value for span in detected), item["id"]
        if "lookalike_order_id" in tags:
            value = re.search(r"order ref (\d{10})", item["text"]).group(1)
            assert not any(span.text == value and span.label in {"PHONE", "AADHAAR"} for span in detected), item["id"]
        if "lookalike_email_upi" in tags:
            value = re.search(r"sales\d{3}@okhdfcbank\.com", item["text"]).group(0)
            assert any(span.label == "EMAIL" and span.text == value for span in detected), item["id"]
            assert not any(span.label == "UPI" and span.text == value for span in detected), item["id"]
        if "lookalike_nonaddress_location" in tags:
            assert not any(span.label == "PINCODE" for span in detected), item["id"]


def test_realistic_dataset_integrity_structured_exactness_and_round_trip():
    items = [json.loads(line) for line in REALISTIC_PATH.read_text(encoding="utf-8").splitlines()]
    assert len(items) == 540
    assert len({item["id"] for item in items}) == 540
    assert sum(not item["spans"] for item in items) == 54

    all_labels = {span["label"] for item in items for span in item["spans"]}
    assert all_labels == {"PERSON", "LOCATION"} | REALISTIC_STRUCTURED

    for item in items:
        text = item["text"]
        for span in item["spans"]:
            assert 0 <= span["start"] < span["end"] <= len(text), item["id"]
            assert text[span["start"] : span["end"]] == span["text"], item["id"]

        expected_structured = {
            (span["start"], span["end"], span["label"])
            for span in item["spans"]
            if span["label"] in REALISTIC_STRUCTURED
        }
        actual_structured = {
            (span.start, span.end, span.label)
            for span in detect_structured_pii(text)
        }
        assert expected_structured == actual_structured, item["id"]

        redacted, mapping = redact(text)
        assert restore(redacted, mapping) == text, item["id"]
