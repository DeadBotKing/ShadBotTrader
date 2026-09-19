"""Phase147A: train Option B grouped-input sequence WaveNet.

Option B keeps the owner-requested sequence tensor source layout but feeds the
model as grouped inputs instead of one flattened feature stream:

    Stored tensor: [samples, window_size, features]

    Keras inputs:
      m5_context_input : [batch, window_size, generated_5m + session]
      source_5m_input  : [batch, window_size, source_5m telemetry]
      htf_context_input: [batch, window_size, closed_4H + closed_1D]

This separates microstructure, source telemetry, and higher-timeframe context
before late fusion into the same advanced WaveNet-style temporal core.
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
from train_pivot_pattern_sequence_wavenet import (
    compute_streaming_scaler_sequence,
    default_meta_path,
    default_tensor_path,
    load_meta,
    normalize_batch_sequence,
)
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_wavenet_option_b")


@dataclass(frozen=True)
class OptionBGroups:
    m5_context: np.ndarray
    source_5m: np.ndarray
    htf_context: np.ndarray


@dataclass(frozen=True)
class OptionBReport:
    model_id: str
    version: int
    tensor_path: str
    meta_path: str
    samples: int
    train_rows: int
    validation_rows: int
    test_rows: int
    stored_x_shape: list[int]
    keras_input_shapes: dict[str, str]
    metrics: dict[str, float]
    architecture_features: list[str]
    feature_count: int
    m5_context_feature_count: int
    source_5m_feature_count: int
    htf_feature_count: int
    branch_target_features: int
    feature_augmentation_mode: str
    feature_augmentation_clip: float
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
        description="Train Phase147A Option B grouped-input sequence WaveNet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_sequence_wavenet_option_b_5m")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--stream-chunk-size", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--branch-filters", type=int, default=48)
    parser.add_argument("--branch-target-features", type=int, default=0, help="0 = raw group feature counts; e.g. 180 expands every Option B input to 180 causal channels")
    parser.add_argument("--feature-augmentation-mode", choices=("off", "causal"), default="off")
    parser.add_argument("--feature-augmentation-clip", type=float, default=8.0)
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
    parser.add_argument("--report-title", default="Option B Pivot Sequence WaveNet training")
    return parser.parse_args(argv)


def option_b_groups(meta: Mapping[str, Any]) -> OptionBGroups:
    names = [str(value) for value in np.asarray(meta.get("feature_names", [])).tolist()]
    groups = [str(value) for value in np.asarray(meta.get("feature_groups", [])).tolist()]
    if not names:
        raise RuntimeError("sequence tensor meta must include feature_names")
    if len(groups) != len(names):
        groups = ["unknown"] * len(names)
    m5_context: list[int] = []
    source_5m: list[int] = []
    htf_context: list[int] = []
    for idx, (name, group) in enumerate(zip(names, groups, strict=True)):
        if group == "source_5m" or name.startswith("src5m_"):
            source_5m.append(idx)
        elif group in {"closed_4h", "closed_1d"} or name.startswith(("h4_", "d1_")):
            htf_context.append(idx)
        elif group in {"generated_5m", "session"} or name.startswith(("m5_", "session_")):
            m5_context.append(idx)
    all_idx = list(range(len(names)))
    return OptionBGroups(
        m5_context=np.asarray(m5_context or all_idx, dtype=np.int32),
        source_5m=np.asarray(source_5m or all_idx, dtype=np.int32),
        htf_context=np.asarray(htf_context or all_idx, dtype=np.int32),
    )


def lagged_values(values: np.ndarray, lag: int) -> np.ndarray:
    shifted = np.zeros_like(values, dtype=np.float32)
    if lag > 0 and values.shape[1] > lag:
        shifted[:, lag:, :] = values[:, :-lag, :]
    return shifted


def rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    window = max(int(window), 1)
    if window <= 1:
        return values.astype(np.float32)
    result = np.zeros_like(values, dtype=np.float32)
    for end in range(values.shape[1]):
        start = max(0, end - window + 1)
        result[:, end, :] = values[:, start : end + 1, :].mean(axis=1)
    return result


def expand_group_features(
    values: np.ndarray, target_features: int, mode: str, clip_value: float
) -> np.ndarray:
    base = np.nan_to_num(values.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    target = max(int(target_features), 0)
    if target <= 0:
        return base
    if base.shape[-1] >= target:
        return base[:, :, :target]
    if mode != "causal":
        pad_width = target - int(base.shape[-1])
        padding = np.zeros((*base.shape[:2], pad_width), dtype=np.float32)
        return np.concatenate([base, padding], axis=-1)
    lag1 = lagged_values(base, 1)
    lag3 = lagged_values(base, 3)
    lag6 = lagged_values(base, 6)
    derived = [
        base,
        base - lag1,
        base - lag3,
        base - lag6,
        rolling_mean(base, 3),
        rolling_mean(base, 6),
        rolling_mean(base, 12),
        np.abs(base - lag1),
        np.abs(base - lag3),
    ]
    expanded = np.concatenate(derived, axis=-1)
    if expanded.shape[-1] < target:
        padding = np.zeros((*expanded.shape[:2], target - expanded.shape[-1]), dtype=np.float32)
        expanded = np.concatenate([expanded, padding], axis=-1)
    expanded = expanded[:, :, :target]
    if clip_value > 0:
        expanded = np.clip(expanded, -float(clip_value), float(clip_value))
    return np.nan_to_num(expanded, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def grouped_normalized_batch(
    normalized: np.ndarray,
    groups: OptionBGroups,
    branch_target_features: int,
    feature_augmentation_mode: str,
    feature_augmentation_clip: float,
) -> dict[str, np.ndarray]:
    return {
        "m5_context_input": expand_group_features(
            normalized[:, :, groups.m5_context],
            branch_target_features,
            feature_augmentation_mode,
            feature_augmentation_clip,
        ),
        "source_5m_input": expand_group_features(
            normalized[:, :, groups.source_5m],
            branch_target_features,
            feature_augmentation_mode,
            feature_augmentation_clip,
        ),
        "htf_context_input": expand_group_features(
            normalized[:, :, groups.htf_context],
            branch_target_features,
            feature_augmentation_mode,
            feature_augmentation_clip,
        ),
    }


def grouped_batch(
    x_batch: np.ndarray,
    groups: OptionBGroups,
    mean: np.ndarray,
    std: np.ndarray,
    branch_target_features: int = 0,
    feature_augmentation_mode: str = "off",
    feature_augmentation_clip: float = 8.0,
) -> dict[str, np.ndarray]:
    normalized = normalize_batch_sequence(x_batch, mean, std)
    return grouped_normalized_batch(
        normalized,
        groups,
        branch_target_features,
        feature_augmentation_mode,
        feature_augmentation_clip,
    )


def make_grouped_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    targets: Mapping[str, np.ndarray],
    groups: OptionBGroups,
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int,
    branch_target_features: int = 0,
    feature_augmentation_mode: str = "off",
    feature_augmentation_clip: float = 8.0,
    weights: Mapping[str, np.ndarray] | None = None,
    shuffle: bool = False,
) -> Any:
    class OptionBSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.tensor_indices = np.asarray(tensor_indices, dtype=np.int64)
            self.targets = {key: np.asarray(value) for key, value in targets.items()}
            self.weights = (
                None if weights is None else {key: np.asarray(value) for key, value in weights.items()}
            )
            self.order = np.arange(len(self.tensor_indices), dtype=np.int64)
            self.rng = np.random.default_rng(20260919)
            self.shuffle = bool(shuffle)
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
            x_batch = grouped_batch(
                np.asarray(x_values[rows]),
                groups,
                mean,
                std,
                int(branch_target_features),
                feature_augmentation_mode,
                float(feature_augmentation_clip),
            )
            y_batch = {key: value[local] for key, value in self.targets.items()}
            if self.weights is None:
                return x_batch, y_batch
            return x_batch, y_batch, {key: value[local] for key, value in self.weights.items()}

    return OptionBSequence()


def make_grouped_predict_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    groups: OptionBGroups,
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int,
    branch_target_features: int = 0,
    feature_augmentation_mode: str = "off",
    feature_augmentation_clip: float = 8.0,
) -> Any:
    class OptionBPredictSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.tensor_indices = np.asarray(tensor_indices, dtype=np.int64)

        def __len__(self) -> int:
            return int(np.ceil(len(self.tensor_indices) / max(int(batch_size), 1)))

        def __getitem__(self, index: int) -> dict[str, np.ndarray]:
            start = index * max(int(batch_size), 1)
            end = min(len(self.tensor_indices), start + max(int(batch_size), 1))
            rows = self.tensor_indices[start:end]
            return grouped_batch(
                np.asarray(x_values[rows]),
                groups,
                mean,
                std,
                int(branch_target_features),
                feature_augmentation_mode,
                float(feature_augmentation_clip),
            )

    return OptionBPredictSequence()


def temporal_branch(
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
    x = branches[0] if len(branches) == 1 else tf.keras.layers.Concatenate(name=f"{name}_concat")(branches)
    x = tf.keras.layers.LayerNormalization(name=f"{name}_norm")(x)
    return x


def build_option_b_model(
    tf: Any,
    window_size: int,
    groups: OptionBGroups,
    args: argparse.Namespace,
) -> Any:
    kernels = parse_int_list(args.temporal_kernels, [3, 5, 9])
    dilations = parse_int_list(args.dilations, [1, 2, 4, 8, 16, 32])
    branch_filters = max(int(args.branch_filters), 1)
    temporal_filters = max(int(args.temporal_filters), 1)

    branch_target = max(int(getattr(args, "branch_target_features", 0)), 0)
    m5_features = branch_target if branch_target > 0 else int(len(groups.m5_context))
    source_features = branch_target if branch_target > 0 else int(len(groups.source_5m))
    htf_features = branch_target if branch_target > 0 else int(len(groups.htf_context))
    m5_input = tf.keras.Input(shape=(window_size, m5_features), name="m5_context_input")
    src_input = tf.keras.Input(shape=(window_size, source_features), name="source_5m_input")
    htf_input = tf.keras.Input(shape=(window_size, htf_features), name="htf_context_input")

    m5 = temporal_branch(tf, m5_input, branch_filters, kernels, args.activation, "m5_context_branch")
    src = temporal_branch(tf, src_input, branch_filters, kernels, args.activation, "source_5m_branch")
    htf = temporal_branch(tf, htf_input, branch_filters, kernels, args.activation, "htf_context_branch")

    fusion = tf.keras.layers.Concatenate(name="option_b_late_fusion")([m5, src, htf])
    x = tf.keras.layers.Conv1D(temporal_filters, 1, padding="same", name="temporal_projection")(
        fusion
    )
    x = tf.keras.layers.LayerNormalization(name="temporal_projection_norm")(x)
    skips = []
    for block in range(max(int(args.residual_blocks), 1)):
        for dilation in dilations:
            x, skip = gated_dilated_residual_block(
                tf,
                x,
                temporal_filters,
                3,
                dilation,
                args.dropout,
                args.se_ratio,
                f"option_b_wavenet_b{block + 1}_d{dilation}",
            )
            skips.append(skip)
    x = tf.keras.layers.Add(name="skip_sum")(skips) if len(skips) > 1 else skips[0]
    x = activation_layer(tf, f"skip_sum_{args.activation}", args.activation)(x)
    x = tf.keras.layers.Conv1D(temporal_filters, 1, padding="same", name="post_skip_1x1")(x)
    x = squeeze_excitation_1d(tf, x, temporal_filters, args.se_ratio, "post_skip_se")
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
    last_state = tf.keras.layers.Cropping1D(
        cropping=(max(int(window_size) - 1, 0), 0), name="last_temporal_crop"
    )(x)
    last_state = tf.keras.layers.Reshape((temporal_filters,), name="last_temporal_state")(
        last_state
    )
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
    model = tf.keras.Model(
        inputs={
            "m5_context_input": m5_input,
            "source_5m_input": src_input,
            "htf_context_input": htf_input,
        },
        outputs=outputs,
        name="pivot_sequence_wavenet_option_b_grouped",
    )
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


def render_html(title: str, report: OptionBReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:21px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase147A Option B grouped-input sequence WaveNet. Research only.</p>
<div class="grid">
<div class="metric"><span>Validation accuracy</span><strong>{report.metrics.get('val_action_accuracy', 0.0):.3f}</strong></div>
<div class="metric"><span>Test accuracy</span><strong>{report.metrics.get('test_action_accuracy', 0.0):.3f}</strong></div>
<div class="metric"><span>Source 5M features</span><strong>{report.source_5m_feature_count}</strong></div>
<div class="metric"><span>Production</span><strong>BLOCKED</strong></div>
</div><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_log_path = (
        Path(args.batch_log_file)
        if str(args.batch_log_file).strip()
        else output_dir / "latest_batch_log.jsonl"
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
        print("  PHASE147A TRAIN OPTION B GROUPED SEQUENCE WAVENET")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        tf = require_tensorflow()
        x_all = np.load(tensor_path, mmap_mode="r")
        meta = load_meta(meta_path)
        groups = option_b_groups(meta)
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
        mean, std, nonfinite_input_values = compute_streaming_scaler_sequence(
            x_all, indices[train_idx], int(args.stream_chunk_size)
        )
        window_size = int(x_all.shape[1])
        model = build_option_b_model(tf, window_size, groups, args)
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
        train_sequence = make_grouped_sequence(
            tf,
            x_all,
            indices[train_idx],
            train_targets,
            groups,
            mean,
            std,
            int(args.batch_size),
            int(args.branch_target_features),
            args.feature_augmentation_mode,
            float(args.feature_augmentation_clip),
            sample_weights(train_targets, args.class_weight),
            shuffle=True,
        )
        validation_sequence = make_grouped_sequence(
            tf,
            x_all,
            indices[validation_idx],
            validation_targets,
            groups,
            mean,
            std,
            int(args.batch_size),
            int(args.branch_target_features),
            args.feature_augmentation_mode,
            float(args.feature_augmentation_clip),
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
                make_grouped_predict_sequence(
                    tf,
                    x_all,
                    indices[validation_idx],
                    groups,
                    mean,
                    std,
                    int(args.batch_size),
                    int(args.branch_target_features),
                    args.feature_augmentation_mode,
                    float(args.feature_augmentation_clip),
                ),
                verbose=0,
            )
        )
        test_pred = prediction_dict(
            model.predict(
                make_grouped_predict_sequence(
                    tf,
                    x_all,
                    indices[test_idx],
                    groups,
                    mean,
                    std,
                    int(args.batch_size),
                    int(args.branch_target_features),
                    args.feature_augmentation_mode,
                    float(args.feature_augmentation_clip),
                ),
                verbose=0,
            )
        )
        metrics: dict[str, float] = {}
        metrics.update(metric_block(validation_targets, validation_pred, args, "val"))
        metrics.update(metric_block(test_targets, test_pred, args, "test"))
        feature_names = [str(value) for value in np.asarray(meta.get("feature_names", [])).tolist()]
        feature_groups = [str(value) for value in np.asarray(meta.get("feature_groups", [])).tolist()]
        selected_shape = [int(len(indices)), int(x_all.shape[1]), int(x_all.shape[2])]
        branch_target = max(int(args.branch_target_features), 0)
        m5_input_features = branch_target if branch_target > 0 else len(groups.m5_context)
        source_input_features = branch_target if branch_target > 0 else len(groups.source_5m)
        htf_input_features = branch_target if branch_target > 0 else len(groups.htf_context)
        keras_shapes = {
            "m5_context_input": f"[batch, {window_size}, {m5_input_features}]",
            "source_5m_input": f"[batch, {window_size}, {source_input_features}]",
            "htf_context_input": f"[batch, {window_size}, {htf_input_features}]",
        }
        report_stub = {
            "model_id": args.model_id,
            "phase": "Phase147A",
            "role": "pivot_sequence_wavenet_option_b_grouped",
            "tensor_path": str(tensor_path),
            "meta_path": str(meta_path),
            "stored_x_shape": selected_shape,
            "keras_input_shapes": keras_shapes,
            "metrics": metrics,
            "batch_log_path": str(batch_log_path),
            "production_status": "research_only_not_approved",
        }
        payload = {
            "scaler_mean": mean.tolist(),
            "scaler_std": std.tolist(),
            "feature_names": feature_names,
            "feature_groups": feature_groups,
            "group_indices": {
                "m5_context": groups.m5_context.tolist(),
                "source_5m": groups.source_5m.tolist(),
                "htf_context": groups.htf_context.tolist(),
            },
            "thresholds": {
                "buy_threshold": args.buy_threshold,
                "sell_threshold": args.sell_threshold,
                "min_margin": args.min_margin,
                "min_buy_r": args.min_buy_r,
                "min_sell_r": args.min_sell_r,
            },
            "architecture": {
                "branch_filters": args.branch_filters,
                "branch_target_features": args.branch_target_features,
                "feature_augmentation_mode": args.feature_augmentation_mode,
                "feature_augmentation_clip": args.feature_augmentation_clip,
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
        report = OptionBReport(
            model_id=args.model_id,
            version=version,
            tensor_path=str(tensor_path),
            meta_path=str(meta_path),
            samples=len(indices),
            train_rows=len(train_idx),
            validation_rows=len(validation_idx),
            test_rows=len(test_idx),
            stored_x_shape=selected_shape,
            keras_input_shapes=keras_shapes,
            metrics=metrics,
            architecture_features=[
                "grouped_multi_input_option_b",
                "separate_generated_5m_session_branch",
                "separate_source_5m_telemetry_branch",
                "separate_htf_context_branch",
                "late_fusion",
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
            m5_context_feature_count=len(groups.m5_context),
            source_5m_feature_count=len(groups.source_5m),
            htf_feature_count=len(groups.htf_context),
            branch_target_features=int(args.branch_target_features),
            feature_augmentation_mode=str(args.feature_augmentation_mode),
            feature_augmentation_clip=float(args.feature_augmentation_clip),
            model_path=model_path,
            record_path=record_path,
            architecture_json_path=architecture_path,
            model_summary_path=summary_path,
            epoch_checkpoint_path=checkpoint_path,
            batch_log_path=str(batch_log_path),
            nonfinite_input_values=int(nonfinite_input_values),
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            production_status="BLOCKED — research Option B sequence WaveNet only",
        )
        if record_path:
            record_file = Path(record_path)
            record = json.loads(record_file.read_text(encoding="utf-8"))
            record["latest_report"] = asdict(report)
            record_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_json).write_text(
            json.dumps({"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        if architecture_path:
            Path(output_dir / "latest_architecture.json").write_text(
                Path(architecture_path).read_text(encoding="utf-8"), encoding="utf-8"
            )
        if summary_path:
            Path(output_dir / "latest_summary.txt").write_text(
                Path(summary_path).read_text(encoding="utf-8"), encoding="utf-8"
            )
        print(f"  X shape     : {report.stored_x_shape}")
        print(f"  inputs      : {report.keras_input_shapes}")
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
