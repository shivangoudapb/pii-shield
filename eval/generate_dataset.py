"""Create deterministic synthetic PII Shield datasets.

Use --split dev during development. The generator refuses to overwrite an
existing eval/test.jsonl file; the one-time v2 regeneration is performed under
the user's explicit authorization, then the test split stays locked.
"""

import argparse
import json
import random
import string
from pathlib import Path
from typing import TypeAlias

from engine.validators import is_valid_aadhaar, verhoeff_check

ROOT = Path(__file__).resolve().parent
Part: TypeAlias = str | tuple[str, str]
CONTEXTS = ("resume", "whatsapp", "invoice", "notice")
LABELS = {"PERSON", "LOCATION", "PHONE", "EMAIL", "AADHAAR", "PAN", "UPI", "PINCODE"}

# Synthetic first-name pools grouped by naming tradition for broad coverage.
FIRST_NAMES_BY_TRADITION = {
    "Kannada": ("Akshara", "Aishwarya", "Aniruddha", "Basavaraj", "Bhuvan", "Chaitra", "Chetan", "Deepa", "Diganth", "Ganesh", "Harsha", "Kavya", "Madhuri", "Nikhil", "Rakshit", "Shreya", "Tejas", "Vinay"),
    "Tamil": ("Abirami", "Anbu", "Arjun", "Bhavani", "Dhanush", "Gautham", "Harini", "Iniya", "Karthik", "Keerthi", "Nandini", "Priya", "Senthil", "Thamizh", "Vasanth", "Yazhini"),
    "Telugu": ("Aadhya", "Ananya", "Bhavana", "Charan", "Chiranjeevi", "Harika", "Keerthana", "Mahesh", "Nikhita", "Pavan", "Sravya", "Sushma", "Teja", "Uday", "Varun", "Yamini"),
    "Malayalam": ("Anjali", "Aparna", "Aswathy", "Devika", "Gokul", "Indu", "Jishnu", "Kalyani", "Nila", "Parvathy", "Ranjith", "Sandeep", "Sreeja", "Unni", "Vineeth", "Zoya"),
    "Hindi": ("Aarav", "Aditi", "Akash", "Diya", "Ishaan", "Jaya", "Karan", "Meera", "Naman", "Pooja", "Rakesh", "Riya", "Sunny", "Tara", "Vikas", "Yash"),
    "Marathi": ("Amol", "Chinmay", "Gauri", "Isha", "Manasi", "Mayur", "Neel", "Omkar", "Pranav", "Rutuja", "Sai", "Shubham", "Sneha", "Vaishnavi", "Vedant", "Vinit"),
    "Bengali": ("Abhik", "Anindita", "Arindam", "Debashish", "Indrani", "Koushik", "Madhurima", "Mainak", "Moumita", "Niladri", "Ritwik", "Sagnik", "Sahana", "Suman", "Tanushree", "Ujjwal"),
    "Punjabi": ("Aman", "Amandeep", "Amrit", "Guneet", "Gurleen", "Harpreet", "Jasmeet", "Kiran", "Mandeep", "Navdeep", "Prabhjot", "Rajinder", "Simran", "Sukhman", "Tejinder", "Veer"),
    "Gujarati": ("Bhargav", "Dhara", "Hiral", "Jignesh", "Krupa", "Maulik", "Niyati", "Parth", "Pinal", "Rachna", "Rohan", "Sagar", "Urvashi", "Vaibhav", "Vraj", "Yashvi"),
    "Muslim": ("Aamir", "Ayesha", "Farhan", "Hina", "Imran", "Iqra", "Mariam", "Mohammed", "Noor", "Rehan", "Saira", "Sana", "Sameer", "Yasmin", "Zain", "Zara"),
    "Christian": ("Alisha", "Anthony", "Ashwin", "Benedict", "Clara", "Daniel", "Esther", "Fiona", "Joel", "Maria", "Mathew", "Nathan", "Noel", "Ruth", "Sharon", "Teresa"),
}

