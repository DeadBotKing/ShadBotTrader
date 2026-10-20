"""Phase142A: train a TensorFlow/Keras WaveNet on pivot-pattern tensors.

Input tensor stored on disk: ``[samples, window, channels]``.
Keras training batches: ``[batch, window, channels]``.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import html
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_wavenet")
ACTION_NAMES = {0: "SELL", 1: "HOLD", 2: "BUY"}
MONITOR_CHOICES = (
    "auto",
    "val_loss",
    "val_action_sparse_categorical_accuracy",
    "val_top_auc",
    "val_bottom_auc",
)


@dataclass(frozen=True)
class PivotWaveNetReport:
    model_id: str
    version: int
    tensor_path: str
    task: str
    rows: int
    tensor_window: int
    channels: int
    train_rows: int
    validation_rows: int
    test_rows: int
    stored_x_shape: list[int]
    keras_batch_shape: str
    metrics: dict[str, float]
    model_path: str
    record_path: str
    output_json: str
    output_html: str
    production_status: str


class MissingTensorFlow(RuntimeError):
    """Raised when TensorFlow is not installed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Phase142A Keras WaveNet on a pivot-pattern 3D tensor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_wavenet_5m")
    parser.add_argument("--task", choices=("multihead",), default="multihead")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all chronological samples")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--filters", type=int, default=48)
    parser.add_argument("--kernel-size", type=int, default=3)
    parser.add_argument("--n-layers", type=int, default=6)
    parser.add_argument("--n-blocks", type=int, default=2)
    parser.add_argument("--dense-units", type=int, default=96)
    parser.add_argument("--dropout", type=float, default=0.20)
    parser.add_argument("--action-loss-weight", type=float, default=1.00)
    parser.add_argument("--top-loss-weight", type=float, default=0.50)
    parser.add_argument("--bottom-loss-weight", type=float, default=0.50)
    parser.add_argument("--r-loss-weight", type=float, default=0.50)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--buy-threshold", type=float, default=0.55)
    parser.add_argument("--sell-threshold", type=float, default=0.55)
    parser.add_argument("--min-margin", type=float, default=0.05)
    parser.add_argument("--min-buy-r", type=float, default=0.0)
    parser.add_argument("--min-sell-r", type=float, default=0.0)
    parser.add_argument("--monitor-metric", choices=MONITOR_CHOICES, default="auto")
    parser.add_argument("--early-stopping-patience", type=int, default=12)
    parser.add_argument("--save-model", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Pivot WaveNet training")
    return parser.parse_args(argv)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "pivot_pattern_tensor_latest.npz"


def require_tensorflow():
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MissingTensorFlow(
            "TensorFlow/Keras is required for Phase142A WaveNet. Install: pip install -r requirements-ai.txt"
        ) from exc
    return tf


def load_tensor(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Pivot tensor not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def selected_indices(rows: int, max_samples: int) -> np.ndarray:
    indices = np.arange(rows, dtype=np.int64)
    if max_samples > 0 and len(indices) > max_samples:
        step = max(1, len(indices) // max_samples)
        indices = indices[::step][:max_samples]
    if len(indices) < 50:
        raise RuntimeError(f"Only {len(indices)} tensor samples selected; need at least 50")
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
    validation_start = min(rows, train_end + gap)
    validation = np.arange(validation_start, max(validation_start, val_end), dtype=np.int64)
    test_start = min(rows, val_end + gap)
    test = np.arange(test_start, rows, dtype=np.int64)
    if len(validation) < 1 or len(test) < 1:
        raise RuntimeError(
            "Purge gap left no validation/test rows; lower --purge-gap or build more samples"
        )
    return train, validation, test


def normalize_train_only(
    x_values: np.ndarray, train_idx: Sequence[int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train = x_values[np.asarray(train_idx, dtype=np.int64)].astype(np.float32)
    mean = np.mean(train, axis=(0, 1), keepdims=True)
    std = np.std(train, axis=(0, 1), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    normalized = (x_values.astype(np.float32) - mean) / std
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    return normalized, mean.astype(np.float32), std.astype(np.float32)


def class_sample_weights(labels: Sequence[int], mode: str) -> np.ndarray | None:
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


def binary_sample_weights(labels: Sequence[float], mode: str) -> np.ndarray | None:
    if mode != "auto":
        return None
    y = np.asarray(labels, dtype=np.float32)
    positives = int(np.sum(y >= 0.5))
    negatives = len(y) - positives
    if positives <= 0 or negatives <= 0:
        return None
    pos_weight = len(y) / (2.0 * positives)
    neg_weight = len(y) / (2.0 * negatives)
    return np.asarray([pos_weight if value >= 0.5 else neg_weight for value in y], dtype=np.float32)


def target_dict(data: Mapping[str, Any], indices: Sequence[int]) -> dict[str, np.ndarray]:
    idx = np.asarray(indices, dtype=np.int64)
    return {
        "action": np.asarray(data["target_action"], dtype=np.int64)[idx],
        "top": np.asarray(data["target_top_zone"], dtype=np.float32)[idx].reshape(-1, 1),
        "bottom": np.asarray(data["target_bottom_zone"], dtype=np.float32)[idx].reshape(-1, 1),
        "buy_r": np.asarray(data["target_buy_r"], dtype=np.float32)[idx].reshape(-1, 1),
        "sell_r": np.asarray(data["target_sell_r"], dtype=np.float32)[idx].reshape(-1, 1),
    }


def sample_weight_dict(
    targets: Mapping[str, np.ndarray], mode: str
) -> dict[str, np.ndarray] | None:
    action_weights = class_sample_weights(targets["action"], mode)
    top_weights = binary_sample_weights(targets["top"], mode)
    bottom_weights = binary_sample_weights(targets["bottom"], mode)
    if action_weights is None and top_weights is None and bottom_weights is None:
        return None
    ones = np.ones(len(targets["action"]), dtype=np.float32)
    return {
        "action": action_weights if action_weights is not None else ones,
        "top": top_weights if top_weights is not None else ones,
        "bottom": bottom_weights if bottom_weights is not None else ones,
        "buy_r": ones,
        "sell_r": ones,
    }


def build_wavenet_model(tf: Any, input_shape: tuple[int, int], args: argparse.Namespace) -> Any:
    inputs = tf.keras.Input(shape=input_shape, name="pivot_tensor")
    x = tf.keras.layers.Conv1D(args.filters, 1, padding="same", name="input_projection")(inputs)
    for block in range(max(int(args.n_blocks), 1)):
        for layer in range(max(int(args.n_layers), 1)):
            dilation = 2**layer
            residual = x
            x = tf.keras.layers.Conv1D(
                args.filters,
                max(int(args.kernel_size), 2),
                padding="causal",
                dilation_rate=dilation,
                activation="relu",
                name=f"b{block + 1}_d{dilation}_conv",
            )(x)
            x = tf.keras.layers.Dropout(
                max(float(args.dropout), 0.0), name=f"b{block + 1}_d{dilation}_dropout"
            )(x)
            x = tf.keras.layers.Conv1D(
                args.filters, 1, padding="same", name=f"b{block + 1}_d{dilation}_mix"
            )(x)
            x = tf.keras.layers.Add(name=f"b{block + 1}_d{dilation}_residual")([residual, x])
            x = tf.keras.layers.LayerNormalization(name=f"b{block + 1}_d{dilation}_norm")(x)
    avg_pool = tf.keras.layers.GlobalAveragePooling1D(name="avg_pool")(x)
    max_pool = tf.keras.layers.GlobalMaxPooling1D(name="max_pool")(x)
    x = tf.keras.layers.Concatenate(name="pool_concat")([avg_pool, max_pool])
    x = tf.keras.layers.Dense(max(int(args.dense_units), 8), activation="relu", name="dense")(x)
    x = tf.keras.layers.Dropout(max(float(args.dropout), 0.0), name="dense_dropout")(x)
    outputs = {
        "action": tf.keras.layers.Dense(3, activation="softmax", name="action")(x),
        "top": tf.keras.layers.Dense(1, activation="sigmoid", name="top")(x),
        "bottom": tf.keras.layers.Dense(1, activation="sigmoid", name="bottom")(x),
        "buy_r": tf.keras.layers.Dense(1, activation="linear", name="buy_r")(x),
        "sell_r": tf.keras.layers.Dense(1, activation="linear", name="sell_r")(x),
    }
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="pivot_pattern_wavenet")
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
        metrics={
            "action": [tf.keras.metrics.SparseCategoricalAccuracy()],
            "top": [tf.keras.metrics.AUC(name="auc")],
            "bottom": [tf.keras.metrics.AUC(name="auc")],
            "buy_r": [tf.keras.metrics.MeanAbsoluteError(name="mae")],
            "sell_r": [tf.keras.metrics.MeanAbsoluteError(name="mae")],
        },
    )
    return model


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    positives = int(np.sum(y_true >= 0.5))
    if positives <= 0:
        return 0.0
    order = np.argsort(-scores)
    sorted_true = y_true[order]
    hits = 0
    precision_sum = 0.0
    for rank, value in enumerate(sorted_true, start=1):
        if float(value) >= 0.5:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / positives


def prediction_dict(raw: Any) -> dict[str, np.ndarray]:
    if isinstance(raw, Mapping):
        return {key: np.asarray(value) for key, value in raw.items()}
    names = ["action", "top", "bottom", "buy_r", "sell_r"]
    return {name: np.asarray(value) for name, value in zip(names, raw, strict=True)}


def selected_action(
    probabilities: np.ndarray, buy_threshold: float, sell_threshold: float, min_margin: float
) -> np.ndarray:
    sell_p = probabilities[:, 0]
    hold_p = probabilities[:, 1]
    buy_p = probabilities[:, 2]
    buy_ok = (buy_p >= buy_threshold) & (buy_p - np.maximum(sell_p, hold_p) >= min_margin)
    sell_ok = (sell_p >= sell_threshold) & (sell_p - np.maximum(buy_p, hold_p) >= min_margin)
    result = np.full(len(probabilities), -1, dtype=np.int64)
    result[buy_ok & ~sell_ok] = 2
    result[sell_ok & ~buy_ok] = 0
    return result


def metric_block(
    targets: Mapping[str, np.ndarray],
    predictions: Mapping[str, np.ndarray],
    args: argparse.Namespace,
    prefix: str,
) -> dict[str, float]:
    action_prob = np.asarray(predictions["action"], dtype=np.float32)
    y_action = np.asarray(targets["action"], dtype=np.int64)
    top_scores = np.asarray(predictions["top"], dtype=np.float32).reshape(-1)
    bottom_scores = np.asarray(predictions["bottom"], dtype=np.float32).reshape(-1)
    buy_r_pred = np.asarray(predictions["buy_r"], dtype=np.float32).reshape(-1)
    sell_r_pred = np.asarray(predictions["sell_r"], dtype=np.float32).reshape(-1)
    selected = selected_action(
        action_prob, args.buy_threshold, args.sell_threshold, args.min_margin
    )
    buy_selected = (selected == 2) & (buy_r_pred >= float(args.min_buy_r))
    sell_selected = (selected == 0) & (sell_r_pred >= float(args.min_sell_r))
    selected_mask = buy_selected | sell_selected
    return {
        f"{prefix}_action_accuracy": (
            float(np.mean(action_prob.argmax(axis=1) == y_action)) if len(y_action) else 0.0
        ),
        f"{prefix}_action_pred_sell_rate": (
            float(np.mean(action_prob.argmax(axis=1) == 0)) if len(y_action) else 0.0
        ),
        f"{prefix}_action_pred_hold_rate": (
            float(np.mean(action_prob.argmax(axis=1) == 1)) if len(y_action) else 0.0
        ),
        f"{prefix}_action_pred_buy_rate": (
            float(np.mean(action_prob.argmax(axis=1) == 2)) if len(y_action) else 0.0
        ),
        f"{prefix}_top_ap": average_precision(
            np.asarray(targets["top"], dtype=np.float32), top_scores
        ),
        f"{prefix}_bottom_ap": average_precision(
            np.asarray(targets["bottom"], dtype=np.float32), bottom_scores
        ),
        f"{prefix}_buy_r_mae": (
            float(np.mean(np.abs(np.asarray(targets["buy_r"], dtype=np.float32) - buy_r_pred)))
            if len(y_action)
            else 0.0
        ),
        f"{prefix}_sell_r_mae": (
            float(np.mean(np.abs(np.asarray(targets["sell_r"], dtype=np.float32) - sell_r_pred)))
            if len(y_action)
            else 0.0
        ),
        f"{prefix}_selected_rate": float(np.mean(selected_mask)) if len(y_action) else 0.0,
        f"{prefix}_buy_selected_rate": float(np.mean(buy_selected)) if len(y_action) else 0.0,
        f"{prefix}_sell_selected_rate": float(np.mean(sell_selected)) if len(y_action) else 0.0,
    }


def next_version(model_dir: Path) -> int:
    versions: list[int] = []
    if model_dir.exists():
        for path in model_dir.glob("v*_training.json"):
            raw = path.stem.removeprefix("v").removesuffix("_training")
            if raw.isdigit():
                versions.append(int(raw))
    return max(versions, default=0) + 1


def monitor_metric(args: argparse.Namespace) -> str:
    if args.monitor_metric == "auto":
        return "val_loss"
    return args.monitor_metric


def render_html(title: str, report: PivotWaveNetReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:21px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase142A Keras WaveNet/TCN. Stored tensor is <code>[samples, window, channels]</code>; Keras batches are <code>[batch, window, channels]</code>.</p>
<div class="grid">
<div class="metric"><span>Rows</span><strong>{report.rows:,}</strong></div>
<div class="metric"><span>Input</span><strong>{report.keras_batch_shape}</strong></div>
<div class="metric"><span>Test accuracy</span><strong>{report.metrics.get('test_action_accuracy', 0.0):.3f}</strong></div>
<div class="metric"><span>Selected rate</span><strong>{report.metrics.get('test_selected_rate', 0.0):.2%}</strong></div>
</div><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def save_model_and_record(
    model: Any,
    report_stub: dict[str, Any],
    payload: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, str, int]:
    if args.save_model != "1":
        return "", "", 0
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    version = next_version(model_dir)
    model_path = model_dir / f"v{version}_model.keras"
    record_path = model_dir / f"v{version}_training.json"
    model.save(model_path)
    record = {
        **report_stub,
        "version": version,
        "model_path": str(model_path),
        "record_path": str(record_path),
        "payload": payload,
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(model_path), str(record_path), version


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE142A TRAIN PIVOT WAVENET / TCN")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        tf = require_tensorflow()
        data = load_tensor(tensor_path)
        x_raw = np.asarray(data["X"])
        all_indices = selected_indices(len(x_raw), int(args.max_samples))
        x_raw = x_raw[all_indices]
        scoped = {
            key: np.asarray(value)[all_indices]
            for key, value in data.items()
            if key.startswith("target_")
        }
        rows = len(x_raw)
        train_idx, validation_idx, test_idx = split_indices(
            rows, args.train_frac, args.val_frac, args.purge_gap
        )
        x_values, mean, std = normalize_train_only(x_raw, train_idx)
        targets_all = {
            "target_action": scoped["target_action"],
            "target_top_zone": scoped["target_top_zone"],
            "target_bottom_zone": scoped["target_bottom_zone"],
            "target_buy_r": scoped["target_buy_r"],
            "target_sell_r": scoped["target_sell_r"],
        }
        train_targets = target_dict(targets_all, train_idx)
        validation_targets = target_dict(targets_all, validation_idx)
        test_targets = target_dict(targets_all, test_idx)
        model = build_wavenet_model(tf, (int(x_values.shape[1]), int(x_values.shape[2])), args)
        callbacks: list[Any] = [
            tf.keras.callbacks.EarlyStopping(
                monitor=monitor_metric(args),
                patience=max(int(args.early_stopping_patience), 1),
                restore_best_weights=True,
            )
        ]
        sample_weights = sample_weight_dict(train_targets, args.class_weight)
        model.fit(
            x_values[train_idx],
            train_targets,
            validation_data=(x_values[validation_idx], validation_targets),
            sample_weight=sample_weights,
            batch_size=max(int(args.batch_size), 1),
            epochs=max(int(args.epochs), 1),
            callbacks=callbacks,
            verbose=2,
        )
        validation_predictions = prediction_dict(
            model.predict(x_values[validation_idx], batch_size=args.batch_size, verbose=0)
        )
        test_predictions = prediction_dict(
            model.predict(x_values[test_idx], batch_size=args.batch_size, verbose=0)
        )
        metrics: dict[str, float] = {}
        metrics.update(metric_block(validation_targets, validation_predictions, args, "val"))
        metrics.update(metric_block(test_targets, test_predictions, args, "test"))
        report_stub = {
            "model_id": args.model_id,
            "phase": "Phase142A",
            "role": "pivot_pattern_wavenet",
            "tensor_path": str(tensor_path),
            "stored_x_shape": [int(value) for value in x_raw.shape],
            "keras_batch_shape": f"[batch, {int(x_values.shape[1])}, {int(x_values.shape[2])}]",
            "train_rows": int(len(train_idx)),
            "validation_rows": int(len(validation_idx)),
            "test_rows": int(len(test_idx)),
            "metrics": metrics,
            "production_status": "research_only_not_approved",
        }
        payload = {
            "scaler_mean": mean.tolist(),
            "scaler_std": std.tolist(),
            "feature_columns": [str(value) for value in data.get("feature_columns", [])],
            "thresholds": {
                "buy_threshold": args.buy_threshold,
                "sell_threshold": args.sell_threshold,
                "min_margin": args.min_margin,
                "min_buy_r": args.min_buy_r,
                "min_sell_r": args.min_sell_r,
            },
            "architecture": {
                "filters": args.filters,
                "kernel_size": args.kernel_size,
                "n_layers": args.n_layers,
                "n_blocks": args.n_blocks,
                "dense_units": args.dense_units,
                "dropout": args.dropout,
            },
        }
        model_path, record_path, version = save_model_and_record(model, report_stub, payload, args)
        report = PivotWaveNetReport(
            model_id=args.model_id,
            version=version,
            tensor_path=str(tensor_path),
            task=args.task,
            rows=rows,
            tensor_window=int(x_values.shape[1]),
            channels=int(x_values.shape[2]),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
            stored_x_shape=[int(value) for value in x_raw.shape],
            keras_batch_shape=f"[batch, {int(x_values.shape[1])}, {int(x_values.shape[2])}]",
            metrics=metrics,
            model_path=model_path,
            record_path=record_path,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            production_status="BLOCKED — research Keras WaveNet only",
        )
        if record_path:
            record_file = Path(record_path)
            record = json.loads(record_file.read_text(encoding="utf-8"))
            record["latest_report"] = asdict(report)
            record_file.write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        payload_json = {
            "args": vars(args),
            "report": asdict(report),
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "model": model_path,
                "record": record_path,
            },
        }
        Path(report.output_json).write_text(
            json.dumps(payload_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        Path(report.output_html).write_text(
            render_html(args.report_title, report), encoding="utf-8"
        )
        print(f"  rows        : {rows:,}")
        print(f"  X shape     : {report.stored_x_shape}")
        print(f"  keras batch : {report.keras_batch_shape}")
        print(f"  val acc     : {metrics.get('val_action_accuracy', 0.0):.4f}")
        print(f"  test acc    : {metrics.get('test_action_accuracy', 0.0):.4f}")
        print(f"  test select : {metrics.get('test_selected_rate', 0.0):.2%}")
        print(f"  model       : {model_path}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
