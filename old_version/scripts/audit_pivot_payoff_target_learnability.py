"""Phase157A: payoff target learnability / imbalance-control diagnostic.

This phase does not train a deep model and does not approve a strategy. It asks
whether the payoff targets that passed Phase154A (B4/B2) are learnable at all
from the existing sequence tensor features under simple, transparent baselines:

* Full three-class SELL/HOLD/BUY centroid classifier.
* Binary actionability classifier: ACTIONABLE vs HOLD.
* Candidate-only side classifier: SELL vs BUY on target_action != HOLD rows.

If these simple diagnostics cannot see actionable/side signal, another large
WaveNet training run is not justified. If they can, the next work is neural
loss/sampling redesign rather than blind architecture scaling.
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
from typing import Any, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from train_pivot_pattern_image_cnn import selected_indices, split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, ACTION_HOLD, ACTION_SELL  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_payoff_target_learnability")
DEFAULT_CANDIDATES = "B4,B2"
ACTION_NAMES = {ACTION_SELL: "SELL", ACTION_HOLD: "HOLD", ACTION_BUY: "BUY"}


@dataclass(frozen=True)
class LearnabilityCandidate:
    candidate_id: str
    tensor_name: str


@dataclass(frozen=True)
class SplitClassRow:
    candidate_id: str
    split: str
    rows: int
    sell_count: int
    hold_count: int
    buy_count: int
    sell_rate: float
    hold_rate: float
    buy_rate: float
    actionable_count: int
    actionable_rate: float
    majority_class: str
    majority_rate: float


@dataclass(frozen=True)
class LearnabilityRow:
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
    train_actionable_rate: float
    validation_actionable_rate: float
    test_actionable_rate: float
    always_hold_validation_accuracy: float
    always_hold_test_accuracy: float
    full3_validation_accuracy: float
    full3_test_accuracy: float
    full3_validation_balanced_accuracy: float
    full3_test_balanced_accuracy: float
    binary_validation_base_rate: float
    binary_test_base_rate: float
    binary_validation_ap: float
    binary_test_ap: float
    binary_validation_ap_lift: float
    binary_test_ap_lift: float
    binary_validation_accuracy: float
    binary_test_accuracy: float
    binary_validation_balanced_accuracy: float
    binary_test_balanced_accuracy: float
    binary_validation_f1: float
    binary_test_f1: float
    side_train_rows: int
    side_validation_rows: int
    side_test_rows: int
    side_validation_accuracy: float
    side_test_accuracy: float
    side_validation_balanced_accuracy: float
    side_test_balanced_accuracy: float
    side_validation_buy_ap: float
    side_test_buy_ap: float
    actionability_learnability_gate: int
    side_learnability_gate: int
    candidate_learnability_gate: int
    warnings: str


@dataclass(frozen=True)
class LearnabilityReport:
    symbol: str
    timeframe: str
    candidates: list[dict[str, Any]]
    completed_candidates: int
    learnable_candidates: int
    best_candidate_id: str
    best_candidate_reason: str
    rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidates_csv: str
    output_splits_csv: str
    production_status: str


class CentroidClassifier:
    """Dependency-free nearest-centroid classifier with softmax distance scores."""

    def __init__(self, classes: Sequence[int]) -> None:
        self.classes = np.asarray(list(classes), dtype=np.int64)
        self.centroids: np.ndarray | None = None
        self.priors: np.ndarray | None = None
        self.fitted_classes: np.ndarray | None = None

    def fit(self, x_values: np.ndarray, y_values: np.ndarray) -> "CentroidClassifier":
        x = np.asarray(x_values, dtype=np.float32)
        y = np.asarray(y_values, dtype=np.int64)
        centroids: list[np.ndarray] = []
        priors: list[float] = []
        fitted: list[int] = []
        global_centroid = x.mean(axis=0) if len(x) else np.zeros(x.shape[1], dtype=np.float32)
        for cls in self.classes:
            mask = y == int(cls)
            if np.any(mask):
                centroids.append(x[mask].mean(axis=0))
                priors.append(float(np.mean(mask)))
                fitted.append(int(cls))
            else:
                centroids.append(global_centroid)
                priors.append(1e-6)
        priors_array = np.asarray(priors, dtype=np.float64)
        self.centroids = np.vstack(centroids).astype(np.float32)
        self.priors = priors_array / max(float(priors_array.sum()), 1e-12)
        self.fitted_classes = np.asarray(fitted, dtype=np.int64)
        return self

    def predict_proba(self, x_values: np.ndarray) -> np.ndarray:
        if self.centroids is None or self.priors is None:
            raise RuntimeError("CentroidClassifier must be fitted before predict_proba")
        x = np.asarray(x_values, dtype=np.float32)
        distances = np.sqrt(((x[:, None, :] - self.centroids[None, :, :]) ** 2).mean(axis=2))
        logits = -distances + np.log(np.maximum(self.priors, 1e-9))[None, :]
        logits -= logits.max(axis=1, keepdims=True)
        raw = np.exp(logits)
        return raw / raw.sum(axis=1, keepdims=True)

    def predict(self, x_values: np.ndarray) -> np.ndarray:
        probabilities = self.predict_proba(x_values)
        return self.classes[probabilities.argmax(axis=1)]


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


def parse_candidates(text: str) -> list[LearnabilityCandidate]:
    candidates: list[LearnabilityCandidate] = []
    for raw in str(text or "").replace(";", ",").split(","):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) == 1:
            candidate_id = parts[0].upper()
            candidates.append(
                LearnabilityCandidate(
                    candidate_id=candidate_id,
                    tensor_name=f"pivot_payoff_sequence_tensor_{safe_slug(candidate_id)}_latest",
                )
            )
        elif len(parts) == 2:
            candidates.append(LearnabilityCandidate(candidate_id=parts[0].upper(), tensor_name=parts[1]))
        else:
            raise RuntimeError(f"candidate must be ID or ID:tensor_name; got {item!r}")
    if not candidates:
        raise RuntimeError("At least one learnability candidate is required")
    return candidates


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit payoff target learnability and imbalance before more deep training.",
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
    parser.add_argument("--min-action-ap-lift", type=float, default=0.05)
    parser.add_argument("--min-binary-balanced-accuracy", type=float, default=0.55)
    parser.add_argument("--min-side-balanced-accuracy", type=float, default=0.55)
    parser.add_argument("--min-candidate-train-rows", type=int, default=200)
    parser.add_argument("--min-candidate-validation-rows", type=int, default=30)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase157A payoff target learnability diagnostic")
    return parser.parse_args(argv)


def candidate_paths(args: argparse.Namespace, candidate: LearnabilityCandidate) -> tuple[Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.timeframe.upper()
    return root / f"{candidate.tensor_name}.npy", root / f"{candidate.tensor_name}_meta.npz"


def load_meta(path: Path) -> dict[str, Any]:
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
                np.concatenate(
                    [last, batch.mean(axis=1), batch.std(axis=1)], axis=1
                ).astype(np.float32)
            )
    return np.vstack(chunks) if chunks else np.zeros((0, 0), dtype=np.float32)


def train_normalize(x_values: np.ndarray, train_idx: Sequence[int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train = x_values[np.asarray(train_idx, dtype=np.int64)]
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std = np.where((~np.isfinite(std)) | (std < 1e-6), 1.0, std)
    normalized = (x_values - mean) / std
    return np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32), mean, std


def class_distribution(candidate_id: str, split: str, y_values: np.ndarray) -> SplitClassRow:
    y = np.asarray(y_values, dtype=np.int64)
    rows = len(y)
    sell_count = int(np.sum(y == ACTION_SELL))
    hold_count = int(np.sum(y == ACTION_HOLD))
    buy_count = int(np.sum(y == ACTION_BUY))
    counts = {"SELL": sell_count, "HOLD": hold_count, "BUY": buy_count}
    majority_class = max(counts, key=counts.get) if rows else ""
    majority_count = counts.get(majority_class, 0)
    return SplitClassRow(
        candidate_id=candidate_id,
        split=split,
        rows=rows,
        sell_count=sell_count,
        hold_count=hold_count,
        buy_count=buy_count,
        sell_rate=float(sell_count / rows) if rows else 0.0,
        hold_rate=float(hold_count / rows) if rows else 0.0,
        buy_rate=float(buy_count / rows) if rows else 0.0,
        actionable_count=int(sell_count + buy_count),
        actionable_rate=float((sell_count + buy_count) / rows) if rows else 0.0,
        majority_class=majority_class,
        majority_rate=float(majority_count / rows) if rows else 0.0,
    )


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


def multiclass_metrics(y_true: np.ndarray, probabilities: np.ndarray, classes: Sequence[int]) -> dict[str, float]:
    y = np.asarray(y_true, dtype=np.int64).reshape(-1)
    class_array = np.asarray(list(classes), dtype=np.int64)
    pred = class_array[np.asarray(probabilities).argmax(axis=1)] if len(y) else np.asarray([], dtype=np.int64)
    recalls: list[float] = []
    for cls in class_array:
        mask = y == int(cls)
        if np.any(mask):
            recalls.append(float(np.mean(pred[mask] == int(cls))))
    return {
        "accuracy": float(np.mean(pred == y)) if len(y) else 0.0,
        "balanced_accuracy": float(np.mean(recalls)) if recalls else 0.0,
    }


def probability_for_class(probabilities: np.ndarray, classes: Sequence[int], target_class: int) -> np.ndarray:
    class_array = list(int(value) for value in classes)
    if target_class not in class_array:
        return np.zeros(int(probabilities.shape[0]), dtype=np.float32)
    return probabilities[:, class_array.index(target_class)].astype(np.float32)


def evaluate_candidate(args: argparse.Namespace, candidate: LearnabilityCandidate) -> tuple[LearnabilityRow, list[SplitClassRow]]:
    tensor_path, meta_path = candidate_paths(args, candidate)
    if not tensor_path.exists():
        raise RuntimeError(f"Tensor not found for {candidate.candidate_id}: {tensor_path}")
    x_all = np.load(tensor_path, mmap_mode="r")
    meta = load_meta(meta_path)
    y_all = np.asarray(meta["target_action"], dtype=np.int64)
    selected = selected_indices(len(x_all), int(args.max_samples))
    train_idx, validation_idx, test_idx = split_indices(
        len(selected), float(args.train_frac), float(args.val_frac), int(args.purge_gap)
    )
    summary = summarize_tensor_windows(x_all, selected, str(args.summary_mode), int(args.chunk_size))
    x_norm, _, _ = train_normalize(summary, train_idx)
    y = y_all[selected]
    train_y = y[train_idx]
    validation_y = y[validation_idx]
    test_y = y[test_idx]
    split_rows = [
        class_distribution(candidate.candidate_id, "train", train_y),
        class_distribution(candidate.candidate_id, "validation", validation_y),
        class_distribution(candidate.candidate_id, "test", test_y),
    ]
    train_dist, validation_dist, test_dist = split_rows

    full_classifier = CentroidClassifier([ACTION_SELL, ACTION_HOLD, ACTION_BUY]).fit(
        x_norm[train_idx], train_y
    )
    val_full_prob = full_classifier.predict_proba(x_norm[validation_idx])
    test_full_prob = full_classifier.predict_proba(x_norm[test_idx])
    val_full = multiclass_metrics(validation_y, val_full_prob, [ACTION_SELL, ACTION_HOLD, ACTION_BUY])
    test_full = multiclass_metrics(test_y, test_full_prob, [ACTION_SELL, ACTION_HOLD, ACTION_BUY])

    train_binary = (train_y != ACTION_HOLD).astype(np.int64)
    validation_binary = (validation_y != ACTION_HOLD).astype(np.int64)
    test_binary = (test_y != ACTION_HOLD).astype(np.int64)
    binary_classifier = CentroidClassifier([0, 1]).fit(x_norm[train_idx], train_binary)
    val_binary_prob = binary_classifier.predict_proba(x_norm[validation_idx])
    test_binary_prob = binary_classifier.predict_proba(x_norm[test_idx])
    val_action_scores = probability_for_class(val_binary_prob, [0, 1], 1)
    test_action_scores = probability_for_class(test_binary_prob, [0, 1], 1)
    val_binary_metrics = binary_metrics(validation_binary, val_action_scores)
    test_binary_metrics = binary_metrics(test_binary, test_action_scores)

    train_candidate_mask = train_y != ACTION_HOLD
    validation_candidate_mask = validation_y != ACTION_HOLD
    test_candidate_mask = test_y != ACTION_HOLD
    side_train_rows = int(np.sum(train_candidate_mask))
    side_validation_rows = int(np.sum(validation_candidate_mask))
    side_test_rows = int(np.sum(test_candidate_mask))
    side_warning = ""
    side_val_metrics = {"accuracy": 0.0, "balanced_accuracy": 0.0, "ap": 0.0}
    side_test_metrics = {"accuracy": 0.0, "balanced_accuracy": 0.0, "ap": 0.0}
    if side_train_rows >= int(args.min_candidate_train_rows) and len(np.unique(train_y[train_candidate_mask])) >= 2:
        side_train_y = (train_y[train_candidate_mask] == ACTION_BUY).astype(np.int64)
        side_classifier = CentroidClassifier([0, 1]).fit(x_norm[train_idx][train_candidate_mask], side_train_y)
        if side_validation_rows:
            side_val_y = (validation_y[validation_candidate_mask] == ACTION_BUY).astype(np.int64)
            side_val_prob = side_classifier.predict_proba(x_norm[validation_idx][validation_candidate_mask])
            side_val_scores = probability_for_class(side_val_prob, [0, 1], 1)
            side_val_metrics = binary_metrics(side_val_y, side_val_scores)
        if side_test_rows:
            side_test_y = (test_y[test_candidate_mask] == ACTION_BUY).astype(np.int64)
            side_test_prob = side_classifier.predict_proba(x_norm[test_idx][test_candidate_mask])
            side_test_scores = probability_for_class(side_test_prob, [0, 1], 1)
            side_test_metrics = binary_metrics(side_test_y, side_test_scores)
    else:
        side_warning = "candidate-only side train rows too small or one-sided"

    binary_base_val = float(np.mean(validation_binary)) if len(validation_binary) else 0.0
    binary_base_test = float(np.mean(test_binary)) if len(test_binary) else 0.0
    action_gate = int(
        val_binary_metrics["ap"] - binary_base_val >= float(args.min_action_ap_lift)
        and val_binary_metrics["balanced_accuracy"] >= float(args.min_binary_balanced_accuracy)
    )
    side_gate = int(
        side_train_rows >= int(args.min_candidate_train_rows)
        and side_validation_rows >= int(args.min_candidate_validation_rows)
        and side_val_metrics["balanced_accuracy"] >= float(args.min_side_balanced_accuracy)
    )
    warnings: list[str] = []
    if side_warning:
        warnings.append(side_warning)
    if not action_gate:
        warnings.append("binary actionability learnability gate failed")
    if not side_gate:
        warnings.append("candidate-only side learnability gate failed")
    row = LearnabilityRow(
        candidate_id=candidate.candidate_id,
        tensor_name=candidate.tensor_name,
        tensor_path=str(tensor_path),
        meta_path=str(meta_path),
        tensor_shape=json.dumps([int(value) for value in x_all.shape]),
        summary_mode=str(args.summary_mode),
        feature_summary_width=int(summary.shape[1]) if summary.ndim == 2 else 0,
        sampled_rows=int(len(selected)),
        train_rows=int(len(train_idx)),
        validation_rows=int(len(validation_idx)),
        test_rows=int(len(test_idx)),
        train_actionable_rate=float(train_dist.actionable_rate),
        validation_actionable_rate=float(validation_dist.actionable_rate),
        test_actionable_rate=float(test_dist.actionable_rate),
        always_hold_validation_accuracy=float(validation_dist.hold_rate),
        always_hold_test_accuracy=float(test_dist.hold_rate),
        full3_validation_accuracy=float(val_full["accuracy"]),
        full3_test_accuracy=float(test_full["accuracy"]),
        full3_validation_balanced_accuracy=float(val_full["balanced_accuracy"]),
        full3_test_balanced_accuracy=float(test_full["balanced_accuracy"]),
        binary_validation_base_rate=binary_base_val,
        binary_test_base_rate=binary_base_test,
        binary_validation_ap=float(val_binary_metrics["ap"]),
        binary_test_ap=float(test_binary_metrics["ap"]),
        binary_validation_ap_lift=float(val_binary_metrics["ap"] - binary_base_val),
        binary_test_ap_lift=float(test_binary_metrics["ap"] - binary_base_test),
        binary_validation_accuracy=float(val_binary_metrics["accuracy"]),
        binary_test_accuracy=float(test_binary_metrics["accuracy"]),
        binary_validation_balanced_accuracy=float(val_binary_metrics["balanced_accuracy"]),
        binary_test_balanced_accuracy=float(test_binary_metrics["balanced_accuracy"]),
        binary_validation_f1=float(val_binary_metrics["f1"]),
        binary_test_f1=float(test_binary_metrics["f1"]),
        side_train_rows=side_train_rows,
        side_validation_rows=side_validation_rows,
        side_test_rows=side_test_rows,
        side_validation_accuracy=float(side_val_metrics["accuracy"]),
        side_test_accuracy=float(side_test_metrics["accuracy"]),
        side_validation_balanced_accuracy=float(side_val_metrics["balanced_accuracy"]),
        side_test_balanced_accuracy=float(side_test_metrics["balanced_accuracy"]),
        side_validation_buy_ap=float(side_val_metrics["ap"]),
        side_test_buy_ap=float(side_test_metrics["ap"]),
        actionability_learnability_gate=action_gate,
        side_learnability_gate=side_gate,
        candidate_learnability_gate=int(action_gate and side_gate),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )
    return row, split_rows


def choose_best(rows: Sequence[LearnabilityRow]) -> tuple[str, str]:
    learnable = [row for row in rows if row.candidate_learnability_gate]
    if learnable:
        ranked = sorted(
            learnable,
            key=lambda row: (
                row.binary_validation_ap_lift,
                row.side_validation_balanced_accuracy,
                row.binary_test_ap_lift,
            ),
            reverse=True,
        )
        return ranked[0].candidate_id, "candidate passed actionability and side learnability gates"
    ranked = sorted(
        rows,
        key=lambda row: (
            row.binary_validation_ap_lift,
            row.side_validation_balanced_accuracy,
            row.binary_validation_balanced_accuracy,
        ),
        reverse=True,
    )
    if ranked:
        return ranked[0].candidate_id, "no gate pass; best diagnostic score only"
    return "", "no candidates evaluated"


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: LearnabilityReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{float(row['train_actionable_rate']):.3f}</td>"
        f"<td>{float(row['validation_actionable_rate']):.3f}</td>"
        f"<td>{float(row['test_actionable_rate']):.3f}</td>"
        f"<td>{float(row['binary_validation_ap']):.3f}</td>"
        f"<td>{float(row['binary_validation_ap_lift']):.3f}</td>"
        f"<td>{float(row['side_validation_balanced_accuracy']):.3f}</td>"
        f"<td>{int(row['candidate_learnability_gate'])}</td></tr>"
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase157A payoff target learnability diagnostic. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Learnability rows</h2><table><thead><tr><th>ID</th><th>Train act</th><th>Val act</th><th>Test act</th><th>Val AP</th><th>Val AP lift</th><th>Side bal acc</th><th>Gate</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE157A PAYOFF TARGET LEARNABILITY / IMBALANCE DIAGNOSTIC")
        print("=" * 74)
        candidates = parse_candidates(args.candidates)
        rows: list[LearnabilityRow] = []
        split_rows: list[SplitClassRow] = []
        for candidate in candidates:
            print(f"  [candidate] {candidate.candidate_id} tensor={candidate.tensor_name}", flush=True)
            row, splits = evaluate_candidate(args, candidate)
            rows.append(row)
            split_rows.extend(splits)
        best_id, best_reason = choose_best(rows)
        row_dicts = [asdict(row) for row in rows]
        split_dicts = [asdict(row) for row in split_rows]
        candidate_csv = output_dir / "latest_candidates.csv"
        split_csv = output_dir / "latest_splits.csv"
        write_csv(candidate_csv, row_dicts)
        write_csv(split_csv, split_dicts)
        report = LearnabilityReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            candidates=[asdict(candidate) for candidate in candidates],
            completed_candidates=len(rows),
            learnable_candidates=sum(int(row.candidate_learnability_gate) for row in rows),
            best_candidate_id=best_id,
            best_candidate_reason=best_reason,
            rows=row_dicts,
            split_rows=split_dicts,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidates_csv=str(candidate_csv),
            output_splits_csv=str(split_csv),
            production_status="BLOCKED — Phase157A learnability diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase157A learnability diagnostic complete")
        print(f"  candidates        : {report.completed_candidates}")
        print(f"  learnable         : {report.learnable_candidates}")
        print(f"  best diagnostic   : {report.best_candidate_id or 'none'}")
        print(f"  output            : {report.output_json}")
        print(f"  elapsed           : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
