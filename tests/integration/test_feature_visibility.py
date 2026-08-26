"""Phase 37 — feature progress, and one feature store per series.

Two questions from the operator:

    "when I run Update features, show me which feature is being computed
     right now, how many are done, how many are left"

    "and check that features are computed and stored SEPARATELY for 5M
     and 1H"

The second question exposed a real defect. The store wrote to
``features/{feature_id}/v{version}.parquet`` — no symbol, no timeframe.
Computing atr_14 for 5M produced v1; computing atr_14 for 1H produced v2
in the SAME directory. Two different quantities, indistinguishable, with
a shared version counter.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.feature_cli import _build_service
from ShadBotTrader.infrastructure.feature.feature_progress import (
    ConsoleFeatureProgress,
    NullFeatureProgress,
)
from ShadBotTrader.infrastructure.feature.parquet_feature_store import ParquetFeatureStore
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1
from ShadBotTrader.presentation.commands.commands import Command, CommandKind, CommandStatus
from ShadBotTrader.presentation.commands.handlers import CommandHandlers, descriptor_for

BASE = datetime(2024, 1, 2, tzinfo=timezone.utc)


def make_candles(count: int, timeframe: str, minutes: int, amplitude: float, start: float):
    """A clean series whose shape depends on the timeframe."""
    out = []
    price = start
    for index in range(count):
        open_ = price
        close = price + math.sin(index / 30.0) * amplitude
        out.append(
            Candle(
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(BASE + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(f"{open_:.2f}")),
                high=Price(Decimal(f"{max(open_, close) + 1:.2f}")),
                low=Price(Decimal(f"{min(open_, close) - 1:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal("100"),
            )
        )
        price = close
    return out


def one_point_result(feature_id: str = "atr_14") -> FeatureResult:
    return FeatureResult(
        feature_id=feature_id,
        points=[FeaturePoint(timestamp=Timestamp(BASE), value=1.0)],
        warmup=0,
    )


# ------------------------------------- 1) one store per symbol/timeframe --
class TestFeaturesAreStoredPerSeries:
    def test_the_path_records_the_symbol_and_the_timeframe(self, tmp_path):
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "5M")

        store.save("atr_14", 1, one_point_result())

        expected = tmp_path / "features" / "XAUUSD" / "5M" / "atr_14" / "v1.parquet"
        assert expected.exists()

    def test_two_timeframes_do_not_share_a_version_counter(self, tmp_path):
        """The bug: 5M wrote v1 and 1H wrote v2 into one directory."""
        base = ParquetFeatureStore(tmp_path)
        five = base.for_series("XAUUSD", "5M")
        hour = base.for_series("XAUUSD", "1H")

        five.save("atr_14", five.next_version("atr_14"), one_point_result())
        hour.save("atr_14", hour.next_version("atr_14"), one_point_result())

        assert (tmp_path / "features/XAUUSD/5M/atr_14/v1.parquet").exists()
        assert (tmp_path / "features/XAUUSD/1H/atr_14/v1.parquet").exists()
        assert not (tmp_path / "features/XAUUSD/5M/atr_14/v2.parquet").exists()

    def test_two_symbols_are_independent_too(self, tmp_path):
        base = ParquetFeatureStore(tmp_path)
        gold = base.for_series("XAUUSD", "5M")
        euro = base.for_series("EURUSD", "5M")

        gold.save("atr_14", gold.next_version("atr_14"), one_point_result())
        euro.save("atr_14", euro.next_version("atr_14"), one_point_result())

        assert (tmp_path / "features/XAUUSD/5M/atr_14/v1.parquet").exists()
        assert (tmp_path / "features/EURUSD/5M/atr_14/v1.parquet").exists()

    def test_a_scoped_store_only_sees_its_own_series(self, tmp_path):
        base = ParquetFeatureStore(tmp_path)
        five = base.for_series("XAUUSD", "5M")
        hour = base.for_series("XAUUSD", "1H")
        five.save("atr_14", 1, one_point_result())

        assert five.exists("atr_14", 1)
        assert not hour.exists("atr_14", 1)
        assert hour.load("atr_14", 1) is None
        assert five.load("atr_14", 1) is not None

    def test_for_series_does_not_mutate_the_original(self, tmp_path):
        """A service holding a store must not have its scope changed."""
        base = ParquetFeatureStore(tmp_path)
        scoped = base.for_series("XAUUSD", "5M")

        assert base.scope is None
        assert scoped.scope == ("XAUUSD", "5M")
        assert scoped is not base

    def test_immutability_still_holds_within_a_series(self, tmp_path):
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "5M")
        store.save("atr_14", 1, one_point_result())

        with pytest.raises(FileExistsError):
            store.save("atr_14", 1, one_point_result())

    def test_a_symbol_cannot_escape_the_features_directory(self, tmp_path):
        store = ParquetFeatureStore(tmp_path).for_series("../../etc", "5M")

        store.save("atr_14", 1, one_point_result())

        written = list((tmp_path / "features").rglob("*.parquet"))
        assert written, "nothing was written at all"
        for path in written:
            assert (tmp_path / "features") in path.parents


# --------------------------------------- 2) the service scopes the store --
class TestTheServiceStoresEachSeriesSeparately:
    def test_computing_both_timeframes_writes_two_trees(self, tmp_path):
        feature_set = standard_feature_set_v1()

        for timeframe, minutes, amplitude, start in (
            ("5M", 5, 4.0, 2000.0),
            ("1H", 60, 25.0, 3000.0),
        ):
            service, _, _ = _build_service(tmp_path)
            service.compute_set(
                feature_set=feature_set,
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe(timeframe),
                candles=make_candles(200, timeframe, minutes, amplitude, start),
                source_dataset_id=f"csv.market_candle.XAUUSD.{timeframe}.L3_normalized",
                dataset_version=1,
            )

        assert (tmp_path / "features/XAUUSD/5M/atr_14/v1.parquet").exists()
        assert (tmp_path / "features/XAUUSD/1H/atr_14/v1.parquet").exists()

    def test_the_two_series_hold_genuinely_different_numbers(self, tmp_path):
        """Same feature, different timeframe, must not be the same values."""
        feature_set = standard_feature_set_v1()

        for timeframe, minutes, amplitude, start in (
            ("5M", 5, 4.0, 2000.0),
            ("1H", 60, 25.0, 3000.0),
        ):
            service, _, _ = _build_service(tmp_path)
            service.compute_set(
                feature_set=feature_set,
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe(timeframe),
                candles=make_candles(200, timeframe, minutes, amplitude, start),
                source_dataset_id=f"csv.market_candle.XAUUSD.{timeframe}.L3_normalized",
                dataset_version=1,
            )

        base = ParquetFeatureStore(tmp_path)
        five = base.for_series("XAUUSD", "5M").load("atr_14", 1)
        hour = base.for_series("XAUUSD", "1H").load("atr_14", 1)

        assert five is not None and hour is not None
        five_values = [point.value for point in five.points if point.value is not None]
        hour_values = [point.value for point in hour.points if point.value is not None]
        assert five_values and hour_values
        assert five_values[0] != hour_values[0]

    def test_recomputing_the_same_series_bumps_only_its_own_version(self, tmp_path):
        """A genuine recompute writes v2 — and only under its own series.

        Phase 38 made unchanged candles reuse v1 instead of writing v2,
        so the second run here changes the candles to force a real
        recompute. What is being pinned is the *scoping*: the new version
        must land under 5M and must not create a 1H tree.
        """
        feature_set = standard_feature_set_v1()

        for count in (200, 240):
            service, _, _ = _build_service(tmp_path)
            service.compute_set(
                feature_set=feature_set,
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe("5M"),
                candles=make_candles(count, "5M", 5, 4.0, 2000.0),
                source_dataset_id="csv.market_candle.XAUUSD.5M.L3_normalized",
                dataset_version=1,
            )

        assert (tmp_path / "features/XAUUSD/5M/atr_14/v1.parquet").exists()
        assert (tmp_path / "features/XAUUSD/5M/atr_14/v2.parquet").exists()
        assert not (tmp_path / "features/XAUUSD/1H").exists()


# ---------------------------------------------------- 3) live progress ---
class TestFeatureProgressIsReported:
    def test_every_feature_is_announced_before_it_is_computed(self, tmp_path):
        import io

        stream = io.StringIO()
        service, _, _ = _build_service(tmp_path)
        service._progress = ConsoleFeatureProgress(stream=stream)

        service.compute_set(
            feature_set=standard_feature_set_v1(),
            symbol=Symbol("XAUUSD"),
            timeframe=Timeframe("5M"),
            candles=make_candles(200, "5M", 5, 4.0, 2000.0),
            source_dataset_id="csv.market_candle.XAUUSD.5M.L3_normalized",
            dataset_version=1,
        )

        output = stream.getvalue()
        assert "FEATURES" in output
        assert "XAUUSD 5M" in output
        assert "atr_14" in output
        assert "/227" in output  # "n/227" counter
        assert "%" in output  # progress bar
        assert "stored v1" in output
        assert "227/227 stored" in output

    def test_the_counter_reaches_the_total(self, tmp_path):
        import io

        stream = io.StringIO()
        service, _, _ = _build_service(tmp_path)
        service._progress = ConsoleFeatureProgress(stream=stream)
        service.compute_set(
            feature_set=standard_feature_set_v1(),
            symbol=Symbol("XAUUSD"),
            timeframe=Timeframe("5M"),
            candles=make_candles(200, "5M", 5, 4.0, 2000.0),
            source_dataset_id="csv.market_candle.XAUUSD.5M.L3_normalized",
            dataset_version=1,
        )

        assert "227/227 |" in stream.getvalue()

    def test_the_default_service_stays_silent(self, tmp_path, capsys):
        service, _, _ = _build_service(tmp_path)
        assert isinstance(service._progress, NullFeatureProgress)

        service.compute_set(
            feature_set=standard_feature_set_v1(),
            symbol=Symbol("XAUUSD"),
            timeframe=Timeframe("5M"),
            candles=make_candles(200, "5M", 5, 4.0, 2000.0),
            source_dataset_id="csv.market_candle.XAUUSD.5M.L3_normalized",
            dataset_version=1,
        )

        assert capsys.readouterr().out == ""

    def test_the_reporter_never_changes_the_result(self, tmp_path):
        """An observer that alters what it observes is a bug, not a feature."""
        import io

        quiet_root = tmp_path / "quiet"
        loud_root = tmp_path / "loud"
        results = []
        for root, reporter in (
            (quiet_root, None),
            (loud_root, ConsoleFeatureProgress(io.StringIO())),
        ):
            service, _, _ = _build_service(root)
            if reporter is not None:
                service._progress = reporter
            outcome = service.compute_set(
                feature_set=standard_feature_set_v1(),
                symbol=Symbol("XAUUSD"),
                timeframe=Timeframe("5M"),
                candles=make_candles(200, "5M", 5, 4.0, 2000.0),
                source_dataset_id="csv.market_candle.XAUUSD.5M.L3_normalized",
                dataset_version=1,
            )
            results.append(
                [(item.feature_id, item.version, item.available_count) for item in outcome.outcomes]
            )

        assert results[0] == results[1]


# ------------------------------------------------ 4) the dashboard button --
class TestTheUpdateFeaturesButton:
    def test_it_defaults_to_every_training_timeframe(self):
        """Phase 39 added 1D, so the default covers all three."""
        from ShadBotTrader.presentation.commands.handlers import (
            TRAINING_TIMEFRAMES,
            parse_timeframes,
        )

        descriptor = descriptor_for(CommandKind.COMPUTE_FEATURES)
        field = next(item for item in descriptor.fields if item.name == "timeframe")

        assert parse_timeframes(field.default) == list(TRAINING_TIMEFRAMES)

    def test_missing_candles_are_reported_not_crashed(self, tmp_path):
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path / "datasets")
        handlers._run_log_dir = tmp_path / "run_logs"

        result = handlers.compute_features(
            Command(CommandKind.COMPUTE_FEATURES, {"symbol": "XAUUSD", "timeframe": "5M,1H"})
        )

        assert result.status is CommandStatus.FAILED
        assert "5M" in result.detail and "1H" in result.detail

    def test_it_writes_a_live_log(self, tmp_path):
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path / "datasets")
        handlers._run_log_dir = tmp_path / "run_logs"

        handlers.compute_features(
            Command(CommandKind.COMPUTE_FEATURES, {"symbol": "XAUUSD", "timeframe": "5M"})
        )

        assert handlers.run_log_path("compute_features").exists()


# ------------------------------------------------- 5) the /data listing ---
class TestTheDataPageShowsTheSeries:
    def test_each_entry_names_its_symbol_and_timeframe(self, tmp_path):
        from ShadBotTrader.presentation.gateway.data_inspector import DataInspector

        base = ParquetFeatureStore(tmp_path)
        base.for_series("XAUUSD", "5M").save("atr_14", 1, one_point_result())
        base.for_series("XAUUSD", "1H").save("atr_14", 1, one_point_result())

        found = DataInspector(tmp_path).features()

        assert found["count"] == 2
        assert {item["series"] for item in found["features"]} == {"XAUUSD 5M", "XAUUSD 1H"}

    def test_pre_phase_37_data_is_labelled_rather_than_hidden(self, tmp_path):
        from ShadBotTrader.presentation.gateway.data_inspector import DataInspector

        legacy = tmp_path / "features" / "atr_14"
        legacy.mkdir(parents=True)
        ParquetFeatureStore(tmp_path).save("atr_14", 1, one_point_result())

        found = DataInspector(tmp_path).features()

        assert found["count"] == 1
        assert "legacy" in found["features"][0]["series"]
