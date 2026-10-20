"""Train tabular booster branches for the trend_signal target.

This is Phase 120/121 research infrastructure: it keeps the existing
WaveNet path intact and adds a separate branch for tree boosters on
causal window summaries. The saved artifacts are intentionally distinct
from ``gold_trend_signal_5m`` so pilot runs cannot overwrite the neural
model.

Examples:
    python scripts/train_trend_signal_boosters.py --symbol XAUUSD \
      --timeframe 5M --booster lightgbm --output-mode multiclass \
      --window 288 --label-horizon 288 --atr-mult 0.5 --train-ratio 80 \
      --folds 3 --val-size 2000 --summary-mode basic --class-weight auto
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.infrastructure.ai.model_roles import trend_signal_model_role
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split
from ShadBotTrader.infrastructure.ai.tabular_window_summary import SUMMARY_MODES, summarise_windows
from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
    average_precision_score,
    classification_report_metrics,
)
from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol, stored_symbols
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2
CLASS_NAMES = {CLASS_SELL: "sell", CLASS_HOLD: "hold", CLASS_BUY: "buy"}
BOOSTER_CHOICES = ("auto", "lightgbm", "xgboost", "catboost")
OUTPUT_MODES = ("multiclass", "buy", "sell")
CLASS_WEIGHT_CHOICES = ("auto", "off")


@dataclass(frozen=True)
class FoldResult:
    fold: int
    train_start: int
    train_end: int
    val_start: int
    val_end: int
    purged_train_samples: int
    metrics: dict[str, float]
    train_balance: dict[str, int]
    val_balance: dict[str, int]


class MissingBoosterDependency(RuntimeError):
    """The selected optional booster package is not installed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a LightGBM/XGBoost/CatBoost branch for trend_signal.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--booster", choices=BOOSTER_CHOICES, default="auto")
    parser.add_argument("--output-mode", choices=OUTPUT_MODES, default="multiclass")
    parser.add_argument("--summary-mode", choices=SUMMARY_MODES, default="basic")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--val-size", type=int, default=2000)
    parser.add_argument("--class-weight", choices=CLASS_WEIGHT_CHOICES, default="auto")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all prepared windows")
    parser.add_argument("--save-record", type=int, default=1)
    parser.add_argument("--storage-root", default=str(REPO_ROOT / "datasets"))
    parser.add_argument("--output-dir", default="run_logs/trend_signal_boosters")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    _, store, _ = build_data_service(storage_root)
    resolved = resolve_stored_symbol(store, symbol, timeframe)
    if not resolved.found:
        raise RuntimeError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    if resolved.is_alias:
        print(f"  [i] {resolved.note}")
    return store.query(Symbol(resolved.resolved), Timeframe(timeframe))


def training_prefix(candles: Sequence[Any], train_ratio: float, window_size: int) -> Sequence[Any]:
    if not 0 < train_ratio <= 100:
        raise ValidationError("train_ratio must be in (0, 100]")
    if train_ratio >= 100:
        return candles
    cutoff = max(window_size + 2, int(len(candles) * train_ratio / 100.0))
    cutoff = min(cutoff, len(candles))
    print(f"  train prefix    : {cutoff:,}/{len(candles):,} candles ({train_ratio:.1f}%)")
    return candles[:cutoff]


def prepare_dataset(args: argparse.Namespace, candles: Sequence[Any]):
    role = trend_signal_model_role(
        timeframe=args.timeframe,
        threshold=args.atr_mult,
        window_size=args.window,
        label_horizon=args.label_horizon,
    )
    service = DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )
    return role, service.prepare(candles, Symbol(args.symbol), Timeframe(args.timeframe), role)


def labels_for_mode(labels: Sequence[int], output_mode: str) -> np.ndarray:
    if output_mode == "buy":
        return np.asarray([1 if label == CLASS_BUY else 0 for label in labels], dtype=np.int64)
    if output_mode == "sell":
        return np.asarray([1 if label == CLASS_SELL else 0 for label in labels], dtype=np.int64)
    return np.asarray(labels, dtype=np.int64)


def class_weights(labels: Sequence[int], output_units: int, mode: str) -> dict[int, float] | None:
    if mode != "auto":
        return None
    counts = Counter(int(label) for label in labels)
    total = sum(counts.values())
    if not total:
        return None
    return {
        cls: total / (output_units * count)
        for cls, count in counts.items()
        if count > 0 and 0 <= cls < output_units
    }


def sample_weights(labels: Sequence[int], weights: dict[int, float] | None) -> np.ndarray | None:
    if not weights:
        return None
    return np.asarray([weights.get(int(label), 1.0) for label in labels], dtype=np.float32)


