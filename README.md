# PII Shield

PII Shield detects India-specific structured identifiers and is being built as a reversible privacy layer for AI chats. The current repository contains the structured validators, regex detector, shared span schema, and synthetic development and locked test datasets. The later rules, NER, merge, redaction, API, UI, evaluation, and deployment phases are not implemented yet.

## Dataset notes

All examples are generated from templates and synthetic values. Emails use the reserved `example.com` domain. Phone, PAN, Aadhaar, UPI, and pincode-like values are generated; names and fictional address combinations come from small hand-written lists. No real customer data is used. Generated identifiers could coincidentally match values assigned outside this project, so the dataset is not evidence about any real person.

The deterministic generator covers resume snippets, WhatsApp-style messages, forms, address text, and a college notice. It includes grouped and ungrouped Aadhaar, several phone formats, synthetic emails and known-provider UPI IDs, PAN, pincodes, invalid Aadhaar-like numbers, OTP/order-number negatives, common-word names, initials, repeated names, and no-PII examples. The development split has 60 examples; the locked test split has 100. The small templates and name/place lists create limited linguistic and regional variety, so results from these data will be indicative rather than representative.

Use `python -m eval.generate_dataset --split dev` to regenerate the development split. The one-time `--split test` command creates the locked test split and refuses to overwrite it. Do not use that split for development or tuning.
