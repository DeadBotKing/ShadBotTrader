"""Phase 40 — dropdowns, and models that actually persist.

The user asked for four things:

    the model type should be a dropdown (price prediction vs signal)
    drop the Signal dataset / Range dataset(s) fields
    one dropdown listing the datasets we actually have (5M, 1H, 1D)
    save the model under its role and the dataset it learned from, and
    let "Retrain" pick from the saved models in a dropdown

Answering the fourth exposed a defect worth more than the feature:
``run_dual_models.py`` never saved anything. It fitted a network,
printed a prediction and exited. Nothing reached ``datasets/models/``,
so every training run since Phase 29 was discarded at process exit and
"Retrain the model" had nothing to retrain.
"""

import pytest

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.presentation.commands.commands import (
    Command,
    CommandField,
    CommandKind,
    CommandStatus,
)
from ShadBotTrader.presentation.commands.handlers import (
    MODEL_ROLE_CHOICES,
    AccountCommandHandlers,
    CommandHandlers,
    descriptors,
    stored_dataset_choices,
    trained_model_choices,
)
from ShadBotTrader.presentation.web.renderer import _render_field


def descriptor_for_kind(kind, storage_root):
    return next(item for item in descriptors(storage_root) if item.kind is kind)


def seed_candles(root, timeframe: str, count: int = 40):
    """Put a stored series on disk so it appears in the dataset list."""
    import math
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from ShadBotTrader.application.services.dataset_update_service import (
        DatasetUpdateService,
    )
    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp
    from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore

    minutes = {"5M": 5, "1H": 60, "1D": 1440}[timeframe]
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = 2000.0
    for index in range(count):
        close = price + math.sin(index / 7.0) * 3
        candles.append(
            Candle(
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(base + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(f"{price:.2f}")),
                high=Price(Decimal(f"{max(price, close) + 1:.2f}")),
                low=Price(Decimal(f"{min(price, close) - 1:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal("10"),
            )
        )
        price = close
    DatasetUpdateService(ParquetCandleStore(root)).update(
        "XAUUSD", timeframe, candles, allow_gap=True
    )


def record(model_id="gold_range_1d", role="range", timeframe="1D", version=1):
    return ModelRecord(
        model_id=model_id,
        role=role,
        symbol="XAUUSD",
        timeframe=timeframe,
        version=version,
        rows=2152,
        windows=2116,
        window_size=32,
        feature_columns=123,
        epochs=1,
        folds=1,
        metrics={"val_mae": 0.0164},
    )


# ------------------------------------------------------ 1) the dropdowns --
class TestTheFormUsesDropdowns:
    def test_a_select_field_renders_as_a_dropdown(self):
        markup = _render_field(
            CommandField(
                "model", "Model type", "signal", kind="select", options=("range", "signal")
            )
        )

        assert "<select" in markup
        assert '<option value="signal" selected>' in markup
        assert '<option value="range">' in markup

    def test_a_text_field_is_still_an_input(self):
        markup = _render_field(CommandField("symbol", "Symbol", "XAUUSD"))

        assert "<select" not in markup
        assert 'type="text"' in markup

    def test_a_select_without_options_falls_back_to_text(self):
        """An empty dropdown is not a choice; it is a dead end."""
        field = CommandField("m", "M", "", kind="select", options=())

        assert not field.is_select
        assert "<select" not in _render_field(field)

    def test_the_model_type_is_a_dropdown(self, tmp_path):
        descriptor = descriptor_for_kind(CommandKind.TRAIN_DUAL_MODELS, tmp_path)
        field = next(item for item in descriptor.fields if item.name == "model")

        assert field.kind == "select"
        assert set(field.options) == set(MODEL_ROLE_CHOICES)
        assert "range" in field.options and "signal" in field.options

    def test_the_dataset_is_a_dropdown_of_what_exists(self, tmp_path):
        seed_candles(tmp_path, "1H")
        seed_candles(tmp_path, "1D")

        descriptor = descriptor_for_kind(CommandKind.TRAIN_DUAL_MODELS, tmp_path)
        field = next(item for item in descriptor.fields if item.name == "dataset")

        assert field.kind == "select"
        assert set(field.options) == {"1H", "1D"}

    def test_the_removed_fields_are_gone(self, tmp_path):
        """The user asked for these two to disappear."""
        descriptor = descriptor_for_kind(CommandKind.TRAIN_DUAL_MODELS, tmp_path)
        names = {item.name for item in descriptor.fields}

        assert "range_timeframes" not in names
        assert "signal_timeframe" not in names
        assert "dataset" in names

    def test_datasets_are_listed_in_timeframe_order(self, tmp_path):
        for timeframe in ("1D", "5M", "1H"):
            seed_candles(tmp_path, timeframe)

        assert stored_dataset_choices(tmp_path) == ["5M", "1H", "1D"]

    def test_an_empty_store_still_offers_the_training_timeframes(self, tmp_path):
        """Better a sensible default than an empty dropdown."""
        assert stored_dataset_choices(tmp_path) == ["5M", "1H", "1D"]


# ------------------------------------------------- 2) models are saved ----
class TestTrainedModelsArePersisted:
    def test_the_training_script_saves_the_artifact(self):
        """The defect: it trained and then threw the result away."""
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "FilesystemArtifactStore" in source
        assert "save_model(" in source

    def test_a_record_carries_the_role_and_the_dataset(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(record())

        loaded = catalogue.read("gold_range_1d", 1)

        assert loaded is not None
        assert loaded.role == "range"
        assert loaded.timeframe == "1D"
        assert loaded.symbol == "XAUUSD"
        assert "range" in loaded.label and "1D" in loaded.label

    def test_the_headline_metric_matches_the_role(self, tmp_path):
        ranged = record()
        signal = ModelRecord(
            model_id="gold_signal_5m",
            role="signal",
            symbol="XAUUSD",
            timeframe="5M",
            metrics={"val_accuracy": 0.83},
        )

        assert "val_mae" in ranged.headline_metric
        assert "83.0%" in signal.headline_metric

    def test_retraining_writes_a_new_version_and_keeps_the_old(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(record(version=1))

        assert catalogue.next_version("gold_range_1d") == 2

        catalogue.write(record(version=2))

        assert catalogue.read("gold_range_1d", 1) is not None
        assert catalogue.read("gold_range_1d", 2) is not None
        assert catalogue.latest_version("gold_range_1d") == 2

    def test_the_list_shows_only_the_latest_version_of_each(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(record(version=1))
        catalogue.write(record(version=2))
        catalogue.write(record(model_id="gold_signal_5m", role="signal", timeframe="5M"))

        found = catalogue.list_all()

        assert {item.model_id for item in found} == {"gold_range_1d", "gold_signal_5m"}
        by_id = {item.model_id: item for item in found}
        assert by_id["gold_range_1d"].version == 2

    def test_a_corrupt_record_is_skipped_not_fatal(self, tmp_path):
        catalogue = ModelCatalogue(tmp_path)
        catalogue.write(record())
        catalogue.record_path("gold_range_1d", 1).write_text("{ broken", encoding="utf-8")

        assert catalogue.read("gold_range_1d", 1) is None
        assert catalogue.list_all() == []

    def test_an_artifact_can_be_renumbered_without_changing_its_bytes(self):
        artifact = ModelArtifact.create(
            ModelId("gold_range_1d"), ModelVersion(1), "tensorflow", "2.21", "keras", b"weights"
        )

        renumbered = artifact.with_version(4)

        assert renumbered.version.number == 4
        assert renumbered.payload == artifact.payload
        assert renumbered.checksum == artifact.checksum

    def test_nothing_trained_means_an_empty_list(self, tmp_path):
        assert trained_model_choices(tmp_path) == []


# ------------------------------------------------------- 3) retraining ----
class TestRetrainUsesTheSavedModels:
    def test_the_saved_model_field_lists_what_exists(self, tmp_path):
        ModelCatalogue(tmp_path).write(record())
        ModelCatalogue(tmp_path).write(
            record(model_id="gold_signal_5m", role="signal", timeframe="5M")
        )

        descriptor = descriptor_for_kind(CommandKind.TRAIN_MODEL, tmp_path)
        field = next(item for item in descriptor.fields if item.name == "saved_model")

        assert field.kind == "select"
        assert set(field.options) == {"gold_range_1d", "gold_signal_5m"}

    def test_retrain_offers_the_dataset_dropdown_too(self, tmp_path):
        seed_candles(tmp_path, "1D")
        descriptor = descriptor_for_kind(CommandKind.TRAIN_MODEL, tmp_path)
        field = next(item for item in descriptor.fields if item.name == "dataset")

        assert field.kind == "select"
        assert "1D" in field.options

    def test_retraining_without_any_model_is_refused_clearly(self, tmp_path):
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path)
        pytest.importorskip("tensorflow")

        result = handlers.train_model(Command(CommandKind.TRAIN_MODEL, {}))

        assert result.status is CommandStatus.REJECTED
        assert "Train a model" in result.message

    def test_an_unknown_model_is_refused(self, tmp_path):
        pytest.importorskip("tensorflow")
        ModelCatalogue(tmp_path).write(record())
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.train_model(
            Command(CommandKind.TRAIN_MODEL, {"saved_model": "not_a_model"})
        )

        assert result.status is CommandStatus.REJECTED
        assert "gold_range_1d" in result.message

    def test_the_saved_role_decides_which_flag_is_used(self, tmp_path, monkeypatch):
        """A range model must be retrained as a range model."""
        pytest.importorskip("tensorflow")
        ModelCatalogue(tmp_path).write(record())
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path)
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            from ShadBotTrader.presentation.commands.commands import CommandResult

            captured["arguments"] = list(arguments)
            captured["message"] = message
            return CommandResult.success(command.kind, message, [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        handlers.train_model(
            Command(
                CommandKind.TRAIN_MODEL,
                {"saved_model": "gold_range_1d", "dataset": "1D"},
            )
        )

        arguments = captured["arguments"]
        assert arguments[arguments.index("--model") + 1] == "range"
        assert arguments[arguments.index("--range-timeframes") + 1] == "1D"

    def test_changing_the_dataset_warns_rather_than_refuses(self, tmp_path, monkeypatch):
        """Allowed, but the operator is told what they changed."""
        pytest.importorskip("tensorflow")
        ModelCatalogue(tmp_path).write(record())
        seed_candles(tmp_path, "1H")
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path)
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            from ShadBotTrader.presentation.commands.commands import CommandResult

            captured["message"] = message
            return CommandResult.success(command.kind, message, [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        handlers.train_model(
            Command(
                CommandKind.TRAIN_MODEL,
                {"saved_model": "gold_range_1d", "dataset": "1H"},
            )
        )

        assert "NOTE" in captured["message"]
        assert "1D" in captured["message"] and "1H" in captured["message"]


# ------------------------------------------------- 4) training the choice --
class TestTrainingUsesTheChosenDataset:
    def test_the_chosen_dataset_reaches_the_script(self, tmp_path, monkeypatch):
        pytest.importorskip("tensorflow")
        seed_candles(tmp_path, "1D")
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            from ShadBotTrader.presentation.commands.commands import CommandResult

            captured["arguments"] = list(arguments)
            return CommandResult.success(command.kind, message, [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        handlers.train_dual_models(
            Command(CommandKind.TRAIN_DUAL_MODELS, {"model": "range", "dataset": "1D"})
        )

        arguments = captured["arguments"]
        assert arguments[arguments.index("--model") + 1] == "range"
        assert arguments[arguments.index("--range-timeframes") + 1] == "1D"

    def test_a_signal_model_uses_the_signal_flag(self, tmp_path, monkeypatch):
        pytest.importorskip("tensorflow")
        seed_candles(tmp_path, "5M")
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            from ShadBotTrader.presentation.commands.commands import CommandResult

            captured["arguments"] = list(arguments)
            return CommandResult.success(command.kind, message, [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        handlers.train_dual_models(
            Command(CommandKind.TRAIN_DUAL_MODELS, {"model": "signal", "dataset": "5M"})
        )

        arguments = captured["arguments"]
        assert arguments[arguments.index("--signal-timeframe") + 1] == "5M"

    def test_a_dataset_that_does_not_exist_is_refused(self, tmp_path):
        pytest.importorskip("tensorflow")
        seed_candles(tmp_path, "1H")
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.train_dual_models(
            Command(CommandKind.TRAIN_DUAL_MODELS, {"model": "range", "dataset": "4H"})
        )

        assert result.status is CommandStatus.REJECTED
        assert "1H" in result.message

    def test_an_unknown_model_type_is_refused(self, tmp_path):
        pytest.importorskip("tensorflow")
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.train_dual_models(
            Command(CommandKind.TRAIN_DUAL_MODELS, {"model": "guess", "dataset": "1H"})
        )

        assert result.status is CommandStatus.REJECTED
        assert "range" in result.message


# ------------------------------------------- 5) the workspace ships clean --
class TestTheWorkspaceCarriesNoMarketData:
    """The user's rule: keep real history out of the delivered archive.

    Their MT5 history lives in their own repository. Shipping a copy
    inside the zip is how two people end up training on two different
    "XAUUSD" and neither can reproduce the other's numbers.
    """

    TEST_SYMBOL = "TESTSYM"

    def test_the_generator_never_uses_a_real_symbol(self):
        """Phase 35's rule, applied to the test-data generator itself."""
        from pathlib import Path

        script = Path(__file__).resolve().parents[2] / "scripts" / "make_test_data.py"
        source = script.read_text(encoding="utf-8")

        assert script.exists()
        assert f'TEST_SYMBOL = "{self.TEST_SYMBOL}"' in source

        # Prose may mention XAUUSD to explain the rule; executable code
        # must never name it. Strip docstrings and comments, then check.
        import ast

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.strip().startswith(("Generate", "A continuous", "The workspace")):
                    continue  # module/function docstrings
                assert "XAUUSD" not in node.value, node.value[:60]

    def test_the_test_symbol_is_not_an_alias_of_a_real_one(self):
        from ShadBotTrader.domain.account.profile import AccountProfile, SymbolMap
        from ShadBotTrader.infrastructure.data.symbol_scope import alias_candidates

        profile = AccountProfile(
            name="alpari",
            login=1,
            server="S",
            symbol_map=SymbolMap(aliases={"XAUUSD": "XAUUSD_i"}),
        )

        assert self.TEST_SYMBOL not in alias_candidates("XAUUSD", profile)

    def test_the_generator_produces_a_usable_series(self, tmp_path):
        import importlib.util
        from pathlib import Path

        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.infrastructure.data.parquet_candle_store import (
            ParquetCandleStore,
        )

        script = Path(__file__).resolve().parents[2] / "scripts" / "make_test_data.py"
        spec = importlib.util.spec_from_file_location("make_test_data", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        exit_code = module.main(
            ["--storage-root", str(tmp_path), "--candles", "60", "--timeframes", "1H"]
        )

        assert exit_code == 0
        stored = ParquetCandleStore(tmp_path).query(Symbol(self.TEST_SYMBOL), Timeframe("1H"))
        assert len(stored) == 60
        # Well-formed candles, not noise: the OHLC invariants must hold.
        for candle in stored[:10]:
            assert candle.high.amount >= candle.low.amount
            assert candle.high.amount >= candle.close.amount
            assert candle.low.amount <= candle.close.amount

    def test_an_unknown_timeframe_is_refused(self, tmp_path):
        import importlib.util
        from pathlib import Path

        script = Path(__file__).resolve().parents[2] / "scripts" / "make_test_data.py"
        spec = importlib.util.spec_from_file_location("make_test_data_2", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.main(["--storage-root", str(tmp_path), "--timeframes", "3Y"]) == 1
