"""Phase 49 — the label rule travels with the model.

The gap this closes was found while reading the Phase 48 evaluator: it
rebuilt the BUY/SELL/HOLD labels with a hard-coded ``threshold = 0.0008``
no matter what the model was trained with. A signal model taught at
0.25% was therefore marked against an exam it never sat — most of the
moves it was trained to call HOLD count as BUY or SELL in the answer
key, so its accuracy came out lower than the truth and the operator was
being told a model was bad when it had simply been graded wrongly.

Three things are proven here:

1. training writes the threshold (and the horizon) into the model record
2. the evaluator rebuilds the labels with THAT threshold, not a constant
3. a model saved before Phase 49 still evaluates, but the report says
   the threshold was assumed rather than read

The measured distribution on the operator's real 5M gold data is what
makes this matter rather than being a tidiness exercise::

    threshold   BUY     SELL    HOLD
    0.08%       29.9%   28.7%   41.4%
    0.25%        8.6%    8.4%   83.0%

The same weights scored against those two answer keys are two different
numbers, and only one of them describes a model that exists.
"""

import json
import math
from pathlib import Path

import pytest

from ShadBotTrader.application.services.model_evaluation_service import (
    DEFAULT_THRESHOLD,
    EvaluationResult,
    ModelEvaluationService,
)
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.presentation.commands.commands import Command, CommandKind
from ShadBotTrader.presentation.commands.handlers import descriptors

REPO_ROOT = Path(__file__).resolve().parents[2]


def a_signal_record(threshold=0.0025, horizon=5, **extra):
    payload = dict(
        model_id="gold_signal_5m",
        role="signal",
        symbol="TESTSYM",
        timeframe="5M",
        version=1,
        rows=600,
        windows=530,
        window_size=64,
        feature_columns=123,
        epochs=3,
        folds=1,
        threshold=threshold,
        horizon=horizon,
        metrics={"val_accuracy": 0.71},
    )
    payload.update(extra)
    return ModelRecord(**payload)


