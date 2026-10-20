"""Phase151A: seed repeatability / validation-to-test transfer audit for Option B.

This phase intentionally does not optimise on the test split. It trains a small
set of Option B models with explicit seeds, evaluates each one on validation and
then on test with the same fixed replay rules, and selects only by validation.

Research-only. No paper/live approval.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_sequence_option_b_seed_transfer")


@dataclass(frozen=True)
class SeedRunReport:
    seed: int
    model_id: str
    train_output_dir: str
    validation_output_dir: str
    test_output_dir: str
    train_json: str
    validation_json: str
    test_json: str
    validation_trades: int
    validation_final_balance: float
    validation_return_percent: float
    validation_profit_factor: float
    validation_max_drawdown: float
    validation_total_cash_pnl: float
    validation_buy_cash_pnl: float
    validation_sell_cash_pnl: float
    validation_positive_months: int
    validation_negative_months: int
    test_trades: int
    test_final_balance: float
    test_return_percent: float
    test_profit_factor: float
    test_max_drawdown: float
    test_total_cash_pnl: float
    test_buy_cash_pnl: float
    test_sell_cash_pnl: float
    test_positive_months: int
    test_negative_months: int
    validation_score: float
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int


@dataclass(frozen=True)
class SeedTransferReport:
    model_id_prefix: str
    seeds: list[int]
    selected_seed: int
    selected_model_id: str
    selected_validation_score: float
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_test_final_balance: float
    selected_transfer_pass_gate: int
    runs: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_csv: str
    production_status: str


def parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for raw in str(text or "").split(","):
        item = raw.strip()
        if not item:
            continue
        value = int(item)
        if value not in seeds:
            seeds.append(value)
    if not seeds:
        raise RuntimeError("At least one seed is required")
    return seeds


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase151A seed repeatability / validation-to-test transfer audit for raw Option B.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id-prefix", default="gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m")
    parser.add_argument("--seeds", default="20260919,20260920,20260921")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--stream-chunk-size", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--branch-filters", type=int, default=48)
    parser.add_argument("--branch-target-features", type=int, default=0)
    parser.add_argument("--feature-augmentation-mode", choices=("off", "causal"), default="off")
    parser.add_argument("--feature-augmentation-clip", type=float, default=8.0)
    parser.add_argument("--zero-feature-file", default="")
    parser.add_argument("--zero-feature-names", default="")
    parser.add_argument("--zero-feature-groups", default="")
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
    parser.add_argument("--top-threshold", type=float, default=0.0)
    parser.add_argument("--bottom-threshold", type=float, default=0.0)
    parser.add_argument("--min-buy-r", type=float, default=-999.0)
    parser.add_argument("--min-sell-r", type=float, default=-999.0)
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--checkpoint-each-epoch", choices=("0", "1"), default="1")
    parser.add_argument("--batch-log-every", type=int, default=1000)
    parser.add_argument("--tp-multiplier", type=float, default=0.75)
    parser.add_argument("--sl-multiplier", type=float, default=0.75)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--selection-metric", choices=("validation_pnl", "validation_pf", "drawdown_adjusted"), default="drawdown_adjusted")
    parser.add_argument("--validation-min-trades", type=int, default=30)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout-minutes-per-command", type=int, default=720)
    parser.add_argument("--skip-training", choices=("0", "1"), default="0")
    parser.add_argument("--skip-existing-models", choices=("0", "1"), default="1")
    return parser.parse_args(argv)


def model_id_for_seed(prefix: str, seed: int) -> str:
    safe_prefix = "_".join(part for part in str(prefix).replace("-", "_").split() if part) or "option_b_seed"
    return f"{safe_prefix}_seed_{int(seed)}"


def existing_model_record(storage_root: str, model_id: str) -> Path | None:
    model_dir = Path(storage_root) / "models" / model_id
    if not model_dir.exists():
        return None
    records = []
    for path in model_dir.glob("v*_training.json"):
        raw = path.stem.removeprefix("v").removesuffix("_training")
        if raw.isdigit():
            records.append((int(raw), path))
    if not records:
        return None
    return sorted(records)[-1][1]


def run_command(command: Sequence[str], timeout_seconds: int) -> None:
    print("\n$ " + " ".join(command), flush=True)
    process = subprocess.Popen(
        list(command),
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    started = time.monotonic()
    for line in process.stdout:
        print(line.rstrip(), flush=True)
        if time.monotonic() - started > timeout_seconds:
            process.kill()
            raise RuntimeError(f"Command timed out after {timeout_seconds}s: {' '.join(command)}")
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Command failed with exit code {return_code}: {' '.join(command)}")


def maybe_add_path(command: list[str], flag: str, value: str) -> None:
    if str(value).strip():
        command.extend([flag, str(value).strip()])


def train_command(args: argparse.Namespace, model_id: str, seed: int, output_dir: Path) -> list[str]:
    command = [
        sys.executable,
        "-u",
        "scripts/train_pivot_pattern_sequence_wavenet_option_b.py",
        "--symbol",
        args.symbol,
        "--timeframe",
        args.timeframe,
        "--model-id",
        model_id,
        "--train-frac",
        str(args.train_frac),
        "--val-frac",
        str(args.val_frac),
        "--purge-gap",
        str(args.purge_gap),
        "--max-samples",
        str(args.max_samples),
        "--stream-chunk-size",
        str(args.stream_chunk_size),
        "--batch-size",
        str(args.batch_size),
        "--epochs",
        str(args.epochs),
        "--learning-rate",
        str(args.learning_rate),
        "--random-seed",
        str(seed),
        "--branch-filters",
        str(args.branch_filters),
        "--branch-target-features",
        str(args.branch_target_features),
        "--feature-augmentation-mode",
        args.feature_augmentation_mode,
        "--feature-augmentation-clip",
        str(args.feature_augmentation_clip),
        "--temporal-filters",
        str(args.temporal_filters),
        "--temporal-kernels",
        args.temporal_kernels,
        "--dilations",
        args.dilations,
        "--residual-blocks",
        str(args.residual_blocks),
        "--attention-heads",
        str(args.attention_heads),
        "--attention-key-dim",
        str(args.attention_key_dim),
        "--se-ratio",
        str(args.se_ratio),
        "--dense-units",
        str(args.dense_units),
        "--dropout",
        str(args.dropout),
        "--activation",
        args.activation,
        "--action-loss-weight",
        str(args.action_loss_weight),
        "--top-loss-weight",
        str(args.top_loss_weight),
        "--bottom-loss-weight",
        str(args.bottom_loss_weight),
        "--r-loss-weight",
        str(args.r_loss_weight),
        "--class-weight",
        args.class_weight,
        "--buy-threshold",
        str(args.buy_threshold),
        "--sell-threshold",
        str(args.sell_threshold),
        "--min-margin",
        str(args.min_margin),
        "--min-buy-r",
        str(args.min_buy_r),
        "--min-sell-r",
        str(args.min_sell_r),
        "--early-stopping-patience",
        str(args.early_stopping_patience),
        "--checkpoint-each-epoch",
        args.checkpoint_each_epoch,
        "--batch-log-every",
        str(args.batch_log_every),
        "--save-model",
        "1",
        "--storage-root",
        args.storage_root,
        "--output-dir",
        str(output_dir),
        "--report-title",
        f"Phase151A Option B seed {seed} training",
    ]
    maybe_add_path(command, "--tensor-path", args.tensor_path)
    maybe_add_path(command, "--meta-path", args.meta_path)
    maybe_add_path(command, "--zero-feature-names", args.zero_feature_names)
    maybe_add_path(command, "--zero-feature-file", args.zero_feature_file)
    maybe_add_path(command, "--zero-feature-groups", args.zero_feature_groups)
    return command


def backtest_command(args: argparse.Namespace, model_id: str, split: str, output_dir: Path) -> list[str]:
    command = [
        sys.executable,
        "-u",
        "scripts/backtest_pivot_pattern_sequence_wavenet.py",
        "--symbol",
        args.symbol,
        "--timeframe",
        args.timeframe,
        "--model-id",
        model_id,
        "--model-version",
        "0",
        "--max-samples",
        str(args.max_samples),
        "--eval-split",
        split,
        "--train-frac",
        str(args.train_frac),
        "--val-frac",
        str(args.val_frac),
        "--purge-gap",
        str(args.purge_gap),
        "--max-windows",
        "0",
        "--batch-size",
        "128",
        "--buy-threshold",
        str(args.buy_threshold),
        "--sell-threshold",
        str(args.sell_threshold),
        "--min-margin",
        str(args.min_margin),
        "--top-threshold",
        str(args.top_threshold),
        "--bottom-threshold",
        str(args.bottom_threshold),
        "--min-buy-r",
        str(args.min_buy_r),
        "--min-sell-r",
        str(args.min_sell_r),
        "--tp-multiplier",
        str(args.tp_multiplier),
        "--sl-multiplier",
        str(args.sl_multiplier),
        "--hold-bars",
        str(args.hold_bars),
        "--spread-mode",
        args.spread_mode,
        "--spread-value",
        str(args.spread_value),
        "--same-bar-policy",
        args.same_bar_policy,
        "--initial-capital",
        str(args.initial_capital),
        "--risk-per-trade",
        str(args.risk_per_trade),
        "--storage-root",
        args.storage_root,
        "--output-dir",
        str(output_dir),
        "--report-title",
        f"Phase151A Option B {split} seed transfer check",
    ]
    maybe_add_path(command, "--tensor-path", args.tensor_path)
    maybe_add_path(command, "--meta-path", args.meta_path)
    maybe_add_path(command, "--flat-path", args.flat_path)
    return command


def load_report(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Expected report not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("report", payload)


def validation_score(report: Mapping[str, Any], metric: str) -> float:
    pnl = float(report.get("total_cash_pnl", 0.0))
    pf = float(report.get("profit_factor", 0.0))
    dd = float(report.get("max_drawdown_cash", 0.0))
    if metric == "validation_pf":
        return pf
    if metric == "validation_pnl":
        return pnl
    return pnl - 0.25 * dd


def build_seed_report(args: argparse.Namespace, seed: int, model_id: str, train_dir: Path, validation_dir: Path, test_dir: Path) -> SeedRunReport:
    validation = load_report(validation_dir / "latest.json")
    test = load_report(test_dir / "latest.json")
    validation_score_value = validation_score(validation, args.selection_metric)
    validation_pass = int(
        int(validation.get("trades", 0)) >= int(args.validation_min_trades)
        and float(validation.get("profit_factor", 0.0)) >= float(args.validation_min_profit_factor)
        and float(validation.get("final_balance", 0.0)) >= float(args.validation_min_final_balance)
    )
    test_pass = int(
        float(test.get("profit_factor", 0.0)) >= float(args.test_min_profit_factor)
        and float(test.get("final_balance", 0.0)) >= float(args.test_min_final_balance)
    )
    return SeedRunReport(
        seed=seed,
        model_id=model_id,
        train_output_dir=str(train_dir),
        validation_output_dir=str(validation_dir),
        test_output_dir=str(test_dir),
        train_json=str(train_dir / "latest.json"),
        validation_json=str(validation_dir / "latest.json"),
        test_json=str(test_dir / "latest.json"),
        validation_trades=int(validation.get("trades", 0)),
        validation_final_balance=float(validation.get("final_balance", 0.0)),
        validation_return_percent=float(validation.get("return_percent", 0.0)),
        validation_profit_factor=float(validation.get("profit_factor", 0.0)),
        validation_max_drawdown=float(validation.get("max_drawdown_cash", 0.0)),
        validation_total_cash_pnl=float(validation.get("total_cash_pnl", 0.0)),
        validation_buy_cash_pnl=float(validation.get("buy_cash_pnl", 0.0)),
        validation_sell_cash_pnl=float(validation.get("sell_cash_pnl", 0.0)),
        validation_positive_months=int(validation.get("positive_months", 0)),
        validation_negative_months=int(validation.get("negative_months", 0)),
        test_trades=int(test.get("trades", 0)),
        test_final_balance=float(test.get("final_balance", 0.0)),
        test_return_percent=float(test.get("return_percent", 0.0)),
        test_profit_factor=float(test.get("profit_factor", 0.0)),
        test_max_drawdown=float(test.get("max_drawdown_cash", 0.0)),
        test_total_cash_pnl=float(test.get("total_cash_pnl", 0.0)),
        test_buy_cash_pnl=float(test.get("buy_cash_pnl", 0.0)),
        test_sell_cash_pnl=float(test.get("sell_cash_pnl", 0.0)),
        test_positive_months=int(test.get("positive_months", 0)),
        test_negative_months=int(test.get("negative_months", 0)),
        validation_score=float(validation_score_value),
        validation_pass_gate=validation_pass,
        test_pass_gate=test_pass,
        transfer_pass_gate=int(validation_pass and test_pass),
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: SeedTransferReport) -> str:
    rows = "".join(
        f"<tr><td>{row['seed']}</td><td>{html.escape(str(row['model_id']))}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_final_balance']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_final_balance']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.runs
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase151A seed transfer audit. Research only.</p>
<p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Selected by validation</h2><pre>{html.escape(json.dumps({'seed': report.selected_seed, 'model_id': report.selected_model_id, 'validation_score': report.selected_validation_score, 'validation_pf': report.selected_validation_profit_factor, 'test_pf': report.selected_test_profit_factor, 'test_final_balance': report.selected_test_final_balance, 'transfer_pass': report.selected_transfer_pass_gate}, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Runs</h2><table><thead><tr><th>Seed</th><th>Model</th><th>Val PF</th><th>Val Final</th><th>Test PF</th><th>Test Final</th><th>Pass</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timeout_seconds = max(int(args.timeout_minutes_per_command), 5) * 60
    try:
        print("\n" + "=" * 74)
        print("  PHASE151A OPTION B SEED TRANSFER VALIDATION")
        print("=" * 74)
        seeds = parse_seeds(args.seeds)
        print(f"  seeds       : {seeds}")
        reports: list[SeedRunReport] = []
        for seed in seeds:
            model_id = model_id_for_seed(args.model_id_prefix, seed)
            seed_root = output_dir / f"seed_{seed}"
            train_dir = seed_root / "train"
            validation_dir = seed_root / "validation_backtest"
            test_dir = seed_root / "test_backtest"
            train_dir.mkdir(parents=True, exist_ok=True)
            validation_dir.mkdir(parents=True, exist_ok=True)
            test_dir.mkdir(parents=True, exist_ok=True)
            existing_record = existing_model_record(args.storage_root, model_id)
            if args.skip_training == "1":
                print(f"  [i] skip-training=1 for {model_id}")
            elif args.skip_existing_models == "1" and existing_record is not None:
                print(f"  [i] existing model found for {model_id}: {existing_record}; skipping retrain")
            else:
                run_command(train_command(args, model_id, seed, train_dir), timeout_seconds)
            run_command(backtest_command(args, model_id, "validation", validation_dir), timeout_seconds)
            run_command(backtest_command(args, model_id, "test", test_dir), timeout_seconds)
            reports.append(build_seed_report(args, seed, model_id, train_dir, validation_dir, test_dir))
        ranked = sorted(reports, key=lambda item: (item.validation_score, item.validation_profit_factor), reverse=True)
        selected = ranked[0]
        rows = [asdict(item) for item in ranked]
        output_csv = output_dir / "latest.csv"
        write_csv(output_csv, rows)
        report = SeedTransferReport(
            model_id_prefix=args.model_id_prefix,
            seeds=seeds,
            selected_seed=int(selected.seed),
            selected_model_id=selected.model_id,
            selected_validation_score=float(selected.validation_score),
            selected_validation_profit_factor=float(selected.validation_profit_factor),
            selected_test_profit_factor=float(selected.test_profit_factor),
            selected_test_final_balance=float(selected.test_final_balance),
            selected_transfer_pass_gate=int(selected.transfer_pass_gate),
            runs=rows,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_csv=str(output_csv),
            production_status="BLOCKED — research seed transfer validation only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html("Phase151A seed transfer validation", report), encoding="utf-8")
        print("\n[DONE] Phase151A seed transfer validation complete")
        print(f"  selected seed : {selected.seed}")
        print(f"  validation PF : {selected.validation_profit_factor:.4f}")
        print(f"  test PF       : {selected.test_profit_factor:.4f}")
        print(f"  transfer pass : {selected.transfer_pass_gate}")
        print(f"  output        : {report.output_json}")
        print(f"  elapsed       : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
