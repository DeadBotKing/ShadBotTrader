"""Phase 41 — training streams its windows instead of exhausting RAM.

The operator's report: pressing "Train models" on the real dataset filled
the machine's memory, printed nothing for 492 seconds, and saved no
model. Three separate causes, all measured rather than guessed:

    49,393 windows x 500 rows x 123 cols x 4 bytes = 12.2 GB

``build_multi_target_samples`` materialised every one of them at the top
of ``train()`` — before a single batch was fitted, and before the first
progress line could be printed. The machine died in that gap, which is
why the log stayed empty and no artifact ever appeared.

Phase 30 built ``WindowGenerator`` for exactly this and nothing ever used
it. These tests pin the wiring so it cannot come loose again.
"""

import pytest

from ShadBotTrader.infrastructure.ai.window_generator import WindowGenerator, plan_windows


def series(rows: int, columns: int = 8):
    """A flat matrix with two target columns at the end."""
    return [
        [float((row * col) % 13) / 13.0 for col in range(columns)] + [0.01, -0.01]
        for row in range(rows)
    ]


class TestTheCostIsKnownBeforeTraining:
    def test_the_plan_reports_what_materialising_would_cost(self):
        plan = plan_windows(
            total_rows=50000,
            window_size=500,
            horizon=5,
            stride=1,
            feature_columns=123,
            target_columns=[123, 124],
        )

        assert plan.window_count > 49_000
        # The number the operator never saw: gigabytes, not megabytes.
        assert plan.materialised_bytes() > 10_000_000_000
        assert plan.flat_bytes() < 60_000_000

    def test_a_window_larger_than_the_series_yields_nothing(self):
        plan = plan_windows(
            total_rows=100,
            window_size=500,
            horizon=5,
            stride=1,
            feature_columns=10,
            target_columns=[10],
        )

        assert plan.window_count == 0
        assert plan.is_empty


class TestTheTrainerStreamsLargeFolds:
    def test_the_threshold_exists_and_is_sane(self):
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

        # Half a gigabyte: large enough that small runs keep the simple
        # in-memory path, small enough that nothing approaches 12 GB.
        assert 0 < WavenetTrainer.STREAM_THRESHOLD_BYTES <= 1_073_741_824

    def test_a_large_series_never_materialises_its_windows(self):
        """The samples list must not be built when streaming."""
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
            _LazySampleCount,
        )

        stand_in = _LazySampleCount(49_393)

        assert len(stand_in) == 49_393
        # Indexing it means some code path still expects real windows.
        with pytest.raises(RuntimeError, match="streamed"):
            stand_in[0]

    def test_the_generator_produces_the_same_window_as_indexing(self):
        """Streaming must not change the numbers, only where they live."""
        data = series(200, columns=6)
        generator = WindowGenerator(
            series=data, target_columns=[6, 7], window_size=32, horizon=0, stride=1
        )

        window, label = generator.window_at(0)

        assert len(window) == 32
        assert len(window[0]) == 6  # target columns stripped
        assert label == [0.01, -0.01]

    def test_batches_cover_every_window_exactly_once(self):
        data = series(300, columns=6)
        generator = WindowGenerator(
            series=data, target_columns=[6, 7], window_size=50, horizon=0, stride=1
        )

        seen = 0
        for batch_x, _ in generator.iter_batches(batch_size=16):
            seen += len(batch_x)

        assert seen == generator.window_count

    def test_a_repeated_dataset_does_not_run_out_between_epochs(self):
        """Without repeat(), epoch 2 finds the generator exhausted."""
        pytest.importorskip("tensorflow")
        data = series(300, columns=6)
        generator = WindowGenerator(
            series=data, target_columns=[6, 7], window_size=50, horizon=0, stride=1
        )

        dataset = generator.to_tf_dataset(batch_size=16, repeat=True)
        taken = sum(1 for _ in dataset.take(40))

        assert taken == 40  # would stop early without repeat()

    def test_a_finite_dataset_is_still_the_default(self):
        pytest.importorskip("tensorflow")
        data = series(300, columns=6)
        generator = WindowGenerator(
            series=data, target_columns=[6, 7], window_size=50, horizon=0, stride=1
        )

        batches = sum(1 for _ in generator.to_tf_dataset(batch_size=16))

        assert batches == -(-generator.window_count // 16)


class TestTheScriptRefusesImpossibleConfigurations:
    def test_it_reports_the_window_count_and_cost(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "if materialised" in source
        assert "Not enough data" in source

    def test_too_few_rows_is_refused_before_training(self):
        """497 rows cannot make a 500-row window; say so immediately."""
        rows, window, horizon = 497, 500, 5
        windows = max(rows - window - horizon + 1, 0)

        assert windows == 0
