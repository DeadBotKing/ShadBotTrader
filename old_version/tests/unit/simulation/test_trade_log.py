"""Per-trade model-decision audit log tests."""

from decimal import Decimal

from ShadBotTrader.domain.simulation.replay import (
    MARKER_ENTRY,
    MARKER_EXIT,
    ReplayRecorder,
    TradeMarker,
)
from ShadBotTrader.infrastructure.simulation.trade_log import trade_log_rows, write_trade_log


def marker(bar, side, kind, price, position, realized=None, fees="0", metadata=None):
    return TradeMarker(
        bar_index=bar,
        timestamp=f"2026-01-01T00:{bar:02d}:00+00:00",
        side=side,
        kind=kind,
        price=Decimal(str(price)),
        quantity=Decimal("0.01"),
        position_after=Decimal(str(position)),
        realized_pnl=None if realized is None else Decimal(str(realized)),
        fees=Decimal(str(fees)),
        metadata=metadata,
    )


def record(rec, index, price, position):
    return rec.record_bar(
        index=index,
        timestamp=f"2026-01-01T00:{index:02d}:00+00:00",
        open_price=Decimal(str(price)),
        high=Decimal(str(price)),
        low=Decimal(str(price)),
        close=Decimal(str(price)),
        volume=Decimal("10"),
        equity=Decimal("100"),
        cash=Decimal("100"),
        position=Decimal(str(position)),
    )


def tape_with_model_decision():
    rec = ReplayRecorder("run-1", "XAUUSD", "5M", Decimal("100"))
    metadata = {
        "signal_class": "buy",
        "sell_probability": 0.08,
        "buy_probability": 0.92,
        "confidence": 0.92,
        "directional_confidence": 0.92,
        "signal_timeframe": "5M",
        "range_reference_close": 4000.0,
        "predicted_high": 4012.0,
        "predicted_low": 3994.0,
        "range_high_offset": 0.003,
        "range_low_offset": -0.0015,
        "range_horizon": 5,
        "range_timeframe": "1H",
        "reward_risk": 1.5,
        "move_fraction": 0.003,
        "entry_reference": 4001.0,
        "take_profit": 4012.0,
        "stop_loss": 3994.0,
        "model_high": 4012.0,
        "model_low": 3994.0,
        "model_reference": 4000.0,
    }
    rec.mark(
        marker(
            0,
            "buy",
            MARKER_ENTRY,
            4001.0,
            0.01,
            metadata=metadata,
            fees="0.004001",
        )
    )
    record(rec, 0, 4001.0, 0.01)
    rec.mark(
        marker(
            1,
            "sell",
            MARKER_EXIT,
            4012.0,
            0,
            realized="0.11",
            fees="0.004012",
            metadata={"bracket_exit_reason": "take_profit"},
        )
    )
    record(rec, 1, 4012.0, 0)
    return rec.build()


def test_trade_log_contains_signal_probabilities_and_bracket_levels():
    rows = trade_log_rows(
        tape_with_model_decision(),
        {"engine": "dual", "spread": 0.04, "commission_rate": 0.0001, "quantity": 0.01},
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["signal_class"] == "buy"
    assert row["sell_probability"] == 0.08
    assert row["buy_probability"] == 0.92
    assert row["predicted_high"] == 4012.0
    assert row["predicted_low"] == 3994.0
    assert row["take_profit"] == 4012.0
    assert row["stop_loss"] == 3994.0
    assert row["exit_reason"] == "take_profit"
    assert row["entry_fees"] == 0.004001
    assert row["exit_fees"] == 0.004012


def test_trade_log_is_written_as_a_reviewable_csv(tmp_path):
    path = write_trade_log(tape_with_model_decision(), tmp_path / "trades.csv")
    text = path.read_text(encoding="utf-8")

    assert "sell_probability" in text.splitlines()[0]
    assert "buy_probability" in text.splitlines()[0]
    assert "take_profit" in text.splitlines()[0]
    assert "0.92" in text
