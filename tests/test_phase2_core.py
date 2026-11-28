import json
from pathlib import Path

import pytest

import redactor as redactor_module
from engine.detect import detect
from engine.merge import merge_spans
from engine.ner import FakeNer, NerDetector
from engine.regex_layer import detect_structured_pii
from engine.rules import detect_rule_pii
from engine.spans import Span
from redactor import redact, restore


def test_fake_ner_returns_spans_from_supplied_text_map():
    text = "Name: Kavya Rao"
    expected = [Span(6, 15, "PERSON", "Kavya Rao", "ner", 0.91)]
    detector: NerDetector = FakeNer({text: expected})

    assert detector.detect(text) == expected
    assert detector.detect("unmapped text") == []


@pytest.mark.parametrize("title", ["Mr.", "Mrs.", "Ms.", "Dr.", "Shri", "Smt.", "Sri"])
def test_title_rule_excludes_title_from_person_span(title):
    text = f"{title} Aarohi Menon joined the call."
    spans = detect_rule_pii(text)
    people = [span for span in spans if span.label == "PERSON"]

    assert len(people) == 1
    assert people[0].text == "Aarohi Menon"
    assert text[people[0].start:people[0].end] == "Aarohi Menon"
    assert people[0].source == "rules"


def test_name_field_rule_detects_person_value_only():
    text = "Name: Kavya Rao\nPhone: 9845012345"
    people = [span for span in detect_rule_pii(text) if span.label == "PERSON"]
    assert [(span.text, span.source) for span in people] == [("Kavya Rao", "rules")]


def test_name_field_supports_case_and_spacing_variants_for_redaction_key():
    text = "Name: Ananya Rao\nName: ananya   rao"
    redacted, mapping = redact(text)

    assert redacted == "Name: [PERSON_1]\nName: [PERSON_1]"
    assert mapping == {"[PERSON_1]": "Ananya Rao"}


def test_signoff_rules_detect_names_after_regards_and_thanks():
    text = "Regards,\nRohan Das\nThanks, Meera Nair"
    people = [span for span in detect_rule_pii(text) if span.label == "PERSON"]
    assert [span.text for span in people] == ["Rohan Das", "Meera Nair"]


def test_regex_span_wins_over_rules_and_longer_ner_span():
    text = "Call 9845012345 today"
    phone = detect_structured_pii(text)[0]
    rule = Span(0, len(text), "PERSON", text, "rules", 1.0)
    ner = Span(0, len(text), "PERSON", text, "ner", 0.99)

    assert merge_spans([ner, rule, phone]) == [phone]


def test_rules_span_wins_over_overlapping_ner_span():
    rule = Span(3, 9, "PERSON", "Aarohi", "rules", 1.0)
    ner = Span(0, 12, "LOCATION", "Dr Aarohi xx", "ner", 0.99)

    assert merge_spans([ner, rule]) == [rule]


def test_same_source_overlap_keeps_the_longer_span():
    text = "abcdefghij"
    short = Span(2, 7, "PERSON", text[2:7], "rules", 1.0)
    long = Span(0, 10, "LOCATION", text, "rules", 1.0)

    assert merge_spans([short, long]) == [long]


def test_merge_drops_ner_below_configured_threshold():
    low = Span(0, 4, "PERSON", "low!", "ner", 0.49)
    high = Span(5, 10, "PERSON", "high!", "ner", 0.8)

    assert merge_spans([low, high], ner_score_threshold=0.7) == [high]


def test_detect_runs_regex_rules_and_supplied_ner_then_merges():
    text = "Dr. Nila Rao lives in Bengaluru; call 9845012345."
    location_start = text.index("Bengaluru")
    ner_span = Span(location_start, location_start + len("Bengaluru"), "LOCATION", "Bengaluru", "ner", 0.9)
    spans = detect(text, FakeNer({text: [ner_span]}))

    assert [(span.label, span.text, span.source) for span in spans] == [
        ("PERSON", "Nila Rao", "rules"),
        ("LOCATION", "Bengaluru", "ner"),
        ("PHONE", "9845012345", "regex"),
    ]


def test_same_name_twice_uses_the_same_placeholder():
    text = "Name: Ananya Rao\nRegards,\nAnanya Rao"
    redacted, mapping = redact(text)

    assert redacted.count("[PERSON_1]") == 2
    assert mapping == {"[PERSON_1]": "Ananya Rao"}


def test_redact_uses_supplied_fake_ner_detector():
    text = "I met Ananya Rao today."
    start = text.index("Ananya Rao")
    span = Span(start, start + len("Ananya Rao"), "PERSON", "Ananya Rao", "ner", 0.95)

    redacted, mapping = redact(text, FakeNer({text: [span]}))

    assert redacted == "I met [PERSON_1] today."
    assert mapping == {"[PERSON_1]": "Ananya Rao"}


