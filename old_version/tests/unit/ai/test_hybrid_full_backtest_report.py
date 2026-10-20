"""Phase 116 full hybrid report helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "report_hybrid_full_backtest.py"


def load_script():
    spec = importlib.util.spec_from_file_location("report_hybrid_full_backtest", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_trade(module, side: str, pnl: float, label_correct: bool = True):
    return module.TradeResult(
        side=side,
        row_index=10,
        source_index=20,
        entry_index=21,
        exit_index=22,
        entry=2000.0,
        tp=2010.0 if side == "BUY" else 1990.0,
        sl=1990.0 if side == "BUY" else 2010.0,
        exit_price=2000.0 + pnl if side == "BUY" else 2000.0 - pnl,
        outcome="take_profit" if pnl > 0 else "stop_loss",
        pnl=pnl,
        label=2 if side == "BUY" else 0,
        label_correct=label_correct,
    )


def test_summarise_computes_trading_metrics():
    module = load_script()
    frame = pd.DataFrame({"x": [1, 2, 3]})
    trades = [make_trade(module, "BUY", 10.0), make_trade(module, "SELL", -4.0, False)]

    summary = module.summarise(
        frame,
        trades,
        no_trade=1,
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=0,
    )

    assert summary.trades == 2
    assert summary.buy_trades == 1
    assert summary.sell_trades == 1
    assert summary.total_pnl == pytest.approx(6.0)
    assert summary.profit_factor == pytest.approx(2.5)
    assert summary.label_precision == pytest.approx(0.5)


def test_equity_svg_contains_polyline():
    module = load_script()
    detail = module._detail_trade(1, "2026-09-09T00:00:00Z", make_trade(module, "BUY", 5.0), 5.0)

    svg = module.equity_svg([detail])

    assert "<svg" in svg
    assert "polyline" in svg


def test_render_html_includes_summary_and_warning():
    module = load_script()
    thresholds = module.ThresholdSpec(0.8, 0.65, 0.05, "test")
    summary = module.FixedBacktestSummary(
        samples=10,
        trades=1,
        buy_trades=1,
        sell_trades=0,
        wins=1,
        losses=0,
        timeouts=0,
        label_correct=1,
        false_positive=0,
        no_trade=9,
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=0,
        win_rate=1.0,
        label_precision=1.0,
        total_pnl=5.0,
        avg_pnl=5.0,
        gross_profit=5.0,
        gross_loss=0.0,
        profit_factor=999.0,
        max_drawdown=0.0,
        coverage=0.1,
    )
    args = module.parse_args([])

    rendered = module.render_html(
        "Test report",
        args,
        Path("matrix.parquet"),
        1,
        thresholds,
        summary,
        [],
        [],
    )

    assert "Test report" in rendered
    assert "Total PnL" in rendered
    assert "fixed-threshold" in rendered
    assert "replay-data" in rendered
    assert "&quot;" not in rendered.split('id="replay-data"', 1)[1].split("</script>", 1)[0]
    assert "Replay کندل" in rendered


def test_account_summary_shows_hundred_dollar_breach_risk():
    module = load_script()
    summary = module.FixedBacktestSummary(
        samples=10,
        trades=1,
        buy_trades=1,
        sell_trades=0,
        wins=1,
        losses=0,
        timeouts=0,
        label_correct=1,
        false_positive=0,
        no_trade=9,
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=0,
        win_rate=1.0,
        label_precision=1.0,
        total_pnl=291.15,
        avg_pnl=291.15,
        gross_profit=291.15,
        gross_loss=0.0,
        profit_factor=999.0,
        max_drawdown=347.04,
        coverage=0.1,
    )

    account = module.account_summary(summary, initial_capital=100.0, units=1.0)

    assert account["final_balance"] == pytest.approx(391.15)
    assert account["would_breach_zero"] is True
