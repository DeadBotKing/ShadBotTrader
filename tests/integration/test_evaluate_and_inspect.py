"""Phase 48 — test a model, inspect a dataset, see the matrix and the network.

Three operator requests:

    "add a section where I pick a model and a dataset, run the test, and
     the error and accuracy get saved to a log"
    "and a section where I pick a dataset and it shows me what the
     dataset is, what matrix, and how many by how many"
    "and in training and retraining, first show the matrix dimensions
     and save the model architecture as a PNG"

The evaluation is the delicate one. A number that comes from a model
that quietly kept learning, or from a matrix assembled differently from
the one training used, describes a model nobody has. So the weights are
frozen, the windows are rebuilt exactly as training builds them, and the
result records which dataset the model was originally trained on — a
model scored on its own training timeframe is being flattered, and the
report says so.
"""

import json

import pytest

from ShadBotTrader.application.services.model_evaluation_service import (
    EvaluationResult,
    ModelEvaluationService,
)
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.infrastructure.ai.model_diagram import (
    DiagramResult,
    describe_input_matrix,
    save_model_diagram,
)
from ShadBotTrader.presentation.commands.commands import (
    Command,
    CommandKind,
    CommandStatus,
)
from ShadBotTrader.presentation.commands.handlers import (
    AccountCommandHandlers,
    descriptors,
)


def field_of(kind, name, root):
    descriptor = next(item for item in descriptors(root) if item.kind is kind)
    return next(item for item in descriptor.fields if item.name == name)


def a_record(model_id="gold_range_1d", role="range", timeframe="1D"):
    return ModelRecord(
        model_id=model_id,
        role=role,
        symbol="TESTSYM",
        timeframe=timeframe,
        version=1,
        rows=597,
        windows=529,
        window_size=64,
        feature_columns=123,
        epochs=3,
        folds=1,
        metrics={"val_mae": 0.0028},
    )


# ------------------------------------------------ 1) evaluating a model --
class TestTheEvaluationButton:
    def test_it_offers_models_and_datasets_as_dropdowns(self, tmp_path):
        ModelCatalogue(tmp_path).write(a_record())

        model_field = field_of(CommandKind.EVALUATE_MODEL, "saved_model", tmp_path)
        dataset_field = field_of(CommandKind.EVALUATE_MODEL, "dataset", tmp_path)

        assert model_field.kind == "select"
        assert "gold_range_1d" in model_field.options
        assert dataset_field.kind == "select"

    def test_with_no_models_it_says_so_rather_than_failing_oddly(self, tmp_path):
        pytest.importorskip("tensorflow")
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.evaluate_model(Command(CommandKind.EVALUATE_MODEL, {}))

        assert result.status is CommandStatus.REJECTED
        assert "Train a model" in result.message

    def test_an_unknown_model_is_refused_with_the_options(self, tmp_path):
        pytest.importorskip("tensorflow")
        ModelCatalogue(tmp_path).write(a_record())
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.evaluate_model(
            Command(CommandKind.EVALUATE_MODEL, {"saved_model": "nope"})
        )

        assert result.status is CommandStatus.REJECTED
        assert "gold_range_1d" in result.message

    def test_a_missing_matrix_is_reported_not_crashed(self, tmp_path):
        ModelCatalogue(tmp_path).write(a_record())
        service = ModelEvaluationService(tmp_path, tmp_path / "logs")

        result = service.evaluate("gold_range_1d", "TESTSYM", "1H")

        assert result.failed
        assert "Build training dataset" in result.reason

    def test_a_missing_model_is_reported_not_crashed(self, tmp_path):
        service = ModelEvaluationService(tmp_path, tmp_path / "logs")

        result = service.evaluate("ghost_model", "TESTSYM", "1D")

        assert result.failed
        assert "No saved model" in result.reason


class TestTheEvaluationLog:
    def test_every_run_is_appended_never_overwritten(self, tmp_path):
        """A comparison is worthless if yesterday's number is gone."""
        service = ModelEvaluationService(tmp_path, tmp_path / "logs")

        for index in range(3):
            service.append_to_log(
                EvaluationResult(
                    model_id="gold_range_1d",
                    role="range",
                    symbol="TESTSYM",
                    timeframe="1D",
                    metrics={"mae": 0.001 * (index + 1)},
                )
            )

        lines = service.log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        assert [json.loads(line)["metrics"]["mae"] for line in lines] == [
            pytest.approx(0.001),
            pytest.approx(0.002),
            pytest.approx(0.003),
        ]

    def test_the_history_survives_a_torn_line(self, tmp_path):
        service = ModelEvaluationService(tmp_path, tmp_path / "logs")
        service.append_to_log(
            EvaluationResult(model_id="a", role="range", symbol="S", timeframe="1D")
        )
        with service.log_path.open("a", encoding="utf-8") as handle:
            handle.write("{ this line was cut off\n")
        service.append_to_log(
            EvaluationResult(model_id="b", role="range", symbol="S", timeframe="1D")
        )

        history = service.history()

        assert [item["model_id"] for item in history] == ["a", "b"]

    def test_the_headline_names_the_metric_of_the_role(self):
        ranged = EvaluationResult(
            model_id="r", role="range", symbol="S", timeframe="1D", metrics={"mae": 0.0028}
        )
        signal = EvaluationResult(
            model_id="s",
            role="signal",
            symbol="S",
            timeframe="5M",
            metrics={"accuracy": 0.83},
            baseline=0.58,
        )

        assert "mae 0.002800" in ranged.headline
        assert "83.00%" in signal.headline
        assert "BETTER" in signal.headline

    def test_a_model_that_only_matches_its_baseline_is_called_out(self):
        """70% on a 70/15/15 split has learned nothing."""
        result = EvaluationResult(
            model_id="s",
            role="signal",
            symbol="S",
            timeframe="5M",
            metrics={"accuracy": 0.70},
            baseline=0.70,
        )

        assert "NO BETTER" in result.headline

    def test_scoring_on_the_training_timeframe_is_flagged(self):
        """Not an error — but the number means much less."""
        result = EvaluationResult(
            model_id="r",
            role="range",
            symbol="S",
            timeframe="1D",
            trained_on="1D",
            metrics={"mae": 0.001},
        )

        assert result.is_same_dataset_it_trained_on
        assert any("flatters it" in line for line in result.summary_lines())

    def test_a_different_timeframe_is_not_flagged(self):
        result = EvaluationResult(
            model_id="r",
            role="range",
            symbol="S",
            timeframe="1H",
            trained_on="1D",
            metrics={"mae": 0.001},
        )

        assert not result.is_same_dataset_it_trained_on


