"""Phase128: train a LightGBM/CatBoost/XGBoost meta-labeler on telemetry features."""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
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

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_meta_labeler")
BOOSTER_CHOICES = ("auto", "lightgbm", "xgboost", "catboost")
TASKS = ("classifier", "regressor")
TARGET_COLUMNS = {
    "classifier": "target_trade_win",
    "regressor": "target_trade_score_r",
}
IDENTITY_OR_TARGET_COLUMNS = {
    "timestamp",
    "source_index",
    "label",
    "close",
    "target_trade_win",
    "target_trade_score_r",
    "target_trade_pnl",
    "target_side",
    "target_exit_index",
    "target_outcome_code",
    "candidate_mask",
}


@dataclass(frozen=True)
class MetaTrainReport:
    model_id: str
    version: int
    flat_path: str
    task: str
    target: str
    rows: int
    feature_columns: int
    train_rows: int
    val_rows: int
    test_rows: int
    candidate_only: str
    booster: str
    metrics: dict[str, float]
    record_path: str


class MissingBoosterDependency(RuntimeError):
    """Raised when the selected optional booster backend is unavailable."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Phase128 hybrid telemetry meta-labeler baseline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="")
    parser.add_argument("--task", choices=TASKS, default="classifier")
    parser.add_argument("--target", default="", help="empty = task default")
    parser.add_argument("--booster", choices=BOOSTER_CHOICES, default="auto")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--min-samples", type=int, default=200)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--meta-threshold", type=float, default=0.55)
    parser.add_argument("--score-threshold", type=float, default=0.0)
    parser.add_argument("--save-record", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def default_model_id(task: str, booster: str, timeframe: str) -> str:
    stem = "meta" if task == "classifier" else "score"
    return f"gold_hybrid_{stem}_{booster}_{timeframe.lower()}"


def target_column(args: argparse.Namespace) -> str:
    return args.target.strip() or TARGET_COLUMNS[args.task]


def feature_columns(frame: pd.DataFrame) -> list[str]:
    columns: list[str] = []
    for column in frame.columns:
        if column in IDENTITY_OR_TARGET_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            columns.append(column)
    return columns


def load_frame(path: Path, args: argparse.Namespace) -> pd.DataFrame:
    frame = pd.read_parquet(path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    target = target_column(args)
    if target not in frame.columns:
        raise RuntimeError(f"Telemetry flat matrix is missing target column: {target}")
    if args.candidate_only == "1":
        if "candidate_mask" not in frame.columns:
            raise RuntimeError("candidate-only training needs candidate_mask column")
        frame = frame[frame["candidate_mask"].astype(float) >= 0.5].copy()
    if len(frame) < args.min_samples:
        raise RuntimeError(
            f"Only {len(frame)} rows after filtering; need at least {args.min_samples}"
        )
    return frame.reset_index(drop=True)


def split_indices(
    rows: int, train_frac: float, val_frac: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not 0.2 <= train_frac <= 0.9:
        raise RuntimeError("train-frac must be in [0.2, 0.9]")
    if not 0.05 <= val_frac <= 0.4:
        raise RuntimeError("val-frac must be in [0.05, 0.4]")
    if train_frac + val_frac >= 0.95:
        raise RuntimeError("train-frac + val-frac must leave at least 5% test rows")
    train_end = max(1, int(rows * train_frac))
    val_end = max(train_end + 1, int(rows * (train_frac + val_frac)))
    val_end = min(val_end, rows - 1)
    return np.arange(train_end), np.arange(train_end, val_end), np.arange(val_end, rows)


def class_weights(labels: Sequence[int], mode: str) -> dict[int, float] | None:
    if mode != "auto":
        return None
    positives = sum(1 for value in labels if int(value) == 1)
    negatives = len(labels) - positives
    if positives <= 0 or negatives <= 0:
        return None
    total = float(len(labels))
    return {0: total / (2.0 * negatives), 1: total / (2.0 * positives)}


def sample_weights(labels: Sequence[int], weights: dict[int, float] | None) -> np.ndarray | None:
    if not weights:
        return None
    return np.asarray([weights.get(int(value), 1.0) for value in labels], dtype=np.float32)


def _lightgbm_model(args: argparse.Namespace):
    try:
        from lightgbm import LGBMClassifier, LGBMRegressor
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install LightGBM: pip install lightgbm") from exc
    common = dict(
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
    if args.task == "classifier":
        return LGBMClassifier(objective="binary", **common)
    return LGBMRegressor(objective="regression", **common)


def _xgboost_model(args: argparse.Namespace):
    try:
        from xgboost import XGBClassifier, XGBRegressor
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install XGBoost: pip install xgboost") from exc
    common = dict(
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        max_depth=args.max_depth,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    if args.task == "classifier":
        return XGBClassifier(objective="binary:logistic", eval_metric="logloss", **common)
    return XGBRegressor(objective="reg:squarederror", eval_metric="rmse", **common)


def _catboost_model(args: argparse.Namespace):
    try:
        from catboost import CatBoostClassifier, CatBoostRegressor
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingBoosterDependency("Install CatBoost: pip install catboost") from exc
    common = dict(
        iterations=args.n_estimators,
        learning_rate=args.learning_rate,
        depth=max(args.max_depth, 1),
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )
    if args.task == "classifier":
        return CatBoostClassifier(loss_function="Logloss", **common)
    return CatBoostRegressor(loss_function="RMSE", **common)


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
        "No requested booster backend is installed. Install one of: lightgbm, xgboost, catboost. "
        + " | ".join(failures)
    )


def positive_scores(model: Any, x_values: np.ndarray, task: str) -> np.ndarray:
    if task == "regressor":
        return np.asarray(model.predict(x_values), dtype=np.float64)
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    if raw.ndim == 1:
        return raw
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    for raw_col, cls in enumerate(classes):
        if cls == 1:
            return raw[:, raw_col]
    return raw[:, -1]


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    positives = int(np.sum(y_true == 1))
    if positives <= 0:
        return 0.0
    order = np.argsort(-scores)
    sorted_true = y_true[order]
    hits = 0
    precision_sum = 0.0
    for rank, value in enumerate(sorted_true, start=1):
        if int(value) == 1:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / positives


def classifier_metrics(
    y_true: np.ndarray, scores: np.ndarray, threshold: float, prefix: str
) -> dict[str, float]:
    pred = (scores >= threshold).astype(int)
    tp = int(np.sum((pred == 1) & (y_true == 1)))
    fp = int(np.sum((pred == 1) & (y_true == 0)))
    tn = int(np.sum((pred == 0) & (y_true == 0)))
    fn = int(np.sum((pred == 0) & (y_true == 1)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        f"{prefix}_accuracy": (tp + tn) / len(y_true) if len(y_true) else 0.0,
        f"{prefix}_precision": precision,
        f"{prefix}_recall": recall,
        f"{prefix}_f1": f1,
        f"{prefix}_ap": average_precision(y_true.astype(int), scores),
        f"{prefix}_positive_rate": float(np.mean(pred == 1)) if len(pred) else 0.0,
        f"{prefix}_base_rate": float(np.mean(y_true == 1)) if len(y_true) else 0.0,
        f"{prefix}_tp": float(tp),
        f"{prefix}_fp": float(fp),
        f"{prefix}_tn": float(tn),
        f"{prefix}_fn": float(fn),
    }


def regression_metrics(
    y_true: np.ndarray, pred: np.ndarray, threshold: float, prefix: str
) -> dict[str, float]:
    error = pred - y_true
    selected = pred >= threshold
    return {
        f"{prefix}_mae": float(np.mean(np.abs(error))) if len(error) else 0.0,
        f"{prefix}_mse": float(np.mean(error * error)) if len(error) else 0.0,
        f"{prefix}_pred_mean": float(np.mean(pred)) if len(pred) else 0.0,
        f"{prefix}_target_mean": float(np.mean(y_true)) if len(y_true) else 0.0,
        f"{prefix}_selected_rate": float(np.mean(selected)) if len(selected) else 0.0,
        f"{prefix}_selected_target_mean": (
            float(np.mean(y_true[selected])) if np.any(selected) else 0.0
        ),
    }


def compute_metrics(
    args: argparse.Namespace,
    y_val: np.ndarray,
    s_val: np.ndarray,
    y_test: np.ndarray,
    s_test: np.ndarray,
) -> dict[str, float]:
    if args.task == "classifier":
        return {
            **classifier_metrics(y_val.astype(int), s_val, args.meta_threshold, "val"),
            **classifier_metrics(y_test.astype(int), s_test, args.meta_threshold, "test"),
        }
    return {
        **regression_metrics(y_val, s_val, args.score_threshold, "val"),
        **regression_metrics(y_test, s_test, args.score_threshold, "test"),
    }


def save_artifact(
    args: argparse.Namespace,
    booster_name: str,
    model: Any,
    features: Sequence[str],
    metrics: dict[str, float],
    rows: int,
    flat_path: Path,
) -> tuple[str, int, str]:
    storage_root = Path(args.storage_root)
    model_id = args.model_id.strip() or default_model_id(args.task, booster_name, args.timeframe)
    catalogue = ModelCatalogue(storage_root)
    version = catalogue.next_version(model_id)
    payload = pickle.dumps(
        {
            "model": model,
            "feature_names": list(features),
            "args": vars(args),
            "task": args.task,
            "target": target_column(args),
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
        training_run_id="hybrid_meta_labeler",
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
        loss_function=f"phase128_{args.task}_{booster_name}",
        horizon=0,
        metrics={key: float(value) for key, value in metrics.items()},
        note=f"Phase128 {args.task} trained on {flat_path}",
    )
    if args.task == "classifier":
        record.decision_thresholds = {
            "meta_threshold": float(args.meta_threshold),
            "selected_by": "phase128_initial_training",
            "target": target_column(args),
        }
    else:
        record.decision_thresholds = {
            "score_threshold": float(args.score_threshold),
            "selected_by": "phase128_initial_training",
            "target": target_column(args),
        }
    record_path = catalogue.write(record)
    return model_id, version, str(record_path)


def write_report(
    args: argparse.Namespace, report: MetaTrainReport, features: Sequence[str]
) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(
        json.dumps(
            {"args": vars(args), "report": asdict(report), "feature_names": list(features)},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        flat_path = (
            Path(args.flat_path)
            if args.flat_path
            else default_flat_path(Path(args.storage_root), args.symbol, args.timeframe)
        )
        rule("PHASE128 HYBRID META-LABELER")
        print(f"  flat        : {flat_path}")
        print(f"  task/target : {args.task} / {target_column(args)}")
        frame = load_frame(flat_path, args)
        features = feature_columns(frame)
        if not features:
            raise RuntimeError("No online-safe numeric feature columns found")
        train_idx, val_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac)
        x = frame[features].to_numpy(dtype=np.float32)
        y = frame[target_column(args)].to_numpy(dtype=np.float32)
        booster_name, model = make_model(args)
        print(f"  booster     : {booster_name}")
        print(f"  rows        : {len(frame):,}")
        print(f"  features    : {len(features):,}")
        print(f"  split       : {len(train_idx):,}/{len(val_idx):,}/{len(test_idx):,}")

        fit_kwargs: dict[str, Any] = {}
        if args.task == "classifier":
            weights = class_weights(y[train_idx].astype(int).tolist(), args.class_weight)
            sample_weight = sample_weights(y[train_idx].astype(int).tolist(), weights)
            if sample_weight is not None:
                fit_kwargs["sample_weight"] = sample_weight
            model.fit(x[train_idx], y[train_idx].astype(int), **fit_kwargs)
        else:
            model.fit(x[train_idx], y[train_idx], **fit_kwargs)

        val_scores = positive_scores(model, x[val_idx], args.task)
        test_scores = positive_scores(model, x[test_idx], args.task)
        metrics = compute_metrics(args, y[val_idx], val_scores, y[test_idx], test_scores)

        model_id = args.model_id.strip() or default_model_id(
            args.task, booster_name, args.timeframe
        )
        version = 0
        record_path = ""
        if args.save_record == "1":
            model_id, version, record_path = save_artifact(
                args, booster_name, model, features, metrics, len(frame), flat_path
            )
            print(f"  saved       : {record_path}")

        report = MetaTrainReport(
            model_id=model_id,
            version=version,
            flat_path=str(flat_path),
            task=args.task,
            target=target_column(args),
            rows=len(frame),
            feature_columns=len(features),
            train_rows=len(train_idx),
            val_rows=len(val_idx),
            test_rows=len(test_idx),
            candidate_only=args.candidate_only,
            booster=booster_name,
            metrics={key: float(value) for key, value in metrics.items()},
            record_path=record_path,
        )
        write_report(args, report, features)
        rule("DONE")
        for key, value in metrics.items():
            print(f"  {key:<28}: {value:.6f}")
        print(f"  report      : {Path(args.output_dir) / 'latest.json'}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
