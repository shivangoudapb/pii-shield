import json
import re
from pathlib import Path

from engine.regex_layer import detect_structured_pii

DEV_PATH = Path(__file__).parents[1] / "eval" / "dev.jsonl"
STRUCTURED = {"PHONE", "EMAIL", "AADHAAR", "PAN", "UPI", "PINCODE"}


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
