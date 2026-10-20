"""Terminal replay of a recorded backtest (Phase 16, section 23).

The same tape the HTML player animates, printed to a console — useful over
SSH, in CI logs, or when the point is to read what happened rather than
watch it. Each bar is drawn as one line: a mini candle glyph, the price,
the model's prediction, the position held, and the equity. Fills are
annotated on the bar they happened on, and a closed trade prints its
result immediately underneath.

Nothing is recomputed here. Every number was produced by the engine.
"""

from __future__ import annotations

import sys
import time
from decimal import Decimal
from typing import List, Optional, Sequence, TextIO

from ShadBotTrader.domain.simulation.replay import (
    MARKER_ENTRY,
    MARKER_EXIT,
    ReplayBar,
    ReplayTape,
    TradeMarker,
)

#: Vertical eighths, used to place the candle body inside the price range.
_BLOCKS = "▁▂▃▄▅▆▇█"


def _sparkline(bar: ReplayBar, low: Decimal, high: Decimal, width: int = 12) -> str:
    """Place the bar's close inside the run's price range as a bar glyph."""
    if high <= low:
        return _BLOCKS[0] * 1
    ratio = (bar.close - low) / (high - low)
    slot = int(ratio * (width - 1))
    body = ["·"] * width
    body[max(0, min(width - 1, slot))] = "▮" if bar.close >= bar.open else "▯"
    return "".join(body)


def _marker_text(marker: TradeMarker) -> str:
    if marker.kind == MARKER_ENTRY:
        arrow = "BUY " if marker.side == "buy" else "SELL"
        return f"OPEN  {arrow} {marker.quantity} @ {marker.price:.2f}"
    if marker.kind == MARKER_EXIT:
        net = marker.net_pnl
        verdict = "WIN " if (net is not None and net > 0) else "LOSS"
        return f"CLOSE {marker.side.upper():<4} {marker.quantity} @ {marker.price:.2f}" + (
            f"  ->  {verdict} net {net:+.4f}" if net is not None else ""
        )
    return f"ADJUST {marker.side.upper()} {marker.quantity} @ {marker.price:.2f}"


class ConsoleReplayPlayer:
    """Prints a replay tape bar by bar, optionally in real time."""

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        delay: float = 0.0,
        show_all_bars: bool = False,
        every: int = 10,
    ) -> None:
        """``show_all_bars`` prints every bar; otherwise only every ``every``
        bar plus every bar that traded, which keeps a 5,000-bar run readable.
        """
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self._delay = max(delay, 0.0)
        self._show_all = show_all_bars
        self._every = max(every, 1)

    def _write(self, text: str = "") -> None:
        self._stream.write(text + "\n")
        self._stream.flush()

    def play(self, tape: ReplayTape) -> None:
        """Walk the tape from the first bar to the last."""
        bars: Sequence[ReplayBar] = tape.bars
        if not bars:
            self._write("The tape is empty — no bars were recorded.")
            return

        low = min(bar.low for bar in bars)
        high = max(bar.high for bar in bars)

        self._write("=" * 96)
        self._write(f"  REPLAY  {tape.symbol} {tape.timeframe}   session {tape.session_id}")
        self._write(
            f"  {len(bars)} bars · starting equity {tape.starting_equity} · "
            f"price range {low:.2f} - {high:.2f}"
        )
        self._write("=" * 96)
        self._write(
            f"{'bar':>5}  {'time':<19} {'chart':<12} {'close':>10} "
            f"{'pred':>7} {'pos':>7} {'equity':>10}"
        )
        self._write("-" * 96)

        closed = 0
        for bar in bars:
            traded = bool(bar.markers)
            visible = self._show_all or traded or bar.index % self._every == 0
            if visible:
                prediction = "warmup" if bar.prediction is None else f"{bar.prediction:.4f}"
                position = f"{bar.position:+.2f}" if bar.position else "flat"
                self._write(
                    f"{bar.index:>5}  {bar.timestamp[:19]:<19} "
                    f"{_sparkline(bar, low, high):<12} {bar.close:>10.2f} "
                    f"{prediction:>7} {position:>7} {bar.equity:>10.4f}"
                )
            for marker in bar.markers:
                if marker.kind == MARKER_EXIT:
                    closed += 1
                self._write(" " * 24 + f"| {_marker_text(marker)}")
            if visible and self._delay:
                time.sleep(self._delay)

        self._summarise(tape, closed)

    def _summarise(self, tape: ReplayTape, closed: int) -> None:
        trips = tape.round_trips()
        wins = [trip for trip in trips if trip["result"] == "win"]
        losses = [trip for trip in trips if trip["result"] == "loss"]

        self._write("-" * 96)
        self._write("  TRADES")
        self._write("-" * 96)
        if not trips:
            self._write("  No round trip completed — nothing was opened and closed.")
        else:
            header = (
                f"  {'#':>3} {'side':<6} {'entry bar':>9} {'entry':>10} "
                f"{'exit bar':>9} {'exit':>10} {'bars':>5} {'net':>11}  result"
            )
            self._write(header)
            for number, trip in enumerate(trips, start=1):
                net = trip["net_pnl"]
                self._write(
                    f"  {number:>3} {trip['direction']:<6} {trip['entry_bar']:>9} "
                    f"{trip['entry_price']:>10.2f} {trip['exit_bar']:>9} "
                    f"{trip['exit_price']:>10.2f} {trip['bars_held']:>5} "
                    f"{net:>+11.4f}  {trip['result'].upper()}"
                )

        still_open = tape.open_position_at_end()
        if still_open is not None:
            self._write(
                f"\n  Still open at the end: {still_open['direction']} "
                f"{still_open['quantity']} @ {still_open['entry_price']:.2f} "
                f"(bar #{still_open['entry_bar']}) — no result yet, not counted."
            )

        final = tape.final_equity
        self._write("-" * 96)
        self._write(f"  closed trades : {len(trips)}  ({len(wins)} win / {len(losses)} loss)")
        if final is not None:
            change = final - tape.starting_equity
            self._write(f"  equity        : {tape.starting_equity} -> {final:.4f} ({change:+.4f})")
        self._write("=" * 96)


def summarise_tape(tape: ReplayTape) -> List[str]:
    """A few plain lines describing the tape, for embedding in reports."""
    trips = tape.round_trips()
    wins = sum(1 for trip in trips if trip["result"] == "win")
    lines = [
        f"bars recorded : {len(tape.bars)}",
        f"fills         : {len(tape.markers)}",
        f"closed trades : {len(trips)} ({wins} win / {len(trips) - wins} loss)",
    ]
    final = tape.final_equity
    if final is not None:
        lines.append(f"equity        : {tape.starting_equity} -> {final:.4f}")
    return lines
