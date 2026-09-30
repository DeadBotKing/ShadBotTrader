"""Phase158A: pivot-zone candidate / actionability reframe audit.

Phase157A showed the full-universe payoff target is too HOLD-dominant. This
phase audits a live-known candidate universe instead:

* top-zone rows create SELL candidate events
* bottom-zone rows create BUY candidate events

For those events it measures enrichment, payoff stability, and simple
learnability with transparent centroid baselines. Research-only.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from train_pivot_pattern_image_cnn import selected_indices, split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, ACTION_HOLD, ACTION_SELL  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_zone_candidate_reframe")
DEFAULT_CANDIDATES = "B4,B2"
SIDE_SELL = 0
SIDE_BUY = 2


@dataclass(frozen=True)
class ZoneCandidateSpec:
    candidate_id: str
    tensor_name: str


@dataclass(frozen=True)
class ZoneSplitRow:
    candidate_id: str
    split: str
    rows: int
    full_actionable_count: int
    full_actionable_rate: float
    top_zone_rows: int
    bottom_zone_rows: int
    both_zone_rows: int
    zone_event_count: int
    zone_event_rate: float
    sell_event_count: int
    buy_event_count: int
    event_win_count: int
    event_win_rate: float
    event_mean_r: float
    event_sum_r: float
    sell_win_rate: float
    buy_win_rate: float
    sell_mean_r: float
    buy_mean_r: float
    matched_target_action_rate: float


@dataclass(frozen=True)
class ZoneReframeRow:
    candidate_id: str
    tensor_name: str
    tensor_path: str
    meta_path: str
    tensor_shape: str
    summary_mode: str
    feature_summary_width: int
    sampled_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    train_zone_event_count: int
    validation_zone_event_count: int
    test_zone_event_count: int
    train_zone_event_rate: float
    validation_zone_event_rate: float
    test_zone_event_rate: float
    train_event_win_rate: float
    validation_event_win_rate: float
    test_event_win_rate: float
    train_event_mean_r: float
    validation_event_mean_r: float
    test_event_mean_r: float
    event_mean_r_sign_flip: int
    validation_sell_mean_r: float
    validation_buy_mean_r: float
    test_sell_mean_r: float
    test_buy_mean_r: float
    validation_best_side: str
    test_best_side: str
    side_preference_stable_gate: int
    event_validation_base_rate: float
    event_test_base_rate: float
    event_validation_ap: float
    event_test_ap: float
    event_validation_ap_lift: float
    event_test_ap_lift: float
    event_validation_accuracy: float
    event_test_accuracy: float
    event_validation_balanced_accuracy: float
    event_test_balanced_accuracy: float
    event_validation_f1: float
    event_test_f1: float
    enrichment_gate: int
    event_learnability_gate: int
    candidate_reframe_gate: int
    warnings: str


@dataclass(frozen=True)
class ZoneReframeReport:
    symbol: str
    timeframe: str
    candidates: list[dict[str, object]]
    completed_candidates: int
    reframe_ready_candidates: int
    best_candidate_id: str
    best_candidate_reason: str
    rows: list[dict[str, object]]
    split_rows: list[dict[str, object]]
    output_json: str
    output_html: str
    output_candidates_csv: str
    output_splits_csv: str
    production_status: str


class CentroidClassifier:
    def __init__(self, classes: Sequence[int]) -> None:
        self.classes = np.asarray(list(classes), dtype=np.int64)
        self.centroids: np.ndarray | None = None
        self.priors: np.ndarray | None = None

    def fit(self, x_values: np.ndarray, y_values: np.ndarray) -> "CentroidClassifier":
        x = np.asarray(x_values, dtype=np.float32)
        y = np.asarray(y_values, dtype=np.int64)
        global_centroid = x.mean(axis=0) if len(x) else np.zeros(x.shape[1], dtype=np.float32)
        centroids: list[np.ndarray] = []
        priors: list[float] = []
        for cls in self.classes:
            mask = y == int(cls)
            if np.any(mask):
                centroids.append(x[mask].mean(axis=0))
                priors.append(float(np.mean(mask)))
            else:
                centroids.append(global_centroid)
                priors.append(1e-6)
        self.centroids = np.vstack(centroids).astype(np.float32)
        priors_array = np.asarray(priors, dtype=np.float64)
        self.priors = priors_array / max(float(priors_array.sum()), 1e-12)
        return self

    def predict_proba(self, x_values: np.ndarray) -> np.ndarray:
        if self.centroids is None or self.priors is None:
            raise RuntimeError("CentroidClassifier must be fitted first")
        x = np.asarray(x_values, dtype=np.float32)
        distances = np.sqrt(((x[:, None, :] - self.centroids[None, :, :]) ** 2).mean(axis=2))
        logits = -distances + np.log(np.maximum(self.priors, 1e-9))[None, :]
        logits -= logits.max(axis=1, keepdims=True)
        raw = np.exp(logits)
        return raw / raw.sum(axis=1, keepdims=True)


def safe_slug(text: str) -> str:
    cleaned = []
    for character in str(text).strip().lower():
        if character.isalnum():
            cleaned.append(character)
        elif character in {"-", "_", " ", "."}:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "candidate"


def parse_candidates(text: str) -> list[ZoneCandidateSpec]:
    candidates: list[ZoneCandidateSpec] = []
    for raw in str(text or "").replace(";", ",").split(","):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) == 1:
            candidate_id = parts[0].upper()
            candidates.append(
                ZoneCandidateSpec(
                    candidate_id=candidate_id,
                    tensor_name=f"pivot_payoff_sequence_tensor_{safe_slug(candidate_id)}_latest",
                )
            )
        elif len(parts) == 2:
            candidates.append(ZoneCandidateSpec(candidate_id=parts[0].upper(), tensor_name=parts[1]))
        else:
            raise RuntimeError(f"candidate must be ID or ID:tensor_name; got {item!r}")
    if not candidates:
        raise RuntimeError("At least one candidate is required")
    return candidates


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit live-known pivot-zone candidate universe for payoff targets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--summary-mode", choices=("last", "basic"), default="basic")
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--min-validation-events", type=int, default=100)
    parser.add_argument("--min-test-events", type=int, default=100)
    parser.add_argument("--min-validation-mean-r", type=float, default=0.0)
    parser.add_argument("--min-test-mean-r", type=float, default=0.0)
    parser.add_argument("--min-event-ap-lift", type=float, default=0.03)
    parser.add_argument("--min-event-balanced-accuracy", type=float, default=0.53)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase158A pivot-zone candidate reframe audit")
    return parser.parse_args(argv)


def candidate_paths(args: argparse.Namespace, candidate: ZoneCandidateSpec) -> tuple[Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.timeframe.upper()
    return root / f"{candidate.tensor_name}.npy", root / f"{candidate.tensor_name}_meta.npz"


def load_meta(path: Path) -> dict[str, object]:
    if not path.exists():
        raise RuntimeError(f"Meta file not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def summarize_tensor_windows(x_values: np.ndarray, rows: Sequence[int], mode: str, chunk_size: int) -> np.ndarray:
    selected = np.asarray(rows, dtype=np.int64)
    chunks: list[np.ndarray] = []
    step = max(int(chunk_size), 1)
    for start in range(0, len(selected), step):
        batch_rows = selected[start : start + step]
        batch = np.asarray(x_values[batch_rows], dtype=np.float32)
        batch = np.nan_to_num(batch, nan=0.0, posinf=0.0, neginf=0.0)
        last = batch[:, -1, :]
        if mode == "last":
            chunks.append(last.astype(np.float32))
        else:
            chunks.append(
                np.concatenate([last, batch.mean(axis=1), batch.std(axis=1)], axis=1).astype(
                    np.float32
                )
            )
    return np.vstack(chunks) if chunks else np.zeros((0, 0), dtype=np.float32)


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.float32).reshape(-1)
    s = np.asarray(scores, dtype=np.float32).reshape(-1)
    positives = float(np.sum(y >= 0.5))
    if positives <= 0:
        return 0.0
    order = np.argsort(-s)
    sorted_y = y[order]
    cumulative = np.cumsum(sorted_y >= 0.5)
    ranks = np.arange(1, len(sorted_y) + 1, dtype=np.float32)
    precision = cumulative / ranks
    return float(np.sum(precision[sorted_y >= 0.5]) / positives)


def binary_metrics(y_true: np.ndarray, positive_scores: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    y = np.asarray(y_true, dtype=np.int64).reshape(-1)
    scores = np.asarray(positive_scores, dtype=np.float32).reshape(-1)
    pred = (scores >= float(threshold)).astype(np.int64)
    tp = int(np.sum((pred == 1) & (y == 1)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    return {
        "accuracy": float((tp + tn) / max(len(y), 1)),
        "balanced_accuracy": float((recall + specificity) / 2.0),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
        "ap": average_precision(y, scores),
    }


def probability_for_class(probabilities: np.ndarray, classes: Sequence[int], target_class: int) -> np.ndarray:
    class_array = [int(value) for value in classes]
    if target_class not in class_array:
        return np.zeros(int(probabilities.shape[0]), dtype=np.float32)
    return probabilities[:, class_array.index(target_class)].astype(np.float32)


def sign(value: float, eps: float = 1e-9) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def sign_flip(train_value: float, validation_value: float, test_value: float) -> int:
    train_sign = sign(train_value)
    validation_sign = sign(validation_value)
    test_sign = sign(test_value)
    return int(train_sign != 0 and validation_sign == train_sign and test_sign not in {0, train_sign})


def normalize_events(train_x: np.ndarray, *arrays: np.ndarray) -> tuple[np.ndarray, ...]:
    if len(train_x) == 0:
        return tuple(arrays)
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std = np.where((~np.isfinite(std)) | (std < 1e-6), 1.0, std)
    return tuple(
        np.nan_to_num((array - mean) / std, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        for array in arrays
    )


def build_zone_events(
    split_rows: Sequence[int],
    x_summary: np.ndarray,
    action: np.ndarray,
    top_zone: np.ndarray,
    bottom_zone: np.ndarray,
    buy_r: np.ndarray,
    sell_r: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    sides: list[int] = []
    scores: list[float] = []
    wins: list[int] = []
    matched: list[int] = []
    for row in np.asarray(split_rows, dtype=np.int64):
        base = x_summary[int(row)]
        if float(top_zone[int(row)]) >= 0.5:
            features.append(np.concatenate([base, np.asarray([-1.0], dtype=np.float32)]))
            sides.append(SIDE_SELL)
            score = float(sell_r[int(row)])
            scores.append(score)
            wins.append(int(score > 0.0))
            matched.append(int(action[int(row)] == ACTION_SELL))
        if float(bottom_zone[int(row)]) >= 0.5:
            features.append(np.concatenate([base, np.asarray([1.0], dtype=np.float32)]))
            sides.append(SIDE_BUY)
            score = float(buy_r[int(row)])
            scores.append(score)
            wins.append(int(score > 0.0))
            matched.append(int(action[int(row)] == ACTION_BUY))
    if not features:
        width = int(x_summary.shape[1]) + 1 if x_summary.ndim == 2 else 1
        return (
            np.zeros((0, width), dtype=np.float32),
            np.asarray([], dtype=np.int64),
            np.asarray([], dtype=np.float32),
            np.asarray([], dtype=np.int64),
            np.asarray([], dtype=np.int64),
        )
    return (
        np.vstack(features).astype(np.float32),
        np.asarray(sides, dtype=np.int64),
        np.asarray(scores, dtype=np.float32),
        np.asarray(wins, dtype=np.int64),
        np.asarray(matched, dtype=np.int64),
    )


def zone_split_row(
    candidate_id: str,
    split: str,
    split_idx: Sequence[int],
    action: np.ndarray,
    top_zone: np.ndarray,
    bottom_zone: np.ndarray,
    sides: np.ndarray,
    scores: np.ndarray,
    wins: np.ndarray,
    matched: np.ndarray,
) -> ZoneSplitRow:
    idx = np.asarray(split_idx, dtype=np.int64)
    rows = int(len(idx))
    split_action = action[idx]
    top_rows = int(np.sum(top_zone[idx] >= 0.5)) if rows else 0
    bottom_rows = int(np.sum(bottom_zone[idx] >= 0.5)) if rows else 0
    both_rows = int(np.sum((top_zone[idx] >= 0.5) & (bottom_zone[idx] >= 0.5))) if rows else 0
    sell_mask = sides == SIDE_SELL
    buy_mask = sides == SIDE_BUY
    return ZoneSplitRow(
        candidate_id=candidate_id,
        split=split,
        rows=rows,
        full_actionable_count=int(np.sum(split_action != ACTION_HOLD)),
        full_actionable_rate=float(np.mean(split_action != ACTION_HOLD)) if rows else 0.0,
        top_zone_rows=top_rows,
        bottom_zone_rows=bottom_rows,
        both_zone_rows=both_rows,
        zone_event_count=int(len(scores)),
        zone_event_rate=float(len(scores) / rows) if rows else 0.0,
        sell_event_count=int(np.sum(sell_mask)),
        buy_event_count=int(np.sum(buy_mask)),
        event_win_count=int(np.sum(wins)),
        event_win_rate=float(np.mean(wins)) if len(wins) else 0.0,
        event_mean_r=float(np.mean(scores)) if len(scores) else 0.0,
        event_sum_r=float(np.sum(scores)) if len(scores) else 0.0,
        sell_win_rate=float(np.mean(wins[sell_mask])) if np.any(sell_mask) else 0.0,
        buy_win_rate=float(np.mean(wins[buy_mask])) if np.any(buy_mask) else 0.0,
        sell_mean_r=float(np.mean(scores[sell_mask])) if np.any(sell_mask) else 0.0,
        buy_mean_r=float(np.mean(scores[buy_mask])) if np.any(buy_mask) else 0.0,
        matched_target_action_rate=float(np.mean(matched)) if len(matched) else 0.0,
    )


def best_side(sell_mean: float, buy_mean: float) -> str:
    if buy_mean > sell_mean:
        return "BUY"
    if sell_mean > buy_mean:
        return "SELL"
    return "TIE"


def evaluate_candidate(args: argparse.Namespace, candidate: ZoneCandidateSpec) -> tuple[ZoneReframeRow, list[ZoneSplitRow]]:
    tensor_path, meta_path = candidate_paths(args, candidate)
    if not tensor_path.exists():
        raise RuntimeError(f"Tensor not found for {candidate.candidate_id}: {tensor_path}")
    x_all = np.load(tensor_path, mmap_mode="r")
    meta = load_meta(meta_path)
    selected = selected_indices(len(x_all), int(args.max_samples))
    train_idx, validation_idx, test_idx = split_indices(
        len(selected), float(args.train_frac), float(args.val_frac), int(args.purge_gap)
    )
    x_summary = summarize_tensor_windows(x_all, selected, str(args.summary_mode), int(args.chunk_size))
    action = np.asarray(meta["target_action"], dtype=np.int64)[selected]
    top_zone = np.asarray(meta["target_top_zone"], dtype=np.float32)[selected].reshape(-1)
    bottom_zone = np.asarray(meta["target_bottom_zone"], dtype=np.float32)[selected].reshape(-1)
    buy_r = np.asarray(meta["target_buy_trade_r"], dtype=np.float32)[selected].reshape(-1)
    sell_r = np.asarray(meta["target_sell_trade_r"], dtype=np.float32)[selected].reshape(-1)

    train_events = build_zone_events(train_idx, x_summary, action, top_zone, bottom_zone, buy_r, sell_r)
    val_events = build_zone_events(validation_idx, x_summary, action, top_zone, bottom_zone, buy_r, sell_r)
    test_events = build_zone_events(test_idx, x_summary, action, top_zone, bottom_zone, buy_r, sell_r)
    train_x, _, train_score, train_win, train_matched = train_events
    val_x, _, val_score, val_win, val_matched = val_events
    test_x, _, test_score, test_win, test_matched = test_events
    train_split = zone_split_row(candidate.candidate_id, "train", train_idx, action, top_zone, bottom_zone, train_events[1], train_score, train_win, train_matched)
    val_split = zone_split_row(candidate.candidate_id, "validation", validation_idx, action, top_zone, bottom_zone, val_events[1], val_score, val_win, val_matched)
    test_split = zone_split_row(candidate.candidate_id, "test", test_idx, action, top_zone, bottom_zone, test_events[1], test_score, test_win, test_matched)
    train_x_n, val_x_n, test_x_n = normalize_events(train_x, train_x, val_x, test_x)

    event_val_metrics = {"accuracy": 0.0, "balanced_accuracy": 0.0, "f1": 0.0, "ap": 0.0}
    event_test_metrics = {"accuracy": 0.0, "balanced_accuracy": 0.0, "f1": 0.0, "ap": 0.0}
    warnings: list[str] = []
    if len(train_win) and len(np.unique(train_win)) >= 2:
        event_model = CentroidClassifier([0, 1]).fit(train_x_n, train_win)
        if len(val_win):
            val_prob = event_model.predict_proba(val_x_n)
            event_val_metrics = binary_metrics(val_win, probability_for_class(val_prob, [0, 1], 1))
        if len(test_win):
            test_prob = event_model.predict_proba(test_x_n)
            event_test_metrics = binary_metrics(test_win, probability_for_class(test_prob, [0, 1], 1))
    else:
        warnings.append("event win classifier skipped: train zone events are one-sided or empty")

    mean_flip = sign_flip(train_split.event_mean_r, val_split.event_mean_r, test_split.event_mean_r)
    val_best_side = best_side(val_split.sell_mean_r, val_split.buy_mean_r)
    test_best_side = best_side(test_split.sell_mean_r, test_split.buy_mean_r)
    side_stable = int(val_best_side == test_best_side and val_best_side != "TIE")
    enrichment_gate = int(
        val_split.zone_event_count >= int(args.min_validation_events)
        and test_split.zone_event_count >= int(args.min_test_events)
        and val_split.event_mean_r >= float(args.min_validation_mean_r)
        and test_split.event_mean_r >= float(args.min_test_mean_r)
        and not mean_flip
    )
    event_gate = int(
        event_val_metrics["ap"] - val_split.event_win_rate >= float(args.min_event_ap_lift)
        and event_val_metrics["balanced_accuracy"] >= float(args.min_event_balanced_accuracy)
    )
    if not enrichment_gate:
        warnings.append("zone candidate enrichment/stability gate failed")
    if not event_gate:
        warnings.append("candidate event win learnability gate failed")
    if not side_stable:
        warnings.append("side preference is not stable between validation and test")
    row = ZoneReframeRow(
        candidate_id=candidate.candidate_id,
        tensor_name=candidate.tensor_name,
        tensor_path=str(tensor_path),
        meta_path=str(meta_path),
        tensor_shape=json.dumps([int(value) for value in x_all.shape]),
        summary_mode=str(args.summary_mode),
        feature_summary_width=int(x_summary.shape[1]) if x_summary.ndim == 2 else 0,
        sampled_rows=int(len(selected)),
        train_rows=int(len(train_idx)),
        validation_rows=int(len(validation_idx)),
        test_rows=int(len(test_idx)),
        train_zone_event_count=int(train_split.zone_event_count),
        validation_zone_event_count=int(val_split.zone_event_count),
        test_zone_event_count=int(test_split.zone_event_count),
        train_zone_event_rate=float(train_split.zone_event_rate),
        validation_zone_event_rate=float(val_split.zone_event_rate),
        test_zone_event_rate=float(test_split.zone_event_rate),
        train_event_win_rate=float(train_split.event_win_rate),
        validation_event_win_rate=float(val_split.event_win_rate),
        test_event_win_rate=float(test_split.event_win_rate),
        train_event_mean_r=float(train_split.event_mean_r),
        validation_event_mean_r=float(val_split.event_mean_r),
        test_event_mean_r=float(test_split.event_mean_r),
        event_mean_r_sign_flip=int(mean_flip),
        validation_sell_mean_r=float(val_split.sell_mean_r),
        validation_buy_mean_r=float(val_split.buy_mean_r),
        test_sell_mean_r=float(test_split.sell_mean_r),
        test_buy_mean_r=float(test_split.buy_mean_r),
        validation_best_side=val_best_side,
        test_best_side=test_best_side,
        side_preference_stable_gate=side_stable,
        event_validation_base_rate=float(val_split.event_win_rate),
        event_test_base_rate=float(test_split.event_win_rate),
        event_validation_ap=float(event_val_metrics["ap"]),
        event_test_ap=float(event_test_metrics["ap"]),
        event_validation_ap_lift=float(event_val_metrics["ap"] - val_split.event_win_rate),
        event_test_ap_lift=float(event_test_metrics["ap"] - test_split.event_win_rate),
        event_validation_accuracy=float(event_val_metrics["accuracy"]),
        event_test_accuracy=float(event_test_metrics["accuracy"]),
        event_validation_balanced_accuracy=float(event_val_metrics["balanced_accuracy"]),
        event_test_balanced_accuracy=float(event_test_metrics["balanced_accuracy"]),
        event_validation_f1=float(event_val_metrics["f1"]),
        event_test_f1=float(event_test_metrics["f1"]),
        enrichment_gate=enrichment_gate,
        event_learnability_gate=event_gate,
        candidate_reframe_gate=int(enrichment_gate and event_gate and side_stable),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )
    return row, [train_split, val_split, test_split]


def choose_best(rows: Sequence[ZoneReframeRow]) -> tuple[str, str]:
    ready = [row for row in rows if row.candidate_reframe_gate]
    if ready:
        ranked = sorted(
            ready,
            key=lambda row: (
                row.validation_event_mean_r,
                row.event_validation_ap_lift,
                row.event_validation_balanced_accuracy,
            ),
            reverse=True,
        )
        return ranked[0].candidate_id, "candidate passed zone enrichment, event learnability and side stability gates"
    ranked = sorted(
        rows,
        key=lambda row: (
            row.validation_event_mean_r,
            row.event_validation_ap_lift,
            row.event_validation_balanced_accuracy,
        ),
        reverse=True,
    )
    if ranked:
        return ranked[0].candidate_id, "no gate pass; best diagnostic score only"
    return "", "no candidates evaluated"


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: ZoneReframeReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{int(row['validation_zone_event_count'])}</td>"
        f"<td>{int(row['test_zone_event_count'])}</td>"
        f"<td>{float(row['validation_event_win_rate']):.3f}</td>"
        f"<td>{float(row['test_event_win_rate']):.3f}</td>"
        f"<td>{float(row['validation_event_mean_r']):.4f}</td>"
        f"<td>{float(row['test_event_mean_r']):.4f}</td>"
        f"<td>{float(row['event_validation_ap_lift']):.3f}</td>"
        f"<td>{html.escape(str(row['validation_best_side']))}</td>"
        f"<td>{html.escape(str(row['test_best_side']))}</td>"
        f"<td>{int(row['candidate_reframe_gate'])}</td></tr>"
        for row in report.rows
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1380px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:13px; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase158A pivot-zone candidate reframe audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Rows</h2><table><thead><tr><th>ID</th><th>Val events</th><th>Test events</th><th>Val WR</th><th>Test WR</th><th>Val mean R</th><th>Test mean R</th><th>Val AP lift</th><th>Val best side</th><th>Test best side</th><th>Gate</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE158A PIVOT-ZONE CANDIDATE / ACTIONABILITY REFRAME AUDIT")
        print("=" * 74)
        candidates = parse_candidates(args.candidates)
        rows: list[ZoneReframeRow] = []
        splits: list[ZoneSplitRow] = []
        for candidate in candidates:
            print(f"  [candidate] {candidate.candidate_id} tensor={candidate.tensor_name}", flush=True)
            row, split_rows = evaluate_candidate(args, candidate)
            rows.append(row)
            splits.extend(split_rows)
        best_id, best_reason = choose_best(rows)
        row_dicts = [asdict(row) for row in rows]
        split_dicts = [asdict(row) for row in splits]
        candidate_csv = output_dir / "latest_candidates.csv"
        split_csv = output_dir / "latest_splits.csv"
        write_csv(candidate_csv, row_dicts)
        write_csv(split_csv, split_dicts)
        report = ZoneReframeReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            candidates=[asdict(candidate) for candidate in candidates],
            completed_candidates=len(rows),
            reframe_ready_candidates=sum(int(row.candidate_reframe_gate) for row in rows),
            best_candidate_id=best_id,
            best_candidate_reason=best_reason,
            rows=row_dicts,
            split_rows=split_dicts,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidates_csv=str(candidate_csv),
            output_splits_csv=str(split_csv),
            production_status="BLOCKED — Phase158A pivot-zone candidate audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase158A pivot-zone reframe audit complete")
        print(f"  candidates      : {report.completed_candidates}")
        print(f"  reframe ready   : {report.reframe_ready_candidates}")
        print(f"  best diagnostic : {report.best_candidate_id or 'none'}")
        print(f"  output          : {report.output_json}")
        print(f"  elapsed         : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
