"""Calibrate BUY/SELL thresholds for trend_signal booster specialist branches.

Phase 122 extends Phase 109 to the new booster branch. It does not train;
it loads the saved BUY and SELL specialist boosters, rebuilds the same
causal tabular window summaries, scores a calibration slice, searches a
BUY-threshold × SELL-threshold grid, and stores the chosen decision
thresholds in the model records when requested.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue
from ShadBotTrader.infrastructure.ai.model_roles import trend_signal_model_role
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split
from ShadBotTrader.infrastructure.ai.tabular_window_summary import SUMMARY_MODES, summarise_windows
from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol, stored_symbols
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

DEFAULT_STORAGE = REPO_ROOT / "datasets"
CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2
CLASS_NAMES = {CLASS_SELL: "sell", CLASS_HOLD: "hold", CLASS_BUY: "buy"}
SCOPES = ("auto", "holdout", "last-fold", "all")


@dataclass(frozen=True)
class SpecialistDecisionRow:
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    samples: int
    trades: int
    buy_trades: int
    sell_trades: int
    correct: int
    buy_correct: int
    sell_correct: int
    false_positive: int
    ambiguous: int
    no_trade: int
    buy_support: int
    sell_support: int
    action_precision: float
    buy_precision: float
    sell_precision: float
    action_recall: float
    buy_recall: float
    sell_recall: float
    action_f1: float
    coverage: float
    score: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate trend_signal BUY/SELL booster specialist thresholds.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--booster", default="lightgbm")
    parser.add_argument("--summary-mode", choices=SUMMARY_MODES, default="basic")
    parser.add_argument("--buy-model-id", default="")
    parser.add_argument("--sell-model-id", default="")
    parser.add_argument("--buy-model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--sell-model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument("--scope", choices=SCOPES, default="auto")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--val-size", type=int, default=2000)
    parser.add_argument("--threshold-min", type=float, default=0.35)
    parser.add_argument("--threshold-max", type=float, default=0.95)
    parser.add_argument("--threshold-step", type=float, default=0.05)
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--min-trades", type=int, default=50)
    parser.add_argument("--min-side-trades", type=int, default=10)
    parser.add_argument("--precision-floor", type=float, default=0.0)
    parser.add_argument("--max-windows", type=int, default=8000, help="0 = every selected window")
    parser.add_argument("--save-record", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default="run_logs/trend_signal_booster_thresholds")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def frange(start: float, stop: float, step: float) -> list[float]:
    if step <= 0:
        raise ValidationError("threshold-step must be positive")
    values: list[float] = []
    current = start
    while current <= stop + 1e-12:
        values.append(round(current, 6))
        current += step
    return values


def choose_scope(scope: str, train_ratio: float) -> str:
    if scope != "auto":
        return scope
    return "holdout" if 0 < train_ratio < 100 else "last-fold"


def default_model_id(kind: str, booster: str, summary_mode: str, timeframe: str) -> str:
    return f"gold_{kind}_{booster}_{summary_mode}_{timeframe.lower()}"


def latest_or_requested(catalogue: ModelCatalogue, model_id: str, requested: int) -> int:
    if requested > 0:
        return requested
    latest = catalogue.latest_version(model_id)
    if latest < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    return latest


def load_booster_artifact(
    storage_root: Path, model_id: str, version: int
) -> tuple[Any, dict[str, Any]]:
    artifact = FilesystemArtifactStore(storage_root).load(ModelId(model_id), ModelVersion(version))
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{version}")
    try:
        payload = pickle.loads(artifact.payload)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not load booster artifact because an optional package is missing. "
            "Install: pip install -r requirements-boosters.txt"
        ) from exc
    return payload["model"], payload


def aligned_positive_probability(model: Any, x_values: np.ndarray) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    if raw.ndim == 1:
        raw = np.column_stack([1.0 - raw, raw])
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    if 1 in classes:
        return raw[:, classes.index(1)]
    return np.zeros(len(raw), dtype=np.float64)


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    _, store, _ = build_data_service(storage_root)
    resolved = resolve_stored_symbol(store, symbol, timeframe)
    if not resolved.found:
        raise RuntimeError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    if resolved.is_alias:
        print(f"  [i] {resolved.note}")
    return store.query(Symbol(resolved.resolved), Timeframe(timeframe))


def prepare_dataset(args: argparse.Namespace, candles: Sequence[Any]):
    role = trend_signal_model_role(
        timeframe=args.timeframe,
        threshold=args.atr_mult,
        window_size=args.window,
        label_horizon=args.label_horizon,
    )
    service = DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )
    return role, service.prepare(candles, Symbol(args.symbol), Timeframe(args.timeframe), role)


def resolved_val_size(rows: int, requested: int, window_size: int) -> int:
    candidate = requested if requested > 0 else max(4, min(2000, rows // 10))
    min_train = max(8, min(rows // 4, 20 * window_size))
    return max(4, min(candidate, rows - min_train - window_size - 4))


def last_fold_positions(dataset: Any, rows: int, requested_val: int, max_folds: int) -> list[int]:
    if dataset.sample_ends is None:
        raise RuntimeError("trend_signal dataset did not expose sample_ends")
    resolved = resolved_val_size(rows, requested_val, dataset.role.window_size)
    plan = expanding_split(
        total_length=rows,
        val_size=resolved,
        step=resolved,
        min_train_size=max(8, min(rows // 4, 20 * dataset.role.window_size)),
        purge_gap=max(dataset.role.window_size - 1, 0),
        sample_end_indices=dataset.sample_ends,
        label_end_indices=dataset.sample_label_ends,
        window_size=dataset.role.window_size,
    )
    folds = list(plan.folds)
    if max_folds > 0:
        folds = folds[-max_folds:]
    if not folds:
        return []
    fold = folds[-1]
    return list(range(fold.val_start, fold.val_end))


def select_evenly(values: Sequence[int], max_count: int) -> list[int]:
    if max_count <= 0 or len(values) <= max_count:
        return list(values)
    step = max(1, len(values) // max_count)
    return list(values[::step])[:max_count]


def selected_positions(
    args: argparse.Namespace,
    dataset: Any,
    candles_count: int,
    effective_scope: str,
) -> list[int]:
    if dataset.sample_ends is None:
        raise RuntimeError("trend_signal dataset did not expose sample_ends")
    total = len(dataset.sample_ends)
    if effective_scope == "all":
        return select_evenly(list(range(total)), args.max_windows)
    if effective_scope == "last-fold":
        return select_evenly(
            last_fold_positions(dataset, total, args.val_size, args.folds), args.max_windows
        )
    if effective_scope == "holdout":
        cutoff = int(candles_count * args.train_ratio / 100.0)
        rows = [
            index
            for index, sample_end in enumerate(dataset.sample_ends)
            if int(sample_end) + int(dataset.dropped_warmup) >= cutoff
        ]
        return select_evenly(rows, args.max_windows)
    raise ValidationError(f"Unknown calibration scope: {effective_scope}")


def true_labels_for_positions(dataset: Any, positions: Sequence[int]) -> list[int]:
    if dataset.sample_ends is None:
        raise RuntimeError("trend_signal dataset did not expose sample_ends")
    target = dataset.target_columns[0]
    return [int(round(dataset.series[dataset.sample_ends[index]][target])) for index in positions]


def class_counts(labels: Sequence[int]) -> dict[str, int]:
    return {name: sum(1 for label in labels if label == cls) for cls, name in CLASS_NAMES.items()}


def decide_pair(
    buy_prob: float,
    sell_prob: float,
    buy_threshold: float,
    sell_threshold: float,
    min_margin: float,
) -> int | None:
    buy_ok = buy_prob >= buy_threshold and buy_prob - sell_prob >= min_margin
    sell_ok = sell_prob >= sell_threshold and sell_prob - buy_prob >= min_margin
    if buy_ok and sell_ok:
        return -1
    if buy_ok:
        return CLASS_BUY
    if sell_ok:
        return CLASS_SELL
    return None


def calibrate_grid(
    y_true: Sequence[int],
    buy_probs: Sequence[float],
    sell_probs: Sequence[float],
    thresholds: Sequence[float],
    min_margin: float,
    min_trades: int,
    min_side_trades: int,
    precision_floor: float,
) -> list[SpecialistDecisionRow]:
    buy_support = sum(1 for label in y_true if label == CLASS_BUY)
    sell_support = sum(1 for label in y_true if label == CLASS_SELL)
    action_support = buy_support + sell_support
    rows: list[SpecialistDecisionRow] = []
    for buy_threshold in thresholds:
        for sell_threshold in thresholds:
            buy_trades = sell_trades = buy_correct = sell_correct = 0
            false_positive = ambiguous = no_trade = 0
            for actual, buy_prob, sell_prob in zip(y_true, buy_probs, sell_probs, strict=True):
                decision = decide_pair(
                    float(buy_prob),
                    float(sell_prob),
                    buy_threshold,
                    sell_threshold,
                    min_margin,
                )
                if decision == -1:
                    ambiguous += 1
                    no_trade += 1
                elif decision is None:
                    no_trade += 1
                elif decision == CLASS_BUY:
                    buy_trades += 1
                    if actual == CLASS_BUY:
                        buy_correct += 1
                    else:
                        false_positive += 1
                elif decision == CLASS_SELL:
                    sell_trades += 1
                    if actual == CLASS_SELL:
                        sell_correct += 1
                    else:
                        false_positive += 1
            trades = buy_trades + sell_trades
            correct = buy_correct + sell_correct
            action_precision = safe_div(correct, trades)
            action_recall = safe_div(correct, action_support)
            action_f1 = (
                2 * action_precision * action_recall / (action_precision + action_recall)
                if action_precision + action_recall
                else 0.0
            )
            score = action_f1
            if (
                trades < min_trades
                or action_precision < precision_floor
                or buy_trades < min_side_trades
                or sell_trades < min_side_trades
            ):
                score = -1.0
            rows.append(
                SpecialistDecisionRow(
                    buy_threshold=buy_threshold,
                    sell_threshold=sell_threshold,
                    min_margin=min_margin,
                    samples=len(y_true),
                    trades=trades,
                    buy_trades=buy_trades,
                    sell_trades=sell_trades,
                    correct=correct,
                    buy_correct=buy_correct,
                    sell_correct=sell_correct,
                    false_positive=false_positive,
                    ambiguous=ambiguous,
                    no_trade=no_trade,
                    buy_support=buy_support,
                    sell_support=sell_support,
                    action_precision=action_precision,
                    buy_precision=safe_div(buy_correct, buy_trades),
                    sell_precision=safe_div(sell_correct, sell_trades),
                    action_recall=action_recall,
                    buy_recall=safe_div(buy_correct, buy_support),
                    sell_recall=safe_div(sell_correct, sell_support),
                    action_f1=action_f1,
                    coverage=safe_div(trades, len(y_true)),
                    score=score,
                )
            )
    return rows


def select_best(rows: Sequence[SpecialistDecisionRow]) -> SpecialistDecisionRow | None:
    valid = [row for row in rows if row.score >= 0]
    if not valid:
        return None
    return max(valid, key=lambda row: (row.score, row.action_precision, row.trades))


def write_csv(path: Path, rows: Sequence[SpecialistDecisionRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        if rows:
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))


def write_html(
    path: Path, best: SpecialistDecisionRow | None, rows: Sequence[SpecialistDecisionRow]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ""
    if best is not None:
        body += f"""
