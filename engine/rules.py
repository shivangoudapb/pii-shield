"""Rule-based detection for structured name cues and Indian street addresses."""

import re

from engine.constants import INDIAN_CITIES
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

_CITY_ALTERNATION = "|".join(
    re.escape(city).replace(r"\ ", r"[ \t]+")
    for city in sorted(INDIAN_CITIES, key=len, reverse=True)
)
_ROAD_OR_UNIT = (
    r"(?:Street|St\.?|Road|Rd\.?|Lane|Ln\.?|Cross|Main|Avenue|Ave\.?|Marg|Path|"
    r"Circle|Chowk|Layout|Nagar|Sector|Colony|Enclave|Extension|Extn\.?|Block|"
    r"Phase|Stage|Pocket|Vihar|Puram|Garden|Gardens|Park|Residency|Heights|"
    r"Apartment|Apartments|Tower|Towers)"
)
_ADDRESS_START = (
    r"(?:"
    r"(?:Flat|Plot|House|Door|Shop|Villa|No\.?)[ \t]*(?:#[ \t]*)?[A-Za-z0-9/-]+"
    r"(?:,[ \t]+|[ \t]+)(?:\d+[A-Za-z/-]*[ \t]+)?(?:[A-Z0-9][A-Za-z0-9.'/-]*[ \t]+){0,4}?"
    + _ROAD_OR_UNIT
    + r"(?:[ \t]+[A-Za-z0-9-]+)?"
    r"|"
    r"\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)?(?:st|nd|rd|th)?[ \t]+"
    r"(?:[A-Z0-9][A-Za-z0-9.'/-]*[ \t]+){0,4}?"
    + _ROAD_OR_UNIT
    + r"(?:[ \t]+\d+[A-Za-z]?)?"
    r"|"
    r"(?:Sector|Phase|Stage|Block)[ \t]+\d+[A-Za-z]?"
    r")"
)
_STRUCTURED_ADDRESS = re.compile(
    r"(?<![A-Za-z0-9])(?P<address>"
    + _ADDRESS_START
    + r"(?:,[ \t]+[A-Za-z0-9][A-Za-z0-9 .'-]{0,38}[A-Za-z0-9.])*"
    + r",[ \t]+(?i:" + _CITY_ALTERNATION + r")"
    + r")(?![A-Za-z])"
)


def detect_rule_pii(text: str) -> list[Span]:
    """Return PERSON and LOCATION spans from high-precision text patterns."""
    if not isinstance(text, str) or not text:
        return []

    spans: dict[tuple[int, int, str], Span] = {}
    for pattern in (_TITLE, _NAME_FIELD, _SIGNOFF,
                    _FOLLOW_UP, _SHIP_TO, _NICKNAME, _SURNAME_ROSTER,
                    _CIRCULAR, _UPDATE_FOR):
        for match in pattern.finditer(text):
            start, end = match.span("name")
            value = text[start:end]
            spans[(start, end, "PERSON")] = Span(
                start=start,
                end=end,
                label="PERSON",
                text=value,
                source="rules",
                score=1.0,
            )
    for match in _STRUCTURED_ADDRESS.finditer(text):
        start, end = match.span("address")
        value = text[start:end]
        spans[(start, end, "LOCATION")] = Span(
            start=start,
            end=end,
            label="LOCATION",
            text=value,
            source="rules",
            score=1.0,
        )
    return sorted(spans.values(), key=lambda span: (span.start, span.end, span.label))
