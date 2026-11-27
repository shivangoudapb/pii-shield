"""Rule-based name detection for common title, field, and sign-off patterns."""

import re

from engine.spans import Span

_TITLE = re.compile(
    r"(?i:\b(?:Mr|Mrs|Ms|Dr|Shri|Smt|Sri)\.?)"
    r"[ \t]+(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)"
)
_NAME_FIELD = re.compile(
    r"(?im)^[ \t]*(?:Name|From)[ \t]*:[ \t]*"
    r"(?P<name>[A-Za-z]+(?:[ \t]+[A-Za-z]+)*?)"
    r"(?=[ \t]*(?:$|[,;|.]|\b(?:PAN|Phone|Email|Aadhaar|UPI|Address)[ \t]*:))"
)
_SIGNOFF = re.compile(
    r"(?i:\b(?:Regards|Thanks)[ \t]*,)"
    r"[ \t]*(?:\r?\n[ \t]*)?"
    r"(?P<name>[A-Z][a-z]+(?:,[ \t]+[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*|(?:[ \t]+[A-Z][a-z]+)*))"
)
_FOLLOW_UP = re.compile(
    r"(?i:follow\s+up\s+with)\s+(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)"
)
_SHIP_TO = re.compile(
    r"(?i:ship\s+to)\s+(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*?)(?=[ \t]+at\b)"
)
_NICKNAME = re.compile(
    r"\((?i:nickname)\s+(?P<name>[A-Za-z][A-Za-z]+)\)"
)
_SURNAME_ROSTER = re.compile(
    r"\((?i:surname\s+on\s+roster)\s*:\s*(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)\)"
)
_CIRCULAR = re.compile(
    r"(?i:\bcircular)\s*[—–-]\s*(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)"
)
_UPDATE_FOR = re.compile(
    r"(?i:\bupdate\s+for)\s+(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*?)(?=[ \t]*[—–-])"
)


def detect_rule_pii(text: str) -> list[Span]:
    """Return PERSON spans from titles, Name fields, and sign-offs."""
    if not isinstance(text, str) or not text:
        return []

    spans: dict[tuple[int, int], Span] = {}
    for pattern in (_TITLE, _NAME_FIELD, _SIGNOFF,
                    _FOLLOW_UP, _SHIP_TO, _NICKNAME, _SURNAME_ROSTER,
                    _CIRCULAR, _UPDATE_FOR):
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
