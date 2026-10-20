"""Strategy evaluation context (Phase 14, section 10).

The context is everything a strategy is allowed to see. It is a plain
domain value: no repositories, no clients, no infrastructure. This keeps
strategies pure and deterministic — the same context always yields the
same signal.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Mapping, Optional, Sequence

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.risk.risk_state import RiskState
from ShadBotTrader.domain.strategy.strategy_types import MarketRegime


class PredictionView:
    """A read-only view of one AI prediction, as a strategy sees it.

    The Trading Platform must validate predictions before use (Phase 14,
    sections 31-32), so the fields needed for that validation — model
    identity/version and the generation timestamp — are explicit.
    """

    def __init__(
        self,
        model_id: str,
        model_version: int,
        value: float,
        confidence: float,
        generated_at: Timestamp,
        feature_set_version: int = 1,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._model_id = model_id
        self._model_version = model_version
        self._value = float(value)
        self._confidence = float(confidence)
        self._generated_at = generated_at
        self._feature_set_version = feature_set_version
        self._metadata: Dict[str, Any] = dict(metadata or {})

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def model_version(self) -> int:
        return self._model_version

    @property
    def value(self) -> float:
        return self._value

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def generated_at(self) -> Timestamp:
        return self._generated_at

    @property
    def feature_set_version(self) -> int:
        return self._feature_set_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def age_seconds(self, now: Timestamp) -> float:
        """Seconds between generation and ``now`` (negative if in future)."""
        return (now.value - self._generated_at.value).total_seconds()


class PortfolioView:
    """A read-only view of the portfolio a strategy may consider."""

    def __init__(
        self,
        equity: Decimal,
        open_position_quantity: Decimal = Decimal("0"),
        open_position_count: int = 0,
    ) -> None:
        self._equity = equity
        self._open_position_quantity = open_position_quantity
        self._open_position_count = open_position_count

    @property
    def equity(self) -> Decimal:
        return self._equity

    @property
    def open_position_quantity(self) -> Decimal:
        """Net signed quantity: positive long, negative short, 0 flat."""
        return self._open_position_quantity

    @property
    def open_position_count(self) -> int:
        return self._open_position_count

    @property
    def is_flat(self) -> bool:
        return self._open_position_quantity == 0

    @property
    def is_long(self) -> bool:
        return self._open_position_quantity > 0

    @property
    def is_short(self) -> bool:
        return self._open_position_quantity < 0


class StrategyContext:
    """Everything a strategy is allowed to see when it evaluates."""

    def __init__(
        self,
        timestamp: Timestamp,
        symbol: Symbol,
        timeframe: Timeframe,
        candles: Sequence[Candle] = (),
        features: Mapping[str, float] | None = None,
        predictions: Sequence[PredictionView] = (),
        portfolio: Optional[PortfolioView] = None,
        risk_state: Optional[RiskState] = None,
        regime: MarketRegime = MarketRegime.UNKNOWN,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._timestamp = timestamp
        self._symbol = symbol
        self._timeframe = timeframe
        self._candles = list(candles)
        self._features: Dict[str, float] = dict(features or {})
        self._predictions = list(predictions)
        self._portfolio = portfolio
        self._risk_state = risk_state
        self._regime = regime
        self._metadata: Dict[str, Any] = dict(metadata or {})

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def candles(self) -> list[Candle]:
        """Candles ordered ascending by open time."""
        return list(self._candles)

    @property
    def features(self) -> Dict[str, float]:
        return dict(self._features)

    @property
    def predictions(self) -> list[PredictionView]:
        return list(self._predictions)

    @property
    def portfolio(self) -> Optional[PortfolioView]:
        return self._portfolio

    @property
    def risk_state(self) -> Optional[RiskState]:
        return self._risk_state

    @property
    def regime(self) -> MarketRegime:
        return self._regime

    @property
    def metadata(self) -> Dict[str, Any]:
        """Non-numeric context supplied by an application service."""
        return dict(self._metadata)

    def feature(self, name: str, default: float | None = None) -> float | None:
        """Return a feature value, or ``default`` when absent."""
        return self._features.get(name, default)

    def prediction_for(self, model_id: str) -> Optional[PredictionView]:
        """Return the first prediction produced by ``model_id``."""
        for prediction in self._predictions:
            if prediction.model_id == model_id:
                return prediction
        return None

    @property
    def latest_candle(self) -> Optional[Candle]:
        return self._candles[-1] if self._candles else None
