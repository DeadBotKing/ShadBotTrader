"""Phase149A: validation-only feature impact audit for pivot sequence models.

This diagnostic answers: which input features look useful, neutral, or harmful
for the currently trained sequence WaveNet candidate?

It works by evaluating a trained model on a chronological validation/test split,
then zero-ablating feature groups and individual raw feature columns at inference
(time-series window) level. If removing a feature improves validation metrics,
that feature is marked as a DROP_CANDIDATE for later anti-overfit filtering.

Important: this is a diagnostic, not proof. Candidate drops must be confirmed by
retraining and/or walk-forward; never select filters on the final test only.
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

from backtest_pivot_pattern_sequence_wavenet import (  # noqa: E402
    default_flat_path,
    eval_tensor_indices,
    is_option_b_record,
    load_meta,
    load_model,
    load_record,
    model_args_from_record,
    normalize_batch,
    resolve_model_files,
)
from train_pivot_pattern_image_cnn import metric_block, selected_indices
from train_pivot_pattern_sequence_wavenet import default_meta_path, default_tensor_path
from train_pivot_pattern_sequence_wavenet_option_b import grouped_normalized_batch, option_b_groups
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_sequence_feature_impact")


@dataclass(frozen=True)
class FeatureImpactRow:
    kind: str
    feature_index: int
    feature_name: str
    feature_group: str
    disabled_count: int
    baseline_composite: float
    ablated_composite: float
    delta_composite: float
    baseline_action_accuracy: float
    ablated_action_accuracy: float
    delta_action_accuracy: float
    baseline_top_ap: float
    ablated_top_ap: float
    delta_top_ap: float
    baseline_bottom_ap: float
    ablated_bottom_ap: float
    delta_bottom_ap: float
    baseline_buy_r_mae: float
    ablated_buy_r_mae: float
    delta_buy_r_mae: float
    baseline_sell_r_mae: float
    ablated_sell_r_mae: float
    delta_sell_r_mae: float
    baseline_selected_rate: float
    ablated_selected_rate: float
    delta_selected_rate: float
    recommendation: str


@dataclass(frozen=True)
class FeatureImpactReport:
    model_id: str
    model_version: int
    model_path: str
    record_path: str
    tensor_path: str
    meta_path: str
    tensor_shape: list[int]
    eval_split: str
    selected_samples: int
    evaluated_samples: int
    evaluated_first_timestamp: str
    evaluated_last_timestamp: str
    option_b_model: bool
    branch_target_features: int
    feature_augmentation_mode: str
    feature_augmentation_clip: float
    baseline_metrics: dict[str, float]
    baseline_composite: float
    feature_count: int
    checked_feature_count: int
    drop_candidates: int
    keep_important: int
    neutral_features: int
    group_rows: list[dict[str, Any]]
    top_drop_candidates: list[dict[str, Any]]
    top_keep_important: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_features_csv: str
    output_groups_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit sequence feature impact via validation/test zero ablation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_sequence_wavenet_option_b_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--model-path", default="")
    parser.add_argument("--record-path", default="")
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--eval-split", choices=("validation", "test", "tail"), default="validation")
    parser.add_argument("--eval-frac", type=float, default=0.15, help="Used only with --eval-split tail")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--min-buy-r", type=float, default=-999.0)
    parser.add_argument("--min-sell-r", type=float, default=-999.0)
    parser.add_argument("--check-groups", choices=("0", "1"), default="1")
    parser.add_argument("--check-features", choices=("0", "1"), default="1")
    parser.add_argument("--feature-group-filter", default="all", help="all or comma list: generated_5m,source_5m,session,closed_4h,closed_1d")
    parser.add_argument("--max-features-to-check", type=int, default=0, help="0 = every matching feature")
    parser.add_argument("--harmful-threshold", type=float, default=0.005)
    parser.add_argument("--useful-threshold", type=float, default=0.005)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase149A sequence feature impact audit")
    return parser.parse_args(argv)


def feature_names(meta: Mapping[str, Any]) -> list[str]:
    return [str(value) for value in np.asarray(meta.get("feature_names", []), dtype=object).tolist()]


def feature_groups(meta: Mapping[str, Any], count: int) -> list[str]:
    groups = [str(value) for value in np.asarray(meta.get("feature_groups", []), dtype=object).tolist()]
    return groups if len(groups) == count else ["unknown"] * count


def threshold_value(args_value: float, record: Mapping[str, Any], key: str, default: float) -> float:
    if args_value >= 0:
        return float(args_value)
    payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
    thresholds = payload.get("thresholds", {}) if isinstance(payload, Mapping) else {}
    return float(thresholds.get(key, default))


def metric_args(args: argparse.Namespace, record: Mapping[str, Any]) -> argparse.Namespace:
    return argparse.Namespace(
        buy_threshold=threshold_value(args.buy_threshold, record, "buy_threshold", 0.34),
        sell_threshold=threshold_value(args.sell_threshold, record, "sell_threshold", 0.34),
        min_margin=threshold_value(args.min_margin, record, "min_margin", 0.0),
        min_buy_r=(
            float(args.min_buy_r)
            if float(args.min_buy_r) > -998
            else threshold_value(-1.0, record, "min_buy_r", -999.0)
        ),
        min_sell_r=(
            float(args.min_sell_r)
            if float(args.min_sell_r) > -998
            else threshold_value(-1.0, record, "min_sell_r", -999.0)
        ),
    )


def target_dict_from_meta(meta: Mapping[str, Any], eval_rows: Sequence[int]) -> dict[str, np.ndarray]:
    idx = np.asarray(eval_rows, dtype=np.int64)
    return {
        "action": np.asarray(meta["target_action"], dtype=np.int64)[idx],
        "top": np.asarray(meta["target_top_zone"], dtype=np.float32)[idx].reshape(-1, 1),
        "bottom": np.asarray(meta["target_bottom_zone"], dtype=np.float32)[idx].reshape(-1, 1),
        "buy_r": np.asarray(meta["target_buy_r"], dtype=np.float32)[idx].reshape(-1, 1),
        "sell_r": np.asarray(meta["target_sell_r"], dtype=np.float32)[idx].reshape(-1, 1),
    }


def composite_score(metrics: Mapping[str, float], prefix: str) -> float:
    return float(
        metrics.get(f"{prefix}_action_accuracy", 0.0)
        + 0.5 * metrics.get(f"{prefix}_top_ap", 0.0)
        + 0.5 * metrics.get(f"{prefix}_bottom_ap", 0.0)
        - 0.25 * metrics.get(f"{prefix}_buy_r_mae", 0.0)
        - 0.25 * metrics.get(f"{prefix}_sell_r_mae", 0.0)
    )


def recommendation(delta_composite: float, harmful_threshold: float, useful_threshold: float) -> str:
    if delta_composite >= harmful_threshold:
        return "DROP_CANDIDATE"
    if delta_composite <= -useful_threshold:
        return "KEEP_IMPORTANT"
    return "NEUTRAL"


def matching_feature_indices(groups: Sequence[str], filter_text: str) -> np.ndarray:
    if filter_text.strip().lower() in {"", "all"}:
        return np.arange(len(groups), dtype=np.int64)
    allowed = {part.strip() for part in filter_text.split(",") if part.strip()}
    return np.asarray([idx for idx, group in enumerate(groups) if group in allowed], dtype=np.int64)


def group_index_map(groups: Sequence[str]) -> dict[str, np.ndarray]:
    result: dict[str, list[int]] = {
        "generated_5m": [],
        "source_5m": [],
        "session": [],
        "closed_4h": [],
        "closed_1d": [],
        "m5_context": [],
        "htf_context": [],
        "all_features": list(range(len(groups))),
    }
    for idx, group in enumerate(groups):
        if group in result:
            result[group].append(idx)
        if group in {"generated_5m", "session"}:
            result["m5_context"].append(idx)
        if group in {"closed_4h", "closed_1d"}:
            result["htf_context"].append(idx)
    return {key: np.asarray(value, dtype=np.int64) for key, value in result.items() if value}


def predict_with_disabled_features(
    tf: Any,
    model: Any,
    x_values: np.ndarray,
    eval_rows: Sequence[int],
    record: Mapping[str, Any],
    meta: Mapping[str, Any],
    option_b: bool,
    disabled_features: Sequence[int],
    batch_size: int,
) -> dict[str, np.ndarray]:
    disabled = np.asarray(disabled_features, dtype=np.int64)
    groups = None
    model_args = None
    if option_b:
        from train_pivot_pattern_sequence_wavenet_option_b import grouped_normalized_batch, option_b_groups

        groups = option_b_groups(meta)
        model_args = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["model_args_from_record"]
        ).model_args_from_record(record)

    class AblationSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.rows = np.asarray(eval_rows, dtype=np.int64)

        def __len__(self) -> int:
            return int(np.ceil(len(self.rows) / max(int(batch_size), 1)))

        def __getitem__(self, index: int):
            start = index * max(int(batch_size), 1)
            end = min(len(self.rows), start + max(int(batch_size), 1))
            rows = self.rows[start:end]
            normalize_batch = __import__(
                "backtest_pivot_pattern_sequence_wavenet", fromlist=["normalize_batch"]
            ).normalize_batch
            normalized = normalize_batch(np.asarray(x_values[rows]), record)
            if disabled.size:
                normalized[:, :, disabled] = 0.0
            if not option_b:
                return normalized
            assert groups is not None and model_args is not None
            return grouped_normalized_batch(
                normalized,
                groups,
                int(model_args.branch_target_features),
                str(model_args.feature_augmentation_mode),
                float(model_args.feature_augmentation_clip),
            )

    return prediction_dict(model.predict(AblationSequence(), verbose=0))


def impact_row(
    kind: str,
    index: int,
    name: str,
    group: str,
    disabled_count: int,
    baseline: Mapping[str, float],
    ablated: Mapping[str, float],
    prefix: str,
    args: argparse.Namespace,
) -> FeatureImpactRow:
    baseline_comp = composite_score(baseline, prefix)
    ablated_comp = composite_score(ablated, prefix)
    delta_comp = ablated_comp - baseline_comp
    return FeatureImpactRow(
        kind=kind,
        feature_index=int(index),
        feature_name=name,
        feature_group=group,
        disabled_count=int(disabled_count),
        baseline_composite=baseline_comp,
        ablated_composite=ablated_comp,
        delta_composite=delta_comp,
        baseline_action_accuracy=float(baseline.get(f"{prefix}_action_accuracy", 0.0)),
        ablated_action_accuracy=float(ablated.get(f"{prefix}_action_accuracy", 0.0)),
        delta_action_accuracy=float(
            ablated.get(f"{prefix}_action_accuracy", 0.0)
            - baseline.get(f"{prefix}_action_accuracy", 0.0)
        ),
        baseline_top_ap=float(baseline.get(f"{prefix}_top_ap", 0.0)),
        ablated_top_ap=float(ablated.get(f"{prefix}_top_ap", 0.0)),
        delta_top_ap=float(ablated.get(f"{prefix}_top_ap", 0.0) - baseline.get(f"{prefix}_top_ap", 0.0)),
        baseline_bottom_ap=float(baseline.get(f"{prefix}_bottom_ap", 0.0)),
        ablated_bottom_ap=float(ablated.get(f"{prefix}_bottom_ap", 0.0)),
        delta_bottom_ap=float(
            ablated.get(f"{prefix}_bottom_ap", 0.0) - baseline.get(f"{prefix}_bottom_ap", 0.0)
        ),
        baseline_buy_r_mae=float(baseline.get(f"{prefix}_buy_r_mae", 0.0)),
        ablated_buy_r_mae=float(ablated.get(f"{prefix}_buy_r_mae", 0.0)),
        delta_buy_r_mae=float(
            ablated.get(f"{prefix}_buy_r_mae", 0.0) - baseline.get(f"{prefix}_buy_r_mae", 0.0)
        ),
        baseline_sell_r_mae=float(baseline.get(f"{prefix}_sell_r_mae", 0.0)),
        ablated_sell_r_mae=float(ablated.get(f"{prefix}_sell_r_mae", 0.0)),
        delta_sell_r_mae=float(
            ablated.get(f"{prefix}_sell_r_mae", 0.0) - baseline.get(f"{prefix}_sell_r_mae", 0.0)
        ),
        baseline_selected_rate=float(baseline.get(f"{prefix}_selected_rate", 0.0)),
        ablated_selected_rate=float(ablated.get(f"{prefix}_selected_rate", 0.0)),
        delta_selected_rate=float(
            ablated.get(f"{prefix}_selected_rate", 0.0)
            - baseline.get(f"{prefix}_selected_rate", 0.0)
        ),
        recommendation=recommendation(delta_comp, args.harmful_threshold, args.useful_threshold),
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_html(title: str, report: FeatureImpactReport) -> str:
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
pre,code {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:4px 8px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase149A validation-only feature impact audit. Research only.</p>
<div class="grid">
<div class="metric"><span>Baseline composite</span><strong>{report.baseline_composite:.4f}</strong></div>
<div class="metric"><span>Features checked</span><strong>{report.checked_feature_count}</strong></div>
<div class="metric"><span>Drop candidates</span><strong>{report.drop_candidates}</strong></div>
<div class="metric"><span>Keep important</span><strong>{report.keep_important}</strong></div>
</div><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Top drop candidates</h2><pre>{html.escape(json.dumps(report.top_drop_candidates, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Top keep important</h2><pre>{html.escape(json.dumps(report.top_keep_important, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


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
    meta_path = (
        Path(args.meta_path)
        if args.meta_path
        else default_meta_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE149A SEQUENCE FEATURE IMPACT AUDIT")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        model_path, record_path, version = resolve_model_files(args)
        record = load_record(record_path)
        tf = require_tensorflow()
        x_all = np.load(tensor_path, mmap_mode="r")
        meta = load_meta(meta_path)
        model = load_model(model_path, record, meta, tuple(int(value) for value in x_all.shape[1:]))
        names = feature_names(meta)
        groups = feature_groups(meta, len(names))
        selected_rows = selected_indices(int(x_all.shape[0]), int(args.max_samples))
        eval_rows, eval_name = eval_tensor_indices(selected_rows, args)
        eval_rows = eval_rows[: int(args.max_windows)] if int(args.max_windows) > 0 else eval_rows
        targets = target_dict_from_meta(meta, eval_rows)
        option_b = is_option_b_record(record)
        baseline_predictions = predict_with_disabled_features(
            tf,
            model,
            x_all,
            eval_rows,
            record,
            meta,
            option_b,
            [],
            max(int(args.batch_size), 1),
        )
        metric_namespace = metric_args(args, record)
        baseline_metrics = metric_block(targets, baseline_predictions, metric_namespace, eval_name)
        baseline_comp = composite_score(baseline_metrics, eval_name)
        group_rows: list[FeatureImpactRow] = []
        if args.check_groups == "1":
            for group_name, group_indices in group_index_map(groups).items():
                ablated_predictions = predict_with_disabled_features(
                    tf,
                    model,
                    x_all,
                    eval_rows,
                    record,
                    meta,
                    option_b,
                    group_indices,
                    max(int(args.batch_size), 1),
                )
                ablated_metrics = metric_block(targets, ablated_predictions, metric_namespace, eval_name)
                group_rows.append(
                    impact_row(
                        "group",
                        -1,
                        group_name,
                        group_name,
                        len(group_indices),
                        baseline_metrics,
                        ablated_metrics,
                        eval_name,
                        args,
                    )
                )
        feature_rows: list[FeatureImpactRow] = []
        feature_indices = matching_feature_indices(groups, args.feature_group_filter)
        if args.max_features_to_check > 0:
            feature_indices = feature_indices[: int(args.max_features_to_check)]
        if args.check_features == "1":
            for ordinal, feature_index in enumerate(feature_indices, start=1):
                print(f"  feature {ordinal}/{len(feature_indices)}: {names[int(feature_index)]}")
                ablated_predictions = predict_with_disabled_features(
                    tf,
                    model,
                    x_all,
                    eval_rows,
                    record,
                    meta,
                    option_b,
                    [int(feature_index)],
                    max(int(args.batch_size), 1),
                )
                ablated_metrics = metric_block(targets, ablated_predictions, metric_namespace, eval_name)
                feature_rows.append(
                    impact_row(
                        "feature",
                        int(feature_index),
                        names[int(feature_index)],
                        groups[int(feature_index)],
                        1,
                        baseline_metrics,
                        ablated_metrics,
                        eval_name,
                        args,
                    )
                )
        all_feature_dicts = [asdict(row) for row in feature_rows]
        group_dicts = [asdict(row) for row in group_rows]
        drop = [row for row in all_feature_dicts if row["recommendation"] == "DROP_CANDIDATE"]
        keep = [row for row in all_feature_dicts if row["recommendation"] == "KEEP_IMPORTANT"]
        neutral = [row for row in all_feature_dicts if row["recommendation"] == "NEUTRAL"]
        drop_sorted = sorted(drop, key=lambda row: row["delta_composite"], reverse=True)
        keep_sorted = sorted(keep, key=lambda row: row["delta_composite"])
        first_time = ""
        last_time = ""
        if len(eval_rows):
            timestamps = np.asarray(meta.get("timestamp", []), dtype=object)
            first_time = str(timestamps[int(eval_rows[0])]) if len(timestamps) > int(eval_rows[0]) else ""
            last_time = str(timestamps[int(eval_rows[-1])]) if len(timestamps) > int(eval_rows[-1]) else ""
        report = FeatureImpactReport(
            model_id=args.model_id,
            model_version=version,
            model_path=str(model_path),
            record_path=str(record_path),
            tensor_path=str(tensor_path),
            meta_path=str(meta_path),
            tensor_shape=[int(value) for value in x_all.shape],
            eval_split=eval_name,
            selected_samples=len(selected_rows),
            evaluated_samples=len(eval_rows),
            evaluated_first_timestamp=first_time,
            evaluated_last_timestamp=last_time,
            option_b_model=bool(option_b),
            branch_target_features=int(getattr(model_args_from_record(record), "branch_target_features", 0)),
            feature_augmentation_mode=str(
                getattr(model_args_from_record(record), "feature_augmentation_mode", "off")
            ),
            feature_augmentation_clip=float(
                getattr(model_args_from_record(record), "feature_augmentation_clip", 8.0)
            ),
            baseline_metrics=dict(baseline_metrics),
            baseline_composite=float(baseline_comp),
            feature_count=len(names),
            checked_feature_count=len(feature_rows),
            drop_candidates=len(drop),
            keep_important=len(keep),
            neutral_features=len(neutral),
            group_rows=group_dicts,
            top_drop_candidates=drop_sorted[:50],
            top_keep_important=keep_sorted[:50],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_features_csv=str(output_dir / "latest_features.csv"),
            output_groups_csv=str(output_dir / "latest_groups.csv"),
            production_status="BLOCKED — feature impact diagnostic only",
        )
        write_csv(Path(report.output_features_csv), all_feature_dicts)
        write_csv(Path(report.output_groups_csv), group_dicts)
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "features_csv": report.output_features_csv,
                "groups_csv": report.output_groups_csv,
            },
        }
        Path(report.output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  model       : {model_path}")
        print(f"  split       : {eval_name}")
        print(f"  evaluated   : {len(eval_rows):,}")
        print(f"  baseline    : {baseline_comp:.6f}")
        print(f"  drop cand.  : {len(drop)}")
        print(f"  keep imp.   : {len(keep)}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
