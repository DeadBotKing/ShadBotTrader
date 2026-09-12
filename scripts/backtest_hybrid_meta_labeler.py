"""Phase128: backtest a trained hybrid meta-labeler on telemetry targets."""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from report_hybrid_full_backtest import (
    DetailedTrade,
    FixedBacktestSummary,
    account_summary,
    load_candles,
    monthly_summary,
    render_html,
    replay_candles_for_indices,
    safe_div,
)
from train_hybrid_meta_labeler import positive_scores

from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_meta_backtest")


@dataclass(frozen=True)
class MetaThresholdSpec:
    meta_threshold: float
    score_threshold: float
    source: str


@dataclass(frozen=True)
class MetaBacktestCounters:
    skipped_by_meta: int
    skipped_no_candidate: int
    skipped_while_open: int
    missing_outcome: int

    @property
    def no_trade(self) -> int:
        return (
            self.skipped_by_meta
            + self.skipped_no_candidate
            + self.skipped_while_open
            + self.missing_outcome
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest Phase128 meta-filter against hybrid telemetry flat matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--meta-model-id", default="gold_hybrid_meta_lightgbm_5m")
    parser.add_argument("--meta-model-version", type=int, default=0, help="0 = latest")
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
    parser.add_argument("--report-title", default="Meta-filtered hybrid chronological backtest")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def load_meta_model(
    storage_root: Path, model_id: str, version: int
) -> tuple[Any, list[str], str, int]:
    catalogue = ModelCatalogue(storage_root)
    resolved = version if version > 0 else catalogue.latest_version(model_id)
    if resolved < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    artifact = FilesystemArtifactStore(storage_root).load(ModelId(model_id), ModelVersion(resolved))
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{resolved}")
    try:
        payload = pickle.loads(artifact.payload)
    except ModuleNotFoundError as exc:
        raise RuntimeError("Could not load meta model; install requirements-boosters.txt") from exc
    task = str(payload.get("task", "classifier")) if isinstance(payload, Mapping) else "classifier"
    model = payload.get("model") if isinstance(payload, Mapping) else None
    features = payload.get("feature_names") if isinstance(payload, Mapping) else None
    if model is None or not isinstance(features, Sequence) or isinstance(features, str):
        raise RuntimeError("Meta model artifact must contain model and feature_names")
    return model, [str(name) for name in features], task, resolved


def resolve_threshold(args: argparse.Namespace, model_id: str, version: int) -> MetaThresholdSpec:
    if args.meta_threshold >= 0:
        return MetaThresholdSpec(args.meta_threshold, args.score_threshold, "cli")
    record = ModelCatalogue(Path(args.storage_root)).read(model_id, version)
    stored = record.decision_thresholds if record else {}
    value = stored.get("meta_threshold") if stored else None
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        threshold = 0.55
    return MetaThresholdSpec(threshold, args.score_threshold, f"model_record:{model_id}:v{version}")


def trade_from_row(number: int, row: pd.Series, score: float, equity: float) -> DetailedTrade:
    side = "BUY" if float(row.get("target_side", 0.0)) > 0 else "SELL"
    entry = float(row.get("candidate_entry_price", 0.0) or 0.0)
    pnl = float(row.get("target_trade_pnl", 0.0) or 0.0)
    exit_price = entry + pnl if side == "BUY" else entry - pnl
    exit_index = int(row.get("target_exit_index", int(row.get("source_index", 0))) or 0)
    outcome_code = float(row.get("target_outcome_code", 0.0) or 0.0)
    if outcome_code > 0:
        outcome = "take_profit"
    elif outcome_code < 0:
        outcome = "stop_loss"
    else:
        outcome = "timeout"
    return DetailedTrade(
        number=number,
        timestamp=str(row.get("timestamp", "")),
        side=side,
        row_index=int(row.name) if row.name is not None else -1,
        source_index=int(row.get("source_index", -1)),
        entry_index=int(row.get("source_index", -1)) + 1,
        exit_index=exit_index,
        entry=entry,
        tp=float(row.get("candidate_take_profit", 0.0) or 0.0),
        sl=float(row.get("candidate_stop_loss", 0.0) or 0.0),
        exit_price=exit_price,
        outcome=outcome,
        pnl=pnl,
        equity=equity,
        label="win" if float(row.get("target_trade_win", 0.0)) > 0.5 else "loss",
        label_correct=int(float(row.get("target_trade_win", 0.0)) > 0.5),
    )


def summary_from_trades(
    samples: int, trades: Sequence[DetailedTrade], counters: MetaBacktestCounters
) -> FixedBacktestSummary:
    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    return FixedBacktestSummary(
        samples=samples,
        trades=len(trades),
        buy_trades=sum(1 for trade in trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in trades if trade.side == "SELL"),
        wins=wins,
        losses=losses,
        timeouts=sum(1 for trade in trades if trade.outcome == "timeout"),
        label_correct=wins,
        false_positive=losses,
        no_trade=max(samples - len(trades), counters.no_trade),
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=counters.missing_outcome,
        win_rate=safe_div(wins, len(trades)),
        label_precision=safe_div(wins, len(trades)),
        total_pnl=sum(pnls),
        avg_pnl=safe_div(sum(pnls), len(trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=max_drawdown(pnls),
        coverage=safe_div(len(trades), samples),
    )


def max_drawdown(pnls: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def passes_meta_gate(score: float, threshold: MetaThresholdSpec, task: str) -> bool:
    if task == "regressor":
        return score >= threshold.score_threshold
    return score >= threshold.meta_threshold


def backtest(
    frame: pd.DataFrame,
    scores: np.ndarray,
    threshold: MetaThresholdSpec,
    task: str = "classifier",
) -> tuple[FixedBacktestSummary, MetaBacktestCounters, list[DetailedTrade]]:
    trades: list[DetailedTrade] = []
    skipped_by_meta = skipped_no_candidate = skipped_while_open = missing_outcome = 0
    open_until = -1
    equity = 0.0
    for offset, (_, row) in enumerate(frame.iterrows()):
        source_index = int(row.get("source_index", -1))
        if source_index <= open_until:
            skipped_while_open += 1
            continue
        if float(row.get("candidate_mask", 0.0)) < 0.5:
            skipped_no_candidate += 1
            continue
        if not passes_meta_gate(float(scores[offset]), threshold, task):
            skipped_by_meta += 1
            continue
        if "target_exit_index" not in row or int(row.get("target_exit_index", -1)) < 0:
            missing_outcome += 1
            continue
        equity += float(row.get("target_trade_pnl", 0.0) or 0.0)
        trade = trade_from_row(len(trades) + 1, row, float(scores[offset]), equity)
        trades.append(trade)
        open_until = max(open_until, trade.exit_index)
    counters = MetaBacktestCounters(
        skipped_by_meta, skipped_no_candidate, skipped_while_open, missing_outcome
    )
    return summary_from_trades(len(frame), trades, counters), counters, trades


def write_csv(path: Path, rows: Sequence[DetailedTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE128 META-FILTERED HYBRID BACKTEST")
        print(f"  flat        : {flat_path}")
        print(f"  meta model  : {args.meta_model_id}")
        model, features, task, version = load_meta_model(
            storage_root, args.meta_model_id, args.meta_model_version
        )
        threshold = resolve_threshold(args, args.meta_model_id, version)
        frame_all = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        missing = [name for name in features if name not in frame_all.columns]
        if missing:
            raise RuntimeError(
                f"Telemetry flat matrix is missing meta feature columns: {missing[:5]}"
            )
        indices = eval_indices(len(frame_all), args.eval_frac, args.max_windows)
        frame = frame_all.iloc[indices].copy().reset_index(drop=True)
        scores = positive_scores(model, frame[features].to_numpy(dtype=np.float32), task)
        summary, counters, trades = backtest(frame, scores, threshold, task)
        account = account_summary(summary, args.initial_capital, args.units)
        monthly = monthly_summary(trades)
        candles = load_candles(storage_root, args.symbol, args.timeframe)
        source_indices = [int(value) for value in frame["source_index"].tolist()]
        candle_rows = replay_candles_for_indices(candles, source_indices, trades)

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
                flat_path,
                version,
                threshold,
                summary,
                trades,
                monthly,
                candle_rows,
            ),
            encoding="utf-8",
        )
        files = {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)}
        payload = {
            "args": vars(args),
            "meta_model_version": version,
            "meta_task": task,
            "rows": len(frame_all),
            "evaluated_rows": len(frame),
            "thresholds": asdict(threshold),
            "summary": asdict(summary),
            "meta_counters": asdict(counters),
            "account": account,
            "monthly": [asdict(row) for row in monthly],
            "files": files,
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rule("DONE")
        print(f"  rows        : {summary.samples:,}/{len(frame_all):,}")
        print(f"  trades      : {summary.trades:,} ({summary.coverage:.2%})")
        print(f"  skipped meta: {counters.skipped_by_meta:,}")
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
