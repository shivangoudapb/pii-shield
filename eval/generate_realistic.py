"""Generate a 540-item realistic synthetic Indian PII benchmark (eval/realistic.jsonl).

All records are 100% synthetic (fictional pairings of Indian names, synthetic
Verhoeff-valid Aadhaar numbers, synthetic PANs/phones/UPI handles, and RFC-2606
example email domains) written in natural multi-line emails, Hinglish WhatsApp
threads, support tickets, resumes, KYC/financial documents, and notices.
"""

from __future__ import annotations

import json
import random
import string
from pathlib import Path
from typing import TypeAlias

from engine.constants import INDIAN_STATE_CODES
from engine.validators import is_valid_phone
from eval.generate_dataset import (
    COMMON_WORD_NAMES,
    FIRST_NAMES_BY_TRADITION,
    NICKNAMES,
    SURNAMES,
    SURNAMES_BY_TRADITION,
    format_aadhaar,
    make_aadhaar,
    make_invalid_aadhaar,
    make_pan,
)

ROOT = Path(__file__).resolve().parent
Part: TypeAlias = str | tuple[str, str]
REALISTIC_LABELS = {
    "PERSON",
    "LOCATION",
    "PHONE",
    "EMAIL",
    "AADHAAR",
    "PAN",
    "UPI",
    "PINCODE",
    "DOB",
    "PASSPORT",
    "VOTER_ID",
    "DRIVING_LICENSE",
    "BANK_ACCOUNT",
    "IP_ADDRESS",
}

REALISTIC_CONTEXTS = (
    "email_thread",
    "whatsapp_chat",
    "support_ticket",
    "resume_profile",
    "financial_kyc",
    "institutional_notice",
)
ITEMS_PER_CONTEXT = 90
TOTAL_REALISTIC_ITEMS = len(REALISTIC_CONTEXTS) * ITEMS_PER_CONTEXT  # 540

UPI_HANDLES = (
    "okhdfcbank",
    "oksbi",
    "okicici",
    "okaxis",
    "ybl",
    "ibl",
    "axl",
    "paytm",
    "upi",
    "kotak",
    "apl",
    "fbl",
    "sbi",
    "hdfcbank",
    "icici",
    "barodampay",
)

EMAIL_DOMAINS = (
    "example.com",
    "example.in",
    "example.org",
    "mail.example.in",
    "corp.example.com",
)

CITY_PIN_PREFIX = (
    ("Bengaluru", "560"),
    ("Mumbai", "400"),
    ("New Delhi", "110"),
    ("Hyderabad", "500"),
    ("Chennai", "600"),
    ("Pune", "411"),
    ("Kolkata", "700"),
    ("Ahmedabad", "380"),
    ("Jaipur", "302"),
    ("Lucknow", "226"),
    ("Kochi", "682"),
    ("Indore", "452"),
    ("Chandigarh", "160"),
    ("Coimbatore", "641"),
    ("Nagpur", "440"),
    ("Vadodara", "390"),
    ("Visakhapatnam", "530"),
    ("Mysuru", "570"),
    ("Noida", "201"),
    ("Gurugram", "122"),
    ("Bhubaneswar", "751"),
    ("Surat", "395"),
    ("Guwahati", "781"),
    ("Thiruvananthapuram", "695"),
)

STREET_NAMES = (
    "MG Road",
    "100 Feet Road",
    "12th Main Road",
    "Linking Road",
    "SV Road",
    "Park Street",
    "Ring Road",
    "4th Cross",
    "7th Cross",
    "Station Road",
    "Temple Street",
    "Lake View Road",
    "Residency Road",
    "Hill Road",
    "Gandhi Marg",
    "Subhash Marg",
    "2nd Main",
    "9th Avenue",
)

LOCALITY_NAMES = (
    "Indiranagar",
    "Koramangala",
    "HSR Layout",
    "Banjara Hills",
    "Jubilee Hills",
    "Kothrud",
    "Viman Nagar",
    "Andheri West",
    "Powai",
    "Salt Lake Sector 5",
    "Anna Nagar",
    "Velachery",
    "Vasant Kunj",
    "Malviya Nagar",
    "Gomti Nagar",
    "Alkapuri",
    "Edappally",
    "Aundh",
    "Jayanagar",
    "Rajajinagar",
    "Bapu Nagar",
    "Shanti Enclave",
    "Green Park",
    "ashok Vihar",
)

BUILDING_NAMES = (
    "Shanti Heights",
    "Kaveri Apartments",
    "Sunrise Towers",
    "Nilgiri Residency",
    "Palm Grove Apartment",
    "Narmada Enclave",
)

COMPANY_LOOKALIKES = (
    "Sundaram Finance",
    "Narayana Health",
    "Mahindra Logistics",
    "Bajaj Electricals",
    "Kirloskar Brothers",
    "Godrej Consumer",
    "Lakshmi Machine Works",
    "shree Cement",
    " Murugappa Group",
    "Kalyani Steels",
)

QUOTED_TITLES = (
    "Park Street",
    "Linking Road",
    "Lotus Lane",
    "Marine Drive",
    "Brigade Road",
    "Malabar Hill",
)


def _make_person(rng: random.Random, force_common: bool = False) -> dict[str, str]:
    if force_common:
        first = rng.choice(COMMON_WORD_NAMES)
        last = rng.choice(SURNAMES)
    else:
        tradition = rng.choice(tuple(FIRST_NAMES_BY_TRADITION))
        first = rng.choice(FIRST_NAMES_BY_TRADITION[tradition])
        last = rng.choice(SURNAMES_BY_TRADITION[tradition])
    middle = rng.choice(string.ascii_uppercase)
    return {
        "first": first,
        "last": last,
        "middle": middle,
        "full": f"{first} {last}",
        "initials": f"{first[0]}. {middle}. {last}",
        "initial_short": f"{first[0]} {last}",
        "surname_first": f"{last}, {first}",
        "nickname": NICKNAMES.get(first, first[: max(3, len(first) - 2)]),
    }


def _make_bad_12digit(rng: random.Random) -> str:
    while True:
        candidate = make_invalid_aadhaar(rng)
        if not is_valid_phone(candidate):
            return candidate


def _make_phone(rng: random.Random, style: int) -> str:
    digits = str(rng.choice("6789")) + "".join(str(rng.randrange(10)) for _ in range(9))
    variant = style % 6
    if variant == 0:
        return f"+91 {digits[:5]} {digits[5:]}"
    if variant == 1:
        return f"+91-{digits[:5]}-{digits[5:]}"
    if variant == 2:
        return f"0{digits}"
    if variant == 3:
        return f"{digits[:5]}-{digits[5:]}"
    if variant == 4:
        return f"{digits[:5]} {digits[5:]}"
    return digits


