from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import engine.ner as ner_module
from engine.ner import GlinerNer


class MockModel:
    def __init__(self, predict):
        self.predict = predict
        self.calls = []
        self.device = None
        self.evaluated = False

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.evaluated = True
        return self

    def predict_entities(self, text, labels, threshold):
        self.calls.append((text, list(labels), threshold))
        return self.predict(text)


def install_mock_model(monkeypatch, model):
    loads = []
    monkeypatch.setattr(ner_module, "_MODEL_CACHE", {})
    monkeypatch.setattr(ner_module, "_load_model", lambda model_id: loads.append(model_id) or model)
    return loads


def entity(text, label="person", score=0.9, start=0, end=None):
    return {
        "text": text[start:end],
        "label": label,
        "score": score,
        "start": start,
        "end": len(text) if end is None else end,
    }


def test_default_labels_threshold_and_cpu_model_cached_once(monkeypatch):
    model = MockModel(lambda _text: [])
    loads = install_mock_model(monkeypatch, model)
    first = GlinerNer()
    second = GlinerNer()

    first.detect("first call")
    second.detect("second call")

    assert loads == ["urchade/gliner_multi_pii-v1"]
    assert [call[1] for call in model.calls] == [
        ["person", "address", "city"],
        ["person", "address", "city"],
    ]
    assert [call[2] for call in model.calls] == [0.3, 0.3]


def test_model_loader_uses_cpu_only(monkeypatch):
    model = MockModel(lambda _text: [])
    calls = []

    class FakeGLiNER:
        @staticmethod
        def from_pretrained(model_name, map_location):
            calls.append((model_name, map_location))
            return model

    monkeypatch.setitem(sys.modules, "gliner", SimpleNamespace(GLiNER=FakeGLiNER))

    assert ner_module._load_model("mock-model") is model
    assert calls == [("mock-model", "cpu")]
    assert model.device == "cpu"
    assert model.evaluated


def test_custom_labels_and_mapping_support_extra_entity_types(monkeypatch):
    text = "Sample Layout"
    model = MockModel(lambda chunk: [entity(chunk, "locality", start=0, end=len(chunk))])
    install_mock_model(monkeypatch, model)
    detector = GlinerNer(
        labels=["person", "locality"],
        label_mapping={"person": "PERSON", "locality": "LOCATION"},
        threshold=0.42,
    )

    spans = detector.detect(text)

    assert model.calls[0][1:] == (["person", "locality"], 0.42)
    assert [(span.text, span.label, span.source, span.score) for span in spans] == [
        ("Sample Layout", "LOCATION", "ner", 0.9)
    ]


@pytest.mark.parametrize("title", ["Dr", "Dr.", "Mr", "Mrs", "Ms", "Shri", "Smt", "Sri", "Prof"])
def test_person_postprocessing_trims_leading_honorific(title, monkeypatch):
    text = f"{title} Venkatesh Iyer"
    model = MockModel(lambda chunk: [entity(chunk, start=0, end=len(chunk))])
    install_mock_model(monkeypatch, model)

    span = GlinerNer().detect(text)[0]

    assert span.text == "Venkatesh Iyer"
    assert text[span.start:span.end] == span.text
    assert span.start == len(title) + 1


def test_person_postprocessing_trims_trailing_ji_and_adjusts_offsets(monkeypatch):
    text = "Dr. Venkatesh Iyer ji"
    model = MockModel(lambda chunk: [entity(chunk, start=0, end=len(chunk))])
    install_mock_model(monkeypatch, model)

    spans = GlinerNer().detect(text)

    assert len(spans) == 1
    assert spans[0].text == "Venkatesh Iyer"
    assert spans[0].start == 4
    assert spans[0].end == 18
    assert text[spans[0].start:spans[0].end] == spans[0].text


def test_empty_one_character_and_mismatched_predictions_are_dropped(monkeypatch):
    text = "A Dr. Xyz"
    predictions = [
        {"text": "A", "label": "person", "score": 0.9, "start": 0, "end": 1},
        {"text": "Dr.", "label": "person", "score": 0.9, "start": 2, "end": 5},
        {"text": "Wrong", "label": "person", "score": 0.9, "start": 6, "end": 9},
    ]
    model = MockModel(lambda _chunk: predictions)
    install_mock_model(monkeypatch, model)

    assert GlinerNer().detect(text) == []


def test_predictions_below_threshold_are_dropped(monkeypatch):
    text = "Aarohi Menon"
    model = MockModel(lambda chunk: [entity(chunk, score=0.29)])
    install_mock_model(monkeypatch, model)

    assert GlinerNer(threshold=0.3).detect(text) == []


