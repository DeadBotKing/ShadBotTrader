"""Phase164A: 1H spread-unit / bracket-cost sensitivity audit.

Phase163A found that 1H pivot rules have raw no-spread signal, but the route
failed under the current ``spread=0.06%`` assumption. This phase does not train
models. It audits whether the failure is caused by an overly pessimistic or
wrong-unit spread assumption and whether wider 1H brackets can survive costs.

Research-only. No paper/live/production gate is opened by this script.
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
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_pivot_1h_entry_feasibility import (  # noqa: E402
    DEFAULT_STORAGE,
    build_zone_masks,
    parse_float_grid,
    parse_int_grid,
    read_ohlc_frame,
    resolve_flat_path_arg,
    simulate_policy_split,
    spread_atr_for_split,
)
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_1h_spread_bracket_sensitivity")
DEFAULT_POLICIES = (
    "BRK_D1_FAST:breakout:1:24:0.05:0.85:0.15:1:1.0:0;"
    "BRK_D0_MID:breakout:0:24:0.10:0.85:0.15:1:1.0:0;"
    "BRK_D0_WIDE:breakout:0:48:0.10:0.85:0.15:1:1.0:0;"
    "BB_D1_WIDE:bottom_buy:1:24:0.15:0.85:0.15:1:1.0:0"
)
DEFAULT_BRACKETS = "B15_10:1.5:1.0;B20_10:2.0:1.0;B25_125:2.5:1.25;B30_15:3.0:1.5"


@dataclass(frozen=True)
class CandidatePolicySpec:
    policy_key: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float


@dataclass(frozen=True)
class BracketSpec:
    bracket_id: str
    tp_atr: float
    sl_atr: float


@dataclass(frozen=True)
class SensitivityRow:
    config_id: str
    policy_key: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    bracket_id: str
    tp_atr: float
    sl_atr: float
    hold_bars: int
    spread_mode: str
    spread_value: float
    train_trades: int
    train_profit_factor: float
    train_total_cash_pnl: float
    train_final_balance: float
    validation_trades: int
    validation_candidate_event_rate: float
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_final_balance: float
    validation_independent_mean_atr: float
    validation_skipped_winners: int
    validation_skipped_losers: int
    test_trades: int
    test_candidate_event_rate: float
    test_profit_factor: float
    test_total_cash_pnl: float
    test_final_balance: float
    test_independent_mean_atr: float
    test_skipped_winners: int
    test_skipped_losers: int
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    validation_score: float
    warnings: str


@dataclass(frozen=True)
class BreakEvenRow:
    group_id: str
    policy_key: str
    side_mapping: str
    entry_delay_bars: int
    bracket_id: str
    tp_atr: float
    sl_atr: float
    hold_bars: int
    spread_mode: str
    tested_spreads: str
    zero_validation_profit_factor: float
    zero_test_profit_factor: float
    zero_validation_total_cash_pnl: float
    zero_test_total_cash_pnl: float
    max_validation_nonnegative_spread: float
    max_test_nonnegative_spread: float
    max_both_nonnegative_spread: float
    max_validation_pass_spread: float
    max_test_pass_spread: float
    max_transfer_pass_spread: float
    first_validation_negative_spread: float
    first_test_negative_spread: float
    first_transfer_fail_spread: float
    best_validation_spread: float
    best_validation_score: float
    best_validation_test_profit_factor: float
    best_validation_test_total_cash_pnl: float


@dataclass(frozen=True)
class Phase164Report:
    symbol: str
    timeframe: str
    flat_path: str
    flat_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    candidate_policies: int
    brackets: int
    hold_bars_grid: list[int]
    fixed_spreads: list[float]
    pct_spreads: list[float]
    evaluated_configs: int
    validation_pass_configs: int
    transfer_pass_configs: int
    fixed_transfer_pass_configs: int
    pct_transfer_pass_configs: int
    selected_config_id: str
    selected_policy_key: str
    selected_spread_mode: str
    selected_spread_value: float
    selected_bracket_id: str
    selected_tp_atr: float
    selected_sl_atr: float
    selected_hold_bars: int
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_validation_total_cash_pnl: float
    selected_test_total_cash_pnl: float
    selected_transfer_pass_gate: int
    route_feasible_gate: int
    top_config_rows: list[dict[str, Any]]
    break_even_rows_preview: list[dict[str, Any]]
    spread_atr_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_grid_csv: str
    output_split_replay_csv: str
    output_break_even_csv: str
    output_spread_atr_csv: str
    output_monthly_csv: str
    production_status: str


def safe_slug(text: str) -> str:
    cleaned: list[str] = []
    for char in str(text).strip():
        if char.isalnum():
            cleaned.append(char)
        elif char in {"-", "_", " ", ".", ":"}:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "item"


def parse_candidate_policies(text: str) -> list[CandidatePolicySpec]:
    policies: list[CandidatePolicySpec] = []
    for raw in str(text or "").split(";"):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 10:
            raise RuntimeError(
                "candidate policy format must be "
                "ID:mapping:delay:rw:zone:top:bottom:exclude:minw:maxw"
            )
        policies.append(
            CandidatePolicySpec(
                policy_key=safe_slug(parts[0]),
                side_mapping=parts[1],
                entry_delay_bars=max(int(parts[2]), 0),
                recent_window_bars=max(int(parts[3]), 1),
                pivot_zone_atr=max(float(parts[4]), 0.0),
                top_position_threshold=float(parts[5]),
                bottom_position_threshold=float(parts[6]),
                exclude_both_zones=1 if str(parts[7]).strip() != "0" else 0,
                min_range_width_atr=max(float(parts[8]), 0.0),
                max_range_width_atr=max(float(parts[9]), 0.0),
            )
        )
    if not policies:
        raise RuntimeError("At least one candidate policy is required")
    return policies


def parse_brackets(text: str) -> list[BracketSpec]:
    brackets: list[BracketSpec] = []
    for raw in str(text or "").split(";"):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 3:
            raise RuntimeError("bracket format must be ID:tp_atr:sl_atr")
        brackets.append(
            BracketSpec(
                bracket_id=safe_slug(parts[0]),
                tp_atr=max(float(parts[1]), 0.01),
                sl_atr=max(float(parts[2]), 0.01),
            )
        )
    if not brackets:
        raise RuntimeError("At least one bracket is required")
    return brackets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit 1H spread-unit and bracket-cost sensitivity before model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=24)
    parser.add_argument("--candidate-policies", default=DEFAULT_POLICIES)
    parser.add_argument("--brackets", default=DEFAULT_BRACKETS)
    parser.add_argument("--hold-bars-grid", default="24,48")
    parser.add_argument("--fixed-spreads", default="0,0.2,0.5,1.0,1.5,2.0")
    parser.add_argument("--pct-spreads", default="0,0.01,0.02,0.03,0.06")
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--max-median-spread-atr", type=float, default=0.12)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--validation-min-trades", type=int, default=10)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-trades", type=int, default=10)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--max-validation-event-rate", type=float, default=0.35)
    parser.add_argument("--max-test-event-rate", type=float, default=0.35)
    parser.add_argument("--score-metric", choices=("cash_pnl", "profit_factor", "independent_mean_atr"), default="cash_pnl")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase164A 1H spread/bracket cost sensitivity audit")
    return parser.parse_args(argv)


def validation_score(row: SensitivityRow, metric: str) -> float:
    if metric == "profit_factor":
        return float(row.validation_profit_factor)
    if metric == "independent_mean_atr":
        return float(row.validation_independent_mean_atr)
    return float(row.validation_total_cash_pnl)


def summarize_config(
    config_id: str,
    policy: CandidatePolicySpec,
    bracket: BracketSpec,
    hold_bars: int,
    spread_mode: str,
    spread_value: float,
    split_rows: Mapping[str, Any],
    args: argparse.Namespace,
) -> SensitivityRow | None:
    validation = split_rows.get("validation")
    test = split_rows.get("test")
    train = split_rows.get("train")
    if validation is None or test is None:
        return None
    warnings: list[str] = []
    if validation.candidate_event_rate > float(args.max_validation_event_rate):
        warnings.append("validation event rate above max")
    if test.candidate_event_rate > float(args.max_test_event_rate):
        warnings.append("test event rate above max")
    if validation.trades < int(args.validation_min_trades):
        warnings.append("validation trades below minimum")
    if test.trades < int(args.test_min_trades):
        warnings.append("test trades below minimum")
    if validation.profit_factor < float(args.validation_min_profit_factor):
        warnings.append("validation PF below minimum")
    if test.profit_factor < float(args.test_min_profit_factor):
        warnings.append("test PF below minimum")
    seed = SensitivityRow(
        config_id=config_id,
        policy_key=policy.policy_key,
        side_mapping=policy.side_mapping,
        entry_delay_bars=int(policy.entry_delay_bars),
        recent_window_bars=int(policy.recent_window_bars),
        pivot_zone_atr=float(policy.pivot_zone_atr),
        top_position_threshold=float(policy.top_position_threshold),
        bottom_position_threshold=float(policy.bottom_position_threshold),
        exclude_both_zones=int(policy.exclude_both_zones),
        min_range_width_atr=float(policy.min_range_width_atr),
        max_range_width_atr=float(policy.max_range_width_atr),
        bracket_id=bracket.bracket_id,
        tp_atr=float(bracket.tp_atr),
        sl_atr=float(bracket.sl_atr),
        hold_bars=int(hold_bars),
        spread_mode=str(spread_mode),
        spread_value=float(spread_value),
        train_trades=int(train.trades if train else 0),
        train_profit_factor=float(train.profit_factor if train else 0.0),
        train_total_cash_pnl=float(train.total_cash_pnl if train else 0.0),
        train_final_balance=float(train.final_balance if train else 0.0),
        validation_trades=int(validation.trades),
        validation_candidate_event_rate=float(validation.candidate_event_rate),
        validation_profit_factor=float(validation.profit_factor),
        validation_total_cash_pnl=float(validation.total_cash_pnl),
        validation_final_balance=float(validation.final_balance),
        validation_independent_mean_atr=float(validation.independent_mean_atr),
        validation_skipped_winners=int(validation.skipped_winners),
        validation_skipped_losers=int(validation.skipped_losers),
        test_trades=int(test.trades),
        test_candidate_event_rate=float(test.candidate_event_rate),
        test_profit_factor=float(test.profit_factor),
        test_total_cash_pnl=float(test.total_cash_pnl),
        test_final_balance=float(test.final_balance),
        test_independent_mean_atr=float(test.independent_mean_atr),
        test_skipped_winners=int(test.skipped_winners),
        test_skipped_losers=int(test.skipped_losers),
        validation_pass_gate=int(validation.pass_gate),
        test_pass_gate=int(test.pass_gate),
        transfer_pass_gate=int(validation.pass_gate and test.pass_gate),
        validation_score=0.0,
        warnings=json.dumps(warnings, ensure_ascii=False),
    )
    return SensitivityRow(**{**asdict(seed), "validation_score": validation_score(seed, str(args.score_metric))})


def evaluate_grid(args: argparse.Namespace, frame: Any, split_map: Mapping[str, np.ndarray], atr: np.ndarray) -> tuple[list[SensitivityRow], list[dict[str, Any]], list[dict[str, Any]]]:
    policies = parse_candidate_policies(args.candidate_policies)
    brackets = parse_brackets(args.brackets)
    hold_values = parse_int_grid(args.hold_bars_grid, (24, 48))
    spread_specs: list[tuple[str, float]] = []
    spread_specs.extend(("fixed", value) for value in parse_float_grid(args.fixed_spreads, (0.0, 0.2, 0.5, 1.0, 1.5, 2.0)))
    spread_specs.extend(("pct", value) for value in parse_float_grid(args.pct_spreads, (0.0, 0.01, 0.02, 0.03, 0.06)))
    rows: list[SensitivityRow] = []
    split_replay_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    mask_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for policy in policies:
        mask_key = json.dumps(asdict(policy), sort_keys=True)
        if mask_key not in mask_cache:
            top_mask, bottom_mask, _ = build_zone_masks(
                frame,
                atr,
                policy.recent_window_bars,
                policy.pivot_zone_atr,
                policy.top_position_threshold,
                policy.bottom_position_threshold,
                policy.exclude_both_zones,
                policy.min_range_width_atr,
                policy.max_range_width_atr,
            )
            mask_cache[mask_key] = (top_mask, bottom_mask)
        top_mask, bottom_mask = mask_cache[mask_key]
        for bracket in brackets:
            for hold_bars in hold_values:
                for spread_mode, spread_value in spread_specs:
                    config_id = (
                        f"{policy.policy_key}|{policy.side_mapping}|d={policy.entry_delay_bars}|"
                        f"rw={policy.recent_window_bars}|zone={policy.pivot_zone_atr:g}|"
                        f"bracket={bracket.bracket_id}|hold={int(hold_bars)}|"
                        f"spread_mode={spread_mode}|spread={float(spread_value):g}"
                    )
                    run_args = SimpleNamespace(
                        **{
                            **vars(args),
                            "spread_mode": spread_mode,
                            "tp_atr": float(bracket.tp_atr),
                            "sl_atr": float(bracket.sl_atr),
                            "hold_bars": int(hold_bars),
                        }
                    )
                    split_rows: dict[str, Any] = {}
                    for split, idx in split_map.items():
                        split_row, months = simulate_policy_split(
                            config_id,
                            split,
                            frame,
                            idx,
                            top_mask,
                            bottom_mask,
                            atr,
                            policy.side_mapping,
                            policy.entry_delay_bars,
                            policy.recent_window_bars,
                            policy.pivot_zone_atr,
                            policy.top_position_threshold,
                            policy.bottom_position_threshold,
                            policy.exclude_both_zones,
                            policy.min_range_width_atr,
                            policy.max_range_width_atr,
                            float(spread_value),
                            run_args,
                        )
                        split_rows[split] = split_row
                        split_replay_rows.append(asdict(split_row))
                        monthly_rows.extend(months)
                    summary = summarize_config(
                        config_id,
                        policy,
                        bracket,
                        int(hold_bars),
                        spread_mode,
                        float(spread_value),
                        split_rows,
                        args,
                    )
                    if summary is not None:
                        rows.append(summary)
    return rows, split_replay_rows, monthly_rows


def max_spread(rows: Sequence[SensitivityRow], predicate: str) -> float:
    valid: list[float] = []
    for row in rows:
        ok = False
        if predicate == "validation_nonnegative":
            ok = row.validation_total_cash_pnl >= 0
        elif predicate == "test_nonnegative":
            ok = row.test_total_cash_pnl >= 0
        elif predicate == "both_nonnegative":
            ok = row.validation_total_cash_pnl >= 0 and row.test_total_cash_pnl >= 0
        elif predicate == "validation_pass":
            ok = bool(row.validation_pass_gate)
        elif predicate == "test_pass":
            ok = bool(row.test_pass_gate)
        elif predicate == "transfer_pass":
            ok = bool(row.transfer_pass_gate)
        if ok:
            valid.append(float(row.spread_value))
    return max(valid) if valid else -1.0


def first_spread(rows: Sequence[SensitivityRow], predicate: str) -> float:
    for row in sorted(rows, key=lambda item: float(item.spread_value)):
        ok = False
        if predicate == "validation_negative":
            ok = row.validation_total_cash_pnl < 0
        elif predicate == "test_negative":
            ok = row.test_total_cash_pnl < 0
        elif predicate == "transfer_fail":
            ok = not bool(row.transfer_pass_gate)
        if ok:
            return float(row.spread_value)
    return -1.0


def build_break_even_rows(rows: Sequence[SensitivityRow]) -> list[BreakEvenRow]:
    grouped: dict[tuple[str, str, int, str, int, str], list[SensitivityRow]] = {}
    for row in rows:
        key = (
            row.policy_key,
            row.side_mapping,
            int(row.entry_delay_bars),
            row.bracket_id,
            int(row.hold_bars),
            row.spread_mode,
        )
        grouped.setdefault(key, []).append(row)
    output: list[BreakEvenRow] = []
    for key, group in grouped.items():
        sorted_group = sorted(group, key=lambda item: float(item.spread_value))
        first = sorted_group[0]
        zero_rows = [row for row in sorted_group if abs(float(row.spread_value)) <= 1e-12]
        zero = zero_rows[0] if zero_rows else first
        best_validation = max(sorted_group, key=lambda item: (item.validation_score, item.validation_profit_factor))
        group_id = "|".join(str(part) for part in key)
        output.append(
            BreakEvenRow(
                group_id=group_id,
                policy_key=first.policy_key,
                side_mapping=first.side_mapping,
                entry_delay_bars=int(first.entry_delay_bars),
                bracket_id=first.bracket_id,
                tp_atr=float(first.tp_atr),
                sl_atr=float(first.sl_atr),
                hold_bars=int(first.hold_bars),
                spread_mode=first.spread_mode,
                tested_spreads=",".join(f"{row.spread_value:g}" for row in sorted_group),
                zero_validation_profit_factor=float(zero.validation_profit_factor),
                zero_test_profit_factor=float(zero.test_profit_factor),
                zero_validation_total_cash_pnl=float(zero.validation_total_cash_pnl),
                zero_test_total_cash_pnl=float(zero.test_total_cash_pnl),
                max_validation_nonnegative_spread=max_spread(sorted_group, "validation_nonnegative"),
                max_test_nonnegative_spread=max_spread(sorted_group, "test_nonnegative"),
                max_both_nonnegative_spread=max_spread(sorted_group, "both_nonnegative"),
                max_validation_pass_spread=max_spread(sorted_group, "validation_pass"),
                max_test_pass_spread=max_spread(sorted_group, "test_pass"),
                max_transfer_pass_spread=max_spread(sorted_group, "transfer_pass"),
                first_validation_negative_spread=first_spread(sorted_group, "validation_negative"),
                first_test_negative_spread=first_spread(sorted_group, "test_negative"),
                first_transfer_fail_spread=first_spread(sorted_group, "transfer_fail"),
                best_validation_spread=float(best_validation.spread_value),
                best_validation_score=float(best_validation.validation_score),
                best_validation_test_profit_factor=float(best_validation.test_profit_factor),
                best_validation_test_total_cash_pnl=float(best_validation.test_total_cash_pnl),
            )
        )
    return sorted(
        output,
        key=lambda row: (
            row.max_transfer_pass_spread,
            row.max_both_nonnegative_spread,
            row.zero_validation_total_cash_pnl,
            row.zero_test_total_cash_pnl,
        ),
        reverse=True,
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase164Report) -> str:
    top_rows = "".join(
        f"<tr><td>{html.escape(str(row['policy_key']))}</td>"
        f"<td>{html.escape(str(row['spread_mode']))}</td>"
        f"<td>{float(row['spread_value']):.4g}</td>"
        f"<td>{html.escape(str(row['bracket_id']))}</td>"
        f"<td>{int(row['hold_bars'])}</td>"
        f"<td>{int(row['validation_trades'])}</td>"
        f"<td>{float(row['validation_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{int(row['test_trades'])}</td>"
        f"<td>{float(row['test_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.top_config_rows[:80]
    )
    be_rows = "".join(
        f"<tr><td>{html.escape(str(row['policy_key']))}</td>"
        f"<td>{html.escape(str(row['spread_mode']))}</td>"
        f"<td>{html.escape(str(row['bracket_id']))}</td>"
        f"<td>{int(row['hold_bars'])}</td>"
        f"<td>{float(row['zero_validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['zero_test_profit_factor']):.3f}</td>"
        f"<td>{float(row['max_transfer_pass_spread']):.4g}</td>"
        f"<td>{float(row['max_both_nonnegative_spread']):.4g}</td></tr>"
        for row in report.break_even_rows_preview[:80]
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1440px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:12px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase164A 1H spread-unit and bracket-cost sensitivity. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'route_feasible_gate': report.route_feasible_gate,
        'selected_config_id': report.selected_config_id,
        'selected_spread_mode': report.selected_spread_mode,
        'selected_spread_value': report.selected_spread_value,
        'selected_validation_pf': report.selected_validation_profit_factor,
        'selected_test_pf': report.selected_test_profit_factor,
        'selected_transfer_pass_gate': report.selected_transfer_pass_gate,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Top config rows</h2><table><thead><tr><th>Policy</th><th>Mode</th><th>Spread</th><th>Bracket</th><th>Hold</th><th>Val trades</th><th>Val PnL</th><th>Val PF</th><th>Test trades</th><th>Test PnL</th><th>Test PF</th><th>Transfer</th></tr></thead><tbody>{top_rows}</tbody></table></section>
<section class="card"><h2>Break-even spread thresholds</h2><table><thead><tr><th>Policy</th><th>Mode</th><th>Bracket</th><th>Hold</th><th>Zero Val PF</th><th>Zero Test PF</th><th>Max transfer spread</th><th>Max both nonnegative spread</th></tr></thead><tbody>{be_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE164A 1H SPREAD / BRACKET COST SENSITIVITY AUDIT")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
        split_map = {"train": train_idx, "validation": validation_idx, "test": test_idx}
        rows, split_replay_rows, monthly_rows = evaluate_grid(args, frame, split_map, atr)
        ranked = sorted(
            rows,
            key=lambda row: (
                row.transfer_pass_gate,
                row.validation_pass_gate,
                row.validation_score,
                row.validation_profit_factor,
                row.test_profit_factor,
            ),
            reverse=True,
        )
        selected = ranked[0] if ranked else None
        break_even_rows = build_break_even_rows(rows)
        spread_atr_rows: list[dict[str, Any]] = []
        for mode, spreads in (
            ("fixed", parse_float_grid(args.fixed_spreads, (0.0, 0.2, 0.5, 1.0, 1.5, 2.0))),
            ("pct", parse_float_grid(args.pct_spreads, (0.0, 0.01, 0.02, 0.03, 0.06))),
        ):
            mode_args = SimpleNamespace(**{**vars(args), "spread_mode": mode})
            for spread in spreads:
                for split, idx in split_map.items():
                    spread_atr_rows.append(asdict(spread_atr_for_split(split, frame, idx, atr, mode_args, float(spread))))
        grid_csv = output_dir / "latest_grid.csv"
        split_csv = output_dir / "latest_split_replay.csv"
        break_even_csv = output_dir / "latest_break_even.csv"
        spread_atr_csv = output_dir / "latest_spread_atr.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        write_csv(grid_csv, [asdict(row) for row in ranked])
        write_csv(split_csv, split_replay_rows)
        write_csv(break_even_csv, [asdict(row) for row in break_even_rows])
        write_csv(spread_atr_csv, spread_atr_rows)
        write_csv(monthly_csv, monthly_rows)
        fixed_transfer = int(sum(1 for row in rows if row.spread_mode == "fixed" and row.transfer_pass_gate))
        pct_transfer = int(sum(1 for row in rows if row.spread_mode == "pct" and row.transfer_pass_gate))
        route_feasible = int(bool(selected) and selected.transfer_pass_gate)
        report = Phase164Report(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            flat_rows=int(len(frame)),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
            candidate_policies=len(parse_candidate_policies(args.candidate_policies)),
            brackets=len(parse_brackets(args.brackets)),
            hold_bars_grid=parse_int_grid(args.hold_bars_grid, (24, 48)),
            fixed_spreads=parse_float_grid(args.fixed_spreads, (0.0, 0.2, 0.5, 1.0, 1.5, 2.0)),
            pct_spreads=parse_float_grid(args.pct_spreads, (0.0, 0.01, 0.02, 0.03, 0.06)),
            evaluated_configs=int(len(rows)),
            validation_pass_configs=int(sum(row.validation_pass_gate for row in rows)),
            transfer_pass_configs=int(sum(row.transfer_pass_gate for row in rows)),
            fixed_transfer_pass_configs=fixed_transfer,
            pct_transfer_pass_configs=pct_transfer,
            selected_config_id=str(selected.config_id) if selected else "",
            selected_policy_key=str(selected.policy_key) if selected else "",
            selected_spread_mode=str(selected.spread_mode) if selected else "",
            selected_spread_value=float(selected.spread_value) if selected else 0.0,
            selected_bracket_id=str(selected.bracket_id) if selected else "",
            selected_tp_atr=float(selected.tp_atr) if selected else 0.0,
            selected_sl_atr=float(selected.sl_atr) if selected else 0.0,
            selected_hold_bars=int(selected.hold_bars) if selected else 0,
            selected_validation_profit_factor=float(selected.validation_profit_factor) if selected else 0.0,
            selected_test_profit_factor=float(selected.test_profit_factor) if selected else 0.0,
            selected_validation_total_cash_pnl=float(selected.validation_total_cash_pnl) if selected else 0.0,
            selected_test_total_cash_pnl=float(selected.test_total_cash_pnl) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            route_feasible_gate=route_feasible,
            top_config_rows=[asdict(row) for row in ranked[:120]],
            break_even_rows_preview=[asdict(row) for row in break_even_rows[:120]],
            spread_atr_rows=spread_atr_rows[:120],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_grid_csv=str(grid_csv),
            output_split_replay_csv=str(split_csv),
            output_break_even_csv=str(break_even_csv),
            output_spread_atr_csv=str(spread_atr_csv),
            output_monthly_csv=str(monthly_csv),
            production_status="BLOCKED — Phase164A 1H spread/bracket diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase164A spread/bracket sensitivity complete")
        print(f"  configs        : {report.evaluated_configs}")
        print(f"  validation pass: {report.validation_pass_configs}")
        print(f"  transfer pass  : {report.transfer_pass_configs}")
        print(f"  selected       : {report.selected_config_id or 'none'}")
        print(f"  route feasible : {report.route_feasible_gate}")
        print(f"  output         : {report.output_json}")
        print(f"  elapsed        : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
