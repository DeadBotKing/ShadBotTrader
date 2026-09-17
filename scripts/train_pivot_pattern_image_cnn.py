"""Phase143A: train Conv2D/Conv3D models on 4D pivot image tensors."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import html
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from train_pivot_pattern_wavenet import (
    average_precision,
    prediction_dict,
    require_tensorflow,
    selected_action,
)

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_image_cnn")
MODEL_KINDS = ("conv2d", "conv3d")


@dataclass(frozen=True)
class ImageCnnReport:
    model_id: str
    version: int
    model_kind: str
    tensor_path: str
    meta_path: str
    samples: int
    train_rows: int
    validation_rows: int
    test_rows: int
    stored_x_shape: list[int]
    keras_batch_shape: str
    metrics: dict[str, float]
    model_path: str
    record_path: str
    architecture_json_path: str
    model_summary_path: str
    epoch_checkpoint_path: str
    batch_log_path: str
    nonfinite_input_values: int
    output_json: str
    output_html: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Phase143A Conv2D/Conv3D model on 4D pivot image tensor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_image_cnn_5m")
    parser.add_argument("--model-kind", choices=MODEL_KINDS, default="conv2d")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--loader-mode", choices=("stream", "memory"), default="stream")
    parser.add_argument("--stream-chunk-size", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--filters", type=int, default=32)
    parser.add_argument("--kernel-size", type=int, default=3)
    parser.add_argument("--dense-units", type=int, default=96)
    parser.add_argument("--dropout", type=float, default=0.20)
    parser.add_argument("--action-loss-weight", type=float, default=1.0)
    parser.add_argument("--top-loss-weight", type=float, default=0.5)
    parser.add_argument("--bottom-loss-weight", type=float, default=0.5)
    parser.add_argument("--r-loss-weight", type=float, default=0.5)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--buy-threshold", type=float, default=0.55)
    parser.add_argument("--sell-threshold", type=float, default=0.55)
    parser.add_argument("--min-margin", type=float, default=0.05)
    parser.add_argument("--min-buy-r", type=float, default=0.0)
    parser.add_argument("--min-sell-r", type=float, default=0.0)
    parser.add_argument("--early-stopping-patience", type=int, default=12)
    parser.add_argument("--checkpoint-each-epoch", choices=("0", "1"), default="1")
    parser.add_argument(
        "--batch-log-every",
        type=int,
        default=10,
        help="0 disables per-batch log; 1 prints every batch",
    )
    parser.add_argument(
        "--batch-log-file", default="", help="Default: <output-dir>/latest_batch_log.jsonl"
    )
    parser.add_argument("--save-model", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Pivot image CNN training")
    return parser.parse_args(argv)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "pivot_pattern_image_tensor_latest.npy"


def default_meta_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root
        / "processed"
        / symbol
        / timeframe
        / "pivot_pattern_image_tensor_latest_meta.npz"
    )


def load_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Image tensor metadata not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def selected_indices(rows: int, max_samples: int) -> np.ndarray:
    indices = np.arange(rows, dtype=np.int64)
    if max_samples > 0 and len(indices) > max_samples:
        step = max(1, len(indices) // max_samples)
        indices = indices[::step][:max_samples]
    if len(indices) < 50:
        raise RuntimeError(f"Only {len(indices)} samples selected; need at least 50")
    return indices


def split_indices(
    rows: int, train_frac: float, val_frac: float, purge_gap: int
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
    train = np.arange(0, max(1, train_end), dtype=np.int64)
    validation = np.arange(
        min(rows, train_end + gap), max(min(rows, train_end + gap), val_end), dtype=np.int64
    )
    test = np.arange(min(rows, val_end + gap), rows, dtype=np.int64)
    if len(validation) < 1 or len(test) < 1:
        raise RuntimeError("Purge gap left no validation/test rows")
    return train, validation, test


def normalize_train_only(
    x_values: np.ndarray, train_idx: Sequence[int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    raw = x_values.astype(np.float32)
    nonfinite = int(raw.size - np.isfinite(raw).sum())
    clean = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    train = clean[np.asarray(train_idx, dtype=np.int64)]
    mean = np.mean(train, axis=(0, 1, 2), keepdims=True)
    std = np.std(train, axis=(0, 1, 2), keepdims=True)
    mean = np.nan_to_num(mean, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    std = np.nan_to_num(std, nan=1.0, posinf=1.0, neginf=1.0).astype(np.float32)
    std = np.where((~np.isfinite(std)) | (std < 1e-6), 1.0, std).astype(np.float32)
    normalized = (clean - mean) / std
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    return normalized.astype(np.float32), mean, std, nonfinite


class BatchProgressLogger:
    """Keras callback that prints and stores train-batch metrics during long epochs."""

    def __init__(self, tf: Any, output_path: Path, every: int) -> None:
        self.callback = tf.keras.callbacks.Callback
        self.output_path = output_path
        self.every = max(int(every), 0)
        self.epoch = 0
        self.global_batch = 0

    def as_callback(self) -> Any:
        outer = self

        class _BatchProgressCallback(outer.callback):
            def on_train_begin(self, logs: Mapping[str, Any] | None = None) -> None:
                if outer.every <= 0:
                    return
                outer.output_path.parent.mkdir(parents=True, exist_ok=True)
                outer.output_path.write_text("", encoding="utf-8")
                print(f"  batch-log   : {outer.output_path}", flush=True)

            def on_epoch_begin(self, epoch: int, logs: Mapping[str, Any] | None = None) -> None:
                outer.epoch = int(epoch) + 1
                if outer.every > 0:
                    print(f"[epoch {outer.epoch}] started", flush=True)

            def on_train_batch_end(self, batch: int, logs: Mapping[str, Any] | None = None) -> None:
                outer.global_batch += 1
                if outer.every <= 0:
                    return
                batch_number = int(batch) + 1
                if batch_number != 1 and batch_number % outer.every != 0:
                    return
                row: dict[str, Any] = {
                    "event": "train_batch_end",
                    "epoch": outer.epoch,
                    "batch": batch_number,
                    "global_batch": outer.global_batch,
                }
                for key, value in (logs or {}).items():
                    try:
                        number = float(value)
                    except (TypeError, ValueError):
                        continue
                    row[str(key)] = number if np.isfinite(number) else str(number)
                with outer.output_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                metric_parts = []
                metric_keys = (
                    "loss",
                    "action_loss",
                    "top_loss",
                    "bottom_loss",
                    "buy_r_loss",
                    "sell_r_loss",
                    "action_sparse_categorical_accuracy",
                )
                for key in metric_keys:
                    if key in row and isinstance(row[key], float):
                        metric_parts.append(f"{key}={row[key]:.5f}")
                print(
                    f"[epoch {outer.epoch} batch {batch_number} global {outer.global_batch}] "
                    + " ".join(metric_parts),
                    flush=True,
                )

            def on_epoch_end(self, epoch: int, logs: Mapping[str, Any] | None = None) -> None:
                if outer.every <= 0:
                    return
                row: dict[str, Any] = {"event": "epoch_end", "epoch": int(epoch) + 1}
                for key, value in (logs or {}).items():
                    try:
                        number = float(value)
                    except (TypeError, ValueError):
                        continue
                    row[str(key)] = number if np.isfinite(number) else str(number)
                with outer.output_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(
                    f"[epoch {int(epoch) + 1}] ended "
                    f"loss={row.get('loss', 'n/a')} val_loss={row.get('val_loss', 'n/a')}",
                    flush=True,
                )

        return _BatchProgressCallback()


def normalize_batch(
    x_batch: np.ndarray, mean: np.ndarray, std: np.ndarray, model_kind: str
) -> np.ndarray:
    clean = np.nan_to_num(x_batch.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    normalized = (clean - mean) / std
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    return maybe_expand_conv3d(normalized, model_kind)


def compute_streaming_scaler(
    x_values: np.ndarray, tensor_indices: Sequence[int], chunk_size: int
) -> tuple[np.ndarray, np.ndarray, int]:
    rows = np.asarray(tensor_indices, dtype=np.int64)
    if len(rows) == 0:
        raise RuntimeError("Cannot fit scaler on zero rows")
    sum_values: np.ndarray | None = None
    sum_squares: np.ndarray | None = None
    count = 0
    nonfinite = 0
    step = max(int(chunk_size), 1)
    for start in range(0, len(rows), step):
        batch_rows = rows[start : start + step]
        batch = np.asarray(x_values[batch_rows], dtype=np.float32)
        nonfinite += int(batch.size - np.isfinite(batch).sum())
        batch = np.nan_to_num(batch, nan=0.0, posinf=0.0, neginf=0.0)
        axes = (0, 1, 2)
        batch_sum = batch.sum(axis=axes, dtype=np.float64)
        batch_squares = np.square(batch, dtype=np.float64).sum(axis=axes, dtype=np.float64)
        sum_values = batch_sum if sum_values is None else sum_values + batch_sum
        sum_squares = batch_squares if sum_squares is None else sum_squares + batch_squares
        count += int(batch.shape[0] * batch.shape[1] * batch.shape[2])
    assert sum_values is not None and sum_squares is not None
    mean_vector = sum_values / max(count, 1)
    variance = np.maximum(sum_squares / max(count, 1) - np.square(mean_vector), 0.0)
    std_vector = np.sqrt(variance)
    std_vector = np.where((~np.isfinite(std_vector)) | (std_vector < 1e-6), 1.0, std_vector)
    mean = mean_vector.reshape(1, 1, 1, -1).astype(np.float32)
    std = std_vector.reshape(1, 1, 1, -1).astype(np.float32)
    mean = np.nan_to_num(mean, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    std = np.nan_to_num(std, nan=1.0, posinf=1.0, neginf=1.0).astype(np.float32)
    return mean, std, nonfinite


def make_tensor_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    targets: Mapping[str, np.ndarray],
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int,
    model_kind: str,
    weights: Mapping[str, np.ndarray] | None = None,
    shuffle: bool = False,
) -> Any:
    class PivotImageTensorSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.tensor_indices = np.asarray(tensor_indices, dtype=np.int64)
            self.targets = {key: np.asarray(value) for key, value in targets.items()}
            self.weights = (
                None
                if weights is None
                else {key: np.asarray(value) for key, value in weights.items()}
            )
            self.order = np.arange(len(self.tensor_indices), dtype=np.int64)
            self.shuffle = bool(shuffle)
            self.on_epoch_end()

        def __len__(self) -> int:
            return int(np.ceil(len(self.tensor_indices) / max(int(batch_size), 1)))

        def on_epoch_end(self) -> None:
            if self.shuffle:
                np.random.default_rng(20260917).shuffle(self.order)

        def __getitem__(self, index: int):
            start = index * max(int(batch_size), 1)
            end = min(len(self.order), start + max(int(batch_size), 1))
            local = self.order[start:end]
            rows = self.tensor_indices[local]
            x_batch = normalize_batch(np.asarray(x_values[rows]), mean, std, model_kind)
            y_batch = {key: value[local] for key, value in self.targets.items()}
            if self.weights is None:
                return x_batch, y_batch
            w_batch = {key: value[local] for key, value in self.weights.items()}
            return x_batch, y_batch, w_batch

    return PivotImageTensorSequence()


def make_predict_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int,
    model_kind: str,
) -> Any:
    class PivotImagePredictSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.tensor_indices = np.asarray(tensor_indices, dtype=np.int64)

        def __len__(self) -> int:
            return int(np.ceil(len(self.tensor_indices) / max(int(batch_size), 1)))

        def __getitem__(self, index: int) -> np.ndarray:
            start = index * max(int(batch_size), 1)
            end = min(len(self.tensor_indices), start + max(int(batch_size), 1))
            rows = self.tensor_indices[start:end]
            return normalize_batch(np.asarray(x_values[rows]), mean, std, model_kind)

    return PivotImagePredictSequence()


def maybe_expand_conv3d(x_values: np.ndarray, model_kind: str) -> np.ndarray:
    if model_kind == "conv3d":
        return x_values[..., None]
    return x_values


def target_dict(meta: Mapping[str, Any], indices: Sequence[int]) -> dict[str, np.ndarray]:
    idx = np.asarray(indices, dtype=np.int64)
    return {
        "action": np.asarray(meta["target_action"], dtype=np.int64)[idx],
        "top": np.asarray(meta["target_top_zone"], dtype=np.float32)[idx].reshape(-1, 1),
        "bottom": np.asarray(meta["target_bottom_zone"], dtype=np.float32)[idx].reshape(-1, 1),
        "buy_r": np.asarray(meta["target_buy_r"], dtype=np.float32)[idx].reshape(-1, 1),
        "sell_r": np.asarray(meta["target_sell_r"], dtype=np.float32)[idx].reshape(-1, 1),
    }


def class_weights(labels: Sequence[int], mode: str) -> np.ndarray | None:
    if mode != "auto":
        return None
    y = np.asarray(labels, dtype=np.int64)
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        return None
    weights = {
        int(cls): len(y) / (len(classes) * count)
        for cls, count in zip(classes, counts, strict=True)
    }
    return np.asarray([weights.get(int(value), 1.0) for value in y], dtype=np.float32)


def binary_weights(labels: np.ndarray, mode: str) -> np.ndarray | None:
    if mode != "auto":
        return None
    y = labels.reshape(-1)
    positives = int(np.sum(y >= 0.5))
    negatives = len(y) - positives
    if positives <= 0 or negatives <= 0:
        return None
    pos_weight = len(y) / (2.0 * positives)
    neg_weight = len(y) / (2.0 * negatives)
    return np.asarray([pos_weight if value >= 0.5 else neg_weight for value in y], dtype=np.float32)


def sample_weights(targets: Mapping[str, np.ndarray], mode: str) -> dict[str, np.ndarray] | None:
    action = class_weights(targets["action"], mode)
    top = binary_weights(targets["top"], mode)
    bottom = binary_weights(targets["bottom"], mode)
    if action is None and top is None and bottom is None:
        return None
    ones = np.ones(len(targets["action"]), dtype=np.float32)
    return {
        "action": action if action is not None else ones,
        "top": top if top is not None else ones,
        "bottom": bottom if bottom is not None else ones,
        "buy_r": ones,
        "sell_r": ones,
    }


def build_conv_model(tf: Any, input_shape: tuple[int, ...], args: argparse.Namespace) -> Any:
    layer_class = tf.keras.layers.Conv3D if args.model_kind == "conv3d" else tf.keras.layers.Conv2D
    pool_avg = (
        tf.keras.layers.GlobalAveragePooling3D
        if args.model_kind == "conv3d"
        else tf.keras.layers.GlobalAveragePooling2D
    )
    pool_max = (
        tf.keras.layers.GlobalMaxPooling3D
        if args.model_kind == "conv3d"
        else tf.keras.layers.GlobalMaxPooling2D
    )
    inputs = tf.keras.Input(shape=input_shape, name="pivot_image_tensor")
    x = inputs
    for block, filters in enumerate((args.filters, args.filters * 2, args.filters * 2), start=1):
        x = layer_class(
            max(int(filters), 1),
            max(int(args.kernel_size), 2),
            padding="same",
            activation="relu",
            name=f"conv_{block}_a",
        )(x)
        x = tf.keras.layers.BatchNormalization(name=f"bn_{block}_a")(x)
        x = layer_class(
            max(int(filters), 1),
            max(int(args.kernel_size), 2),
            padding="same",
            activation="relu",
            name=f"conv_{block}_b",
        )(x)
        x = tf.keras.layers.BatchNormalization(name=f"bn_{block}_b")(x)
        x = tf.keras.layers.Dropout(max(float(args.dropout), 0.0), name=f"dropout_{block}")(x)
    x = tf.keras.layers.Concatenate(name="pool_concat")(
        [pool_avg(name="avg_pool")(x), pool_max(name="max_pool")(x)]
    )
    x = tf.keras.layers.Dense(max(int(args.dense_units), 8), activation="relu", name="dense")(x)
    x = tf.keras.layers.Dropout(max(float(args.dropout), 0.0), name="dense_dropout")(x)
    outputs = {
        "action": tf.keras.layers.Dense(3, activation="softmax", name="action")(x),
        "top": tf.keras.layers.Dense(1, activation="sigmoid", name="top")(x),
        "bottom": tf.keras.layers.Dense(1, activation="sigmoid", name="bottom")(x),
        "buy_r": tf.keras.layers.Dense(1, activation="linear", name="buy_r")(x),
        "sell_r": tf.keras.layers.Dense(1, activation="linear", name="sell_r")(x),
    }
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name=f"pivot_pattern_{args.model_kind}")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=float(args.learning_rate)),
        loss={
            "action": tf.keras.losses.SparseCategoricalCrossentropy(),
            "top": tf.keras.losses.BinaryCrossentropy(),
            "bottom": tf.keras.losses.BinaryCrossentropy(),
            "buy_r": tf.keras.losses.Huber(),
            "sell_r": tf.keras.losses.Huber(),
        },
        loss_weights={
            "action": float(args.action_loss_weight),
            "top": float(args.top_loss_weight),
            "bottom": float(args.bottom_loss_weight),
            "buy_r": float(args.r_loss_weight),
            "sell_r": float(args.r_loss_weight),
        },
        metrics={"action": [tf.keras.metrics.SparseCategoricalAccuracy()]},
    )
    return model


def metric_block(
    targets: Mapping[str, np.ndarray],
    predictions: Mapping[str, np.ndarray],
    args: argparse.Namespace,
    prefix: str,
) -> dict[str, float]:
    action_prob = np.asarray(predictions["action"], dtype=np.float32)
    y_action = np.asarray(targets["action"], dtype=np.int64)
    selected = selected_action(
        action_prob, args.buy_threshold, args.sell_threshold, args.min_margin
    )
    top_scores = np.asarray(predictions["top"], dtype=np.float32).reshape(-1)
    bottom_scores = np.asarray(predictions["bottom"], dtype=np.float32).reshape(-1)
    buy_r = np.asarray(predictions["buy_r"], dtype=np.float32).reshape(-1)
    sell_r = np.asarray(predictions["sell_r"], dtype=np.float32).reshape(-1)
    selected_mask = ((selected == 2) & (buy_r >= args.min_buy_r)) | (
        (selected == 0) & (sell_r >= args.min_sell_r)
    )
    return {
        f"{prefix}_action_accuracy": (
            float(np.mean(action_prob.argmax(axis=1) == y_action)) if len(y_action) else 0.0
        ),
        f"{prefix}_top_ap": average_precision(
            np.asarray(targets["top"], dtype=np.float32).reshape(-1), top_scores
        ),
        f"{prefix}_bottom_ap": average_precision(
            np.asarray(targets["bottom"], dtype=np.float32).reshape(-1), bottom_scores
        ),
        f"{prefix}_buy_r_mae": (
            float(np.mean(np.abs(np.asarray(targets["buy_r"]).reshape(-1) - buy_r)))
            if len(y_action)
            else 0.0
        ),
        f"{prefix}_sell_r_mae": (
            float(np.mean(np.abs(np.asarray(targets["sell_r"]).reshape(-1) - sell_r)))
            if len(y_action)
            else 0.0
        ),
        f"{prefix}_selected_rate": float(np.mean(selected_mask)) if len(y_action) else 0.0,
    }


def next_version(model_dir: Path) -> int:
    versions: list[int] = []
    if model_dir.exists():
        for path in model_dir.glob("v*_training.json"):
            raw = path.stem.removeprefix("v").removesuffix("_training")
            if raw.isdigit():
                versions.append(int(raw))
    return max(versions, default=0) + 1


def save_architecture_artifacts(model: Any, model_dir: Path, version: int) -> tuple[str, str]:
    summary_lines: list[str] = []
    model.summary(print_fn=summary_lines.append)
    summary_path = model_dir / f"v{version}_summary.txt"
    architecture_path = model_dir / f"v{version}_architecture.json"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    try:
        architecture = json.loads(model.to_json())
    except Exception as error:
        architecture = {"error": f"model.to_json() failed: {type(error).__name__}: {error}"}
    architecture_path.write_text(
        json.dumps(architecture, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return str(architecture_path), str(summary_path)


def prepare_training_artifact_paths(
    model: Any, args: argparse.Namespace
) -> tuple[Path, int, str, str, str]:
    """Create model directory and pre-training artifacts before the first epoch.

    Final model save happens after training, but long training runs need visible
    artifacts and epoch checkpoints immediately so operator work is not lost if
    a run is interrupted.
    """
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    version = next_version(model_dir)
    architecture_path, summary_path = save_architecture_artifacts(model, model_dir, version)
    checkpoint_path = model_dir / f"v{version}_epoch_checkpoint.keras"
    return model_dir, version, str(checkpoint_path), architecture_path, summary_path


def save_model(
    model: Any,
    report_stub: dict[str, Any],
    payload: dict[str, Any],
    args: argparse.Namespace,
    prepared_version: int | None = None,
    prepared_architecture_path: str = "",
    prepared_summary_path: str = "",
) -> tuple[str, str, str, str, int]:
    if args.save_model != "1":
        return "", "", "", "", 0
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    version = (
        prepared_version
        if prepared_version is not None and prepared_version > 0
        else next_version(model_dir)
    )
    model_path = model_dir / f"v{version}_model.keras"
    record_path = model_dir / f"v{version}_training.json"
    model.save(model_path)
    if prepared_architecture_path and prepared_summary_path:
        architecture_path, summary_path = save_architecture_artifacts(model, model_dir, version)
    else:
        architecture_path, summary_path = save_architecture_artifacts(model, model_dir, version)
    record = {
        **report_stub,
        "version": version,
        "model_path": str(model_path),
        "record_path": str(record_path),
        "architecture_json_path": architecture_path,
        "model_summary_path": summary_path,
        "payload": payload,
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(model_path), str(record_path), architecture_path, summary_path, version


def render_html(title: str, report: ImageCnnReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase143A Conv2D/Conv3D on 4D pivot image tensor.</p></section>
<section class="card"><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_log_path = (
        Path(args.batch_log_file) if args.batch_log_file else output_dir / "latest_batch_log.jsonl"
    )
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    meta_path = (
        Path(args.meta_path)
        if args.meta_path
        else default_meta_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE143A TRAIN PIVOT IMAGE CNN")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        tf = require_tensorflow()
        x_all = np.load(tensor_path, mmap_mode="r")
        meta = load_meta(meta_path)
        indices = selected_indices(len(x_all), int(args.max_samples))
        meta_scoped = {
            key: np.asarray(value)[indices]
            for key, value in meta.items()
            if key.startswith("target_")
        }
        train_idx, validation_idx, test_idx = split_indices(
            len(indices), args.train_frac, args.val_frac, args.purge_gap
        )
        train_targets = target_dict(meta_scoped, train_idx)
        validation_targets = target_dict(meta_scoped, validation_idx)
        test_targets = target_dict(meta_scoped, test_idx)
        selected_shape = [int(len(indices)), *[int(value) for value in x_all.shape[1:]]]

        if args.loader_mode == "stream":
            mean, std, nonfinite_input_values = compute_streaming_scaler(
                x_all, indices[train_idx], int(args.stream_chunk_size)
            )
            base_input_shape = tuple(int(value) for value in x_all.shape[1:])
            model_input_shape = (
                (*base_input_shape, 1) if args.model_kind == "conv3d" else base_input_shape
            )
            model = build_conv_model(tf, model_input_shape, args)
        else:
            x_loaded = np.asarray(x_all[indices], dtype=np.float32)
            x_norm, mean, std, nonfinite_input_values = normalize_train_only(x_loaded, train_idx)
            x_model = maybe_expand_conv3d(x_norm, args.model_kind)
            model_input_shape = tuple(int(value) for value in x_model.shape[1:])
            model = build_conv_model(tf, model_input_shape, args)

        (
            _model_dir,
            prepared_version,
            epoch_checkpoint_path,
            pretrain_architecture_path,
            pretrain_summary_path,
        ) = (
            prepare_training_artifact_paths(model, args)
            if args.save_model == "1"
            else (Path(args.storage_root) / "models" / args.model_id, 0, "", "", "")
        )
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=max(int(args.early_stopping_patience), 1),
                restore_best_weights=True,
            )
        ]
        if args.save_model == "1" and args.checkpoint_each_epoch == "1":
            callbacks.append(
                tf.keras.callbacks.ModelCheckpoint(
                    filepath=epoch_checkpoint_path,
                    monitor="val_loss",
                    save_best_only=False,
                    save_weights_only=False,
                    verbose=1,
                )
            )
        callbacks.append(
            tf.keras.callbacks.CSVLogger(str(Path(args.output_dir) / "latest_training_log.csv"))
        )
        callbacks.append(
            BatchProgressLogger(tf, batch_log_path, int(args.batch_log_every)).as_callback()
        )
        if epoch_checkpoint_path:
            print(f"  checkpoint  : {epoch_checkpoint_path}")
            print(f"  pre-summary : {pretrain_summary_path}")
            print(f"  pre-arch    : {pretrain_architecture_path}")
        print(f"  loader-mode : {args.loader_mode}")

        if args.loader_mode == "stream":
            train_sequence = make_tensor_sequence(
                tf,
                x_all,
                indices[train_idx],
                train_targets,
                mean,
                std,
                int(args.batch_size),
                args.model_kind,
                sample_weights(train_targets, args.class_weight),
                shuffle=True,
            )
            validation_sequence = make_tensor_sequence(
                tf,
                x_all,
                indices[validation_idx],
                validation_targets,
                mean,
                std,
                int(args.batch_size),
                args.model_kind,
                None,
                shuffle=False,
            )
            model.fit(
                train_sequence,
                validation_data=validation_sequence,
                epochs=max(int(args.epochs), 1),
                callbacks=callbacks,
                verbose=2,
            )
            validation_pred = prediction_dict(
                model.predict(
                    make_predict_sequence(
                        tf,
                        x_all,
                        indices[validation_idx],
                        mean,
                        std,
                        int(args.batch_size),
                        args.model_kind,
                    ),
                    verbose=0,
                )
            )
            test_pred = prediction_dict(
                model.predict(
                    make_predict_sequence(
                        tf,
                        x_all,
                        indices[test_idx],
                        mean,
                        std,
                        int(args.batch_size),
                        args.model_kind,
                    ),
                    verbose=0,
                )
            )
        else:
            model.fit(
                x_model[train_idx],
                train_targets,
                validation_data=(x_model[validation_idx], validation_targets),
                sample_weight=sample_weights(train_targets, args.class_weight),
                batch_size=max(int(args.batch_size), 1),
                epochs=max(int(args.epochs), 1),
                callbacks=callbacks,
                verbose=2,
            )
            validation_pred = prediction_dict(
                model.predict(x_model[validation_idx], batch_size=args.batch_size, verbose=0)
            )
            test_pred = prediction_dict(
                model.predict(x_model[test_idx], batch_size=args.batch_size, verbose=0)
            )

        metrics: dict[str, float] = {}
        metrics.update(metric_block(validation_targets, validation_pred, args, "val"))
        metrics.update(metric_block(test_targets, test_pred, args, "test"))
        report_stub = {
            "model_id": args.model_id,
            "phase": "Phase143A",
            "role": "pivot_image_cnn",
            "model_kind": args.model_kind,
            "tensor_path": str(tensor_path),
            "meta_path": str(meta_path),
            "stored_x_shape": selected_shape,
            "keras_batch_shape": f"[batch, {', '.join(str(int(v)) for v in model_input_shape)}]",
            "metrics": metrics,
            "batch_log_path": str(batch_log_path),
            "production_status": "research_only_not_approved",
        }
        payload = {
            "scaler_mean": mean.tolist(),
            "scaler_std": std.tolist(),
            "model_kind": args.model_kind,
            "feature_5m_names": [str(value) for value in meta.get("feature_5m_names", [])],
            "feature_htf_names": [str(value) for value in meta.get("feature_htf_names", [])],
            "thresholds": {
                "buy_threshold": args.buy_threshold,
                "sell_threshold": args.sell_threshold,
                "min_margin": args.min_margin,
                "min_buy_r": args.min_buy_r,
                "min_sell_r": args.min_sell_r,
            },
        }
        model_path, record_path, architecture_path, summary_path, version = save_model(
            model,
            report_stub,
            payload,
            args,
            prepared_version=prepared_version,
            prepared_architecture_path=pretrain_architecture_path,
            prepared_summary_path=pretrain_summary_path,
        )
        report = ImageCnnReport(
            model_id=args.model_id,
            version=version,
            model_kind=args.model_kind,
            tensor_path=str(tensor_path),
            meta_path=str(meta_path),
            samples=len(indices),
            train_rows=len(train_idx),
            validation_rows=len(validation_idx),
            test_rows=len(test_idx),
            stored_x_shape=selected_shape,
            keras_batch_shape=f"[batch, {', '.join(str(int(v)) for v in model_input_shape)}]",
            metrics=metrics,
            model_path=model_path,
            record_path=record_path,
            architecture_json_path=architecture_path,
            model_summary_path=summary_path,
            epoch_checkpoint_path=epoch_checkpoint_path,
            batch_log_path=str(batch_log_path),
            nonfinite_input_values=int(nonfinite_input_values),
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            production_status="BLOCKED — research image CNN only",
        )
        if record_path:
            record_file = Path(record_path)
            record = json.loads(record_file.read_text(encoding="utf-8"))
            record["latest_report"] = asdict(report)
            record_file.write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        Path(report.output_json).write_text(
            json.dumps(
                {"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        Path(report.output_html).write_text(
            render_html(args.report_title, report), encoding="utf-8"
        )
        print(f"  X shape     : {report.stored_x_shape}")
        print(f"  keras batch : {report.keras_batch_shape}")
        print(f"  val acc     : {metrics.get('val_action_accuracy', 0.0):.4f}")
        print(f"  test acc    : {metrics.get('test_action_accuracy', 0.0):.4f}")
        print(f"  test select : {metrics.get('test_selected_rate', 0.0):.2%}")
        print(f"  nonfinite input values sanitized: {report.nonfinite_input_values:,}")
        print(f"  model       : {model_path}")
        print(f"  summary     : {summary_path}")
        print(f"  architecture: {architecture_path}")
        print(f"  checkpoint  : {epoch_checkpoint_path}")
        print(f"  batch log   : {batch_log_path}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
