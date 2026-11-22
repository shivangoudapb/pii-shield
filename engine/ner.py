"""Stub named-entity detector interface for the engine."""

from typing import Protocol

from engine.spans import Span


class NerDetector(Protocol):
    """Interface implemented by any model-backed or test NER detector."""

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