def _make_email(rng: random.Random, person: dict[str, str], idx: int) -> str:
    first = person["first"].lower().replace("'", "")
    last = person["last"].lower().replace("'", "")
    domain = EMAIL_DOMAINS[idx % len(EMAIL_DOMAINS)]
    sep = (".", "_", "")[idx % 3]
    num = rng.randrange(10, 99)
    return f"{first}{sep}{last}{num}@{domain}"


def _make_upi(rng: random.Random, person: dict[str, str], idx: int) -> str:
    first = person["first"].lower().replace("'", "")
    last = person["last"].lower().replace("'", "")
    provider = UPI_HANDLES[idx % len(UPI_HANDLES)]
    num = rng.randrange(11, 99)
    handle = f"{first}.{last[:4]}{num}" if idx % 2 == 0 else f"{first}{num}"
    return f"{handle}@{provider}"


_SORTED_STATE_CODES = tuple(sorted(INDIAN_STATE_CODES))
_DOB_MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _make_passport(rng: random.Random) -> str:
    letter = rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ")
    return f"{letter}{rng.randint(1, 9)}{rng.randrange(100000, 1000000):06d}"


def _make_voter_id(rng: random.Random) -> str:
    prefix = "".join(rng.choice(string.ascii_uppercase) for _ in range(3))
    return f"{prefix}{rng.randint(1, 9)}{rng.randrange(100000, 1000000):06d}"


def _make_driving_license(rng: random.Random, style: int) -> str:
    state = rng.choice(_SORTED_STATE_CODES)
    rto = f"{rng.randint(1, 45):02d}"
    year = rng.randint(2006, 2024)
    serial = f"{rng.randint(1, 9)}{rng.randrange(100000, 1000000):06d}"
    if style % 3 == 0:
        return f"{state}-{rto}-{year}-{serial}"
    if style % 3 == 1:
        return f"{state} {rto} {year} {serial}"
    return f"{state}{rto}{year}{serial}"


def _make_dob(rng: random.Random, style: int) -> str:
    year = rng.randint(1972, 2004)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    if style % 4 == 0:
        return f"{day:02d}/{month:02d}/{year}"
    if style % 4 == 1:
        return f"{day:02d}-{month:02d}-{year}"
    if style % 4 == 2:
        return f"{year}-{month:02d}-{day:02d}"
    return f"{day} {_DOB_MONTH_NAMES[month - 1]} {year}"


def _make_bank_account(rng: random.Random, style: int) -> str:
    length = (11, 12, 14, 16)[style % 4]
    return str(rng.randint(1, 9)) + "".join(str(rng.randrange(10)) for _ in range(length - 1))


def _make_ip(rng: random.Random, style: int) -> str:
    if style % 5 == 0:
        return f"2001:db8:{rng.randint(1, 255):x}::{rng.randint(1, 99):x}"
    first = rng.choice((49, 103, 106, 117, 122, 192))
    return f"{first}.{rng.randint(1, 250)}.{rng.randint(1, 250)}.{rng.randint(2, 254)}"


def _make_address_and_pin(rng: random.Random, style: int) -> tuple[str, str, str]:
    city, pin_prefix = rng.choice(CITY_PIN_PREFIX)
    pin = f"{pin_prefix}{rng.randrange(1, 99):03d}"
    if pin.endswith("000"):
        pin = f"{pin_prefix}014"
    street = rng.choice(STREET_NAMES)
    locality = rng.choice(LOCALITY_NAMES)
    # Normalise accidental leading lowercase in locality fixture
    locality = locality[0].upper() + locality[1:]
    kind = style % 4
    if kind == 0:
        flat_no = f"{rng.randint(1, 9)}{rng.randint(0, 9)}{rng.choice(('A', 'B', 'C', ''))}"
        bldg = rng.choice(BUILDING_NAMES)
        addr = f"Flat {flat_no}, {bldg}, {street}, {locality}, {city}"
    elif kind == 1:
        num = rng.randint(4, 180)
        addr = f"{num} {street}, {locality}, {city}"
    elif kind == 2:
        ord_num = rng.choice(("1st", "2nd", "3rd", "4th", "5th", "6th"))
        addr = f"{ord_num} Cross, {locality}, {city}"
    else:
        plot = rng.randint(10, 95)
        addr = f"Plot {plot}, {locality}, {city}"
    return addr, pin, city


def _assemble(
    item_id: str,
    context: str,
    template: str,
    parts: list[Part],
    tags: set[str],
) -> dict:
    fragments: list[str] = []
    spans: list[dict] = []
    cursor = 0
    common_lower = {w.casefold() for w in COMMON_WORD_NAMES}
    for part in parts:
        if isinstance(part, str):
            fragments.append(part)
            cursor += len(part)
            continue
        label, value = part
        start = cursor
        fragments.append(value)
        cursor += len(value)
        spans.append({"start": start, "end": cursor, "label": label, "text": value})

    text = "".join(fragments)
    for span in spans:
        assert span["label"] in REALISTIC_LABELS
        assert text[span["start"] : span["end"]] == span["text"]
        if span["label"] == "PERSON":
            tokens = span["text"].replace(",", " ").replace(".", " ").split()
            if any(tok.casefold() in common_lower for tok in tokens):
                tags.add("common_word_name")
            if span["text"].islower():
                tags.add("lowercase_name")
            if span["text"].isupper() and len(span["text"]) > 2:
                tags.add("all_caps_name")

    return {
        "id": item_id,
        "context": context,
        "template": template,
        "text": text,
        "spans": spans,
        "tags": sorted(tags),
    }


