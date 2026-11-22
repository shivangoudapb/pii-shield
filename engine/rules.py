"""Rule-based name detection for common title, field, and sign-off patterns."""

import re

from engine.spans import Span

_TITLE = re.compile(
    r"(?i:\b(?:Mr|Mrs|Ms|Dr|Shri|Smt|Sri)\.?)"
    r"[ \t]+(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)"
)
_NAME_FIELD = re.compile(
    r"(?im)^[ \t]*Name[ \t]*:[ \t]*"
    r"(?P<name>[A-Za-z]+(?:[ \t]+[A-Za-z]+)*?)"
    r"(?=[ \t]*(?:$|[,;|.]|\b(?:PAN|Phone|Email|Aadhaar|UPI|Address)[ \t]*:))"
)
_SIGNOFF = re.compile(
    r"(?i:\b(?:Regards|Thanks)[ \t]*,)"
    r"[ \t]*(?:\r?\n[ \t]*)?"
    r"(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)"
)


def detect_rule_pii(text: str) -> list[Span]:
    """Return PERSON spans from titles, Name fields, and sign-offs."""
    if not isinstance(text, str) or not text:
        return []

    spans: dict[tuple[int, int], Span] = {}
    for pattern in (_TITLE, _NAME_FIELD, _SIGNOFF):
        for match in pattern.finditer(text):
            start, end = match.span("name")
            value = text[start:end]
            spans[(start, end)] = Span(
                start=start,
                end=end,
                label="PERSON",
                text=value,
                source="rules",
                score=1.0,
            )
    return sorted(spans.values(), key=lambda span: (span.start, span.end))
