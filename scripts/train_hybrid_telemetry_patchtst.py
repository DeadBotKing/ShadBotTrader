"""Phase131A: train a PatchTST meta model on the Phase127 telemetry tensor."""

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
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
from train_hybrid_telemetry_wavenet import (
    MONITOR_CHOICES,
    TASKS,
    class_weights,
    compute_metrics,
    default_tensor_path,
    load_tensor,
    monitor_mode,
    normalize_train_only,
    prediction_arrays,
    require_tensorflow,
    sample_weights,
    selected_indices,
    serialize_model,
    split_indices,
    target_payload,
)

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_telemetry_patchtst")


@dataclass(frozen=True)
class TelemetryPatchTSTReport:
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
    patch_len: int
    stride: int
    layers: int
    metrics: dict[str, float]
    record_path: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Phase131 PatchTST model on a Phase127 telemetry tensor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_telemetry_patchtst_5m")
    parser.add_argument("--task", choices=TASKS, default="multihead")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all selected samples")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--patch-len", type=int, default=16)
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--ff-units", type=int, default=128)
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


def patch_count(time_steps: int, patch_len: int, stride: int) -> int:
    validate_patch_args(time_steps, patch_len, stride)
    return 1 + (time_steps - patch_len) // stride


def validate_patch_args(time_steps: int, patch_len: int, stride: int) -> None:
    if patch_len < 1:
        raise RuntimeError("patch-len must be positive")
    if stride < 1:
        raise RuntimeError("stride must be positive")
    if patch_len > time_steps:
        raise RuntimeError(
            f"patch-len {patch_len} is larger than tensor window {time_steps}; lower --patch-len"
        )


def transformer_encoder_block(
    tf: Any,
    x: Any,
    d_model: int,
    heads: int,
    ff_units: int,
    dropout: float,
    name: str,
) -> Any:
    """A compact Transformer encoder block over temporal patches."""

    attn_input = tf.keras.layers.LayerNormalization(name=f"{name}_attn_ln")(x)
    attn = tf.keras.layers.MultiHeadAttention(
        num_heads=max(heads, 1),
        key_dim=max(d_model // max(heads, 1), 1),
        dropout=max(dropout, 0.0),
        name=f"{name}_mha",
    )(attn_input, attn_input)
    if dropout > 0:
        attn = tf.keras.layers.Dropout(dropout, name=f"{name}_attn_dropout")(attn)
    x = tf.keras.layers.Add(name=f"{name}_attn_residual")([x, attn])

    ff_input = tf.keras.layers.LayerNormalization(name=f"{name}_ff_ln")(x)
    ff = tf.keras.layers.Dense(max(ff_units, 1), activation="gelu", name=f"{name}_ff_1")(ff_input)
    if dropout > 0:
        ff = tf.keras.layers.Dropout(dropout, name=f"{name}_ff_dropout")(ff)
    ff = tf.keras.layers.Dense(max(d_model, 1), name=f"{name}_ff_2")(ff)
    return tf.keras.layers.Add(name=f"{name}_ff_residual")([x, ff])


def build_patchtst_model(tf: Any, input_shape: tuple[int, int], args: argparse.Namespace):
    time_steps, _channels = input_shape
    validate_patch_args(time_steps, args.patch_len, args.stride)
    n_patches = patch_count(time_steps, args.patch_len, args.stride)
    d_model = max(args.d_model, 1)

    inputs = tf.keras.Input(shape=input_shape, name="telemetry_window")
    x = tf.keras.layers.Conv1D(
        d_model,
        kernel_size=args.patch_len,
        strides=args.stride,
        padding="valid",
        name="patch_projection",
    )(inputs)
    positions = tf.keras.layers.Embedding(n_patches, d_model, name="position_embedding")(
        tf.keras.ops.arange(n_patches)
    )
    x = tf.keras.layers.Add(name="add_position")([x, positions])
    if args.dropout > 0:
        x = tf.keras.layers.Dropout(args.dropout, name="patch_dropout")(x)
    for layer in range(max(args.layers, 1)):
        x = transformer_encoder_block(
            tf,
            x,
            d_model,
            max(args.heads, 1),
            max(args.ff_units, 1),
            max(args.dropout, 0.0),
            f"encoder_{layer + 1}",
        )
    x = tf.keras.layers.LayerNormalization(name="final_ln")(x)
    x = tf.keras.layers.GlobalAveragePooling1D(name="global_pool")(x)
    x = tf.keras.layers.Dense(max(args.dense_units, 1), activation="relu", name="dense")(x)
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
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="hybrid_telemetry_patchtst")
    model.compile(optimizer=optimizer, loss=losses, loss_weights=loss_weights, metrics=metrics)
    return model


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
    model_id = args.model_id.strip() or "gold_hybrid_telemetry_patchtst_5m"
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
            "architecture": "patchtst",
            "patch_len": int(args.patch_len),
            "stride": int(args.stride),
        }
    )
    artifact = ModelArtifact.create(
        model_id=ModelId(model_id),
        version=ModelVersion(version),
        framework="tensorflow",
        framework_version=str(getattr(tf, "__version__", "tensorflow")),
        format="pickle_keras",
        payload=payload,
        training_run_id="hybrid_telemetry_patchtst",
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
        window_size=int(args.patch_len),
        feature_columns=len(channel_names),
        epochs=int(args.epochs),
        folds=1,
        threshold=0.0,
        learning_rate=float(args.learning_rate),
        loss_function=f"phase131_{args.task}_patchtst",
        horizon=0,
        metrics={key: float(value) for key, value in metrics.items()},
        note=f"Phase131 PatchTST trained on {tensor_path}",
        decision_thresholds={
            "meta_threshold": float(args.meta_threshold),
            "score_threshold": float(args.score_threshold),
            "selected_by": "phase131_initial_training",
            "task": args.task,
        },
    )
    record_path = catalogue.write(record)
    return model_id, version, str(record_path)


