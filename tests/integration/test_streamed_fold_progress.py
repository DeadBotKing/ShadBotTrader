"""Phase 43 — a streamed fold must not crash the batch progress callback.

The operator's crash, on the real 5M dataset (47,886 training windows):

    total_batches=max(1, -(-len(train_x) // max(self._batch_size, 1)))
    TypeError: The dataset is infinite.

Phase 41 made large folds stream from a ``tf.data`` pipeline, and Phase
41 also made that pipeline ``repeat()`` so a multi-epoch run does not
run dry between epochs. A repeating dataset has no length — asking for
one raises. The batch callback was still asking.

The fold geometry already knows how many batches an epoch contains, so
the count comes from arithmetic now. These tests pin both halves: the
dataset really is infinite, and the trainer never asks it how long it is.
"""

import ast
from pathlib import Path

import pytest

TRAINER = (
    Path(__file__).resolve().parents[2]
    / "src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py"
)


class TestTheTrainerNeverMeasuresAStreamedDataset:
    def test_len_is_not_called_on_the_training_input(self):
        """The exact expression that crashed, gone for good."""
        source = TRAINER.read_text(encoding="utf-8")

        assert "len(train_x)" not in source
        assert "len(val_x)" not in source

    def test_the_batch_count_comes_from_the_fold_geometry(self):
        source = TRAINER.read_text(encoding="utf-8")

        assert "train_steps or max(" in source
        assert "batches_per_epoch" in source

    def test_no_len_call_wraps_a_dataset_variable(self):
        """Parse it rather than trust a substring search."""
        tree = ast.parse(TRAINER.read_text(encoding="utf-8"))
        offenders = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "len"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in {"train_x", "val_x"}
            ):
                offenders.append(node.args[0].id)

        assert offenders == []


class TestARepeatedDatasetReallyHasNoLength:
    def test_len_raises_on_a_repeating_dataset(self):
        """Proves the failure mode is real, not a misread of the traceback."""
        tf = pytest.importorskip("tensorflow")

        dataset = tf.data.Dataset.from_tensor_slices([1, 2, 3]).repeat()

        with pytest.raises(TypeError, match="infinite"):
            len(dataset)

    def test_the_generator_repeats_only_when_asked(self):
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.window_generator import WindowGenerator

        series = [[float(i % 5)] * 4 + [0.01, -0.01] for i in range(200)]
        generator = WindowGenerator(
            series=series, target_columns=[4, 5], window_size=20, horizon=0, stride=1
        )

        finite = generator.to_tf_dataset(batch_size=8)
        infinite = generator.to_tf_dataset(batch_size=8, repeat=True)

        # A from_generator dataset never reports a length — "unknown"
        # without repeat(), "infinite" with it. Either way len() raises,
        # which is precisely why the batch count must not come from it.
        with pytest.raises(TypeError):
            len(finite)
        with pytest.raises(TypeError, match="infinite"):
            len(infinite)

        # But it still yields exactly the right number of batches.
        assert sum(1 for _ in finite) == -(-generator.window_count // 8)


class TestTheStreamedPathReportsItsBatches:
    def test_steps_are_returned_for_a_streamed_fold(self):
        """_dataset_for must hand back a usable steps_per_epoch."""
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

        rows, columns, window = 6000, 60, 500
        series = [
            [float((row * col) % 7) / 7.0 for col in range(columns)] + [0.01, -0.01]
            for row in range(rows)
        ]
        trainer = WavenetTrainer(
            series=series,
            target_column=0,
            target_columns=[columns, columns + 1],
            window_size=window,
            batch_size=32,
        )
        trainer._n_features_cache = columns
        trainer._stream_all = True

        dataset, labels, steps = trainer._dataset_for(0, 4000)

        assert labels is None, "a streamed fold carries its labels inside the dataset"
        assert steps == -(-4000 // 32)
        with pytest.raises(TypeError, match="infinite"):
            len(dataset)

    def test_a_small_fold_still_uses_plain_arrays(self):
        """Streaming is for large folds; small ones keep the fast path."""
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

        rows, columns, window = 300, 8, 20
        series = [[float(row % 5)] * columns + [0.01, -0.01] for row in range(rows)]
        trainer = WavenetTrainer(
            series=series,
            target_column=0,
            target_columns=[columns, columns + 1],
            window_size=window,
            batch_size=8,
        )
        trainer._n_features_cache = columns
        from ShadBotTrader.infrastructure.ai.data_windowing import (
            build_multi_target_samples,
        )

        trainer._samples = build_multi_target_samples(
            series, window_size=window, target_columns=[columns, columns + 1], scale=True
        )

        x, y, steps = trainer._dataset_for(0, 50)

        assert y is not None
        assert steps == 0  # 0 means "let Keras infer it from the arrays"
        assert len(x) == 50
