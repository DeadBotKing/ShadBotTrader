"""Phase129A: backtest a trained telemetry WaveNet/TCN meta-filter."""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
import tempfile
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
from train_hybrid_telemetry_wavenet import default_tensor_path, load_tensor, prediction_arrays

from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_telemetry_wavenet_backtest")
DECISION_MODES = ("meta", "score", "both")


@dataclass(frozen=True)
class TelemetryWaveNetThresholds:
    meta_threshold: float
    score_threshold: float
    decision_mode: str
    source: str


@dataclass(frozen=True)
class WaveNetBacktestCounters:
    skipped_no_candidate: int
    skipped_by_wavenet: int
    skipped_while_open: int
    missing_flat_row: int
    missing_outcome: int

    @property
    def no_trade(self) -> int:
        return (
            self.skipped_no_candidate
            + self.skipped_by_wavenet
            + self.skipped_while_open
            + self.missing_flat_row
            + self.missing_outcome
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest Phase129 telemetry WaveNet/TCN meta-filter.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_telemetry_wavenet_5m")
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
    parser.add_argument("--report-title", default="Telemetry WaveNet filtered hybrid replay")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def require_tensorflow():
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "TensorFlow is required. Install: pip install -r requirements-ai.txt"
        ) from exc
    return tf


def deserialize_model(model_bytes: bytes) -> Any:
    tf = require_tensorflow()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.keras"
        path.write_bytes(model_bytes)
        return tf.keras.models.load_model(path)


def load_wavenet_artifact(
    storage_root: Path, model_id: str, version: int
) -> tuple[Any, dict[str, Any], int]:
    catalogue = ModelCatalogue(storage_root)
    resolved = version if version > 0 else catalogue.latest_version(model_id)
    if resolved < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    artifact = FilesystemArtifactStore(storage_root).load(ModelId(model_id), ModelVersion(resolved))
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{resolved}")
    payload = pickle.loads(artifact.payload)
    if not isinstance(payload, Mapping) or "model_bytes" not in payload:
        raise RuntimeError("Telemetry WaveNet artifact must contain model_bytes")
    return deserialize_model(payload["model_bytes"]), dict(payload), resolved


def resolve_thresholds(
    args: argparse.Namespace, payload: Mapping[str, Any], model_id: str, version: int
) -> TelemetryWaveNetThresholds:
    meta = (
        args.meta_threshold
        if args.meta_threshold >= 0
        else float(payload.get("meta_threshold", 0.55))
    )
    score = float(
        args.score_threshold if args.score_threshold != 0.0 else payload.get("score_threshold", 0.0)
    )
    source = "cli" if args.meta_threshold >= 0 else f"model_record:{model_id}:v{version}"
    return TelemetryWaveNetThresholds(meta, score, args.decision_mode, source)


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def normalize_with_payload(x_values: np.ndarray, payload: Mapping[str, Any]) -> np.ndarray:
    mean = np.asarray(payload["scaler_mean"], dtype=np.float32)
    std = np.asarray(payload["scaler_std"], dtype=np.float32)
    std = np.where(std < 1e-6, 1.0, std)
    return np.nan_to_num(
        (x_values.astype(np.float32) - mean) / std, nan=0.0, posinf=0.0, neginf=0.0
    )


def passes_gate(win_prob: float, score_r: float, thresholds: TelemetryWaveNetThresholds) -> bool:
    if thresholds.decision_mode == "meta":
        return win_prob >= thresholds.meta_threshold
    if thresholds.decision_mode == "score":
        return score_r >= thresholds.score_threshold
    return win_prob >= thresholds.meta_threshold and score_r >= thresholds.score_threshold


def trade_from_flat(number: int, row: pd.Series, equity: float) -> DetailedTrade:
    side = "BUY" if float(row.get("target_side", 0.0)) > 0 else "SELL"
    entry = float(row.get("candidate_entry_price", 0.0) or 0.0)
    pnl = float(row.get("target_trade_pnl", 0.0) or 0.0)
    exit_price = entry + pnl if side == "BUY" else entry - pnl
    outcome_code = float(row.get("target_outcome_code", 0.0) or 0.0)
    outcome = (
        "take_profit" if outcome_code > 0 else ("stop_loss" if outcome_code < 0 else "timeout")
    )
    return DetailedTrade(
        number=number,
        timestamp=str(row.get("timestamp", "")),
        side=side,
        row_index=int(row.name) if row.name is not None else -1,
        source_index=int(row.get("source_index", -1)),
        entry_index=int(row.get("source_index", -1)) + 1,
        exit_index=int(row.get("target_exit_index", int(row.get("source_index", -1))) or -1),
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


def max_drawdown(pnls: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def summary_from_trades(
    samples: int, trades: Sequence[DetailedTrade], counters: WaveNetBacktestCounters
) -> FixedBacktestSummary:
    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    total = sum(pnls)
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
        invalid_bracket=counters.missing_outcome + counters.missing_flat_row,
        win_rate=safe_div(wins, len(trades)),
        label_precision=safe_div(wins, len(trades)),
        total_pnl=total,
        avg_pnl=safe_div(total, len(trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=max_drawdown(pnls),
        coverage=safe_div(len(trades), samples),
    )


def backtest(
    source_indices: np.ndarray,
    candidate_mask: np.ndarray,
    win_scores: np.ndarray,
    score_r: np.ndarray,
    flat_by_source: Mapping[int, pd.Series],
    thresholds: TelemetryWaveNetThresholds,
) -> tuple[FixedBacktestSummary, WaveNetBacktestCounters, list[DetailedTrade]]:
    skipped_no_candidate = skipped_by_wavenet = skipped_while_open = 0
    missing_flat_row = missing_outcome = 0
    open_until = -1
    equity = 0.0
    trades: list[DetailedTrade] = []
    for offset, source in enumerate(source_indices):
        source_index = int(source)
        if source_index <= open_until:
            skipped_while_open += 1
            continue
        if candidate_mask[offset] < 0.5:
            skipped_no_candidate += 1
            continue
        if not passes_gate(float(win_scores[offset]), float(score_r[offset]), thresholds):
            skipped_by_wavenet += 1
            continue
        row = flat_by_source.get(source_index)
        if row is None:
            missing_flat_row += 1
            continue
        if int(row.get("target_exit_index", -1)) < 0:
            missing_outcome += 1
            continue
        equity += float(row.get("target_trade_pnl", 0.0) or 0.0)
        trade = trade_from_flat(len(trades) + 1, row, equity)
        trades.append(trade)
        open_until = max(open_until, trade.exit_index)
    counters = WaveNetBacktestCounters(
        skipped_no_candidate,
        skipped_by_wavenet,
        skipped_while_open,
        missing_flat_row,
        missing_outcome,
    )
    return summary_from_trades(len(source_indices), trades, counters), counters, trades


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
        rule("PHASE129 TELEMETRY WAVENET BACKTEST")
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
                    "wavenet_counters": asdict(counters),
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
