"""Create deterministic, fully synthetic PII Shield evaluation data.

Run with --split dev while tuning. Generate --split test once, at lock time;
the script refuses to overwrite an existing locked test file.
"""

import argparse
import json
import random
import string
from pathlib import Path
from typing import TypeAlias

from engine.validators import is_valid_aadhaar, verhoeff_check

ROOT = Path(__file__).resolve().parent
FIRST_NAMES = (
    "Aarohi", "Kiran", "Sagar", "Jyoti", "Gopal", "Mukta", "Ganga", "Nila",
    "Ishaan", "Devika", "Rohan", "Meera", "Tara", "Kabir", "Anaya", "Rehan",
)
LAST_NAMES = (
    "Rao", "Menon", "Iyer", "Reddy", "Shetty", "Dutta", "Patil", "Nair",
    "Sen", "Kulkarni", "Bose", "Das", "Joshi", "Pillai", "Khan", "Naidu",
)
STREETS = ("Cedar Cross", "Maple Road", "Lotus Lane", "River View Road", "Amber Cross")
LOCALITIES = ("Sample Nagar", "Demo Layout", "Fictional Sector 4", "Practice Colony")
CITIES = ("Bengaluru", "Mysuru", "Pune", "Kochi", "Jaipur", "Indore")
Part: TypeAlias = str | tuple[str, str]


def make_aadhaar(rng: random.Random) -> str:
    """Build a checksum-valid synthetic 12-digit number."""
    body = str(rng.randint(2, 9)) + "".join(str(rng.randrange(10)) for _ in range(10))
    for check_digit in "0123456789":
        candidate = body + check_digit
        if verhoeff_check(candidate):
            return candidate
    raise AssertionError("A Verhoeff check digit must exist")


def format_aadhaar(number: str, style: int) -> str:
    if style % 3 == 1:
        return f"{number[:4]} {number[4:8]} {number[8:]}"
    if style % 3 == 2:
        return f"{number[:4]}-{number[4:8]}-{number[8:]}"
    return number


def make_phone(rng: random.Random, style: int) -> str:
    number = str(rng.choice("6789")) + "".join(str(rng.randrange(10)) for _ in range(9))
    if style % 4 == 0:
        return f"+91 {number[:5]} {number[5:]}"
    if style % 4 == 1:
        return f"0{number}"
    if style % 4 == 2:
        return f"{number[:5]}-{number[5:]}"
    return number


def make_pan(rng: random.Random) -> str:
    letters = "".join(rng.choice(string.ascii_uppercase) for _ in range(5))
    return f"{letters}{rng.randrange(10000):04d}{rng.choice(string.ascii_uppercase)}"


def make_person(rng: random.Random, style: int) -> str:
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    if style % 4 == 1:
        return f"{first.lower()} {last.lower()}"
    if style % 4 == 2:
        return f"{first.upper()} {last.upper()}"
    if style % 4 == 3:
        return f"{first[0]}. {last}"
    return f"{first} {last}"


def make_location(rng: random.Random) -> str:
    number = rng.randrange(1, 100)
    return f"{number}, {rng.choice(STREETS)}, {rng.choice(LOCALITIES)}, {rng.choice(CITIES)}"


def make_item(item_id: str, context: str, parts: list[Part]) -> dict:
    fragments: list[str] = []
    spans: list[dict] = []
    text_length = 0
    for part in parts:
        if isinstance(part, str):
            fragments.append(part)
            text_length += len(part)
            continue
        label, value = part
        start = text_length
        fragments.append(value)
        text_length += len(value)
        # Validate the offsets before the record is written to JSONL.
        assert "".join(fragments)[start:text_length] == value
        spans.append({"start": start, "end": text_length, "label": label})
    return {"id": item_id, "context": context, "text": "".join(fragments), "spans": spans}


def make_negative(rng: random.Random) -> list[Part]:
    valid = make_aadhaar(rng)
    bad_check = str((int(valid[-1]) + 1) % 10)
    invalid_aadhaar = valid[:-1] + bad_check
    assert not is_valid_aadhaar(invalid_aadhaar)
    otp = rng.randrange(100000, 1000000)
    order_id = str(rng.choice("12345")) + "".join(str(rng.randrange(10)) for _ in range(9))
    return [
        "Synthetic QA note: invalid Aadhaar-like value ", invalid_aadhaar,
        "; OTP ", str(otp), "; order number ", order_id, ".",
    ]


