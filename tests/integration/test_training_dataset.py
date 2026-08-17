"""Integration tests for the Phase 30 dataset and live buffer.

Covers the two things the user specified precisely: a stored training
dataset the models read through stride-1 windows, and a self-maintaining
live buffer that yields the newest 500 rows.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.training_data_service import TrainingDataService
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.training_dataset import DatasetSpec, matrix_digest
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.feature_matrix import CANDLE_COLUMNS, RAW_PRICE_COLUMNS
from ShadBotTrader.infrastructure.ai.live_matrix import LiveMatrixBuilder
from ShadBotTrader.infrastructure.data.live_buffer import LiveMarketData
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

SYMBOL = "XAUUSD"
BASE = datetime(2024, 1, 2, tzinfo=timezone.utc)


def candles(count: int, timeframe: str = "5M", minutes: int = 5):
    symbol = Symbol(SYMBOL)
    tf = Timeframe(timeframe)
    out = []
    price = 2000.0
    for index in range(count):
        move = math.sin(index / 40.0) * 4.0 + ((index % 7) - 3) * 0.3
        open_, close = price, price + move
        out.append(
            Candle(
                symbol=symbol,
                timeframe=tf,
                open_time=Timestamp(BASE + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1.1, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1.1, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal("100"),
            )
        )
        price = close
    return out


@pytest.fixture
def service(tmp_path):
    return TrainingDataService(
        tmp_path, feature_set=standard_feature_set(), resolver=CalculatorRegistry()
    )


@pytest.fixture
def spec():
    # 1,200 candles keeps the suite fast; the 100,000 path is identical.
    return DatasetSpec(symbol=SYMBOL, timeframes=("5M", "1H"), target_candles=1200)


# ------------------------------------------------------------- columns ---
class TestColumnLayout:
    def test_the_raw_market_prices_are_present(self):
        """They were missing before Phase 30 — only wavelet-filtered ones existed."""
        assert "open_rel" in RAW_PRICE_COLUMNS
        assert "high_rel" in RAW_PRICE_COLUMNS
        assert "low_rel" in RAW_PRICE_COLUMNS
        assert "close_rel" in RAW_PRICE_COLUMNS
        assert len(RAW_PRICE_COLUMNS) == 8

    def test_the_matrix_is_one_hundred_and_twenty_three_columns_wide(self, service, spec):
        record, rows, columns, _ = service.build_slice(candles(400), SYMBOL, "5M", 400)

        assert record.feature_columns == 123
        assert len(columns) == 123
        assert len(CANDLE_COLUMNS) == 14  # 8 raw + 6 derived

    def test_close_relative_to_itself_is_always_zero(self, service):
        _, rows, columns, _ = service.build_slice(candles(300), SYMBOL, "5M", 300)
        position = columns.index("close_rel")

        assert all(abs(row[position]) < 1e-12 for row in rows)

    def test_raw_prices_are_ratios_not_levels(self, service):
        """Otherwise the model memorises the training price range."""
        _, rows, columns, _ = service.build_slice(candles(300), SYMBOL, "5M", 300)
        position = columns.index("high_rel")

        # gold trades near 2000; a ratio must stay tiny
        assert all(abs(row[position]) < 0.5 for row in rows)


# ------------------------------------------------------------- dataset ---
class TestDatasetBuild:
    def test_both_timeframes_are_built_and_stored(self, service, spec):
        manifest = service.build(
            spec, {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)}
        )

        assert set(manifest.slices) == {"5M", "1H"}
        assert service.matrix_path(SYMBOL, "5M").exists()
        assert service.matrix_path(SYMBOL, "1H").exists()
        assert service.manifest_path(SYMBOL).exists()

    def test_a_stored_matrix_round_trips_unchanged(self, service, spec):
        manifest = service.build(
            spec, {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)}
        )
        stored = service.load_matrix(SYMBOL, "5M")

        assert stored is not None
        assert stored.width == 123
        assert len(stored) == manifest.slices["5M"].feature_rows
        assert matrix_digest(stored.rows) == manifest.slices["5M"].digest

    def test_a_short_history_is_reported_not_hidden(self, service, spec):
        """Brokers do not always have 100k bars; rounding that away lies."""
        manifest = service.build(spec, {"5M": candles(600, "5M", 5), "1H": candles(600, "1H", 60)})

        assert not manifest.is_complete
        assert manifest.slices["5M"].shortfall == 600
        assert any("short by" in warning.lower() for warning in manifest.warnings())

    def test_a_missing_timeframe_fails_loudly(self, service, spec):
        with pytest.raises(ValidationError) as error:
            service.build(spec, {"5M": candles(1200)})
        assert "1H" in str(error.value)

    def test_the_summary_describes_an_absent_dataset(self, service):
        assert service.summary("NOTHING")["exists"] is False


class TestWeeklyRefresh:
    def test_a_fresh_dataset_is_not_due(self, service, spec):
        service.build(spec, {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)})

        assert not service.is_refresh_due(SYMBOL)
        assert service.days_since_refresh(SYMBOL) == pytest.approx(0, abs=0.01)

    def test_an_absent_dataset_is_always_due(self, service):
        assert service.is_refresh_due("NEVER_BUILT")

    def test_refreshing_bumps_the_revision(self, service, spec):
        data = {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)}
        first = service.build(spec, data)
        second = service.refresh(spec, data)

        assert first.revision == 1
        assert second.revision == 2

    def test_recomputing_the_same_candles_reproduces_the_digest(self, service, spec):
        """Proof that "recomputed from scratch" is deterministic."""
        data = {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)}
        first = service.build(spec, data)
        second = service.refresh(spec, data)

        assert first.slices["5M"].digest == second.slices["5M"].digest

    def test_new_candles_change_the_digest(self, service, spec):
        first = service.build(spec, {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)})
        second = service.refresh(
            spec, {"5M": candles(1400, "5M", 5), "1H": candles(1400, "1H", 60)}
        )

        assert first.slices["5M"].digest != second.slices["5M"].digest
        assert second.slices["5M"].feature_rows > first.slices["5M"].feature_rows


class TestWindowAccess:
    def test_the_generator_reads_the_stored_matrix(self, service, spec):
        service.build(spec, {"5M": candles(1200, "5M", 5), "1H": candles(1200, "1H", 60)})

        generator = service.window_generator(
            SYMBOL, "5M", target_columns=[121, 122], window_size=500, horizon=5
        )

        assert generator.window_count > 0
        assert generator.input_shape[0] == 500

    def test_asking_for_an_unbuilt_dataset_explains_the_fix(self, service):
        with pytest.raises(ValidationError) as error:
            service.window_generator("MISSING", "5M", target_columns=[0])
        assert "run_training_dataset" in str(error.value)


# ---------------------------------------------------------- live matrix ---
class TestLiveMatrix:
    def test_the_buffer_yields_a_five_hundred_row_input(self):
        live = LiveMarketData(timeframes=("5M",))
        live.prime("5M", candles(800))

        builder = LiveMatrixBuilder(
            SYMBOL, feature_set=standard_feature_set(), resolver=CalculatorRegistry()
        )
        window = builder.build(live.buffer("5M"))

        assert window.shape == (500, 123)
        assert window.buffered_candles == 800

    def test_the_window_holds_the_newest_rows(self):
        live = LiveMarketData(timeframes=("5M",))
        history = candles(800)
        live.prime("5M", history)

        builder = LiveMatrixBuilder(
            SYMBOL, feature_set=standard_feature_set(), resolver=CalculatorRegistry()
        )
        window = builder.build(live.buffer("5M"))

        assert window.last_timestamp == str(history[-1].open_time)
        assert window.reference_close == float(history[-1].close.amount)

    def test_a_new_candle_shifts_the_window_forward(self):
        live = LiveMarketData(timeframes=("5M",))
        live.prime("5M", candles(800))
        builder = LiveMatrixBuilder(
            SYMBOL, feature_set=standard_feature_set(), resolver=CalculatorRegistry()
        )
        before = builder.build(live.buffer("5M"))

        live.push("5M", candles(801)[-1])
        after = builder.build(live.buffer("5M"))

        assert after.last_timestamp != before.last_timestamp
        assert after.shape == (500, 123)
        assert live.buffer("5M").size == 800  # still exactly 800

    def test_too_little_history_refuses_instead_of_padding(self):
        live = LiveMarketData(timeframes=("5M",))
        live.prime("5M", candles(520))  # 500 needed + 51 warm-up = short

        builder = LiveMatrixBuilder(
            SYMBOL, feature_set=standard_feature_set(), resolver=CalculatorRegistry()
        )
        window, reason = builder.try_build(live.buffer("5M"))

        assert window is None
        assert "warm-up" in reason
        assert "Increase the buffer capacity" in reason

    def test_the_live_columns_match_the_training_columns(self, service, spec):
        """Training and inference must see the identical world."""
        _, _, training_columns, _ = service.build_slice(candles(800), SYMBOL, "5M", 800)

        live = LiveMarketData(timeframes=("5M",))
        live.prime("5M", candles(800))
        builder = LiveMatrixBuilder(
            SYMBOL, feature_set=standard_feature_set(), resolver=CalculatorRegistry()
        )
        window = builder.build(live.buffer("5M"))

        assert window.column_names == training_columns
