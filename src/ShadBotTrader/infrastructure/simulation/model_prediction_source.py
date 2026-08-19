"""Drive a backtest with the trained models (Phase 31, part B).

Until now the backtester ran on ``MomentumPredictionSource``, a
deliberate baseline. This source replaces it with the real Phase 29
signal model, so a backtest finally measures the thing that will trade.

The hard part is not inference — it is honesty about time. A backtest
that lets a model see bar ``t+1`` while deciding at bar ``t`` produces a
beautiful equity curve and loses money live. Two guarantees:

**Causality.** The source keeps its own rolling window and only ever
appends the bar the engine has already delivered. Nothing else is
reachable.

**No silent warm-up.** Until ``window_size`` bars have arrived the source
returns ``None`` — abstain — rather than padding the window. A padded
window is a model reading invented history.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Sequence

from ShadBotTrader.domain.ai.prediction_target import SignalForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.ports import PredictionSource


class ModelPredictionSource(PredictionSource):
    """Feeds the backtest with the trained signal model's output.

    The engine's ``PredictionSource`` contract is a single float in
    ``[0, 1]``. For the binary forecast this is simply the BUY
    probability; SELL is below 0.5. A low winning probability is handled
    by the strategy confidence gate, not by a HOLD model class.

    The full forecast stays available via :meth:`last_forecast` for
    anything that wants the probabilities themselves.
    """

    def __init__(
        self,
        artifact: Any,
        predictor: Any,
        symbol: Symbol,
        timeframe: Timeframe,
        feature_set: Any = None,
        resolver: Any = None,
        window_size: int = 500,
        recompute_every: int = 1,
        hold_confidence_penalty: float = 0.5,
    ) -> None:
        if window_size < 2:
            raise ValidationError("window_size must be >= 2")
        if recompute_every < 1:
            raise ValidationError("recompute_every must be >= 1")

        self._artifact = artifact
        self._predictor = predictor
        self._symbol = symbol
        self._timeframe = timeframe
        self._feature_set = feature_set
        self._resolver = resolver
        self._window_size = window_size
        self._recompute_every = recompute_every
        self._hold_penalty = float(hold_confidence_penalty)

        # Enough history for the window plus feature warm-up.
        self._candles: Deque[Candle] = deque(maxlen=window_size * 2)
        self._bars_seen = 0
        self._last_forecast: Optional[SignalForecast] = None
        self._last_value: Optional[float] = None
        self._predictions_made = 0
        self._abstentions = 0

    # ------------------------------------------------------------ state --
    @property
    def last_forecast(self) -> Optional[SignalForecast]:
        """The most recent binary forecast, if any."""
        return self._last_forecast

    @property
    def predictions_made(self) -> int:
        return self._predictions_made

    @property
    def abstentions(self) -> int:
        """Bars the source declined to judge (warm-up or a failed input)."""
        return self._abstentions

    def stats(self) -> Dict[str, Any]:
        return {
            "bars_seen": self._bars_seen,
            "predictions": self._predictions_made,
            "abstentions": self._abstentions,
            "window_size": self._window_size,
            "recompute_every": self._recompute_every,
        }

    # ------------------------------------------------------------- port --
    def observe(self, event: MarketEvent) -> None:
        """Record the bar the engine just delivered — and nothing more."""
        if event.candle is not None:
            self._candles.append(event.candle)
            self._bars_seen += 1

    def predict(self, event: MarketEvent) -> Optional[float]:
        """Directional value in [0, 1], or None to abstain."""
        if len(self._candles) < self._window_size:
            self._abstentions += 1
            return None

        # Re-running a 500x123 forward pass on every bar is expensive; on
        # skipped bars the previous forecast is reused rather than
        # fabricating a new one.
        if (
            self._recompute_every > 1
            and self._last_value is not None
            and self._bars_seen % self._recompute_every != 0
        ):
            return self._last_value

        window = self._build_window()
        if window is None:
            self._abstentions += 1
            return None

        forecast = self._predictor.forecast(self._artifact, window)
        self._last_forecast = forecast
        self._predictions_made += 1

        # Binary signal model: directional_confidence is the BUY
        # probability and every prediction is either BUY or SELL.  A low
        # winning probability is rejected by the confidence gate, not
        # encoded as a third HOLD class.
        self._last_value = float(forecast.directional_confidence)
        return self._last_value

    def confidence(self, event: MarketEvent) -> float:
        """Confidence of the current forecast; 0 when abstaining."""
        if self._last_forecast is None:
            return 0.0
        return self._last_forecast.confidence

    def reset(self) -> None:
        self._candles.clear()
        self._bars_seen = 0
        self._last_forecast = None
        self._last_value = None
        self._predictions_made = 0
        self._abstentions = 0

    # -------------------------------------------------------- internals --
    def _build_window(self) -> Optional[List[List[float]]]:
        """Features over the buffered candles, newest ``window_size`` rows."""
        from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix

        candles: Sequence[Candle] = list(self._candles)
        try:
            matrix = build_feature_matrix(
                candles=candles,
                symbol=self._symbol,
                timeframe=self._timeframe,
                feature_set=self._feature_set,
                resolver=self._resolver,
                include_features=self._feature_set is not None and self._resolver is not None,
            )
        except Exception:
            # A malformed window must not abort a 100k-bar backtest; the
            # source abstains for this bar and the run continues.
            return None

        if len(matrix) < self._window_size:
            return None

        from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

        rows = [list(row) for row in matrix.rows[-self._window_size :]]
        return minmax_scale_window(rows)