def test_redact_normalizes_entity_case_and_whitespace(monkeypatch):
    text = "Ananya Rao | ananya   rao"
    fake_spans = [
        Span(0, 10, "PERSON", "Ananya Rao", "rules", 1.0),
        Span(13, 25, "PERSON", "ananya   rao", "rules", 1.0),
    ]
    monkeypatch.setattr(redactor_module, "detect", lambda _text, _ner_detector=None: fake_spans)

    redacted, mapping = redact(text)
    assert redacted == "[PERSON_1] | [PERSON_1]"
    assert mapping == {"[PERSON_1]": "Ananya Rao"}


def test_restore_round_trip_for_every_dev_item_with_regex_and_rules_only():
    dev_path = Path(__file__).parents[1] / "eval" / "dev.jsonl"
    items = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines()]

    for item in items:
        redacted, mapping = redact(item["text"])
        assert restore(redacted, mapping) == item["text"], item["id"]


def test_restore_accepts_case_changed_placeholder_and_punctuation_edits():
    redacted, mapping = redact("Name: Ananya Rao.")
    placeholder = next(iter(mapping)).lower()

    assert restore(f"({placeholder})!", mapping) == "(Ananya Rao)!"


def test_restore_leaves_unknown_placeholders_untouched():
    assert restore("Keep [UNKNOWN_7] as written.", {"[PERSON_1]": "Ananya Rao"}) == (
        "Keep [UNKNOWN_7] as written."
    )


def test_redaction_does_not_log_raw_text(caplog):
    text = "Name: Ananya Rao; call 9845012345"
    with caplog.at_level("DEBUG"):
        redact(text)

    assert caplog.text == ""
    assert text not in caplog.text


def test_reversed_signoff_rule_detects_surname_comma_firstname():
    text = "Regards,\nKaur, Jasmeet\nThanks,\nKamath, Chetan"
    people = [span for span in detect_rule_pii(text) if span.label == "PERSON"]
    assert [span.text for span in people] == ["Kaur, Jasmeet", "Kamath, Chetan"]


def test_contextual_name_rules_detect_from_followup_shipto_nickname_roster_circular_update():
    text = (
        "From: Aarohi Menon\n"
        "Please follow up with Senthil Iyer today.\n"
        "Ship to Yasmin Pathan at 18 Cedar Cross.\n"
        "Details (nickname Simry) and (surname on roster: Dhillon).\n"
        "College circular — Mukta; Hostel update for Madhurima Sen — paid."
    )
    people = [span.text for span in detect_rule_pii(text) if span.label == "PERSON"]
    assert people == [
        "Aarohi Menon",
        "Senthil Iyer",
        "Yasmin Pathan",
        "Simry",
        "Dhillon",
        "Mukta",
        "Madhurima Sen",
    ]


@pytest.mark.parametrize(
    ("text", "expected_location"),
    [
        (
            "Deliver to 41 Lotus Lane, Test Garden, Hyderabad tomorrow.",
            "41 Lotus Lane, Test Garden, Hyderabad",
        ),
        (
            "Address: 96 Maple Road, Sample Nagar, Hyderabad, 500034",
            "96 Maple Road, Sample Nagar, Hyderabad",
        ),
        (
            "Office at 2nd Cross, HSR Layout, Bengaluru.",
            "2nd Cross, HSR Layout, Bengaluru",
        ),
        (
            "Residence: Flat 4B, 12 MG Road, Indiranagar, Bengaluru 560038",
            "Flat 4B, 12 MG Road, Indiranagar, Bengaluru",
        ),
        (
            "Campus map desk: 23 River View Road, Fictional Sector 4, Mysuru, PIN 355322",
            "23 River View Road, Fictional Sector 4, Mysuru",
        ),
    ],
)
def test_structured_address_rule_detects_full_indian_addresses(text, expected_location):
    locations = [span for span in detect_rule_pii(text) if span.label == "LOCATION"]
    assert len(locations) == 1
    assert locations[0].text == expected_location
    assert text[locations[0].start:locations[0].end] == expected_location
    assert locations[0].source == "rules"


def test_detect_replaces_split_ner_address_fragments_with_full_address():
    text = "Ship to 96 Maple Road, Sample Nagar, Hyderabad, 500034"
    s1 = text.index("96 Maple Road")
    s2 = text.index("Hyderabad")
    partial_ner = FakeNer({
        text: [
            Span(s1, s1 + len("96 Maple Road"), "LOCATION", "96 Maple Road", "ner", 0.88),
            Span(s2, s2 + len("Hyderabad"), "LOCATION", "Hyderabad", "ner", 0.92),
        ]
    })
    spans = detect(text, partial_ner)
    assert [(span.label, span.text) for span in spans] == [
        ("LOCATION", "96 Maple Road, Sample Nagar, Hyderabad"),
        ("PINCODE", "500034"),
    ]


