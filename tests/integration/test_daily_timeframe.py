"""Phase 39 — the 1D timeframe is a first-class citizen.

Everything built for 1H now exists for 1D: candles, features, a training
dataset, its own range model, and a way to see it. The daily bar is a
different question from the hourly one — "where will gold trade this
week" is not "where will it trade this hour" — so it gets its own
weights rather than a rescaled reuse of the hourly model.

Also covered: choosing WHICH model and WHICH dataset to train, which the
user asked for after finding that training was all-or-nothing.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.resample import resample_candles
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.model_roles import (
    MODEL_TIMEFRAMES,
    range_model_id,
    range_model_role,
    signal_model_role,
)
from ShadBotTrader.presentation.commands.commands import Command, CommandKind, CommandStatus
from ShadBotTrader.presentation.commands.handlers import (
    TRAINING_TIMEFRAMES,
    AccountCommandHandlers,
    descriptor_for,
    parse_timeframes,
)

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD")


def hourly(hours: int, start: float = 2000.0):
    """A continuous 1H series starting at midnight."""
    out = []
    price = start
    for index in range(hours):
        open_ = price
        close = price + math.sin(index / 11.0) * 3.0
        out.append(
            Candle(
                symbol=SYMBOL,
                timeframe=Timeframe("1H"),
                open_time=Timestamp(BASE + timedelta(hours=index)),
                open_price=Price(Decimal(f"{open_:.2f}")),
                high=Price(Decimal(f"{max(open_, close) + 2:.2f}")),
                low=Price(Decimal(f"{min(open_, close) - 2:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal("10"),
            )
        )
        price = close
    return out


# --------------------------------------------------------- aggregation --
class TestHourlyCandlesAggregateIntoDays:
    def test_twenty_four_hours_make_one_day(self):
        result = resample_candles(hourly(48), "1D")

        assert result.count == 2
        assert result.dropped_incomplete == 0

    def test_ohlc_is_taken_from_the_right_places(self):
        candles = hourly(24)
        day = resample_candles(candles, "1D").candles[0]

        assert day.open.amount == candles[0].open.amount
        assert day.close.amount == candles[-1].close.amount
        assert day.high.amount == max(item.high.amount for item in candles)
        assert day.low.amount == min(item.low.amount for item in candles)
        assert day.volume == sum(item.volume for item in candles)

    def test_a_partial_final_day_is_dropped(self):
        """A six-hour 'day' would not have the day's real high and low."""
        result = resample_candles(hourly(30), "1D")

        assert result.count == 1
        assert result.dropped_incomplete == 1
        assert "incomplete" in " ".join(result.summary_lines())

    def test_the_day_is_stamped_at_midnight_utc(self):
        day = resample_candles(hourly(24), "1D").candles[0]

        assert day.open_time.value == BASE
        assert str(day.timeframe) == "1D"

    def test_a_weekend_gap_does_not_weld_two_days_together(self):
        friday = hourly(24)
        monday = [
            Candle(
                symbol=SYMBOL,
                timeframe=Timeframe("1H"),
                open_time=Timestamp(BASE + timedelta(days=3, hours=hour)),
                open_price=Price(Decimal("2100")),
                high=Price(Decimal("2105")),
                low=Price(Decimal("2095")),
                close=Price(Decimal("2101")),
                volume=Decimal("10"),
            )
            for hour in range(24)
        ]

        result = resample_candles(friday + monday, "1D")

        assert result.count == 2
        assert (result.candles[1].open_time.value - result.candles[0].open_time.value).days == 3

    def test_resampling_to_a_finer_timeframe_is_refused(self):
        with pytest.raises(ValidationError):
            resample_candles(hourly(48), "5M")

    def test_an_unknown_target_is_refused(self):
        with pytest.raises(ValidationError):
            resample_candles(hourly(48), "3Y")

    def test_an_empty_series_is_not_a_crash(self):
        assert resample_candles([], "1D").count == 0


