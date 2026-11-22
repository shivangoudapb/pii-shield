import pytest

from engine.regex_layer import detect_structured_pii
from engine.spans import Span


def labels_for(text):
    return [(span.label, span.text) for span in detect_structured_pii(text)]


def test_invalid_aadhaar_lookalike_is_not_reported():
    assert not any(label == "AADHAAR" for label, _ in labels_for("ID 234567890123"))


def test_grouped_aadhaar_is_one_span_and_not_phone():
    text = "Aadhaar 2345 6789 0124"
    spans = detect_structured_pii(text)
    aadhaar = [span for span in spans if span.label == "AADHAAR"]

    assert len(aadhaar) == 1
    assert aadhaar[0].text == "2345 6789 0124"
    assert not any(span.label == "PHONE" for span in spans)


def test_hyphenated_aadhaar_is_one_span():
    spans = detect_structured_pii("Aadhaar 2345-6789-0124")
    assert [(span.label, span.text) for span in spans] == [("AADHAAR", "2345-6789-0124")]


@pytest.mark.parametrize("phone", [
    "+91 98450 12345",
    "09845012345",
    "98450-12345",
    "9845012345",
])
def test_indian_phone_formats(phone):
    spans = detect_structured_pii(f"Call {phone} please")
    assert [(span.label, span.text) for span in spans] == [("PHONE", phone)]


@pytest.mark.parametrize("number", [
    "1234567890123456",
    "1198450123456789",  # Contains a valid phone-shaped substring.
    "Order number 20269845012345",
])
def test_phone_does_not_match_inside_longer_digit_sequence(number):
    assert not any(span.label == "PHONE" for span in detect_structured_pii(number))


@pytest.mark.parametrize("number", ["1234567890", "5234567890"])
def test_order_ids_starting_one_to_five_are_not_phones(number):
    assert not any(span.label == "PHONE" for span in detect_structured_pii(number))


def test_upi_and_email_are_distinguished():
    text = "UPI name@okhdfcbank; email name@gmail.com"
    assert labels_for(text) == [
        ("UPI", "name@okhdfcbank"),
        ("EMAIL", "name@gmail.com"),
    ]


def test_identifiers_before_sentence_punctuation_keep_exact_span():
    text = "Pay name@okhdfcbank and email sample@example.com."
    spans = detect_structured_pii(text)
    assert [(span.label, span.text) for span in spans] == [
        ("UPI", "name@okhdfcbank"),
        ("EMAIL", "sample@example.com"),
    ]


@pytest.mark.parametrize("text", [
    "Deliver to Bengaluru 560001",
    "Near MG Cross, 560001",
    "Sector 4 560001",
    "Flat 2, 560001",
])
def test_pincode_flagged_in_address_context(text):
    assert ("PINCODE", "560001") in labels_for(text)


@pytest.mark.parametrize("text", [
    "OTP 560001",
    "Order number 560001",
    "Order ID: 560001",
    "Verification code 560001",
    "OTP, 560001",
])
def test_otp_and_order_code_lookalikes_are_not_pincodes(text):
    assert not any(label == "PINCODE" for label, _ in labels_for(text))


def test_two_pii_items_next_to_each_other_are_both_found():
    text = "9845012345name@okhdfcbank"
    spans = detect_structured_pii(text)
    assert [(span.label, span.text) for span in spans] == [
        ("PHONE", "9845012345"),
        ("UPI", "name@okhdfcbank"),
    ]


def test_all_spans_slice_the_original_text_exactly():
    text = "PAN ABCDE1234F, phone +91 98450 12345, mail name@gmail.com"
    for span in detect_structured_pii(text):
        assert text[span.start:span.end] == span.text
        assert span.source == "regex"
        assert span.end > span.start


def test_shared_span_schema_has_all_required_fields():
    span = Span(2, 6, "PHONE", "1234", "regex", 1.0)
    assert (span.start, span.end, span.label, span.text, span.source, span.score) == (
        2, 6, "PHONE", "1234", "regex", 1.0
    )
