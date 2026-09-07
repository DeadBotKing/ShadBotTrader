"""Phase 107 — honest audit of the trend_signal BUY/HOLD/SELL target.

This script is deliberately useful even when TensorFlow is not installed:
it first audits the labels, split geometry, baselines and feature matrix.
If a trained model exists and TensorFlow can be imported, it also scores
that frozen model and prints per-class metrics.

Examples:
    PYTHONPATH=src python scripts/evaluate_trend_signal_5m.py \
      --symbol XAUUSD --timeframe 5M --window 288 --label-horizon 288 \
      --atr-mult 0.5 --folds 3 --storage-root datasets
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_STORAGE = REPO_ROOT / "datasets"
CLASS_NAMES = {0: "SELL", 1: "HOLD", 2: "BUY"}


class NoStoredData(RuntimeError):
    """Raised when the requested candle series does not exist on disk."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit trend_signal labels and, when possible, score the saved model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument(
        "--val-size",
        type=int,
        default=0,
        help="validation samples per fold; 0 = trainer auto geometry (10% pool)",
    )
    parser.add_argument(
        "--model-id",
        default="",
        help="model id to score; empty = gold_trend_signal_{timeframe}",
    )
    parser.add_argument(
        "--max-windows",
        type=int,
        default=5000,
        help="model scoring windows; 0 = every labelled window",
    )
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument(
        "--json-out",
        default="run_logs/trend_signal_audit_latest.json",
        help="machine-readable summary; empty = do not write JSON",
    )
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def pct(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:.1%}"


def qstats(values: Sequence[float]) -> dict[str, float] | None:
    """Small deterministic quantile summary."""
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    n = len(ordered)

    def at(frac: float) -> float:
        return ordered[min(n - 1, max(0, int(frac * (n - 1))))]

    return {
        "min": ordered[0],
        "p25": at(0.25),
        "median": at(0.50),
        "p75": at(0.75),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
    }


def fmt_stats(values: Sequence[float], suffix: str = "") -> str:
    stats = qstats(values)
    if stats is None:
        return "n/a"
    return (
        f"min {stats['min']:.3f}{suffix} · p25 {stats['p25']:.3f}{suffix} · "
        f"median {stats['median']:.3f}{suffix} · p75 {stats['p75']:.3f}{suffix} · "
        f"max {stats['max']:.3f}{suffix} · mean {stats['mean']:.3f}{suffix}"
    )


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    """Load real stored candles using the same symbol-resolution path as training."""
    from ShadBotTrader.data_cli import build_service
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.account import AccountProfileStore
    from ShadBotTrader.infrastructure.data.symbol_scope import (
        resolve_stored_symbol,
        stored_symbols,
    )

    _, store, _ = build_service(storage_root)
    try:
        profile = AccountProfileStore().active()
    except Exception:
        profile = None

    resolved = resolve_stored_symbol(store, symbol, timeframe, profile)
    if not resolved.found:
        raise NoStoredData(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}. "
            "Fetch market data first."
        )
    if resolved.is_alias:
        print(f"  [i] {resolved.note}")
    return store.query(Symbol(resolved.resolved), Timeframe(timeframe))


def build_service() -> Any:
    """Feature-rich DualModelService, matching the training CLI."""
    from ShadBotTrader.application.services.dual_model_service import DualModelService
    from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
    from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

    return DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )


