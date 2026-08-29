"""فاز ۷۹ — WindowGenerator با برچسب seq2seq (مسیر streamed مدل رنج).

ریشه: مدل رنج seq2seq با دیتای بزرگ (1H: 4.3GB > آستانهٔ 512MB) به مسیر
استریم می‌رود؛ WindowGenerator label را فقط برای «سطر آخر» می‌ساخت
([batch, 2]) و RangeLoss که [batch, window, 2] می‌خواهد کرش می‌کرد:
«Index out of range using input dim 2; input has only 2 dims».

قفل‌ها: window_at با seq2seq برچسبِ هر سطر پنجره را می‌دهد؛
_to_arrays و to_tf_dataset شکل [batch, window, n_targets] می‌دهند.
"""

from __future__ import annotations

import numpy as np
import pytest

from ShadBotTrader.infrastructure.ai.window_generator import WindowGenerator


def _series(rows: int = 20):
    return [[float(r) + c / 10 for c in range(3)] + [100.0 + r, 90.0 + r] for r in range(rows)]


def _gen(seq2seq: bool, rows: int = 20):
    return WindowGenerator(
        series=_series(rows),
        target_columns=[3, 4],
        window_size=5,
        horizon=0,
        stride=1,
        scale=True,
        classification=False,
        seq2seq=seq2seq,
    )


def test_seq2seq_labels_cover_every_window_row():
    gen = _gen(seq2seq=True)
    window, label = gen.window_at(0)

    assert len(window) == 5
    assert len(label) == 5 and len(label[0]) == 2
    series = _series()
    for i in range(5):
        assert label[i] == [series[i][3], series[i][4]]


def test_non_seq2seq_labels_stay_last_row_only():
    gen = _gen(seq2seq=False)
    window, label = gen.window_at(0)
    assert len(label) == 2  # فقط [high, low] سطر آخر


def test_to_arrays_shapes():
    gen = _gen(seq2seq=True)
    w, label = gen.window_at(0)
    x, y = gen._to_arrays(np, [w], [label])
    assert x.shape == (1, 5, 3)
    assert y.shape == (1, 5, 2)


def test_tf_dataset_yields_three_dim_labels():
    pytest.importorskip("tensorflow")
    gen = _gen(seq2seq=True)
    ds = gen.to_tf_dataset(batch_size=2, start=0, stop=10)
    for _xb, yb in ds.take(1):
        assert yb.shape[1:] == (5, 2)
        break