SURNAMES_BY_TRADITION = {
    "Kannada": ("Rao", "Shetty", "Gowda", "Hegde", "Bhat", "Murthy", "Acharya", "Nayak", "Urs", "Kamath"),
    "Tamil": ("Iyer", "Iyengar", "Pillai", "Gounder", "Chettiar", "Subramanian", "Nadar", "Venkataraman", "Rajendran", "Shanmugam"),
    "Telugu": ("Reddy", "Naidu", "Chowdary", "Varma", "Kandukuri", "Alluri", "Gollapudi", "Yarlagadda", "Daggubati", "Konidela"),
    "Malayalam": ("Nair", "Menon", "Kurup", "Panicker", "Warrier", "Nambiar", "Kuriakose", "Varghese", "Pisharody", "Pillai"),
    "Hindi": ("Sharma", "Verma", "Gupta", "Tiwari", "Mishra", "Singh", "Sinha", "Saxena", "Chaturvedi", "Awasthi"),
    "Marathi": ("Deshmukh", "Kulkarni", "Patil", "Joshi", "Bhosale", "Chavan", "Jadhav", "Gokhale", "Pawar", "Deshpande"),
    "Bengali": ("Banerjee", "Mukherjee", "Chatterjee", "Dutta", "Bose", "Ghosh", "Das", "Sen", "Roy", "Mitra"),
    "Punjabi": ("Sandhu", "Gill", "Kaur", "Brar", "Dhillon", "Sidhu", "Grewal", "Bedi", "Chahal", "Saini"),
    "Gujarati": ("Patel", "Shah", "Mehta", "Desai", "Trivedi", "Bhatt", "Parikh", "Amin", "Thakkar", "Modi"),
    "Muslim": ("Khan", "Shaikh", "Ansari", "Qureshi", "Siddiqui", "Hussain", "Mirza", "Farooqi", "Memon", "Pathan"),
    "Christian": ("D'Souza", "Fernandes", "D'Costa", "Rodrigues", "Thomas", "Jacob", "Varghese", "Kurian", "Pereira", "Lobo"),
}

COMMON_WORD_NAMES = (
    "Kiran", "Sagar", "Jyoti", "Gopal", "Mukta", "Ganga", "Sunny", "Pooja", "Ocean", "Cherry",
    "Chandra", "Shanti", "Anand", "Aruna", "Bala", "Deepa", "Geeta", "Indra", "Kamal", "Kanti",
    "Leela", "Manju", "Maya", "Meera", "Neel", "Pinky", "Preeti", "Raja", "Rani", "Ravi", "Sarita",
    "Lucky", "Faith", "Hope", "Veena",
)
NICKNAMES = {
    "Ananya": "Anu", "Aarav": "Avi", "Kavya": "Kavi", "Venkatesh": "Venky", "Suresh": "Suri",
    "Priya": "Pree", "Mohammed": "Mo", "Lakshmi": "Laks", "Rohan": "Ro", "Sagar": "Sags",
    "Kiran": "Kiru", "Meera": "Mimi", "Ayesha": "Ash", "Harini": "Hari", "Gauri": "Gau",
}
STREETS = ("Cedar Cross", "Maple Road", "Lotus Lane", "River View Road", "Amber Cross", "Pine Street", "Coral Road", "Mango Cross")
LOCALITIES = ("Sample Nagar", "Demo Layout", "Fictional Sector 4", "Practice Colony", "Paper Mill Road", "Cedar Enclave", "Model Extension", "Test Garden")
CITIES = ("Bengaluru", "Mysuru", "Pune", "Kochi", "Jaipur", "Indore", "Chennai", "Hyderabad", "Kolkata", "Surat")
NON_ADDRESS_WORDS = ("Lotus Lane", "Cedar Cross", "Sample Nagar", "Maple Road", "River View")
COMPANY_LOOKALIKES = ("Ravi Kumar & Sons", "Lakshmi Textiles", "Meera Trading House", "Arjun Foods")
NEGATIVE_KINDS = (
    "invalid_aadhaar", "six_digit_code", "order_id", "company_name", "email_like_upi", "location_word"
)

TEMPLATE_NAMES = {
    "resume": ("contact_header", "career_summary", "pan_profile", "address_card", "education_row", "reference_request", "identity_line", "relocation_note"),
    "whatsapp": ("casual_request", "forwarded_message", "hinglish_chat", "line_break_chat", "emoji_message", "voice_note", "typo_reply", "group_chat"),
    "invoice": ("customer_header", "flat_table", "shipment_block", "payment_footer", "kyc_fields", "purchase_note", "remittance_line", "billing_narrative"),
    "notice": ("student_list", "circular", "campus_address", "signoff", "event_registration", "hostel_update", "field_trip", "class_roster"),
}


