"""فاز ۶۵ — نقاط انتخاب مدل سیگنال روی ریپلی.

خواستهٔ اپراتور: توی ریپلی ببینیم مدل سیگنال کجاها «انتخاب» کرده
(BUY/SELL مجزا با رنگ)، حتی وقتی براکت/گیت بعدی معامله را رد می‌کند.

قفل‌ها:
1. ``SignalMarker`` اعتبارسنجی + with_outcome (بدون جهش state)
2. recorder: record → resolve → build؛ candidate خالی = candidate می‌ماند
3. resolution: candidate هم‌جهت با entry واقعی → filled؛ دو candidate
   هرگز یک entry را شریک نمی‌شوند
4. tape.to_dict شامل signal_points است (خوراک رندرر)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.simulation.replay import (
    SIGNAL_CANDIDATE,
    SIGNAL_FILLED,
    SIGNAL_REJECTED,
    ReplayRecorder,
    SignalMarker,
    TradeMarker,
)


def _marker(bar: int, side: str = "buy") -> TradeMarker:
    return TradeMarker(
        bar_index=bar,
        timestamp=f"t{bar}",
        side=side,
        kind="entry",
        price=Decimal("2000"),
        quantity=Decimal("0.01"),
        position_after=Decimal("0.01"),
    )


def _bar_kwargs(index: int) -> dict:
    b = _bar(index)
    return dict(
        index=index,
        timestamp=f"t{index}",
        open_price=b.open,
        high=b.high,
        low=b.low,
        close=b.close,
        volume=b.volume,
        equity=b.equity,
        cash=b.cash,
        position=b.position,
    )


def _bar(index: int):
    from ShadBotTrader.domain.simulation.replay import ReplayBar

    return ReplayBar(
        index=index,
        timestamp=f"t{index}",
        open_price=Decimal("2000"),
        high=Decimal("2001"),
        low=Decimal("1999"),
        close=Decimal("2000.5"),
        volume=Decimal("10"),
        equity=Decimal("100"),
        cash=Decimal("100"),
        position=Decimal("0"),
    )


def test_signal_marker_validation():
    with pytest.raises(ValidationError):
        SignalMarker(bar_index=-1, timestamp="t", side="buy", confidence=0.7)
    with pytest.raises(ValidationError):
        SignalMarker(bar_index=0, timestamp="t", side="hold", confidence=0.7)
    with pytest.raises(ValidationError):
        SignalMarker(bar_index=0, timestamp="t", side="buy", confidence=1.5)
    with pytest.raises(ValidationError):
        SignalMarker(bar_index=0, timestamp="t", side="buy", confidence=0.7, outcome="x")


def test_with_outcome_does_not_mutate_original():
    point = SignalMarker(3, "t3", "sell", 0.81)
    resolved = point.with_outcome(SIGNAL_REJECTED, "bracket rejected")
    assert point.outcome == SIGNAL_CANDIDATE and point.reason == ""
    assert resolved.outcome == SIGNAL_REJECTED and resolved.reason == "bracket rejected"


def test_recorder_resolution_pairs_candidate_with_following_entry():
    recorder = ReplayRecorder("s", "XAUUSD", "5M", Decimal("100"))
    recorder.record_signal(10, "t10", "buy", 0.83)  # بعداً پر می‌شود
    recorder.record_signal(40, "t40", "sell", 0.66, SIGNAL_REJECTED, "no range")
    recorder.record_signal(70, "t70", "buy", 0.71)  # candidate بدون entry → می‌ماند
    recorder.mark(_marker(11, "buy"))  # entry بعد از سیگنال اول
    recorder.record_bar(**_bar_kwargs(11))
    recorder.record_bar(**_bar_kwargs(41))
    recorder.record_bar(**_bar_kwargs(71))

    tape = recorder.build()
    points = {p.bar_index: p for p in tape.signal_points}

    assert points[10].outcome == SIGNAL_FILLED
    assert points[40].outcome == SIGNAL_REJECTED and "no range" in points[40].reason
    assert points[70].outcome == SIGNAL_CANDIDATE
    assert points[10].confidence == 0.83 and points[10].side == "buy"


def test_two_candidates_do_not_share_one_entry():
    recorder = ReplayRecorder("s", "XAUUSD", "5M", Decimal("100"))
    recorder.record_signal(10, "t10", "buy", 0.9)
    recorder.record_signal(20, "t20", "buy", 0.8)
    recorder.mark(_marker(21, "buy"))  # فقط یک entry
    recorder.record_bar(**_bar_kwargs(21))

    tape = recorder.build()
    filled = [p for p in tape.signal_points if p.outcome == SIGNAL_FILLED]
    assert len(filled) == 1 and filled[0].bar_index == 20  # نزدیک‌ترین قبضه می‌کند


def test_levels_survive_resolution_and_payload():
    """فاز ۶۶: TP/SL مدل ثبت، حفظ و در payload می‌آید؛ override هم کار می‌کند."""
    recorder = ReplayRecorder("s", "XAUUSD", "5M", Decimal("100"))
    recorder.record_signal(
        10,
        "t10",
        "buy",
        0.83,
        take_profit=2043.23,
        stop_loss=1893.11,
    )
    # override واقعی براکت بعد از fill (next-open)
    recorder.resolve_signal(
        10,
        "buy",
        SIGNAL_FILLED,
        "entry @ 2001.5",
        take_profit=2043.23,
        stop_loss=1892.05,
    )
    recorder.mark(_marker(11, "buy"))
    recorder.record_bar(**_bar_kwargs(11))

    tape = recorder.build()
    point = tape.signal_points[0]
    assert point.outcome == SIGNAL_FILLED
    assert point.take_profit == 2043.23
    assert point.stop_loss == 1892.05  # نسخهٔ براکت، نه مدل خام

    payload = tape.to_dict()["signal_points"][0]
    assert payload["tp"] == 2043.23 and payload["sl"] == 1892.05


def test_level_validation_rejects_non_positive():
    with pytest.raises(ValidationError):
        SignalMarker(0, "t", "buy", 0.7, take_profit=0)
    with pytest.raises(ValidationError):
        SignalMarker(0, "t", "buy", 0.7, stop_loss=-5)


def test_tape_payload_exposes_signal_points_for_the_renderer():
    recorder = ReplayRecorder("s", "XAUUSD", "5M", Decimal("100"))
    recorder.record_signal(5, "t5", "sell", 0.64, SIGNAL_REJECTED, "session filter")
    recorder.record_bar(**_bar_kwargs(5))
    payload = recorder.build().to_dict()

    assert "signal_points" in payload
    assert payload["signal_points"] == [
        {
            "bar": 5,
            "time": "t5",
            "side": "sell",
            "conf": 0.64,
            "outcome": "rejected",
            "reason": "session filter",
            "tp": None,
            "sl": None,
        }
    ]
