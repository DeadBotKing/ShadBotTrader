"""Phase 126A chronological single-position hybrid replay/backtest.

The Phase 125/116 research backtests scored every eligible signal row as an
independent trade. This script is closer to an account replay: it walks forward
chronologically, keeps at most one position open, skips new entries while that
position is open, and records the same HTML candle replay with entry/TP/SL/exit
markers and account-balance diagnostics.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from backtest_hybrid_xgboost_head import (
    TradeResult,
    aligned_predict_proba,
    decide_action,
    default_matrix_path,
    eval_slice_indices,
    load_candles,
    load_head,
    range_filter_pass,
    safe_div,
    simulate_trade,
)
from report_hybrid_full_backtest import (
    DetailedTrade,
    FixedBacktestSummary,
    ThresholdSpec,
    account_summary,
    build_stream_chunk,
    load_record,
    monthly_summary,
    render_html,
    replay_candles_for_indices,
    resolve_thresholds,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_chronological_backtest")


@dataclass(frozen=True)
class ChronologicalCounters:
    """Non-trade reasons in the single-position replay."""

    no_trade_probability: int
    skipped_while_open: int
    ambiguous: int
    invalid_range: int
    invalid_bracket: int

    @property
    def no_trade(self) -> int:
        return (
            self.no_trade_probability
            + self.skipped_while_open
            + self.ambiguous
            + self.invalid_range
            + self.invalid_bracket
        )


@dataclass(frozen=True)
class ChronologicalResult:
    summary: FixedBacktestSummary
    counters: ChronologicalCounters
    trades: list[DetailedTrade]
    raw_trades: list[TradeResult]
    source_indices: list[int]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chronological single-position replay for the hybrid range-aware model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument(
        "--source-mode",
        choices=("matrix", "stream"),
        default="stream",
        help="matrix = replay an existing hybrid matrix; stream = build/evaluate rows in chunks.",
    )
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0, help="0 = all selected rows")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument(
        "--stream-scope",
        choices=("all", "holdout", "last-fold", "auto"),
        default="all",
    )
    parser.add_argument("--stream-chunk-size", type=int, default=500)
    parser.add_argument(
        "--stream-wavenet",
        choices=("neutral", "batch"),
        default="neutral",
        help="neutral avoids the RAM spike from one huge WaveNet tensor.",
    )
    parser.add_argument("--booster", default="lightgbm")
    parser.add_argument("--summary-mode", default="basic")
    parser.add_argument("--include-specialists", choices=("0", "1"), default="1")
    parser.add_argument("--include-multiclass-booster", choices=("0", "1"), default="1")
    parser.add_argument("--include-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--require-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--buy-model-id", default="")
    parser.add_argument("--sell-model-id", default="")
    parser.add_argument("--multiclass-model-id", default="")
    parser.add_argument("--wavenet-model-id", default="gold_trend_signal_5m")
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--buy-model-version", type=int, default=0)
    parser.add_argument("--sell-model-version", type=int, default=0)
    parser.add_argument("--multiclass-model-version", type=int, default=0)
    parser.add_argument("--wavenet-model-version", type=int, default=0)
    parser.add_argument("--range-1d-version", type=int, default=0)
    parser.add_argument("--range-4h-version", type=int, default=0)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-4h-room", type=float, default=2.0)
    parser.add_argument("--min-1d-room", type=float, default=5.0)
    parser.add_argument("--min-tp-distance", type=float, default=2.0)
    parser.add_argument("--min-sl-distance", type=float, default=2.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument(
        "--units",
        type=float,
        default=0.1,
        help="Cash PnL multiplier; 0.1 means one XAUUSD price-dollar move = $0.10 PnL.",
    )
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Chronological hybrid single-position replay")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def summarise_chronological(
    samples: int,
    raw_trades: Sequence[TradeResult],
    counters: ChronologicalCounters,
) -> FixedBacktestSummary:
    pnls = [trade.pnl for trade in raw_trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in raw_trades if trade.pnl > 0)
    losses = sum(1 for trade in raw_trades if trade.pnl < 0)
    label_correct = sum(1 for trade in raw_trades if trade.label_correct)
    total = sum(pnls)
    return FixedBacktestSummary(
        samples=samples,
        trades=len(raw_trades),
        buy_trades=sum(1 for trade in raw_trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in raw_trades if trade.side == "SELL"),
        wins=wins,
        losses=losses,
        timeouts=sum(1 for trade in raw_trades if trade.outcome == "timeout"),
        label_correct=label_correct,
        false_positive=len(raw_trades) - label_correct,
        no_trade=max(samples - len(raw_trades), counters.no_trade),
        ambiguous=counters.ambiguous,
        invalid_range=counters.invalid_range,
        invalid_bracket=counters.invalid_bracket,
        win_rate=safe_div(wins, len(raw_trades)),
        label_precision=safe_div(label_correct, len(raw_trades)),
        total_pnl=total,
        avg_pnl=safe_div(total, len(raw_trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=_max_drawdown(pnls),
        coverage=safe_div(len(raw_trades), samples),
    )


def _max_drawdown(pnls: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def _detail_trade(number: int, timestamp: str, trade: TradeResult, equity: float) -> DetailedTrade:
    from backtest_hybrid_xgboost_head import CLASS_NAMES

    return DetailedTrade(
        number=number,
        timestamp=timestamp,
        side=trade.side,
        row_index=trade.row_index,
        source_index=trade.source_index,
        entry_index=trade.entry_index,
        exit_index=trade.exit_index,
        entry=trade.entry,
        tp=trade.tp,
        sl=trade.sl,
        exit_price=trade.exit_price,
        outcome=trade.outcome,
        pnl=trade.pnl,
        equity=equity,
        label=CLASS_NAMES.get(trade.label, str(trade.label)),
        label_correct=int(trade.label_correct),
    )


def evaluate_frame_chronological(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    candles: Sequence[Any],
    args: argparse.Namespace,
    thresholds: ThresholdSpec,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate rows in chronological order with one position at a time."""

    current = state or {
        "raw_trades": [],
        "detailed": [],
        "equity": 0.0,
        "open_until_index": -1,
        "no_trade_probability": 0,
        "skipped_while_open": 0,
        "ambiguous": 0,
        "invalid_range": 0,
        "invalid_bracket": 0,
        "samples": 0,
    }
    for offset, (_, row) in enumerate(frame.iterrows()):
        current["samples"] += 1
        source_index = int(row["source_index"])
        if source_index <= int(current["open_until_index"]):
            current["skipped_while_open"] += 1
            continue

        decision = decide_action(
            probabilities[offset],
            thresholds.buy_threshold,
            thresholds.sell_threshold,
            thresholds.min_margin,
        )
        if decision == -1:
            current["ambiguous"] += 1
            continue
        if decision is None:
            current["no_trade_probability"] += 1
            continue
        if not range_filter_pass(row, decision, args.min_4h_room, args.min_1d_room):
            current["invalid_range"] += 1
            continue
        trade = simulate_trade(row, decision, candles, args)
        if trade is None:
            current["invalid_bracket"] += 1
            continue

        current["raw_trades"].append(trade)
        current["equity"] += trade.pnl
        current["open_until_index"] = max(int(current["open_until_index"]), trade.exit_index)
        current["detailed"].append(
            _detail_trade(
                len(current["detailed"]) + 1,
                str(row["timestamp"]),
                trade,
                float(current["equity"]),
            )
        )
    return current