def make_records(split: str, count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    records = []
    split_prefix = "d" if split == "dev" else "t"
    for index in range(count):
        style = index + seed
        person = make_person(rng, style)
        phone = make_phone(rng, style)
        pan = make_pan(rng)
        aadhaar = format_aadhaar(make_aadhaar(rng), style)
        email = f"sample{seed % 1000}{index:03d}@example.com"
        upi = f"payee{seed % 1000}{index:03d}@okhdfcbank"
        pincode = f"{rng.randrange(1, 10)}{rng.randrange(10000, 100000):05d}"
        location = make_location(rng)
        item_id = f"{split_prefix}{index + 1:03d}"
        case = index % 10

        if case == 0:
            context = "resume"
            title = "Dr. " if style % 6 == 0 else ""
            parts = ["Resume contact: ", title, ("PERSON", person), "; phone ", ("PHONE", phone),
                     "; email ", ("EMAIL", email), "."]
        elif case == 1:
            context = "invoice"
            parts = ["Name: ", ("PERSON", person), "; Aadhaar: ", ("AADHAAR", aadhaar),
                     "; PAN: ", ("PAN", pan), "."]
        elif case == 2:
            context = "whatsapp"
            parts = ["Please send payment to ", ("UPI", upi), " and call ", ("PHONE", phone), "."]
        elif case == 3:
            context = "address"
            parts = ["Deliver to ", ("LOCATION", location), ", ", ("PINCODE", pincode), "."]
        elif case == 4:
            context = "negative"
            parts = ["Synthetic QA note for ", ("PERSON", person), ": "] + make_negative(rng)
        elif case == 5:
            context = "notice"
            parts = ["College notice: contact ", ("PERSON", person), " at ", ("EMAIL", email),
                     "; reminder for ", ("PERSON", person.split()[0]), "."]
        elif case == 6:
            context = "address"
            parts = ["Courier for ", ("PERSON", person), " at ", ("LOCATION", location),
                     ", ", ("PINCODE", pincode), "; PAN ", ("PAN", pan), "."]
        elif case == 7:
            context = "invoice"
            parts = ["Customer ", ("PERSON", person), " Aadhaar ", ("AADHAAR", aadhaar),
                     " UPI ", ("UPI", upi), "."]
        elif case == 8:
            context = "no-pii"
            parts = ["The library will open at nine, and the meeting is moved to Friday."]
        else:
            context = "whatsapp"
            parts = ["Support follow-up: call ", ("PHONE", phone), ", email ", ("EMAIL", email),
                     ", UPI ", ("UPI", upi), ", PAN ", ("PAN", pan), "."]

        records.append(make_item(item_id, context, parts))
    return records


def validate_records(records: list[dict], expected_count: int) -> None:
    assert len(records) == expected_count
    assert len({record["id"] for record in records}) == expected_count
    allowed = {"PERSON", "LOCATION", "PHONE", "EMAIL", "AADHAAR", "PAN", "UPI", "PINCODE"}
    for record in records:
        text = record["text"]
        for span in record["spans"]:
            assert span["label"] in allowed
            assert 0 <= span["start"] < span["end"] <= len(text)
    assert sum(not record["spans"] for record in records) == expected_count // 10


def write_jsonl(path: Path, records: list[dict], *, refuse_existing: bool) -> None:
    if refuse_existing and path.exists():
        raise FileExistsError(f"Refusing to overwrite locked dataset: {path.name}")
    contents = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    path.write_text(contents, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    args = parser.parse_args()

    if args.split in {"test", "all"} and (ROOT / "test.jsonl").exists():
        raise SystemExit("eval/test.jsonl already exists and is locked; refusing to overwrite it")
    if args.split in {"dev", "all"}:
        dev = make_records("dev", 60, 731)
        validate_records(dev, 60)
        write_jsonl(ROOT / "dev.jsonl", dev, refuse_existing=False)
        print("Wrote 60 synthetic development items.")
    if args.split in {"test", "all"}:
        test = make_records("test", 100, 1907)
        validate_records(test, 100)
        write_jsonl(ROOT / "test.jsonl", test, refuse_existing=True)
        print("Wrote 100 synthetic locked test items. Do not inspect or tune against this split.")


if __name__ == "__main__":
    main()
