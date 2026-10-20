"""Phase134A: run a guarded hybrid paper/shadow replay from production config.

This script never sends broker orders. It consumes the frozen Phase134 config and
runs the selected stack over stored telemetry rows to produce an audit trail that
resembles the future live decision log.
"""

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
from backtest_hybrid_meta_labeler import MetaThresholdSpec
from backtest_hybrid_meta_labeler import backtest as backtest_flat_meta
from report_hybrid_full_backtest import (
    account_summary,
    load_candles,
    monthly_summary,
    render_html,
    replay_candles_for_indices,
)
from train_hybrid_meta_labeler import positive_scores
from validate_production_hybrid_stack import telemetry_schema

from ShadBotTrader.application.services.hybrid_production_service import (
    read_stack_config,
    validate_stack_config,
)
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_CONFIG = REPO_ROOT / "configs" / "hybrid_production_stack.json"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_paper_shadow")


@dataclass(frozen=True)
class PaperDecisionRow:
    row_number: int
    timestamp: str
    source_index: int
    status: str
    reason: str
    side: str
    meta_score: float
    entry: float
    take_profit: float
    stop_loss: float
    exit_index: int
    pnl: float
    balance_after: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase134 guarded paper/shadow replay from production config.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG))
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--allow-validation-fail", choices=("0", "1"), default="0")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Hybrid production paper shadow")
    return parser.parse_args(argv)


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def load_flat_model(
    storage_root: Path, model_id: str, version: int
) -> tuple[Any, list[str], str, int]:
    catalogue = ModelCatalogue(storage_root)
    resolved = version if version > 0 else catalogue.latest_version(model_id)
    if resolved < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    artifact = FilesystemArtifactStore(storage_root).load(ModelId(model_id), ModelVersion(resolved))
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{resolved}")
    payload = pickle.loads(artifact.payload)
    if not isinstance(payload, Mapping) or "model" not in payload:
        raise RuntimeError("Phase134 paper shadow currently supports flat meta models or base mode")
    features = payload.get("feature_names")
    if not isinstance(features, Sequence) or isinstance(features, str):
        raise RuntimeError("Flat meta artifact missing feature_names")
    return (
        payload["model"],
        [str(name) for name in features],
        str(payload.get("task", "classifier")),
        resolved,
    )


def scores_for_config(
    frame: pd.DataFrame, config: Any, storage_root: Path
) -> tuple[np.ndarray, str]:
    if config.meta_model_type == "none" or not config.meta_model_id:
        return np.ones(len(frame), dtype=np.float64), "base"
    if config.meta_model_type != "flat":
        raise RuntimeError(
            "paper_shadow v1 supports meta_model_type=none or flat; tensor models stay research until Phase133 passes"
        )
    model, features, task, version = load_flat_model(
        storage_root, config.meta_model_id, config.meta_model_version
    )
    missing = [name for name in features if name not in frame.columns]
    if missing:
        raise RuntimeError(f"Telemetry flat is missing production meta features: {missing[:5]}")
    scores = positive_scores(model, frame[features].to_numpy(dtype=np.float32), task)
    return scores, f"{config.meta_model_id}:v{version}:{task}"


def decision_rows(
    trades: Sequence[Any], initial_capital: float, units: float
) -> list[PaperDecisionRow]:
    rows: list[PaperDecisionRow] = []
    for trade in trades:
        rows.append(
            PaperDecisionRow(
                row_number=int(trade.number),
                timestamp=str(trade.timestamp),
                source_index=int(trade.source_index),
                status="would_trade",
                reason="paper shadow only; no broker order sent",
                side=str(trade.side),
                meta_score=0.0,
                entry=float(trade.entry),
                take_profit=float(trade.tp),
                stop_loss=float(trade.sl),
                exit_index=int(trade.exit_index),
                pnl=float(trade.pnl),
                balance_after=float(initial_capital + trade.equity * units),
            )
        )
    return rows


def write_decision_csv(path: Path, rows: Sequence[PaperDecisionRow]) -> None:
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
    config = read_stack_config(args.config_path)
    schema_hash, _rows, _channels = telemetry_schema(
        config.telemetry_flat_path, config.telemetry_tensor_path
    )
    validation = validate_stack_config(config, schema_hash)
    if not validation.passed and args.allow_validation_fail != "1":
        raise SystemExit(
            "Production stack validation failed. Run validate_production_hybrid_stack.py first, or pass --allow-validation-fail 1 for research-only dry run."
        )
    if config.mode == "live":
        raise SystemExit(
            "run_hybrid_paper_shadow.py never runs live mode. Use paper_shadow config."
        )

    flat_path = Path(args.flat_path) if args.flat_path else Path(config.telemetry_flat_path)
    if not flat_path.exists():
        flat_path = default_flat_path(storage_root, config.symbol, config.timeframe)
    frame_all = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    indices = eval_indices(len(frame_all), args.eval_frac, args.max_windows)
    frame = frame_all.iloc[indices].copy().reset_index(drop=True)
    scores, scorer = scores_for_config(frame, config, storage_root)
    threshold = MetaThresholdSpec(
        meta_threshold=0.0 if scorer == "base" else config.meta_threshold,
        score_threshold=config.score_threshold,
        source=f"phase134:{scorer}",
    )
    summary, counters, trades = backtest_flat_meta(frame, scores, threshold, task="classifier")
    account = account_summary(summary, config.initial_capital, config.position_size_units)
    monthly = monthly_summary(trades)
    candles = load_candles(storage_root, config.symbol, config.timeframe)
    source_indices = [int(value) for value in frame["source_index"].tolist()]
    candle_rows = replay_candles_for_indices(candles, source_indices, trades)
    rows = decision_rows(trades, config.initial_capital, config.position_size_units)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "latest.csv"
    json_path = out_dir / "latest.json"
    html_path = out_dir / "latest.html"
    write_decision_csv(csv_path, rows)
    html_path.write_text(
        render_html(
            args.report_title,
            argparse.Namespace(
                symbol=config.symbol,
                timeframe=config.timeframe,
                initial_capital=config.initial_capital,
                units=config.position_size_units,
                max_hold_bars=48,
                min_4h_room=2.0,
                min_1d_room=5.0,
                min_tp_distance=2.0,
                min_sl_distance=2.0,
                spread_mode="pct",
                spread_value=0.06,
                slippage=0.0,
                same_bar_policy="stop_first",
            ),
            flat_path,
            config.meta_model_version,
            threshold,
            summary,
            trades,
            monthly,
            candle_rows,
        ),
        encoding="utf-8",
    )
    payload = {
        "args": vars(args),
        "config": config.to_dict(),
        "validation": validation.to_dict(),
        "scorer": scorer,
        "evaluated_rows": len(frame),
        "summary": asdict(summary),
        "paper_counters": asdict(counters),
        "account": account,
        "monthly": [asdict(row) for row in monthly],
        "files": {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)},
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 74)
    print("  PHASE134 HYBRID PAPER SHADOW")
    print("=" * 74)
    print(f"  scorer      : {scorer}")
    print(f"  rows        : {len(frame):,}")
    print(f"  would trades: {summary.trades:,}")
    print(f"  total pnl   : {summary.total_pnl:+.2f}")
    print(f"  final       : ${account['final_balance']:.2f}")
    print(f"  report      : {json_path}")
    print("  real orders : DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
