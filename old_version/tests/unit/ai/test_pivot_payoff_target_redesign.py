"""Phase154A pivot payoff target redesign helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_pivot_payoff_target_redesign as phase154
from scripts.train_pivot_pattern_recognition import ACTION_BUY, ACTION_HOLD, ACTION_SELL


def test_parse_phase154_default_candidates():
    candidates = phase154.parse_candidates(phase154.DEFAULT_CANDIDATES)

    assert [candidate.candidate_id for candidate in candidates[:3]] == ["B1", "B2", "B3"]
    assert candidates[0].lookahead_bars == 24
    assert candidates[0].pivot_zone_atr == 0.35
    assert candidates[0].tp_atr == 0.75
    assert candidates[0].sl_atr == 0.75
    assert candidates[1].min_score_edge == 0.1


def test_first_hit_score_respects_stop_first_same_bar_policy():
    high = np.asarray([101.0], dtype=float)
    low = np.asarray([99.0], dtype=float)
    close = np.asarray([100.0], dtype=float)

    score, target_hit, stop_hit, ambiguous = phase154.first_hit_score(
        high,
        low,
        close,
        entry=100.0,
        atr_value=1.0,
        tp_atr=1.0,
        sl_atr=1.0,
        side="BUY",
        same_bar_policy="stop_first",
        timeout_score_mode="zero",
    )

    assert score == -1.0
    assert target_hit == 0
    assert stop_hit == 1
    assert ambiguous == 1


def test_first_hit_score_respects_target_first_same_bar_policy():
    score, target_hit, stop_hit, ambiguous = phase154.first_hit_score(
        np.asarray([101.0], dtype=float),
        np.asarray([99.0], dtype=float),
        np.asarray([100.0], dtype=float),
        entry=100.0,
        atr_value=1.0,
        tp_atr=1.0,
        sl_atr=1.0,
        side="BUY",
        same_bar_policy="target_first",
        timeout_score_mode="zero",
    )

    assert score == 1.0
    assert target_hit == 1
    assert stop_hit == 0
    assert ambiguous == 1


def test_apply_payoff_candidate_labels_bottom_buy_and_top_sell():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=8, freq="5min", tz="UTC"),
            "open": [100, 100, 100, 100, 100, 100, 100, 100],
            "high": [100, 100, 100, 102, 102, 102, 102, 102],
            "low": [100, 100, 100, 100, 100, 100, 98, 98],
            "close": [100, 100, 100, 100, 102, 102, 102, 102],
            "h4_atr_for_risk": [1.0] * 8,
        }
    )
    candidate = phase154.PayoffCandidate(
        candidate_id="B",
        label="unit",
        lookahead_bars=3,
        pivot_zone_atr=0.25,
        tp_atr=1.0,
        sl_atr=1.0,
        min_score_edge=0.0,
    )

    relabeled = phase154.apply_payoff_candidate(
        frame,
        candidate,
        recent_window_bars=3,
        same_bar_policy="stop_first",
        timeout_score_mode="zero",
    )

    assert int(relabeled.loc[2, "target_action"]) == ACTION_BUY
    assert int(relabeled.loc[5, "target_action"]) == ACTION_SELL
    assert int(relabeled.loc[7, "target_action"]) == ACTION_HOLD


def test_sign_flip_detects_payoff_regime_change():
    assert phase154.sign_flip(-0.1, -0.2, 0.05) == 1
    assert phase154.sign_flip(0.1, 0.2, -0.05) == 1
    assert phase154.sign_flip(0.1, 0.2, 0.05) == 0
