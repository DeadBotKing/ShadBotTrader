"""Phase130A: backtest a trained telemetry TSMixer meta-filter."""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from backtest_hybrid_telemetry_wavenet import (
    DECISION_MODES,
    backtest,
    default_flat_path,
    eval_indices,
    load_wavenet_artifact,
    normalize_with_payload,
    resolve_thresholds,
    rule,
    write_csv,
)
from report_hybrid_full_backtest import (
    account_summary,
    load_candles,
    monthly_summary,
    render_html,
    replay_candles_for_indices,
)
from train_hybrid_telemetry_wavenet import default_tensor_path, load_tensor, prediction_arrays

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_telemetry_tsmixer_backtest")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest Phase130 telemetry TSMixer meta-filter.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_telemetry_tsmixer_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--decision-mode", choices=DECISION_MODES, default="meta")
    parser.add_argument("--meta-threshold", type=float, default=-1.0)
    parser.add_argument("--score-threshold", type=float, default=0.0)
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-4h-room", type=float, default=2.0)
    parser.add_argument("--min-1d-room", type=float, default=5.0)
    parser.add_argument("--min-tp-distance", type=float, default=2.0)
    parser.add_argument("--min-sl-distance", type=float, default=2.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Telemetry TSMixer filtered hybrid replay")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(storage_root, args.symbol, args.timeframe)
    )
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE130 TELEMETRY TSMIXER BACKTEST")
        print(f"  tensor      : {tensor_path}")
        print(f"  flat        : {flat_path}")
        model, payload, version = load_wavenet_artifact(
            storage_root, args.model_id, args.model_version
        )
        task = str(payload.get("task", "multihead"))
        thresholds = resolve_thresholds(args, payload, args.model_id, version)
        data = load_tensor(tensor_path)
        indices = eval_indices(len(data["X"]), args.eval_frac, args.max_windows)
        x_values = normalize_with_payload(np.asarray(data["X"], dtype=np.float32)[indices], payload)
        win_scores, score_scores = prediction_arrays(model, x_values, task)
        if task == "regressor":
            win_scores = np.ones_like(score_scores, dtype=np.float64)
        candidate_mask = np.asarray(
            data.get("candidate_mask", np.ones(len(data["X"]))), dtype=np.float32
        )[indices]
        source_indices = np.asarray(data["source_index"], dtype=np.int64)[indices]
        flat = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        flat_by_source = {int(row["source_index"]): row for _, row in flat.iterrows()}
        summary, counters, trades = backtest(
            source_indices, candidate_mask, win_scores, score_scores, flat_by_source, thresholds
        )
        account = account_summary(summary, args.initial_capital, args.units)
        monthly = monthly_summary(trades)
        candles = load_candles(storage_root, args.symbol, args.timeframe)
        candle_rows = replay_candles_for_indices(candles, source_indices.tolist(), trades)

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        html_path = out_dir / "latest.html"
        write_csv(csv_path, trades)
        html_path.write_text(
            render_html(
                args.report_title,
                args,
                tensor_path,
                version,
                thresholds,
                summary,
                trades,
                monthly,
                candle_rows,
            ),
            encoding="utf-8",
        )
        files = {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)}
        json_path.write_text(
            json.dumps(
                {
                    "args": vars(args),
                    "model_version": version,
                    "task": task,
                    "rows": int(len(data["X"])),
                    "evaluated_rows": int(len(indices)),
                    "thresholds": asdict(thresholds),
                    "summary": asdict(summary),
                    "tsmixer_counters": asdict(counters),
                    "account": account,
                    "monthly": [asdict(row) for row in monthly],
                    "files": files,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        rule("DONE")
        print(f"  rows        : {summary.samples:,}/{len(data['X']):,}")
        print(f"  trades      : {summary.trades:,} ({summary.coverage:.2%})")
        print(f"  skipped nn  : {counters.skipped_by_wavenet:,}")
        print(f"  total pnl   : {summary.total_pnl:+.2f}")
        print(f"  profit fact.: {summary.profit_factor:.3f}")
        print(f"  final       : ${account['final_balance']:.2f}")
        print(f"  report      : {json_path}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
