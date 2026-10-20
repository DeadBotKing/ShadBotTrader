"""Phase173A broker-cost-aware 1H target learnability helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_broker_cost_aware_1h_target_learnability as phase173
from scripts.audit_broker_cost_aware_1h_target_family import EventOutcome, LABEL_NEGATIVE, LABEL_POSITIVE, parse_families
from scripts.audit_pivot_payoff_target_redesign import resolve_atr


def make_frame(rows: int = 180) -> pd.DataFrame:
    close = np.full(rows, 100.0)
    close[::12] = 91.0
    close[6::12] = 109.0
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=rows, freq="1h", tz="UTC"),
            "open": close,
            "high": np.full(rows, 110.0),
            "low": np.full(rows, 90.0),
            "close": close,
            "atr": np.full(rows, 10.0),
        }
    )


def test_average_precision_balanced_accuracy_and_f1():
    y = np.asarray([1, 0, 1, 0])
    scores = np.asarray([0.9, 0.1, 0.8, 0.2])
    pred = np.asarray([1, 0, 1, 0])

    assert phase173.average_precision(y, scores) == 1.0
    assert phase173.balanced_accuracy(y, pred) == 1.0
    assert phase173.f1_score(y, pred) == 1.0


def test_centroid_model_learns_simple_separation():
    x = np.asarray([[1.0, 1.0], [1.2, 1.1], [-1.0, -1.0], [-1.1, -1.2]])
    y = np.asarray([1, 1, 0, 0])

    model = phase173.CentroidBinaryModel().fit(x, y)
    pred = model.predict(x)

    assert phase173.balanced_accuracy(y, pred) >= 0.75


def test_event_feature_row_and_matrix():
    frame = make_frame(40)
    atr = resolve_atr(frame)
    family = parse_families("F:label:breakout:0:12:0.2:0.85:0.15:1:1:0:0.5:0.5:6")[0]
    event = EventOutcome("F", 12, 12, 13, 14, str(frame.at[12, "timestamp"]), "bottom", "SELL", LABEL_POSITIVE, 1.0, 1.0, "take_profit", 10.0, "fixed", 0.4, 0.5, 0.5, 6)
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    recent_high, recent_low = phase173.rolling_high_low_np(high, low, 12)
    args = phase173.parse_args(["--spread-value", "0.4"])

    row = phase173.event_feature_row(family, event, "train", 0, frame, atr, recent_high, recent_low, args)
    x, y, sides, labels = phase173.matrix_from_rows([row])

    assert row.target_positive == 1
    assert x.shape == (1, len(phase173.FEATURE_COLUMNS))
    assert y.tolist() == [1]
    assert sides == ["SELL"]
    assert labels == [LABEL_POSITIVE]


def test_static_family_learnability_runs_on_fixture():
    frame = make_frame(180)
    atr = resolve_atr(frame)
    family = parse_families("F:label:breakout:0:12:0.2:0.85:0.15:1:1:0:0.5:0.5:6")[0]
    args = phase173.parse_args(
        [
            "--families",
            "F:label:breakout:0:12:0.2:0.85:0.15:1:1:0:0.5:0.5:6",
            "--spread-value",
            "0",
            "--purge-gap",
            "0",
            "--min-train-events",
            "1",
            "--min-validation-events",
            "1",
            "--min-test-events",
            "1",
            "--min-positive-rate",
            "0",
            "--max-positive-rate",
            "1",
        ]
    )

    rows, _events = phase173.build_family_dataset(family, frame, atr, args)
    split_rows, _model = phase173.static_family_learnability(family, rows, args)

    assert rows
    assert len(split_rows) == 3
    assert {row.split for row in split_rows} == {"train", "validation", "test"}


def test_summarize_family_computes_gate():
    split_rows = [
        phase173.LearnabilitySplitRow("F", "train", 10, 5, 5, 0, 0.5, 0.5, 0.7, 0.2, 0.6, 0.5, 0.0, 5, 0.7, 5, 0.7, 0.0),
        phase173.LearnabilitySplitRow("F", "validation", 10, 5, 5, 0, 0.5, 0.5, 0.7, 0.2, 0.6, 0.5, 0.0, 5, 0.7, 5, 0.7, 0.0),
        phase173.LearnabilitySplitRow("F", "test", 10, 5, 5, 0, 0.5, 0.5, 0.7, 0.2, 0.6, 0.5, 0.0, 5, 0.7, 5, 0.7, 0.0),
    ]
    wf = [phase173.LearnabilityFoldRow("F", 1, 10, 10, 10, 0.5, 0.5, 0.5, 0.2, 0.2, 0.6, 0.6, 0.0, 0.0, 1)]
    family = parse_families("F:label:breakout:0:12:0.2:0.85:0.15:1:1:0:0.5:0.5:6")[0]
    args = phase173.parse_args(
        [
            "--min-train-events", "1",
            "--min-validation-events", "1",
            "--min-test-events", "1",
            "--min-positive-rate", "0",
            "--max-positive-rate", "1",
            "--min-ap-lift", "0.1",
            "--min-balanced-accuracy", "0.5",
            "--min-walkforward-folds", "1",
            "--min-walkforward-pass-ratio", "0.5",
        ]
    )

    summary = phase173.summarize_family(family, split_rows, wf, args)

    assert summary.target_learnability_ready_gate == 1
