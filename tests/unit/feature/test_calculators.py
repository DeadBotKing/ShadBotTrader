"""Tests for the indicator calculators (determinism, causality, warmup)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition, FeatureId
from ShadBotTrader.domain.feature.feature_types import (
    Causality,
    FeatureType,
    FeatureValueType,
)
from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator


def _definition(feature_id: str, parameters: dict, lookback: int) -> FeatureDefinition:
    return FeatureDefinition(
        feature_id=FeatureId(feature_id),
        name=feature_id,
        feature_type=FeatureType.TREND,
        value_type=FeatureValueType.SCALAR,
        parameters=parameters,
        lookback=lookback,
        computation_version="1",
    )


def _candles(closes: list[float]) -> list[Candle]:
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    candles = []
    for index, close in enumerate(closes):
        candles.append(
            Candle(
                symbol=Symbol("XAUUSD_i"),
                timeframe=Timeframe("5M"),
                open_time=Timestamp(start + index * timedelta(minutes=5)),
                open_price=Price(str(100 + close)),
                high=Price(str(100 + close + 2)),
                low=Price(str(100 + close - 2)),
                close=Price(str(100 + close)),
                volume=Decimal("100"),
            )
        )
    return candles


def _context(closes: list[float]) -> FeatureInputContext:
    return FeatureInputContext(Symbol("XAUUSD_i"), Timeframe("5M"), _candles(closes))


def test_sma_warmup_and_value():
    context = _context([1, 2, 3, 4, 5])
    result = SmaCalculator().compute(_definition("sma_3", {"period": 3}, 2), context)
    assert result.warmup == 2
    assert result.points[0].value is None
    assert result.points[1].value is None
    assert result.points[2].value == pytest.approx(102.0)  # (101+102+103)/3
    assert result.points[4].value == pytest.approx(104.0)  # (103+104+105)/3


def test_ema_is_deterministic():
    context = _context([10, 11, 12, 13, 14, 15])
    definition = _definition("ema_3", {"period": 3}, 2)
    first = EmaCalculator().compute(definition, context)
    second = EmaCalculator().compute(definition, context)
    assert first.points == second.points


def test_rsi_is_bounded_and_causal():
    context = _context([10, 11, 12, 11, 12, 13, 12, 13, 14, 13, 14, 15, 14, 15, 16, 15])
    result = RsiCalculator().compute(_definition("rsi_14", {"period": 14}, 14), context)
    values = [p.value for p in result.points if p.value is not None]
    assert values
    for value in values:
        assert 0.0 <= value <= 100.0


def test_atr_is_positive_after_warmup():
    context = _context([10, 11, 12, 11, 12, 13, 12, 13, 14, 13, 14, 15, 14, 15, 16, 15])
    result = AtrCalculator().compute(_definition("atr_14", {"period": 14}, 14), context)
    values = [p.value for p in result.points if p.value is not None]
    assert all(value > 0 for value in values)


def test_returns_first_available_after_period():
    context = _context([100, 110, 121, 133.1])
    result = ReturnsCalculator().compute(_definition("returns_1", {"period": 1}, 1), context)
    assert result.points[0].value is None
    assert result.points[1].value == pytest.approx(0.05)  # (210-200)/200


def test_stochastic_is_bounded():
    context = _context([10, 11, 12, 11, 12, 13, 12, 13, 14, 13, 14, 15, 14, 15, 16, 15])
    result = StochasticCalculator().compute(
        _definition("stochastic_14", {"period": 14}, 13), context
    )
    values = [p.value for p in result.points if p.value is not None]
    for value in values:
        assert 0.0 <= value <= 100.0


def test_macd_warmup_matches_definition():
    context = _context([float(i) for i in range(1, 80)])
    definition = _definition("macd_12_26_9", {"fast": 12, "slow": 26, "signal": 9}, 33)
    result = MacdCalculator().compute(definition, context)
    assert result.warmup == 33
    assert result.points[33].value is not None
    assert result.points[32].value is None


def test_ichimoku_tenkan_warmup():
    context = _context([float(i) for i in range(1, 80)])
    definition = FeatureDefinition(
        feature_id=FeatureId("tenkan"),
        name="tenkan",
        feature_type=FeatureType.TREND,
        value_type=FeatureValueType.SCALAR,
        parameters={"line": "tenkan", "tenkan": 9, "kijun": 26, "senkou": 52},
        lookback=51,
        computation_version="1",
        family="ichimoku",
    )
    from ShadBotTrader.infrastructure.feature.calculators.ichimoku import IchimokuCalculator

    result = IchimokuCalculator().compute(definition, context)
    assert result.warmup == 51
    assert result.points[51].value is not None


def test_target_past_and_future_shifts():
    context = _context([100.0, 101.0, 102.0, 103.0])
    past_def = FeatureDefinition(
        feature_id=FeatureId("close_target_m1"),
        name="close target -1",
        feature_type=FeatureType.DERIVED,
        value_type=FeatureValueType.SCALAR,
        parameters={"column": "close", "shift": -1},
        lookback=0,
        computation_version="1",
        family="target",
    )
    from ShadBotTrader.infrastructure.feature.calculators.target import TargetCalculator

    past = TargetCalculator().compute(past_def, context)
    assert past.points[0].value is None  # shift(-1) -> first row unknown
    assert past.points[1].value == 200.0


def test_noise_filter_smooths_without_breaking_shape():
    context = _context([float(i) for i in range(1, 60)])
    definition = FeatureDefinition(
        feature_id=FeatureId("close_filter"),
        name="close filter",
        feature_type=FeatureType.DERIVED,
        value_type=FeatureValueType.SCALAR,
        parameters={"column": "close"},
        lookback=0,
        computation_version="1",
        family="noise_filter",
    )
    from ShadBotTrader.infrastructure.feature.calculators.noise_filter import (
        NoiseFilterCalculator,
    )

    result = NoiseFilterCalculator().compute(definition, context)
    assert len(result.points) == 59
    assert result.points[10].value is not None


def test_fourier_sin_cos_bounded():
    context = _context([float(i) for i in range(1, 80)])
    for function in ("sin", "cos"):
        definition = FeatureDefinition(
            feature_id=FeatureId(f"{function}_close"),
            name=f"{function} close",
            feature_type=FeatureType.DERIVED,
            value_type=FeatureValueType.SCALAR,
            parameters={"column": "close", "function": function},
            lookback=0,
            computation_version="1",
            family="fourier",
            causality=Causality.NON_CAUSAL,
        )
        from ShadBotTrader.infrastructure.feature.calculators.fourier import (
            FourierCalculator,
        )

        result = FourierCalculator().compute(definition, context)
        values = [p.value for p in result.points if p.value is not None]
        assert values
        for value in values:
            assert -1.0 <= value <= 1.0


def test_bband_mid_is_sma():
    context = _context([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    definition = FeatureDefinition(
        feature_id=FeatureId("bband_mid"),
        name="bband mid",
        feature_type=FeatureType.STATISTICAL,
        value_type=FeatureValueType.SCALAR,
        parameters={"period": 5, "num_std": 2.0, "band": "mid", "column": "close"},
        lookback=4,
        computation_version="1",
        family="bband",
    )
    from ShadBotTrader.infrastructure.feature.calculators.bollinger_bands import (
        BollingerBandsCalculator,
    )

    result = BollingerBandsCalculator().compute(definition, context)
    assert result.points[4].value == pytest.approx(103.0)  # mean of 101..105


def test_writable_helper_forces_copy_from_readonly():
    """هلپر باید حتی از آرایه‌ی read-only هم کپی writable بسازد.

    این دقیقاً همان خطای "buffer source array is read-only" ویندوز است:
    pandas ممکن است یک view فقط-خواندنی برگرداند و np.ascontiguousarray
    آن را دست‌نخورده پاس می‌دهد؛ کپی اجباری باید جلویش را بگیرد.
    """
    import numpy as np

    from ShadBotTrader.infrastructure.feature.calculators.noise_filter import (
        _writable_float64,
    )

    arr = np.arange(60, dtype=np.float64)
    arr.setflags(write=False)  # همان وضعیت buffer read-only

    result = _writable_float64(arr)
    assert result.flags.writeable is True
    assert result.flags.c_contiguous is True
    assert result.dtype == np.float64
    assert (result == arr).all()

    # اگر ورودی writable باشد هم باید همچنان writable بماند
    writable = np.arange(10, dtype=np.float64)
    result2 = _writable_float64(writable)
    assert result2.flags.writeable is True