def _unique_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys(name for pool in FIRST_NAMES_BY_TRADITION.values() for name in pool))


def _unique_surnames() -> tuple[str, ...]:
    return tuple(dict.fromkeys(name for pool in SURNAMES_BY_TRADITION.values() for name in pool))


FIRST_NAMES = _unique_names()
SURNAMES = _unique_surnames()
assert len(set(FIRST_NAMES) | set(COMMON_WORD_NAMES)) >= 150
assert len(SURNAMES) >= 80
assert len(set(COMMON_WORD_NAMES)) >= 25


def make_aadhaar(rng: random.Random) -> str:
    body = str(rng.randint(2, 9)) + "".join(str(rng.randrange(10)) for _ in range(10))
    for check_digit in "0123456789":
        candidate = body + check_digit
        if verhoeff_check(candidate):
            return candidate
    raise AssertionError("A Verhoeff check digit must exist")


def make_invalid_aadhaar(rng: random.Random) -> str:
    valid = make_aadhaar(rng)
    for check_digit in "0123456789":
        candidate = valid[:-1] + check_digit
        if candidate != valid and not is_valid_aadhaar(candidate):
            return candidate
    raise AssertionError("A nearby invalid Verhoeff value must exist")


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


def make_person_data(rng: random.Random, force_common: bool = False) -> dict[str, str]:
    if force_common:
        first = rng.choice(COMMON_WORD_NAMES)
        last = rng.choice(SURNAMES)
        tradition = "Common-word synthetic"
    else:
        tradition = rng.choice(tuple(FIRST_NAMES_BY_TRADITION))
        first = rng.choice(FIRST_NAMES_BY_TRADITION[tradition])
        last = rng.choice(SURNAMES_BY_TRADITION[tradition])
    return {
        "first": first,
        "last": last,
        "middle": rng.choice(string.ascii_uppercase),
        "full": f"{first} {last}",
        "nickname": NICKNAMES.get(first, first[: max(2, len(first) - 2)] + "y"),
        "tradition": tradition,
    }


def name_parts(person: dict[str, str], form: str = "full", casing: str = "title") -> list[Part]:
    first, last = person["first"], person["last"]
    if form == "first":
        value = first
        prefix = ""
    elif form == "initials":
        value = f"{first[0]}. {person['middle']}. {last}"
        prefix = ""
    elif form == "initial_no_dot":
        value = f"{first[0]} {last}"
        prefix = ""
    elif form == "surname_first":
        value = f"{last}, {first}"
        prefix = ""
    elif form == "honorific_first":
        value = first
        prefix = "Dr. "
    else:
        value = f"{first} {last}"
        prefix = ""
    if casing == "lower":
        value = value.lower()
    elif casing == "upper":
        value = value.upper()
    return ([prefix] if prefix else []) + [("PERSON", value)]


def make_location(rng: random.Random) -> str:
    return f"{rng.randrange(1, 100)} {rng.choice(STREETS)}, {rng.choice(LOCALITIES)}, {rng.choice(CITIES)}"


def make_item(item_id: str, context: str, template: str, parts: list[Part], tags: set[str]) -> dict:
    fragments: list[str] = []
    spans: list[dict] = []
    cursor = 0
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
        assert text[span["start"]:span["end"]] == span["text"]
        if span["label"] == "PERSON":
            name = span["text"]
            if any(token.casefold() in {word.casefold() for word in COMMON_WORD_NAMES} for token in name.replace(",", " ").split()):
                tags.add("common_word_name")
            if name.islower():
                tags.add("lowercase_name")
            if name.isupper():
                tags.add("all_caps_name")
    return {
        "id": item_id,
        "context": context,
        "template": template,
        "text": text,
        "spans": spans,
        "tags": sorted(tags),
    }


