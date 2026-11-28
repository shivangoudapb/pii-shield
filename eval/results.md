# Evaluation results: dev (current engine)

All data is synthetic. Relaxed matching requires overlap / max(span lengths) ≥ 50% with the same label. Labels with zero gold and zero predicted spans in the 8-label `dev` split report `1.000` by convention.

## Exact-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 1.000 | 0.286 | 0.444 | 0.963 | 0.743 | 0.839 | 1.000 | 0.871 | 0.931 |
| LOCATION | 1.000 | 1.000 | 1.000 | 0.211 | 0.444 | 0.286 | 0.750 | 1.000 | 0.857 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 1.000 | 0.662 | 0.797 | 0.767 | 0.378 | 0.507 | 0.979 | 0.939 | 0.959 |

## Relaxed-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 1.000 | 0.286 | 0.444 | 0.981 | 0.757 | 0.855 | 1.000 | 0.871 | 0.931 |
| LOCATION | 1.000 | 1.000 | 1.000 | 0.421 | 0.889 | 0.571 | 0.750 | 1.000 | 0.857 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 1.000 | 0.662 | 0.797 | 0.836 | 0.412 | 0.552 | 0.979 | 0.939 | 0.959 |

## Split checks

- Items: 60
- Gold spans per label: `{"AADHAAR": 4, "EMAIL": 21, "LOCATION": 9, "PAN": 10, "PERSON": 70, "PHONE": 18, "PINCODE": 7, "UPI": 9}`
- No-PII false-alarm rate (C): 0.000
- Full-pipeline round-trip rate (C): 1.000

## Initial Phase 3 dev tuning sweep

| Threshold | Label set | PERSON precision | PERSON recall | PERSON F1 | Hybrid micro F1 |
|---:|---|---:|---:|---:|---:|
| 0.2 | base | 0.887 | 0.671 | 0.764 | 0.845 |
| 0.3 | base | 0.885 | 0.657 | 0.754 | 0.841 |
| 0.4 | base | 0.885 | 0.657 | 0.754 | 0.847 |
| 0.5 | base | 0.885 | 0.657 | 0.754 | 0.847 |
| 0.2 | expanded | 0.855 | 0.671 | 0.752 | 0.825 |
| 0.3 | expanded | 0.865 | 0.643 | 0.738 | 0.828 |
| 0.4 | expanded | 0.865 | 0.643 | 0.738 | 0.837 |
| 0.5 | expanded | 0.865 | 0.643 | 0.738 | 0.837 |

## Latency and memory

- Hybrid latency after warm-up: median 311.98 ms/item; p95 405.39 ms/item.
- Peak process RAM with model loaded: 2725.7 MiB.

---

# Evaluation results: realistic (540-item 14-label benchmark)

All data is synthetic (`eval/realistic.jsonl`, generated deterministically with `seed=9407` across 6 domains and 84 multi-sentence/multi-paragraph templates).

## Exact-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 0.997 | 0.693 | 0.818 | 0.885 | 0.786 | 0.832 | 0.948 | 0.914 | 0.931 |
| LOCATION | 1.000 | 1.000 | 1.000 | 0.070 | 0.086 | 0.077 | 0.976 | 1.000 | 0.988 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| DOB | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PASSPORT | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| VOTER_ID | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| DRIVING_LICENSE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| BANK_ACCOUNT | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| IP_ADDRESS | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 0.999 | 0.894 | 0.943 | 0.653 | 0.281 | 0.393 | 0.980 | 0.970 | 0.975 |

## Relaxed-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 1.000 | 0.695 | 0.820 | 0.900 | 0.799 | 0.846 | 0.961 | 0.925 | 0.943 |
| LOCATION | 1.000 | 1.000 | 1.000 | 0.674 | 0.820 | 0.740 | 0.976 | 1.000 | 0.988 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| DOB | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PASSPORT | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| VOTER_ID | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| DRIVING_LICENSE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| BANK_ACCOUNT | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| IP_ADDRESS | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 1.000 | 0.894 | 0.944 | 0.836 | 0.360 | 0.503 | 0.984 | 0.974 | 0.979 |

## Split checks

- Items: 540
- Gold spans per label: `{"AADHAAR": 69, "BANK_ACCOUNT": 31, "DOB": 36, "DRIVING_LICENSE": 30, "EMAIL": 276, "IP_ADDRESS": 24, "LOCATION": 245, "PAN": 156, "PASSPORT": 26, "PERSON": 844, "PHONE": 321, "PINCODE": 232, "UPI": 123, "VOTER_ID": 19}`
- No-PII false-alarm rate (C): 0.222 (12/54 adversarial lookalike-heavy paragraphs had a GLiNER false alarm; structured regex/validator false-alarm rate was 0.000)
- Full-pipeline round-trip rate (C): 1.000

## Latency and memory

- Hybrid latency after warm-up: median 361.52 ms/item; p95 528.11 ms/item.
- Peak process RAM with model loaded: 2725.7 MiB.

---

# Evaluation results: test (locked Phase 3 one-time baseline)

Preserved verbatim from the single locked test-split evaluation prior to post-Phase-3 rule and label expansions (`eval/test.jsonl` was not re-opened or modified).

## Exact-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 0.750 | 0.078 | 0.141 | 0.860 | 0.741 | 0.796 | 0.860 | 0.741 | 0.796 |
| LOCATION | 0.000 | 0.000 | 0.000 | 0.258 | 0.444 | 0.327 | 0.400 | 0.444 | 0.421 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 0.977 | 0.500 | 0.661 | 0.718 | 0.376 | 0.493 | 0.890 | 0.840 | 0.864 |

## Relaxed-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 0.750 | 0.078 | 0.141 | 0.930 | 0.802 | 0.861 | 0.930 | 0.802 | 0.861 |
| LOCATION | 0.000 | 0.000 | 0.000 | 0.484 | 0.833 | 0.612 | 0.550 | 0.611 | 0.579 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 0.977 | 0.500 | 0.661 | 0.824 | 0.432 | 0.567 | 0.932 | 0.880 | 0.905 |

## Split checks

- Items: 100
- Gold spans per label: `{"AADHAAR": 9, "EMAIL": 34, "LOCATION": 18, "PAN": 17, "PERSON": 116, "PHONE": 29, "PINCODE": 12, "UPI": 15}`
- No-PII false-alarm rate (C): 0.000
- Full-pipeline round-trip rate (C): 1.000

## Latency and memory

- Hybrid latency after warm-up: median 212.45 ms/item; p95 253.86 ms/item.
- Peak process RAM with model loaded: 2729.2 MiB.

Scores are indicative only: all datasets are synthetic.