def finalise_state(state: dict[str, Any], source_indices: Sequence[int]) -> ChronologicalResult:
    counters = ChronologicalCounters(
        no_trade_probability=int(state["no_trade_probability"]),
        skipped_while_open=int(state["skipped_while_open"]),
        ambiguous=int(state["ambiguous"]),
        invalid_range=int(state["invalid_range"]),
        invalid_bracket=int(state["invalid_bracket"]),
    )
    raw_trades = list(state["raw_trades"])
    summary = summarise_chronological(int(state["samples"]), raw_trades, counters)
    return ChronologicalResult(
        summary=summary,
        counters=counters,
        trades=list(state["detailed"]),
        raw_trades=raw_trades,
        source_indices=list(source_indices),
    )


def select_stream_positions(
    args: argparse.Namespace, dataset: Any, candles_count: int
) -> list[int]:
    from report_hybrid_full_backtest import select_stream_positions as select_positions

    return select_positions(args, dataset, candles_count)


def replay_matrix_mode(
    args: argparse.Namespace,
    model: Any,
    features: Sequence[str],
    thresholds: ThresholdSpec,
    matrix_path: Path,
) -> tuple[ChronologicalResult, Sequence[Any], int, int, Path]:
    full_frame = pd.read_parquet(matrix_path)
    missing = [name for name in features if name not in full_frame.columns]
    if missing:
        raise RuntimeError(f"Hybrid matrix is missing model feature columns: {missing[:5]}")
    indices = eval_slice_indices(len(full_frame), args.eval_frac, args.max_windows)
    frame = full_frame.iloc[indices].copy()
    x_values = (
        frame[list(features)].replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=np.float32)
    )
    probabilities = aligned_predict_proba(model, x_values)
    candles = load_candles(Path(args.storage_root), args.symbol, args.timeframe)
    state = evaluate_frame_chronological(frame, probabilities, candles, args, thresholds)
    source_indices = [int(value) for value in frame["source_index"].tolist()]
    return finalise_state(state, source_indices), candles, len(full_frame), len(frame), matrix_path


