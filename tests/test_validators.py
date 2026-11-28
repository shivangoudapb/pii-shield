import pytest

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
)


@pytest.mark.parametrize("number", ["2363", " 2363 "])
def test_standard_verhoeff_valid_vector(number):
    # Standard Verhoeff check-digit example: 2363 is valid.
    from engine.validators import verhoeff_check

    assert verhoeff_check(number.strip()) is True


@pytest.mark.parametrize("number", ["12345", "2364", "2363x"])
def test_standard_verhoeff_invalid_vectors(number):
    from engine.validators import verhoeff_check

    assert verhoeff_check(number) is False


@pytest.mark.parametrize("number", ["234567890124", "2345 6789 0124", "2345-6789-0124"])
def test_valid_aadhaar_formats(number):
    assert is_valid_aadhaar(number)


def test_aadhaar_normalizes_grouped_input():
    assert normalize_aadhaar("2345-6789-0124") == "234567890124"


@pytest.mark.parametrize("number", [
    "034567890123",  # Aadhaar cannot start with 0.
    "134567890123",  # Aadhaar cannot start with 1.
    "234567890123",  # Checksum changed.
    "2345 678 90123",  # Invalid grouping.
    "2345678901244",
    "123456789012",  # A random 12-digit sequence is not enough.
])
def test_invalid_aadhaar(number):
    assert not is_valid_aadhaar(number)


@pytest.mark.parametrize("pan", ["ABCDE1234F", "abcde1234f"])
def test_pan_valid(pan):
    assert is_valid_pan(pan)


@pytest.mark.parametrize("pan", ["ABCD1234F", "ABCDE12345", "ABCDE1234", "ABCDE-1234-F"])
def test_pan_invalid(pan):
    assert not is_valid_pan(pan)


@pytest.mark.parametrize("phone", [
    "9845012345", "+91 98450 12345", "91-98450-12345", "09845012345", "98450-12345"
])
def test_phone_valid(phone):
    assert is_valid_phone(phone)


def test_phone_normalizes_valid_phone():
    assert normalize_phone("+91 98450-12345") == "9845012345"


@pytest.mark.parametrize("phone", ["5845012345", "984501234", "+1 9845012345", "9198450123456", "1234567890"])
def test_phone_invalid(phone):
    assert not is_valid_phone(phone)


@pytest.mark.parametrize("upi", [
    "name@okhdfcbank",
    "handle@oksbi",
    "user@paytm",
    "rohan@ybl",
    "priya.nair@ibl",
    "merchant@axl",
    "ananya@upi",
    "kavya@kotak",
    "shop@fbl",
    "customer@apl",
    "pay@barodampay",
])
def test_upi_valid_known_providers(upi):
    assert is_valid_upi(upi)


@pytest.mark.parametrize("value", ["name@gmail.com", "name@unknownbank", "not-an-id", "@okhdfcbank"])
def test_upi_rejects_email_and_unknown_provider(value):
    assert not is_valid_upi(value)


@pytest.mark.parametrize("email", ["name@gmail.com", "a.b+tag@example.co.in"])
def test_email_valid(email):
    assert is_valid_email(email)


@pytest.mark.parametrize("email", ["name@", "@example.com", "name@gmail", "two words@example.com"])
def test_email_invalid(email):
    assert not is_valid_email(email)


@pytest.mark.parametrize("code", ["110001", "560001", "682001"])
def test_pincode_format_valid(code):
    assert is_valid_pincode(code)


@pytest.mark.parametrize("code", ["010001", "000000", "12345", "1234567", "12 3456", "abcdef"])
def test_pincode_format_invalid(code):
    assert not is_valid_pincode(code)


@pytest.mark.parametrize("passport", ["J8364921", "K1029384", "Z9876543"])
def test_passport_valid(passport):
    assert is_valid_passport(passport)


@pytest.mark.parametrize("passport", ["A0000000", "AB1234567", "12345678", "J123456", "J12345678"])
def test_passport_invalid(passport):
    assert not is_valid_passport(passport)


@pytest.mark.parametrize("epic", ["ABC1234567", "kar9845012", "DLQ4019283"])
def test_voter_id_valid(epic):
    assert is_valid_voter_id(epic)


@pytest.mark.parametrize("epic", ["AB1234567", "ABCD123456", "ABC0000000", "1234567890"])
def test_voter_id_invalid(epic):
    assert not is_valid_voter_id(epic)


@pytest.mark.parametrize("dl", [
    "KA0120201234567",
    "KA-01-2020-1234567",
    "MH 12 2019 0012345",
    "DL-0420180123456",
])
def test_driving_license_valid(dl):
    assert is_valid_driving_license(dl)


@pytest.mark.parametrize("dl", [
    "ZZ0120201234567",  # Invalid state code
    "KA0118991234567",  # Implausible year
    "KA0120200000000",  # All-zero serial
    "KA01202012345",    # Too short
])
def test_driving_license_invalid(dl):
    assert not is_valid_driving_license(dl)


@pytest.mark.parametrize("dob", [
    "14/08/1998",
    "05-11-2001",
    "1995-02-28",
    "29/02/2000",
    "9 Jan 1994",
    "18 August 1989",
])
def test_dob_valid(dob):
    assert is_valid_dob(dob)


@pytest.mark.parametrize("dob", [
    "31/02/1998",  # Invalid calendar date
    "29/02/1999",  # Non-leap year
    "15/13/1995",  # Invalid month
    "12/05/1850",  # Out of range year
    "not-a-date",
])
def test_dob_invalid(dob):
    assert not is_valid_dob(dob)


@pytest.mark.parametrize("acct", ["012345678901", "123456789", "1234 5678 9012 3456", "987654321012345678"])
def test_bank_account_valid(acct):
    assert is_valid_bank_account(acct)


@pytest.mark.parametrize("acct", ["12345678", "1234567890123456789", "000000000000", "ABCD12345678"])
def test_bank_account_invalid(acct):
    assert not is_valid_bank_account(acct)


@pytest.mark.parametrize("ip", ["49.37.142.88", "192.168.1.1", "2001:db8::1"])
def test_ip_address_valid(ip):
    assert is_valid_ip_address(ip)


@pytest.mark.parametrize("ip", ["999.1.2.3", "3.11.0", "192.168.1", "example.com"])
def test_ip_address_invalid(ip):
    assert not is_valid_ip_address(ip)


