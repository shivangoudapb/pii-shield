"""Hand-built checks for the evaluation metric functions."""

from eval.run_eval import score_spans


def test_exact_and_relaxed_scores_for_perfect_match():
    gold = [(0, 5, "PERSON"), (10, 20, "PHONE")]
    predicted = [(0, 5, "PERSON"), (10, 20, "PHONE")]

    result = score_spans(gold, predicted)

    assert result["exact"]["micro"] == {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    assert result["relaxed"]["micro"] == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_partial_overlap_counts_only_for_relaxed_same_label_match():
    gold = [(0, 10, "PERSON")]
    predicted = [(5, 15, "PERSON")]

    result = score_spans(gold, predicted)

    assert result["exact"]["micro"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    assert result["relaxed"]["micro"] == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_relaxed_match_requires_half_overlap_and_same_label():
    result = score_spans(
        [(0, 10, "PERSON")],
        [(6, 12, "PERSON"), (0, 10, "LOCATION")],
    )

    assert result["relaxed"]["micro"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0}


def test_duplicate_predictions_do_not_double_count_a_gold_span():
    result = score_spans(
        [(0, 10, "PERSON")],
        [(0, 10, "PERSON"), (0, 10, "PERSON")],
    )

    assert result["exact"]["PERSON"] == {"precision": 0.5, "recall": 1.0, "f1": 2 / 3}
    assert result["relaxed"]["PERSON"] == {"precision": 0.5, "recall": 1.0, "f1": 2 / 3}


def test_metric_labels_include_misses_and_false_alarms():
    result = score_spans([(1, 3, "PHONE")], [(1, 3, "EMAIL")])

    assert result["exact"]["PHONE"]["recall"] == 0.0
    assert result["exact"]["EMAIL"]["precision"] == 0.0

