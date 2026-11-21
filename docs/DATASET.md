# Dataset Guide

## Goal
~150-200 short, realistic, **fully synthetic** texts with labelled PII spans, so we can measure the detector honestly.

## Split
- `eval/dev.jsonl`: ~60 items. Use freely for development and tuning.
- `eval/test.jsonl`: ~100 items. **Locked.** Only run at the end of each evaluation round; do not tune against it.

## Format (JSONL, one object per line)
```json
{"id": "t012", "context": "whatsapp", "text": "Hi, this is Ananya Rao. Call me on 98450 12345", "spans": [{"start": 15, "end": 25, "label": "PERSON"}, {"start": 38, "end": 49, "label": "PHONE"}]}
```
Offsets are character offsets, end exclusive. Verify them with a script that checks `text[start:end]` looks right.

## Entity labels
| Label | Include | Exclude |
|---|---|---|
| PERSON | full or partial personal names ("Ananya Rao", "Rahul") | companies, product names, job titles |
| LOCATION | street/area/city/state parts of an address ("2nd Cross, HSR Layout, Bengaluru") | generic words like "home", "office" |
| PHONE | Indian mobile numbers in any common format | order IDs, OTPs |
| EMAIL | email addresses | |
| AADHAAR | 12-digit valid Aadhaar-format numbers | any 12-digit number that fails the checksum |
| PAN | PAN-format IDs | |
| UPI | UPI IDs | normal email addresses |
| PINCODE | 6-digit pincodes in address context | order numbers, OTPs |

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
