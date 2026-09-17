"""Phase144A: train advanced 4D Pivot Image WaveNet.

This is the non-baseline architecture for the owner-requested tensor layout:

    stored X: [samples, window, features_5m, features_4h_1d]
    Keras batch: [batch, window, features_5m, features_4h_1d]

Architecture summary:

* separate pure 5M branch from the HTF-bias column
* separate pure 4H/1D branch from the 5M-bias row
* per-time-step interaction image encoder over [features_5m, features_4h_1d]
* multi-scale kernels
* gated tanh-sigmoid dilated temporal WaveNet residual blocks
* squeeze-excitation channel attention
* temporal multi-head self-attention
* multi-head trading outputs
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

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from train_pivot_pattern_image_cnn import (
    BatchProgressLogger,
    compute_streaming_scaler,
    default_meta_path,
    default_tensor_path,
    load_meta,
    make_predict_sequence,
    make_tensor_sequence,
    metric_block,
    next_version,
    normalize_train_only,
    sample_weights,
    selected_indices,
    split_indices,
    target_dict,
)
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_image_wavenet")


@dataclass(frozen=True)
class ImageWaveNetReport:
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


def parse_int_list(text: str, default: Sequence[int]) -> list[int]:
    values: list[int] = []
    for raw in (part.strip() for part in str(text).split(",")):
        if not raw:
            continue
        value = max(int(raw), 1)
        if value not in values:
            values.append(value)
    return values or list(default)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Phase144A advanced 4D Pivot Image WaveNet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_image_wavenet_5m")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--loader-mode", choices=("stream", "memory"), default="stream")
    parser.add_argument("--stream-chunk-size", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--spatial-filters", type=int, default=32)
    parser.add_argument("--branch-filters", type=int, default=32)
    parser.add_argument("--temporal-filters", type=int, default=64)
    parser.add_argument("--spatial-kernels", default="1,3,5")
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
    parser.add_argument("--report-title", default="Advanced Pivot Image WaveNet training")
    return parser.parse_args(argv)


def activation_layer(tf: Any, name: str, activation: str) -> Any:
    if activation == "gelu":
        return tf.keras.layers.Activation(tf.keras.activations.gelu, name=name)
    if activation == "swish":
        return tf.keras.layers.Activation(tf.keras.activations.swish, name=name)
    return tf.keras.layers.Activation("tanh", name=name)


def squeeze_excitation_1d(tf: Any, x: Any, filters: int, ratio: int, name: str) -> Any:
    hidden = max(int(filters) // max(int(ratio), 1), 4)
    se = tf.keras.layers.GlobalAveragePooling1D(name=f"{name}_gap")(x)
    se = tf.keras.layers.Dense(hidden, activation="tanh", name=f"{name}_dense_1")(se)
    se = tf.keras.layers.Dense(filters, activation="sigmoid", name=f"{name}_dense_2")(se)
    se = tf.keras.layers.Reshape((1, filters), name=f"{name}_reshape")(se)
    return tf.keras.layers.Multiply(name=f"{name}_scale")([x, se])


def multi_scale_temporal_branch(
    tf: Any,
    x: Any,
    filters: int,
    kernels: Sequence[int],
    activation: str,
    name: str,
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
    if len(branches) == 1:
        return branches[0]
    return tf.keras.layers.Concatenate(name=f"{name}_concat")(branches)


def time_distributed_spatial_encoder(
    tf: Any,
    inputs: Any,
    filters: int,
    kernels: Sequence[int],
    activation: str,
    dropout: float,
) -> Any:
    # [batch, time, f5, htf] -> [batch, time, f5, htf, 1]
    x = tf.keras.layers.Reshape(
        (inputs.shape[1], inputs.shape[2], inputs.shape[3], 1), name="interaction_add_channel"
    )(inputs)
    branches = []
    for kernel in kernels:
        kernel_size = (max(int(kernel), 1), max(int(kernel), 1))
        branch = tf.keras.layers.TimeDistributed(
            tf.keras.layers.Conv2D(filters, kernel_size, padding="same", activation=None),
            name=f"spatial_td_conv_k{kernel}",
        )(x)
        branch = tf.keras.layers.TimeDistributed(
            tf.keras.layers.BatchNormalization(), name=f"spatial_td_bn_k{kernel}"
        )(branch)
        branch = tf.keras.layers.TimeDistributed(
            activation_layer(tf, f"spatial_inner_{activation}_k{kernel}", activation),
            name=f"spatial_td_{activation}_k{kernel}",
        )(branch)
        branch = tf.keras.layers.TimeDistributed(
            tf.keras.layers.GlobalAveragePooling2D(), name=f"spatial_td_gap_k{kernel}"
        )(branch)
        branches.append(branch)
    x = (
        branches[0]
        if len(branches) == 1
        else tf.keras.layers.Concatenate(name="spatial_multiscale_concat")(branches)
    )
    x = tf.keras.layers.Dropout(max(float(dropout), 0.0), name="spatial_dropout")(x)
    return x


def gated_dilated_residual_block(
    tf: Any,
    x: Any,
    filters: int,
    kernel_size: int,
    dilation: int,
    dropout: float,
    se_ratio: int,
    block_name: str,
) -> tuple[Any, Any]:
    residual = x
    filter_branch = tf.keras.layers.Conv1D(
        filters,
        max(int(kernel_size), 2),
        padding="causal",
        dilation_rate=max(int(dilation), 1),
        activation="tanh",
        name=f"{block_name}_filter_tanh",
    )(x)
    gate_branch = tf.keras.layers.Conv1D(
        filters,
        max(int(kernel_size), 2),
        padding="causal",
        dilation_rate=max(int(dilation), 1),
        activation="sigmoid",
        name=f"{block_name}_gate_sigmoid",
    )(x)
    x = tf.keras.layers.Multiply(name=f"{block_name}_gated_multiply")([filter_branch, gate_branch])
    x = tf.keras.layers.SpatialDropout1D(
        max(float(dropout), 0.0), name=f"{block_name}_spatial_dropout"
    )(x)
    x = squeeze_excitation_1d(tf, x, filters, se_ratio, f"{block_name}_se")
    skip = tf.keras.layers.Conv1D(filters, 1, padding="same", name=f"{block_name}_skip")(x)
    transformed = tf.keras.layers.Conv1D(
        filters, 1, padding="same", name=f"{block_name}_residual_projection"
    )(x)
    if int(residual.shape[-1]) != int(filters):
        residual = tf.keras.layers.Conv1D(
            filters, 1, padding="same", name=f"{block_name}_match_channels"
        )(residual)
    output = tf.keras.layers.Add(name=f"{block_name}_residual_add")([residual, transformed])
    output = tf.keras.layers.LayerNormalization(name=f"{block_name}_residual_norm")(output)
    return output, skip


def build_image_wavenet_model(
    tf: Any, input_shape: tuple[int, int, int], args: argparse.Namespace
) -> Any:
    spatial_kernels = parse_int_list(args.spatial_kernels, [1, 3, 5])
    temporal_kernels = parse_int_list(args.temporal_kernels, [3, 5, 9])
    dilations = parse_int_list(args.dilations, [1, 2, 4, 8, 16, 32])
    inputs = tf.keras.Input(shape=input_shape, name="pivot_image_tensor")

    # Pure 5M branch from HTF-bias column: [batch, time, features_5m]
    pure_5m = tf.keras.layers.Lambda(lambda t: t[:, :, :, 0], name="pure_5m_from_htf_bias")(inputs)
    pure_5m = multi_scale_temporal_branch(
        tf,
        pure_5m,
        max(int(args.branch_filters), 1),
        temporal_kernels,
        args.activation,
        "pure_5m_temporal",
    )

    # Pure HTF branch from 5M-bias row: [batch, time, features_4h_1d]
    pure_htf = tf.keras.layers.Lambda(lambda t: t[:, :, 0, :], name="pure_htf_from_5m_bias")(inputs)
    pure_htf = multi_scale_temporal_branch(
        tf,
        pure_htf,
        max(int(args.branch_filters), 1),
        temporal_kernels,
        args.activation,
        "pure_htf_temporal",
    )

    spatial = time_distributed_spatial_encoder(
        tf,
        inputs,
        max(int(args.spatial_filters), 1),
        spatial_kernels,
        args.activation,
        args.dropout,
    )

    x = tf.keras.layers.Concatenate(name="separate_branch_fusion")([pure_5m, pure_htf, spatial])
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
                f"wavenet_b{block + 1}_d{dilation}",
            )
            skips.append(skip)
    x = tf.keras.layers.Add(name="skip_sum")(skips) if len(skips) > 1 else skips[0]
    x = activation_layer(tf, f"skip_sum_{args.activation}", args.activation)(x)
    x = tf.keras.layers.Conv1D(
        max(int(args.temporal_filters), 1), 1, padding="same", name="post_skip_1x1"
    )(x)

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
    last_state = tf.keras.layers.Lambda(lambda t: t[:, -1, :], name="last_temporal_state")(x)
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
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="pivot_image_wavenet_advanced")
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


def save_architecture_artifacts(model: Any, model_dir: Path, version: int) -> tuple[str, str]:
    summary_lines: list[str] = []
    model.summary(print_fn=summary_lines.append)
    summary_path = model_dir / f"v{version}_summary.txt"
    architecture_path = model_dir / f"v{version}_architecture.json"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    architecture_path.write_text(model.to_json(indent=2), encoding="utf-8")
    return str(architecture_path), str(summary_path)


def prepare_artifact_paths(model: Any, args: argparse.Namespace) -> tuple[Path, int, str, str, str]:
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    version = next_version(model_dir)
    architecture_path, summary_path = save_architecture_artifacts(model, model_dir, version)
    checkpoint_path = model_dir / f"v{version}_epoch_checkpoint.keras"
    return model_dir, version, str(checkpoint_path), architecture_path, summary_path


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
    resolved_version = version if version > 0 else next_version(model_dir)
    model_path = model_dir / f"v{resolved_version}_model.keras"
    record_path = model_dir / f"v{resolved_version}_training.json"
    model.save(model_path)
    architecture_path, summary_path = save_architecture_artifacts(
        model, model_dir, resolved_version
    )
    record = {
        **dict(report_stub),
        "version": resolved_version,
        "model_path": str(model_path),
        "record_path": str(record_path),
        "architecture_json_path": architecture_path,
        "model_summary_path": summary_path,
        "payload": dict(payload),
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(model_path), str(record_path), architecture_path, summary_path, resolved_version


def render_html(title: str, report: ImageWaveNetReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Advanced 4D Pivot Image WaveNet: residual, SE, dilated temporal conv, separate 5M/HTF branches, temporal attention, multi-scale kernels, gated tanh.</p></section>
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
        print("  PHASE144A TRAIN ADVANCED PIVOT IMAGE WAVENET")
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
            model_input_shape = tuple(int(value) for value in x_all.shape[1:])
            model = build_image_wavenet_model(tf, model_input_shape, args)
        else:
            x_loaded = np.asarray(x_all[indices], dtype=np.float32)
            x_norm, mean, std, nonfinite_input_values = normalize_train_only(x_loaded, train_idx)
            model_input_shape = tuple(int(value) for value in x_norm.shape[1:])
            model = build_image_wavenet_model(tf, model_input_shape, args)

        _model_dir, version, checkpoint_path, architecture_path, summary_path = (
            prepare_artifact_paths(model, args)
            if args.save_model == "1"
            else (Path(args.storage_root) / "models" / args.model_id, 0, "", "", "")
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
        if checkpoint_path:
            print(f"  checkpoint  : {checkpoint_path}")
            print(f"  summary     : {summary_path}")
            print(f"  architecture: {architecture_path}")
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
                "conv2d",
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
                "conv2d",
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
                        "conv2d",
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
                        "conv2d",
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
        report_stub = {
            "model_id": args.model_id,
            "phase": "Phase144A",
            "role": "pivot_image_wavenet_advanced",
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
            "feature_5m_names": [str(value) for value in meta.get("feature_5m_names", [])],
            "feature_htf_names": [str(value) for value in meta.get("feature_htf_names", [])],
            "thresholds": {
                "buy_threshold": args.buy_threshold,
                "sell_threshold": args.sell_threshold,
                "min_margin": args.min_margin,
                "min_buy_r": args.min_buy_r,
                "min_sell_r": args.min_sell_r,
            },
            "architecture": {
                "spatial_filters": args.spatial_filters,
                "branch_filters": args.branch_filters,
                "temporal_filters": args.temporal_filters,
                "spatial_kernels": parse_int_list(args.spatial_kernels, [1, 3, 5]),
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
        report = ImageWaveNetReport(
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
                "separate_5m_branch",
                "separate_htf_branch",
                "time_distributed_spatial_multiscale_conv2d",
                "gated_tanh_sigmoid_dilated_temporal_wavenet",
                "residual_connections",
                "skip_connections",
                "squeeze_excitation",
                "temporal_self_attention",
                "multi_scale_kernels",
            ],
            model_path=model_path,
            record_path=record_path,
            architecture_json_path=architecture_path,
            model_summary_path=summary_path,
            epoch_checkpoint_path=checkpoint_path,
            batch_log_path=str(batch_log_path),
            nonfinite_input_values=int(nonfinite_input_values),
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            production_status="BLOCKED — research advanced image WaveNet only",
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
