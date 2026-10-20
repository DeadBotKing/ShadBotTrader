"""Unit tests for the replay tape (Phase 16, sections 22-23).

The tape is a *recording*: it must report what happened, and must not
invent a result for a trade that has not produced one yet.
"""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.simulation.replay import (
    MARKER_ADJUST,
    MARKER_ENTRY,
    MARKER_EXIT,
    ReplayRecorder,
    TradeMarker,
)


def d(value: str) -> Decimal:
    return Decimal(value)


def marker(
    bar: int,
    side: str,
    kind: str,
    price: str,
    quantity: str = "1",
    position_after: str = "0",
    realized: str | None = None,
    fees: str = "0",
) -> TradeMarker:
    return TradeMarker(
        bar_index=bar,
        timestamp=f"2026-01-01T00:{bar:02d}:00+00:00",
        side=side,
        kind=kind,
        price=d(price),
        quantity=d(quantity),
        position_after=d(position_after),
        realized_pnl=None if realized is None else d(realized),
        fees=d(fees),
    )


def recorder(equity: str = "100") -> ReplayRecorder:
    return ReplayRecorder("s1", "XAUUSD_i", "5M", d(equity))


def record(rec: ReplayRecorder, index: int, close: str, equity: str, position: str = "0"):
    return rec.record_bar(
        index=index,
        timestamp=f"2026-01-01T00:{index:02d}:00+00:00",
        open_price=d(close),
        high=d(close),
        low=d(close),
        close=d(close),
        volume=d("10"),
        equity=d(equity),
        cash=d(equity),
        position=d(position),
        prediction=None,
    )


# ------------------------------------------------------------- markers ---
def test_marker_rejects_a_kind_it_does_not_know():
    with pytest.raises(ValidationError):
        marker(0, "buy", "teleport", "2000")


def test_marker_rejects_a_non_positive_quantity():
    with pytest.raises(ValidationError):
        marker(0, "buy", MARKER_ENTRY, "2000", quantity="0")


def test_an_entry_has_no_result_yet():
    """An open position has produced nothing; zero would be a lie."""
    entry = marker(0, "buy", MARKER_ENTRY, "2000")
    assert entry.realized_pnl is None
    assert entry.net_pnl is None


def test_net_pnl_subtracts_the_fees_of_the_closing_fill():
    exit_marker = marker(3, "sell", MARKER_EXIT, "2010", realized="10", fees="0.25")
    assert exit_marker.net_pnl == d("9.75")


# --------------------------------------------------------------- tape ---
def test_recorder_attaches_pending_marks_to_the_bar_being_recorded():
    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="1"))
    bar = record(rec, 0, "2000", "100", position="1")

    assert len(bar.markers) == 1
    # the mark must not leak into the next bar
    second = record(rec, 1, "2001", "101")
    assert second.markers == ()


def test_round_trip_pairs_the_entry_with_its_exit():
    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="1"))
    record(rec, 0, "2000", "100", position="1")
    record(rec, 1, "2005", "105", position="1")
    rec.mark(marker(2, "sell", MARKER_EXIT, "2010", realized="10", fees="0.5"))
    record(rec, 2, "2010", "109.5")

    trips = rec.build().round_trips()

    assert len(trips) == 1
    trip = trips[0]
    assert trip["direction"] == "long"
    assert trip["entry_bar"] == 0
    assert trip["exit_bar"] == 2
    assert trip["bars_held"] == 2
    assert trip["net_pnl"] == pytest.approx(9.5)
    assert trip["result"] == "win"


def test_round_trip_net_pnl_includes_entry_and_exit_fees():
    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="1", fees="0.5"))
    record(rec, 0, "2000", "100", position="1")
    rec.mark(marker(1, "sell", MARKER_EXIT, "2010", realized="10", fees="0.5"))
    record(rec, 1, "2010", "109")

    trip = rec.build().round_trips()[0]

    assert trip["fees"] == pytest.approx(1.0)
    assert trip["entry_fees"] == pytest.approx(0.5)
    assert trip["exit_fees"] == pytest.approx(0.5)
    assert trip["net_pnl"] == pytest.approx(9.0)


def test_round_trip_preserves_bracket_levels_for_audit():
    levels = {"take_profit": "2010", "stop_loss": "1990", "model_high": "2010"}
    # Metadata is attached at construction to mirror the engine's entry
    # marker. The small test helper has no metadata argument.
    rec = recorder()
    rec.mark(
        TradeMarker(
            bar_index=0,
            timestamp="2026-01-01T00:00:00+00:00",
            side="buy",
            kind=MARKER_ENTRY,
            price=d("2000"),
            quantity=d("1"),
            position_after=d("1"),
            metadata=levels,
        )
    )
    record(rec, 0, "2000", "100", position="1")
    rec.mark(marker(1, "sell", MARKER_EXIT, "2010", realized="10"))
    record(rec, 1, "2010", "110")

    trip = rec.build().round_trips()[0]

    assert trip["bracket"] == levels


def test_a_losing_round_trip_is_reported_as_a_loss():
    rec = recorder()
    rec.mark(marker(0, "sell", MARKER_ENTRY, "2000", position_after="-1"))
    record(rec, 0, "2000", "100", position="-1")
    rec.mark(marker(1, "buy", MARKER_EXIT, "2010", realized="-10", fees="0.5"))
    record(rec, 1, "2010", "89.5")

    trip = rec.build().round_trips()[0]

    assert trip["direction"] == "short"
    assert trip["result"] == "loss"
    assert trip["net_pnl"] == pytest.approx(-10.5)


def test_a_position_left_open_produces_no_round_trip():
    """It has no result yet — counting it would fabricate one."""
    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="1"))
    record(rec, 0, "2000", "100", position="1")
    record(rec, 1, "2005", "105", position="1")

    tape = rec.build()

    assert tape.round_trips() == []
    still_open = tape.open_position_at_end()
    assert still_open is not None
    assert still_open["direction"] == "long"
    assert still_open["entry_bar"] == 0


def test_no_open_position_is_reported_when_the_run_ended_flat():
    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="1"))
    record(rec, 0, "2000", "100", position="1")
    rec.mark(marker(1, "sell", MARKER_EXIT, "2010", realized="10"))
    record(rec, 1, "2010", "110", position="0")

    assert rec.build().open_position_at_end() is None


def test_closing_markers_are_the_ones_carrying_a_result():
    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="2"))
    record(rec, 0, "2000", "100", position="2")
    rec.mark(marker(1, "sell", MARKER_ADJUST, "2010", realized="5", position_after="1"))
    record(rec, 1, "2010", "105", position="1")
    rec.mark(marker(2, "sell", MARKER_EXIT, "2020", realized="10"))
    record(rec, 2, "2020", "115")

    tape = rec.build()

    assert len(tape.markers) == 3
    assert len(tape.closing_markers) == 1
    assert tape.closing_markers[0].kind == MARKER_EXIT


def test_an_empty_tape_says_so_instead_of_guessing():
    tape = recorder().build()

    assert tape.is_empty
    assert tape.final_equity is None
    assert tape.round_trips() == []
    assert tape.open_position_at_end() is None


def test_to_dict_is_json_serialisable_and_keeps_undefined_values_null():
    import json

    rec = recorder()
    rec.mark(marker(0, "buy", MARKER_ENTRY, "2000", position_after="1"))
    record(rec, 0, "2000", "100", position="1")

    payload = json.loads(json.dumps(rec.build().to_dict()))

    assert payload["bar_count"] == 1
    assert payload["markers"][0]["realized_pnl"] is None
    assert payload["bars"][0]["p"] is None