def no_pii_text(context: str, index: int) -> str:
    variants = {
        "resume": (
            "Portfolio review moved to Thursday; please upload the revised draft before noon.",
            "The workshop agenda now includes a short session on interview preparation.",
        ),
        "whatsapp": (
            "fwd: team sync shifted to 4pm today 👍 pls check the shared notes",
            "hii all, meeting moved to friday 😅 will send the agenda soon",
        ),
        "invoice": (
            "Line item: paper clips x 4; subtotal pending internal review.",
            "Payment terms are unchanged; attach the purchase order after approval.",
        ),
        "notice": (
            "Campus notice: library hours stay unchanged this week.",
            "The field trip briefing has moved to the second lecture hall.",
        ),
    }
    return variants[context][index % 2]


def build_template(context: str, template_id: int, fields: dict, person_bits: list[Part]) -> list[Part]:
    e = lambda label, value: (label, value)
    full = person_bits
    person = fields["person"]
    phone, email, upi = fields["phone"], fields["email"], fields["upi"]
    pan, aadhaar = fields["pan"], fields["aadhaar"]
    location, pin = fields["location"], fields["pincode"]
    if context == "resume":
        templates = [
            ["Resume contact • ", *full, " | mobile ", e("PHONE", phone), " | mail ", e("EMAIL", email)],
            ["Career summary: ", *full, " is open to a new role; reach them at ", e("EMAIL", email)],
            ["Candidate ", *full, " / PAN ", e("PAN", pan), " / phone ", e("PHONE", phone)],
            ["Address card for ", *full, ": ", e("LOCATION", location), ", ", e("PINCODE", pin)],
            ["Education row — ", *full, "; call ", e("PHONE", phone), " after 6pm"],
            ["References requested by ", *full, "; payment handle ", e("UPI", upi)],
            ["Photo ID entry: ", *full, " | Aadhaar ", e("AADHAAR", aadhaar)],
            ["Quick CV ", *full, " • relocate near ", e("LOCATION", location), " • ", e("EMAIL", email)],
        ]
    elif context == "whatsapp":
        second = name_parts(fields["second_person"], "full", fields["case_style"])
        templates = [
            ["hey ", *full, " can u share ur resume? call ", e("PHONE", phone)],
            ["Fwd: role opening — ", *full, " pls reply to ", e("EMAIL", email), " before 5"],
            ["bhai ", *full, " ka contact ", e("PHONE", phone), " hai, send msg when free"],
            ["From: ", *full, "\nneed the form today\nmail ", e("EMAIL", email)],
            ["hii ", *full, " 😅 pls send UPI ", e("UPI", upi), " when u can"],
            ["[voice note] ", *full, " said call after class: ", e("PHONE", phone)],
            ["pls call ", e("PHONE", phone), " — ", *full, " needs the file asappp"],
            ["group: ", *full, " and ", *second, " are sharing PAN ", e("PAN", pan), " here"],
        ]
    elif context == "invoice":
        templates = [
            ["Invoice to ", *full, "; PAN ", e("PAN", pan), "; email ", e("EMAIL", email)],
            ["Customer | ", *full, " | Phone | ", e("PHONE", phone), " | Total | 2400"],
            ["Ship to ", *full, " at ", e("LOCATION", location), ", ", e("PINCODE", pin)],
            ["Payment footer: UPI ", e("UPI", upi), " / contact ", e("EMAIL", email)],
            ["KYC row for ", *full, " Aadhaar ", e("AADHAAR", aadhaar), " PAN ", e("PAN", pan)],
            ["Purchase note — ", *full, " ordered supplies; call ", e("PHONE", phone)],
            ["Remit to ", e("UPI", upi), "; billing contact ", *full, " at ", e("EMAIL", email)],
            ["Billed party: ", *full, "\nDelivery: ", e("LOCATION", location), ", ", e("PINCODE", pin), "\nPAN ", e("PAN", pan)],
        ]
    else:  # notice
        second = name_parts(fields["second_person"], "initials", "title")
        third = name_parts(fields["third_person"], "full", "title")
        templates = [
            ["Student list: ", *full, ", ", *second, ", ", *third],
            ["College circular — ", *full, "; contact ", e("PHONE", phone), " for details"],
            ["Campus map desk for ", *full, ": ", e("LOCATION", location), ", PIN ", e("PINCODE", pin)],
            ["Regards,\n", *full, "\nOffice contact ", e("EMAIL", email)],
            ["Event registration: ", *full, " / ", e("EMAIL", email), " / PAN ", e("PAN", pan)],
            ["Hostel update for ", *full, " — UPI ", e("UPI", upi), " for meal plan"],
            ["Field trip form: ", *full, " pickup at ", e("LOCATION", location), "; call ", e("PHONE", phone)],
            ["Class roster note — ", *full, "\nAadhaar ", e("AADHAAR", aadhaar), "\nmail ", e("EMAIL", email)],
        ]
    return templates[template_id]