def effective_val_size(pool_rows: int, requested: int = 0) -> int:
    if requested and requested > 0:
        return int(requested)
    return max(4, min(2000, pool_rows // 10))


def fold_label_balances(dataset: Any, role: Any, max_folds: int, val_size: int = 0) -> list[dict]:
    """Mirror the trainer's expanding roll-forward split and count labels."""
    from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split

    sample_ends = getattr(dataset, "sample_ends", None)
    if sample_ends is None or not dataset.target_columns:
        return []

    rows = len(sample_ends)
    if rows <= 0:
        return []
    target_col = dataset.target_columns[0]
    labels = [int(round(dataset.series[idx][target_col])) for idx in sample_ends]

    resolved_val = val_size or effective_val_size(rows)
    step = max(1, resolved_val)
    min_train_size = max(8, min(rows // 4, 20 * role.window_size))
    purge_gap = max(role.window_size - 1, 0)
    resolved_val = max(4, min(resolved_val, rows - min_train_size - purge_gap - 4))
    if resolved_val <= 0:
        return []

    plan = expanding_split(
        total_length=rows,
        val_size=resolved_val,
        step=step,
        min_train_size=min_train_size,
        purge_gap=purge_gap,
        sample_end_indices=dataset.sample_ends,
        label_end_indices=dataset.sample_label_ends,
        window_size=role.window_size,
    )
    folds = list(plan.folds)
    if max_folds and max_folds > 0:
        folds = folds[-max_folds:]

    balances: list[dict] = []
    for index, fold in enumerate(folds):
        train_counts = Counter(labels[fold.train_start : fold.train_end])
        val_counts = Counter(labels[fold.val_start : fold.val_end])
        balances.append(
            {
                "fold": index + 1,
                "train_range": [fold.train_start, fold.train_end],
                "val_range": [fold.val_start, fold.val_end],
                "purged_train_samples": int(getattr(fold, "purged_train_samples", 0)),
                "train": {CLASS_NAMES[k].lower(): int(train_counts.get(k, 0)) for k in range(3)},
                "val": {CLASS_NAMES[k].lower(): int(val_counts.get(k, 0)) for k in range(3)},
            }
        )
    return balances


def average_precision(
    y_true: Sequence[int], scores: Sequence[float], positive: int
) -> float | None:
    """Average precision for one positive class; no sklearn dependency required."""
    pairs = sorted(zip(scores, y_true, strict=True), key=lambda item: item[0], reverse=True)
    positives = sum(1 for label in y_true if label == positive)
    if positives == 0:
        return None
    hits = 0
    precision_sum = 0.0
    for rank, (_score, label) in enumerate(pairs, start=1):
        if label == positive:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / positives


def classification_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, Any]:
    matrix = [[0 for _ in range(3)] for _ in range(3)]
    for actual, predicted in zip(y_true, y_pred, strict=True):
        if 0 <= actual <= 2 and 0 <= predicted <= 2:
            matrix[actual][predicted] += 1

    total = sum(sum(row) for row in matrix)
    correct = sum(matrix[i][i] for i in range(3))
    per_class: dict[str, dict[str, float | int]] = {}
    recalls: list[float] = []
    f1s: list[float] = []
    weighted_f1_sum = 0.0
    for cls in range(3):
        tp = matrix[cls][cls]
        fp = sum(matrix[row][cls] for row in range(3) if row != cls)
        fn = sum(matrix[cls][col] for col in range(3) if col != cls)
        support = sum(matrix[cls])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        recalls.append(recall)
        f1s.append(f1)
        weighted_f1_sum += f1 * support
        per_class[CLASS_NAMES[cls].lower()] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }

    return {
        "confusion_matrix": matrix,
        "accuracy": correct / total if total else 0.0,
        "balanced_accuracy": statistics.fmean(recalls) if recalls else 0.0,
        "macro_f1": statistics.fmean(f1s) if f1s else 0.0,
        "weighted_f1": weighted_f1_sum / total if total else 0.0,
        "per_class": per_class,
    }


def select_sample_positions(total: int, max_windows: int) -> list[int]:
    if total <= 0:
        return []
    if max_windows <= 0 or total <= max_windows:
        return list(range(total))
    step = max(1, total // max_windows)
    return list(range(0, total, step))[:max_windows]


def model_input_mismatch(expected: Any, window_size: int, feature_count: int) -> str | None:
    """Return a human reason when a saved model cannot score this audit window."""
    if expected is None or len(expected) != 3:
        return None
    exp_window, exp_features = expected[1], expected[2]
    if exp_window is not None and int(exp_window) != int(window_size):
        return (
            f"model expects window={exp_window}, but this audit was run with "
            f"window={window_size}"
        )
    if exp_features is not None and int(exp_features) != int(feature_count):
        return (
            f"model expects {exp_features} features, but the current matrix has " f"{feature_count}"
        )
    return None


def score_model(args: argparse.Namespace, role: Any, dataset: Any) -> dict[str, Any] | None:
    """Score the frozen latest trend_signal model when TF/artifacts are available."""
    import numpy as np

    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window
    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
    from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

    model_id = args.model_id.strip() or f"gold_trend_signal_{args.timeframe.strip().lower()}"
    catalogue = ModelCatalogue(args.storage_root)
    version = catalogue.latest_version(model_id)
    if not version:
        print("\n  [i] No trained trend_signal model found; model scoring skipped.")
        print(f"      expected model id: {model_id}")
        return None

    record = catalogue.read(model_id, version)
    artifact = FilesystemArtifactStore(args.storage_root).load(
        ModelId(model_id), ModelVersion(version)
    )
    if record is None or artifact is None:
        print(f"\n  [i] {model_id} v{version} is listed but weights/record are missing; skipped.")
        return None

    try:
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _deserialize_model
    except ImportError as error:
        print("\n  [i] TensorFlow is not installed; model scoring skipped.")
        print(f"      {type(error).__name__}: {error}")
        return None

    try:
        model = _deserialize_model(artifact.payload)
    except ImportError as error:
        print("\n  [i] TensorFlow is not installed; model scoring skipped.")
        print(f"      {type(error).__name__}: {error}")
        return None
    expected = getattr(model, "input_shape", None)
    mismatch = model_input_mismatch(expected, role.window_size, dataset.feature_count)
    if mismatch is not None:
        print("\n  [i] Saved model input shape does not match this audit; model scoring skipped.")
        print(f"      {mismatch}")
        print("      To score that saved model, re-run the audit with its recorded window size.")
        print("      The label/fold audit above is still valid for the requested configuration.")
        return None

    sample_ends = list(dataset.sample_ends or [])
    positions = select_sample_positions(len(sample_ends), int(args.max_windows))
    if not positions:
        print("\n  [i] No complete labelled windows available for model scoring.")
        return None

    target_col = dataset.target_columns[0]
    y_true: list[int] = []
    probs: list[list[float]] = []
    batch_rows: list[list[list[float]]] = []
    batch_actual: list[int] = []
    batch = 128
    scale_range = getattr(role, "input_scale_range", (-2.0, 2.0))

    def flush() -> None:
        if not batch_rows:
            return
        x = np.array(batch_rows, dtype=np.float32)
        raw = model.predict(x, verbose=0)
        raw_arr = np.asarray(raw)
        if raw_arr.ndim == 3:
            raw_arr = raw_arr[:, -1, :]
        if raw_arr.ndim != 2 or raw_arr.shape[1] != 3:
            raise ValueError(f"unexpected model output shape {raw_arr.shape}; expected [batch, 3]")
        for row in raw_arr:
            total = float(np.sum(row))
            if total > 0:
                probs.append([float(v) / total for v in row])
            else:
                probs.append([0.0, 0.0, 0.0])
        y_true.extend(batch_actual)
        batch_rows.clear()
        batch_actual.clear()

    for pos in positions:
        end = sample_ends[pos]
        window = [
            row[: dataset.feature_count]
            for row in dataset.series[end - role.window_size + 1 : end + 1]
        ]
        batch_rows.append(minmax_scale_window(window, scale_range))
        batch_actual.append(int(round(dataset.series[end][target_col])))
        if len(batch_rows) >= batch:
            flush()
    flush()

    y_pred = [max(range(3), key=lambda idx: row[idx]) for row in probs]
    metrics = classification_metrics(y_true, y_pred)
    ap_buy = average_precision(y_true, [row[2] for row in probs], positive=2)
    ap_sell = average_precision(y_true, [row[0] for row in probs], positive=0)
    probability_stats = {}
    for idx in range(3):
        values = [row[idx] for row in probs]
        probability_stats[CLASS_NAMES[idx].lower()] = {
            "mean": statistics.fmean(values) if values else 0.0,
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "min": min(values) if values else 0.0,
            "max": max(values) if values else 0.0,
        }

    return {
        "model_id": model_id,
        "version": version,
        "record_timeframe": getattr(record, "timeframe", ""),
        "windows_scored": len(y_true),
        "sampled_from_windows": len(sample_ends),
        "metrics": metrics,
        "average_precision_buy": ap_buy,
        "average_precision_sell": ap_sell,
        "probability_stats": probability_stats,
    }


def print_model_score(report: dict[str, Any]) -> None:
    rule("MODEL SCORE")
    print(f"  model      : {report['model_id']} v{report['version']}")
    print(
        f"  windows    : {report['windows_scored']:,} scored"
        f" / {report['sampled_from_windows']:,} labelled"
    )
    metrics = report["metrics"]
    print("  confusion  : rows=actual, cols=predicted [SELL,HOLD,BUY]")
    for name, row in zip(("SELL", "HOLD", "BUY"), metrics["confusion_matrix"], strict=True):
        print(f"    {name:<4}: {row}")
    print(f"  accuracy   : {pct(metrics['accuracy'])}")
    print(f"  balanced   : {pct(metrics['balanced_accuracy'])}")
    print(f"  macro F1   : {metrics['macro_f1']:.4f}")
    print(f"  weighted F1: {metrics['weighted_f1']:.4f}")
    sell_ap = pct(report["average_precision_sell"])
    buy_ap = pct(report["average_precision_buy"])
    print(f"  PR-AUC/AP  : SELL {sell_ap} · BUY {buy_ap}")
    print("  per class  :")
    for name, values in metrics["per_class"].items():
        print(
            f"    {name:<4} precision={pct(values['precision'])} "
            f"recall={pct(values['recall'])} f1={values['f1']:.4f} "
            f"support={values['support']:,}"
        )
    print("  probability spread:")
    max_stdev = 0.0
    for name, stats in report["probability_stats"].items():
        max_stdev = max(max_stdev, float(stats["stdev"]))
        print(
            f"    {name:<4} mean={stats['mean']:.4f} stdev={stats['stdev']:.4f} "
            f"min={stats['min']:.4f} max={stats['max']:.4f}"
        )
    if max_stdev < 0.01:
        print("  [!] collapse check: probabilities are almost constant (stdev < 0.01).")


def write_json(path_text: str, payload: dict[str, Any]) -> None:
    if not path_text.strip():
        return
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  json report : {path}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    args.storage_root = str(storage_root)

    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.model_roles import trend_signal_model_role
    from ShadBotTrader.infrastructure.ai.target_builder import build_trend_signal_labels

    symbol = args.symbol.strip().upper()
    timeframe = args.timeframe.strip().upper()
    role = trend_signal_model_role(
        timeframe=timeframe,
        threshold=float(args.atr_mult),
        window_size=max(int(args.window), 2),
        label_horizon=max(int(args.label_horizon), 1),
    )

    print("=== ShadBotTrader — Phase 107 trend_signal audit ===")
    print(f"symbol {symbol} | timeframe {timeframe} | window {role.window_size}")
    print(
        f"label horizon {role.label_horizon} | "
        f"barrier {role.target.threshold:.3f} × daily-range proxy"
    )

    try:
        candles = load_candles(storage_root, symbol, timeframe)
    except NoStoredData as error:
        print(f"\n  [X] {error}")
        return 1

    first_time = str(candles[0].open_time)[:19]
    last_time = str(candles[-1].open_time)[:19]
    labels = build_trend_signal_labels(
        candles,
        horizon=role.label_horizon,
        atr_mult=role.target.threshold,
    )

    rule("RAW LABEL AUDIT")
    print(f"  candles    : {len(candles):,} ({first_time} .. {last_time})")
    print(f"  labels     : {len(labels):,} accepted from {labels.examined_count:,} examined starts")
    print(f"  warmup skip: {labels.warmup_skipped:,}")
    print(f"  ambiguous  : {labels.ambiguous_count:,} (both barriers hit in the same candle)")
    accepted_partial = sum(
        1 for source in labels.source_index if source + role.label_horizon >= len(candles)
    )
    print(
        f"  partial hz : {labels.partial_horizon_count:,} examined near-tail starts; "
        f"{accepted_partial:,} accepted labels have less than full horizon"
    )
    counts = labels.distribution()
    total = sum(counts.values())
    for key in ("sell", "hold", "buy"):
        count = counts.get(key, 0)
        share = count / total if total else 0.0
        print(f"  {key.upper():<4}       : {count:,} ({share:.1%})")
    majority = max(counts.values()) / total if total else 0.0
    hold_base = counts.get("hold", 0) / total if total else 0.0
    print(f"  majority baseline: {majority:.1%}")
    print(f"  always-HOLD base : {hold_base:.1%}")

    distances_all = [
        end - start for start, end in zip(labels.source_index, labels.label_end_index, strict=True)
    ]
    distances_hits = [
        end - start
        for label, start, end in zip(
            labels.labels, labels.source_index, labels.label_end_index, strict=True
        )
        if label != 1
    ]
    barrier_values = labels.barrier_price_dist or labels.barrier_dist
    print(f"  label distance all : {fmt_stats([float(v) for v in distances_all], ' bars')}")
    print(f"  first-hit distance : {fmt_stats([float(v) for v in distances_hits], ' bars')}")
    print(f"  barrier distance  : {fmt_stats([float(v) for v in barrier_values], ' USD')}")

    service = build_service()
    try:
        dataset = service.prepare(candles, Symbol(symbol), Timeframe(timeframe), role)
    except Exception as error:
        print(f"\n  [X] Cannot prepare feature matrix: {type(error).__name__}: {error}")
        return 1

    summary = dataset.summary()
    rule("FEATURE MATRIX / WINDOWS")
    print(f"  usable rows    : {summary['rows']:,}")
    print(f"  feature columns: {summary['feature_columns']:,}")
    print(f"  dropped warmup : {summary['dropped_warmup']:,}")
    print(f"  excluded feats : {summary.get('excluded_features', 0):,}")
    print(f"  skipped feats  : {summary.get('skipped_features', 0):,}")
    sample_count = len(dataset.sample_ends or [])
    print(f"  labelled windows: {sample_count:,}")
    print(f"  target column  : {dataset.target_columns[0] if dataset.target_columns else 'n/a'}")

    balances = fold_label_balances(
        dataset,
        role,
        max_folds=max(int(args.folds), 1),
        val_size=max(int(args.val_size), 0),
    )
    rule("ROLL-FORWARD FOLD AUDIT")
    if not balances:
        print("  [!] Not enough labelled windows to build a fold plan.")
    else:
        for row in balances:
            print(
                f"  fold {row['fold']}: train{tuple(row['train_range'])} {row['train']} "
                f"-> val{tuple(row['val_range'])} {row['val']} "
                f"purged={row['purged_train_samples']}"
            )

    json_payload: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "window": role.window_size,
        "label_horizon": role.label_horizon,
        "atr_mult": role.target.threshold,
        "candles": len(candles),
        "labels": len(labels),
        "distribution": counts,
        "majority_baseline": majority,
        "always_hold_baseline": hold_base,
        "warmup_skipped": labels.warmup_skipped,
        "ambiguous_count": labels.ambiguous_count,
        "partial_horizon_count": labels.partial_horizon_count,
        "accepted_partial_horizon_count": accepted_partial,
        "distance_all": qstats([float(v) for v in distances_all]),
        "distance_first_hits": qstats([float(v) for v in distances_hits]),
        "barrier_distance": qstats([float(v) for v in barrier_values]),
        "feature_matrix": summary,
        "folds": balances,
        "model_score": None,
    }

    model_report = score_model(args, role, dataset)
    if model_report is not None:
        print_model_score(model_report)
        json_payload["model_score"] = model_report

    write_json(args.json_out, json_payload)

    rule("VERDICT")
    print("  Phase 107 is an audit only: it does not train or change model weights.")
    if total and majority >= 0.80:
        print("  [!] Labels are highly imbalanced; Phase 108 class weights/F1 is mandatory.")
    else:
        print("  Label balance is not extreme, but F1/precision/recall are still required.")
    if labels.partial_horizon_count:
        print(
            "  [!] Near-tail labels with partial horizons exist in the current target builder; "
            "treat the last horizon block carefully in training/evaluation."
        )
    print("  Next recommended step: Phase 108 — class weights + per-class F1/PR-AUC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
