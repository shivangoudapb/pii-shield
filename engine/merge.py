"""Resolve overlapping detector spans by source priority and span length."""

from collections.abc import Iterable

from engine.spans import Span

_SOURCE_PRIORITY = {"regex": 3, "rules": 2, "ner": 1}


def merge_spans(
    spans: Iterable[Span], ner_score_threshold: float = 0.5
) -> list[Span]:
    """Drop low-confidence NER spans and resolve overlaps deterministically."""
    candidates = [
        span for span in spans
        if span.end > span.start
        and (span.source != "ner" or span.score >= ner_score_threshold)
    ]
    candidates.sort(
        key=lambda span: (
            -_SOURCE_PRIORITY.get(span.source, 0),
            -(span.end - span.start),
            span.start,
            span.end,
            span.label,
        )
    )

    selected: list[Span] = []
    for candidate in candidates:
        overlaps = any(
            candidate.start < chosen.end and chosen.start < candidate.end
            for chosen in selected
        )
        if not overlaps:
            selected.append(candidate)

    return sorted(selected, key=lambda span: (span.start, span.end, span.label))