def _no_pii_parts(context: str, variant: int, rng: random.Random) -> tuple[list[Part], set[str]]:
    otp = f"{rng.randrange(100000, 999999)}"
    order_id = str(rng.choice("12345")) + "".join(str(rng.randrange(10)) for _ in range(9))
    bad_aadhaar = _make_bad_12digit(rng)
    company = COMPANY_LOOKALIKES[variant % len(COMPANY_LOOKALIKES)].strip()
    title = QUOTED_TITLES[variant % len(QUOTED_TITLES)]
    tags = {"no_pii", "lookalike_negative"}

    bank: dict[str, list[tuple[str, set[str]]]] = {
        "email_thread": [
            (
                f"Subject: Q3 deployment window & build verification\n\n"
                f"Team,\nBuild verification code {otp} (commit e3e39c51 on runtime v3.11.4) passed "
                f"staging checks on 24/11/2025 against service trace reference {bad_aadhaar}. "
                f"Vendor integration with {company} remains scheduled for Friday at 11:30 IST.",
                {"lookalike_six_digit_code", "lookalike_invalid_aadhaar", "lookalike_company_name"},
            ),
            (
                f"Hi everyone,\n\nPlease review the procurement comparison for {company} "
                f"under purchase order ref {order_id}. Our creative brief deck is titled "
                f"'{title}' in the shared drive.\n\nThanks,\nOperations Desk",
                {"lookalike_order_id", "lookalike_company_name", "lookalike_nonaddress_location"},
            ),
        ],
        "whatsapp_chat": [
            (
                f"[11:04] admin: guys login OTP {otp} mat share karna kisi ke saath 😅\n"
                f"[11:05] ops: order ref {order_id} dispatch ho gaya hai, listening to ‘{title}’ rn!",
                {"lookalike_six_digit_code", "lookalike_order_id", "lookalike_nonaddress_location"},
            ),
            (
                f"fwd: server maintenance tonight 11pm–1am IST. internal tracking reference "
                f"{bad_aadhaar} closed after testing with {company} sandbox.",
                {"lookalike_invalid_aadhaar", "lookalike_company_name"},
            ),
        ],
        "support_ticket": [
            (
                f"Ticket summary: Shipment under order number {order_id} and AWB tracking "
                f"reference {bad_aadhaar} is in transit. Customer entered verification code "
                f"{otp} at the kiosk.",
                {"lookalike_order_id", "lookalike_invalid_aadhaar", "lookalike_six_digit_code"},
            ),
            (
                f"Automated alert: B2B ledger sync for {company} completed with batch code "
                f"{otp}. Audio hold track set to \"{title}\".",
                {"lookalike_company_name", "lookalike_six_digit_code", "lookalike_nonaddress_location"},
            ),
        ],
        "resume_profile": [
            (
                f"EXPERIENCE HIGHLIGHTS\n"
                f"• Led ERP migration for {company} across 4 regional warehouses.\n"
                f"• Reduced latency by 38% on batch job order ref {order_id} and "
                f"published internal case study \"{title}\".",
                {"lookalike_company_name", "lookalike_order_id", "lookalike_nonaddress_location"},
            ),
            (
                f" Role requisition code {otp} — Senior Platform Engineer (Hybrid).\n"
                f"Must have 5+ years in Python, FastAPI, and distributed caching. "
                f"Internal budget reference {bad_aadhaar}.",
                {"lookalike_six_digit_code", "lookalike_invalid_aadhaar"},
            ),
        ],
        "financial_kyc": [
            (
                f"TAX INVOICE SUMMARY (B2B)\n"
                f"Supplier entity: {company}\n"
                f"Purchase order number {order_id} | NEFT batch reference {bad_aadhaar}\n"
                f"Voucher verification code {otp} — paid in full.",
                {"lookalike_company_name", "lookalike_order_id", "lookalike_invalid_aadhaar", "lookalike_six_digit_code"},
            ),
            (
                f"Reconciliation note: Ledger entry under transaction reference {bad_aadhaar} "
                f"and approval code {otp} matched {company} statement.",
                {"lookalike_invalid_aadhaar", "lookalike_six_digit_code", "lookalike_company_name"},
            ),
        ],
        "institutional_notice": [
            (
                f"DEPARTMENT CIRCULAR\n"
                f"The annual film screening of ‘{title}’ will take place in Auditorium B "
                f"at 4:00 PM. Equipment gate pass code {otp} has been issued to security.",
                {"lookalike_nonaddress_location", "lookalike_six_digit_code"},
            ),
            (
                f"Library inventory notice: Consignment order ref {order_id} from publisher "
                f"partner {company} (waybill reference {bad_aadhaar}) has arrived.",
                {"lookalike_order_id", "lookalike_company_name", "lookalike_invalid_aadhaar"},
            ),
        ],
    }
    text, extra_tags = bank[context][variant % 2]
    return [text], tags | extra_tags


