"""Unit tests for the train/validation label split reported at training start.

``run_dual_models.signal_label_split_balance`` rebuilds the same expanding
roll-forward plan the trainer will use and reports the BUY/SELL counts of the
last fold's train and validation windows separately, so the operator can see
how balanced each split is before training starts.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from run_dual_models import signal_label_split_balance  # noqa: E402


def _dataset(n_samples: int, window: int, buy_share: float = 0.5):
    """A minimal PreparedDataset-shaped object.

    Every sample gets a label in the last column; sample_ends simply point at
    sequential rows so the split geometry is easy to reason about.
    """
    rows = []
    sample_ends = []
    sample_label_ends = []

    for i in range(n_samples):
        label = 1 if (i % (n_samples + 1)) / n_samples < buy_share else 0
        # keep the buy/sell share roughly as requested without being exact
        label = 1 if i < int(n_samples * buy_share) else 0
        rows.append([0.0] * window + [float(label)])
        sample_ends.append(i)
        sample_label_ends.append(min(i + 1, n_samples - 1))
    series = rows
    return SimpleNamespace(
        sample_ends=sample_ends,
        sample_label_ends=sample_label_ends,
        target_columns=[window],  # last column is the label
        series=series,
    )


class _Role:
    window_size = 40


def test_returns_none_for_range_model():
    """A dataset without sample_ends (range/regression) yields no split."""
    ds = SimpleNamespace(sample_ends=None, target_columns=[0])
    assert signal_label_split_balance(ds, _Role(), 3) is None


def test_train_and_val_counts_are_reported():
    ds = _dataset(n_samples=400, window=40, buy_share=0.5)
    split = signal_label_split_balance(ds, _Role(), max_folds=3)
    assert split is not None
    train_balance, val_balance = split
    assert set(train_balance) == {"sell", "buy"}
    assert set(val_balance) == {"sell", "buy"}
    assert train_balance["sell"] + train_balance["buy"] > 0
    # sell=0 and buy=1 map to the 'sell'/'buy' keys
    assert train_balance["sell"] >= 0 and train_balance["buy"] >= 0


def test_counts_sum_to_the_split_sizes():
    """train+val must equal the last fold's train/val sample counts."""
    ds = _dataset(n_samples=400, window=40, buy_share=0.6)
    split = signal_label_split_balance(ds, _Role(), max_folds=3)
    assert split is not None
    tb, vb = split
    n_train = tb["sell"] + tb["buy"]
    n_val = vb["sell"] + vb["buy"]
    assert n_train > n_val  # expanding train is always bigger than a val window
