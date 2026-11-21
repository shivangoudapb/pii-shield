"""Shared typed schema for detector spans."""

from dataclasses import dataclass
from typing import Literal

SpanLabel = Literal[
    "PERSON",
    "LOCATION",
    "PHONE",
    "EMAIL",
    "AADHAAR",
    "PAN",
    "UPI",
    "PINCODE",
]
SpanSource = Literal["regex", "rules", "ner"]


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open character range and its detected entity metadata."""

    start: int
    end: int
    label: SpanLabel
    text: str
    source: SpanSource
    score: float
