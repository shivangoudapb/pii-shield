"""In-memory, reversible redaction using generated placeholders."""

import re

from engine.detect import detect
from engine.ner import NerDetector
from engine.spans import Span

_PLACEHOLDER = re.compile(r"\[([A-Za-z]+_[0-9]+)\]", re.IGNORECASE)


def _normalise_entity(value: str) -> str:
    return " ".join(value.casefold().split())


def _redact_spans(text: str, spans: list[Span]) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    placeholders: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}
    output: list[str] = []
    cursor = 0

    for span in sorted(spans, key=lambda item: (item.start, item.end)):
        if span.start < cursor or span.end > len(text):
            continue
        original = text[span.start:span.end]
        if original != span.text:
            continue
        output.append(text[cursor:span.start])
        key = (span.label, _normalise_entity(original))
        placeholder = placeholders.get(key)
        if placeholder is None:
            counters[span.label] = counters.get(span.label, 0) + 1
            placeholder = f"[{span.label}_{counters[span.label]}]"
            placeholders[key] = placeholder
            mapping[placeholder] = original
        output.append(placeholder)
        cursor = span.end

    output.append(text[cursor:])
    return "".join(output), mapping


def redact(
    text: str, ner_detector: NerDetector | None = None
) -> tuple[str, dict[str, str]]:
    """Redact detected PII and return text plus a call-local placeholder map."""
    spans = detect(text, ner_detector)
    return _redact_spans(text, spans)


def restore(text: str, mapping: dict[str, str]) -> str:
    """Restore known placeholders, ignoring placeholder case and preserving unknowns."""
    lookup = {placeholder.upper(): value for placeholder, value in mapping.items()}
    return _PLACEHOLDER.sub(
        lambda match: lookup.get(match.group(0).upper(), match.group(0)),
        text,
    )
