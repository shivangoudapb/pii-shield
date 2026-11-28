"""Regex-based detection for validated structured Indian PII."""

import re
from collections.abc import Callable

from engine.spans import Span, SpanLabel
from engine.validators import (
    is_valid_aadhaar,
    is_valid_bank_account,
    is_valid_dob,
    is_valid_driving_license,
    is_valid_email,
    is_valid_ip_address,
    is_valid_pan,
    is_valid_passport,
    is_valid_phone,
    is_valid_pincode,
    is_valid_upi,
    is_valid_voter_id,
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
_PASSPORT_CANDIDATE = re.compile(r"(?<![A-Za-z0-9-])[A-Z][0-9]{7}(?![A-Za-z0-9])")
_VOTER_ID_CANDIDATE = re.compile(r"(?<![A-Za-z0-9-])[A-Z]{3}[0-9]{7}(?![A-Za-z0-9])")
_DRIVING_LICENSE_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9-])[A-Z]{2}[ -]?[0-9]{2}[ -]?(?:19|20)[0-9]{2}[ -]?[0-9]{7}(?![A-Za-z0-9])"
)
_DOB_CONTEXT_CANDIDATE = re.compile(
    r"(?i:\b(?:d\.?o\.?b\.?|date\s+of\s+birth|birth\s*date|born(?:\s+on)?))"
    r"[ \t]*[:=-]?[ \t]*"
    r"(?P<dob>\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}[ \t]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r",?[ \t]+\d{4})(?![0-9])"
)
_BANK_ACCOUNT_CONTEXT_CANDIDATE = re.compile(
    r"(?i:\b(?:bank\s+account(?:\s*(?:no\.?|number|num|#))?|"
    r"account\s*(?:no\.?|number|num|#)|"
    r"a/c(?:\s*(?:no\.?|number|num|#))?|"
    r"acc(?:ount)?\s*no\.?))"
    r"[ \t]*[:=-]?[ \t]*"
    r"(?P<acct>[0-9]{3,18}(?:[ -][0-9]{3,6}){0,3})(?![0-9])"
)
_IP_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9.])(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
    r"(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}(?![A-Za-z0-9.])|"
    r"(?<![A-Za-z0-9:])(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}(?![A-Za-z0-9:])|"
    r"(?<![A-Za-z0-9:])(?:[0-9A-Fa-f]{1,4}:){1,7}:[0-9A-Fa-f]{1,4}(?![A-Za-z0-9:])"
)
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

    # Detect context-gated Bank Accounts and Aadhaar before phones so overlapping
    # numeric substrings are not misclassified.
    for match in _BANK_ACCOUNT_CONTEXT_CANDIDATE.finditer(text):
        acct_start, acct_end = match.span("acct")
        acct_val = text[acct_start:acct_end]
        if is_valid_bank_account(acct_val):
            found.append(Span(
                start=acct_start,
                end=acct_end,
                label="BANK_ACCOUNT",
                text=acct_val,
                source="regex",
                score=1.0,
            ))
    for match in _AADHAAR_CANDIDATE.finditer(text):
        if any(match.start() < span.end and span.start < match.end() for span in found):
            continue
        value = match.group(0)
        if is_valid_aadhaar(value):
            found.append(Span(
                start=match.start(),
                end=match.end(),
                label="AADHAAR",
                text=value,
                source="regex",
                score=1.0,
            ))
    protected_numeric_ranges = [(span.start, span.end) for span in found]

    add_matches(_PAN_CANDIDATE, "PAN", is_valid_pan)
    add_matches(_DRIVING_LICENSE_CANDIDATE, "DRIVING_LICENSE", is_valid_driving_license)
    dl_ranges = [(span.start, span.end) for span in found if span.label == "DRIVING_LICENSE"]
    for pattern, label, validator in (
        (_VOTER_ID_CANDIDATE, "VOTER_ID", is_valid_voter_id),
        (_PASSPORT_CANDIDATE, "PASSPORT", is_valid_passport),
    ):
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in dl_ranges):
                continue
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

    add_matches(_PHONE_CANDIDATE, "PHONE", is_valid_phone)
    # Never emit a phone subspan from inside an Aadhaar, Bank Account, or Driving Licence.
    block_phone_ranges = protected_numeric_ranges + dl_ranges
    found = [
        span for span in found
        if span.label != "PHONE"
        or not any(span.start < end and start < span.end for start, end in block_phone_ranges)
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
        if any(match.start() < span.end and span.start < match.end() for span in found):
            continue
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

    for match in _DOB_CONTEXT_CANDIDATE.finditer(text):
        dob_start, dob_end = match.span("dob")
        dob_val = text[dob_start:dob_end]
        if is_valid_dob(dob_val):
            found.append(Span(
                start=dob_start,
                end=dob_end,
                label="DOB",
                text=dob_val,
                source="regex",
                score=1.0,
            ))

    add_matches(_IP_CANDIDATE, "IP_ADDRESS", is_valid_ip_address)

    return sorted(found, key=lambda span: (span.start, span.end, span.label))
