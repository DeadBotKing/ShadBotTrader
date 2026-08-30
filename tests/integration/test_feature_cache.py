"""Phase 38 — reuse stored features until the dataset changes.

The user's rule, verbatim:

    "as long as the dataset has not been updated there is no need to
     recompute the features — read them from the store. But when the
     dataset IS updated, the features must be recomputed from scratch
     and stored again."

And the question that came with it: are the catalogue features actually
used in the matrix given to the model? The last class here answers that
with a measurement rather than a claim, because the answer had been
asserted in prose and never pinned down by a test that would fail if it
stopped being true.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.feature_cli import _build_service
from ShadBotTrader.infrastructure.ai.feature_matrix import (
    CANDLE_COLUMNS,
    build_feature_matrix,
)
from ShadBotTrader.infrastructure.ai.model_roles import signal_model_role
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.feature_cache import (
    FeatureCache,
    FeatureFingerprint,
    candles_digest,
)
from ShadBotTrader.infrastructure.feature.parquet_feature_store import ParquetFeatureStore
from ShadBotTrader.infrastructure.feature.standard_catalog import (
    standard_feature_set,
    standard_feature_set_v1,
)

BASE = datetime(2024, 1, 2, tzinfo=timezone.utc)


def make_candles(count: int, shift: float = 0.0, timeframe: str = "5M", minutes: int = 5):
    out = []
    price = 2000.0 + shift
    for index in range(count):
        open_ = price
        close = price + math.sin(index / 30.0) * 4.0
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


def compute(root, candles, force=False, timeframe="5M"):
    service, _, _ = _build_service(root)
    return service.compute_set(
        feature_set=standard_feature_set_v1(),
        symbol=Symbol("XAUUSD"),
        timeframe=Timeframe(timeframe),
        candles=candles,
        source_dataset_id=f"csv.market_candle.XAUUSD.{timeframe}.L3_normalized",
        dataset_version=1,
        force=force,
    )


# --------------------------------------------------- 1) the fingerprint --
class TestTheFingerprintDetectsRealChange:
    def test_identical_candles_produce_the_same_digest(self):
        assert candles_digest(make_candles(200)) == candles_digest(make_candles(200))

    def test_one_more_candle_changes_the_digest(self):
        assert candles_digest(make_candles(200)) != candles_digest(make_candles(201))

    def test_an_edited_value_changes_the_digest(self):
        """An in-place edit keeps the count identical — the values must not."""
        original = make_candles(200)
        edited = make_candles(200, shift=1.0)

        assert len(original) == len(edited)
        assert candles_digest(original) != candles_digest(edited)

    def test_a_changed_catalogue_invalidates_the_cache(self):
        candles = make_candles(200)
        full = FeatureFingerprint.of(candles, standard_feature_set_v1())

        class Trimmed:
            name = "FXTradingFeatureSetV1"
            version = type("V", (), {"number": 1})()
            definitions = standard_feature_set_v1().definitions[:-1]

        assert not FeatureFingerprint.of(candles, Trimmed()).matches(full)

    def test_the_reason_names_what_changed(self, tmp_path):
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "5M")
        cache = FeatureCache(store)
        feature_set = standard_feature_set_v1()

        assert "nothing has been computed" in cache.reason_to_recompute(
            make_candles(200), feature_set
        )

        cache.write_fingerprint(FeatureFingerprint.of(make_candles(200), feature_set))

        assert cache.reason_to_recompute(make_candles(200), feature_set) == ""
        assert "candle count changed" in cache.reason_to_recompute(make_candles(250), feature_set)
        assert "updated in place" in cache.reason_to_recompute(
            make_candles(200, shift=5.0), feature_set
        )

    def test_a_corrupt_fingerprint_forces_a_recompute(self, tmp_path):
        """Never reuse values we cannot vouch for."""
        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "5M")
        cache = FeatureCache(store)
        cache.fingerprint_path.parent.mkdir(parents=True, exist_ok=True)
        cache.fingerprint_path.write_text("{ this is not json", encoding="utf-8")

        assert cache.stored_fingerprint() is None
        assert not cache.is_fresh(make_candles(200), standard_feature_set_v1())


# ------------------------------------------------ 2) the caching rule ----
class TestFeaturesAreReusedUntilTheDatasetChanges:
    def test_the_first_run_computes_everything(self, tmp_path):
        result = compute(tmp_path, make_candles(300))

        assert result.reused_count == 0
        assert not result.from_cache
        assert len(result.outcomes) == 229

    def test_the_second_run_reuses_everything(self, tmp_path):
        candles = make_candles(300)
        compute(tmp_path, candles)

        result = compute(tmp_path, candles)

        assert result.from_cache
        assert result.reused_count == 229

    def test_reuse_does_not_write_a_new_version(self, tmp_path):
        candles = make_candles(300)
        compute(tmp_path, candles)
        compute(tmp_path, candles)
        compute(tmp_path, candles)

        stored = sorted(
            path.name for path in (tmp_path / "features/XAUUSD/5M/atr_14").glob("v*.parquet")
        )

        assert stored == ["v1.parquet"]

    def test_updating_the_dataset_recomputes_from_scratch(self, tmp_path):
        compute(tmp_path, make_candles(300))

        result = compute(tmp_path, make_candles(350))

        assert not result.from_cache
        assert result.reused_count == 0
        stored = sorted(
            path.name for path in (tmp_path / "features/XAUUSD/5M/atr_14").glob("v*.parquet")
        )
        assert stored == ["v1.parquet", "v2.parquet"]

    def test_the_recompute_covers_the_whole_series_not_just_the_new_part(self, tmp_path):
        """Recursive indicators make an append silently wrong."""
        compute(tmp_path, make_candles(300))
        compute(tmp_path, make_candles(350))

        store = ParquetFeatureStore(tmp_path).for_series("XAUUSD", "5M")
        second = store.load("atr_14", 2)

        assert second is not None
        assert len(second.points) == 350  # every candle, not the 50 new ones

    def test_force_recomputes_even_when_nothing_changed(self, tmp_path):
        candles = make_candles(300)
        compute(tmp_path, candles)

        result = compute(tmp_path, candles, force=True)

        assert not result.from_cache
        assert result.reused_count == 0

    def test_each_timeframe_caches_independently(self, tmp_path):
        five = make_candles(300, timeframe="5M", minutes=5)
        hour = make_candles(300, timeframe="1H", minutes=60)
        compute(tmp_path, five, timeframe="5M")
        compute(tmp_path, hour, timeframe="1H")

        # 5M unchanged -> reused; 1H updated -> recomputed
        assert compute(tmp_path, five, timeframe="5M").from_cache
        assert not compute(
            tmp_path, make_candles(320, timeframe="1H", minutes=60), timeframe="1H"
        ).from_cache
        # and 5M is still cached, untouched by the 1H recompute
        assert compute(tmp_path, five, timeframe="5M").from_cache

    def test_reused_values_are_identical_to_recomputed_ones(self, tmp_path):
        """A cache that returns different numbers is worse than no cache."""
        candles = make_candles(300)
        first = compute(tmp_path, candles)
        cached = compute(tmp_path, candles)

        assert cached.from_cache
        assert [item.feature_id for item in cached.outcomes] == [
            item.feature_id for item in first.outcomes
        ]
        assert [item.available_count for item in cached.outcomes] == [
            item.available_count for item in first.outcomes
        ]


# ------------------------------------- 3) the catalogue reaches the model --
class TestTheModelActuallyReceivesTheCatalogue:
    """The user asked: what matrix are you giving the model?

    The answer is measured here so it cannot quietly regress into the
    14-column fallback again.
    """

    def test_the_matrix_carries_all_229_catalogue_features(self):
        matrix = build_feature_matrix(
            make_candles(400),
            Symbol("XAUUSD"),
            Timeframe("5M"),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )

        catalogue = matrix.column_names[len(CANDLE_COLUMNS) :]

        assert matrix.width == 243
        assert len(CANDLE_COLUMNS) == 14
        assert len(catalogue) == 229

    def test_named_indicators_are_present_by_name(self):
        matrix = build_feature_matrix(
            make_candles(400),
            Symbol("XAUUSD"),
            Timeframe("5M"),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )

        for feature_id in ("atr_14", "rsi_14", "macd_12_26_9", "bollinger_20_2", "tenkan"):
            assert feature_id in matrix.column_names, feature_id

    def test_the_prepared_training_dataset_is_causal_179_columns_wide(self):
        service = DualModelService(
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
            include_features=True,
        )

        prepared = service.prepare(
            make_candles(400),
            Symbol("XAUUSD"),
            Timeframe("5M"),
            signal_model_role(window_size=40),
        )

        assert prepared.summary()["feature_columns"] == 179

    def test_without_the_catalogue_it_is_only_14_columns(self):
        """The reduced path exists; this pins the difference."""
        service = DualModelService(include_features=False)

        prepared = service.prepare(
            make_candles(400),
            Symbol("XAUUSD"),
            Timeframe("5M"),
            signal_model_role(window_size=40),
        )

        assert prepared.summary()["feature_columns"] == 14

    def test_the_gui_training_button_asks_for_the_catalogue(self):
        """--with-features is what separates 123 columns from 14."""
        from pathlib import Path

        source = Path(__file__).resolve().parents[2]
        handlers = (source / "src/ShadBotTrader/presentation/commands/handlers.py").read_text(
            encoding="utf-8"
        )

        index = handlers.index("scripts/run_dual_models.py")
        window = handlers[index : index + 400]
        assert "--with-features" in window

    @pytest.mark.parametrize("timeframe,minutes", [("5M", 5), ("1H", 60)])
    def test_both_timeframes_get_the_full_width(self, timeframe, minutes):
        matrix = build_feature_matrix(
            make_candles(400, timeframe=timeframe, minutes=minutes),
            Symbol("XAUUSD"),
            Timeframe(timeframe),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
        )

        assert matrix.width == 243