def write_report(
    args: argparse.Namespace, report: TelemetryPatchTSTReport, channel_names: Sequence[str]
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
        rule("PHASE131 TELEMETRY PATCHTST")
        print(f"  tensor      : {tensor_path}")
        print(f"  task        : {args.task}")
        data = load_tensor(tensor_path)
        selected = selected_indices(data, args.candidate_only, args.max_samples)
        x_raw = np.asarray(data["X"], dtype=np.float32)[selected]
        channel_names = [
            str(value) for value in np.asarray(data["channel_names"], dtype=object).tolist()
        ]
        validate_patch_args(int(x_raw.shape[1]), args.patch_len, args.stride)
        train_idx, val_idx, test_idx = split_indices(
            len(x_raw), args.train_frac, args.val_frac, args.purge_gap
        )
        x_values, mean, std = normalize_train_only(x_raw, train_idx)
        y_train = target_payload(data, selected[train_idx], args.task)
        y_val = target_payload(data, selected[val_idx], args.task)
        sample_weight = sample_weight_payload(y_train, args)
        tf = require_tensorflow()
        model = build_patchtst_model(tf, (x_values.shape[1], x_values.shape[2]), args)
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
        print(f"  patches     : {patch_count(int(x_values.shape[1]), args.patch_len, args.stride)}")
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
        model_id = args.model_id.strip() or "gold_hybrid_telemetry_patchtst_5m"
        version = 0
        record_path = ""
        if args.save_record == "1":
            model_id, version, record_path = save_artifact(
                args, tf, model, channel_names, mean, std, metrics, len(x_raw), tensor_path
            )
            print(f"  saved       : {record_path}")
        report = TelemetryPatchTSTReport(
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
            patch_len=int(args.patch_len),
            stride=int(args.stride),
            layers=max(args.layers, 1),
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
