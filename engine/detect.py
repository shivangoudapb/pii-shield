"""Combine structured regex, rules, and an optional NER detector."""

from engine.merge import merge_spans
from engine.ner import NerDetector
from engine.regex_layer import detect_structured_pii
from engine.rules import detect_rule_pii
from engine.spans import Span


def detect(
    text: str,
    ner_detector: NerDetector | None = None,
    ner_score_threshold: float = 0.5,
) -> list[Span]:
    """Run available detection layers and return merged spans in text order."""
    candidates = detect_structured_pii(text) + detect_rule_pii(text)
    if ner_detector is not None:
        candidates.extend(ner_detector.detect(text))
    return merge_spans(candidates, ner_score_threshold=ner_score_threshold)
