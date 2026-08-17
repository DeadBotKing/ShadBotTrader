"""Integration tests: recording a backtest and replaying it (Phase 16 §23).

The recording must describe the *same* run the metrics describe. If the
tape and the metrics ever disagree, the replay is fiction — so these
tests compare them against each other rather than against fixed numbers.
"""

import json
from decimal import Decimal

from ShadBotTrader.application.services.backtest_service import BacktestService
from ShadBotTrader.domain.simulation.replay import MARKER_ENTRY, MARKER_EXIT
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.infrastructure.simulation import (
    ConsoleReplayPlayer,
    MomentumPredictionSource,
    ScriptedPredictionSource,
    summarise_tape,
)
from ShadBotTrader.presentation.web.replay_renderer import render_replay
from tests.simulation_fixtures import TF, XAU, candles_from, rising


def d(value: str) -> Decimal:
    return Decimal(value)


def service(**overrides) -> BacktestService:
    return BacktestService(
        configuration=overrides.pop(
            "configuration",
            SimulationConfiguration(
                initial_capital=d("100000"),
                spread=d("4"),
                commission_rate=d("0.0001"),
                warmup_bars=4,
            ),
        ),
        base_quantity=overrides.pop("base_quantity", d("1")),
        **overrides,
    )


def run(candles, source=None, record=True):
    return service().run(
        "replay-test",
        XAU,
        TF,
        candles,
        prediction_source=source or MomentumPredictionSource(lookback=3),
        record_replay=record,
    )


# ------------------------------------------------------------- recording ---
def test_no_tape_is_produced_unless_recording_was_asked_for():
    """A parameter sweep must not pay for a recording nobody reads."""
    result = run(rising(30), record=False)

    assert result.tape is None


def test_the_tape_has_one_bar_per_processed_event():
    candles = rising(30)
    result = run(candles)

    assert result.tape is not None
    assert len(result.tape.bars) == result.bars_processed == len(candles)


def test_the_tape_records_every_fill_the_engine_reported():
    result = run(rising(40))

    assert result.tape is not None
    assert len(result.tape.markers) == result.fills


def test_tape_equity_matches_the_equity_curve_bar_for_bar():
    result = run(rising(30))
    tape = result.tape

    assert tape is not None
    curve = result.equity_curve.points
    assert [bar.equity for bar in tape.bars] == [point.equity for point in curve]
    assert tape.final_equity == result.metrics.final_equity


def test_completed_round_trips_match_the_reported_trade_count():
    result = run(candles_from([str(2000 + (i % 7) * 6) for i in range(60)]))
    tape = result.tape

    assert tape is not None
    assert len(tape.round_trips()) == result.metrics.trade_count


def test_round_trip_pnl_sums_to_the_realised_result():
    result = run(candles_from([str(2000 + (i % 5) * 8) for i in range(60)]))
    tape = result.tape

    assert tape is not None
    trips = tape.round_trips()
    if not trips:  # nothing closed: nothing to compare, and that is legitimate
        return
    total = sum(Decimal(str(trip["net_pnl"])) for trip in trips)
    reported = sum(trade.net_pnl for trade in result.trades)
    assert total == reported


def test_markers_are_placed_on_the_bar_whose_price_they_traded_at():
    result = run(rising(30))
    tape = result.tape

    assert tape is not None
    for bar in tape.bars:
        for marker in bar.markers:
            assert marker.bar_index == bar.index
            assert marker.timestamp == bar.timestamp


def test_an_entry_marker_carries_no_result_but_an_exit_does():
    """Scripted: buy on bar 5, exit on bar 8 — one clean round trip."""
    source = ScriptedPredictionSource({5: 0.95, 8: 0.05})
    result = run(rising(20), source=source)
    tape = result.tape

    assert tape is not None
    entries = [m for m in tape.markers if m.kind == MARKER_ENTRY]
    exits = [m for m in tape.markers if m.kind == MARKER_EXIT]
    assert entries and exits
    assert all(marker.realized_pnl is None for marker in entries)
    assert all(marker.realized_pnl is not None for marker in exits)


def test_position_on_the_tape_follows_the_ledger():
    source = ScriptedPredictionSource({5: 0.95, 9: 0.05})
    result = run(rising(20), source=source)
    tape = result.tape

    assert tape is not None
    # flat before the entry, exposed after it, flat again after the exit
    assert tape.bars[4].position == 0
    assert tape.bars[6].position != 0
    assert tape.bars[-1].position == 0


def test_recording_does_not_change_the_outcome_of_the_run():
    """The observer must be passive: same data, same seed, same result."""
    candles = candles_from([str(2000 + (i % 6) * 7) for i in range(50)])
    plain = run(candles, record=False)
    recorded = run(candles, record=True)

    assert recorded.metrics.total_return == plain.metrics.total_return
    assert recorded.metrics.trade_count == plain.metrics.trade_count
    assert recorded.fills == plain.fills


def test_the_tape_is_available_while_stepping_through_a_run():
    engine = service().build(
        "stepwise",
        XAU,
        TF,
        rising(20),
        prediction_source=MomentumPredictionSource(lookback=3),
        record_replay=True,
    )
    engine.step()
    engine.step()

    tape = engine.tape
    assert tape is not None
    assert len(tape.bars) == 2


# ---------------------------------------------------------------- output ---
def test_the_html_player_is_self_contained():
    result = run(rising(30))
    tape = result.tape
    assert tape is not None

    markup = render_replay(tape, result.metrics)

    assert markup.startswith("<!DOCTYPE html>")
    assert "http://" not in markup and "https://" not in markup
    assert "<script src=" not in markup
    assert "cdn" not in markup.lower()


def test_the_player_embeds_the_recorded_bars_as_data():
    result = run(rising(30))
    tape = result.tape
    assert tape is not None

    markup = render_replay(tape, result.metrics)
    payload = markup.split("const TAPE = ", 1)[1].split(";\nconst METRICS", 1)[0]
    decoded = json.loads(payload)

    assert decoded["bar_count"] == len(tape.bars)
    assert len(decoded["bars"]) == len(tape.bars)


def test_the_player_survives_a_run_that_never_traded():
    """No trade is a legitimate outcome and must not break the page."""
    result = run(rising(6))  # warmup consumes almost everything
    tape = result.tape
    assert tape is not None

    markup = render_replay(tape, result.metrics)

    assert "No trade closed yet" in markup


def test_the_console_player_prints_bars_and_trades(capsys):
    result = run(candles_from([str(2000 + (i % 5) * 8) for i in range(40)]))
    tape = result.tape
    assert tape is not None

    ConsoleReplayPlayer(show_all_bars=True).play(tape)
    printed = capsys.readouterr().out

    assert "REPLAY" in printed
    assert "TRADES" in printed
    assert str(len(tape.bars)) in printed


def test_summarise_tape_reports_the_recording_in_plain_lines():
    result = run(rising(30))
    tape = result.tape
    assert tape is not None

    lines = summarise_tape(tape)

    assert any("bars recorded" in line for line in lines)
    assert any(str(len(tape.bars)) in line for line in lines)
