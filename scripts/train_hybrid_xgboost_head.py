"""Train the final hybrid XGBoost/LightGBM head on Phase 123 matrix.

Phase 124 consumes the matrix produced by
``scripts/build_hybrid_xgboost_matrix.py``. That matrix already contains
base-model outputs (booster specialists, optional WaveNet) and range-model
room features. This script trains a small final tree head that learns how
to combine those signals into SELL/HOLD/BUY while reporting collapse-safe
metrics.
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
import pandas as pd

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import classification_report_metrics

DEFAULT_STORAGE = REPO_ROOT / "datasets"
CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2
CLASS_NAMES = {CLASS_SELL: "sell", CLASS_HOLD: "hold", CLASS_BUY: "buy"}
BOOSTER_CHOICES = ("auto", "lightgbm", "xgboost", "catboost")
CLASS_WEIGHT_CHOICES = ("auto", "off")
IDENTITY_COLUMNS = {"timestamp", "source_index", "sample_end", "label"}


@dataclass(frozen=True)
class HybridHeadReport:
    model_id: str
    version: int
    matrix_path: str
    rows: int
    feature_columns: int
    train_rows: int
    val_rows: int
    booster: str
    metrics: dict[str, float]
    train_balance: dict[str, int]
    val_balance: dict[str, int]
    record_path: str


class MissingBoosterDependency(RuntimeError):
    """Raised when the selected optional booster backend is unavailable."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train final hybrid XGBoost/LightGBM head from hybrid matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="")
    parser.add_argument("--booster", choices=BOOSTER_CHOICES, default="auto")
    parser.add_argument("--class-weight", choices=CLASS_WEIGHT_CHOICES, default="auto")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--drop-price-levels", choices=("0", "1"), default="1")
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--min-samples", type=int, default=500)
    parser.add_argument("--save-record", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default="run_logs/hybrid_xgboost_head")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def class_counts(labels: Sequence[int]) -> dict[str, int]:
    counts = Counter(int(label) for label in labels)
    return {name: int(counts.get(index, 0)) for index, name in CLASS_NAMES.items()}


def default_matrix_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_xgboost_matrix_latest.parquet"


def default_model_id(booster: str, timeframe: str) -> str:
    return f"gold_hybrid_{booster}_head_{timeframe.lower()}"


def feature_columns(frame: pd.DataFrame, drop_price_levels: bool) -> list[str]:
    columns: list[str] = []
    for column in frame.columns:
        if column in IDENTITY_COLUMNS:
            continue
        if drop_price_levels and (column == "close" or column.endswith("_price")):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            columns.append(column)
    return columns


def split_indices(rows: int, train_frac: float, min_samples: int) -> tuple[np.ndarray, np.ndarray]:
    if rows < min_samples:
        raise RuntimeError(f"Hybrid matrix has only {rows} rows; need at least {min_samples}")
    if not 0.1 <= train_frac <= 0.9:
        raise RuntimeError("train-frac must be in [0.1, 0.9]")
    split = int(rows * train_frac)
    split = max(1, min(rows - 1, split))
    return np.arange(split), np.arange(split, rows)


def class_weights(labels: Sequence[int], classes: int, mode: str) -> dict[int, float] | None:
    if mode != "auto":
        return None
    counts = Counter(int(label) for label in labels)
    total = sum(counts.values())
    if total <= 0:
        return None
    return {
        cls: total / (classes * count)
        for cls, count in counts.items()
        if count > 0 and 0 <= cls < classes
    }


def sample_weights(labels: Sequence[int], weights: dict[int, float] | None) -> np.ndarray | None:
    if not weights:
        return None
    return np.asarray([weights.get(int(label), 1.0) for label in labels], dtype=np.float32)


def _lightgbm_model(args: argparse.Namespace):
    try:
        from lightgbm import LGBMClassifier
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install LightGBM: pip install lightgbm") from exc
    return LGBMClassifier(
        objective="multiclass",
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


def _xgboost_model(args: argparse.Namespace):
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install XGBoost: pip install xgboost") from exc
    return XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        max_depth=args.max_depth,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        eval_metric="mlogloss",
        tree_method="hist",
    )


def _catboost_model(args: argparse.Namespace):
    try:
        from catboost import CatBoostClassifier
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install CatBoost: pip install catboost") from exc
    return CatBoostClassifier(
        loss_function="MultiClass",
        iterations=args.n_estimators,
        learning_rate=args.learning_rate,
        depth=max(1, args.max_depth),
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )


def make_model(args: argparse.Namespace) -> tuple[str, Any]:
    requested = [args.booster] if args.booster != "auto" else ["lightgbm", "xgboost", "catboost"]
    failures: list[str] = []
    for name in requested:
        try:
            if name == "lightgbm":
                return name, _lightgbm_model(args)
            if name == "xgboost":
                return name, _xgboost_model(args)
            if name == "catboost":
                return name, _catboost_model(args)
        except MissingBoosterDependency as error:
            failures.append(str(error))
    raise MissingBoosterDependency(
        "No requested booster backend is installed. Install one of: "
        "pip install lightgbm xgboost catboost. " + " | ".join(failures)
    )


