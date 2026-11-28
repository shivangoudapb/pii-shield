"""Combine structured regex, rules, and an optional NER detector."""

import re

from engine.constants import CORPORATE_SUFFIX_WORDS, INDIAN_CITIES
from engine.merge import merge_spans
from engine.ner import NerDetector
from engine.regex_layer import detect_structured_pii
from engine.rules import detect_rule_pii
from engine.spans import Span

_ADDRESS_BRIDGE = re.compile(
    r",[ \t]+(?:[A-Za-z0-9][A-Za-z0-9 .'-]{0,38}[A-Za-z0-9.],[ \t]+)?"
)
_CORPORATE_SUFFIX_LOWER = frozenset(word.casefold() for word in CORPORATE_SUFFIX_WORDS)
_CORPORATE_SUFFIX_AFTER = re.compile(
    r"^[ \t]+(?:&[ \t]+)?(?:"
    + "|".join(re.escape(word) for word in sorted(CORPORATE_SUFFIX_WORDS, key=len, reverse=True))
    + r")\b"
)


def _is_company_person_false_alarm(text: str, span: Span) -> bool:
    """Return True when a PERSON candidate is actually an Indian company name."""
    if span.label != "PERSON":
        return False
    words = span.text.split()
    if len(words) >= 2 and words[-1].rstrip(".,").casefold() in _CORPORATE_SUFFIX_LOWER:
        return True
    if _CORPORATE_SUFFIX_AFTER.match(text[span.end:]) is not None:
        return True
    return False


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
    filtered = [
        span for span in candidates if not _is_company_person_false_alarm(text, span)
    ]
    merged = merge_spans(filtered, ner_score_threshold=ner_score_threshold)
    return _merge_adjacent_locations(text, merged)
