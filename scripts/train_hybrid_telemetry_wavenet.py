"""Phase129A: train a WaveNet/TCN meta model on the Phase127 telemetry tensor."""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import json
import pickle
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_telemetry_wavenet")
TASKS = ("classifier", "regressor", "multihead")
MONITOR_CHOICES = (
    "auto",
    "val_loss",
    "val_meta_win_ap",
    "val_meta_win_precision",
    "val_score_r_mae",
)


@dataclass(frozen=True)
class TelemetryWaveNetReport:
    model_id: str
    version: int
    tensor_path: str
    task: str
    rows: int
    tensor_window: int
    channels: int
    train_rows: int
    val_rows: int
    test_rows: int
    candidate_only: str
    purge_gap: int
    metrics: dict[str, float]
    record_path: str


class MissingTensorFlow(RuntimeError):
    """Raised when TensorFlow is not installed for Phase129."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Phase129 WaveNet/TCN model on a Phase127 telemetry tensor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_telemetry_wavenet_5m")
    parser.add_argument("--task", choices=TASKS, default="multihead")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all selected samples")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--filters", type=int, default=48)
    parser.add_argument("--kernel-size", type=int, default=3)
    parser.add_argument("--n-layers", type=int, default=5)
    parser.add_argument("--n-blocks", type=int, default=2)
    parser.add_argument("--dense-units", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=0.20)
    parser.add_argument("--score-loss-weight", type=float, default=0.50)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--meta-threshold", type=float, default=0.55)
    parser.add_argument("--score-threshold", type=float, default=0.0)
    parser.add_argument("--monitor-metric", choices=MONITOR_CHOICES, default="auto")
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--save-record", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_tensor_latest.npz"


def require_tensorflow():
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise MissingTensorFlow(
            "TensorFlow is required for Phase129. Install: pip install -r requirements-ai.txt"
        ) from exc
    return tf


def load_tensor(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Telemetry tensor not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def selected_indices(data: Mapping[str, Any], candidate_only: str, max_samples: int) -> np.ndarray:
    rows = int(len(data["X"]))
    indices = np.arange(rows, dtype=np.int64)
    if candidate_only == "1":
        mask = np.asarray(data.get("candidate_mask", np.ones(rows)), dtype=np.float32)
        indices = indices[mask >= 0.5]
    if max_samples > 0 and len(indices) > max_samples:
        step = max(1, len(indices) // max_samples)
        indices = indices[::step][:max_samples]
    if len(indices) < 50:
        raise RuntimeError(f"Only {len(indices)} tensor samples selected; need at least 50")
    return indices


def split_indices(
    rows: int,
    train_frac: float,
    val_frac: float,
    purge_gap: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not 0.2 <= train_frac <= 0.9:
        raise RuntimeError("train-frac must be in [0.2, 0.9]")
    if not 0.05 <= val_frac <= 0.4:
        raise RuntimeError("val-frac must be in [0.05, 0.4]")
    if train_frac + val_frac >= 0.95:
        raise RuntimeError("train-frac + val-frac must leave at least 5% test rows")
    train_end = int(rows * train_frac)
    val_end = int(rows * (train_frac + val_frac))
    gap = max(int(purge_gap), 0)
    train_idx = np.arange(0, max(1, train_end), dtype=np.int64)
    val_start = min(rows, train_end + gap)
    val_idx = np.arange(val_start, max(val_start, val_end), dtype=np.int64)
    test_start = min(rows, val_end + gap)
    test_idx = np.arange(test_start, rows, dtype=np.int64)
    if len(val_idx) < 1 or len(test_idx) < 1:
        raise RuntimeError(
            "Purge gap left no validation/test rows. Lower --purge-gap, lower --train-frac/--val-frac, or build more tensor samples."
        )
    return train_idx, val_idx, test_idx


def normalize_train_only(
    x_values: np.ndarray,
    train_idx: Sequence[int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train = x_values[np.asarray(train_idx, dtype=np.int64)].astype(np.float32)
    mean = np.mean(train, axis=(0, 1), keepdims=True)
    std = np.std(train, axis=(0, 1), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    normalized = (x_values.astype(np.float32) - mean) / std
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    return normalized, mean.astype(np.float32), std.astype(np.float32)


def class_weights(labels: Sequence[float], mode: str) -> dict[int, float] | None:
    if mode != "auto":
        return None
    y = [int(round(value)) for value in labels]
    positives = sum(1 for value in y if value == 1)
    negatives = len(y) - positives
    if positives <= 0 or negatives <= 0:
        return None
    total = float(len(y))
    return {0: total / (2.0 * negatives), 1: total / (2.0 * positives)}


def sample_weights(labels: Sequence[float], weights: dict[int, float] | None) -> np.ndarray | None:
    if not weights:
        return None
    return np.asarray([weights.get(int(round(value)), 1.0) for value in labels], dtype=np.float32)


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
    y = y_true.astype(int)
    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        f"{prefix}_meta_accuracy": (tp + tn) / len(y) if len(y) else 0.0,
        f"{prefix}_meta_precision": precision,
        f"{prefix}_meta_recall": recall,
        f"{prefix}_meta_f1": f1,
        f"{prefix}_meta_ap": average_precision(y, scores),
        f"{prefix}_meta_positive_rate": float(np.mean(pred == 1)) if len(pred) else 0.0,
        f"{prefix}_meta_prob_mean": float(np.mean(scores)) if len(scores) else 0.0,
        f"{prefix}_meta_prob_stdev": float(np.std(scores)) if len(scores) else 0.0,
        f"{prefix}_meta_collapse": 1.0 if len(scores) and float(np.std(scores)) < 1e-6 else 0.0,
    }


def regression_metrics(
    y_true: np.ndarray, pred: np.ndarray, threshold: float, prefix: str
) -> dict[str, float]:
    error = pred - y_true
    selected = pred >= threshold
    return {
        f"{prefix}_score_mae": float(np.mean(np.abs(error))) if len(error) else 0.0,
        f"{prefix}_score_mse": float(np.mean(error * error)) if len(error) else 0.0,
        f"{prefix}_score_pred_mean": float(np.mean(pred)) if len(pred) else 0.0,
        f"{prefix}_score_pred_stdev": float(np.std(pred)) if len(pred) else 0.0,
        f"{prefix}_score_target_mean": float(np.mean(y_true)) if len(y_true) else 0.0,
        f"{prefix}_score_selected_rate": float(np.mean(selected)) if len(selected) else 0.0,
        f"{prefix}_score_selected_target_mean": (
            float(np.mean(y_true[selected])) if np.any(selected) else 0.0
        ),
        f"{prefix}_score_collapse": 1.0 if len(pred) and float(np.std(pred)) < 1e-6 else 0.0,
    }


def build_wavenet_model(tf: Any, input_shape: tuple[int, int], args: argparse.Namespace):
    inputs = tf.keras.Input(shape=input_shape, name="telemetry_window")
    x = tf.keras.layers.Conv1D(args.filters, 1, padding="same", name="input_projection")(inputs)
    skips = []
    for block in range(max(args.n_blocks, 1)):
        for layer in range(max(args.n_layers, 1)):
            dilation = 2**layer
            prefix = f"b{block + 1}_l{layer + 1}_d{dilation}"
            tanh = tf.keras.layers.Conv1D(
                args.filters,
                args.kernel_size,
                padding="causal",
                dilation_rate=dilation,
                activation="tanh",
                name=f"{prefix}_tanh",
            )(x)
            gate = tf.keras.layers.Conv1D(
                args.filters,
                args.kernel_size,
                padding="causal",
                dilation_rate=dilation,
                activation="sigmoid",
                name=f"{prefix}_gate",
            )(x)
            z = tf.keras.layers.Multiply(name=f"{prefix}_gated")([tanh, gate])
            if args.dropout > 0:
                z = tf.keras.layers.Dropout(args.dropout, name=f"{prefix}_dropout")(z)
            z = tf.keras.layers.Conv1D(args.filters, 1, padding="same", name=f"{prefix}_skip")(z)
            x = tf.keras.layers.Add(name=f"{prefix}_residual")([x, z])
            skips.append(z)
    if len(skips) > 1:
        x = tf.keras.layers.Add(name="skip_sum")(skips)
    x = tf.keras.layers.Activation("relu", name="skip_relu")(x)
    x = tf.keras.layers.GlobalAveragePooling1D(name="global_pool")(x)
    x = tf.keras.layers.Dense(args.dense_units, activation="relu", name="dense")(x)
    if args.dropout > 0:
        x = tf.keras.layers.Dropout(args.dropout, name="dense_dropout")(x)

    outputs: Any
    losses: Any
    metrics: Any
    loss_weights: Any = None
    if args.task == "classifier":
        outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="meta_win")(x)
        losses = "binary_crossentropy"
        metrics = [
            tf.keras.metrics.BinaryAccuracy(name="accuracy"),
            tf.keras.metrics.AUC(curve="PR", name="ap"),
        ]
    elif args.task == "regressor":
        outputs = tf.keras.layers.Dense(1, activation="linear", name="score_r")(x)
        losses = tf.keras.losses.Huber()
        metrics = [tf.keras.metrics.MeanAbsoluteError(name="mae")]
    else:
        outputs = {
            "meta_win": tf.keras.layers.Dense(1, activation="sigmoid", name="meta_win")(x),
            "score_r": tf.keras.layers.Dense(1, activation="linear", name="score_r")(x),
        }
        losses = {"meta_win": "binary_crossentropy", "score_r": tf.keras.losses.Huber()}
        loss_weights = {"meta_win": 1.0, "score_r": float(args.score_loss_weight)}
        metrics = {
            "meta_win": [
                tf.keras.metrics.BinaryAccuracy(name="accuracy"),
                tf.keras.metrics.AUC(curve="PR", name="ap"),
            ],
            "score_r": [tf.keras.metrics.MeanAbsoluteError(name="mae")],
        }

    try:
        optimizer = tf.keras.optimizers.AdamW(learning_rate=args.learning_rate, weight_decay=1e-5)
    except AttributeError:  # pragma: no cover
        optimizer = tf.keras.optimizers.Adam(learning_rate=args.learning_rate)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="hybrid_telemetry_wavenet")
    model.compile(optimizer=optimizer, loss=losses, loss_weights=loss_weights, metrics=metrics)
    return model


def target_payload(data: Mapping[str, Any], indices: Sequence[int], task: str) -> Any:
    idx = np.asarray(indices, dtype=np.int64)
    y_win = np.asarray(data["target_trade_win"], dtype=np.float32)[idx]
    y_score = np.asarray(data["target_trade_score_r"], dtype=np.float32)[idx]
    if task == "classifier":
        return y_win
    if task == "regressor":
        return y_score
    return {"meta_win": y_win, "score_r": y_score}


def sample_weight_payload(y_train: Any, args: argparse.Namespace) -> Any:
    if args.task == "regressor":
        return None
    labels = y_train["meta_win"] if isinstance(y_train, dict) else y_train
    weights = sample_weights(labels, class_weights(labels, args.class_weight))
    if weights is None:
        return None
    if args.task == "multihead":
        return {"meta_win": weights, "score_r": np.ones_like(weights, dtype=np.float32)}
    return weights


def prediction_arrays(model: Any, x_values: np.ndarray, task: str) -> tuple[np.ndarray, np.ndarray]:
    raw = model.predict(x_values, verbose=0)
    if task == "classifier":
        return np.asarray(raw, dtype=np.float64).reshape(-1), np.zeros(
            len(x_values), dtype=np.float64
        )
    if task == "regressor":
        return np.zeros(len(x_values), dtype=np.float64), np.asarray(raw, dtype=np.float64).reshape(
            -1
        )
    if isinstance(raw, Mapping):
        return (
            np.asarray(raw["meta_win"], dtype=np.float64).reshape(-1),
            np.asarray(raw["score_r"], dtype=np.float64).reshape(-1),
        )
    return (
        np.asarray(raw[0], dtype=np.float64).reshape(-1),
        np.asarray(raw[1], dtype=np.float64).reshape(-1),
    )


def compute_metrics(
    data: Mapping[str, Any],
    val_idx: Sequence[int],
    test_idx: Sequence[int],
    val_win: np.ndarray,
    val_score: np.ndarray,
    test_win: np.ndarray,
    test_score: np.ndarray,
    args: argparse.Namespace,
) -> dict[str, float]:
    y_val_win = np.asarray(data["target_trade_win"], dtype=np.float32)[np.asarray(val_idx)]
    y_test_win = np.asarray(data["target_trade_win"], dtype=np.float32)[np.asarray(test_idx)]
    y_val_score = np.asarray(data["target_trade_score_r"], dtype=np.float32)[np.asarray(val_idx)]
    y_test_score = np.asarray(data["target_trade_score_r"], dtype=np.float32)[np.asarray(test_idx)]
    metrics: dict[str, float] = {}
    if args.task in ("classifier", "multihead"):
        metrics.update(classifier_metrics(y_val_win, val_win, args.meta_threshold, "val"))
        metrics.update(classifier_metrics(y_test_win, test_win, args.meta_threshold, "test"))
    if args.task in ("regressor", "multihead"):
        metrics.update(regression_metrics(y_val_score, val_score, args.score_threshold, "val"))
        metrics.update(regression_metrics(y_test_score, test_score, args.score_threshold, "test"))
    return metrics


def monitor_name(args: argparse.Namespace) -> str:
    if args.monitor_metric != "auto":
        mapping = {
            "val_meta_win_ap": "val_meta_win_ap",
            "val_meta_win_precision": "val_meta_win_accuracy",
            "val_score_r_mae": "val_score_r_mae",
        }
        return mapping.get(args.monitor_metric, args.monitor_metric)
    if args.task == "classifier":
        return "val_ap"
    if args.task == "regressor":
        return "val_mae"
    return "val_loss"


def monitor_mode(name: str) -> str:
    if name.endswith("_ap") or name.endswith("_precision") or name.endswith("_accuracy"):
        return "max"
    return "min"


def serialize_model(model: Any) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.keras"
        model.save(path)
        return path.read_bytes()


def save_artifact(
    args: argparse.Namespace,
    tf: Any,
    model: Any,
    channel_names: Sequence[str],
    mean: np.ndarray,
    std: np.ndarray,
    metrics: dict[str, float],
    rows: int,
    tensor_path: Path,
) -> tuple[str, int, str]:
    storage_root = Path(args.storage_root)
    catalogue = ModelCatalogue(storage_root)
    model_id = args.model_id.strip() or "gold_hybrid_telemetry_wavenet_5m"
    version = catalogue.next_version(model_id)
    payload = pickle.dumps(
        {
            "model_bytes": serialize_model(model),
            "channel_names": list(channel_names),
            "scaler_mean": mean.astype(np.float32),
            "scaler_std": std.astype(np.float32),
            "args": vars(args),
            "task": args.task,
            "meta_threshold": float(args.meta_threshold),
            "score_threshold": float(args.score_threshold),
        }
    )
    artifact = ModelArtifact.create(
        model_id=ModelId(model_id),
        version=ModelVersion(version),
        framework="tensorflow",
        framework_version=str(getattr(tf, "__version__", "tensorflow")),
        format="pickle_keras",
        payload=payload,
        training_run_id="hybrid_telemetry_wavenet",
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
        window_size=int(args.n_layers),
        feature_columns=len(channel_names),
        epochs=int(args.epochs),
        folds=1,
        threshold=0.0,
        learning_rate=float(args.learning_rate),
        loss_function=f"phase129_{args.task}_wavenet_tcn",
        horizon=0,
        metrics={key: float(value) for key, value in metrics.items()},
        note=f"Phase129 WaveNet/TCN trained on {tensor_path}",
        decision_thresholds={
            "meta_threshold": float(args.meta_threshold),
            "score_threshold": float(args.score_threshold),
            "selected_by": "phase129_initial_training",
            "task": args.task,
        },
    )
    record_path = catalogue.write(record)
    return model_id, version, str(record_path)


def write_report(
    args: argparse.Namespace, report: TelemetryWaveNetReport, channel_names: Sequence[str]
) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(
        json.dumps(
            {"args": vars(args), "report": asdict(report), "channel_names": list(channel_names)},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        rule("PHASE129 TELEMETRY WAVENET/TCN")
        print(f"  tensor      : {tensor_path}")
        print(f"  task        : {args.task}")
        data = load_tensor(tensor_path)
        selected = selected_indices(data, args.candidate_only, args.max_samples)
        x_raw = np.asarray(data["X"], dtype=np.float32)[selected]
        channel_names = [
            str(value) for value in np.asarray(data["channel_names"], dtype=object).tolist()
        ]
        train_idx, val_idx, test_idx = split_indices(
            len(x_raw), args.train_frac, args.val_frac, args.purge_gap
        )
        x_values, mean, std = normalize_train_only(x_raw, train_idx)
        y_train = target_payload(data, selected[train_idx], args.task)
        y_val = target_payload(data, selected[val_idx], args.task)
        sample_weight = sample_weight_payload(y_train, args)
        tf = require_tensorflow()
        model = build_wavenet_model(tf, (x_values.shape[1], x_values.shape[2]), args)
        callbacks: list[Any] = []
        monitor = monitor_name(args)
        if args.early_stopping_patience > 0:
            callbacks.append(
                tf.keras.callbacks.EarlyStopping(
                    monitor=monitor,
                    mode=monitor_mode(monitor),
                    patience=args.early_stopping_patience,
                    restore_best_weights=True,
                )
            )
        print(f"  shape       : {list(x_values.shape)}")
        print(f"  split       : {len(train_idx):,}/{len(val_idx):,}/{len(test_idx):,}")
        print(f"  monitor     : {monitor}")
        fit_kwargs: dict[str, Any] = {}
        if sample_weight is not None:
            fit_kwargs["sample_weight"] = sample_weight
        model.fit(
            x_values[train_idx],
            y_train,
            validation_data=(x_values[val_idx], y_val),
            epochs=max(args.epochs, 1),
            batch_size=max(args.batch_size, 1),
            callbacks=callbacks,
            verbose=2,
            **fit_kwargs,
        )
        val_win, val_score = prediction_arrays(model, x_values[val_idx], args.task)
        test_win, test_score = prediction_arrays(model, x_values[test_idx], args.task)
        metrics = compute_metrics(
            data,
            selected[val_idx],
            selected[test_idx],
            val_win,
            val_score,
            test_win,
            test_score,
            args,
        )
        model_id = args.model_id.strip() or "gold_hybrid_telemetry_wavenet_5m"
        version = 0
        record_path = ""
        if args.save_record == "1":
            model_id, version, record_path = save_artifact(
                args, tf, model, channel_names, mean, std, metrics, len(x_raw), tensor_path
            )
            print(f"  saved       : {record_path}")
        report = TelemetryWaveNetReport(
            model_id=model_id,
            version=version,
            tensor_path=str(tensor_path),
            task=args.task,
            rows=len(x_raw),
            tensor_window=int(x_values.shape[1]),
            channels=int(x_values.shape[2]),
            train_rows=len(train_idx),
            val_rows=len(val_idx),
            test_rows=len(test_idx),
            candidate_only=args.candidate_only,
            purge_gap=max(args.purge_gap, 0),
            metrics={key: float(value) for key, value in metrics.items()},
            record_path=record_path,
        )
        write_report(args, report, channel_names)
        rule("DONE")
        for key, value in metrics.items():
            print(f"  {key:<30}: {value:.6f}")
        print(f"  report      : {Path(args.output_dir) / 'latest.json'}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
