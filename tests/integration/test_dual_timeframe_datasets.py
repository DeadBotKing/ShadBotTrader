"""Phase 35 — two real datasets, one per timeframe.

Regression suite for four defects the operator found by asking a simple
question: "why doesn't Build training dataset care about the timeframe?"

1. ``Fetch market data`` fetched ONE timeframe, but the build needs two.
2. The build silently generated sample candles for whatever was missing,
   so the range model trained on a sine wave and looked trained.
3. Feature warm-up dropped rows from anywhere in the series, which could
   glue non-adjacent candles together.
4. Candles were stored under the broker's symbol (``XAUUSD_i``) while
   everything else read the canonical one (``XAUUSD``), producing two
   disconnected datasets for one instrument.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.dataset_update_service import DatasetUpdateService
from ShadBotTrader.application.services.training_data_service import TrainingDataService
from ShadBotTrader.domain.account.profile import AccountProfile, SymbolMap
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.domain.dataset.training_dataset import DatasetSpec
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore
from ShadBotTrader.infrastructure.data.symbol_scope import (
    alias_candidates,
    resolve_stored_symbol,
    stored_symbols,
)
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set
from ShadBotTrader.presentation.commands.commands import Command, CommandKind, CommandStatus
from ShadBotTrader.presentation.commands.handlers import (
    TRAINING_TIMEFRAMES,
    AccountCommandHandlers,
    descriptor_for,
    parse_timeframes,
)

BASE = datetime(2024, 1, 2, tzinfo=timezone.utc)


def make_candles(count: int, symbol: str = "XAUUSD", timeframe: str = "5M", minutes: int = 5):
    """A gently oscillating but perfectly continuous series."""
    out = []
    price = 2000.0
    for index in range(count):
        move = math.sin(index / 40.0) * 4.0 + ((index % 7) - 3) * 0.3
        open_, close = price, price + move
        out.append(
            Candle(
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(BASE + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(f"{open_:.2f}")),
                high=Price(Decimal(f"{max(open_, close) + 1.0:.2f}")),
                low=Price(Decimal(f"{min(open_, close) - 1.0:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal("100"),
            )
        )
        price = close
    return out


class FakeProvider:
    """Returns broker-named records for whatever timeframe is asked."""

    provider_name = "fake-mt5"

    def __init__(self, per_timeframe: dict[str, int]):
        self._per_timeframe = per_timeframe
        self.requests: list[tuple[str, str]] = []

    def fetch_candles(self, symbol, timeframe, source):
        self.requests.append((symbol, timeframe))
        minutes = 60 if timeframe.upper() == "1H" else 5
        count = self._per_timeframe.get(timeframe.upper(), 0)
        return [
            RawCandleRecord(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=candle.open_time.value.isoformat(),
                open=str(candle.open.amount),
                high=str(candle.high.amount),
                low=str(candle.low.amount),
                close=str(candle.close.amount),
                volume=str(candle.volume),
                extra={},
            )
            for candle in make_candles(count, symbol, timeframe, minutes)
        ]

    def shutdown(self):
        pass


# ------------------------------------------------- 1) both timeframes ---
class TestBothTimeframesAreFetched:
    def test_the_field_accepts_a_list(self):
        assert parse_timeframes("5M,1H") == ["5M", "1H"]
        assert parse_timeframes(" 5m ; 1h ") == ["5M", "1H"]
        assert parse_timeframes("5M,5M,1H") == ["5M", "1H"]
        assert parse_timeframes("") == []

    def test_the_button_defaults_to_both_training_timeframes(self):
        """The old default was '5M' alone, which left 1H empty."""
        descriptor = descriptor_for(CommandKind.FETCH_MARKET_DATA)
        field = next(f for f in descriptor.fields if f.name == "timeframe")

        assert parse_timeframes(field.default) == list(TRAINING_TIMEFRAMES)

    def test_each_timeframe_lands_in_its_own_store(self, tmp_path):
        store = ParquetCandleStore(tmp_path)
        provider = FakeProvider({"5M": 60, "1H": 40})
        updater = DatasetUpdateService(store, provider=provider)

        for timeframe in ("5M", "1H"):
            updater.fetch_and_update("XAUUSD", timeframe, bars=100)

        assert len(store.query(Symbol("XAUUSD"), Timeframe("5M"))) == 60
        assert len(store.query(Symbol("XAUUSD"), Timeframe("1H"))) == 40


# ------------------------------------------------- 2) no sample data ----
class TestSampleDataIsNeverSubstituted:
    def test_the_build_refuses_when_a_timeframe_is_missing(self, tmp_path):
        """The 1H model must not be trained on invented candles."""
        store = ParquetCandleStore(tmp_path)
        DatasetUpdateService(store, provider=FakeProvider({"5M": 60})).fetch_and_update(
            "XAUUSD", "5M", bars=100
        )

        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)
        missing = handlers.missing_timeframes("XAUUSD")

        assert missing == ["1H"]

        result = handlers.build_dataset(Command(CommandKind.BUILD_DATASET, {"symbol": "XAUUSD"}))

        assert result.status is CommandStatus.REJECTED
        assert "1H" in result.message
        assert "Fetch market data" in result.message

    def test_the_build_is_allowed_once_both_exist(self, tmp_path):
        store = ParquetCandleStore(tmp_path)
        provider = FakeProvider({"5M": 60, "1H": 40})
        updater = DatasetUpdateService(store, provider=provider)
        for timeframe in ("5M", "1H"):
            updater.fetch_and_update("XAUUSD", timeframe, bars=100)

        handlers = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path)

        assert handlers.missing_timeframes("XAUUSD") == []

    def test_the_fetch_button_refuses_without_mt5(self, tmp_path, monkeypatch):
        """No MT5 used to mean 'generate a sine wave under the real symbol'."""
        from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        monkeypatch.setattr(mt5mod, "is_available", lambda: False)
        handlers = CommandHandlers(tmp_path / "db.sqlite", tmp_path)

        result = handlers.fetch_market_data(
            Command(CommandKind.FETCH_MARKET_DATA, {"symbol": "XAUUSD", "timeframe": "5M,1H"})
        )

        assert result.status is CommandStatus.REJECTED
        assert "MetaTrader 5" in result.message
        # and nothing was written
        assert stored_symbols(tmp_path) == []


# ------------------------------------------- 3) contiguity of the rows --
class TestRowsAreOnlyCutFromTheEnds:
    def test_the_kept_rows_are_consecutive_candles(self):
        matrix = build_feature_matrix(
            make_candles(400),
            Symbol("XAUUSD"),
            Timeframe("5M"),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )

        assert matrix.is_contiguous
        assert matrix.source_index == list(
            range(matrix.source_index[0], matrix.source_index[-1] + 1)
        )

    def test_warm_up_only_removes_the_front(self):
        candles = make_candles(400)
        matrix = build_feature_matrix(
            candles,
            Symbol("XAUUSD"),
            Timeframe("5M"),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )

        # first kept row is the warm-up boundary, nothing before survives
        assert matrix.source_index[0] == matrix.dropped_warmup
        # rows lost = front cut + tail cut, and nothing else
        assert len(matrix) == len(candles) - matrix.dropped_warmup - matrix.dropped_tail

    def test_a_feature_with_an_interior_hole_loses_its_column_not_rows(self):
        """A hole in the middle must never cost a row."""

        class HoledFeature:
            """Produces None for one bar in the middle of the series."""

            def compute(self, definition, context):
                from ShadBotTrader.domain.feature.feature_result import (
                    FeaturePoint,
                    FeatureResult,
                )

                points = [
                    FeaturePoint(
                        timestamp=candle.open_time,
                        value=None if index == 50 else 1.0,
                    )
                    for index, candle in enumerate(context.candles)
                ]
                return FeatureResult(
                    feature_id=definition.feature_id.value,
                    points=points,
                    warmup=0,
                )

        class OneFeatureSet:
            def __init__(self, definition):
                self.definitions = [definition]

        class OneResolver:
            def resolve(self, family):
                return HoledFeature()

        definition = standard_feature_set().definitions[0]
        matrix = build_feature_matrix(
            make_candles(100),
            Symbol("XAUUSD"),
            Timeframe("5M"),
            feature_set=OneFeatureSet(definition),
            resolver=OneResolver(),
            include_features=True,
        )

        assert definition.feature_id.value in matrix.holed_features
        assert matrix.is_contiguous
        assert len(matrix) == 100  # no row was sacrificed

    def test_the_slice_records_contiguity(self, tmp_path):
        service = TrainingDataService(
            tmp_path,
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        record, *_ = service.build_slice(make_candles(400), "XAUUSD", "5M", 400)

        assert record.contiguous is True
        assert record.warmup_dropped > 0
        assert record.to_dict()["contiguous"] is True


# ------------------------------------------------ 4) one symbol, one set --
class TestBrokerAliasesShareOneDataset:
    def test_candles_are_stored_canonically_not_under_the_broker_name(self, tmp_path):
        """The bug: fetching XAUUSD_i created a second, invisible dataset."""
        store = ParquetCandleStore(tmp_path)
        provider = FakeProvider({"5M": 60})
        updater = DatasetUpdateService(store, provider=provider)

        updater.fetch_and_update("XAUUSD_i", "5M", bars=100, store_as="XAUUSD")

        assert provider.requests == [("XAUUSD_i", "5M")]  # asked the broker its way
        assert stored_symbols(tmp_path) == ["XAUUSD"]  # stored our way
        assert len(store.query(Symbol("XAUUSD"), Timeframe("5M"))) == 60

    def test_a_second_fetch_appends_to_the_same_dataset(self, tmp_path):
        store = ParquetCandleStore(tmp_path)
        updater = DatasetUpdateService(store, provider=FakeProvider({"5M": 60}))

        updater.fetch_and_update("XAUUSD_i", "5M", bars=100, store_as="XAUUSD")
        second = updater.fetch_and_update("XAUUSD_i", "5M", bars=100, store_as="XAUUSD")

        assert second.final_count == 60  # same bars re-sent: updated, not duplicated
        assert stored_symbols(tmp_path) == ["XAUUSD"]

    def test_history_written_under_the_old_alias_is_still_found(self, tmp_path):
        """Pre-Phase-35 data must not become unreachable."""
        store = ParquetCandleStore(tmp_path)
        DatasetUpdateService(store, provider=FakeProvider({"5M": 60})).fetch_and_update(
            "XAUUSD_i", "5M", bars=100
        )
        profile = AccountProfile(
            name="alpari",
            login=53102853,
            server="Alpari-MT5-Demo",
            symbol_map=SymbolMap(aliases={"XAUUSD": "XAUUSD_i"}),
        )

        resolved = resolve_stored_symbol(store, "XAUUSD", "5M", profile)

        assert resolved.found
        assert resolved.resolved == "XAUUSD_i"
        assert resolved.is_alias
        assert "XAUUSD_i" in resolved.note

    def test_the_canonical_name_wins_when_both_exist(self, tmp_path):
        store = ParquetCandleStore(tmp_path)
        updater = DatasetUpdateService(store, provider=FakeProvider({"5M": 60}))
        updater.fetch_and_update("XAUUSD_i", "5M", bars=100)  # legacy
        updater.fetch_and_update("XAUUSD", "5M", bars=100)  # canonical

        profile = AccountProfile(
            name="alpari",
            login=1,
            server="S",
            symbol_map=SymbolMap(aliases={"XAUUSD": "XAUUSD_i"}),
        )

        assert resolve_stored_symbol(store, "XAUUSD", "5M", profile).resolved == "XAUUSD"

    def test_candidates_are_ordered_canonical_first(self):
        profile = AccountProfile(
            name="alpari",
            login=1,
            server="S",
            symbol_map=SymbolMap(aliases={"XAUUSD": "XAUUSD_i"}),
        )

        assert alias_candidates("XAUUSD", profile) == ["XAUUSD", "XAUUSD_i"]

    def test_nothing_stored_reports_every_name_it_looked_under(self, tmp_path):
        store = ParquetCandleStore(tmp_path)

        resolved = resolve_stored_symbol(store, "XAUUSD", "1H")

        assert not resolved.found
        assert "XAUUSD" in resolved.note


# --------------------------------------------------------- the manifest --
class TestTheManifestDescribesTwoDatasets:
    def test_one_slice_per_timeframe_with_its_own_matrix(self, tmp_path):
        service = TrainingDataService(
            tmp_path,
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        spec = DatasetSpec(
            symbol="XAUUSD", timeframes=("5M", "1H"), target_candles=400, window_rows=50
        )

        manifest = service.build(
            spec,
            {
                "5M": make_candles(400, timeframe="5M", minutes=5),
                "1H": make_candles(400, timeframe="1H", minutes=60),
            },
        )

        assert set(manifest.slices) == {"5M", "1H"}
        assert service.matrix_path("XAUUSD", "5M").exists()
        assert service.matrix_path("XAUUSD", "1H").exists()
        assert service.matrix_path("XAUUSD", "5M") != service.matrix_path("XAUUSD", "1H")

    def test_the_two_slices_are_independent(self, tmp_path):
        """Different candles must produce different digests."""
        service = TrainingDataService(
            tmp_path,
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        spec = DatasetSpec(
            symbol="XAUUSD", timeframes=("5M", "1H"), target_candles=400, window_rows=50
        )
        manifest = service.build(
            spec,
            {
                "5M": make_candles(400, timeframe="5M", minutes=5),
                "1H": make_candles(380, timeframe="1H", minutes=60),
            },
        )

        assert manifest.slices["5M"].candles == 400
        assert manifest.slices["1H"].candles == 380
        assert manifest.slices["5M"].digest != manifest.slices["1H"].digest

    @pytest.mark.parametrize("timeframe", ["5M", "1H"])
    def test_each_slice_reports_it_is_contiguous(self, tmp_path, timeframe):
        service = TrainingDataService(
            tmp_path,
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        record, *_ = service.build_slice(
            make_candles(400, timeframe=timeframe, minutes=5 if timeframe == "5M" else 60),
            "XAUUSD",
            timeframe,
            400,
        )

        assert record.contiguous


# ------------------------------------------ demo runs vs. real symbols --
class TestDemoScriptsCannotPolluteARealSymbol:
    """The demo scripts still generate candles — under their own symbol.

    Before Phase 35 they wrote sample data under ``XAUUSD_i``, which is
    exactly the broker alias the resolver falls back to. One demo run
    could therefore hand invented candles to a real training build.
    """

    DEMO_SYMBOL = "DEMOXAU"

    def test_a_script_that_generates_candles_never_uses_a_gold_symbol(self):
        """Only scripts calling generate_sample are constrained.

        The real-data scripts (run_training_dataset, run_dual_models,
        run_weekly_update, run_live_loop) legitimately default to
        XAUUSD — they read the store, they never write into it.
        """
        import re
        from pathlib import Path

        scripts = Path(__file__).resolve().parents[2] / "scripts"
        offenders = []
        for path in sorted(scripts.glob("run_*.py")):
            text = path.read_text(encoding="utf-8")
            if "generate_sample(" not in text:
                continue
            for match in re.finditer(r"[\"'](XAUUSD[A-Za-z0-9_.]*)[\"']", text):
                line = text[: match.start()].rsplit("\n", 1)[-1]
                if "SYMBOL" in line or "default=" in line:
                    offenders.append(f"{path.name}: {match.group(1)}")

        assert offenders == [], (
            f"These scripts generate candles and would store them under a "
            f"real gold symbol: {offenders}. Use {self.DEMO_SYMBOL} instead."
        )

    def test_the_generating_scripts_are_still_covered(self):
        """Guards the guard: if generate_sample vanishes, say so."""
        from pathlib import Path

        scripts = Path(__file__).resolve().parents[2] / "scripts"
        generating = {
            path.name
            for path in scripts.glob("run_*.py")
            if "generate_sample(" in path.read_text(encoding="utf-8")
        }

        assert generating, "no script generates samples any more — retire this test"
        assert "run_backtest.py" in generating

    def test_the_demo_symbol_is_not_an_alias_of_the_canonical_one(self):
        profile = AccountProfile(
            name="alpari",
            login=1,
            server="S",
            symbol_map=SymbolMap(aliases={"XAUUSD": "XAUUSD_i"}),
        )

        assert self.DEMO_SYMBOL not in alias_candidates("XAUUSD", profile)