def _lightgbm_model(args: argparse.Namespace, output_mode: str):
    try:
        from lightgbm import LGBMClassifier
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install LightGBM: pip install lightgbm") from exc
    objective = "multiclass" if output_mode == "multiclass" else "binary"
    return LGBMClassifier(
        objective=objective,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        num_leaves=args.num_leaves,
        max_depth=args.max_depth,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )


def _xgboost_model(args: argparse.Namespace, output_mode: str):
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install XGBoost: pip install xgboost") from exc
    objective = "multi:softprob" if output_mode == "multiclass" else "binary:logistic"
    kwargs: dict[str, Any] = {
        "objective": objective,
        "n_estimators": args.n_estimators,
        "learning_rate": args.learning_rate,
        "max_depth": args.max_depth,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "random_state": 42,
        "n_jobs": -1,
        "eval_metric": "mlogloss" if output_mode == "multiclass" else "logloss",
        "tree_method": "hist",
    }
    if output_mode == "multiclass":
        kwargs["num_class"] = 3
    return XGBClassifier(**kwargs)


def _catboost_model(args: argparse.Namespace, output_mode: str):
    try:
        from catboost import CatBoostClassifier
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install CatBoost: pip install catboost") from exc
    return CatBoostClassifier(
        loss_function="MultiClass" if output_mode == "multiclass" else "Logloss",
        iterations=args.n_estimators,
        learning_rate=args.learning_rate,
        depth=max(1, args.max_depth),
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )


def make_model(args: argparse.Namespace, output_mode: str):
    requested = [args.booster] if args.booster != "auto" else ["lightgbm", "xgboost", "catboost"]
    failures: list[str] = []
    for name in requested:
        try:
            if name == "lightgbm":
                return name, _lightgbm_model(args, output_mode)
            if name == "xgboost":
                return name, _xgboost_model(args, output_mode)
            if name == "catboost":
                return name, _catboost_model(args, output_mode)
        except MissingBoosterDependency as error:
            failures.append(str(error))
    raise MissingBoosterDependency(
        "No requested booster backend is installed. "
        "Install one of: pip install lightgbm xgboost catboost. " + " | ".join(failures)
    )


def aligned_predict_proba(model: Any, x_values: np.ndarray, output_units: int) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    if raw.ndim == 1:
        raw = np.column_stack([1.0 - raw, raw])
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    aligned = np.zeros((len(raw), output_units), dtype=np.float64)
    for raw_col, cls in enumerate(classes):
        if 0 <= cls < output_units:
            aligned[:, cls] = raw[:, raw_col]
    row_sums = aligned.sum(axis=1)
    missing = row_sums <= 0
    if np.any(missing):
        aligned[missing, :] = 1.0 / output_units
        row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def binary_metrics(y_true: Sequence[int], probs: np.ndarray, event_name: str) -> dict[str, float]:
    pred = [1 if value >= 0.5 else 0 for value in probs[:, 1]]
    tp = sum(
        1 for actual, guessed in zip(y_true, pred, strict=True) if actual == 1 and guessed == 1
    )
    fp = sum(
        1 for actual, guessed in zip(y_true, pred, strict=True) if actual == 0 and guessed == 1
    )
    fn = sum(
        1 for actual, guessed in zip(y_true, pred, strict=True) if actual == 1 and guessed == 0
    )
    tn = sum(
        1 for actual, guessed in zip(y_true, pred, strict=True) if actual == 0 and guessed == 0
    )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    total = tp + fp + fn + tn
    return {
        "val_accuracy": (tp + tn) / total if total else 0.0,
        f"val_{event_name}_precision": precision,
        f"val_{event_name}_recall": recall,
        f"val_{event_name}_f1": f1,
        f"val_{event_name}_ap": average_precision_score(y_true, probs[:, 1].tolist(), 1),
        f"val_{event_name}_support": float(sum(1 for item in y_true if item == 1)),
        f"val_{event_name}_predicted": float(sum(pred)),
        "val_event_f1": f1,
        "val_event_recall": recall,
    }


def multiclass_metrics(y_true: Sequence[int], probs: np.ndarray) -> dict[str, float]:
    guessed = [int(value) for value in np.argmax(probs, axis=1)]
    return classification_report_metrics(y_true, guessed, probs, 3)


