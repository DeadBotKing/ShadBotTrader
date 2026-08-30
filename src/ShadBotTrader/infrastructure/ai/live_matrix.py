"""Turn the live 800-candle buffer into a (500, 123) model input.

Phase 30 §5. Every five minutes the buffer receives one new candle per
timeframe; this module recomputes the features over the whole buffer and
hands the models the most recent 500 rows.

Why recompute all 800 rather than just the new bar: recursive indicators
(EMA, MACD, ATR) depend on their own history, so a value computed from a
one-bar update is not the value the training pipeline produced. The
training and live paths must agree exactly, or the model sees a different
world at inference than it learned from. 800 rows costs well under a
second — far cheaper than a subtly mismatched input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
from ShadBotTrader.infrastructure.data.live_buffer import REQUIRED_WINDOW, RollingCandleBuffer


@dataclass(frozen=True)
class LiveWindow:
    """A ready-to-predict model input plus the context behind it."""

    rows: List[List[float]]
    column_names: List[str]
    timeframe: str
    reference_close: float
    last_timestamp: str
    buffered_candles: int
    warmup_dropped: int
    #: ATR(14) at the reference candle (فاز ۹۵) — de-normalizes an
    #: ATR-unit range forecast back into dollars. 0.0 when unavailable.
    atr_reference: float = 0.0

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.rows), len(self.column_names))

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeframe": self.timeframe,
            "shape": list(self.shape),
            "reference_close": self.reference_close,
            "last_timestamp": self.last_timestamp,
            "buffered_candles": self.buffered_candles,
            "warmup_dropped": self.warmup_dropped,
            "atr_reference": self.atr_reference,
        }


class LiveMatrixBuilder:
    """Builds model inputs from a rolling buffer."""

    def __init__(
        self,
        symbol: str,
        feature_set: Any = None,
        resolver: Any = None,
        window_rows: int = REQUIRED_WINDOW,
    ) -> None:
        if window_rows < 2:
            raise ValidationError("window_rows must be >= 2")
        self._symbol = symbol
        self._feature_set = feature_set
        self._resolver = resolver
        self._window_rows = window_rows

    @property
    def window_rows(self) -> int:
        return self._window_rows

    def build(self, buffer: RollingCandleBuffer) -> LiveWindow:
        """Compute features over the buffer and take the last N rows.

        Raises with an actionable message when the buffer cannot yet
        produce a full window — a short input would be the model reading
        garbage, so it is refused rather than padded.
        """
        candles: Sequence[Candle] = buffer.candles
        if not candles:
            raise ValidationError(
                f"{buffer.timeframe}: the buffer is empty. Prime it with "
                f"history before requesting a prediction."
            )

        matrix = build_feature_matrix(
            candles=candles,
            symbol=Symbol(self._symbol),
            timeframe=Timeframe(buffer.timeframe),
            feature_set=self._feature_set,
            resolver=self._resolver,
            include_features=self._feature_set is not None and self._resolver is not None,
            causal_only=True,
        )

        if len(matrix) < self._window_rows:
            raise ValidationError(
                f"{buffer.timeframe}: {len(candles)} candles buffered produced "
                f"only {len(matrix)} usable rows after {matrix.dropped_warmup} "
                f"were consumed by feature warm-up, but the models need "
                f"{self._window_rows}. Increase the buffer capacity to at "
                f"least {self._window_rows + matrix.dropped_warmup}."
            )

        rows = [list(row) for row in matrix.rows[-self._window_rows :]]
        last_candle = candles[-1]

        # فاز ۹۵: ATR(14) روی همان بافر — برای مدل رنج ATR-unit
        atr_reference = 0.0
        try:
            from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

            atr_value = atr_from_candles(list(candles), period=14)
            atr_reference = float(atr_value) if atr_value is not None else 0.0
        except ValidationError:
            atr_reference = 0.0

        return LiveWindow(
            rows=rows,
            column_names=list(matrix.column_names),
            timeframe=buffer.timeframe,
            reference_close=float(last_candle.close.amount),
            last_timestamp=str(last_candle.open_time),
            buffered_candles=len(candles),
            warmup_dropped=matrix.dropped_warmup,
            atr_reference=atr_reference,
        )

    def try_build(self, buffer: RollingCandleBuffer) -> tuple[Optional[LiveWindow], str]:
        """Non-raising variant for the trading loop.

        Returns ``(window, "")`` on success or ``(None, reason)`` — a
        five-minute loop should log why it skipped a tick, not crash.
        """
        try:
            return self.build(buffer), ""
        except ValidationError as error:
            return None, str(error)


def scale_for_model(rows: Sequence[Sequence[float]]) -> List[List[float]]:
    """Apply the same per-window scaling training used.

    Inference must scale exactly as training did; anything else feeds the
    model a differently-shaped world than it learned from.
    """
    from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

    return minmax_scale_window([list(row) for row in rows])
