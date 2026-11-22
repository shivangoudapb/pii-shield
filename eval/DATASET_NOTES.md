# Dataset v2 notes

- Regenerated: 2026-11-22
- Reason: the v1 templates were too narrow.
- Authorization: one-time regeneration of both splits was explicitly approved. The v2 `test.jsonl` split is locked for good after this regeneration; do not modify it or tune against it.
- Contents: synthetic data only; 60 development items and 100 test items, balanced across resume, WhatsApp, invoice, and notice contexts; 10% no-PII items in each split.
- Verification: `eval/validate_dataset.py --split all` checked span bounds, exact text slices, non-overlap, item counts, template variety, and WhatsApp casing coverage. No detector was run against either regenerated split.
- SHA-256 (`eval/test.jsonl`): `2A60BFF3746E66AFA37947F0FFFDDC631E468E10BF13D01E47BECD0F6D417F88`