def test_detect_merges_adjacent_locality_and_city_ner_spans_but_not_city_lists():
    addr_text = "Relocating near Indiranagar, Bengaluru next month."
    i_start = addr_text.index("Indiranagar")
    b_start = addr_text.index("Bengaluru")
    merged = detect(
        addr_text,
        FakeNer({
            addr_text: [
                Span(i_start, i_start + len("Indiranagar"), "LOCATION", "Indiranagar", "ner", 0.82),
                Span(b_start, b_start + len("Bengaluru"), "LOCATION", "Bengaluru", "ner", 0.90),
            ]
        }),
    )
    assert [(s.label, s.text) for s in merged] == [("LOCATION", "Indiranagar, Bengaluru")]

    cities_text = "Offices in Mumbai, Pune"
    m_start = cities_text.index("Mumbai")
    p_start = cities_text.index("Pune")
    separate = detect(
        cities_text,
        FakeNer({
            cities_text: [
                Span(m_start, m_start + len("Mumbai"), "LOCATION", "Mumbai", "ner", 0.90),
                Span(p_start, p_start + len("Pune"), "LOCATION", "Pune", "ner", 0.90),
            ]
        }),
    )
    assert [(s.label, s.text) for s in separate] == [
        ("LOCATION", "Mumbai"),
        ("LOCATION", "Pune"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Thanks,\nOperations Desk",
        "Regards,\nFinance Team",
        "Dear Hiring Committee,\nPlease review.",
        "From: Customer Support\nTicket closed.",
    ],
)
def test_rules_do_not_flag_role_or_department_signoffs_as_person(text):
    assert [s for s in detect_rule_pii(text) if s.label == "PERSON"] == []


def test_rules_handle_apostrophe_names_email_headers_and_reversed_from_field():
    text = (
        "From: Pathan, Jyoti\n"
        "From: Ruth D'Costa <ruth@example.com>\n"
        "Prof. K. M. Rajendran reviewed the paper.\n"
        "Placement record: Name: A. Rao, Address: Plot 42, Indiranagar, Bengaluru"
    )
    spans = detect_rule_pii(text)
    people = [s.text for s in spans if s.label == "PERSON"]
    locations = [s.text for s in spans if s.label == "LOCATION"]
    assert people == ["Pathan, Jyoti", "Ruth D'Costa", "K. M. Rajendran", "A. Rao"]
    assert locations == ["Plot 42, Indiranagar, Bengaluru"]


@pytest.mark.parametrize(
    "company_snippet",
    [
        "Vendor partner Sundaram Finance approved the invoice.",
        "Previously at Narayana Health and Bajaj Electricals.",
        " Ledger matched Kirloskar Brothers and Lakshmi Machine Works.",
        "Supplier Ravi Kumar & Sons shipped via Mahindra Logistics.",
    ],
)
def test_detect_suppresses_person_false_alarms_inside_company_names(company_snippet):
    # Simulate NER tagging the leading personal/deity root inside company names.
    words = ["Sundaram", "Narayana", "Bajaj", "Kirloskar", "Lakshmi", "Ravi Kumar", "Mahindra"]
    fake_spans = []
    for word in words:
        if word in company_snippet:
            idx = company_snippet.index(word)
            fake_spans.append(Span(idx, idx + len(word), "PERSON", word, "ner", 0.91))
    assert detect(company_snippet, FakeNer({company_snippet: fake_spans})) == []


def test_underscore_labels_redact_and_restore_round_trip():
    text = (
        "Voter ID DLQ4019283, DL KA-01-2020-1234567, "
        "A/c No: 309182736451, DOB: 14 Aug 1998, Passport J8364921, IP 49.37.142.88"
    )
    redacted, mapping = redact(text)
    assert "[VOTER_ID_1]" in redacted
    assert "[DRIVING_LICENSE_1]" in redacted
    assert "[BANK_ACCOUNT_1]" in redacted
    assert "[DOB_1]" in redacted
    assert "[PASSPORT_1]" in redacted
    assert "[IP_ADDRESS_1]" in redacted
    assert restore(redacted, mapping) == text
    assert restore(redacted.lower(), mapping) == text.lower().replace(
        "dlq4019283", "DLQ4019283"
    ).replace("ka-01-2020-1234567", "KA-01-2020-1234567").replace(
        "14 aug 1998", "14 Aug 1998"
    ).replace("j8364921", "J8364921")
