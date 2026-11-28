"""Public Python library interface for PII Shield."""

from engine.detect import detect
from engine.ner import FakeNer, GlinerNer, NerDetector
from engine.spans import Span, SpanLabel, SpanSource
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
    normalize_aadhaar,
    normalize_phone,
    verhoeff_check,
)
from redactor import redact, restore

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "FakeNer",
    "GlinerNer",
    "NerDetector",
    "Span",
    "SpanLabel",
    "SpanSource",
    "detect",
    "is_valid_aadhaar",
    "is_valid_bank_account",
    "is_valid_dob",
    "is_valid_driving_license",
    "is_valid_email",
    "is_valid_ip_address",
    "is_valid_pan",
    "is_valid_passport",
    "is_valid_phone",
    "is_valid_pincode",
    "is_valid_upi",
    "is_valid_voter_id",
    "normalize_aadhaar",
    "normalize_phone",
    "redact",
    "restore",
    "verhoeff_check",
]
