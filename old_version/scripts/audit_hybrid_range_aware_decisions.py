"""Phase 116 integration audit for the hybrid range-aware decision path.

The script routes the Phase 124 hybrid head and Phase 125/113 thresholds
through the normal trading pipeline:

    HybridRangeAwareStrategy -> PositionAwareDecisionEngine -> RiskGate -> IntentFactory

It does not execute broker orders. Its job is to prove that the profitable
research rule is now represented as an auditable runtime decision path.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd

from ShadBotTrader.application.services.trading_decision_service import TradingDecisionService
from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.prediction_target import HybridHeadForecast, RangeForecast
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.hybrid_head_predictor import HybridHeadPredictor
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol, stored_symbols
from ShadBotTrader.infrastructure.trading import (
    DefaultIntentFactory,
    InMemoryDecisionJournal,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)
from ShadBotTrader.infrastructure.trading.hybrid_range_aware_strategy import (
    HYBRID_HEAD_FORECAST_KEY,
    RANGE_1D_FORECAST_KEY,
    RANGE_4H_FORECAST_KEY,
    RAW_ENTRY_PRICE_KEY,
    ROOM_REFERENCE_PRICE_KEY,
    HybridRangeAwareConfig,
    HybridRangeAwareStrategy,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_decision_audit")
CLASS_NAMES = {0: "sell", 1: "hold", 2: "buy"}


@dataclass(frozen=True)
class ThresholdSpec:
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    source: str


@dataclass(frozen=True)
class AuditRow:
    row_index: int
    timestamp: str
    source_index: int
    label: str
    status: str
    signal_type: str
    decision: str
    intent_side: str
    reason: str
    sell_probability: float
    hold_probability: float
    buy_probability: float
    raw_entry_price: float
    entry_price: float
    take_profit: float
    stop_loss: float
    tp_distance: float
    sl_distance: float
    range_4h_room: float
    range_1d_room: float
    range_4h_high: float
    range_4h_low: float
    range_1d_high: float
    range_1d_low: float
    label_correct: int


@dataclass(frozen=True)
class AuditSummary:
    rows: int
    trade_intents: int
    no_trade: int
    buy_intents: int
    sell_intents: int
    label_correct: int
    label_precision: float
    coverage: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the Phase 116 hybrid range-aware runtime decision path.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--eval-frac", type=float, default=0.30)
    parser.add_argument("--max-windows", type=int, default=0, help="0 = all eval rows")
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--min-4h-room", type=float, default=2.0)
    parser.add_argument("--min-1d-room", type=float, default=5.0)
    parser.add_argument("--min-tp-distance", type=float, default=2.0)
    parser.add_argument("--min-sl-distance", type=float, default=2.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--base-quantity", type=float, default=1.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def default_matrix_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_xgboost_matrix_latest.parquet"


def eval_slice_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    _, store, _ = build_data_service(storage_root)
    resolved = resolve_stored_symbol(store, symbol, timeframe)
    if not resolved.found:
        raise RuntimeError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    return sorted(
        store.query(Symbol(resolved.resolved), Timeframe(timeframe)),
        key=lambda candle: candle.open_time.value,
    )


def latest_or_requested(catalogue: ModelCatalogue, model_id: str, version: int) -> int:
    resolved = version if version > 0 else catalogue.latest_version(model_id)
    if resolved < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    return resolved


def load_model_record(storage_root: Path, model_id: str, version: int) -> tuple[ModelRecord, int]:
    catalogue = ModelCatalogue(storage_root)
    resolved = latest_or_requested(catalogue, model_id, version)
    record = catalogue.read(model_id, resolved)
    if record is None:
        raise RuntimeError(f"No model record found for {model_id} v{resolved}")
    return record, resolved


def load_artifact(storage_root: Path, model_id: str, version: int):
    artifact = FilesystemArtifactStore(storage_root).load(ModelId(model_id), ModelVersion(version))
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{version}")
    return artifact


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def resolve_thresholds(args: argparse.Namespace, record: ModelRecord) -> ThresholdSpec:
    buy = _finite_or_none(args.buy_threshold)
    sell = _finite_or_none(args.sell_threshold)
    margin = _finite_or_none(args.min_margin)
    if buy is not None and sell is not None and buy >= 0 and sell >= 0:
        return ThresholdSpec(buy, sell, max(0.0, margin or 0.0), "cli")

    thresholds = record.decision_thresholds or {}
    buy = _finite_or_none(thresholds.get("buy_prob"))
    sell = _finite_or_none(thresholds.get("sell_prob"))
    saved_margin = _finite_or_none(thresholds.get("min_margin"))
    if buy is None or sell is None:
        raise RuntimeError(
            f"Model {record.model_id} v{record.version} has no saved Phase125 thresholds. "
            "Run scripts/backtest_hybrid_xgboost_head.py with --save-record 1 first."
        )
    return ThresholdSpec(
        buy_threshold=buy,
        sell_threshold=sell,
        min_margin=max(0.0, saved_margin if margin is None or margin < 0 else margin),
        source=f"model_record:{record.model_id}:v{record.version}",
    )


def range_forecast_from_row(
    row: Mapping[str, Any], prefix: str, timeframe: str
) -> RangeForecast | None:
    available = _finite_or_none(row.get(f"{prefix}_available")) or 0.0
    if available < 0.5:
        return None
    high = _finite_or_none(row.get(f"{prefix}_high_price"))
    low = _finite_or_none(row.get(f"{prefix}_low_price"))
    reference = _finite_or_none(row.get("close"))
    if high is None or low is None or reference is None or reference <= 0:
        return None
    return RangeForecast(
        reference_close=reference,
        high_offset=high / reference - 1.0,
        low_offset=low / reference - 1.0,
        horizon=1,
        timeframe=timeframe,
        generated_at=str(row.get("timestamp", "")),
    )


def raw_entry_price(row: Mapping[str, Any], candles: Sequence[Any]) -> tuple[float, str]:
    source_index = int(row.get("source_index", -1))
    entry_index = source_index + 1
    if 0 <= entry_index < len(candles):
        return float(candles[entry_index].open.amount), "next_open_mid"
    close = _finite_or_none(row.get("close"))
    if close is None:
        raise RuntimeError(f"No entry price available for source_index={source_index}")
    return close, "row_close_fallback"


def timestamp_from_row(row: Mapping[str, Any]) -> Timestamp:
    raw = row.get("timestamp", "")
    try:
        value = pd.to_datetime(raw, utc=True).to_pydatetime()
    except Exception:
        value = datetime.now(timezone.utc)
    return Timestamp(value)


def build_context(
    row_index: int,
    row: Mapping[str, Any],
    forecast: HybridHeadForecast,
    range_1d: RangeForecast | None,
    range_4h: RangeForecast | None,
    raw_entry: float,
    entry_source: str,
    args: argparse.Namespace,
) -> StrategyContext:
    timestamp = timestamp_from_row(row)
    metadata = {
        "matrix_row_index": row_index,
        "source_index": int(row.get("source_index", -1)),
        "entry_price_source": entry_source,
        RAW_ENTRY_PRICE_KEY: raw_entry,
        ROOM_REFERENCE_PRICE_KEY: float(row.get("close", raw_entry)),
    }
    return StrategyContext(
        timestamp=timestamp,
        symbol=Symbol(args.symbol),
        timeframe=Timeframe(args.timeframe),
        predictions=[
            PredictionView(
                model_id=args.model_id,
                model_version=int(forecast.model_version),
                value=forecast.buy_probability - forecast.sell_probability,
                confidence=forecast.confidence,
                generated_at=timestamp,
                metadata={
                    HYBRID_HEAD_FORECAST_KEY: forecast,
                    RANGE_1D_FORECAST_KEY: range_1d,
                    RANGE_4H_FORECAST_KEY: range_4h,
                },
            )
        ],
        portfolio=PortfolioView(equity=Decimal(str(args.capital)), open_position_count=0),
        metadata=metadata,
    )


def make_trading_service(
    config: HybridRangeAwareConfig, base_quantity: float
) -> TradingDecisionService:
    return TradingDecisionService(
        strategies=[HybridRangeAwareStrategy(config=config)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=999, min_confidence=0.0)),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal(str(base_quantity))),
        journal=InMemoryDecisionJournal(),
    )


def audit_row_from_outcome(
    row_index: int,
    row: Mapping[str, Any],
    forecast: HybridHeadForecast,
    outcome: Any,
    raw_entry: float,
) -> AuditRow:
    signal = outcome.signal
    decision = outcome.decision
    intent = outcome.intent
    signal_context = signal.context if signal is not None else {}
    side = signal.signal_type.value if signal is not None else ""
    label = CLASS_NAMES.get(int(row.get("label", 1)), str(row.get("label", "")))
    traded = intent is not None
    intent_side = intent.side.value if intent is not None else ""
    label_correct = int(traded and intent_side.lower() == label)
    range_room = signal_context.get("range_room", {}) if isinstance(signal_context, dict) else {}
    return AuditRow(
        row_index=row_index,
        timestamp=str(row.get("timestamp", "")),
        source_index=int(row.get("source_index", -1)),
        label=label,
        status="trade" if traded else "no_trade",
        signal_type=side,
        decision=decision.decision_type.value if decision is not None else "",
        intent_side=intent_side,
        reason=outcome.rejected_reason or (signal.reason if signal is not None else ""),
        sell_probability=forecast.sell_probability,
        hold_probability=forecast.hold_probability,
        buy_probability=forecast.buy_probability,
        raw_entry_price=raw_entry,
        entry_price=float(signal_context.get("entry_price", 0.0) or 0.0),
        take_profit=float(signal_context.get("take_profit", 0.0) or 0.0),
        stop_loss=float(signal_context.get("stop_loss", 0.0) or 0.0),
        tp_distance=float(signal_context.get("tp_distance", 0.0) or 0.0),
        sl_distance=float(signal_context.get("sl_distance", 0.0) or 0.0),
        range_4h_room=float(range_room.get("range_4h_room", 0.0) or 0.0),
        range_1d_room=float(range_room.get("range_1d_room", 0.0) or 0.0),
        range_4h_high=float(row.get("range_4h_high_price", 0.0) or 0.0),
        range_4h_low=float(row.get("range_4h_low_price", 0.0) or 0.0),
        range_1d_high=float(row.get("range_1d_high_price", 0.0) or 0.0),
        range_1d_low=float(row.get("range_1d_low_price", 0.0) or 0.0),
        label_correct=label_correct,
    )


def summarise(rows: Sequence[AuditRow]) -> AuditSummary:
    trades = [row for row in rows if row.status == "trade"]
    buy = [row for row in trades if row.intent_side.lower() == "buy"]
    sell = [row for row in trades if row.intent_side.lower() == "sell"]
    correct = sum(row.label_correct for row in trades)
    return AuditSummary(
        rows=len(rows),
        trade_intents=len(trades),
        no_trade=len(rows) - len(trades),
        buy_intents=len(buy),
        sell_intents=len(sell),
        label_correct=correct,
        label_precision=correct / len(trades) if trades else 0.0,
        coverage=len(trades) / len(rows) if rows else 0.0,
    )


def write_csv(path: Path, rows: Sequence[AuditRow]) -> None:
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
    matrix_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else default_matrix_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE 116 HYBRID RANGE-AWARE DECISION AUDIT")
        print(f"  matrix      : {matrix_path}")
        print(f"  model       : {args.model_id}")

        record, version = load_model_record(storage_root, args.model_id, args.model_version)
        thresholds = resolve_thresholds(args, record)
        print(
            "  thresholds  : "
            f"buy={thresholds.buy_threshold:.3f} "
            f"sell={thresholds.sell_threshold:.3f} "
            f"margin={thresholds.min_margin:.3f} ({thresholds.source})"
        )

        artifact = load_artifact(storage_root, record.model_id, version)
        predictor = HybridHeadPredictor(
            horizon=max(record.horizon or 288, 1), timeframe=record.timeframe
        )
        payload = predictor.load_payload(artifact)
        full_frame = pd.read_parquet(matrix_path)
        missing = [name for name in payload.feature_names if name not in full_frame.columns]
        if missing:
            raise RuntimeError(f"Hybrid matrix is missing model feature columns: {missing[:5]}")
        indices = eval_slice_indices(len(full_frame), args.eval_frac, args.max_windows)
        frame = full_frame.iloc[indices].copy()
        row_maps = [dict(row) for _, row in frame.iterrows()]
        probabilities = predictor.probabilities(artifact, row_maps)
        candles = load_candles(storage_root, args.symbol, args.timeframe)

        config = HybridRangeAwareConfig(
            buy_threshold=thresholds.buy_threshold,
            sell_threshold=thresholds.sell_threshold,
            min_margin=thresholds.min_margin,
            min_4h_room=max(args.min_4h_room, 0.0),
            min_1d_room=max(args.min_1d_room, 0.0),
            min_tp_distance=max(args.min_tp_distance, 0.0),
            min_sl_distance=max(args.min_sl_distance, 0.0),
            spread_mode=args.spread_mode,
            spread_value=max(args.spread_value, 0.0),
            slippage=max(args.slippage, 0.0),
        )
        trading = make_trading_service(config, max(args.base_quantity, 0.000001))

        audit_rows: list[AuditRow] = []
        for offset, ((row_index, row), probs) in enumerate(
            zip(frame.iterrows(), probabilities, strict=True)
        ):
            row_map = dict(row)
            forecast = HybridHeadForecast.from_vector(
                probs,
                horizon=max(record.horizon or 288, 1),
                timeframe=record.timeframe,
                generated_at=str(row_map.get("timestamp", "")),
                model_id=record.model_id,
                model_version=version,
            )
            range_1d = range_forecast_from_row(row_map, "range_1d", "1D")
            range_4h = range_forecast_from_row(row_map, "range_4h", "4H")
            raw_entry, entry_source = raw_entry_price(row_map, candles)
            context = build_context(
                int(row_index),
                row_map,
                forecast,
                range_1d,
                range_4h,
                raw_entry,
                entry_source,
                args,
            )
            outcome = trading.evaluate(context)
            audit_rows.append(
                audit_row_from_outcome(int(row_index), row_map, forecast, outcome, raw_entry)
            )
            if offset and offset % 500 == 0:
                print(f"  audited     : {offset:,}/{len(frame):,}")

        summary = summarise(audit_rows)
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        write_csv(csv_path, audit_rows)
        files = {"csv": str(csv_path), "json": str(json_path)}
        payload_json = {
            "args": vars(args),
            "model_version": version,
            "matrix_rows": len(full_frame),
            "eval_rows": len(frame),
            "thresholds": asdict(thresholds),
            "config": config.to_dict(),
            "summary": asdict(summary),
            "files": files,
        }
        json_path.write_text(
            json.dumps(payload_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        rule("DECISION AUDIT SUMMARY")
        print(f"  rows        : {summary.rows:,}")
        print(f"  intents     : {summary.trade_intents:,} ({summary.coverage:.2%})")
        print(f"  buy/sell    : {summary.buy_intents:,} / {summary.sell_intents:,}")
        print(f"  label prec. : {summary.label_precision:.2%}")
        print(f"  report      : {json_path}")
        print(f"  audit csv   : {csv_path}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
