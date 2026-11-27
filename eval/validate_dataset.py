"""Validate dataset annotations and print aggregate-only statistics.

This script deliberately imports no detector code and never prints item text.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPLIT_PATHS = {
    "dev": ROOT / "dev.jsonl",
    "test": ROOT / "test.jsonl",
    "realistic": ROOT / "realistic.jsonl",
}
EXPECTED_COUNTS = {"dev": 60, "test": 100, "realistic": 540}


def validate_split(split: str) -> dict:
    path = SPLIT_PATHS[split]
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    seen_ids: set[str] = set()
    labels: Counter[str] = Counter()
    contexts: Counter[str] = Counter()
    templates: dict[str, set[str]] = defaultdict(set)
    no_pii = 0
    hard = Counter()
    for item in items:
        item_id = item.get("id", "<missing-id>")
        assert item_id not in seen_ids, f"Duplicate item id: {item_id}"
        seen_ids.add(item_id)
        text = item["text"]
        context = item["context"]
        contexts[context] += 1
        templates[context].add(item["template"])
        spans = sorted(item["spans"], key=lambda span: (span["start"], span["end"]))
        no_pii += not spans
        previous_end = -1
        for span in spans:
            assert 0 <= span["start"] < span["end"] <= len(text), f"Invalid bounds in {item_id}"
            assert text[span["start"]:span["end"]] == span["text"], f"Slice mismatch in {item_id}"
            assert span["start"] >= previous_end, f"Overlapping spans in {item_id}"
            previous_end = span["end"]
            labels[span["label"]] += 1
        tags = set(item.get("tags", []))
        hard["common_word_names"] += "common_word_name" in tags
        hard["lookalike_negatives"] += "lookalike_negative" in tags
        hard["lowercase_names"] += "lowercase_name" in tags
        hard["all_caps_names"] += "all_caps_name" in tags
        hard["repeated_person"] += "repeated_person" in tags
    assert len(items) == EXPECTED_COUNTS[split], f"Unexpected item count in {split}"
    assert no_pii == len(items) // 10, f"Unexpected no-PII count in {split}"
    min_templates = 12 if split == "realistic" else 8
    assert all(len(templates[context]) >= min_templates for context in contexts), f"Insufficient template variety in {split}"
    whatsapp = [item for item in items if item["context"] in {"whatsapp", "whatsapp_chat"}]
    casing = sum("messy_chat_casing" in item.get("tags", []) for item in whatsapp)
    assert casing * 4 >= len(whatsapp), f"Insufficient WhatsApp casing variety in {split}"
    return {
        "items": len(items),
        "items_per_context": dict(sorted(contexts.items())),
        "spans_per_label": dict(sorted(labels.items())),
        "no_pii_items": no_pii,
        "hard_cases": dict(sorted(hard.items())),
        "whatsapp_lower_or_all_caps": casing,
        "templates_per_context": {key: len(value) for key, value in sorted(templates.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "realistic", "all"), default="all")
    split = parser.parse_args().split
    selected = (
        {k: p for k, p in SPLIT_PATHS.items() if k in {"dev", "test"} or p.exists()}
        if split == "all"
        else {split: SPLIT_PATHS[split]}
    )
    for name in selected:
        stats = validate_split(name)
        print(f"{name}: annotations valid; aggregate stats={json.dumps(stats, sort_keys=True)}")


if __name__ == "__main__":
    main()
