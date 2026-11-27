"""Combine structured regex, rules, and an optional NER detector."""

import re

from engine.constants import INDIAN_CITIES
from engine.merge import merge_spans
from engine.ner import NerDetector
from engine.regex_layer import detect_structured_pii
from engine.rules import detect_rule_pii
from engine.spans import Span

_ADDRESS_BRIDGE = re.compile(
    r",[ \t]+(?:[A-Za-z0-9][A-Za-z0-9 .'-]{0,38}[A-Za-z0-9.],[ \t]+)?"
)


def _merge_adjacent_locations(text: str, spans: list[Span]) -> list[Span]:
    """Assemble comma-separated street/locality + city spans into one LOCATION."""
    if len(spans) < 2:
        return spans

    assembled: list[Span] = [spans[0]]
    for current in spans[1:]:
        previous = assembled[-1]
        if (
            previous.label == "LOCATION"
            and current.label == "LOCATION"
            and previous.text.strip().casefold() not in INDIAN_CITIES
            and _ADDRESS_BRIDGE.fullmatch(text[previous.end:current.start])
        ):
            source = "rules" if "rules" in (previous.source, current.source) else previous.source
            assembled[-1] = Span(
                start=previous.start,
                end=current.end,
                label="LOCATION",
                text=text[previous.start:current.end],
                source=source,
                score=min(previous.score, current.score),
            )
        else:
            assembled.append(current)
    return assembled


def detect(
    text: str,
    ner_detector: NerDetector | None = None,
    ner_score_threshold: float = 0.5,
) -> list[Span]:
    """Run available detection layers and return merged spans in text order."""
    candidates = detect_structured_pii(text) + detect_rule_pii(text)
    if ner_detector is not None:
        candidates.extend(ner_detector.detect(text))
    merged = merge_spans(candidates, ner_score_threshold=ner_score_threshold)
    return _merge_adjacent_locations(text, merged)
