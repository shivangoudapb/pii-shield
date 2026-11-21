# Evaluation Plan

## Metric
Entity-level, exact-match on (start, end, label). Report **precision, recall, F1** per label and overall (micro). Optionally also report a relaxed match (overlap ≥ 50%) for PERSON and LOCATION, since boundary errors on names are common.

- Precision = correct detections / all detections (false alarms hurt this)
- Recall = correct detections / all true PII spans (**misses hurt this. For a privacy tool, recall matters most.**)

## Systems compared
| System | Description |
|---|---|
| A. Regex-only | structured layer + rules, no ML |
| B. NER-only | pretrained NER model alone |
| C. Hybrid | regex + rules + NER with merge (the real tool) |
| D. (optional) Hybrid + fine-tuned NER | only if time allows |

## Results table (fill in)
| Label | A P | A R | A F1 | B P | B R | B F1 | C P | C R | C F1 |
|---|---|---|---|---|---|---|---|---|---|
| PERSON | | | | | | | | | |
| LOCATION | | | | | | | | | |
| PHONE | | | | | | | | | |
| EMAIL | | | | | | | | | |
| AADHAAR | | | | | | | | | |
| PAN | | | | | | | | | |
| UPI | | | | | | | | | |
| PINCODE | | | | | | | | | |
| **Overall** | | | | | | | | | |

Also report: number of test items, number of spans per label, and the false-alarm rate on the no-PII items.

## Round-trip check
`restore(redact(x)) == x` pass rate on the full dataset (should be 100%).

## Error analysis (this is the valuable part)
For the hybrid system, list real failures and group them:
- **Missed names:** which kinds? (common-word names, initials, lowercase, regional names)
- **False alarms:** what got flagged wrongly? (company names, places mistaken for people)
- **Boundary errors:** partial name captured
- **Structured misses:** any phone/Aadhaar/PAN formats not handled
- For each group: 2-3 concrete examples, a guess at why, and what would fix it

## Latency and size (for the README)
- Median time per request on the deployed instance
- Model size and RAM use

## Honest reporting rules
- Report numbers from the locked test set only.
- State clearly that the data is synthetic and small, so numbers are indicative, not a guarantee.
- Include the weak spots. A clear failure analysis is worth more than a perfect-looking score.
