"""Pure validators for Indian structured identifiers."""

from datetime import date
import ipaddress
import re

from engine.constants import INDIAN_STATE_CODES, UPI_PROVIDERS

# Verhoeff multiplication table (d), permutation table (p), and inverse table
# (inv), as published in the standard Verhoeff algorithm description.
_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)

_AADHAAR_RE = re.compile(r"^[2-9][0-9]{3}(?:[ -]?[0-9]{4}){2}$")
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$", re.IGNORECASE)
_PHONE_RE = re.compile(r"^(?:(?:\+91|91|0)[ -]?)?[6-9][0-9]{4}[ -]?[0-9]{5}$")
_UPI_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]{0,254})@([A-Za-z0-9.-]+)$")
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
_PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")
_PASSPORT_RE = re.compile(r"^[A-Z][0-9]{7}$", re.IGNORECASE)
_VOTER_ID_RE = re.compile(r"^[A-Z]{3}[0-9]{7}$", re.IGNORECASE)
_DRIVING_LICENSE_RE = re.compile(
    r"^([A-Z]{2})[ -]?([0-9]{2})[ -]?([0-9]{4})[ -]?([0-9]{7})$", re.IGNORECASE
)
_BANK_ACCOUNT_RE = re.compile(r"^[0-9]+(?:[ -][0-9]+)*$")
_DOB_DMY_RE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$")
_DOB_YMD_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DOB_TEXT_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})$")
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def verhoeff_check(number: str) -> bool:
    """Return whether a non-empty ASCII digit string has a valid Verhoeff checksum."""
    if not isinstance(number, str) or not number or not number.isascii() or not number.isdigit():
        return False
    checksum = 0
    for index, digit in enumerate(reversed(number)):
        checksum = _D[checksum][_P[index % 8][int(digit)]]
    return checksum == 0


def normalize_aadhaar(value: str) -> str | None:
    """Return a valid Aadhaar as 12 digits, otherwise None."""
    if not isinstance(value, str) or not _AADHAAR_RE.fullmatch(value):
        return None
    digits = value.replace(" ", "").replace("-", "")
    if len(digits) != 12 or digits[0] in "01" or not verhoeff_check(digits):
        return None
    return digits


def is_valid_aadhaar(value: str) -> bool:
    return normalize_aadhaar(value) is not None


def is_valid_pan(value: str) -> bool:
    return isinstance(value, str) and _PAN_RE.fullmatch(value) is not None


def normalize_phone(value: str) -> str | None:
    """Return a valid Indian mobile number as 10 digits, otherwise None."""
    if not isinstance(value, str) or not _PHONE_RE.fullmatch(value):
        return None
    digits = re.sub(r"[ +\-]", "", value)
    if digits.startswith("+91"):
        digits = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 and digits[0] in "6789" else None


def is_valid_phone(value: str) -> bool:
    return normalize_phone(value) is not None


def is_valid_upi(value: str) -> bool:
    """Accept handle@known-provider IDs; reject ordinary email domains."""
    if not isinstance(value, str):
        return False
    match = _UPI_RE.fullmatch(value)
    return bool(match and match.group(2).lower() in UPI_PROVIDERS)


def is_valid_pincode(value: str) -> bool:
    """Check only the six-digit pincode format; contextual detection is separate."""
    return isinstance(value, str) and _PINCODE_RE.fullmatch(value) is not None


def is_valid_email(value: str) -> bool:
    return isinstance(value, str) and _EMAIL_RE.fullmatch(value) is not None


def is_valid_passport(value: str) -> bool:
    """Validate Indian passport format ([A-Z][0-9]{7}, non-zero serial)."""
    if not isinstance(value, str) or not value.isascii() or not _PASSPORT_RE.fullmatch(value):
        return False
    return value[1:] != "0000000"


def is_valid_voter_id(value: str) -> bool:
    """Validate Indian Voter ID / EPIC format ([A-Z]{3}[0-9]{7}, non-zero serial)."""
    if not isinstance(value, str) or not value.isascii() or not _VOTER_ID_RE.fullmatch(value):
        return False
    return value[3:] != "0000000"


def is_valid_driving_license(value: str) -> bool:
    """Validate standard 15-character Indian Parivahan Driving Licence format."""
    if not isinstance(value, str) or not value.isascii():
        return False
    match = _DRIVING_LICENSE_RE.fullmatch(value)
    if not match:
        return False
    state, rto, year_str, serial = match.groups()
    if state.upper() not in INDIAN_STATE_CODES or rto == "00" or serial == "0000000":
        return False
    year = int(year_str)
    return 1950 <= year <= date.today().year


def is_valid_dob(value: str) -> bool:
    """Validate calendar Date of Birth strings in common Indian/ISO formats."""
    if not isinstance(value, str) or not value.isascii():
        return False
    text = value.strip()
    dmy = _DOB_DMY_RE.fullmatch(text)
    if dmy:
        day, month, year = (int(part) for part in dmy.groups())
    else:
        ymd = _DOB_YMD_RE.fullmatch(text)
        if ymd:
            year, month, day = (int(part) for part in ymd.groups())
        else:
            named = _DOB_TEXT_RE.fullmatch(text)
            if not named:
                return False
            day_str, month_name, year_str = named.groups()
            month = _MONTHS.get(month_name.lower(), 0)
            if not month:
                return False
            day, year = int(day_str), int(year_str)

    if not (1900 <= year <= date.today().year):
        return False
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def is_valid_bank_account(value: str) -> bool:
    """Validate 9-to-18-digit Indian bank account numbers (with optional separators)."""
    if not isinstance(value, str) or not value.isascii() or not _BANK_ACCOUNT_RE.fullmatch(value):
        return False
    digits = value.replace(" ", "").replace("-", "")
    return 9 <= len(digits) <= 18 and int(digits) > 0


def is_valid_ip_address(value: str) -> bool:
    """Validate IPv4 or IPv6 literal addresses."""
    if not isinstance(value, str) or not value.isascii() or "/" in value:
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True