def test_chunking_remaps_offsets_and_deduplicates_overlap_predictions(monkeypatch):
    text = "0123456789AliceXYZ"

    def predict(chunk):
        if "Alice" not in chunk:
            return []
        start = chunk.index("Alice")
        return [entity(chunk, start=start, end=start + len("Alice"))]

    model = MockModel(predict)
    install_mock_model(monkeypatch, model)
    detector = GlinerNer(chunk_size=15, chunk_overlap=5)

    spans = detector.detect(text)

    assert len(model.calls) == 2
    assert all(len(call[0]) <= 15 for call in model.calls)
    assert len(spans) == 1
    assert spans[0].start == 10
    assert spans[0].end == 15
    assert spans[0].text == "Alice"
    assert text[spans[0].start:spans[0].end] == spans[0].text


def test_chunk_after_first_window_is_remapped_to_full_text(monkeypatch):
    text = "x" * 20 + "Kavya Rao" + " y"

    def predict(chunk):
        if "Kavya Rao" not in chunk:
            return []
        start = chunk.index("Kavya Rao")
        return [entity(chunk, start=start, end=start + len("Kavya Rao"))]

    model = MockModel(predict)
    install_mock_model(monkeypatch, model)
    spans = GlinerNer(chunk_size=15, chunk_overlap=5).detect(text)

    assert len(spans) == 1
    assert spans[0].start == 20
    assert spans[0].end == 29
    assert text[spans[0].start:spans[0].end] == "Kavya Rao"


def test_empty_input_does_not_load_model(monkeypatch):
    loads = install_mock_model(monkeypatch, MockModel(lambda _text: []))
    assert GlinerNer().detect("") == []
    assert loads == []


@pytest.mark.slow
def test_real_gliner_model_finds_expected_person_names():
    detector = GlinerNer()
    cases = [
        (
            "hey sagar can u share ur resume, mine is rahul sharma btw",
            ["sagar", "rahul sharma"],
        ),
        (
            "Student list: Priya Nair, Mohammed Irfan, Jyoti Patil, K. S. Manjunath",
            ["Priya Nair", "Mohammed Irfan", "Jyoti Patil", "K. S. Manjunath"],
        ),
        ("Regards, Dr. Venkatesh Iyer", ["Venkatesh Iyer"]),
    ]

    for text, expected_names in cases:
        detected = [span.text.casefold() for span in detector.detect(text) if span.label == "PERSON"]
        assert all(any(name.casefold() in item for item in detected) for name in expected_names)


@pytest.mark.parametrize(
    "prefix",
    ["bhai", "Candidate", "hii", "hiii", "hey", "hi", "dear", "yaar", "from", "to", "pls", "arre"],
)
def test_person_postprocessing_strips_stopword_prefixes(prefix, monkeypatch):
    text = f"{prefix} Rohan Verma"
    model = MockModel(lambda chunk: [entity(chunk, start=0, end=len(chunk))])
    install_mock_model(monkeypatch, model)

    spans = GlinerNer().detect(text)

    assert len(spans) == 1
    assert spans[0].text == "Rohan Verma"
    assert spans[0].start == len(prefix) + 1
    assert text[spans[0].start:spans[0].end] == "Rohan Verma"


@pytest.mark.parametrize(
    ("raw_span", "expected_name"),
    [
        ("hii bhai nikhita reddy", "nikhita reddy"),
        ("hey Dr. Venkatesh Iyer", "Venkatesh Iyer"),
        ("urgently Ananya Rao", "Ananya Rao"),
        ("nikhita reddy", "nikhita reddy"),
    ],
)
def test_person_postprocessing_handles_chained_prefixes_and_lowercase_names(
    raw_span, expected_name, monkeypatch
):
    model = MockModel(lambda chunk: [entity(chunk, start=0, end=len(chunk))])
    install_mock_model(monkeypatch, model)

    spans = GlinerNer().detect(raw_span)

    assert len(spans) == 1
    assert spans[0].text == expected_name
    assert raw_span[spans[0].start:spans[0].end] == expected_name


@pytest.mark.parametrize(
    ("word", "label"),
    [
        ("Customer", "person"),
        ("address", "address"),
        ("Client", "person"),
        ("User", "person"),
        ("Person", "person"),
        ("Name", "person"),
    ],
)
def test_ner_word_blocklist_drops_false_alarm_words(word, label, monkeypatch):
    model = MockModel(lambda chunk: [entity(chunk, label=label, start=0, end=len(chunk))])
    install_mock_model(monkeypatch, model)

    assert GlinerNer().detect(word) == []


@pytest.mark.parametrize(
    "text,quoted_part",
    [
        ("playlist title: ‘Lotus Lane’ (not an address)", "Lotus Lane"),
        ('now playing "Maple Road" live', "Maple Road"),
        ("book review: 'Cedar Cross' chapter 2", "Cedar Cross"),
    ],
)
def test_ner_drops_quoted_non_address_location_titles(text, quoted_part, monkeypatch):
    start = text.index(quoted_part)
    end = start + len(quoted_part)
    model = MockModel(lambda chunk: [entity(chunk, label="address", start=start, end=end)])
    install_mock_model(monkeypatch, model)

    assert GlinerNer().detect(text) == []
