# Dataset v2 notes

- Regenerated: 2026-11-22
- Reason: the v1 templates were too narrow.
- Authorization: one-time regeneration of both splits was explicitly approved. The v2 `test.jsonl` split is locked for good after this regeneration; do not modify it or tune against it.
- Contents: synthetic data only; 60 development items and 100 test items, balanced across resume, WhatsApp, invoice, and notice contexts; 10% no-PII items in each split.
- Regeneration verification: `eval/validate_dataset.py --split all` checked span bounds, exact text slices, non-overlap, item counts, template variety, and WhatsApp casing coverage. At regeneration time, no detector was run against either split.
- One-time evaluation: the frozen Phase 3 configuration was committed before the single test evaluation. No code or configuration was changed after test results were observed.
- SHA-256 (`eval/test.jsonl`): `2A60BFF3746E66AFA37947F0FFFDDC631E468E10BF13D01E47BECD0F6D417F88`

## Realistic benchmark split (`eval/realistic.jsonl`)

- Generated deterministically by `eval/generate_realistic.py` (`seed=9407`) without modifying `eval/dev.jsonl` or the locked `eval/test.jsonl`.
- Contents: 540 synthetic items (90 per domain across `email_thread`, `whatsapp_chat`, `support_ticket`, `resume_profile`, `financial_kyc`, and `institutional_notice`), 84 multi-sentence/multi-paragraph templates, 2,432 annotated spans across all 14 PII labels (`PERSON`, `LOCATION`, `PHONE`, `EMAIL`, `AADHAAR`, `PAN`, `UPI`, `PINCODE`, `DOB`, `PASSPORT`, `VOTER_ID`, `DRIVING_LICENSE`, `BANK_ACCOUNT`, `IP_ADDRESS`), 54 hard no-PII items (10%), and 383 items with inline lookalike negatives (invalid Verhoeff 12-digit references, 6-digit OTP/verification codes, 10-digit order IDs, non-DOB dates, version/commit strings, Indian company lookalikes, and quoted cultural titles).
