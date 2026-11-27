"""Regex-based detection for validated structured Indian PII."""

import re
from collections.abc import Callable

from engine.spans import Span, SpanLabel
from engine.validators import (
    is_valid_aadhaar,
    is_valid_email,
    is_valid_pan,
    is_valid_phone,
    is_valid_pincode,
    is_valid_upi,
)

# ASCII-only digit classes match the validators and prevent Unicode digit lookalikes.
_AADHAAR_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9])[2-9][0-9]{3}(?:(?:[ -])[0-9]{4}){2}(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])[2-9][0-9]{11}(?![A-Za-z0-9])"
)
_PAN_CANDIDATE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{5}[0-9]{4}[A-Za-z](?![A-Za-z0-9])")
_PHONE_CANDIDATE = re.compile(
    r"(?<![0-9])(?:(?:\+91|91|0)[ -]?)?[6-9][0-9]{4}[ -]?[0-9]{5}(?![0-9])"
)
_EMAIL_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
    r"(?![A-Za-z0-9-])"
)
_UPI_CANDIDATE = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._-]{0,254}@[A-Za-z0-9-]+")
_PINCODE_CANDIDATE = re.compile(r"(?<![0-9])[1-9][0-9]{5}(?![0-9])")
_ADDRESS_CONTEXT = re.compile(
    r"\b(?:"
    r"bengaluru|bangalore|mumbai|navi\s+mumbai|delhi|new\s+delhi|hyderabad|"
    r"chennai|kolkata|pune|ahmedabad|jaipur|surat|lucknow|kanpur|nagpur|"
    r"indore|thane|bhopal|visakhapatnam|vizag|patna|vadodara|ghaziabad|"
    r"ludhiana|agra|nashik|faridabad|meerut|rajkot|varanasi|srinagar|"
    r"aurangabad|amritsar|prayagraj|allahabad|ranchi|coimbatore|vijayawada|"
    r"jodhpur|madurai|raipur|kota|guwahati|chandigarh|mysuru|mysore|noida|"
    r"gurugram|gurgaon|kochi|cochin|thiruvananthapuram|trivandrum|mangaluru|"
    r"mangalore|bhubaneswar|dehradun|shimla|panaji|goa|kerala|karnataka|"
    r"maharashtra|tamil\s+nadu|telangana|gujarat|rajasthan|haryana|punjab|"
    r"address|pin|pincode|postal|street|road|lane|cross|avenue|marg|"
    r"sector|nagar|layout|colony|enclave|extension|phase|stage|block|pocket|"
    r"plot|house|flat|apartment|apartments|floor|building|tower|residency|"
    r"garden|gardens|park|vihar|puram|chowk|district|taluk|tehsil"
    r")\b",
    re.IGNORECASE,
)
_NON_ADDRESS_CONTEXT = re.compile(
    r"\b(?:otp|order|verification|code|transaction|reference|tracking|"
    r"(?:atm|upi)\s*pin|order\s*(?:no|number|id))\b",
    re.IGNORECASE,
)


def _pincode_has_address_context(text: str, start: int) -> bool:
    """Use nearby address terms or an unambiguous, non-code comma context."""
    left = text[max(0, start - 48):start]
    right = text[start:start + 24]
    context = left + " " + right
    if _NON_ADDRESS_CONTEXT.search(context):
        return False
    if _ADDRESS_CONTEXT.search(context):
        return True
    # A comma is a common flattened-address separator. A nearby code/order marker
    # above takes precedence so values such as "OTP, 560001" stay unflagged.
    return "," in left[-12:]


def detect_structured_pii(text: str) -> list[Span]:
    """Return validated structured PII spans in source order, without changing text."""
    if not isinstance(text, str) or not text:
        return []

    found: list[Span] = []

    def add_matches(
        pattern: re.Pattern[str], label: SpanLabel, validator: Callable[[str], bool]
    ) -> None:
        for match in pattern.finditer(text):
            value = match.group(0)
            if validator(value):
                found.append(Span(
                    start=match.start(),
                    end=match.end(),
                    label=label,
                    text=value,
                    source="regex",
                    score=1.0,
                ))

    # Detect Aadhaar before phones so overlapping candidates can be suppressed.
    add_matches(_AADHAAR_CANDIDATE, "AADHAAR", is_valid_aadhaar)
    aadhaar_ranges = [(span.start, span.end) for span in found]

    add_matches(_PAN_CANDIDATE, "PAN", is_valid_pan)
    add_matches(_PHONE_CANDIDATE, "PHONE", is_valid_phone)
    # Aadhaar is allowed to contain separators; never emit a phone subspan from it.
    found = [
        span for span in found
        if span.label != "PHONE"
        or not any(span.start < end and start < span.end for start, end in aadhaar_ranges)
    ]

    # Known-provider validation keeps UPI IDs distinct from ordinary email.
    # Split a candidate at a recognized phone when two entities directly touch.
    for match in _UPI_CANDIDATE.finditer(text):
        value = match.group(0)
        start = match.start()
        for phone in (span for span in found if span.label == "PHONE"):
            if start <= phone.start < phone.end < match.end():
                suffix = text[phone.end:match.end()]
                if is_valid_upi(suffix):
                    start = phone.end
                    value = suffix
                    break
        if not is_valid_upi(value):
            continue
        found.append(Span(
            start=start,
            end=match.end(),
            label="UPI",
            text=value,
            source="regex",
            score=1.0,
        ))
    add_matches(_EMAIL_CANDIDATE, "EMAIL", is_valid_email)

    for match in _PINCODE_CANDIDATE.finditer(text):
        value = match.group(0)
        if is_valid_pincode(value) and _pincode_has_address_context(text, match.start()):
            found.append(Span(
                start=match.start(),
                end=match.end(),
                label="PINCODE",
                text=value,
                source="regex",
                score=1.0,
            ))

    return sorted(found, key=lambda span: (span.start, span.end, span.label))
