"""Evaluate regex/rules, GLiNER, and hybrid detection on synthetic data.

Only aggregate metrics are printed. Dataset examples are written to the
explicitly requested evaluation reports, never to logs or the terminal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

from engine.detect import detect
from engine.merge import merge_spans
from engine.ner import DEFAULT_LABELS, DEFAULT_LABEL_MAPPING, GlinerNer, NerDetector
from engine.regex_layer import detect_structured_pii
from engine.rules import detect_rule_pii
from engine.spans import Span, SpanLabel
from redactor import _redact_spans, restore

ROOT = Path(__file__).resolve().parent
ALL_LABELS: tuple[str, ...] = (
    "PERSON", "LOCATION", "PHONE", "EMAIL", "AADHAAR", "PAN", "UPI", "PINCODE"
)
THRESHOLDS = (0.2, 0.3, 0.4, 0.5)
LABEL_SETS: dict[str, tuple[str, ...]] = {
    "base": ("person", "address", "city"),
    "expanded": ("person", "address", "city", "locality", "street address"),
}
LABEL_MAPPING = dict(DEFAULT_LABEL_MAPPING) | {"locality": "LOCATION", "street address": "LOCATION"}
ERROR_GROUPS = (
    "common-word names", "initials", "lowercase", "regional names",
    "company-name lookalikes", "boundary errors", "other",
)


class _RequestCache:
    """Avoid duplicate NER calls for the B and C comparisons in one split."""

    def __init__(self, detector: NerDetector) -> None:
        self.detector = detector
        self.cache: dict[str, list[Span]] = {}

    def detect(self, text: str) -> list[Span]:
        if text not in self.cache:
            self.cache[text] = self.detector.detect(text)
        return list(self.cache[text])

    def clear(self) -> None:
        self.cache.clear()


def _triple(span: Span | dict | tuple[int, int, str]) -> tuple[int, int, str]:
    if isinstance(span, dict):
        return int(span["start"]), int(span["end"]), str(span["label"])
    if isinstance(span, tuple):
        return int(span[0]), int(span[1]), str(span[2])
    return span.start, span.end, str(span.label)


def _prf(tp: int, predicted: int, gold: int) -> dict[str, float]:
    precision = tp / predicted if predicted else (1.0 if not gold else 0.0)
    recall = tp / gold if gold else (1.0 if not predicted else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _score_one(gold: list[tuple[int, int, str]], predicted: list[tuple[int, int, str]], relaxed: bool) -> dict[str, dict[str, float]]:
    """Greedily pair one prediction to at most one same-label gold span."""
    candidates: list[tuple[float, int, int]] = []
    for pred_index, (ps, pe, plabel) in enumerate(predicted):
        for gold_index, (gs, ge, glabel) in enumerate(gold):
            if plabel != glabel:
                continue
            if not relaxed:
                if (ps, pe) == (gs, ge):
                    candidates.append((1.0, pred_index, gold_index))
                continue
            overlap = max(0, min(pe, ge) - max(ps, gs))
            denominator = max(pe - ps, ge - gs)
            ratio = overlap / denominator if denominator else 0.0
            if ratio >= 0.5:
                candidates.append((ratio, pred_index, gold_index))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    used_pred: set[int] = set()
    used_gold: set[int] = set()
    matched_pairs: list[tuple[int, int]] = []
    true_positive = 0
    for _, pred_index, gold_index in candidates:
        if pred_index not in used_pred and gold_index not in used_gold:
            used_pred.add(pred_index)
            used_gold.add(gold_index)
            matched_pairs.append((pred_index, gold_index))
            true_positive += 1

    labels = set(ALL_LABELS)
    labels.update(label for _, _, label in gold)
    labels.update(label for _, _, label in predicted)
    counts: dict[str, dict[str, int]] = {}
    for label in labels:
        g = [span for span in gold if span[2] == label]
        p = [span for span in predicted if span[2] == label]
        # Count matched pairs by label directly; duplicate spans remain false alarms.
        tp = sum(1 for pi, gi in matched_pairs if predicted[pi][2] == label and gold[gi][2] == label)
        counts[label] = {"tp": tp, "predicted": len(p), "gold": len(g)}
    total_tp = sum(count["tp"] for count in counts.values())
    total_pred = sum(count["predicted"] for count in counts.values())
    total_gold = sum(count["gold"] for count in counts.values())
    return {
        label: _prf(c["tp"], c["predicted"], c["gold"])
        for label, c in counts.items()
    } | {"micro": _prf(total_tp, total_pred, total_gold)}


def score_spans(gold: Sequence[Span | dict], predicted: Sequence[Span | dict]) -> dict[str, dict[str, dict[str, float]]]:
    """Compute exact and relaxed entity metrics (micro plus every label)."""
    gold_t = [_triple(span) for span in gold]
    pred_t = [_triple(span) for span in predicted]
    return {
        "exact": _score_one(gold_t, pred_t, relaxed=False),
        "relaxed": _score_one(gold_t, pred_t, relaxed=True),
    }


def load_items(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _system_spans(system: str, text: str, ner: NerDetector, ner_score_threshold: float = 0.5) -> list[Span]:
    if system == "A":
        return merge_spans(detect_structured_pii(text) + detect_rule_pii(text))
    if system == "B":
        return ner.detect(text)
    return detect(text, ner, ner_score_threshold=ner_score_threshold)


def evaluate_items(items: list[dict], system: str, ner: NerDetector, ner_score_threshold: float = 0.5) -> dict:
    gold_all: list[tuple[int, int, str]] = []
    predicted_all: list[tuple[int, int, str]] = []
    no_pii_total = 0
    no_pii_false_alarms = 0
    round_trip_passes = 0
    item_outputs: list[tuple[dict, list[Span]]] = []
    offset = 0
    for item in items:
        text = item["text"]
        predicted = _system_spans(system, text, ner, ner_score_threshold)
        gold_all.extend((span["start"] + offset, span["end"] + offset, span["label"]) for span in item["spans"])
        predicted_all.extend((span.start + offset, span.end + offset, span.label) for span in predicted)
        offset += len(text) + 1
        item_outputs.append((item, predicted))
        if not item["spans"]:
            no_pii_total += 1
            no_pii_false_alarms += bool(predicted)
        if system == "C":
            redacted, mapping = _redact_spans(text, predicted)
            round_trip_passes += restore(redacted, mapping) == text
    return {
        "metrics": score_spans(gold_all, predicted_all),
        "false_alarm_rate_no_pii": no_pii_false_alarms / no_pii_total if no_pii_total else None,
        "round_trip_rate": round_trip_passes / len(items) if system == "C" and items else None,
        "items": len(items),
        "gold_spans_per_label": _span_counts(gold_all),
        "outputs": item_outputs,
    }


def _span_counts(spans: Iterable[Span | dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for span in spans:
        if isinstance(span, tuple):
            counts[span[2]] += 1
        else:
            counts[_triple(span)[2]] += 1
    return dict(sorted(counts.items()))


def _frozen_ner(config: dict) -> GlinerNer:
    return GlinerNer(
        model_name=os.environ.get("PII_SHIELD_EVAL_MODEL_PATH", config.get("model_name", "urchade/gliner_multi_pii-v1")),
        labels=config["labels"],
        label_mapping=config.get("label_mapping", LABEL_MAPPING),
        threshold=float(config["threshold"]),
    )


def tune_dev() -> tuple[dict, list[dict]]:
    items = load_items(ROOT / "dev.jsonl")
    trials: list[dict] = []
    for label_set_name, labels in LABEL_SETS.items():
        for threshold in THRESHOLDS:
            config = {"threshold": threshold, "labels": list(labels), "label_mapping": LABEL_MAPPING}
            ner = _frozen_ner(config)
            result = evaluate_items(items, "C", ner, threshold)
            person = result["metrics"]["exact"]["PERSON"]
            trial = {
                "threshold": threshold,
                "label_set": label_set_name,
                "labels": list(labels),
                "person_precision": person["precision"],
                "person_recall": person["recall"],
                "person_f1": person["f1"],
                "hybrid_exact_micro_f1": result["metrics"]["exact"]["micro"]["f1"],
            }
            trials.append(trial)
            print("DEV_TUNE " + json.dumps(trial, sort_keys=True))
    # Favor recall, then precision, then overall F1. This is a privacy-oriented
    # ranking; all candidates remain visible for the owner to inspect.
    best = max(trials, key=lambda row: (row["person_recall"], row["person_precision"], row["hybrid_exact_micro_f1"]))
    chosen = {
        "model_name": "urchade/gliner_multi_pii-v1",
        "threshold": best["threshold"],
        "labels": best["labels"],
        "label_set": best["label_set"],
    }
    return chosen, trials


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _format_results(results: dict[str, dict], split: str, tuning_trials: list[dict] | None = None, latency: dict | None = None) -> str:
    lines = [f"# Evaluation results: {split}", "", "All data is synthetic. Relaxed matching requires overlap / max(span lengths) ≥ 50% with the same label.", "", "## Exact-match metrics", "", "| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label in (*ALL_LABELS, "micro"):
        vals = [results[system]["metrics"]["exact"][label][key] for system in "ABC" for key in ("precision", "recall", "f1")]
        lines.append(f"| {'**Overall**' if label == 'micro' else label} | " + " | ".join(_pct(value) for value in vals) + " |")
    lines += ["", "## Relaxed-match metrics", "", "| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label in (*ALL_LABELS, "micro"):
        vals = [results[system]["metrics"]["relaxed"][label][key] for system in "ABC" for key in ("precision", "recall", "f1")]
        lines.append(f"| {'**Overall**' if label == 'micro' else label} | " + " | ".join(_pct(value) for value in vals) + " |")
    lines += ["", "## Split checks", "", f"- Items: {results['C']['items']}", f"- Gold spans per label: `{json.dumps(results['C']['gold_spans_per_label'], sort_keys=True)}`", f"- No-PII false-alarm rate (C): {_pct(results['C']['false_alarm_rate_no_pii'])}", f"- Full-pipeline round-trip rate (C): {_pct(results['C']['round_trip_rate'])}"]
    if tuning_trials:
        lines += ["", "## Dev tuning sweep", "", "| Threshold | Label set | PERSON precision | PERSON recall | PERSON F1 | Hybrid micro F1 |", "|---:|---|---:|---:|---:|---:|"]
        for row in tuning_trials:
            lines.append(f"| {row['threshold']:.1f} | {row['label_set']} | {_pct(row['person_precision'])} | {_pct(row['person_recall'])} | {_pct(row['person_f1'])} | {_pct(row['hybrid_exact_micro_f1'])} |")
    if latency:
        lines += ["", "## Latency and memory", "", f"- Hybrid latency after warm-up: median {latency['median_ms']:.2f} ms/item; p95 {latency['p95_ms']:.2f} ms/item.", f"- Peak process RAM with model loaded: {latency['peak_ram_mb']:.1f} MiB."]
    lines += ["", "Scores are indicative only: the dataset is small and synthetic.", ""]
    return "\n".join(lines)


def _error_group(item: dict, expected: dict | None, detected: Span | None) -> str:
    tags = set(item.get("tags", []))
    if "lookalike_company_name" in tags:
        return "company-name lookalikes"
    if "common_word_name" in tags:
        return "common-word names"
    if expected and ("initial" in expected["text"] or any(tag.startswith("repeat_initial") for tag in tags)):
        return "initials"
    if expected and expected["text"].islower() or "lowercase_name" in tags:
        return "lowercase"
    if expected and len(expected["text"].split()) > 0 and any(token in expected["text"] for token in ("D'Souza", "Fernandes", "Mohammed", "Gowda", "Reddy", "Menon", "Nair")):
        return "regional names"
    if expected and detected and expected["label"] == detected.label and expected["start"] < detected.end and detected.start < expected["end"]:
        return "boundary errors"
    return "other"


def write_errors(items_outputs: list[tuple[dict, list[Span]]], path: Path) -> None:
    groups: dict[str, list[str]] = {group: [] for group in ERROR_GROUPS}
    for item, detected in items_outputs:
        relevant_gold = [span for span in item["spans"] if span["label"] in {"PERSON", "LOCATION"}]
        relevant_pred = [span for span in detected if span.label in {"PERSON", "LOCATION"}]
        unmatched_gold = [span for span in relevant_gold if not any(_exact(span, pred) for pred in relevant_pred)]
        unmatched_pred = [span for span in relevant_pred if not any(_exact(gold, span) for gold in relevant_gold)]
        for expected in unmatched_gold:
            overlap = next((pred for pred in relevant_pred if pred.label == expected["label"] and expected["start"] < pred.end and pred.start < expected["end"]), None)
            group = _error_group(item, expected, overlap)
            groups[group].append(f"- Miss | item {item['id']} | text: {item['text']!r} | expected: {expected['text']!r} [{expected['start']}:{expected['end']} {expected['label']}] | detected: {overlap.text!r} [{overlap.start}:{overlap.end} {overlap.label}]" if overlap else f"- Miss | item {item['id']} | text: {item['text']!r} | expected: {expected['text']!r} [{expected['start']}:{expected['end']} {expected['label']}] | detected: none")
        for prediction in unmatched_pred:
            overlap = next((gold for gold in relevant_gold if gold["label"] == prediction.label and prediction.start < gold["end"] and gold["start"] < prediction.end), None)
            group = _error_group(item, overlap, prediction)
            groups[group].append(f"- False alarm | item {item['id']} | text: {item['text']!r} | expected: {overlap['text']!r} [{overlap['start']}:{overlap['end']} {overlap['label']}] | detected: {prediction.text!r} [{prediction.start}:{prediction.end} {prediction.label}]" if overlap else f"- False alarm | item {item['id']} | text: {item['text']!r} | expected: none | detected: {prediction.text!r} [{prediction.start}:{prediction.end} {prediction.label}]")
    lines = ["# Hybrid PERSON/LOCATION errors", "", "Each item below is a test-set miss or false alarm. Raw dataset text appears here by design, as explicitly requested for error analysis.", ""]
    for group in ERROR_GROUPS:
        lines += [f"## {group}", ""]
        lines += groups[group] or ["- None."]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _exact(gold: dict, pred: Span) -> bool:
    return (gold["start"], gold["end"], gold["label"]) == (pred.start, pred.end, pred.label)


def _peak_ram_mb() -> float:
    if __import__("os").name == "nt":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize / (1024 * 1024)
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 1024 if peak > 1024 * 1024 else peak / 1024


def measure_latency(items: list[dict], ner: NerDetector, ner_score_threshold: float = 0.5) -> dict:
    if not items:
        return {"median_ms": 0.0, "p95_ms": 0.0, "peak_ram_mb": _peak_ram_mb()}
    if isinstance(ner, _RequestCache):
        ner.clear()
    detect(items[0]["text"], ner, ner_score_threshold=ner_score_threshold)  # warm-up after model load
    timings: list[float] = []
    for item in items:
        start = time.perf_counter()
        detect(item["text"], ner, ner_score_threshold=ner_score_threshold)
        timings.append((time.perf_counter() - start) * 1000)
    ordered = sorted(timings)
    p95_index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999) - 1))
    return {"median_ms": statistics.median(ordered), "p95_ms": ordered[p95_index], "peak_ram_mb": _peak_ram_mb()}


def evaluate_split(split: str, config: dict, trials: list[dict] | None = None) -> dict[str, dict]:
    items = load_items(ROOT / f"{split}.jsonl")
    ner = _frozen_ner(config)
    threshold = float(config.get("ner_score_threshold", 0.5))
    cached_ner = _RequestCache(ner)
    results = {system: evaluate_items(items, system, cached_ner, threshold) for system in "ABC"}
    latency = measure_latency(items, ner, threshold)
    results["_latency"] = latency
    if split == "test":
        write_errors(results["C"]["outputs"], ROOT / "errors.md")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tune-dev", action="store_true", help="sweep settings on dev and write selected config")
    parser.add_argument("--evaluate-frozen", action="store_true", help="run A/B/C on dev and test using committed config")
    args = parser.parse_args()
    if args.tune_dev == args.evaluate_frozen:
        parser.error("choose exactly one of --tune-dev or --evaluate-frozen")
    config_path = ROOT / "config.json"
    if args.tune_dev:
        config, trials = tune_dev()
        config["label_mapping"] = LABEL_MAPPING
        config["ner_score_threshold"] = float(config["threshold"])
        config["selection_metric"] = "exact PERSON recall, tie-break by precision then hybrid micro F1"
        config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (ROOT / "dev_tuning.json").write_text(json.dumps(trials, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        items = load_items(ROOT / "dev.jsonl")
        ner = _frozen_ner(config)
        threshold = float(config["ner_score_threshold"])
        results = {system: evaluate_items(items, system, ner, threshold) for system in "ABC"}
        latency = measure_latency(items, ner, threshold)
        (ROOT / "results.md").write_text(_format_results(results, "dev", trials, latency), encoding="utf-8")
        print("Selected dev-only config: " + json.dumps(config, sort_keys=True))
        print("Wrote eval/config.json and dev results. Commit/freeze config before --evaluate-frozen.")
    else:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        lock_path = ROOT / "test_run.lock"
        if lock_path.exists():
            parser.error("the one-time test evaluation has already started")
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "eval/config.json"], cwd=ROOT.parent, capture_output=True)
        changed = subprocess.run(["git", "status", "--porcelain", "--", "eval/config.json"], cwd=ROOT.parent, capture_output=True, text=True)
        if tracked.returncode or changed.stdout.strip():
            parser.error("eval/config.json must be committed and unchanged before the one-time test run")
        summaries = {}
        summaries["dev"] = evaluate_split("dev", config)
        print("DEV SUMMARY " + json.dumps({system: {"exact_micro": summaries["dev"][system]["metrics"]["exact"]["micro"], "relaxed_micro": summaries["dev"][system]["metrics"]["relaxed"]["micro"], "no_pii_false_alarm_rate": summaries["dev"][system]["false_alarm_rate_no_pii"], "round_trip_rate": summaries["dev"][system]["round_trip_rate"]} for system in "ABC"}, sort_keys=True))
        # Create the one-time marker immediately before opening the locked split.
        lock_path.write_text(hashlib.sha256(config_path.read_bytes()).hexdigest() + "\n", encoding="ascii")
        summaries["test"] = evaluate_split("test", config)
        print("TEST SUMMARY " + json.dumps({system: {"exact_micro": summaries["test"][system]["metrics"]["exact"]["micro"], "relaxed_micro": summaries["test"][system]["metrics"]["relaxed"]["micro"], "no_pii_false_alarm_rate": summaries["test"][system]["false_alarm_rate_no_pii"], "round_trip_rate": summaries["test"][system]["round_trip_rate"]} for system in "ABC"}, sort_keys=True))
        trial_path = ROOT / "dev_tuning.json"
        trials = json.loads(trial_path.read_text(encoding="utf-8")) if trial_path.exists() else None
        formatted = []
        for split in ("dev", "test"):
            formatted.append(_format_results(summaries[split], split, trials if split == "dev" else None, summaries[split]["_latency"]))
        realistic = ROOT / "realistic.jsonl"
        if realistic.exists():
            items = load_items(realistic)
            ner = _frozen_ner(config)
            real_results = {system: evaluate_items(items, system, ner, float(config["ner_score_threshold"])) for system in "ABC"}
            print("REALISTIC SUMMARY " + json.dumps({system: real_results[system]["metrics"]["exact"]["micro"] for system in "ABC"}, sort_keys=True))
            formatted.append("# Evaluation results: realistic hand-written split\n\n" + json.dumps({system: real_results[system]["metrics"] for system in "ABC"}, indent=2, sort_keys=True))
        (ROOT / "results.md").write_text("\n\n---\n\n".join(formatted), encoding="utf-8")


if __name__ == "__main__":
    main()