def repeated_parts(person: dict[str, str], style: int) -> tuple[list[Part], list[Part], str]:
    if style == 0:  # full name, then first name
        return name_parts(person, "full"), [" — follow up with ", ("PERSON", person["first"])], "full_then_first"
    if style == 1:  # first name, then full name
        return name_parts(person, "first"), ["; full record: ", ("PERSON", person["full"])], "first_then_full"
    if style == 2:  # initials, then surname
        initial = f"{person['first'][0]}. {person['middle']}. {person['last']}"
        return [("PERSON", initial)], [" (surname on roster: ", ("PERSON", person["last"]), ")"], "initials_then_surname"
    alias = person["nickname"]
    return name_parts(person, "full"), [" (nickname ", ("PERSON", alias), ")"], "nickname_style"


def negative_extra(kind: str, rng: random.Random, index: int) -> tuple[list[Part], str]:
    if kind == "invalid_aadhaar":
        return [" | non-Aadhaar 12-digit ref ", make_invalid_aadhaar(rng)], "lookalike_invalid_aadhaar"
    if kind == "six_digit_code":
        return [" | locker reference ", f"{rng.randrange(100000, 1000000)}"], "lookalike_six_digit_code"
    if kind == "order_id":
        order = str(rng.choice("12345")) + "".join(str(rng.randrange(10)) for _ in range(9))
        return [" | order ref ", order], "lookalike_order_id"
    if kind == "company_name":
        company = COMPANY_LOOKALIKES[index % len(COMPANY_LOOKALIKES)]
        return [" | vendor company ", company], "lookalike_company_name"
    if kind == "email_like_upi":
        address = f"sales{index:03d}@okhdfcbank.com"
        return [" | email ", ("EMAIL", address)], "lookalike_email_upi"
    word = NON_ADDRESS_WORDS[index % len(NON_ADDRESS_WORDS)]
    return [" | playlist title: ‘", word, "’ (not an address)"], "lookalike_nonaddress_location"


def no_pii_positions(split: str, context_index: int) -> set[int]:
    if split == "dev":
        distributions = ({8, 14}, {8, 14}, {14}, {14})
    else:
        distributions = ({8, 16, 24}, {8, 16, 24}, {16, 24}, {16, 24})
    return set(distributions[context_index])


