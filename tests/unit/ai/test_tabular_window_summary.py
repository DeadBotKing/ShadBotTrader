"""Phase 120 — causal tabular summaries for booster branches."""

from __future__ import annotations

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.tabular_window_summary import summarise_windows


def test_last_summary_uses_only_window_end_values():
    series = [[float(i), float(i * 10), 99.0] for i in range(10)]

    summary = summarise_windows(
        series=series,
        feature_count=2,
        column_names=["a", "b", "target"],
        sample_ends=[4, 5],
        window_size=3,
        mode="last",
    )

    assert summary.feature_names == ["a__last", "b__last"]
    assert summary.values.tolist() == [[4.0, 40.0], [5.0, 50.0]]


def test_basic_summary_adds_causal_trailing_statistics():
    series = [[float(i), float(i * 2), 0.0] for i in range(1, 21)]

    summary = summarise_windows(
        series=series,
        feature_count=2,
        column_names=["a", "b", "target"],
        sample_ends=[11],
        window_size=12,
        mode="basic",
        scales=[3, 12],
    )

    assert "a__mean_12" in summary.feature_names
    assert "a__delta_12" in summary.feature_names
    mean_12 = summary.values[0, summary.feature_names.index("a__mean_12")]
    delta_12 = summary.values[0, summary.feature_names.index("a__delta_12")]
    assert mean_12 == pytest.approx(6.5)
    assert delta_12 == pytest.approx(11.0)


def test_summary_rejects_incomplete_windows():
    with pytest.raises(ValidationError):
        summarise_windows(
            series=[[1.0], [2.0], [3.0]],
            feature_count=1,
            column_names=["a"],
            sample_ends=[1],
            window_size=3,
        )
