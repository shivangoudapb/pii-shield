# Evaluation results: dev

All data is synthetic. Relaxed matching requires overlap / max(span lengths) ≥ 50% with the same label.

## Exact-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 1.000 | 0.057 | 0.108 | 0.870 | 0.671 | 0.758 | 0.887 | 0.671 | 0.764 |
| LOCATION | 0.000 | 0.000 | 0.000 | 0.190 | 0.444 | 0.267 | 0.286 | 0.444 | 0.348 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 1.000 | 0.493 | 0.661 | 0.680 | 0.345 | 0.457 | 0.882 | 0.811 | 0.845 |

## Relaxed-match metrics

| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PERSON | 1.000 | 0.057 | 0.108 | 0.944 | 0.729 | 0.823 | 0.962 | 0.729 | 0.829 |
| LOCATION | 0.000 | 0.000 | 0.000 | 0.381 | 0.889 | 0.533 | 0.357 | 0.556 | 0.435 |
| PHONE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AADHAAR | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PAN | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| UPI | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| PINCODE | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| **Overall** | 1.000 | 0.493 | 0.661 | 0.787 | 0.399 | 0.529 | 0.919 | 0.845 | 0.880 |

## Split checks

- Items: 60
- Gold spans per label: `{"AADHAAR": 4, "EMAIL": 21, "LOCATION": 9, "PAN": 10, "PERSON": 70, "PHONE": 18, "PINCODE": 7, "UPI": 9}`
- No-PII false-alarm rate (C): 0.000
- Full-pipeline round-trip rate (C): 1.000

## Dev tuning sweep

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

- Hybrid latency after warm-up: median 195.72 ms/item; p95 243.88 ms/item.
- Peak process RAM with model loaded: 2728.2 MiB.

Scores are indicative only: the dataset is small and synthetic.