# ------------------------------------------- 1) the record carries it --
class TestTheRecordCarriesTheThreshold:
    def test_it_survives_a_write_and_a_read(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(a_signal_record(threshold=0.0025, horizon=7))

        loaded = catalogue.read("gold_signal_5m", 1)

        assert loaded is not None
        assert loaded.threshold == pytest.approx(0.0025)
        assert loaded.horizon == 7

    def test_it_appears_in_the_json_on_disk(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        path = catalogue.write(a_signal_record(threshold=0.0015))

        payload = json.loads(path.read_text(encoding="utf-8"))

        assert payload["threshold"] == pytest.approx(0.0015)
        assert payload["horizon"] == 5

    def test_a_record_written_before_phase_49_still_loads(self, tmp_path):
        """Absence must read as zero, not crash the dropdown."""
        directory = tmp_path / "models" / "gold_signal_5m"
        directory.mkdir(parents=True)
        (directory / "v1_training.json").write_text(
            json.dumps(
                {
                    "model_id": "gold_signal_5m",
                    "role": "signal",
                    "symbol": "TESTSYM",
                    "timeframe": "5M",
                    "version": 1,
                }
            ),
            encoding="utf-8",
        )

        loaded = ModelCatalogue(tmp_path).read("gold_signal_5m", 1)

        assert loaded is not None
        assert loaded.threshold == 0.0
        assert loaded.horizon == 0

    def test_the_summary_states_the_band_for_a_signal_model(self):
        lines = a_signal_record(threshold=0.0025).summary_lines()

        assert any("0.2500%" in line for line in lines)

    def test_a_range_model_does_not_pretend_to_have_one(self):
        record = ModelRecord(
            model_id="gold_range_1d",
            role="range",
            symbol="TESTSYM",
            timeframe="1D",
        )

        assert record.threshold_percent == "n/a"
        assert not any("threshold" in line for line in record.summary_lines())


# --------------------------------------------- 2) training writes it --
class TestTrainingWritesIt:
    def test_both_save_paths_record_the_role_threshold(self):
        """Checkpoint save AND final save — missing either loses it."""
        source = (REPO_ROOT / "scripts" / "run_dual_models.py").read_text(encoding="utf-8")

        occurrences = source.count("threshold=(float(role.target.threshold)")
        assert occurrences == 2, (
            "the threshold must be written by the per-epoch checkpoint and by "
            f"the final save; found {occurrences} of the 2 call sites"
        )

    def test_the_horizon_is_recorded_too(self):
        source = (REPO_ROOT / "scripts" / "run_dual_models.py").read_text(encoding="utf-8")

        assert source.count("horizon=int(role.horizon)") == 2


# ----------------------------------------- 3) evaluation reads it back --
class TestTheEvaluatorUsesTheRecordedThreshold:
    def test_no_hard_coded_threshold_is_left_in_the_scorer(self):
        """The exact bug: `threshold = 0.0008` sitting inside _score_signal."""
        import ast
        import inspect

        from ShadBotTrader.application.services import model_evaluation_service

        source = inspect.getsource(model_evaluation_service.ModelEvaluationService._score_signal)
        tree = ast.parse(source.strip())

        assigned = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "threshold" for target in node.targets
            )
        ]
        assert not assigned, "_score_signal must take the threshold as a parameter"
        assert (
            "threshold"
            in inspect.signature(
                model_evaluation_service.ModelEvaluationService._score_signal
            ).parameters
        )

    def test_the_labels_change_when_the_threshold_changes(self, tmp_path):
        """The whole point: two bands, two answer keys, two accuracies."""
        forward_returns = [0.0020, -0.0020, 0.0004, -0.0004, 0.0030]

        def label(forward, threshold):
            return 2 if forward > threshold else 0 if forward < -threshold else 1

        loose = [label(value, 0.0008) for value in forward_returns]
        tight = [label(value, 0.0025) for value in forward_returns]

        assert loose == [2, 0, 1, 1, 2]
        assert tight == [1, 1, 1, 1, 2]
        assert loose != tight

    def test_a_model_with_a_threshold_is_scored_against_its_own_band(self, tmp_path):
        pytest.importorskip("tensorflow")
        _train_a_tiny_signal_model(tmp_path, threshold=0.0025)

        service = ModelEvaluationService(tmp_path, tmp_path / "logs")
        result = service.evaluate("gold_signal_5m", "TESTSYM", "5M", max_windows=40)

        assert not result.failed, result.reason
        assert result.threshold == pytest.approx(0.0025)
        assert not result.threshold_assumed
        assert any("0.2500%" in line for line in result.summary_lines())

    def test_a_pre_phase_49_model_says_the_band_was_assumed(self, tmp_path):
        pytest.importorskip("tensorflow")
        _train_a_tiny_signal_model(tmp_path, threshold=0.0)

        service = ModelEvaluationService(tmp_path, tmp_path / "logs")
        result = service.evaluate("gold_signal_5m", "TESTSYM", "5M", max_windows=40)

        assert not result.failed, result.reason
        assert result.threshold == pytest.approx(DEFAULT_THRESHOLD)
        assert result.threshold_assumed
        assert any("ASSUMED" in line for line in result.summary_lines())

    def test_the_band_reaches_the_evaluation_log(self, tmp_path):
        service = ModelEvaluationService(tmp_path, tmp_path / "logs")
        service.append_to_log(
            EvaluationResult(
                model_id="gold_signal_5m",
                role="signal",
                symbol="TESTSYM",
                timeframe="5M",
                threshold=0.0025,
                horizon=5,
            )
        )

        entry = service.history()[-1]

        assert entry["threshold"] == pytest.approx(0.0025)
        assert entry["horizon"] == 5


