"""Phase145A: train advanced Conv1D/WaveNet on pivot sequence tensors.

Input tensor layout:

    stored X: [samples, window_size, features]
    Keras batch: [batch, window_size, features]

This is Option A: concatenate 5M + closed 4H + closed 1D + session/source
features on one feature axis, then use a WaveNet/TCN-style temporal model.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import html
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import numpy as np
from train_pivot_pattern_image_cnn import (
    BatchProgressLogger,
    metric_block,
    next_version,
    sample_weights,
    selected_indices,
    split_indices,
    target_dict,
)
from train_pivot_pattern_image_wavenet import (
    activation_layer,
    gated_dilated_residual_block,
    parse_int_list,
    save_architecture_artifacts,
    squeeze_excitation_1d,
)
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_wavenet")


@dataclass(frozen=True)
class SequenceWaveNetReport:
    model_id: str
    version: int
    tensor_path: str
    meta_path: str
    samples: int
    train_rows: int
    validation_rows: int
    test_rows: int
    stored_x_shape: list[int]
    keras_batch_shape: str
    metrics: dict[str, float]
    architecture_features: list[str]
    feature_count: int
    m5_feature_count: int
    htf_feature_count: int
    other_feature_count: int
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
        description="Train Phase145A advanced Conv1D/WaveNet on [samples, window, features].",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_sequence_wavenet_5m")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--loader-mode", choices=("stream", "memory"), default="stream")
    parser.add_argument("--stream-chunk-size", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--branch-filters", type=int, default=48)
    parser.add_argument("--temporal-filters", type=int, default=96)
    parser.add_argument("--temporal-kernels", default="3,5,9")
    parser.add_argument("--dilations", default="1,2,4,8,16,32")
    parser.add_argument("--residual-blocks", type=int, default=2)
    parser.add_argument("--attention-heads", type=int, default=4)
    parser.add_argument("--attention-key-dim", type=int, default=16)
    parser.add_argument("--se-ratio", type=int, default=8)
    parser.add_argument("--dense-units", type=int, default=128)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--activation", choices=("tanh", "swish", "gelu"), default="tanh")
    parser.add_argument("--action-loss-weight", type=float, default=1.0)
    parser.add_argument("--top-loss-weight", type=float, default=0.5)
    parser.add_argument("--bottom-loss-weight", type=float, default=0.5)
    parser.add_argument("--r-loss-weight", type=float, default=0.5)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--buy-threshold", type=float, default=0.34)
    parser.add_argument("--sell-threshold", type=float, default=0.34)
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--min-buy-r", type=float, default=-999.0)
    parser.add_argument("--min-sell-r", type=float, default=-999.0)
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--checkpoint-each-epoch", choices=("0", "1"), default="1")
    parser.add_argument("--batch-log-every", type=int, default=10)
    parser.add_argument("--batch-log-file", default="")
    parser.add_argument("--save-model", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Advanced Pivot Sequence WaveNet training")
    return parser.parse_args(argv)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root / "processed" / symbol / timeframe / "pivot_pattern_sequence_tensor_latest.npy"
    )


def default_meta_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root
        / "processed"
        / symbol
        / timeframe
        / "pivot_pattern_sequence_tensor_latest_meta.npz"
    )


def load_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Sequence tensor metadata not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def normalize_train_only_sequence(
    x_values: np.ndarray, train_idx: Sequence[int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    raw = x_values.astype(np.float32)
    nonfinite = int(raw.size - np.isfinite(raw).sum())
    clean = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    train = clean[np.asarray(train_idx, dtype=np.int64)]
    mean = np.mean(train, axis=(0, 1), keepdims=True)
    std = np.std(train, axis=(0, 1), keepdims=True)
    mean = np.nan_to_num(mean, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    std = np.nan_to_num(std, nan=1.0, posinf=1.0, neginf=1.0).astype(np.float32)
    std = np.where((~np.isfinite(std)) | (std < 1e-6), 1.0, std).astype(np.float32)
    normalized = (clean - mean) / std
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    return normalized.astype(np.float32), mean, std, nonfinite


def compute_streaming_scaler_sequence(
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
        batch_sum = batch.sum(axis=(0, 1), dtype=np.float64)
        batch_squares = np.square(batch, dtype=np.float64).sum(axis=(0, 1), dtype=np.float64)
        sum_values = batch_sum if sum_values is None else sum_values + batch_sum
        sum_squares = batch_squares if sum_squares is None else sum_squares + batch_squares
        count += int(batch.shape[0] * batch.shape[1])
    assert sum_values is not None and sum_squares is not None
    mean_vector = sum_values / max(count, 1)
    variance = np.maximum(sum_squares / max(count, 1) - np.square(mean_vector), 0.0)
    std_vector = np.sqrt(variance)
    std_vector = np.where((~np.isfinite(std_vector)) | (std_vector < 1e-6), 1.0, std_vector)
    mean = mean_vector.reshape(1, 1, -1).astype(np.float32)
    std = std_vector.reshape(1, 1, -1).astype(np.float32)
    return mean, std, nonfinite


def normalize_batch_sequence(x_batch: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    clean = np.nan_to_num(x_batch.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    normalized = (clean - mean) / std
    return np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def make_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    targets: Mapping[str, np.ndarray],
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int,
    weights: Mapping[str, np.ndarray] | None = None,
    shuffle: bool = False,
) -> Any:
    class PivotSequence(tf.keras.utils.Sequence):
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
            self.rng = np.random.default_rng(20260917)
            self.on_epoch_end()

        def __len__(self) -> int:
            return int(np.ceil(len(self.tensor_indices) / max(int(batch_size), 1)))

        def on_epoch_end(self) -> None:
            if self.shuffle:
                self.rng.shuffle(self.order)

        def __getitem__(self, index: int):
            start = index * max(int(batch_size), 1)
            end = min(len(self.order), start + max(int(batch_size), 1))
            local = self.order[start:end]
            rows = self.tensor_indices[local]
            x_batch = normalize_batch_sequence(np.asarray(x_values[rows]), mean, std)
            y_batch = {key: value[local] for key, value in self.targets.items()}
            if self.weights is None:
                return x_batch, y_batch
            return x_batch, y_batch, {key: value[local] for key, value in self.weights.items()}

    return PivotSequence()


def make_predict_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int,
) -> Any:
    class PivotPredictSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.tensor_indices = np.asarray(tensor_indices, dtype=np.int64)

        def __len__(self) -> int:
            return int(np.ceil(len(self.tensor_indices) / max(int(batch_size), 1)))

        def __getitem__(self, index: int) -> np.ndarray:
            start = index * max(int(batch_size), 1)
            end = min(len(self.tensor_indices), start + max(int(batch_size), 1))
            return normalize_batch_sequence(
                np.asarray(x_values[self.tensor_indices[start:end]]), mean, std
            )

    return PivotPredictSequence()


def grouped_indices(meta: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    names = [str(value) for value in np.asarray(meta.get("feature_names", [])).tolist()]
    groups = [str(value) for value in np.asarray(meta.get("feature_groups", [])).tolist()]
    if not names:
        raise RuntimeError("sequence tensor meta must include feature_names")
    if len(groups) != len(names):
        groups = ["unknown"] * len(names)
    m5 = [
        idx
        for idx, (name, group) in enumerate(zip(names, groups, strict=True))
        if group in {"generated_5m", "source_5m", "session"}
        or name.startswith(("m5_", "src5m_", "session_"))
    ]
    htf = [
        idx
        for idx, (name, group) in enumerate(zip(names, groups, strict=True))
        if group in {"closed_4h", "closed_1d"} or name.startswith(("h4_", "d1_"))
    ]
    all_idx = np.arange(len(names), dtype=np.int32)
    return (
        np.asarray(m5 or all_idx, dtype=np.int32),
        np.asarray(htf or all_idx, dtype=np.int32),
        all_idx,
    )


def gather_features(tf: Any, x: Any, indices: np.ndarray, name: str) -> Any:
    constants = tf.constant(indices.tolist(), dtype=tf.int32)
    time_dim = int(x.shape[1]) if x.shape[1] is not None else None
    return tf.keras.layers.Lambda(
        lambda tensor: tf.gather(tensor, constants, axis=-1),
        output_shape=(time_dim, int(len(indices))),
        name=name,
    )(x)


def multi_scale_temporal(
    tf: Any, x: Any, filters: int, kernels: Sequence[int], activation: str, name: str
) -> Any:
    branches = []
    for kernel in kernels:
        branch = tf.keras.layers.Conv1D(
            filters,
            max(int(kernel), 1),
            padding="causal",
            activation=None,
            name=f"{name}_k{kernel}_conv",
        )(x)
        branch = activation_layer(tf, f"{name}_k{kernel}_{activation}", activation)(branch)
        branches.append(branch)
    return (
        branches[0]
        if len(branches) == 1
        else tf.keras.layers.Concatenate(name=f"{name}_concat")(branches)
    )


def build_sequence_wavenet_model(
    tf: Any, input_shape: tuple[int, int], meta: Mapping[str, Any], args: argparse.Namespace
) -> Any:
    temporal_kernels = parse_int_list(args.temporal_kernels, [3, 5, 9])
    dilations = parse_int_list(args.dilations, [1, 2, 4, 8, 16, 32])
    m5_idx, htf_idx, all_idx = grouped_indices(meta)
    inputs = tf.keras.Input(shape=input_shape, name="pivot_sequence_tensor")
    pure_5m = gather_features(tf, inputs, m5_idx, "gather_5m_features")
    pure_htf = gather_features(tf, inputs, htf_idx, "gather_htf_features")
    all_features = gather_features(tf, inputs, all_idx, "gather_all_features")

    branch_filters = max(int(args.branch_filters), 1)
    pure_5m = multi_scale_temporal(
        tf, pure_5m, branch_filters, temporal_kernels, args.activation, "m5_branch"
    )
    pure_htf = multi_scale_temporal(
        tf, pure_htf, branch_filters, temporal_kernels, args.activation, "htf_branch"
    )
    all_features = multi_scale_temporal(
        tf, all_features, branch_filters, temporal_kernels, args.activation, "all_feature_branch"
    )

    x = tf.keras.layers.Concatenate(name="sequence_branch_fusion")(
        [pure_5m, pure_htf, all_features]
    )
    x = tf.keras.layers.Conv1D(
        max(int(args.temporal_filters), 1), 1, padding="same", name="temporal_projection"
    )(x)
    x = tf.keras.layers.LayerNormalization(name="temporal_projection_norm")(x)
    skips = []
    for block in range(max(int(args.residual_blocks), 1)):
        for dilation in dilations:
            x, skip = gated_dilated_residual_block(
                tf,
                x,
                max(int(args.temporal_filters), 1),
                3,
                dilation,
                args.dropout,
                args.se_ratio,
                f"sequence_wavenet_b{block + 1}_d{dilation}",
            )
            skips.append(skip)
    x = tf.keras.layers.Add(name="skip_sum")(skips) if len(skips) > 1 else skips[0]
    x = activation_layer(tf, f"skip_sum_{args.activation}", args.activation)(x)
    x = tf.keras.layers.Conv1D(
        max(int(args.temporal_filters), 1), 1, padding="same", name="post_skip_1x1"
    )(x)
    x = squeeze_excitation_1d(
        tf, x, max(int(args.temporal_filters), 1), args.se_ratio, "post_skip_se"
    )
    attention = tf.keras.layers.MultiHeadAttention(
        num_heads=max(int(args.attention_heads), 1),
        key_dim=max(int(args.attention_key_dim), 1),
        dropout=max(float(args.dropout), 0.0),
        name="temporal_self_attention",
    )(x, x)
    x = tf.keras.layers.Add(name="attention_residual")([x, attention])
    x = tf.keras.layers.LayerNormalization(name="attention_norm")(x)
    avg_pool = tf.keras.layers.GlobalAveragePooling1D(name="temporal_avg_pool")(x)
    max_pool = tf.keras.layers.GlobalMaxPooling1D(name="temporal_max_pool")(x)
    last_state = tf.keras.layers.Lambda(
        lambda tensor: tensor[:, -1, :],
        output_shape=(int(x.shape[-1]) if x.shape[-1] is not None else None,),
        name="last_temporal_state",
    )(x)
    x = tf.keras.layers.Concatenate(name="temporal_pool_concat")([avg_pool, max_pool, last_state])
    x = tf.keras.layers.Dense(max(int(args.dense_units), 8), activation="tanh", name="dense_tanh")(
        x
    )
    x = tf.keras.layers.Dropout(max(float(args.dropout), 0.0), name="dense_dropout")(x)
    outputs = {
        "action": tf.keras.layers.Dense(3, activation="softmax", name="action")(x),
        "top": tf.keras.layers.Dense(1, activation="sigmoid", name="top")(x),
        "bottom": tf.keras.layers.Dense(1, activation="sigmoid", name="bottom")(x),
        "buy_r": tf.keras.layers.Dense(1, activation="linear", name="buy_r")(x),
        "sell_r": tf.keras.layers.Dense(1, activation="linear", name="sell_r")(x),
    }
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="pivot_sequence_wavenet_advanced")
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


def prepare_paths(model: Any, args: argparse.Namespace) -> tuple[int, str, str, str]:
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    version = next_version(model_dir)
    architecture_path, summary_path = save_architecture_artifacts(model, model_dir, version)
    checkpoint_path = str(model_dir / f"v{version}_epoch_checkpoint.keras")
    return version, checkpoint_path, architecture_path, summary_path


def save_final_model(
    model: Any,
    report_stub: Mapping[str, Any],
    payload: Mapping[str, Any],
    args: argparse.Namespace,
    version: int,
) -> tuple[str, str, str, str, int]:
    if args.save_model != "1":
        return "", "", "", "", 0
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    resolved = version if version > 0 else next_version(model_dir)
    model_path = model_dir / f"v{resolved}_model.keras"
    record_path = model_dir / f"v{resolved}_training.json"
    model.save(model_path)
    architecture_path, summary_path = save_architecture_artifacts(model, model_dir, resolved)
    record = {
        **dict(report_stub),
        "version": resolved,
        "model_path": str(model_path),
        "record_path": str(record_path),
        "architecture_json_path": architecture_path,
        "model_summary_path": summary_path,
        "payload": dict(payload),
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(model_path), str(record_path), architecture_path, summary_path, resolved


def render_html(title: str, report: SequenceWaveNetReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Advanced Conv1D/WaveNet over [batch, window, features].</p></section>
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
        print("  PHASE145A TRAIN ADVANCED PIVOT SEQUENCE WAVENET")
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
            mean, std, nonfinite_input_values = compute_streaming_scaler_sequence(
                x_all, indices[train_idx], int(args.stream_chunk_size)
            )
            model_input_shape = tuple(int(value) for value in x_all.shape[1:])
            model = build_sequence_wavenet_model(tf, model_input_shape, meta, args)
        else:
            x_loaded = np.asarray(x_all[indices], dtype=np.float32)
            x_norm, mean, std, nonfinite_input_values = normalize_train_only_sequence(
                x_loaded, train_idx
            )
            model_input_shape = tuple(int(value) for value in x_norm.shape[1:])
            model = build_sequence_wavenet_model(tf, model_input_shape, meta, args)
        version, checkpoint_path, architecture_path, summary_path = (
            prepare_paths(model, args) if args.save_model == "1" else (0, "", "", "")
        )
        callbacks: list[Any] = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=max(int(args.early_stopping_patience), 1),
                restore_best_weights=True,
            ),
            tf.keras.callbacks.CSVLogger(str(output_dir / "latest_training_log.csv")),
            BatchProgressLogger(tf, batch_log_path, int(args.batch_log_every)).as_callback(),
        ]
        if args.save_model == "1" and args.checkpoint_each_epoch == "1":
            callbacks.append(
                tf.keras.callbacks.ModelCheckpoint(
                    filepath=checkpoint_path,
                    monitor="val_loss",
                    save_best_only=False,
                    save_weights_only=False,
                    verbose=1,
                )
            )
        print(f"  loader-mode : {args.loader_mode}")
        if checkpoint_path:
            print(f"  checkpoint  : {checkpoint_path}")
            print(f"  summary     : {summary_path}")
            print(f"  architecture: {architecture_path}")
        if args.loader_mode == "stream":
            train_sequence = make_sequence(
                tf,
                x_all,
                indices[train_idx],
                train_targets,
                mean,
                std,
                int(args.batch_size),
                sample_weights(train_targets, args.class_weight),
                shuffle=True,
            )
            validation_sequence = make_sequence(
                tf,
                x_all,
                indices[validation_idx],
                validation_targets,
                mean,
                std,
                int(args.batch_size),
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
                        tf, x_all, indices[validation_idx], mean, std, int(args.batch_size)
                    ),
                    verbose=0,
                )
            )
            test_pred = prediction_dict(
                model.predict(
                    make_predict_sequence(
                        tf, x_all, indices[test_idx], mean, std, int(args.batch_size)
                    ),
                    verbose=0,
                )
            )
        else:
            model.fit(
                x_norm[train_idx],
                train_targets,
                validation_data=(x_norm[validation_idx], validation_targets),
                sample_weight=sample_weights(train_targets, args.class_weight),
                batch_size=max(int(args.batch_size), 1),
                epochs=max(int(args.epochs), 1),
                callbacks=callbacks,
                verbose=2,
            )
            validation_pred = prediction_dict(
                model.predict(x_norm[validation_idx], batch_size=args.batch_size, verbose=0)
            )
            test_pred = prediction_dict(
                model.predict(x_norm[test_idx], batch_size=args.batch_size, verbose=0)
            )
        metrics: dict[str, float] = {}
        metrics.update(metric_block(validation_targets, validation_pred, args, "val"))
        metrics.update(metric_block(test_targets, test_pred, args, "test"))
        feature_names = [str(value) for value in np.asarray(meta.get("feature_names", [])).tolist()]
        feature_groups = [
            str(value) for value in np.asarray(meta.get("feature_groups", [])).tolist()
        ]
        m5_count = sum(
            1 for group in feature_groups if group in {"generated_5m", "source_5m", "session"}
        )
        htf_count = sum(1 for group in feature_groups if group in {"closed_4h", "closed_1d"})
        other_count = len(feature_names) - m5_count - htf_count
        report_stub = {
            "model_id": args.model_id,
            "phase": "Phase145A",
            "role": "pivot_sequence_wavenet_advanced",
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
            "feature_names": feature_names,
            "feature_groups": feature_groups,
            "thresholds": {
                "buy_threshold": args.buy_threshold,
                "sell_threshold": args.sell_threshold,
                "min_margin": args.min_margin,
                "min_buy_r": args.min_buy_r,
                "min_sell_r": args.min_sell_r,
            },
            "architecture": {
                "branch_filters": args.branch_filters,
                "temporal_filters": args.temporal_filters,
                "temporal_kernels": parse_int_list(args.temporal_kernels, [3, 5, 9]),
                "dilations": parse_int_list(args.dilations, [1, 2, 4, 8, 16, 32]),
                "residual_blocks": args.residual_blocks,
                "attention_heads": args.attention_heads,
                "attention_key_dim": args.attention_key_dim,
                "se_ratio": args.se_ratio,
                "activation": args.activation,
            },
        }
        model_path, record_path, architecture_path, summary_path, version = save_final_model(
            model, report_stub, payload, args, version
        )
        report = SequenceWaveNetReport(
            model_id=args.model_id,
            version=version,
            tensor_path=str(tensor_path),
            meta_path=str(meta_path),
            samples=len(indices),
            train_rows=len(train_idx),
            validation_rows=len(validation_idx),
            test_rows=len(test_idx),
            stored_x_shape=selected_shape,
            keras_batch_shape=f"[batch, {', '.join(str(int(v)) for v in model_input_shape)}]",
            metrics=metrics,
            architecture_features=[
                "concatenated_feature_axis",
                "separate_5m_branch",
                "separate_htf_branch",
                "all_feature_branch",
                "multi_scale_temporal_kernels",
                "gated_tanh_sigmoid_dilated_wavenet",
                "residual_connections",
                "skip_connections",
                "squeeze_excitation",
                "temporal_self_attention",
                "avg_max_last_pooling",
                "multi_task_heads",
            ],
            feature_count=len(feature_names),
            m5_feature_count=m5_count,
            htf_feature_count=htf_count,
            other_feature_count=other_count,
            model_path=model_path,
            record_path=record_path,
            architecture_json_path=architecture_path,
            model_summary_path=summary_path,
            epoch_checkpoint_path=checkpoint_path,
            batch_log_path=str(batch_log_path),
            nonfinite_input_values=int(nonfinite_input_values),
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            production_status="BLOCKED — research sequence WaveNet only",
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
        if architecture_path:
            Path(output_dir / "latest_architecture.json").write_text(
                Path(architecture_path).read_text(encoding="utf-8"), encoding="utf-8"
            )
        if summary_path:
            Path(output_dir / "latest_summary.txt").write_text(
                Path(summary_path).read_text(encoding="utf-8"), encoding="utf-8"
            )
        print(f"  X shape     : {report.stored_x_shape}")
        print(f"  keras batch : {report.keras_batch_shape}")
        print(f"  features    : {report.feature_count:,}")
        print(f"  val acc     : {metrics.get('val_action_accuracy', 0.0):.4f}")
        print(f"  test acc    : {metrics.get('test_action_accuracy', 0.0):.4f}")
        print(f"  test select : {metrics.get('test_selected_rate', 0.0):.2%}")
        print(f"  model       : {model_path}")
        print(f"  summary     : {summary_path}")
        print(f"  architecture: {architecture_path}")
        print(f"  checkpoint  : {checkpoint_path}")
        print(f"  batch log   : {batch_log_path}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