<h2>Best thresholds</h2>
<ul>
  <li>BUY threshold: {best.buy_threshold:.3f}</li>
  <li>SELL threshold: {best.sell_threshold:.3f}</li>
  <li>Precision: {best.action_precision:.1%}</li>
  <li>Recall: {best.action_recall:.1%}</li>
  <li>F1: {best.action_f1:.4f}</li>
  <li>Coverage: {best.coverage:.1%}</li>
  <li>Trades: {best.trades}</li>
</ul>
"""
    top = sorted(rows, key=lambda row: row.score, reverse=True)[:25]
    body += "<h2>Top grid rows</h2><table><tr>"
    headers = list(asdict(top[0]).keys()) if top else []
    body += "".join(f"<th>{name}</th>" for name in headers) + "</tr>"
    for row in top:
        data = asdict(row)
        body += "<tr>" + "".join(f"<td>{data[name]}</td>" for name in headers) + "</tr>"
    body += "</table>"
    path.write_text(
        """<!doctype html><meta charset="utf-8"><style>
body{font-family:system-ui;background:#0e1117;color:#e6edf3;padding:24px}
table{border-collapse:collapse}td,th{border:1px solid #30363d;padding:4px 8px}
th{color:#8b949e}</style><title>Trend-signal booster thresholds</title>""" + body,
        encoding="utf-8",
    )


def save_record_thresholds(
    storage_root: Path,
    buy_model_id: str,
    buy_version: int,
    sell_model_id: str,
    sell_version: int,
    best: SpecialistDecisionRow,
    metadata: dict[str, Any],
) -> list[str]:
    catalogue = ModelCatalogue(storage_root)
    written: list[str] = []
    thresholds = {
        "buy_prob": best.buy_threshold,
        "sell_prob": best.sell_threshold,
        "min_margin": best.min_margin,
        "selected_by": "phase122_booster_specialist_grid_action_f1",
        "action_precision": best.action_precision,
        "action_recall": best.action_recall,
        "action_f1": best.action_f1,
        "coverage": best.coverage,
        "trades": best.trades,
        "buy_trades": best.buy_trades,
        "sell_trades": best.sell_trades,
        "samples": best.samples,
        "metadata": metadata,
    }
    for model_id, version in ((buy_model_id, buy_version), (sell_model_id, sell_version)):
        record = catalogue.read(model_id, version)
        if record is None:
            continue
        record.decision_thresholds = dict(thresholds)
        written.append(str(catalogue.write(record)))
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    buy_model_id = args.buy_model_id or default_model_id(
        "buy", args.booster, args.summary_mode, args.timeframe
    )
    sell_model_id = args.sell_model_id or default_model_id(
        "sell", args.booster, args.summary_mode, args.timeframe
    )
    effective_scope = choose_scope(args.scope, args.train_ratio)

    try:
        rule("TREND_SIGNAL BOOSTER THRESHOLD CALIBRATION")
        print(f"  symbol      : {args.symbol}")
        print(f"  timeframe   : {args.timeframe}")
        print(f"  scope       : {effective_scope}")
        print(f"  buy model   : {buy_model_id}")
        print(f"  sell model  : {sell_model_id}")

        catalogue = ModelCatalogue(storage_root)
        buy_version = latest_or_requested(catalogue, buy_model_id, args.buy_model_version)
        sell_version = latest_or_requested(catalogue, sell_model_id, args.sell_model_version)
        buy_model, _buy_payload = load_booster_artifact(storage_root, buy_model_id, buy_version)
        sell_model, _sell_payload = load_booster_artifact(storage_root, sell_model_id, sell_version)

        candles = load_candles(storage_root, args.symbol, args.timeframe)
        role, dataset = prepare_dataset(args, candles)
        positions = selected_positions(args, dataset, len(candles), effective_scope)
        if not positions:
            raise RuntimeError("No calibration windows selected")
        sample_ends = [dataset.sample_ends[index] for index in positions]  # type: ignore[index]
        y_true = true_labels_for_positions(dataset, positions)

        rule("CALIBRATION DATA")
        print(f"  windows     : {len(positions):,}")
        print(f"  labels      : {class_counts(y_true)}")
        summary = summarise_windows(
            series=dataset.series,
            feature_count=dataset.feature_count,
            column_names=dataset.column_names,
            sample_ends=sample_ends,
            window_size=role.window_size,
            mode=args.summary_mode,
        )
        print(f"  features    : {summary.columns:,}")

        buy_probs = aligned_positive_probability(buy_model, summary.values)
        sell_probs = aligned_positive_probability(sell_model, summary.values)
        thresholds = frange(args.threshold_min, args.threshold_max, args.threshold_step)
        rows = calibrate_grid(
            y_true,
            buy_probs,
            sell_probs,
            thresholds,
            min_margin=max(args.min_margin, 0.0),
            min_trades=max(args.min_trades, 0),
            min_side_trades=max(args.min_side_trades, 0),
            precision_floor=max(args.precision_floor, 0.0),
        )
        best = select_best(rows)

        rule("BEST THRESHOLDS")
        if best is None:
            print("  [X] No threshold pair satisfied the constraints.")
        else:
            print(f"  buy prob    : {best.buy_threshold:.3f}")
            print(f"  sell prob   : {best.sell_threshold:.3f}")
            print(f"  min margin  : {best.min_margin:.3f}")
            print(f"  trades      : {best.trades:,}/{best.samples:,} ({best.coverage:.1%})")
            print(f"  buy/sell    : {best.buy_trades:,} / {best.sell_trades:,}")
            print(f"  precision   : {best.action_precision:.1%}")
            print(f"  recall      : {best.action_recall:.1%}")
            print(f"  action F1   : {best.action_f1:.4f}")
            print(f"  buy P/R     : {best.buy_precision:.1%} / {best.buy_recall:.1%}")
            print(f"  sell P/R    : {best.sell_precision:.1%} / {best.sell_recall:.1%}")

        out_dir = Path(args.output_dir)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = out_dir / f"{stamp}.csv"
        html_path = out_dir / f"{stamp}.html"
        json_path = out_dir / f"{stamp}.json"
        latest_csv = out_dir / "latest.csv"
        latest_html = out_dir / "latest.html"
        latest_json = out_dir / "latest.json"
        write_csv(csv_path, rows)
        write_csv(latest_csv, rows)
        write_html(html_path, best, rows)
        write_html(latest_html, best, rows)

        metadata = {
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "buy_model_id": buy_model_id,
            "buy_model_version": buy_version,
            "sell_model_id": sell_model_id,
            "sell_model_version": sell_version,
            "summary_mode": args.summary_mode,
            "scope": effective_scope,
            "train_ratio": args.train_ratio,
            "window": args.window,
            "label_horizon": args.label_horizon,
            "atr_mult": args.atr_mult,
        }
        written_records: list[str] = []
        if best is not None and args.save_record == "1":
            written_records = save_record_thresholds(
                storage_root,
                buy_model_id,
                buy_version,
                sell_model_id,
                sell_version,
                best,
                metadata,
            )
            for path in written_records:
                print(f"  record saved: {path}")

        payload = {
            "args": vars(args),
            "metadata": metadata,
            "best": asdict(best) if best is not None else None,
            "rows": [asdict(row) for row in rows],
            "written_records": written_records,
            "files": {
                "csv": str(csv_path),
                "html": str(html_path),
                "json": str(json_path),
                "latest_csv": str(latest_csv),
                "latest_html": str(latest_html),
                "latest_json": str(latest_json),
            },
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        latest_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  csv/html/json: {latest_csv} | {latest_html} | {latest_json}")
        return 0 if best is not None else 2
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
