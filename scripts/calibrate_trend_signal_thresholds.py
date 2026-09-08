"""Phase 109 — calibrate BUY/SELL thresholds for trend_signal models.

The script loads a frozen trend_signal model, predicts labelled windows,
tries a BUY threshold × SELL threshold grid, and writes CSV/HTML/JSON
artifacts with precision/recall/F1/coverage statistics.  It never trains
or changes model weights.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_STORAGE = REPO_ROOT / "datasets"
CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2


@dataclass(frozen=True)
class ThresholdRow:
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
    action_precision: float
    buy_precision: float
    sell_precision: float
    action_recall: float
    buy_recall: float
    sell_recall: float
    action_f1: float
    coverage: float
    score: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "min_margin": self.min_margin,
            "samples": self.samples,
            "trades": self.trades,
            "buy_trades": self.buy_trades,
            "sell_trades": self.sell_trades,
            "correct": self.correct,
            "buy_correct": self.buy_correct,
            "sell_correct": self.sell_correct,
            "false_positive": self.false_positive,
            "ambiguous": self.ambiguous,
            "no_trade": self.no_trade,
            "action_precision": self.action_precision,
            "buy_precision": self.buy_precision,
            "sell_precision": self.sell_precision,
            "action_recall": self.action_recall,
            "buy_recall": self.buy_recall,
            "sell_recall": self.sell_recall,
            "action_f1": self.action_f1,
            "coverage": self.coverage,
            "score": self.score,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate BUY/SELL probability thresholds for a trend_signal model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--model-id", default="")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument(
        "--scope",
        choices=("auto", "holdout", "last-fold", "all"),
        default="auto",
        help=(
            "windows used for calibration; auto uses holdout when "
            "train-ratio < 100 else last-fold"
        ),
    )
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--val-size", type=int, default=0)
    parser.add_argument("--threshold-min", type=float, default=0.35)
    parser.add_argument("--threshold-max", type=float, default=0.95)
    parser.add_argument("--threshold-step", type=float, default=0.05)
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--min-trades", type=int, default=50)
    parser.add_argument("--precision-floor", type=float, default=0.0)
    parser.add_argument("--max-windows", type=int, default=8000, help="0 = every selected window")
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default="run_logs/trend_signal_thresholds")
    parser.add_argument(
        "--save-record",
        choices=("0", "1"),
        default="1",
        help="write the selected thresholds into the model's training record",
    )
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def frange(start: float, stop: float, step: float) -> list[float]:
    if step <= 0:
        raise ValueError("threshold-step must be positive")
    values: list[float] = []
    current = start
    while current <= stop + 1e-12:
        values.append(round(current, 6))
        current += step
    return values


def choose_scope(requested: str, train_ratio: float) -> str:
    if requested != "auto":
        return requested
    return "holdout" if 0 < train_ratio < 100 else "last-fold"


def select_sample_positions(total: int, max_windows: int) -> list[int]:
    if total <= 0:
        return []
    if max_windows <= 0 or total <= max_windows:
        return list(range(total))
    step = max(1, total // max_windows)
    return list(range(0, total, step))[:max_windows]


def class_counts(labels: Sequence[int]) -> dict[str, int]:
    return {
        "sell": sum(1 for value in labels if value == CLASS_SELL),
        "hold": sum(1 for value in labels if value == CLASS_HOLD),
        "buy": sum(1 for value in labels if value == CLASS_BUY),
    }


def decide_action(
    probs: Sequence[float], buy_threshold: float, sell_threshold: float, min_margin: float
) -> int | None:
    """Return BUY/SELL decision, HOLD/no-trade as None, ambiguous as -1."""
    sell_p, hold_p, buy_p = float(probs[0]), float(probs[1]), float(probs[2])
    buy_ok = (
        buy_p >= buy_threshold and buy_p - sell_p >= min_margin and buy_p - hold_p >= min_margin
    )
    sell_ok = (
        sell_p >= sell_threshold and sell_p - buy_p >= min_margin and sell_p - hold_p >= min_margin
    )
    if buy_ok and sell_ok:
        return -1
    if buy_ok:
        return CLASS_BUY
    if sell_ok:
        return CLASS_SELL
    return None


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def calibrate_grid(
    y_true: Sequence[int],
    probabilities: Sequence[Sequence[float]],
    threshold_values: Sequence[float],
    min_margin: float,
    min_trades: int,
    precision_floor: float,
) -> list[ThresholdRow]:
    actual_buy = sum(1 for value in y_true if value == CLASS_BUY)
    actual_sell = sum(1 for value in y_true if value == CLASS_SELL)
    actual_actions = actual_buy + actual_sell
    rows: list[ThresholdRow] = []
    for buy_th in threshold_values:
        for sell_th in threshold_values:
            buy_trades = sell_trades = buy_correct = sell_correct = 0
            false_positive = ambiguous = no_trade = 0
            for actual, probs in zip(y_true, probabilities, strict=True):
                decision = decide_action(probs, buy_th, sell_th, min_margin)
                if decision == -1:
                    ambiguous += 1
                    no_trade += 1
                    continue
                if decision is None:
                    no_trade += 1
                    continue
                if decision == CLASS_BUY:
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
            buy_precision = safe_div(buy_correct, buy_trades)
            sell_precision = safe_div(sell_correct, sell_trades)
            action_recall = safe_div(correct, actual_actions)
            buy_recall = safe_div(buy_correct, actual_buy)
            sell_recall = safe_div(sell_correct, actual_sell)
            action_f1 = (
                2 * action_precision * action_recall / (action_precision + action_recall)
                if action_precision + action_recall
                else 0.0
            )
            score = action_f1
            if trades < min_trades or action_precision < precision_floor:
                score = -1.0
            rows.append(
                ThresholdRow(
                    buy_threshold=buy_th,
                    sell_threshold=sell_th,
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
                    action_precision=action_precision,
                    buy_precision=buy_precision,
                    sell_precision=sell_precision,
                    action_recall=action_recall,
                    buy_recall=buy_recall,
                    sell_recall=sell_recall,
                    action_f1=action_f1,
                    coverage=safe_div(trades, len(y_true)),
                    score=score,
                )
            )
    return rows


def select_best(rows: Sequence[ThresholdRow]) -> ThresholdRow | None:
    if not rows:
        return None
    valid = [row for row in rows if row.score >= 0]
    pool = valid if valid else list(rows)
    return max(pool, key=lambda row: (row.score, row.action_precision, row.trades))


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    from ShadBotTrader.data_cli import build_service
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.account import AccountProfileStore
    from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol, stored_symbols

    _, store, _ = build_service(storage_root)
    try:
        profile = AccountProfileStore().active()
    except Exception:
        profile = None
    resolved = resolve_stored_symbol(store, symbol, timeframe, profile)
    if not resolved.found:
        raise FileNotFoundError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    if resolved.is_alias:
        print(f"  [i] {resolved.note}")
    return store.query(Symbol(resolved.resolved), Timeframe(timeframe))


def build_training_service() -> Any:
    from ShadBotTrader.application.services.dual_model_service import DualModelService
    from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
    from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

    return DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )


def selected_positions(
    args: argparse.Namespace, dataset: Any, role: Any, candle_count: int
) -> tuple[str, list[int]]:
    sample_ends = list(dataset.sample_ends or [])
    scope = choose_scope(args.scope, float(args.train_ratio))
    if scope == "all":
        positions = list(range(len(sample_ends)))
    elif scope == "holdout":
        if not 0 < float(args.train_ratio) < 100:
            raise ValueError("holdout scope requires --train-ratio in (0,100)")
        cutoff = int(candle_count * float(args.train_ratio) / 100.0)
        dropped = int(getattr(dataset, "dropped_warmup", 0) or 0)
        positions = [pos for pos, end in enumerate(sample_ends) if end + dropped >= cutoff]
    else:
        from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split

        rows = len(sample_ends)
        val_size = int(args.val_size) if int(args.val_size) > 0 else max(4, min(2000, rows // 10))
        step = max(1, val_size)
        min_train_size = max(8, min(rows // 4, 20 * role.window_size))
        purge_gap = max(role.window_size - 1, 0)
        val_size = max(4, min(val_size, rows - min_train_size - purge_gap - 4))
        plan = expanding_split(
            total_length=rows,
            val_size=val_size,
            step=step,
            min_train_size=min_train_size,
            purge_gap=purge_gap,
            sample_end_indices=dataset.sample_ends,
            label_end_indices=dataset.sample_label_ends,
            window_size=role.window_size,
        )
        folds = list(plan.folds)
        if int(args.folds) > 0:
            folds = folds[-int(args.folds) :]
        if not folds:
            positions = []
        else:
            last = folds[-1]
            positions = list(range(last.val_start, last.val_end))
    sampled = select_sample_positions(len(positions), int(args.max_windows))
    return scope, [positions[index] for index in sampled]


def predict_probabilities(
    args: argparse.Namespace, role: Any, dataset: Any, positions: Sequence[int]
):
    import numpy as np

    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window
    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
    from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _deserialize_model

    model_id = args.model_id.strip() or f"gold_trend_signal_{args.timeframe.strip().lower()}"
    catalogue = ModelCatalogue(args.storage_root)
    version = int(args.model_version) or catalogue.latest_version(model_id)
    if not version:
        raise FileNotFoundError(f"No saved model found for {model_id}")
    record = catalogue.read(model_id, version)
    artifact = FilesystemArtifactStore(args.storage_root).load(
        ModelId(model_id), ModelVersion(version)
    )
    if record is None or artifact is None:
        raise FileNotFoundError(f"Missing record/artifact for {model_id} v{version}")
    model = _deserialize_model(artifact.payload)
    expected = getattr(model, "input_shape", None)
    if expected is not None and len(expected) == 3:
        exp_window, exp_features = expected[1], expected[2]
        if exp_window is not None and int(exp_window) != int(role.window_size):
            raise ValueError(
                f"model expects window={exp_window}, but calibration uses window={role.window_size}"
            )
        if exp_features is not None and int(exp_features) != int(dataset.feature_count):
            raise ValueError(
                f"model expects {exp_features} features, matrix has {dataset.feature_count}"
            )

    sample_ends = list(dataset.sample_ends or [])
    target_col = dataset.target_columns[0]
    labels: list[int] = []
    probs: list[list[float]] = []
    batch_rows: list[list[list[float]]] = []
    batch_labels: list[int] = []
    batch_size = max(1, int(args.batch))
    scale_range = getattr(role, "input_scale_range", (-2.0, 2.0))

    def flush() -> None:
        if not batch_rows:
            return
        x = np.array(batch_rows, dtype=np.float32)
        raw = np.asarray(model.predict(x, verbose=0))
        if raw.ndim == 3:
            raw = raw[:, -1, :]
        if raw.ndim != 2 or raw.shape[1] != 3:
            raise ValueError(f"unexpected model output shape {raw.shape}; expected [batch,3]")
        for row in raw:
            total = float(np.sum(row))
            probs.append([float(v) / total for v in row] if total > 0 else [0.0, 0.0, 0.0])
        labels.extend(batch_labels)
        batch_rows.clear()
        batch_labels.clear()

    for pos in positions:
        end = sample_ends[pos]
        window = [
            row[: dataset.feature_count]
            for row in dataset.series[end - role.window_size + 1 : end + 1]
        ]
        batch_rows.append(minmax_scale_window(window, scale_range))
        batch_labels.append(int(round(dataset.series[end][target_col])))
        if len(batch_rows) >= batch_size:
            flush()
    flush()
    return model_id, version, record, labels, probs


def write_csv(path: Path, rows: Sequence[ThresholdRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict().keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def colour(value: float) -> str:
    value = max(0.0, min(1.0, value))
    red = int(255 * (1.0 - value))
    green = int(180 * value)
    return f"rgb({red},{green},80)"


def write_heatmap(
    path: Path, rows: Sequence[ThresholdRow], threshold_values: Sequence[float]
) -> None:
    by_pair = {(row.buy_threshold, row.sell_threshold): row for row in rows}
    table = []
    for buy_th in threshold_values:
        cells = [f"<th>{buy_th:.2f}</th>"]
        for sell_th in threshold_values:
            row = by_pair.get((buy_th, sell_th))
            if row is None:
                cells.append("<td>n/a</td>")
                continue
            cells.append(
                "<td style='background:%s' title='trades=%s precision=%.3f recall=%.3f'>"
                "%.3f<br><small>%s trades</small></td>"
                % (
                    colour(row.action_f1),
                    row.trades,
                    row.action_precision,
                    row.action_recall,
                    row.action_f1,
                    row.trades,
                )
            )
        table.append("<tr>" + "".join(cells) + "</tr>")
    header = (
        "<tr><th>BUY\\SELL</th>" + "".join(f"<th>{v:.2f}</th>" for v in threshold_values) + "</tr>"
    )
    html = f"""<!doctype html>