def replay_stream_mode(
    args: argparse.Namespace,
    model: Any,
    features: Sequence[str],
    thresholds: ThresholdSpec,
) -> tuple[ChronologicalResult, Sequence[Any], int, int, Path]:
    from build_hybrid_xgboost_matrix import (
        RangeFeatureConfig,
        RangeFeatureProvider,
        prepare_trend_dataset,
    )

    storage_root = Path(args.storage_root)
    signal_candles = load_candles(storage_root, args.symbol, args.timeframe)
    role, dataset = prepare_trend_dataset(args, signal_candles)
    positions = select_stream_positions(args, dataset, len(signal_candles))
    if not positions:
        raise RuntimeError("No stream positions selected for chronological replay")

    range_1d_provider = RangeFeatureProvider(
        storage_root,
        args.symbol,
        RangeFeatureConfig("1d", "1D", args.range_1d_model_id, args.range_1d_version, True),
    )
    range_4h_provider = RangeFeatureProvider(
        storage_root,
        args.symbol,
        RangeFeatureConfig("4h", "4H", args.range_4h_model_id, args.range_4h_version, True),
    )

    state: dict[str, Any] | None = None
    source_indices: list[int] = []
    warnings: list[str] = []
    chunk_size = max(int(args.stream_chunk_size), 50)
    for start in range(0, len(positions), chunk_size):
        chunk_positions = positions[start : start + chunk_size]
        frame = build_stream_chunk(
            args,
            dataset,
            role,
            signal_candles,
            chunk_positions,
            range_1d_provider,
            range_4h_provider,
            features,
            warnings,
        )
        source_indices.extend(int(value) for value in frame["source_index"].tolist())
        x_values = (
            frame[list(features)]
            .replace([np.inf, -np.inf], 0.0)
            .fillna(0.0)
            .to_numpy(dtype=np.float32)
        )
        probabilities = aligned_predict_proba(model, x_values)
        state = evaluate_frame_chronological(
            frame,
            probabilities,
            signal_candles,
            args,
            thresholds,
            state,
        )
        print(
            f"  streamed   : {min(start + chunk_size, len(positions)):,}/{len(positions):,} rows; "
            f"trades={len(state['raw_trades']) if state else 0:,}; "
            f"skipped-open={state['skipped_while_open'] if state else 0:,}"
        )
    for warning in warnings[:10]:
        print(f"  [!] {warning}")
    if state is None:
        raise RuntimeError("Streaming replay did not evaluate any rows")
    label = Path(f"stream_chronological_{args.symbol}_{args.timeframe}_{args.stream_scope}")
    return (
        finalise_state(state, source_indices),
        signal_candles,
        len(positions),
        len(positions),
        label,
    )