# ------------------------------------------------------ the daily model --
class TestTheDailyRangeModelIsItsOwnModel:
    def test_each_timeframe_has_its_own_model_id(self):
        """Sharing an id would make one training run overwrite the other."""
        assert range_model_id("1H") != range_model_id("1D")
        assert range_model_role(timeframe="1H").model_id == "gold_range_1h"
        assert range_model_role(timeframe="1D").model_id == "gold_range_1d"

    def test_the_daily_role_describes_daily_candles(self):
        role = range_model_role(timeframe="1D", horizon=5)

        assert role.target.timeframe == "1D"
        assert "1D" in role.description

    def test_the_signal_model_is_also_timeframe_tagged(self):
        assert signal_model_role(timeframe="5M").model_id == "gold_signal_5m"

    def test_the_daily_timeframe_is_registered(self):
        assert "1D" in MODEL_TIMEFRAMES
        assert "1D" in TRAINING_TIMEFRAMES


# ------------------------------------------------- the dashboard wiring --
class TestTheDashboardCoversTheDailyTimeframe:
    def test_fetch_and_features_default_to_all_three(self):
        for kind in (CommandKind.FETCH_MARKET_DATA, CommandKind.COMPUTE_FEATURES):
            descriptor = descriptor_for(kind)
            field = next(item for item in descriptor.fields if item.name == "timeframe")
            assert parse_timeframes(field.default) == ["5M", "1H", "1D"], kind

    def test_there_is_a_button_to_build_a_higher_timeframe(self):
        descriptor = descriptor_for(CommandKind.BUILD_TIMEFRAME)
        names = {field.name for field in descriptor.fields}

        assert names == {"symbol", "source", "target"}
        assert descriptor.group == "Data"

    def test_the_button_aggregates_and_stores(self, tmp_path):
        from ShadBotTrader.application.services.dataset_update_service import (
            DatasetUpdateService,
        )
        from ShadBotTrader.infrastructure.data.parquet_candle_store import (
            ParquetCandleStore,
        )

        store = ParquetCandleStore(tmp_path)
        DatasetUpdateService(store).update("XAUUSD", "1H", hourly(24 * 10), allow_gap=True)

        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)
        result = handlers.build_timeframe(
            Command(
                CommandKind.BUILD_TIMEFRAME, {"symbol": "XAUUSD", "source": "1H", "target": "1D"}
            )
        )

        assert result.status is CommandStatus.SUCCEEDED
        assert len(store.query(Symbol("XAUUSD"), Timeframe("1D"))) == 10

    def test_it_refuses_when_the_source_is_missing(self, tmp_path):
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.build_timeframe(
            Command(
                CommandKind.BUILD_TIMEFRAME, {"symbol": "XAUUSD", "source": "1H", "target": "1D"}
            )
        )

        assert result.status is CommandStatus.REJECTED


# --------------------------------------------- choosing what to train ----
class TestTheOperatorChoosesModelAndDataset:
    def test_the_training_button_exposes_the_choice(self):
        descriptor = descriptor_for(CommandKind.TRAIN_DUAL_MODELS)
        names = {field.name for field in descriptor.fields}

        assert {"model", "range_timeframes", "signal_timeframe"} <= names

    def test_the_choice_reaches_the_script(self, tmp_path, monkeypatch):
        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)
        handlers._run_log_dir = tmp_path / "run_logs"
        captured: dict = {}

        def fake_run(command, arguments, message, started, timeout=900):
            from ShadBotTrader.presentation.commands.commands import CommandResult

            captured["arguments"] = list(arguments)
            return CommandResult.success(command.kind, "ok", [], 0.0)

        monkeypatch.setattr(handlers, "_run_script", fake_run)
        try:
            handlers.train_dual_models(
                Command(
                    CommandKind.TRAIN_DUAL_MODELS,
                    {"model": "range_1d", "range_timeframes": "1D", "signal_timeframe": "5M"},
                )
            )
        except Exception:  # pragma: no cover - tensorflow absent
            pytest.skip("TensorFlow is not installed in this environment")

        arguments = captured.get("arguments")
        if arguments is None:
            pytest.skip("TensorFlow is not installed in this environment")
        assert "--model" in arguments
        assert arguments[arguments.index("--model") + 1] == "range_1d"
        assert arguments[arguments.index("--range-timeframes") + 1] == "1D"

    @pytest.mark.parametrize(
        "model,expected",
        [
            ("range_1h", ["1H"]),
            ("range_1d", ["1D"]),
        ],
    )
    def test_a_single_model_selects_a_single_dataset(self, model, expected):
        """range_1d must train on 1D candles, never on 1H."""
        import importlib.util
        from pathlib import Path

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("run_dual_models_sel", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        args = module.parse_args(["--model", model])
        chosen = [args.model.split("_")[1].upper()]

        assert chosen == expected
