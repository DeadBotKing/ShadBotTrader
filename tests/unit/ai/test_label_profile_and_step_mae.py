"""فاز ۹۵-د — پروفایل لیبل و خطای per-step.

* ``seq2seq_label_profile``: میانهٔ لیبل هر گام (اقلیم داده) — مدلِ
  بی‌مهارت دقیقاً به همین منحنی می‌رسد.
* ``_range_validation_metrics``: MAE به تفکیک گام k روی آخرین timestep
  (همان خروجی که inference مصرف می‌کند) — بدون نیاز به TensorFlow.
"""

import numpy as np
import pytest

from ShadBotTrader.infrastructure.ai.target_builder import seq2seq_label_profile


def _row(values: list[float]) -> list[float]:
    """Feature noise + flat targets [h1, l1, h2, l2, ...]."""
    return [0.0, 0.0] + values


class TestSeq2SeqLabelProfile:
    def test_medians_split_train_vs_recent(self):
        # 4 rows: first 2 train, last 2 recent (val_size=2)
        rows = [
            _row([0.10, -0.10, 0.30, -0.30]),
            _row([0.20, -0.20, 0.40, -0.40]),
            _row([9.00, -9.00, 1.00, -1.00]),
            _row([1.00, -2.00, 2.00, -2.00]),
        ]
        profile = seq2seq_label_profile(rows, target_columns=[2, 3, 4, 5], val_size=2)

        assert set(profile) == {"train", "recent"}
        # train medians of (0.10, 0.20) etc.
        assert profile["train"]["high"] == [pytest.approx(0.15), pytest.approx(0.35)]
        assert profile["train"]["low"] == [pytest.approx(-0.15), pytest.approx(-0.35)]
        # recent medians of (9.00, 1.00) and (1.00, 2.00)
        assert profile["recent"]["high"] == [pytest.approx(5.00), pytest.approx(1.50)]
        assert profile["recent"]["low"] == [pytest.approx(-5.50), pytest.approx(-1.50)]

    def test_zero_val_size_puts_everything_in_train(self):
        rows = [_row([0.1, -0.1, 0.3, -0.3]), _row([0.3, -0.3, 0.5, -0.5])]
        profile = seq2seq_label_profile(rows, target_columns=[2, 3, 4, 5], val_size=0)
        assert "recent" not in profile
        assert len(profile["train"]["high"]) == 2

    def test_empty_inputs_are_rejected_quietly(self):
        assert seq2seq_label_profile([], [2, 3], val_size=1) == {}
        assert seq2seq_label_profile([_row([0.1, -0.1])], [], val_size=1) == {}

    def test_odd_target_count_is_refused(self):
        profile = seq2seq_label_profile([_row([0.1, -0.1, 9.9])], [2, 3, 4], val_size=0)
        assert profile == {}


class TestPerStepValidationMetrics:
    def _metrics(self, actual: np.ndarray, predicted: np.ndarray) -> dict:
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

        trainer = WavenetTrainer.__new__(WavenetTrainer)  # بدون TF
        trainer._batch_size = 2
        fake_model = type(
            "M",
            (),
            {"predict": staticmethod(lambda x, verbose=0, steps=None: predicted)},
        )
        return trainer._range_validation_metrics(
            fake_model,
            validation_x=None,
            validation_y=actual,
            validation_steps=0,
            start=0,
            stop=0,
        )

    def test_seq2seq_metrics_use_the_last_timestep_per_step(self):
        # [N=2, window=3, H*2=4] — فقط آخرین timestep خوانده می‌شود
        last = np.array(
            [
                [0.10, -0.10, 0.50, -0.50],
                [0.30, -0.30, 0.70, -0.70],
            ]
        )
        actual = np.zeros((2, 3, 4))
        actual[:, -1, :] = last
        predicted = actual.copy()
        predicted[:, -1, 0] += 0.10  # high k1 error +0.1
        predicted[:, -1, 1] -= 0.10  # low  k1 error -0.1
        predicted[:, -1, 2] += 0.20  # high k2 error +0.2
        predicted[:, -1, 3] -= 0.20  # low  k2 error -0.2

        metrics = self._metrics(actual, predicted)

        assert metrics["val_high_mae"] == pytest.approx(0.10)
        assert metrics["val_low_mae"] == pytest.approx(0.10)
        assert metrics["val_step1_mae"] == pytest.approx(0.10)
        assert metrics["val_step2_mae"] == pytest.approx(0.20)

    def test_flat_output_shape_has_only_one_pair(self):
        # خروجی scalar فقط [high, low] دارد — فقط step1 تعریف دارد
        actual = np.array([[0.10, -0.10]])
        predicted = actual + np.array([[0.10, -0.10]])
        metrics = self._metrics(actual, predicted)
        assert metrics["val_step1_mae"] == pytest.approx(0.10)
        assert "val_step2_mae" not in metrics