def write_trade_csv(path: Path, rows: Sequence[DetailedTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_outputs(
    args: argparse.Namespace,
    result: ChronologicalResult,
    candles: Sequence[Any],
    source_rows: int,
    evaluated_rows: int,
    matrix_label: Path,
    model_version: int,
    thresholds: ThresholdSpec,
) -> dict[str, str]:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "latest.csv"
    json_path = out_dir / "latest.json"
    html_path = out_dir / "latest.html"
    write_trade_csv(csv_path, result.trades)
    monthly = monthly_summary(result.trades)
    account = account_summary(result.summary, args.initial_capital, args.units)
    candle_rows = replay_candles_for_indices(candles, result.source_indices, result.trades)
    html_path.write_text(
        render_html(
            args.report_title,
            args,
            matrix_label,
            model_version,
            thresholds,
            result.summary,
            result.trades,
            monthly,
            candle_rows,
        ),
        encoding="utf-8",
    )
    files = {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)}
    payload = {
        "args": vars(args),
        "model_version": model_version,
        "source_rows": source_rows,
        "evaluated_rows": evaluated_rows,
        "thresholds": asdict(thresholds),
        "summary": asdict(result.summary),
        "chronological": asdict(result.counters),
        "account": account,
        "monthly": [asdict(row) for row in monthly],
        "replay": {
            "candles": len(candle_rows),
            "trades": len(result.trades),
            "html_controls": "single-position candle-by-candle slider with entry/exit/TP/SL markers",
        },
        "files": files,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return files


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    matrix_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else default_matrix_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE 126A CHRONOLOGICAL HYBRID REPLAY")
        print(f"  source mode : {args.source_mode}")
        print(f"  matrix      : {matrix_path}")
        print(f"  model       : {args.model_id}")
        record, version = load_record(storage_root, args.model_id, args.model_version)
        thresholds = resolve_thresholds(args, record)
        print(
            "  thresholds  : "
            f"buy={thresholds.buy_threshold:.3f} "
            f"sell={thresholds.sell_threshold:.3f} "
            f"margin={thresholds.min_margin:.3f} ({thresholds.source})"
        )
        model, features, loaded_version = load_head(storage_root, args.model_id, version)
        if args.source_mode == "stream":
            result, candles, source_rows, evaluated_rows, matrix_label = replay_stream_mode(
                args, model, features, thresholds
            )
        else:
            result, candles, source_rows, evaluated_rows, matrix_label = replay_matrix_mode(
                args, model, features, thresholds, matrix_path
            )
        files = write_outputs(
            args,
            result,
            candles,
            source_rows,
            evaluated_rows,
            matrix_label,
            loaded_version,
            thresholds,
        )
        account = account_summary(result.summary, args.initial_capital, args.units)
        summary = result.summary
        rule("CHRONOLOGICAL SUMMARY")
        print(f"  rows        : {summary.samples:,}/{source_rows:,}")
        print(f"  trades      : {summary.trades:,} ({summary.coverage:.2%})")
        print(f"  skipped open: {result.counters.skipped_while_open:,}")
        print(f"  buy/sell    : {summary.buy_trades:,} / {summary.sell_trades:,}")
        print(f"  win rate    : {summary.win_rate:.2%}")
        print(f"  label prec. : {summary.label_precision:.2%}")
        print(f"  total pnl   : {summary.total_pnl:+.2f}")
        print(f"  avg pnl     : {summary.avg_pnl:+.4f}")
        print(f"  profit fact.: {summary.profit_factor:.3f}")
        print(f"  max DD      : {summary.max_drawdown:.2f}")
        print(
            f"  initial/final: ${account['initial_capital']:.2f} -> ${account['final_balance']:.2f}"
        )
        print(f"  cash max DD : ${account['max_drawdown_cash']:.2f}")
        print(f"  html report : {files['html']}")
        print(f"  json report : {files['json']}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