def resolved_val_size(rows: int, requested: int, window_size: int) -> int:
    candidate = requested if requested > 0 else max(4, min(2000, rows // 10))
    min_train = max(8, min(rows // 4, 20 * window_size))
    return max(4, min(candidate, rows - min_train - window_size - 4))


def fold_plan(
    dataset: Any,
    rows: int,
    val_size: int,
    max_folds: int,
    sample_ends: Sequence[int],
    sample_label_ends: Sequence[int] | None,
):
    resolved = resolved_val_size(rows, val_size, dataset.role.window_size)
    plan = expanding_split(
        total_length=rows,
        val_size=resolved,
        step=resolved,
        min_train_size=max(8, min(rows // 4, 20 * dataset.role.window_size)),
        purge_gap=max(dataset.role.window_size - 1, 0),
        sample_end_indices=list(sample_ends),
        label_end_indices=list(sample_label_ends) if sample_label_ends is not None else None,
        window_size=dataset.role.window_size,
    )
    folds = list(plan.folds)
    return folds[-max_folds:] if max_folds > 0 else folds


def balance(labels: Sequence[int], output_mode: str) -> dict[str, int]:
    counts = Counter(int(label) for label in labels)
    if output_mode == "multiclass":
        return {CLASS_NAMES[index]: int(counts.get(index, 0)) for index in range(3)}
    return {"negative": int(counts.get(0, 0)), "positive": int(counts.get(1, 0))}


def model_id_for(booster: str, timeframe: str, output_mode: str, summary_mode: str) -> str:
    suffix = output_mode if output_mode != "multiclass" else "trend_signal"
    return f"gold_{suffix}_{booster}_{summary_mode}_{timeframe.lower()}"


def next_version(root: Path, model_id: str) -> int:
    return ModelCatalogue(root).next_version(model_id)


def save_artifact(
    args: argparse.Namespace,
    booster_name: str,
    model: Any,
    feature_names: Sequence[str],
    final_metrics: dict[str, float],
    rows: int,
    windows: int,
) -> Path:
    root = Path(args.storage_root)
    model_id = model_id_for(booster_name, args.timeframe, args.output_mode, args.summary_mode)
    version = next_version(root, model_id)
    payload = pickle.dumps(
        {
            "model": model,
            "feature_names": list(feature_names),
            "args": vars(args),
            "classes": [int(value) for value in getattr(model, "classes_", [])],
        }
    )
    artifact = ModelArtifact.create(
        model_id=ModelId(model_id),
        version=ModelVersion(version),
        framework=booster_name,
        framework_version=str(getattr(model, "__module__", booster_name)),
        format="pickle",
        payload=payload,
        training_run_id="trend_signal_booster",
    )
    FilesystemArtifactStore(root).save(artifact)
    record = ModelRecord(
        model_id=model_id,
        role="signal",
        symbol=args.symbol,
        timeframe=args.timeframe,
        version=version,
        rows=rows,
        windows=windows,
        window_size=args.window,
        feature_columns=len(feature_names),
        epochs=int(args.n_estimators),
        folds=args.folds,
        threshold=args.atr_mult,
        learning_rate=args.learning_rate,
        loss_function=f"{booster_name}_{args.output_mode}",
        horizon=args.label_horizon,
        metrics={key: float(value) for key, value in final_metrics.items()},
        note=(
            "Phase120 booster branch; tabular window summary; "
            f"output_mode={args.output_mode}; summary_mode={args.summary_mode}"
        ),
    )
    return ModelCatalogue(root).write(record)


def write_outputs(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    latest_json = out_dir / "latest.json"
    latest_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report  : {latest_json}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    rule("TREND_SIGNAL BOOSTER BRANCH")
    print(f"  symbol      : {args.symbol}")
    print(f"  timeframe   : {args.timeframe}")
    print(f"  booster     : {args.booster}")
    print(f"  output mode : {args.output_mode}")
    print(f"  summary     : {args.summary_mode}")
    print(f"  window      : {args.window}")
    print(f"  horizon     : {args.label_horizon}")
    print(f"  barrier     : {args.atr_mult}xATR14")

    try:
        candles_all = load_candles(Path(args.storage_root), args.symbol, args.timeframe)
        candles = training_prefix(candles_all, args.train_ratio, args.window)
        role, dataset = prepare_dataset(args, candles)
        if dataset.sample_ends is None:
            raise RuntimeError("trend_signal dataset did not expose sample_ends")
        labels_raw = [
            int(round(dataset.series[index][dataset.target_columns[0]]))
            for index in dataset.sample_ends
        ]
        sample_label_ends = list(dataset.sample_label_ends or [])
        if args.max_samples and args.max_samples > 0:
            keep = min(args.max_samples, len(labels_raw))
            sample_ends = dataset.sample_ends[-keep:]
            sample_label_ends = sample_label_ends[-keep:] if sample_label_ends else []
            labels_raw = labels_raw[-keep:]
        else:
            sample_ends = list(dataset.sample_ends)

        rule("WINDOW SUMMARY")
        summary = summarise_windows(
            series=dataset.series,
            feature_count=dataset.feature_count,
            column_names=dataset.column_names,
            sample_ends=sample_ends,
            window_size=role.window_size,
            mode=args.summary_mode,
        )
        y_all = labels_for_mode(labels_raw, args.output_mode)
        output_units = 3 if args.output_mode == "multiclass" else 2
        print(f"  samples     : {summary.rows:,}")
        print(f"  features    : {summary.columns:,}")
        print(f"  raw labels  : {balance(labels_raw, 'multiclass')}")
        print(f"  train labels: {balance(y_all.tolist(), args.output_mode)}")

        folds = fold_plan(
            dataset,
            len(sample_ends),
            args.val_size,
            args.folds,
            sample_ends,
            sample_label_ends or None,
        )
        if not folds:
            raise RuntimeError("No roll-forward folds could be built")

        rule("ROLL-FORWARD BOOSTER TRAINING")
        best_score = float("-inf")
        best_model: Any = None
        best_metrics: dict[str, float] = {}
        best_booster_name = ""
        fold_results: list[FoldResult] = []

        for fold_no, fold in enumerate(folds, start=1):
            x_train = summary.values[fold.train_start : fold.train_end]
            y_train = y_all[fold.train_start : fold.train_end]
            x_val = summary.values[fold.val_start : fold.val_end]
            y_val = y_all[fold.val_start : fold.val_end]
            booster_name, model = make_model(args, args.output_mode)
            weights = sample_weights(
                y_train.tolist(), class_weights(y_train.tolist(), output_units, args.class_weight)
            )
            fit_kwargs: dict[str, Any] = {}
            if weights is not None:
                fit_kwargs["sample_weight"] = weights
            model.fit(x_train, y_train, **fit_kwargs)
            probs = aligned_predict_proba(model, x_val, output_units)
            metrics = (
                multiclass_metrics(y_val.tolist(), probs)
                if args.output_mode == "multiclass"
                else binary_metrics(y_val.tolist(), probs, args.output_mode)
            )
            score_name = (
                "val_action_min_f1_supported"
                if args.output_mode == "multiclass"
                else "val_event_f1"
            )
            score = float(metrics.get(score_name, 0.0))
            if score > best_score:
                best_score = score
                best_model = model
                best_metrics = metrics
                best_booster_name = booster_name
            result = FoldResult(
                fold=fold_no,
                train_start=fold.train_start,
                train_end=fold.train_end,
                val_start=fold.val_start,
                val_end=fold.val_end,
                purged_train_samples=int(getattr(fold, "purged_train_samples", 0)),
                metrics={key: float(value) for key, value in metrics.items()},
                train_balance=balance(y_train.tolist(), args.output_mode),
                val_balance=balance(y_val.tolist(), args.output_mode),
            )
            fold_results.append(result)
            print(
                f"  fold {fold_no}/{len(folds)} "
                f"train[{fold.train_start}:{fold.train_end}] -> "
                f"val[{fold.val_start}:{fold.val_end}] purged={result.purged_train_samples}"
            )
            print(f"    train balance: {result.train_balance}")
            print(f"    val balance  : {result.val_balance}")
            print(f"    score {score_name}: {score:.6f}")
            if args.output_mode == "multiclass":
                print(
                    "    sell/buy F1 : "
                    f"{metrics.get('val_sell_f1', 0.0):.4f} / "
                    f"{metrics.get('val_buy_f1', 0.0):.4f} | "
                    f"collapse={metrics.get('val_action_collapse', 0.0):.0f}"
                )
            else:
                print(
                    f"    {args.output_mode} P/R/F1: "
                    f"{metrics.get(f'val_{args.output_mode}_precision', 0.0):.1%} / "
                    f"{metrics.get(f'val_{args.output_mode}_recall', 0.0):.1%} / "
                    f"{metrics.get(f'val_{args.output_mode}_f1', 0.0):.4f}"
                )

        if best_model is None:
            raise RuntimeError("No booster model was trained")

        record_path = None
        if args.save_record:
            record_path = save_artifact(
                args,
                best_booster_name,
                best_model,
                summary.feature_names,
                best_metrics,
                rows=len(dataset.series),
                windows=len(sample_ends),
            )
            print(f"\n  SAVED booster branch: {record_path}")

        report = {
            "args": vars(args),
            "booster": best_booster_name,
            "best_score": best_score,
            "best_metrics": best_metrics,
            "record_path": str(record_path) if record_path else "",
            "folds": [asdict(item) for item in fold_results],
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        write_outputs(args, report)
        rule("DONE")
        print(f"  best score : {best_score:.6f}")
        print(f"  elapsed    : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
