# PII Shield: Reversible Privacy Layer for AI Chats (India-aware)

## Problem
People paste real personal data into AI chatbots every day: resumes with phone numbers, customer WhatsApp chats, student lists, invoices with PAN or Aadhaar numbers. That data lands on third-party servers. In India, the DPDP Act makes organisations responsible for personal data, yet telling people to "just don't paste it" fails because they still need the AI's help.

Existing redaction tools are mostly built for Western data formats (SSN, US phone numbers) and usually just black text out. That makes the AI's answer less useful, because the answer can't be mapped back to the real person.

## Solution
**PII Shield** sits between the user and any AI chatbot.

1. The user pastes raw text. PII Shield replaces personal data with consistent placeholders, e.g. `[PERSON_1]`, `[PHONE_1]`.
2. The user sends the redacted text to any LLM.
3. The user pastes the AI's reply back. PII Shield restores the real values.

The AI never sees the personal data, and the user still gets a finished, usable answer.

## What makes it different
- **India-specific detection:** Aadhaar (validated with the Verhoeff checksum, so random 12-digit numbers are not flagged), PAN, UPI IDs, Indian phone formats, 6-digit pincodes.
- **Hybrid detection:** regex and validators for structured data, rules for common patterns, and a pretrained NER model for names and places.
- **Reversible:** consistent placeholders and a restore step, not one-way masking.
- **Measured, not claimed:** evaluated on a labelled Indian test set with precision/recall/F1 per entity type, comparing regex-only, NER-only and hybrid, plus an honest error analysis.

## Users
Students, freelancers, small businesses and support teams who use AI tools with real customer or personal data.

## Deliverables
- Deployed web app (two-box UI: redact and restore)
- GitHub repository with code, labelled dataset, tests and evaluation
- 2-minute demo recording

## Honest limitations
- NER will miss some names, especially ones that are also common words (e.g. Kiran, Sagar, Jyoti) and noisy chat text. Results are reported openly.
- The deployed version processes text on a server in memory and does not log or store it. A fully in-browser version (nothing leaves the device) is a stretch goal, not a claim.
- Reduces exposure risk; does not guarantee privacy or legal compliance.
- Scope: English and Roman-script Hinglish text. No native-script text, images or PDFs.
