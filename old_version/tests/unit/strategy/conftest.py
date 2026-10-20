"""Shared builders for the trading (strategy) domain tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.risk.risk_state import RiskState
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import SignalStrength, SignalType

BASE_TIME = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def symbol() -> Symbol:
    return Symbol("XAUUSD_i")


@pytest.fixture
def timeframe() -> Timeframe:
    return Timeframe("5M")


@pytest.fixture
def now() -> Timestamp:
    return Timestamp(BASE_TIME)


def make_prediction(
    value: float = 0.8,
    confidence: float = 0.9,
    age_seconds: float = 0.0,
    model_id: str = "gold_direction",
    model_version: int = 1,
) -> PredictionView:
    """Build a prediction generated ``age_seconds`` before BASE_TIME."""
    return PredictionView(
        model_id=model_id,
        model_version=model_version,
        value=value,
        confidence=confidence,
        generated_at=Timestamp(BASE_TIME - timedelta(seconds=age_seconds)),
    )


def make_context(
    symbol: Symbol,
    timeframe: Timeframe,
    predictions=(),
    portfolio: PortfolioView | None = None,
    risk_state: RiskState | None = None,
    timestamp: Timestamp | None = None,
) -> StrategyContext:
    return StrategyContext(
        timestamp=timestamp or Timestamp(BASE_TIME),
        symbol=symbol,
        timeframe=timeframe,
        predictions=list(predictions),
        portfolio=portfolio,
        risk_state=risk_state,
    )


def make_signal(
    symbol: Symbol,
    timeframe: Timeframe,
    signal_type: SignalType = SignalType.BUY,
    confidence: float = 0.9,
    timestamp: Timestamp | None = None,
    strategy_id: str = "ai_directional",
) -> TradingSignal:
    return TradingSignal(
        signal_id=f"sig:{signal_type.value}",
        strategy_id=StrategyId(strategy_id),
        strategy_version=StrategyVersion(1),
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp or Timestamp(BASE_TIME),
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=confidence,
    )


def flat_portfolio(equity: str = "10000") -> PortfolioView:
    return PortfolioView(equity=Decimal(equity), open_position_quantity=Decimal("0"))


def long_portfolio(quantity: str = "1", equity: str = "10000") -> PortfolioView:
    return PortfolioView(
        equity=Decimal(equity),
        open_position_quantity=Decimal(quantity),
        open_position_count=1,
    )


def short_portfolio(quantity: str = "-1", equity: str = "10000") -> PortfolioView:
    return PortfolioView(
        equity=Decimal(equity),
        open_position_quantity=Decimal(quantity),
        open_position_count=1,
    )


def calm_risk() -> RiskState:
    return RiskState(
        max_drawdown_percent=Decimal("2"),
        max_daily_loss_percent=Decimal("1"),
        exposure_ratio=Decimal("0.1"),
    )


def breached_risk() -> RiskState:
    return RiskState(
        max_drawdown_percent=Decimal("50"),
        max_daily_loss_percent=Decimal("30"),
        exposure_ratio=Decimal("0.9"),
    )
