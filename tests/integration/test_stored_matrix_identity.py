"""Phase 39 — a matrix read from the store is byte-identical to a computed one.

The user's condition for accepting this optimisation, verbatim:

    "reading from the store + a test proving the loaded matrix is
     byte-for-byte identical to the computed one"

That is the right bar. ``build_feature_matrix`` scales price-valued
features against the close of their own row, trims warm-up from the
front and forward-looking columns from the tail. If reading from the
store took a different path through any of that, the model would train
on subtly different numbers and nothing would fail loudly.

So the store only changes WHERE the feature columns come from. Every
transformation stays in one place, shared by both paths, and these tests
compare the packed IEEE-754 bytes of the two results.
"""

import math
import struct
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.feature_cli import _build_service
from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
from ShadBotTrader.infrastructure.ai.stored_feature_source import (
    StoredFeatureSource,
    stored_source_for,
)
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.parquet_feature_store import ParquetFeatureStore
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

BASE = datetime(2024, 1, 2, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD")


def make_candles(count: int, timeframe: str = "1H", minutes: int = 60, start: float = 2000.0):
    out = []
    price = start
    for index in range(count):
        open_ = price
        close = price + math.sin(index / 25.0) * 6.0 + ((index % 5) - 2) * 0.4
        out.append(
            Candle(
                symbol=SYMBOL,
                timeframe=Timeframe(timeframe),
                open_time=Timestamp(BASE + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(f"{open_:.2f}")),
                high=Price(Decimal(f"{max(open_, close) + 1.5:.2f}")),
                low=Price(Decimal(f"{min(open_, close) - 1.5:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal("125"),
            )
        )
        price = close
    return out


def matrix_bytes(matrix) -> bytes:
    """Every value packed exactly as IEEE-754 doubles."""
    buffer = bytearray()
    for row in matrix.rows:
        for value in row:
            buffer += struct.pack("<d", float(value))
    return bytes(buffer)


def seed_store(root, candles, timeframe="1H"):
    service, _, _ = _build_service(root)
    service.compute_set(
        feature_set=standard_feature_set(),
        symbol=SYMBOL,
        timeframe=Timeframe(timeframe),
        candles=candles,
        source_dataset_id=f"csv.market_candle.XAUUSD.{timeframe}.L3_normalized",
        dataset_version=1,
    )


# ------------------------------------------------ the identity contract --
class TestLoadedAndComputedMatricesAreIdentical:
    @pytest.mark.parametrize("timeframe,minutes", [("1H", 60), ("1D", 1440), ("5M", 5)])
    def test_the_bytes_match_exactly(self, tmp_path, timeframe, minutes):
        candles = make_candles(400, timeframe, minutes)
        seed_store(tmp_path, candles, timeframe)

        computed = build_feature_matrix(
            candles,
            SYMBOL,
            Timeframe(timeframe),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        source = stored_source_for(tmp_path, "XAUUSD", timeframe, candles, standard_feature_set())
        assert source is not None, "the store should have been usable"
        loaded = build_feature_matrix(
            candles,
            SYMBOL,
            Timeframe(timeframe),
            feature_set=standard_feature_set(),
            source=source,
        )

        assert matrix_bytes(loaded) == matrix_bytes(computed)

    def test_the_shape_and_columns_match(self, tmp_path):
        candles = make_candles(400)
        seed_store(tmp_path, candles)

        computed = build_feature_matrix(
            candles,
            SYMBOL,
            Timeframe("1H"),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        loaded = build_feature_matrix(
            candles,
            SYMBOL,
            Timeframe("1H"),
            feature_set=standard_feature_set(),
            source=stored_source_for(tmp_path, "XAUUSD", "1H", candles, standard_feature_set()),
        )

        assert loaded.column_names == computed.column_names
        assert loaded.source_index == computed.source_index
        assert loaded.dropped_warmup == computed.dropped_warmup
        assert loaded.dropped_tail == computed.dropped_tail
        assert loaded.width == 123

    def test_the_warmup_survives_the_round_trip(self, tmp_path):
        """Warm-up is metadata, not a value — it must still be stored."""
        candles = make_candles(300)
        seed_store(tmp_path, candles)
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "1H")

        result = store.load("tenkan", store.next_version("tenkan") - 1)

        assert result is not None
        assert result.warmup == 51  # the catalogue's deepest lookback

    def test_reading_is_not_slower_than_computing(self, tmp_path):
        """The whole point is speed; a slower cache is a bug."""
        import time

        candles = make_candles(600)
        seed_store(tmp_path, candles)

        start = time.monotonic()
        build_feature_matrix(
            candles,
            SYMBOL,
            Timeframe("1H"),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        computed_seconds = time.monotonic() - start

        source = stored_source_for(tmp_path, "XAUUSD", "1H", candles, standard_feature_set())
        start = time.monotonic()
        build_feature_matrix(
            candles,
            SYMBOL,
            Timeframe("1H"),
            feature_set=standard_feature_set(),
            source=source,
        )
        loaded_seconds = time.monotonic() - start

        assert loaded_seconds < computed_seconds


# ------------------------------------------------------ the safety rails --
class TestTheStoreIsRefusedWhenItDoesNotMatch:
    def test_a_changed_dataset_disables_the_store(self, tmp_path):
        seed_store(tmp_path, make_candles(300))

        source = stored_source_for(
            tmp_path, "XAUUSD", "1H", make_candles(350), standard_feature_set()
        )

        assert source is None  # -> the caller recomputes

    def test_an_empty_store_disables_it(self, tmp_path):
        assert (
            stored_source_for(tmp_path, "XAUUSD", "1H", make_candles(300), standard_feature_set())
            is None
        )

    def test_a_length_mismatch_is_refused_per_feature(self, tmp_path):
        candles = make_candles(300)
        seed_store(tmp_path, candles)
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "1H")

        source = StoredFeatureSource(store=store, candles=candles[:200])

        assert source.get("atr_14") is None
        assert "length mismatch" in source.misses["atr_14"]

    def test_shifted_timestamps_are_refused(self, tmp_path):
        """Same length, wrong bars — the most dangerous failure mode."""
        candles = make_candles(300)
        seed_store(tmp_path, candles)
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "1H")

        shifted = make_candles(300)[:299]
        shifted.append(
            Candle(
                symbol=SYMBOL,
                timeframe=Timeframe("1H"),
                open_time=Timestamp(BASE + timedelta(days=900)),
                open_price=Price(Decimal("2000")),
                high=Price(Decimal("2001")),
                low=Price(Decimal("1999")),
                close=Price(Decimal("2000")),
                volume=Decimal("1"),
            )
        )
        source = StoredFeatureSource(store=store, candles=shifted)

        assert source.get("atr_14") is None
        assert "timestamp mismatch" in source.misses["atr_14"]

    def test_a_partial_store_is_reported(self, tmp_path):
        candles = make_candles(300)
        seed_store(tmp_path, candles)
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "1H")
        source = StoredFeatureSource(store=store, candles=candles)

        source.get("atr_14")
        source.get("a_feature_that_was_never_computed")

        assert source.served == 1
        assert not source.is_complete
        assert "nothing stored" in source.misses["a_feature_that_was_never_computed"]

    def test_the_training_service_falls_back_when_incomplete(self, tmp_path):
        """A partial cache must never narrow the model input."""
        from ShadBotTrader.application.services.training_data_service import (
            TrainingDataService,
        )

        candles = make_candles(400)
        seed_store(tmp_path, candles)
        # Remove one feature so the cache can no longer serve the full set.
        import shutil

        shutil.rmtree(tmp_path / "features/XAUUSD/1H/atr_14")

        service = TrainingDataService(
            tmp_path,
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )
        record, *_ = service.build_slice(candles, "XAUUSD", "1H", len(candles))

        assert record.feature_columns == 70
        assert "computed" in service.last_source