# -------------------------------------- 4) retraining inherits the band --
class TestRetrainingInheritsTheBand:
    def test_the_field_is_empty_so_the_model_supplies_the_default(self, tmp_path):
        ModelCatalogue(tmp_path).write(a_signal_record(threshold=0.0025))

        descriptor = next(
            item for item in descriptors(tmp_path) if item.kind is CommandKind.TRAIN_MODEL
        )
        field = next(item for item in descriptor.fields if item.name == "threshold_pct")

        assert field.default == ""
        assert "keep the threshold" in field.hint

    def test_a_blank_field_keeps_the_saved_band(self, tmp_path):
        """0.25% must not silently become 0.08% because a box was empty."""
        pytest.importorskip("tensorflow")
        from ShadBotTrader.presentation.commands.handlers import AccountCommandHandlers

        ModelCatalogue(tmp_path).write(a_signal_record(threshold=0.0025))
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        captured = {}

        def fake_run_script(command, argv, message, started, timeout=0):
            captured["argv"] = argv
            return None

        handlers._run_script = fake_run_script  # type: ignore[method-assign]
        handlers.train_model(
            Command(
                CommandKind.TRAIN_MODEL,
                {"saved_model": "gold_signal_5m", "dataset": "5M", "threshold_pct": ""},
            )
        )

        argv = captured["argv"]
        assert float(argv[argv.index("--threshold") + 1]) == pytest.approx(0.0025)

    def test_an_explicit_percent_still_wins(self, tmp_path):
        pytest.importorskip("tensorflow")
        from ShadBotTrader.presentation.commands.handlers import AccountCommandHandlers

        ModelCatalogue(tmp_path).write(a_signal_record(threshold=0.0025))
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        captured = {}

        def fake_run_script(command, argv, message, started, timeout=0):
            captured["argv"] = argv
            return None

        handlers._run_script = fake_run_script  # type: ignore[method-assign]
        handlers.train_model(
            Command(
                CommandKind.TRAIN_MODEL,
                {"saved_model": "gold_signal_5m", "dataset": "5M", "threshold_pct": "0.4"},
            )
        )

        argv = captured["argv"]
        assert float(argv[argv.index("--threshold") + 1]) == pytest.approx(0.004)


# ------------------------------------------------------------ helpers --
def _train_a_tiny_signal_model(root, threshold):
    """Save a real (tiny) Keras signal model plus its record and matrix.

    Real weights rather than a stub: the evaluator loads and runs them,
    so a fake would prove nothing about the path under test.
    """
    import numpy as np
    import tensorflow as tf

    from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.infrastructure.ai.feature_matrix import CANDLE_COLUMNS
    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
        FilesystemArtifactStore,
    )
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _serialize_model

    window_size = 8
    columns = len(CANDLE_COLUMNS)

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(window_size, columns)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(3, activation="softmax"),
        ]
    )

    FilesystemArtifactStore(root).save(
        ModelArtifact.create(
            model_id=ModelId("gold_signal_5m"),
            version=ModelVersion(1),
            framework="tensorflow",
            framework_version="",
            format="keras",
            payload=_serialize_model(model),
            training_run_id="threshold-test",
        )
    )

    ModelCatalogue(root).write(
        a_signal_record(threshold=threshold, window_size=window_size, feature_columns=columns)
    )

    # A matrix with a real return_1 column so labels can be rebuilt.
    rows = 120
    values = []
    for index in range(rows):
        row = [0.0] * columns
        row[CANDLE_COLUMNS.index("return_1")] = 0.001 * math.sin(index / 3.0)
        row[CANDLE_COLUMNS.index("close_rel")] = 1.0
        values.append(row)

    path = root / "training" / "TESTSYM" / "5M_matrix.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        rows=np.array(values, dtype=np.float32),
        columns=np.array(list(CANDLE_COLUMNS), dtype=object),
        source_index=np.arange(rows, dtype=np.int64),
    )
