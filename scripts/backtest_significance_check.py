"""Phase 113 significance checks for the hybrid-head range backtest.

This script does not change the trading rule. It reloads the Phase 124 hybrid
head, applies one already-selected Phase 125 threshold pair, then compares that
observed PnL against random entries that use the same evaluation slice, same
range TP/SL construction, same spread/slippage policy, and the same BUY/SELL
trade counts.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import json
import sys
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
import pandas as pd
from backtest_hybrid_xgboost_head import (
    CLASS_BUY,
    CLASS_SELL,
    BacktestRow,
    TradeResult,
    aligned_predict_proba,
    default_matrix_path,
    eval_slice_indices,
    evaluate_thresholds,
    load_candles,
    load_head,
    max_drawdown,
    range_filter_pass,
    safe_div,
    simulate_trade,
)

from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_BACKTEST_LOG = Path("run_logs/hybrid_head_backtest/latest.json")
DEFAULT_OUTPUT_DIR = Path("run_logs/significance_checks")


@dataclass(frozen=True)
class ThresholdSpec:
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    source: str


@dataclass(frozen=True)
class TrialResult:
    trial: int
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    timeouts: int
    label_correct: int
    false_positive: int
    win_rate: float
    label_precision: float
    total_pnl: float
    avg_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    white_max_total_pnl: float


@dataclass(frozen=True)
class DistributionStats:
    trials: int
    mean: float
    stdev: float
    minimum: float
    p05: float
    p50: float
    p95: float
    p99: float
    maximum: float
    probability_positive: float
    better_or_equal_observed: int
    p_value: float


@dataclass(frozen=True)
class CandidateProfile:
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    trades: int
    buy_trades: int
    sell_trades: int
    observed_total_pnl: float
    observed_profit_factor: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monte Carlo random baseline for Phase 125 hybrid-head TP/SL backtest.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--eval-frac", type=float, default=0.30)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--min-trades", type=int, default=0)
    parser.add_argument("--precision-floor", type=float, default=0.0)
    parser.add_argument("--min-profit-factor", type=float, default=0.0)
    parser.add_argument("--score-metric", default="total_pnl")
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-4h-room", type=float, default=2.0)
    parser.add_argument("--min-1d-room", type=float, default=5.0)
    parser.add_argument("--min-tp-distance", type=float, default=2.0)
    parser.add_argument("--min-sl-distance", type=float, default=2.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--max-windows", type=int, default=0, help="0 = all eval rows")
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--white-check",
        choices=("0", "1"),
        default="1",
        help="Use Phase 125 candidate rows to approximate a White Reality-style max test.",
    )
    parser.add_argument(
        "--candidate-rows-path",
        default=str(DEFAULT_BACKTEST_LOG),
        help="Phase 125 JSON containing the searched threshold rows.",
    )
    parser.add_argument(
        "--white-max-candidates",
        type=int,
        default=0,
        help="0 = all valid candidates; otherwise keep top observed-PnL candidates.",
    )
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def read_thresholds_from_record(
    storage_root: Path,
    model_id: str,
    model_version: int,
) -> ThresholdSpec | None:
    catalogue = ModelCatalogue(storage_root)
    version = model_version if model_version > 0 else catalogue.latest_version(model_id)
    if version < 1:
        return None
    record = catalogue.read(model_id, version)
    if record is None:
        return None
    thresholds = record.decision_thresholds or {}
    buy = _finite_or_none(thresholds.get("buy_prob"))
    sell = _finite_or_none(thresholds.get("sell_prob"))
    margin = _finite_or_none(thresholds.get("min_margin"))
    if buy is None or sell is None:
        return None
    return ThresholdSpec(
        buy_threshold=buy,
        sell_threshold=sell,
        min_margin=max(0.0, margin or 0.0),
        source=f"model_record:{model_id}:v{version}",
    )


def read_thresholds_from_backtest(path: Path) -> ThresholdSpec | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    best = payload.get("best") or {}
    buy = _finite_or_none(best.get("buy_threshold"))
    sell = _finite_or_none(best.get("sell_threshold"))
    margin = _finite_or_none(best.get("min_margin"))
    if buy is None or sell is None:
        return None
    return ThresholdSpec(
        buy_threshold=buy,
        sell_threshold=sell,
        min_margin=max(0.0, margin or 0.0),
        source=f"phase125_json:{path}",
    )


def resolve_thresholds(args: argparse.Namespace, storage_root: Path) -> ThresholdSpec:
    buy = _finite_or_none(args.buy_threshold)
    sell = _finite_or_none(args.sell_threshold)
    margin = _finite_or_none(args.min_margin)
    if buy is not None and sell is not None and buy >= 0 and sell >= 0:
        return ThresholdSpec(
            buy_threshold=buy,
            sell_threshold=sell,
            min_margin=max(0.0, margin or 0.0),
            source="cli",
        )

    record_thresholds = read_thresholds_from_record(
        storage_root, args.model_id, int(args.model_version)
    )
    if record_thresholds is not None:
        return record_thresholds

    backtest_thresholds = read_thresholds_from_backtest(Path(args.candidate_rows_path))
    if backtest_thresholds is not None:
        return backtest_thresholds

    raise RuntimeError(
        "No thresholds supplied and no saved decision_thresholds were found. "
        "Pass --buy-threshold, --sell-threshold and --min-margin, or run Phase 125 "
        "with --save-record 1 first."
    )


def build_trade_pool(
    frame: pd.DataFrame,
    candles: Sequence[Any],
    args: argparse.Namespace,
) -> dict[int, list[TradeResult]]:
    pools: dict[int, list[TradeResult]] = {CLASS_BUY: [], CLASS_SELL: []}
    for _, row in frame.iterrows():
        for side in (CLASS_BUY, CLASS_SELL):
            if not range_filter_pass(row, side, args.min_4h_room, args.min_1d_room):
                continue
            trade = simulate_trade(row, side, candles, args)
            if trade is not None:
                pools[side].append(trade)
    return pools


def summarise_trades(trial: int, trades: Sequence[TradeResult], white_max: float) -> TrialResult:
    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    timeouts = sum(1 for trade in trades if trade.outcome == "timeout")
    label_correct = sum(1 for trade in trades if trade.label_correct)
    buy_trades = sum(1 for trade in trades if trade.side == "BUY")
    sell_trades = sum(1 for trade in trades if trade.side == "SELL")
    total_pnl = sum(pnls)
    return TrialResult(
        trial=trial,
        trades=len(trades),
        buy_trades=buy_trades,
        sell_trades=sell_trades,
        wins=wins,
        losses=losses,
        timeouts=timeouts,
        label_correct=label_correct,
        false_positive=len(trades) - label_correct,
        win_rate=safe_div(wins, len(trades)),
        label_precision=safe_div(label_correct, len(trades)),
        total_pnl=total_pnl,
        avg_pnl=safe_div(total_pnl, len(trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=max_drawdown(pnls),
        white_max_total_pnl=white_max,
    )


def _sample_without_overlap(
    rng: np.random.Generator,
    first_pool: Sequence[TradeResult],
    first_count: int,
    second_pool: Sequence[TradeResult],
    second_count: int,
) -> list[TradeResult] | None:
    if len(first_pool) < first_count:
        return None
    first_indices = (
        rng.choice(len(first_pool), size=first_count, replace=False) if first_count else []
    )
    first = [first_pool[int(index)] for index in first_indices]
    blocked_rows = {trade.row_index for trade in first}
    second_candidates = [
        index for index, trade in enumerate(second_pool) if trade.row_index not in blocked_rows
    ]
    if len(second_candidates) < second_count:
        return None
    second_indices = (
        rng.choice(second_candidates, size=second_count, replace=False) if second_count else []
    )
    second = [second_pool[int(index)] for index in second_indices]
    return [*first, *second]


def sample_random_trades(
    rng: np.random.Generator,
    pools: dict[int, Sequence[TradeResult]],
    buy_count: int,
    sell_count: int,
) -> list[TradeResult]:
    buy_pool = pools[CLASS_BUY]
    sell_pool = pools[CLASS_SELL]
    if len(buy_pool) < buy_count or len(sell_pool) < sell_count:
        raise RuntimeError(
            "Not enough eligible random trade candidates for the model side counts: "
            f"need BUY/SELL {buy_count}/{sell_count}, "
            f"have {len(buy_pool)}/{len(sell_pool)}."
        )

    buy_slack = len(buy_pool) - buy_count
    sell_slack = len(sell_pool) - sell_count
    if buy_slack <= sell_slack:
        sampled = _sample_without_overlap(rng, buy_pool, buy_count, sell_pool, sell_count)
        if sampled is not None:
            return sampled
        sampled = _sample_without_overlap(rng, sell_pool, sell_count, buy_pool, buy_count)
    else:
        sampled = _sample_without_overlap(rng, sell_pool, sell_count, buy_pool, buy_count)
        if sampled is not None:
            return sampled
        sampled = _sample_without_overlap(rng, buy_pool, buy_count, sell_pool, sell_count)
    if sampled is None:
        raise RuntimeError(
            "Could not sample random BUY/SELL trades without duplicate entry bars. "
            "Reduce side-count matching or verify the range filters."
        )
    return sampled


def distribution_stats(values: Sequence[float], observed: float) -> DistributionStats:
    if not values:
        return DistributionStats(
            trials=0,
            mean=0.0,
            stdev=0.0,
            minimum=0.0,
            p05=0.0,
            p50=0.0,
            p95=0.0,
            p99=0.0,
            maximum=0.0,
            probability_positive=0.0,
            better_or_equal_observed=0,
            p_value=1.0,
        )
    array = np.asarray(values, dtype=np.float64)
    better = int(np.sum(array >= observed))
    return DistributionStats(
        trials=int(len(array)),
        mean=float(np.mean(array)),
        stdev=float(np.std(array, ddof=1)) if len(array) > 1 else 0.0,
        minimum=float(np.min(array)),
        p05=float(np.quantile(array, 0.05)),
        p50=float(np.quantile(array, 0.50)),
        p95=float(np.quantile(array, 0.95)),
        p99=float(np.quantile(array, 0.99)),
        maximum=float(np.max(array)),
        probability_positive=float(np.mean(array > 0.0)),
        better_or_equal_observed=better,
        p_value=float((better + 1) / (len(array) + 1)),
    )


def load_candidate_profiles(path: Path, max_candidates: int) -> list[CandidateProfile]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    rows = payload.get("rows") or []
    profiles: list[CandidateProfile] = []
    seen: set[tuple[float, float, float, int, int]] = set()
    for row in rows:
        score = _finite_or_none(row.get("score"))
        trades = int(row.get("trades") or 0)
        buy_trades = int(row.get("buy_trades") or 0)
        sell_trades = int(row.get("sell_trades") or 0)
        if score is None or score < 0 or trades <= 0:
            continue
        key = (
            float(row.get("buy_threshold") or 0.0),
            float(row.get("sell_threshold") or 0.0),
            float(row.get("min_margin") or 0.0),
            buy_trades,
            sell_trades,
        )
        if key in seen:
            continue
        seen.add(key)
        profiles.append(
            CandidateProfile(
                buy_threshold=key[0],
                sell_threshold=key[1],
                min_margin=key[2],
                trades=trades,
                buy_trades=buy_trades,
                sell_trades=sell_trades,
                observed_total_pnl=float(row.get("total_pnl") or 0.0),
                observed_profit_factor=float(row.get("profit_factor") or 0.0),
            )
        )
    profiles.sort(key=lambda item: item.observed_total_pnl, reverse=True)
    if max_candidates > 0:
        profiles = profiles[:max_candidates]
    return profiles


def run_random_trials(
    pools: dict[int, Sequence[TradeResult]],
    observed: BacktestRow,
    profiles: Sequence[CandidateProfile],
    trials: int,
    seed: int,
) -> list[TrialResult]:
    rng = np.random.default_rng(seed)
    results: list[TrialResult] = []
    for trial in range(1, trials + 1):
        model_random = sample_random_trades(
            rng,
            pools,
            observed.buy_trades,
            observed.sell_trades,
        )
        white_max = float("nan")
        if profiles:
            profile_totals: list[float] = []
            for profile in profiles:
                sampled = sample_random_trades(
                    rng,
                    pools,
                    profile.buy_trades,
                    profile.sell_trades,
                )
                profile_totals.append(sum(trade.pnl for trade in sampled))
            white_max = max(profile_totals) if profile_totals else float("nan")
        results.append(summarise_trades(trial, model_random, white_max))
    return results


def write_trials_csv(path: Path, rows: Sequence[TrialResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    matrix_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else default_matrix_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE 113 HYBRID SIGNIFICANCE CHECK")
        print(f"  matrix      : {matrix_path}")
        print(f"  model       : {args.model_id}")
        print(f"  trials      : {max(args.trials, 1):,}")

        thresholds = resolve_thresholds(args, storage_root)
        args.min_margin = thresholds.min_margin
        print(
            "  thresholds  : "
            f"buy={thresholds.buy_threshold:.3f} "
            f"sell={thresholds.sell_threshold:.3f} "
            f"margin={thresholds.min_margin:.3f} ({thresholds.source})"
        )

        model, features, version = load_head(storage_root, args.model_id, args.model_version)
        full_frame = pd.read_parquet(matrix_path)
        indices = eval_slice_indices(len(full_frame), args.eval_frac, args.max_windows)
        frame = full_frame.iloc[indices].copy()
        missing = [name for name in features if name not in frame.columns]
        if missing:
            raise RuntimeError(f"Hybrid matrix is missing model feature columns: {missing[:5]}")
        x_values = (
            frame[features].replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=np.float32)
        )
        probabilities = aligned_predict_proba(model, x_values)
        candles = load_candles(storage_root, args.symbol, args.timeframe)
        observed = evaluate_thresholds(
            frame,
            probabilities,
            candles,
            args,
            thresholds.buy_threshold,
            thresholds.sell_threshold,
        )
        if observed.trades <= 0:
            raise RuntimeError("Selected thresholds produced zero executable trades.")

        pools = build_trade_pool(frame, candles, args)
        profiles: list[CandidateProfile] = []
        if args.white_check == "1":
            profiles = load_candidate_profiles(
                Path(args.candidate_rows_path), max(args.white_max_candidates, 0)
            )
        if profiles and not any(
            profile.buy_trades == observed.buy_trades
            and profile.sell_trades == observed.sell_trades
            for profile in profiles
        ):
            profiles.insert(
                0,
                CandidateProfile(
                    buy_threshold=observed.buy_threshold,
                    sell_threshold=observed.sell_threshold,
                    min_margin=observed.min_margin,
                    trades=observed.trades,
                    buy_trades=observed.buy_trades,
                    sell_trades=observed.sell_trades,
                    observed_total_pnl=observed.total_pnl,
                    observed_profit_factor=observed.profit_factor,
                ),
            )

        trials = run_random_trials(
            pools,
            observed,
            profiles,
            max(args.trials, 1),
            int(args.seed),
        )
        random_pnls = [trial.total_pnl for trial in trials]
        random_stats = distribution_stats(random_pnls, observed.total_pnl)
        white_values = [
            trial.white_max_total_pnl for trial in trials if np.isfinite(trial.white_max_total_pnl)
        ]
        white_stats = distribution_stats(white_values, observed.total_pnl) if white_values else None

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        write_trials_csv(csv_path, trials)
        files = {"csv": str(csv_path), "json": str(json_path)}
        payload = {
            "args": vars(args),
            "model_version": version,
            "matrix_rows": len(full_frame),
            "eval_rows": len(frame),
            "thresholds": asdict(thresholds),
            "observed": asdict(observed),
            "trade_pool": {
                "buy_candidates": len(pools[CLASS_BUY]),
                "sell_candidates": len(pools[CLASS_SELL]),
            },
            "random_baseline": asdict(random_stats),
            "white_reality_style": asdict(white_stats) if white_stats else None,
            "white_candidate_count": len(profiles),
            "white_candidates": [asdict(profile) for profile in profiles],
            "files": files,
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        rule("SIGNIFICANCE RESULT")
        print(
            "  observed    : "
            f"pnl={observed.total_pnl:.2f} pf={observed.profit_factor:.3f} "
            f"trades={observed.trades:,} buy/sell={observed.buy_trades}/{observed.sell_trades}"
        )
        print(
            "  random pnl  : "
            f"mean={random_stats.mean:.2f} p95={random_stats.p95:.2f} "
            f"p99={random_stats.p99:.2f} max={random_stats.maximum:.2f}"
        )
        print(f"  p-value     : {random_stats.p_value:.4f} (random >= observed total_pnl)")
        if white_stats is not None:
            print(
                "  white-style : "
                f"candidates={len(profiles)} p95={white_stats.p95:.2f} "
                f"p99={white_stats.p99:.2f} p-value={white_stats.p_value:.4f}"
            )
        else:
            print("  white-style : skipped (no valid Phase 125 candidate rows found)")
        print(f"  report      : {json_path}")
        print(f"  trials csv  : {csv_path}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
