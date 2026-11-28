# Dataset Guide

## Goal
~150-200 short, realistic, **fully synthetic** texts with labelled PII spans, so we can measure the detector honestly.

## Split
- `eval/dev.jsonl`: 60 items (original 8 labels). Use freely for development and tuning.
- `eval/test.jsonl`: 100 items (original 8 labels). **Locked.** Do not modify or tune against it.
- `eval/realistic.jsonl`: 540 multi-sentence / multi-paragraph synthetic items across 6 domains covering all **14 PII labels** (`eval/generate_realistic.py`, `seed=9407`).

## Format (JSONL, one object per line)
```json
{"id": "t012", "context": "whatsapp", "text": "Hi, this is Ananya Rao. Call me on 98450 12345", "spans": [{"start": 12, "end": 22, "label": "PERSON", "text": "Ananya Rao"}, {"start": 35, "end": 46, "label": "PHONE", "text": "98450 12345"}]}
```
Offsets are character offsets, end exclusive. Verify them with `python -m eval.validate_dataset --split all`.

## Entity labels (14)
| Label | Include | Exclude |
|---|---|---|
| PERSON | full or partial personal names ("Ananya Rao", "Rahul") | companies, product names, job titles |
| LOCATION | street/area/city/state parts of an address ("2nd Cross, HSR Layout, Bengaluru") | generic words like "home", "office", quoted song/film titles |
| PHONE | Indian mobile numbers in any common format | order IDs, OTPs |
| EMAIL | email addresses | UPI handles |
| AADHAAR | 12-digit valid Verhoeff Aadhaar numbers | any 12-digit number that fails the Verhoeff checksum |
| PAN | PAN-format IDs (`[A-Z]{5}[0-9]{4}[A-Z]`) | Voter IDs |
| UPI | UPI IDs across 80+ NPCI bank handles | normal email addresses |
| PINCODE | 6-digit pincodes in address context | order numbers, OTPs |
| DOB | birth dates in explicit DOB context (`DOB:`, `Born on`) | invoice dates, meeting dates, deadlines |
| PASSPORT | Indian passport numbers (`[A-Z][1-9][0-9]{6}`) in passport context | generic alphanumeric codes |
| VOTER_ID | Indian EPIC Voter IDs (`[A-Z]{3}[0-9]{7}`) | serial codes with trailing letters |
| DRIVING_LICENSE | Indian DL numbers with valid state/UT RTO prefix + year + 7-digit serial | invalid state prefixes |
| BANK_ACCOUNT | 9–18 digit numbers in explicit banking context (`A/c No`, `IFSC`) | bare order/tracking numbers |
| IP_ADDRESS | valid IPv4 (`0–255` octets) and IPv6 addresses | software version numbers (`v1.2.3.4`) |

Decision to make early: keep PERSON and LOCATION as separate labels, and treat full street addresses as LOCATION (no separate ADDRESS label). Keep it simple.

## Contexts (spread items across these)
1. **Resume/CV snippets**
2. **WhatsApp/customer-support chats** (informal, Hinglish, typos)
3. **Invoices/forms** ("Name:", "PAN:", tables flattened to text)
4. **College/institution notices and student lists**

## Make it hard on purpose
Include these so results aren't inflated:
- Names that are also common words: Kiran, Sagar, Jyoti, Gopal, Mukta, Ganga
- Names from diverse regions (Kannada, Tamil, Telugu, Hindi, Bengali, Punjabi, Marathi, Malayalam), with initials ("K. S. Rao") and honorifics
- Lowercase or ALL-CAPS names in chats
- **Negatives:** 12-digit numbers that fail the Aadhaar checksum, 10-digit order IDs, OTPs, 6-digit codes that aren't pincodes, company names that look like people, emails vs UPI IDs
- Same person mentioned twice, with full name then first name only
- Phone formats: `+91 98450 12345`, `09845012345`, `98450-12345`, `9845012345`
- Aadhaar formats: `2345 6789 0123`, `2345-6789-0123`, `234567890123`
- Roughly 10-15% of items with **no PII at all** (to measure false alarms)

## Generation approach
1. Write a generator script using lists of Indian first/last names, areas, cities, UPI handles, and template sentences per context. Generate structured values programmatically (valid Verhoeff Aadhaar numbers, valid PAN patterns, phone numbers).
2. Use an LLM to produce natural-sounding variations and messy chat text from your templates, with the spans re-located by script afterwards.
3. **Manually review at least 30% of items**, especially all hard cases, and fix label mistakes. A wrong label makes the metrics meaningless.
4. Add a `DATASET_NOTES.md` section in the README: how data was made, that it is synthetic, known biases.

## Safety
All data must be synthetic. Generated Aadhaar/PAN/phone values are random and may coincidentally match real ones. Never use real people's data.