def _build_domain_item(
    context: str,
    tpl_idx: int,
    rng: random.Random,
    global_idx: int,
) -> tuple[str, list[Part], set[str]]:
    e = lambda label, val: (label, val)
    p1 = _make_person(rng, force_common=(global_idx % 4 == 0))
    p2 = _make_person(rng)
    p3 = _make_person(rng)

    phone1 = _make_phone(rng, global_idx)
    phone2 = _make_phone(rng, global_idx + 3)
    email1 = _make_email(rng, p1, global_idx)
    email2 = _make_email(rng, p2, global_idx + 1)
    upi1 = _make_upi(rng, p1, global_idx)
    pan1 = make_pan(rng)
    pan2 = make_pan(rng)
    aadhaar1 = format_aadhaar(make_aadhaar(rng), global_idx)
    addr1, pin1, _ = _make_address_and_pin(rng, global_idx)
    passport1 = _make_passport(rng)
    voter1 = _make_voter_id(rng)
    dl1 = _make_driving_license(rng, global_idx)
    dob1 = _make_dob(rng, global_idx)
    acct1 = _make_bank_account(rng, global_idx)
    ip1 = _make_ip(rng, global_idx)

    otp = f"{rng.randrange(100000, 999999)}"
    order_id = str(rng.choice("12345")) + "".join(str(rng.randrange(10)) for _ in range(9))
    bad_aadhaar = _make_bad_12digit(rng)
    company = COMPANY_LOOKALIKES[global_idx % len(COMPANY_LOOKALIKES)].strip()
    quoted_title = QUOTED_TITLES[global_idx % len(QUOTED_TITLES)]
    tags: set[str] = {f"tpl_{tpl_idx + 1:02d}"}

    if context == "email_thread":
        templates: list[tuple[str, list[Part], set[str]]] = [
            (
                "email_interview_invite",
                [
                    "From: ", e("PERSON", p2["full"]), " <", e("EMAIL", email2), ">\n",
                    "To: ", e("PERSON", p1["full"]), " <", e("EMAIL", email1), ">\n",
                    "Subject: Onsite interview schedule — Backend Engineering\n\n",
                    "Dear ", e("PERSON", p1["first"]), ",\n\n",
                    "We are pleased to invite you to our office at ", e("LOCATION", addr1), " - ", e("PINCODE", pin1),
                    ". At the reception kiosk, enter visitor verification code ", otp, " and ask for Dr. ", e("PERSON", p3["full"]),
                    ". If delayed, call ", e("PHONE", phone2), ".\n\nRegards,\n", e("PERSON", p2["full"]),
                ],
                {"repeated_person", "lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "email_vendor_reimbursement",
                [
                    "Hi Finance Team,\n\nPlease process the reimbursement for ", e("PERSON", p1["full"]),
                    " against expense order ref ", order_id, " (vendor partner ", company, "). ",
                    "You can settle via UPI to ", e("UPI", upi1), " or confirm over email at ", e("EMAIL", email1),
                    ". PAN on file: ", e("PAN", pan1), ".\n\nThanks,\n", e("PERSON", p1["surname_first"]),
                ],
                {"repeated_person", "initial_or_surname_format", "lookalike_negative", "lookalike_order_id", "lookalike_company_name"},
            ),
            (
                "email_courier_dispatch",
                [
                    "Subject: Laptop dispatch (AWB tracking reference ", bad_aadhaar, ")\n\nHi IT Desk,\n",
                    "Please ship the MacBook kit to ", e("PERSON", p1["full"]), " at ",
                    e("LOCATION", addr1), ", PIN ", e("PINCODE", pin1),
                    ". The courier partner can reach ", e("PERSON", p1["first"]), " directly on ",
                    e("PHONE", phone1), ".\n\nRegards,\n", e("PERSON", p2["initials"]),
                ],
                {"repeated_person", "initial_or_surname_format", "lookalike_negative", "lookalike_invalid_aadhaar"},
            ),
            (
                "email_lease_renewal",
                [
                    "From: ", e("PERSON", p1["surname_first"]), "\n",
                    "Subject: Lease renewal — ", e("LOCATION", addr1), "\n\n",
                    "Hello Mr. ", e("PERSON", p2["full"]), ",\n",
                    "Sharing my updated KYC details for the rent agreement renewal at ", e("LOCATION", addr1),
                    ", ", e("PINCODE", pin1), ". Tenant PAN is ", e("PAN", pan1), " and Aadhaar is ", e("AADHAAR", aadhaar1),
                    ". Please send the stamped copy to ", e("EMAIL", email1), ".",
                ],
                {"initial_or_surname_format"},
            ),
            (
                "email_forwarded_escalation",
                [
                    "---------- Forwarded message ---------\n",
                    "From: ", e("PERSON", p1["full"]), " <", e("EMAIL", email1), ">\n\n",
                    "Team, please follow up with ", e("PERSON", p2["full"]), " (", e("PHONE", phone2), ") ",
                    "regarding service ticket code ", otp, " (client IP ", e("IP_ADDRESS", ip1),
                    ") for client ", company, ".\n\n",
                    "Thanks,\n", e("PERSON", p1["full"]),
                ],
                {"repeated_person", "lookalike_negative", "lookalike_six_digit_code", "lookalike_company_name"},
            ),
            (
                "email_payroll_declaration",
                [
                    "Dear Payroll,\n\nMy name on the portal appears as ", e("PERSON", p1["initials"]),
                    " (surname on roster: ", e("PERSON", p1["last"]), "). Please link PAN ", e("PAN", pan1),
                    " and mobile ", e("PHONE", phone1), " to my profile before the 25th.\n\nRegards,\n",
                    e("PERSON", p1["full"]),
                ],
                {"repeated_person", "initial_or_surname_format"},
            ),
            (
                "email_event_speaker_travel",
                [
                    "Hi Travel Desk,\n\nProf. ", e("PERSON", p1["full"]), " (Passport ", e("PASSPORT", passport1),
                    ") will be speaking on our panel titled ‘",
                    quoted_title, "’. Please arrange airport cab pickup from ", e("LOCATION", addr1), ", ",
                    e("PINCODE", pin1), " and send itinerary updates to ", e("EMAIL", email1), " and ", e("PHONE", phone1), ".",
                ],
                {"lookalike_negative", "lookalike_nonaddress_location"},
            ),
            (
                "email_medical_claim_query",
                [
                    "Subject: Cashless claim query — reference ", bad_aadhaar, "\n\n",
                    "Hello Claims Team,\nSubmitting discharge documents from ", company, " for ",
                    e("PERSON", p1["full"]), " (Aadhaar ", e("AADHAAR", aadhaar1), "). ",
                    "Refund any co-pay balance to UPI ", e("UPI", upi1), " or call ", e("PHONE", phone1), ".",
                ],
                {"lookalike_negative", "lookalike_invalid_aadhaar", "lookalike_company_name"},
            ),
            (
                "email_alumni_directory",
                [
                    "Name: ", e("PERSON", p1["full"]), "\n",
                    "Email: ", e("EMAIL", email1), "\n",
                    "Phone: ", e("PHONE", phone1), "\n\n",
                    "Note: Happy to mentor final-year students (nickname ", e("PERSON", p1["nickname"]),
                    "). Currently relocating to ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
                ],
                {"repeated_person"},
            ),
            (
                "email_society_maintenance",
                [
                    "Dear Residents,\n\nQuarterly maintenance for ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    " is due by the 10th. Please pay via UPI ", e("UPI", upi1), " and drop the UTR to treasurer ",
                    "Shri ", e("PERSON", p1["full"]), " at ", e("EMAIL", email1), " (voucher code ", otp, ").",
                ],
                {"lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "email_internship_offer",
                [
                    "Hi ", e("PERSON", p1["first"]), ",\n\nCongratulations on your internship offer! ",
                    "Please courier signed forms to Ms. ", e("PERSON", p2["full"]), " at ", e("LOCATION", addr1),
                    ", ", e("PINCODE", pin1), " and share your PAN (", e("PAN", pan1), ") with ",
                    e("EMAIL", email2), ".\n\nRegards,\n", e("PERSON", p2["full"]),
                ],
                {"repeated_person"},
            ),
            (
                "email_bank_mandate_update",
                [
                    "From: ", e("PERSON", p1["full"]), "\n",
                    "Subject: NACH mandate & contact update\n\n",
                    "Please update my Bank Account No: ", e("BANK_ACCOUNT", acct1),
                    ", registered mobile ", e("PHONE", phone1), ", and email ",
                    e("EMAIL", email1), " against loan order ref ", order_id, ". My PAN is ", e("PAN", pan1),
                    ".\n\nThanks,\n", e("PERSON", p1["initials"]),
                ],
                {"repeated_person", "initial_or_surname_format", "lookalike_negative", "lookalike_order_id"},
            ),
        ]
        return templates[tpl_idx]

    if context == "whatsapp_chat":
        low_full = p1["full"].lower()
        low_first = p1["first"].lower()
        up_full = p1["full"].upper()
        templates = [
            (
                "wa_delivery_instructions",
                [
                    "[19:12] ", e("PERSON", low_full), ": bhaiya parcel gate pe security ko mat dena, seedha ",
                    e("LOCATION", addr1), " (", e("PINCODE", pin1), ") pe aana\n",
                    "[19:13] rider: ok sir doorstep OTP ", otp, " ready rakhna, issue ho toh ", e("PHONE", phone1), " pe call krunga",
                ],
                {"messy_chat", "messy_chat_casing", "lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "wa_bill_split_upi",
                [
                    "hey ", e("PERSON", low_full), " 👋 dinner split ₹840 bhej de on ", e("UPI", upi1),
                    " ya gpay number ", e("PHONE", phone1), " — bank transaction reference ", bad_aadhaar,
                    " fail dikha raha tha kal 😅",
                ],
                {"messy_chat", "messy_chat_casing", "lookalike_negative", "lookalike_invalid_aadhaar"},
            ),
            (
                "wa_referral_forward",
                [
                    "Fwd: hiring backend devs! ", e("PERSON", up_full), " pls send ur updated CV to ",
                    e("EMAIL", email1), " today — also follow up with ", e("PERSON", p2["full"]),
                    " on ", e("PHONE", phone2), " (ex-", company, ")",
                ],
                {"messy_chat", "messy_chat_casing", "lookalike_negative", "lookalike_company_name"},
            ),
            (
                "wa_hinglish_contact_share",
                [
                    "bhai ", e("PERSON", p1["initial_short"]), " ka naya number ", e("PHONE", phone1),
                    " save kr le, purana band ho gaya. email same hai: ", e("EMAIL", email1),
                ],
                {"messy_chat", "initial_or_surname_format"},
            ),
            (
                "wa_flatmate_kyc_docs",
                [
                    "[10:05] ", e("PERSON", p1["first"]), ": broker mang raha hai PAN, Aadhaar aur DL police verification ke liye\n",
                    "[10:07] ", e("PERSON", p1["full"]), ": ye le PAN ", e("PAN", pan1), ", Aadhaar ",
                    e("AADHAAR", aadhaar1), ", DL ", e("DRIVING_LICENSE", dl1),
                    ", flat address ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), " daal dena",
                ],
                {"messy_chat", "repeated_person"},
            ),
            (
                "wa_doctor_appointment",
                [
                    "pls call ", e("PHONE", phone1), " once free — patient DOB: ", e("DOB", dob1),
                    ", Dr. ", e("PERSON", p2["full"]),
                    " clinic shifted near ", e("LOCATION", addr1), ". token verification code ", otp, " dikhana padega",
                ],
                {"messy_chat", "lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "wa_group_trip_roster",
                [
                    "group update: ", e("PERSON", p1["full"]), " (nickname ", e("PERSON", p1["nickname"]),
                    ") and ", e("PERSON", p2["full"]), " booked cabs under order ref ", order_id,
                    " — playlist ‘", quoted_title, "’ ready rakho 🎶",
                ],
                {"messy_chat", "repeated_person", "lookalike_negative", "lookalike_order_id", "lookalike_nonaddress_location"},
            ),
            (
                "wa_allcaps_urgent_help",
                [
                    "[voice note transcript] ", e("PERSON", up_full), " SAID CALL ", e("PHONE", phone1),
                    " URGENTLY; send refund to ", e("UPI", upi1), " before 6pm",
                ],
                {"messy_chat", "messy_chat_casing"},
            ),
            (
                "wa_lowercase_resume_ping",
                [
                    "hii ", e("PERSON", low_full), " can u forward ", e("PERSON", low_first),
                    "'s portfolio to ", e("EMAIL", email2), "? recruiter Dr. ", e("PERSON", p2["full"]), " asked for it",
                ],
                {"messy_chat", "messy_chat_casing", "repeated_person"},
            ),
            (
                "wa_surname_roster_check",
                [
                    "From: ", e("PERSON", p1["surname_first"]), "\n",
                    "arre attendance sheet me ", e("PERSON", p1["initials"]), " likha hai (surname on roster: ",
                    e("PERSON", p1["last"]), "), mail ", e("EMAIL", email1), " pe correction bhej diya",
                ],
                {"messy_chat", "repeated_person", "initial_or_surname_format"},
            ),
            (
                "wa_courier_return_chat",
                [
                    "yaar ", e("PERSON", p1["full"]), " mera return parcel order number ", order_id,
                    " pickup krwa dena from ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    " — refund UPI ", e("UPI", upi1), " diya hai",
                ],
                {"messy_chat", "lookalike_negative", "lookalike_order_id"},
            ),
            (
                "wa_freelance_pan_share",
                [
                    "[16:40] accounts: hi ", e("PERSON", low_full), ", TDS ke liye PAN aur bank account bhejna\n",
                    "[16:42] ", e("PERSON", low_first), ": PAN ", e("PAN", pan1), ", A/c No: ",
                    e("BANK_ACCOUNT", acct1), " — ya UPI ", e("UPI", upi1),
                    " pe kr dena, thanks!",
                ],
                {"messy_chat", "messy_chat_casing", "repeated_person"},
            ),
        ]
        return templates[tpl_idx]

    if context == "support_ticket":
        templates = [
            (
                "ticket_return_pickup",
                [
                    "Ticket #SR-9941 | Order number ", order_id, "\n",
                    "Customer Name: ", e("PERSON", p1["full"]), "\n",
                    "Issue: Reverse pickup not attempted at ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    ". Reach customer on ", e("PHONE", phone1), " or refund ₹1,299 to ", e("UPI", upi1), ".",
                ],
                {"lookalike_negative", "lookalike_order_id"},
            ),
            (
                "ticket_broadband_relocation",
                [
                    "Service Request (verification code ", otp, "): Shift fiber connection for ",
                    "Mr. ", e("PERSON", p1["full"]), " to ", e("LOCATION", addr1), " - ", e("PINCODE", pin1),
                    ". Alternate contact: ", e("PHONE", phone1), " | registered email: ", e("EMAIL", email1), ".",
                ],
                {"lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "ticket_wallet_kyc_review",
                [
                    "KYC Escalation Note\nName: ", e("PERSON", p1["full"]), "\n",
                    "Submitted PAN: ", e("PAN", pan1), " | Aadhaar: ", e("AADHAAR", aadhaar1), "\n",
                    "Internal case reference ", bad_aadhaar, " — agent should follow up with ",
                    e("PERSON", p1["first"]), " at ", e("EMAIL", email1), ".",
                ],
                {"repeated_person", "lookalike_negative", "lookalike_invalid_aadhaar"},
            ),
            (
                "ticket_flight_refund",
                [
                    "Passenger ", e("PERSON", p1["initials"]), " (surname on roster: ", e("PERSON", p1["last"]),
                    ", Passport ", e("PASSPORT", passport1),
                    ") requested cancellation on booking order ref ", order_id, ". ",
                    "Send credit note to ", e("EMAIL", email1), " and SMS alert to ", e("PHONE", phone1), ".",
                ],
                {"repeated_person", "initial_or_surname_format", "lookalike_negative", "lookalike_order_id"},
            ),
            (
                "ticket_upi_dispute",
                [
                    "Dispute logged by Smt. ", e("PERSON", p1["full"]), ": debit of ₹2,500 from ", e("UPI", upi1),
                    " to merchant ", company, " failed (NPCI transaction reference ", bad_aadhaar,
                    "). Callback number: ", e("PHONE", phone1), ".",
                ],
                {"lookalike_negative", "lookalike_company_name", "lookalike_invalid_aadhaar"},
            ),
            (
                "ticket_sim_replacement",
                [
                    "Store walk-in KYC: ", e("PERSON", p1["full"]), " presented Aadhaar ", e("AADHAAR", aadhaar1),
                    " and Voter ID ", e("VOTER_ID", voter1),
                    " for SIM swap on ", e("PHONE", phone1), ". Residential address verified as ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
                ],
                set(),
            ),
            (
                "ticket_b2b_contact_change",
                [
                    "Account: ", company, " | Admin update for ", e("PERSON", p1["full"]), " — ",
                    "new billing email ", e("EMAIL", email1), " and phone ", e("PHONE", phone1),
                    " (auth code ", otp, ").",
                ],
                {"lookalike_negative", "lookalike_company_name", "lookalike_six_digit_code"},
            ),
            (
                "ticket_address_correction",
                [
                    "Ship to ", e("PERSON", p1["full"]), " at ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    " instead of the old hub. Waybill tracking reference ", bad_aadhaar,
                    " updated; notify ", e("EMAIL", email1), ".",
                ],
                {"lookalike_negative", "lookalike_invalid_aadhaar"},
            ),
            (
                "ticket_insurance_nominee",
                [
                    "Policy endorsement: Policyholder ", e("PERSON", p1["full"]), " (PAN ", e("PAN", pan1),
                    ", DOB: ", e("DOB", dob1),
                    ") added nominee Mrs. ", e("PERSON", p2["full"]), ", residing at ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
                ],
                set(),
            ),
            (
                "ticket_app_crash_report",
                [
                    "Bug report from ", e("EMAIL", email1), " (app build 2.14.8, client IP ",
                    e("IP_ADDRESS", ip1), "): checkout freezes when playing promo clip ‘",
                    quoted_title, "’ on order number ", order_id, ". Please follow up with ",
                    e("PERSON", p1["full"]), " on ", e("PHONE", phone1), ".",
                ],
                {"lookalike_negative", "lookalike_nonaddress_location", "lookalike_order_id"},
            ),
            (
                "ticket_demat_transmission",
                [
                    "From: ", e("PERSON", p1["surname_first"]), "\n",
                    "Requesting demat statement for PAN ", e("PAN", pan1), " linked to mobile ",
                    e("PHONE", phone1), ". Ticket verification code ", otp, " confirmed on call.",
                ],
                {"initial_or_surname_format", "lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "ticket_hospital_billing_help",
                [
                    "Patient coordinator Dr. ", e("PERSON", p2["full"]), " escalated billing query for ",
                    "Name: ", e("PERSON", p1["full"]), ", Phone: ", e("PHONE", phone1),
                    ", refund UPI: ", e("UPI", upi1), " at partner facility ", company, ".",
                ],
                {"lookalike_negative", "lookalike_company_name"},
            ),
        ]
        return templates[tpl_idx]

    if context == "resume_profile":
        templates = [
            (
                "cv_full_header_block",
                [
                    "Name: ", e("PERSON", p1["full"]), " | DOB: ", e("DOB", dob1), "\n",
                    "Location: ", e("LOCATION", addr1), " - ", e("PINCODE", pin1), "\n",
                    "Mobile: ", e("PHONE", phone1), " | Email: ", e("EMAIL", email1), "\n\n",
                    "Summary: Backend engineer with 4 years of experience at ", company,
                    " building high-throughput payment APIs.",
                ],
                {"lookalike_negative", "lookalike_company_name"},
            ),
            (
                "cv_recruiter_screen_note",
                [
                    "Recruiter screen — ", e("PERSON", p1["full"]), " (nickname ", e("PERSON", p1["nickname"]),
                    ")\nCurrent base: ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    "\nReachable on ", e("PHONE", phone1), " / ", e("EMAIL", email1),
                    " | requisition code ", otp, ". Follow up with ", e("PERSON", p1["first"]), " on Monday.",
                ],
                {"repeated_person", "lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "cv_cover_letter_signoff",
                [
                    "Dear Hiring Committee,\n\nI am writing to apply for the Data Analyst position ",
                    "(job order ref ", order_id, "). Over the past three years at ", company,
                    ", I automated reporting pipelines across retail ops.\n\nRegards,\n",
                    e("PERSON", p1["full"]), "\n", e("PHONE", phone1), " | ", e("EMAIL", email1),
                ],
                {"lookalike_negative", "lookalike_order_id", "lookalike_company_name"},
            ),
            (
                "cv_background_check_form",
                [
                    "BACKGROUND VERIFICATION FORM\nCandidate ", e("PERSON", p1["initials"]),
                    " (surname on roster: ", e("PERSON", p1["last"]), ")\nPermanent Address: ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), "\nPAN: ", e("PAN", pan1),
                    " | Aadhaar: ", e("AADHAAR", aadhaar1), " | Passport: ", e("PASSPORT", passport1),
                    " | DL: ", e("DRIVING_LICENSE", dl1),
                ],
                {"repeated_person", "initial_or_surname_format"},
            ),
            (
                "cv_academic_references",
                [
                    "References:\n1. Prof. ", e("PERSON", p1["full"]), ", Department of CS — ",
                    e("EMAIL", email1), ", ", e("PHONE", phone1), "\n2. Dr. ", e("PERSON", p2["full"]),
                    ", Principal Scientist — ", e("EMAIL", email2), " (co-author on monograph ‘",
                    quoted_title, "’)",
                ],
                {"lookalike_negative", "lookalike_nonaddress_location"},
            ),
            (
                "cv_freelance_consultant_bio",
                [
                    "Consultant Profile — ", e("PERSON", p1["surname_first"]), "\n",
                    "Tax PAN: ", e("PAN", pan1), " | Retainer UPI: ", e("UPI", upi1), "\n",
                    "Studio: ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    " | Portfolio ref ", bad_aadhaar,
                ],
                {"initial_or_surname_format", "lookalike_negative", "lookalike_invalid_aadhaar"},
            ),
            (
                "cv_onboarding_kyc_packet",
                [
                    "New Joiner Packet — Name: ", e("PERSON", p1["full"]),
                    ", PAN: ", e("PAN", pan1), ", Aadhaar: ", e("AADHAAR", aadhaar1),
                    ", Emergency Contact: Shri ", e("PERSON", p2["full"]), " (", e("PHONE", phone2), ").",
                ],
                set(),
            ),
            (
                "cv_relocation_summary",
                [
                    "Candidate update for ", e("PERSON", p1["full"]), " — relocating to ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), " next month. ",
                    "Primary email ", e("EMAIL", email1), " and mobile ", e("PHONE", phone1), ".",
                ],
                set(),
            ),
            (
                "cv_panel_feedback",
                [
                    "Panelist Dr. ", e("PERSON", p2["full"]), " recommends strong hire for ",
                    "Name: ", e("PERSON", p1["full"]), ". Please follow up with ",
                    e("PERSON", p1["first"]), " at ", e("EMAIL", email1), " (ATS order ref ", order_id, ").",
                ],
                {"repeated_person", "lookalike_negative", "lookalike_order_id"},
            ),
            (
                "cv_stipend_disbursal",
                [
                    "Intern Stipend Form\nName: ", e("PERSON", p1["full"]), "\n",
                    "Phone: ", e("PHONE", phone1), " | Bank Account Number: ", e("BANK_ACCOUNT", acct1),
                    " | UPI ID: ", e("UPI", upi1), "\n",
                    "College batch verification code ", otp, " verified.",
                ],
                {"lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "cv_executive_referral",
                [
                    "From: ", e("PERSON", p2["full"]), "\n",
                    "Sharing CV of Ms. ", e("PERSON", p1["full"]), " from ", company,
                    ". Reach her directly on ", e("PHONE", phone1), " or ", e("EMAIL", email1), ".",
                ],
                {"lookalike_negative", "lookalike_company_name"},
            ),
            (
                "cv_alumni_placement_row",
                [
                    "Placement record: Name: ", e("PERSON", p1["initial_short"]),
                    ", Address: ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    ", Contact: ", e("PHONE", phone1), ", Email: ", e("EMAIL", email1),
                ],
                {"initial_or_surname_format"},
            ),
        ]
        return templates[tpl_idx]

    if context == "financial_kyc":
        templates = [
            (
                "fin_freelance_invoice",
                [
                    "INVOICE #INV-2026 | Order number ", order_id, "\n",
                    "Billed by: Name: ", e("PERSON", p1["full"]), " | PAN: ", e("PAN", pan1), "\n",
                    "Address: ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), "\n",
                    "Client: ", company, "\n",
                    "Remit via UPI to ", e("UPI", upi1), " or email remittance advice to ", e("EMAIL", email1), ".",
                ],
                {"lookalike_negative", "lookalike_order_id", "lookalike_company_name"},
            ),
            (
                "fin_hra_rent_receipt",
                [
                    "RENT RECEIPT (HRA DECLARATION)\n",
                    "Received ₹28,000 from tenant Mr. ", e("PERSON", p1["full"]), " (PAN ", e("PAN", pan1),
                    ") towards monthly rent of ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".\n",
                    "Landlord: Smt. ", e("PERSON", p2["full"]), " | Landlord PAN: ", e("PAN", pan2),
                    " | Contact: ", e("PHONE", phone2),
                ],
                set(),
            ),
            (
                "fin_ckyc_verification",
                [
                    "CKYC Verification Record (batch reference ", bad_aadhaar, ")\n",
                    "Name: ", e("PERSON", p1["full"]), " | Date of Birth: ", e("DOB", dob1),
                    "\nAadhaar: ", e("AADHAAR", aadhaar1),
                    " | PAN: ", e("PAN", pan1), " | Voter ID: ", e("VOTER_ID", voter1),
                    "\nMobile: ", e("PHONE", phone1),
                    " | Email: ", e("EMAIL", email1),
                ],
                {"lookalike_negative", "lookalike_invalid_aadhaar"},
            ),
            (
                "fin_vendor_payout_voucher",
                [
                    "Payout approval (verification code ", otp, ") for consultant ",
                    "Dr. ", e("PERSON", p1["full"]), ": transfer ₹45,000 to Account No: ",
                    e("BANK_ACCOUNT", acct1), " or UPI ", e("UPI", upi1),
                    " after TDS under PAN ", e("PAN", pan1), ".",
                ],
                {"lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "fin_gst_shipping_manifest",
                [
                    "Consignee: ", company, " | Attention: ",
                    "Mr. ", e("PERSON", p1["full"]), "\nShip to ", e("PERSON", p1["full"]), " at ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), "\nDriver DL: ",
                    e("DRIVING_LICENSE", dl1), " | Driver contact: ",
                    e("PHONE", phone1), " | e-Waybill reference ", bad_aadhaar,
                ],
                {"repeated_person", "lookalike_negative", "lookalike_company_name", "lookalike_invalid_aadhaar"},
            ),
            (
                "fin_mutual_fund_fatca",
                [
                    "FATCA / KYC Update — Investor ", e("PERSON", p1["initials"]),
                    " (surname on roster: ", e("PERSON", p1["last"]), "), PAN ", e("PAN", pan1),
                    ", Aadhaar ", e("AADHAAR", aadhaar1), ", correspondence address ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
                ],
                {"repeated_person", "initial_or_surname_format"},
            ),
            (
                "fin_reimbursement_ledger",
                [
                    "Expense claim update for ", e("PERSON", p1["full"]), " — ₹3,420 approved under ",
                    "order ref ", order_id, ". Crediting ", e("UPI", upi1), "; confirmation sent to ",
                    e("EMAIL", email1), ".",
                ],
                {"lookalike_negative", "lookalike_order_id"},
            ),
            (
                "fin_loan_coapplicant_note",
                [
                    "Co-applicant screening (portal IP ", e("IP_ADDRESS", ip1), "): Sri ",
                    e("PERSON", p1["full"]), " (Phone ", e("PHONE", phone1),
                    ", PAN ", e("PAN", pan1), ") and Mrs. ", e("PERSON", p2["full"]),
                    " residing at ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
                ],
                set(),
            ),
            (
                "fin_security_deposit_refund",
                [
                    "Regards,\n", e("PERSON", p1["surname_first"]), "\n",
                    "Please refund my security deposit for ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                    " to UPI ", e("UPI", upi1), " or call ", e("PHONE", phone1), " (receipt code ", otp, ").",
                ],
                {"initial_or_surname_format", "lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "fin_royalty_statement",
                [
                    "Royalty statement for book ‘", quoted_title, "’ — Author Name: ",
                    e("PERSON", p1["full"]), ", PAN: ", e("PAN", pan1), ", payout UPI: ",
                    e("UPI", upi1), ", email: ", e("EMAIL", email1), ".",
                ],
                {"lookalike_negative", "lookalike_nonaddress_location"},
            ),
            (
                "fin_credit_card_dispatch",
                [
                    "Card dispatch alert (courier OTP ", otp, " sent to ", e("PHONE", phone1), "): ",
                    "Deliver physical card to Mr. ", e("PERSON", p1["full"]), " at ",
                    e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
                ],
                {"lookalike_negative", "lookalike_six_digit_code"},
            ),
            (
                "fin_auditor_signoff",
                [
                    "Statutory audit queries for ", company, " reviewed. Please follow up with ",
                    e("PERSON", p1["full"]), " (", e("EMAIL", email1), ", ", e("PHONE", phone1),
                    ") before filing.\n\nThanks,\n", e("PERSON", p2["full"]),
                ],
                {"lookalike_negative", "lookalike_company_name"},
            ),
        ]
        return templates[tpl_idx]

    # institutional_notice
    templates = [
        (
            "notice_faculty_circular",
            [
                "College circular — ", e("PERSON", p1["full"]), "\n",
                "Final-year project viva is scheduled on Friday. Coordinate with Dr. ",
                e("PERSON", p2["full"]), " at ", e("EMAIL", email2), " or call ",
                e("PHONE", phone1), " (circular code ", otp, ").",
            ],
            {"lookalike_negative", "lookalike_six_digit_code"},
        ),
        (
            "notice_hostel_allotment",
            [
                "Hostel update for ", e("PERSON", p1["full"]), " — room allotted near ",
                e("LOCATION", addr1), ", ", e("PINCODE", pin1), ". Mess fee UPI handle: ",
                e("UPI", upi1), " | warden phone: ", e("PHONE", phone2), ".",
            ],
            set(),
        ),
        (
            "notice_student_committee_list",
            [
                "Cultural Fest Committee (‘", quoted_title, "’):\n",
                "1. Ms. ", e("PERSON", p1["full"]), " — ", e("PHONE", phone1), "\n",
                "2. Mr. ", e("PERSON", p2["full"]), " — ", e("EMAIL", email2), "\n",
                "3. ", e("PERSON", p3["initials"]), " (surname on roster: ", e("PERSON", p3["last"]), ")",
            ],
            {"repeated_person", "initial_or_surname_format", "lookalike_negative", "lookalike_nonaddress_location"},
        ),
        (
            "notice_scholarship_kyc",
            [
                "Scholarship verification desk: Name: ", e("PERSON", p1["full"]),
                " (DOB: ", e("DOB", dob1), ") must bring original Aadhaar (", e("AADHAAR", aadhaar1),
                "), PAN (", e("PAN", pan1), "), and Bank Account No: ", e("BANK_ACCOUNT", acct1),
                " to Admin Block. Application reference ", bad_aadhaar, ".",
            ],
            {"lookalike_negative", "lookalike_invalid_aadhaar"},
        ),
        (
            "notice_society_agm",
            [
                "AGM Notice — ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), "\n",
                "All flat owners are requested to RSVP to Secretary Shri ", e("PERSON", p1["full"]),
                " at ", e("EMAIL", email1), " or ", e("PHONE", phone1), ".\n\nRegards,\n",
                e("PERSON", p1["surname_first"]),
            ],
            {"repeated_person", "initial_or_surname_format"},
        ),
        (
            "notice_clinic_camp",
            [
                "Community Health Camp in partnership with ", company, "\n",
                "Lead Physician: Dr. ", e("PERSON", p1["full"]), " (", e("PHONE", phone1), ")\n",
                "Venue: ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                " | Registration order ref ", order_id,
            ],
            {"lookalike_negative", "lookalike_company_name", "lookalike_order_id"},
        ),
        (
            "notice_bus_route_coordinator",
            [
                "Transport notice: Pickup point at ", e("LOCATION", addr1), ", ", e("PINCODE", pin1),
                " will be coordinated by Smt. ", e("PERSON", p1["full"]), " (nickname ",
                e("PERSON", p1["nickname"]), ", DL ", e("DRIVING_LICENSE", dl1),
                "). Emergency helpline: ", e("PHONE", phone1), ".",
            ],
            {"repeated_person"},
        ),
        (
            "notice_exam_hall_roster",
            [
                "From: ", e("PERSON", p2["full"]), "\n",
                "Seat discrepancy reported for ", e("PERSON", p1["initials"]),
                " (surname on roster: ", e("PERSON", p1["last"]), ", Voter ID ", e("VOTER_ID", voter1),
                ", Passport ", e("PASSPORT", passport1), "). Send hall ticket scan to ",
                e("EMAIL", email1), " quoting verification code ", otp, ".",
            ],
            {"repeated_person", "initial_or_surname_format", "lookalike_negative", "lookalike_six_digit_code"},
        ),
        (
            "notice_alumni_donation_receipt",
            [
                "Endowment Cell Receipt — Donor Name: ", e("PERSON", p1["full"]),
                ", PAN for 80G certificate: ", e("PAN", pan1), ", UPI: ", e("UPI", upi1),
                ", Address: ", e("LOCATION", addr1), ", ", e("PINCODE", pin1), ".",
            ],
            set(),
        ),
        (
            "notice_lab_equipment_delivery",
            [
                "Lab purchase order number ", order_id, " from ", company, ": ",
                "Ship to ", e("PERSON", p1["full"]), " at ", e("LOCATION", addr1), ", ",
                e("PINCODE", pin1), ". Lab phone: ", e("PHONE", phone1), ".",
            ],
            {"lookalike_negative", "lookalike_order_id", "lookalike_company_name"},
        ),
        (
            "notice_workshop_certificates",
            [
                "Participants of the AI Workshop should follow up with ", e("PERSON", p1["full"]),
                " at ", e("EMAIL", email1), " if certificates are missing.\n\nThanks,\n",
                e("PERSON", p2["full"]),
            ],
            set(),
        ),
        (
            "notice_library_clearance",
            [
                "No-dues clearance (kiosk IP ", e("IP_ADDRESS", ip1), ") for Name: ", e("PERSON", p1["full"]),
                " | Mobile: ", e("PHONE", phone1), " | Email: ", e("EMAIL", email1),
                " | Ledger reference ", bad_aadhaar, " cleared.",
            ],
            {"lookalike_negative", "lookalike_invalid_aadhaar"},
        ),
    ]
    return templates[tpl_idx]


def make_realistic_records(seed: int = 9407) -> list[dict]:
    records: list[dict] = []
    # Exactly 9 no-PII items per 90-item context => 54 / 540 (10.0%)
    no_pii_slots = {9, 19, 29, 39, 49, 59, 69, 79, 89}
    global_idx = 0

    for ctx_idx, context in enumerate(REALISTIC_CONTEXTS):
        for local_idx in range(ITEMS_PER_CONTEXT):
            rng = random.Random(seed + ctx_idx * 4099 + local_idx * 131)
            item_id = f"r{global_idx + 1:03d}"

            if local_idx in no_pii_slots:
                parts, tags = _no_pii_parts(context, local_idx // 10, rng)
                records.append(_assemble(item_id, context, f"{context}_no_pii_{(local_idx // 10) % 2 + 1}", parts, tags))
                global_idx += 1
                continue

            tpl_idx = local_idx % 12
            tpl_name, parts, tags = _build_domain_item(context, tpl_idx, rng, global_idx)
            records.append(_assemble(item_id, context, tpl_name, parts, tags))
            global_idx += 1

    assert len(records) == TOTAL_REALISTIC_ITEMS
    assert sum(not r["spans"] for r in records) == TOTAL_REALISTIC_ITEMS // 10
    return records


def main() -> None:
    records = make_realistic_records()
    out_path = ROOT / "realistic.jsonl"
    content = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {len(records)} realistic synthetic items to {out_path.name}.")


if __name__ == "__main__":
    main()
