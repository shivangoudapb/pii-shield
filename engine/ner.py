"""GLiNER-backed NER adapter with lazy CPU loading and safe chunk offsets."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from threading import Lock
from typing import Any, Protocol

from engine.constants import NON_PERSON_ROLE_WORDS
from engine.spans import Span, SpanLabel

DEFAULT_MODEL_NAME = "urchade/gliner_multi_pii-v1"
DEFAULT_LABELS = ("person", "address", "city")
DEFAULT_LABEL_MAPPING: dict[str, SpanLabel] = {
    "person": "PERSON",
    "address": "LOCATION",
    "city": "LOCATION",
}
_HONORIFIC = re.compile(r"(?i:(?:Dr|Mr|Mrs|Ms|Shri|Smt|Sri|Prof))\.?(?:[ \t]+|$)")
_TRAILING_JI = re.compile(r"[ \t]+ji$", re.IGNORECASE)
_PERSON_PREFIX_STOP = re.compile(
    r"(?i:(?:bhai|bhaiya|didi|candidate|applicant|hi+|hey+|hello|dear|yaar|"
    r"bro|from|to|with|for|by|cc|attn|pls|plz|please|arre|arey|regards|thanks|fwd))[ \t]+"
)
_LOWERCASE_PARTICLES = frozenset({"de", "da", "del", "van", "von", "bin", "al", "ul", "ur"})
_LEADING_LOWER_BEFORE_UPPER = re.compile(r"(?P<lead>[a-z]+)[ \t]+(?=[A-Z][a-z])")
_NER_WORD_BLOCKLIST = frozenset({
    "customer", "address", "client", "user", "person", "name",
})
_OPEN_QUOTES = frozenset({"'", '"', "‘", "“", "`"})
_CLOSE_QUOTES = frozenset({"'", '"', "’", "”", "`"})
_MODEL_CACHE: dict[str, Any] = {}
_MODEL_CACHE_LOCK = Lock()


class NerDetector(Protocol):
    """Interface implemented by model-backed and test NER detectors."""

    def detect(self, text: str) -> list[Span]:
        """Return NER spans for text without logging or persisting it."""
        ...


class FakeNer:
    """Deterministic test detector returning spans keyed by complete input text."""

    def __init__(self, spans_by_text: dict[str, list[Span]]) -> None:
        self._spans_by_text = {
            text: tuple(spans) for text, spans in spans_by_text.items()
        }

    def detect(self, text: str) -> list[Span]:
        return list(self._spans_by_text.get(text, ()))


def _load_model(model_name: str) -> Any:
    """Load GLiNER on CPU; importing the dependency is deferred until needed."""
    from gliner import GLiNER

    model = GLiNER.from_pretrained(model_name, map_location="cpu")
    if hasattr(model, "to"):
        model.to("cpu")
    if hasattr(model, "eval"):
        model.eval()
    return model


def _cached_model(model_name: str) -> Any:
    with _MODEL_CACHE_LOCK:
        if model_name not in _MODEL_CACHE:
            _MODEL_CACHE[model_name] = _load_model(model_name)
        return _MODEL_CACHE[model_name]


def _deduplicate(spans: list[Span]) -> list[Span]:
    """Collapse same-entity predictions that overlap across chunk windows."""
    selected: list[Span] = []
    for candidate in sorted(spans, key=lambda span: (-span.score, span.start, span.end)):
        normalized = " ".join(candidate.text.casefold().split())
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(selected)
                if existing.label == candidate.label
                and " ".join(existing.text.casefold().split()) == normalized
                and candidate.start < existing.end
                and existing.start < candidate.end
            ),
            None,
        )
        if duplicate_index is None:
            selected.append(candidate)
    return sorted(selected, key=lambda span: (span.start, span.end, span.label))


class GlinerNer:
    """NerDetector using ``urchade/gliner_multi_pii-v1`` on CPU by default."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        labels: Sequence[str] | None = None,
        label_mapping: Mapping[str, SpanLabel] | None = None,
        threshold: float = 0.3,
        chunk_size: int = 1800,
        chunk_overlap: int = 200,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if chunk_size < 2 or not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

        self.model_name = model_name
        self.labels = tuple(DEFAULT_LABELS if labels is None else labels)
        if not self.labels:
            raise ValueError("at least one GLiNER label is required")
        self.label_mapping = dict(DEFAULT_LABEL_MAPPING)
        if label_mapping:
            self.label_mapping.update(
                {label.casefold(): mapped for label, mapped in label_mapping.items()}
            )
        self.threshold = threshold
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _chunks(self, text: str):
        """Yield character windows with overlap to stay below model token limits."""
        step = self.chunk_size - self.chunk_overlap
        for start in range(0, len(text), step):
            end = min(start + self.chunk_size, len(text))
            yield start, end, text[start:end]
            if end == len(text):
                break

    def _to_span(self, chunk: str, chunk_start: int, entity: Mapping[str, Any]) -> Span | None:
        try:
            start = int(entity["start"])
            end = int(entity["end"])
            entity_text = entity["text"]
            model_label = str(entity["label"]).casefold()
            score = float(entity["score"])
        except (KeyError, TypeError, ValueError):
            return None

        if not isinstance(entity_text, str) or not (0 <= start < end <= len(chunk)):
            return None
        if chunk[start:end] != entity_text or score < self.threshold:
            return None

        label = self.label_mapping.get(model_label)
        if label is None:
            return None

        left, right = start, end
        while left < right and chunk[left].isspace():
            left += 1
        while right > left and chunk[right - 1].isspace():
            right -= 1

        if label == "PERSON":
            trailing_ji = _TRAILING_JI.search(chunk[left:right])
            if trailing_ji:
                right = left + trailing_ji.start()
                while right > left and chunk[right - 1].isspace():
                    right -= 1
            while left < right:
                honorific = _HONORIFIC.match(chunk[left:right])
                if honorific:
                    left += honorific.end()
                else:
                    prefix = _PERSON_PREFIX_STOP.match(chunk[left:right])
                    if prefix:
                        left += prefix.end()
                    else:
                        lower_lead = _LEADING_LOWER_BEFORE_UPPER.match(chunk[left:right])
                        if lower_lead and lower_lead.group("lead") not in _LOWERCASE_PARTICLES:
                            left += lower_lead.end()
                        else:
                            break
                while left < right and chunk[left].isspace():
                    left += 1

        if right - left <= 1:
            return None
        clean_text = chunk[left:right]
        if clean_text.casefold() in _NER_WORD_BLOCKLIST:
            return None
        if label == "PERSON":
            tokens = re.findall(r"[A-Za-z]+", clean_text)
            if any(tok.casefold() in NON_PERSON_ROLE_WORDS for tok in tokens):
                return None
        if label == "LOCATION":
            quoted_outside = (
                left > 0
                and right < len(chunk)
                and chunk[left - 1] in _OPEN_QUOTES
                and chunk[right] in _CLOSE_QUOTES
            )
            quoted_inside = (
                len(clean_text) >= 2
                and clean_text[0] in _OPEN_QUOTES
                and clean_text[-1] in _CLOSE_QUOTES
            )
            if (quoted_outside or quoted_inside) and "," not in clean_text and not any(
                ch.isdigit() for ch in clean_text
            ):
                return None
        full_start = chunk_start + left
        full_end = chunk_start + right
        return Span(
            start=full_start,
            end=full_end,
            label=label,
            text=clean_text,
            source="ner",
            score=score,
        )

    def detect(self, text: str) -> list[Span]:
        if not isinstance(text, str) or not text:
            return []

        model = _cached_model(self.model_name)
        spans: list[Span] = []
        for chunk_start, _chunk_end, chunk in self._chunks(text):
            entities = model.predict_entities(
                chunk,
                list(self.labels),
                threshold=self.threshold,
            )
            for entity in entities:
                span = self._to_span(chunk, chunk_start, entity)
                if span is not None and text[span.start:span.end] == span.text:
                    spans.append(span)
        return _deduplicate(spans)