def make_records(split: str, count: int, seed: int) -> list[dict]:
    if split not in {"dev", "test"} or count % len(CONTEXTS):
        raise ValueError("split must be dev/test and count must divide evenly across contexts")
    per_context = count // len(CONTEXTS)
    if (split, count) not in {("dev", 60), ("test", 100)}:
        raise ValueError("supported dataset sizes are 60 dev items and 100 test items")

    records: list[dict] = []
    global_index = 0
    for context_index, context in enumerate(CONTEXTS):
        for local_index in range(per_context):
            rng = random.Random(seed + context_index * 1009 + local_index * 37)
            item_id = f"{'d' if split == 'dev' else 't'}{global_index + 1:03d}"
            template_id = local_index % 8
            template_name = f"{context}_{TEMPLATE_NAMES[context][template_id]}"
            tags: set[str] = {f"template_{template_id + 1:02d}"}

            if local_index in no_pii_positions(split, context_index):
                tags.add("no_pii")
                records.append(make_item(item_id, context, template_name, [no_pii_text(context, local_index)], tags))
                global_index += 1
                continue

            force_common = (global_index % 3 == 0)
            person = make_person_data(rng, force_common=force_common)
            case_style = "title"
            if context == "whatsapp" and local_index % 4 == 0:
                case_style = "lower"
            elif context == "whatsapp" and local_index % 4 == 1:
                case_style = "upper"
            fields = {
                "person": person,
                "second_person": make_person_data(rng),
                "third_person": make_person_data(rng),
                "case_style": case_style,
                "phone": make_phone(rng, global_index),
                "email": f"sample{seed % 1000}{global_index:03d}@example.com",
                "upi": f"payee{seed % 1000}{global_index:03d}@okhdfcbank",
                "pan": make_pan(rng),
                "aadhaar": format_aadhaar(make_aadhaar(rng), global_index),
                "location": make_location(rng),
                "pincode": f"{rng.randrange(1, 10)}{rng.randrange(10000, 100000):05d}",
            }

            repeat = global_index % 4 == 0
            if repeat:
                person_bits, repeated, repeat_tag = repeated_parts(person, global_index // 4 % 4)
                tags.add("repeated_person")
                tags.add(f"repeat_{repeat_tag}")
            else:
                name_form = ("full", "initials", "initial_no_dot", "surname_first", "full", "first", "honorific_first", "full")[template_id]
                person_bits = name_parts(person, name_form, case_style)
                repeated = []

            # Keep casing hard cases visible even when the item also exercises
            # repeated-person formatting (which otherwise defaults to title case).
            if context == "whatsapp" and case_style in {"lower", "upper"}:
                def apply_case(parts: list[Part]) -> list[Part]:
                    return [
                        (label, value.lower() if case_style == "lower" else value.upper())
                        if isinstance(part, tuple) and part[0] == "PERSON"
                        else part
                        for part in parts
                        for label, value in ([part] if isinstance(part, tuple) else [("", "")])
                    ]
                person_bits = apply_case(person_bits)
                repeated = apply_case(repeated)

            parts = build_template(context, template_id, fields, person_bits)
            if repeat:
                parts.extend(repeated)
            if context == "whatsapp" and case_style in {"lower", "upper"}:
                tags.add("messy_chat_casing")
            if context == "whatsapp" and template_id in {1, 2, 3, 4, 5, 6, 7}:
                tags.add("messy_chat")
            if template_id in {1, 3, 6}:
                tags.add("initial_or_surname_format")

            if global_index % 3 == 0:
                negative_kind = NEGATIVE_KINDS[(global_index // 3) % len(NEGATIVE_KINDS)]
                extra_parts, negative_tag = negative_extra(negative_kind, rng, global_index)
                parts.extend(extra_parts)
                tags.update({"lookalike_negative", negative_tag})

            records.append(make_item(item_id, context, template_name, parts, tags))
            global_index += 1

    validate_records(records, count, split)
    return records


def validate_records(records: list[dict], expected_count: int, split: str) -> None:
    assert len(records) == expected_count
    assert len({record["id"] for record in records}) == expected_count
    assert sum(not record["spans"] for record in records) == expected_count // 10
    for context in CONTEXTS:
        examples = [record for record in records if record["context"] == context]
        assert len({record["template"] for record in examples}) >= 8
        casing_cases = sum(
            "messy_chat_casing" in record["tags"] for record in examples
        )
        if context == "whatsapp":
            assert casing_cases * 4 >= len(examples), "At least 25% of WhatsApp items need lower/ALL-CAPS names"

    for record in records:
        text = record["text"]
        ordered = sorted(record["spans"], key=lambda span: (span["start"], span["end"]))
        previous_end = -1
        for span in ordered:
            assert span["label"] in LABELS
            assert 0 <= span["start"] < span["end"] <= len(text)
            assert text[span["start"]:span["end"]] == span["text"]
            assert span["start"] >= previous_end, f"Overlapping annotations in item {record['id']}"
            previous_end = span["end"]


def write_jsonl(path: Path, records: list[dict]) -> None:
    if path.name == "test.jsonl" and path.exists():
        raise FileExistsError("eval/test.jsonl is locked; refusing to overwrite it")
    content = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    args = parser.parse_args()

    if args.split in {"test", "all"} and (ROOT / "test.jsonl").exists():
        raise SystemExit("eval/test.jsonl already exists and is locked; refusing to overwrite it")
    if args.split in {"dev", "all"}:
        dev = make_records("dev", 60, 2801)
        write_jsonl(ROOT / "dev.jsonl", dev)
        print("Wrote 60 synthetic development items.")
    if args.split in {"test", "all"}:
        test = make_records("test", 100, 4603)
        write_jsonl(ROOT / "test.jsonl", test)
        print("Wrote 100 synthetic locked test items. Do not inspect or tune against this split.")


if __name__ == "__main__":
    main()
