"""Console reporting for simulation runs (Phase 16, sections 74-76)."""

from __future__ import annotations

import sys
from decimal import Decimal
from typing import List, Optional, TextIO

from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.performance import PerformanceMetrics, TradeRecord
from ShadBotTrader.domain.simulation.ports import SimulationReporter
from ShadBotTrader.domain.simulation.session import SimulationSession


def _show(value: Optional[Decimal], digits: int = 4) -> str:
    """Format an optional metric, making 'undefined' explicit."""
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


class ConsoleSimulationReporter(SimulationReporter):
    """Prints the plan, optional per-bar progress and the final report."""

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        show_steps: bool = False,
        step_every: int = 25,
    ) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self._show_steps = show_steps
        self._step_every = max(step_every, 1)
        self._steps = 0

    def _write(self, text: str = "") -> None:
        self._stream.write(text + "\n")
        self._stream.flush()

    def on_session_start(self, session: SimulationSession) -> None:
        config = session.configuration
        self._steps = 0
        self._write()
        self._write("=" * 70)
        self._write(f"  BACKTEST  {session.session_id}")
        self._write("=" * 70)
        self._write(f"  mode            : {config.mode.value}")
        self._write(f"  initial capital : {config.initial_capital} {config.base_currency}")
        self._write(f"  spread          : {config.spread}")
        self._write(f"  slippage        : {config.slippage_rate}")
        self._write(f"  commission      : {config.commission_rate}")
        self._write(f"  warmup bars     : {config.warmup_bars}")
        self._write(f"  seed            : {config.seed}")
        self._write("-" * 70)

    def on_step(self, event: MarketEvent, equity: str) -> None:
        self._steps += 1
        if not self._show_steps or self._steps % self._step_every:
            return
        self._write(f"  bar {self._steps:>5} | {event.event_time} | equity {equity}")

    def on_session_end(
        self,
        session: SimulationSession,
        metrics: PerformanceMetrics,
        trades: List[TradeRecord],
    ) -> None:
        self._write("-" * 70)
        self._write("  RESULTS")
        self._write("-" * 70)
        self._write(f"  starting equity   : {metrics.starting_equity:.2f}")
        self._write(f"  final equity      : {metrics.final_equity:.2f}")
        self._write(
            f"  total return      : {metrics.total_return:.2f} "
            f"({metrics.total_return_percent:.2f}%)"
        )
        self._write(f"  fees paid         : {metrics.total_fees:.4f}")
        self._write("")
        self._write(
            f"  max drawdown      : {metrics.max_drawdown:.2f} "
            f"({metrics.max_drawdown_percent:.2f}%)"
        )
        self._write(f"  volatility        : {_show(metrics.volatility, 6)}")
        self._write(f"  sharpe            : {_show(metrics.sharpe)}")
        self._write(f"  recovery factor   : {_show(metrics.recovery_factor)}")
        self._write("")
        self._write(f"  trades            : {metrics.trade_count}")
        self._write(f"  wins / losses     : {metrics.win_count} / {metrics.loss_count}")
        self._write(f"  hit rate          : {_show(metrics.hit_rate)}")
        self._write(f"  profit factor     : {_show(metrics.profit_factor)}")
        self._write(f"  expectancy        : {_show(metrics.expectancy)}")
        self._write(f"  average win       : {_show(metrics.average_win)}")
        self._write(f"  average loss      : {_show(metrics.average_loss)}")
        self._write("=" * 70)
        self._write()