def aligned_predict_proba(model: Any, x_values: np.ndarray) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    aligned = np.zeros((len(raw), 3), dtype=np.float64)
    for raw_col, cls in enumerate(classes):
        if 0 <= cls < 3:
            aligned[:, cls] = raw[:, raw_col]
    row_sums = aligned.sum(axis=1)
    missing = row_sums <= 0
    if np.any(missing):
        aligned[missing, :] = 1.0 / 3.0
        row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def save_artifact(
    args: argparse.Namespace,
    booster_name: str,
    model: Any,
    features: Sequence[str],
    metrics: dict[str, float],
    rows: int,
    matrix_path: Path,
) -> tuple[str, int, str]:
    storage_root = Path(args.storage_root)
    model_id = args.model_id.strip() or default_model_id(booster_name, args.timeframe)
    catalogue = ModelCatalogue(storage_root)
    version = catalogue.next_version(model_id)
    payload = pickle.dumps(
        {
            "model": model,
            "feature_names": list(features),
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
        training_run_id="hybrid_xgboost_head",
    )
    FilesystemArtifactStore(storage_root).save(artifact)
    record = ModelRecord(
        model_id=model_id,
        role="signal",
        symbol=args.symbol,
        timeframe=args.timeframe,
        version=version,
        rows=rows,
        windows=rows,
        window_size=1,
        feature_columns=len(features),
        epochs=int(args.n_estimators),
        folds=1,
        threshold=0.0,
        learning_rate=float(args.learning_rate),
        loss_function=f"hybrid_{booster_name}_multiclass",
        horizon=0,
        metrics={key: float(value) for key, value in metrics.items()},
        note=f"Phase124 hybrid head trained on {matrix_path}",
    )
    record_path = catalogue.write(record)
    return model_id, version, str(record_path)


def write_outputs(
    args: argparse.Namespace, report: HybridHeadReport, feature_names: Sequence[str]
) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"args": vars(args), "report": asdict(report), "feature_names": list(feature_names)}
    (out_dir / "latest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        matrix_path = (
            Path(args.matrix_path)
            if args.matrix_path
            else default_matrix_path(Path(args.storage_root), args.symbol, args.timeframe)
        )
        rule("HYBRID XGBOOST HEAD")
        print(f"  matrix      : {matrix_path}")
        print(f"  booster     : {args.booster}")
        print(f"  train frac  : {args.train_frac:.2f}")
        frame = pd.read_parquet(matrix_path)
        if "label" not in frame.columns:
            raise RuntimeError("Hybrid matrix must contain a label column")
        features = feature_columns(frame, args.drop_price_levels == "1")
        if not features:
            raise RuntimeError("No numeric feature columns found in the hybrid matrix")
        y = frame["label"].astype(int).to_numpy()
        x = frame[features].replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=np.float32)
        train_idx, val_idx = split_indices(len(frame), args.train_frac, args.min_samples)
        x_train, y_train = x[train_idx], y[train_idx]
        x_val, y_val = x[val_idx], y[val_idx]
        booster_name, model = make_model(args)
        weights = sample_weights(
            y_train.tolist(), class_weights(y_train.tolist(), 3, args.class_weight)
        )
        fit_kwargs: dict[str, Any] = {}
        if weights is not None:
            fit_kwargs["sample_weight"] = weights
        model.fit(x_train, y_train, **fit_kwargs)
        probs = aligned_predict_proba(model, x_val)
        guessed = [int(value) for value in np.argmax(probs, axis=1)]
        metrics = classification_report_metrics(y_val.tolist(), guessed, probs, 3)

        rule("QUALITY")
        print(f"  rows/features : {len(frame):,} / {len(features):,}")
        print(f"  train/val     : {len(train_idx):,} / {len(val_idx):,}")
        print(f"  train balance : {class_counts(y_train.tolist())}")
        print(f"  val balance   : {class_counts(y_val.tolist())}")
        print(f"  val_accuracy  : {metrics.get('val_accuracy_from_confusion', 0.0):.1%}")
        print(f"  macro_f1      : {metrics.get('val_macro_f1', 0.0):.4f}")
        print(f"  action_min_f1 : {metrics.get('val_action_min_f1_supported', 0.0):.4f}")
        print(f"  action_collapse: {metrics.get('val_action_collapse', 0.0):.0f}")
        for name in ("sell", "hold", "buy"):
            print(
                f"  {name:<4} P/R/F1  : "
                f"{metrics.get(f'val_{name}_precision', 0.0):.1%} / "
                f"{metrics.get(f'val_{name}_recall', 0.0):.1%} / "
                f"{metrics.get(f'val_{name}_f1', 0.0):.4f}"
            )

        model_id = args.model_id.strip() or default_model_id(booster_name, args.timeframe)
        version = 0
        record_path = ""
        if args.save_record == "1":
            model_id, version, record_path = save_artifact(
                args, booster_name, model, features, metrics, len(frame), matrix_path
            )
            print(f"\n  SAVED hybrid head: {record_path}")

        report = HybridHeadReport(
            model_id=model_id,
            version=version,
            matrix_path=str(matrix_path),
            rows=len(frame),
            feature_columns=len(features),
            train_rows=len(train_idx),
            val_rows=len(val_idx),
            booster=booster_name,
            metrics={key: float(value) for key, value in metrics.items()},
            train_balance=class_counts(y_train.tolist()),
            val_balance=class_counts(y_val.tolist()),
            record_path=record_path,
        )
        write_outputs(args, report, features)
        rule("DONE")
        print(f"  report : {Path(args.output_dir) / 'latest.json'}")
        print(f"  elapsed: {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