# ------------------------------------------------ 2) inspecting a dataset --
class TestTheInspectButton:
    def test_the_dataset_is_a_dropdown(self, tmp_path):
        field = field_of(CommandKind.INSPECT_DATASET, "dataset", tmp_path)

        assert field.kind == "select"

    def test_it_reports_the_matrix_shape(self, tmp_path):
        from tests.integration.test_evaluate_and_inspect import _seed_matrix

        _seed_matrix(tmp_path, "TESTSYM", "1D", rows=200, columns=123)
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.inspect_dataset(
            Command(
                CommandKind.INSPECT_DATASET,
                {"symbol": "TESTSYM", "dataset": "1D", "window": "64"},
            )
        )

        assert result.status is CommandStatus.SUCCEEDED
        assert "200 x 123" in result.message
        body = "\n".join(result.lines)
        assert "dataset matrix : 200 rows x 123 columns" in body
        assert "model input    : 64 rows x 123 columns per window" in body
        assert "tensor shape" in body

    def test_a_dataset_without_a_matrix_says_what_to_do(self, tmp_path):
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.inspect_dataset(
            Command(CommandKind.INSPECT_DATASET, {"symbol": "TESTSYM", "dataset": "1D"})
        )

        assert result.status is CommandStatus.SUCCEEDED
        assert any("Build training dataset" in line for line in result.lines)


def _seed_matrix(root, symbol, timeframe, rows=200, columns=123):
    """Write a training matrix straight to disk for the inspector to read."""
    import numpy as np

    from ShadBotTrader.infrastructure.ai.feature_matrix import CANDLE_COLUMNS

    names = list(CANDLE_COLUMNS) + [f"feature_{i}" for i in range(columns - len(CANDLE_COLUMNS))]
    path = root / "training" / symbol / f"{timeframe}_matrix.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        rows=np.array(
            [[float(r % 7) / 7 for _ in range(columns)] for r in range(rows)], dtype=np.float32
        ),
        columns=np.array(names, dtype=object),
        source_index=np.arange(rows, dtype=np.int64),
    )
    return path


# --------------------------------------------- 3) matrix + architecture --
class TestTheMatrixIsDescribedBeforeTraining:
    def test_the_description_states_the_tensor_shape(self):
        lines = describe_input_matrix(rows=49897, columns=123, window_size=500, horizon=5)
        body = "\n".join(lines)

        assert "49,897 rows x 123 columns" in body
        assert "14 candle-derived + 109 catalogue features" in body
        assert "(49,393, 500, 123)" in body

    def test_too_few_rows_reports_zero_windows(self):
        lines = describe_input_matrix(rows=100, columns=123, window_size=500, horizon=5)

        assert "windows        : 0" in "\n".join(lines)

    def test_the_training_script_prints_it(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "describe_input_matrix" in source
        assert "INPUT MATRIX" in source


class TestTheArchitectureDiagram:
    def test_a_png_is_written_for_a_real_model(self, tmp_path):
        pytest.importorskip("tensorflow")
        import tensorflow as tf

        model = tf.keras.Sequential([tf.keras.layers.Input(shape=(8,)), tf.keras.layers.Dense(3)])

        result = save_model_diagram(model, tmp_path / "arch.png", title="test model")

        assert result.saved
        assert result.path.exists()
        assert result.path.stat().st_size > 0
        assert "diagram saved" in result.describe()

    def test_the_summary_text_is_readable_without_box_glyphs(self, tmp_path):
        """The default Pillow font draws box characters as empty squares."""
        from ShadBotTrader.infrastructure.ai.model_diagram import _to_ascii_box

        assert _to_ascii_box("┏━━━┳━━━┓") == "+===+===+"
        assert _to_ascii_box("│ Layer │") == "| Layer |"

    def test_a_failure_is_reported_not_raised(self, tmp_path):
        """A missing diagram must never stop a training run."""

        class Hopeless:
            def summary(self, print_fn=None):
                raise RuntimeError("no summary available")

        result = save_model_diagram(Hopeless(), tmp_path / "arch.png")

        assert isinstance(result, DiagramResult)
        assert result.reason  # it explains itself

    def test_the_training_script_saves_one(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "save_model_diagram" in source
        assert "_architecture.png" in source

    def test_it_is_saved_only_once_per_run(self):
        """Twenty epochs must not write twenty PNGs."""
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "diagram_done" in source