<html lang="fa" dir="rtl"><meta charset="utf-8">
<title>trend_signal threshold heatmap</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;background:#111;color:#eee}}
table{{border-collapse:collapse;direction:ltr}}
th,td{{border:1px solid #555;padding:6px;text-align:center;font-size:12px}}
th{{background:#222;color:#fff}}
small{{color:#111}}
</style>
<h1>trend_signal threshold heatmap</h1>
<p>هر سلول action_f1 را نشان می‌دهد؛ داخل tooltip تعداد trade، precision و recall هست.</p>
<table>{header}{''.join(table)}</table>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def save_record_thresholds(
    record: Any, catalogue: Any, best: ThresholdRow, metadata: dict[str, Any]
) -> Path:
    record.decision_thresholds = {
        "buy_prob": best.buy_threshold,
        "sell_prob": best.sell_threshold,
        "min_margin": best.min_margin,
        "selected_by": "phase109_label_grid_action_f1",
        "action_precision": best.action_precision,
        "action_recall": best.action_recall,
        "action_f1": best.action_f1,
        "coverage": best.coverage,
        "trades": best.trades,
        "samples": best.samples,
        "metadata": metadata,
    }
    return catalogue.write(record)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    args.storage_root = str(storage_root)

    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue
    from ShadBotTrader.infrastructure.ai.model_roles import trend_signal_model_role

    symbol = args.symbol.strip().upper()
    timeframe = args.timeframe.strip().upper()
    role = trend_signal_model_role(
        timeframe=timeframe,
        threshold=float(args.atr_mult),
        window_size=max(int(args.window), 2),
        label_horizon=max(int(args.label_horizon), 1),
    )

    print("=== ShadBotTrader — Phase 109 trend_signal threshold calibration ===")
    print(f"symbol {symbol} | timeframe {timeframe} | window {role.window_size}")
    print(f"horizon {role.label_horizon} | barrier {role.target.threshold:.3f}")

    candles = load_candles(storage_root, symbol, timeframe)
    dataset = build_training_service().prepare(candles, Symbol(symbol), Timeframe(timeframe), role)
    scope, positions = selected_positions(args, dataset, role, candle_count=len(candles))
    if not positions:
        print("\n  [X] No labelled windows selected for calibration.")
        return 1
    print(f"selected scope: {scope} | windows: {len(positions):,}")

    try:
        model_id, version, record, y_true, probabilities = predict_probabilities(
            args, role, dataset, positions
        )
    except Exception as error:
        print(f"\n  [X] Cannot score model: {type(error).__name__}: {error}")
        return 1

    thresholds = frange(
        float(args.threshold_min), float(args.threshold_max), float(args.threshold_step)
    )
    rows = calibrate_grid(
        y_true,
        probabilities,
        thresholds,
        min_margin=max(float(args.min_margin), 0.0),
        min_trades=max(int(args.min_trades), 0),
        precision_floor=max(float(args.precision_floor), 0.0),
    )
    best = select_best(rows)
    if best is None:
        print("\n  [X] Threshold grid produced no rows.")
        return 1

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{model_id}_v{version}_{scope}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    csv_path = output_dir / f"{stem}.csv"
    html_path = output_dir / f"{stem}.html"
    json_path = output_dir / f"{stem}.json"
    latest_json = output_dir / "latest.json"
    latest_html = output_dir / "latest.html"
    latest_csv = output_dir / "latest.csv"

    write_csv(csv_path, rows)
    write_csv(latest_csv, rows)
    write_heatmap(html_path, rows, thresholds)
    write_heatmap(latest_html, rows, thresholds)

    metadata = {
        "symbol": symbol,
        "timeframe": timeframe,
        "model_id": model_id,
        "version": version,
        "window": role.window_size,
        "label_horizon": role.label_horizon,
        "atr_mult": role.target.threshold,
        "scope": scope,
        "train_ratio": float(args.train_ratio),
        "class_counts": class_counts(y_true),
        "threshold_values": thresholds,
        "min_trades": int(args.min_trades),
        "precision_floor": float(args.precision_floor),
        "csv": str(csv_path),
        "html": str(html_path),
    }
    payload = {"metadata": metadata, "best": best.to_dict()}
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    latest_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    rule("BEST THRESHOLDS")
    print(f"  model      : {model_id} v{version}")
    print(f"  scope      : {scope} ({len(y_true):,} windows) classes={class_counts(y_true)}")
    print(f"  BUY prob   : {best.buy_threshold:.2f}")
    print(f"  SELL prob  : {best.sell_threshold:.2f}")
    print(f"  min margin : {best.min_margin:.2f}")
    print(f"  trades     : {best.trades:,} ({best.coverage:.1%} coverage)")
    print(
        f"  precision  : action {best.action_precision:.1%} | "
        f"BUY {best.buy_precision:.1%} | SELL {best.sell_precision:.1%}"
    )
    print(
        f"  recall     : action {best.action_recall:.1%} | "
        f"BUY {best.buy_recall:.1%} | SELL {best.sell_recall:.1%}"
    )
    print(f"  action F1  : {best.action_f1:.4f}")
    print(f"  files      : {csv_path}")
    print(f"             : {html_path}")

    if args.save_record == "1":
        record_path = save_record_thresholds(record, ModelCatalogue(storage_root), best, metadata)
        print(f"  record     : thresholds saved to {record_path}")
    else:
        print("  record     : not modified (--save-record=0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
