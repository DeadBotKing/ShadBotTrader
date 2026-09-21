"""Phase155A: payoff-target tensor build + diagnostic Option B training.

This wrapper takes Phase154A payoff-stable candidates (B4 first, B2 backup),
builds candidate tensors, audits tensor health, trains raw Option B with an
explicit seed, and runs validation/test ATR PnL checks.

Research-only. No production/paper/live approval.
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

from audit_pivot_payoff_target_redesign import PayoffCandidate, parse_candidates  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_payoff_option_b_diagnostic")
DEFAULT_CANDIDATES = (
    "B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1;"
    "B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1"
)


@dataclass(frozen=True)
class PayoffOptionBDiagnosticRow:
    candidate_id: str
    label: str
    output_name: str
    model_id: str
    tensor_path: str
    meta_path: str
    flat_path: str
    build_json: str
    health_json: str
    train_json: str
    validation_backtest_json: str
    test_backtest_json: str
    health_status: str
    health_nonfinite_cells: int
    train_val_action_accuracy: float
    train_test_action_accuracy: float
    train_val_selected_rate: float
    train_test_selected_rate: float
    validation_trades: int
    validation_final_balance: float
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_max_drawdown: float
    test_trades: int
    test_final_balance: float
    test_profit_factor: float
    test_total_cash_pnl: float
    test_max_drawdown: float
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int


@dataclass(frozen=True)
class PayoffOptionBDiagnosticReport:
    symbol: str
    timeframe: str
    candidates: list[dict[str, Any]]
    completed_candidates: int
    selected_candidate_id: str
    selected_model_id: str
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_test_final_balance: float
    selected_transfer_pass_gate: int
    rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_csv: str
    production_status: str


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase155A payoff-target tensor + Option B diagnostic training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--source-mode", choices=("storage", "yahoo", "files"), default="storage")
    parser.add_argument("--yahoo-symbol", default="GC=F")
    parser.add_argument("--daily-range", default="5y")
    parser.add_argument("--hourly-range", default="730d")
    parser.add_argument("--five-range", default="60d")
    parser.add_argument("--hourly-timeframe", default="1H")
    parser.add_argument("--h4-timeframe", default="4H")
    parser.add_argument("--daily-timeframe", default="1D")
    parser.add_argument("--daily-path", default="")
    parser.add_argument("--hourly-path", default="")
    parser.add_argument("--h4-path", default="")
    parser.add_argument("--five-path", default="")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "target_first", "skip_ambiguous"), default="stop_first")
    parser.add_argument("--timeout-score-mode", choices=("zero", "close_r"), default="zero")
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--build-max-samples", type=int, default=0)
    parser.add_argument("--include-source-5m-features", choices=("0", "1"), default="1")
    parser.add_argument("--source-5m-feature-path", nargs="?", const="", default="")
    parser.add_argument("--max-features", type=int, default=0)
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--axis-normalization", choices=("robust", "standard", "none"), default="robust")
    parser.add_argument("--feature-clip", type=float, default=8.0)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--max-tensor-mb", type=float, default=8192.0)
    parser.add_argument("--health-full-scan", choices=("0", "1"), default="1")
    parser.add_argument("--health-max-scan-samples", type=int, default=0)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--train-max-samples", type=int, default=24000)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--random-seed", type=int, default=20260921)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--stream-chunk-size", type=int, default=512)
    parser.add_argument("--branch-filters", type=int, default=48)
    parser.add_argument("--branch-target-features", type=int, default=0)
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
    parser.add_argument("--class-weight", choices=("auto", "off"), default="off")
    parser.add_argument("--buy-threshold", type=float, default=0.34)
    parser.add_argument("--sell-threshold", type=float, default=0.34)
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--top-threshold", type=float, default=0.0)
    parser.add_argument("--bottom-threshold", type=float, default=0.0)
    parser.add_argument("--min-buy-r", type=float, default=-999.0)
    parser.add_argument("--min-sell-r", type=float, default=-999.0)
    parser.add_argument("--tp-multiplier", type=float, default=0.75)
    parser.add_argument("--sl-multiplier", type=float, default=0.75)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--validation-min-trades", type=int, default=20)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--skip-existing-tensors", choices=("0", "1"), default="0")
    parser.add_argument("--skip-training", choices=("0", "1"), default="0")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout-minutes-per-command", type=int, default=720)
    parser.add_argument("--report-title", default="Phase155A payoff-target Option B diagnostic")
    return parser.parse_args(argv)


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


def output_name(candidate: PayoffCandidate) -> str:
    return f"pivot_payoff_sequence_tensor_{safe_slug(candidate.candidate_id)}_latest"


def model_id(args: argparse.Namespace, candidate: PayoffCandidate) -> str:
    return f"gold_pivot_payoff_option_b_{safe_slug(candidate.candidate_id)}_5m"


def candidate_paths(args: argparse.Namespace, candidate: PayoffCandidate) -> tuple[Path, Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.timeframe.upper()
    name = output_name(candidate)
    tensor = root / f"{name}.npy"
    meta = root / f"{name}_meta.npz"
    flat = root / f"{name.replace('sequence_tensor', 'sequence_flat')}.parquet"
    return tensor, meta, flat


def build_command(args: argparse.Namespace, candidate: PayoffCandidate, build_dir: Path) -> list[str]:
    return [
        sys.executable,
        "-u",
        "scripts/build_pivot_payoff_sequence_tensor.py",
        "--source-mode", args.source_mode,
        "--symbol", args.symbol,
        "--yahoo-symbol", args.yahoo_symbol,
        "--daily-range", args.daily_range,
        "--hourly-range", args.hourly_range,
        "--five-range", args.five_range,
        "--five-timeframe", args.timeframe,
        "--hourly-timeframe", args.hourly_timeframe,
        "--h4-timeframe", args.h4_timeframe,
        "--daily-timeframe", args.daily_timeframe,
        "--daily-path", args.daily_path,
        "--hourly-path", args.hourly_path,
        "--h4-path", args.h4_path,
        "--five-path", args.five_path,
        "--candidate-id", candidate.candidate_id,
        "--candidate-label", candidate.label,
        "--lookahead-bars", str(candidate.lookahead_bars),
        "--pivot-zone-atr", str(candidate.pivot_zone_atr),
        "--tp-atr", str(candidate.tp_atr),
        "--sl-atr", str(candidate.sl_atr),
        "--min-score-edge", str(candidate.min_score_edge),
        "--recent-window-bars", str(args.recent_window_bars),
        "--same-bar-policy", args.same_bar_policy,
        "--timeout-score-mode", args.timeout_score_mode,
        "--window-size", str(args.window_size),
        "--sample-stride", str(args.sample_stride),
        "--max-samples", str(args.build_max_samples),
        "--include-source-5m-features", args.include_source_5m_features,
        "--source-5m-feature-path", args.source_5m_feature_path,
        "--max-features", str(args.max_features),
        "--dtype", args.dtype,
        "--axis-normalization", args.axis_normalization,
        "--feature-clip", str(args.feature_clip),
        "--chunk-size", str(args.chunk_size),
        "--max-tensor-mb", str(args.max_tensor_mb),
        "--storage-root", args.storage_root,
        "--output-dir", str(build_dir),
        "--output-name", output_name(candidate),
    ]


def health_command(args: argparse.Namespace, candidate: PayoffCandidate, build_dir: Path, health_dir: Path) -> list[str]:
    tensor, meta, flat = candidate_paths(args, candidate)
    return [
        sys.executable,
        "-u",
        "scripts/audit_pivot_pattern_sequence_tensor.py",
        "--symbol", args.symbol,
        "--timeframe", args.timeframe,
        "--tensor-path", str(tensor),
        "--meta-path", str(meta),
        "--flat-path", str(flat),
        "--builder-report", str(build_dir / "latest.json"),
        "--chunk-size", str(args.chunk_size),
        "--full-scan", args.health_full_scan,
        "--max-scan-samples", str(args.health_max_scan_samples),
        "--fail-on-reported-feature-nonfinite", "1",
        "--storage-root", args.storage_root,
        "--output-dir", str(health_dir),
    ]


def train_command(args: argparse.Namespace, candidate: PayoffCandidate, train_dir: Path) -> list[str]:
    tensor, meta, _ = candidate_paths(args, candidate)
    return [
        sys.executable,
        "-u",
        "scripts/train_pivot_pattern_sequence_wavenet_option_b.py",
        "--symbol", args.symbol,
        "--timeframe", args.timeframe,
        "--tensor-path", str(tensor),
        "--meta-path", str(meta),
        "--model-id", model_id(args, candidate),
        "--train-frac", str(args.train_frac),
        "--val-frac", str(args.val_frac),
        "--purge-gap", str(args.purge_gap),
        "--max-samples", str(args.train_max_samples),
        "--stream-chunk-size", str(args.stream_chunk_size),
        "--batch-size", str(args.batch_size),
        "--epochs", str(args.epochs),
        "--learning-rate", str(args.learning_rate),
        "--random-seed", str(args.random_seed),
        "--branch-filters", str(args.branch_filters),
        "--branch-target-features", str(args.branch_target_features),
        "--feature-augmentation-mode", args.feature_augmentation_mode,
        "--feature-augmentation-clip", str(args.feature_augmentation_clip),
        "--temporal-filters", str(args.temporal_filters),
        "--temporal-kernels", args.temporal_kernels,
        "--dilations", args.dilations,
        "--residual-blocks", str(args.residual_blocks),
        "--attention-heads", str(args.attention_heads),
        "--attention-key-dim", str(args.attention_key_dim),
        "--se-ratio", str(args.se_ratio),
        "--dense-units", str(args.dense_units),
        "--dropout", str(args.dropout),
        "--activation", args.activation,
        "--action-loss-weight", str(args.action_loss_weight),
        "--top-loss-weight", str(args.top_loss_weight),
        "--bottom-loss-weight", str(args.bottom_loss_weight),
        "--r-loss-weight", str(args.r_loss_weight),
        "--class-weight", args.class_weight,
        "--buy-threshold", str(args.buy_threshold),
        "--sell-threshold", str(args.sell_threshold),
        "--min-margin", str(args.min_margin),
        "--min-buy-r", str(args.min_buy_r),
        "--min-sell-r", str(args.min_sell_r),
        "--early-stopping-patience", str(args.early_stopping_patience),
        "--checkpoint-each-epoch", "1",
        "--batch-log-every", "25",
        "--save-model", "1",
        "--storage-root", args.storage_root,
        "--output-dir", str(train_dir),
        "--report-title", f"Phase155A payoff Option B {candidate.candidate_id} training",
    ]


def backtest_command(args: argparse.Namespace, candidate: PayoffCandidate, split: str, output_dir: Path) -> list[str]:
    tensor, meta, flat = candidate_paths(args, candidate)
    return [
        sys.executable,
        "-u",
        "scripts/backtest_pivot_pattern_sequence_wavenet.py",
        "--symbol", args.symbol,
        "--timeframe", args.timeframe,
        "--tensor-path", str(tensor),
        "--meta-path", str(meta),
        "--flat-path", str(flat),
        "--model-id", model_id(args, candidate),
        "--model-version", "0",
        "--max-samples", str(args.train_max_samples),
        "--eval-split", split,
        "--train-frac", str(args.train_frac),
        "--val-frac", str(args.val_frac),
        "--purge-gap", str(args.purge_gap),
        "--max-windows", "0",
        "--batch-size", "128",
        "--buy-threshold", str(args.buy_threshold),
        "--sell-threshold", str(args.sell_threshold),
        "--min-margin", str(args.min_margin),
        "--top-threshold", str(args.top_threshold),
        "--bottom-threshold", str(args.bottom_threshold),
        "--min-buy-r", str(args.min_buy_r),
        "--min-sell-r", str(args.min_sell_r),
        "--tp-multiplier", str(args.tp_multiplier),
        "--sl-multiplier", str(args.sl_multiplier),
        "--hold-bars", str(args.hold_bars),
        "--spread-mode", args.spread_mode,
        "--spread-value", str(args.spread_value),
        "--same-bar-policy", "stop_first" if args.same_bar_policy == "skip_ambiguous" else args.same_bar_policy,
        "--initial-capital", str(args.initial_capital),
        "--risk-per-trade", str(args.risk_per_trade),
        "--storage-root", args.storage_root,
        "--output-dir", str(output_dir),
        "--report-title", f"Phase155A payoff Option B {candidate.candidate_id} {split} backtest",
    ]


def load_report(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Expected report not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("report", payload)


def nested_report(path: Path) -> Mapping[str, Any]:
    payload = load_report(path)
    return payload.get("report", payload) if isinstance(payload, Mapping) else {}


def build_row(args: argparse.Namespace, candidate: PayoffCandidate, root: Path) -> PayoffOptionBDiagnosticRow:
    tensor, meta, flat = candidate_paths(args, candidate)
    build_json = root / "build" / "latest.json"
    health_json = root / "health" / "latest.json"
    train_json = root / "train" / "latest.json"
    validation_json = root / "validation_backtest" / "latest.json"
    test_json = root / "test_backtest" / "latest.json"
    health = nested_report(health_json)
    train = nested_report(train_json)
    validation = nested_report(validation_json)
    test = nested_report(test_json)
    train_metrics = train.get("metrics", {}) if isinstance(train, Mapping) else {}
    validation_pass = int(
        int(validation.get("trades", 0)) >= int(args.validation_min_trades)
        and float(validation.get("profit_factor", 0.0)) >= float(args.validation_min_profit_factor)
        and float(validation.get("final_balance", 0.0)) >= float(args.validation_min_final_balance)
    )
    test_pass = int(
        float(test.get("profit_factor", 0.0)) >= float(args.test_min_profit_factor)
        and float(test.get("final_balance", 0.0)) >= float(args.test_min_final_balance)
    )
    health_scan = health.get("scan", {}) if isinstance(health, Mapping) else {}
    return PayoffOptionBDiagnosticRow(
        candidate_id=candidate.candidate_id,
        label=candidate.label,
        output_name=output_name(candidate),
        model_id=model_id(args, candidate),
        tensor_path=str(tensor),
        meta_path=str(meta),
        flat_path=str(flat),
        build_json=str(build_json),
        health_json=str(health_json),
        train_json=str(train_json),
        validation_backtest_json=str(validation_json),
        test_backtest_json=str(test_json),
        health_status=str(health.get("status", "UNKNOWN")),
        health_nonfinite_cells=int(health_scan.get("nonfinite_cells", 0)),
        train_val_action_accuracy=float(train_metrics.get("val_action_accuracy", 0.0)),
        train_test_action_accuracy=float(train_metrics.get("test_action_accuracy", 0.0)),
        train_val_selected_rate=float(train_metrics.get("val_selected_rate", 0.0)),
        train_test_selected_rate=float(train_metrics.get("test_selected_rate", 0.0)),
        validation_trades=int(validation.get("trades", 0)),
        validation_final_balance=float(validation.get("final_balance", 0.0)),
        validation_profit_factor=float(validation.get("profit_factor", 0.0)),
        validation_total_cash_pnl=float(validation.get("total_cash_pnl", 0.0)),
        validation_max_drawdown=float(validation.get("max_drawdown_cash", 0.0)),
        test_trades=int(test.get("trades", 0)),
        test_final_balance=float(test.get("final_balance", 0.0)),
        test_profit_factor=float(test.get("profit_factor", 0.0)),
        test_total_cash_pnl=float(test.get("total_cash_pnl", 0.0)),
        test_max_drawdown=float(test.get("max_drawdown_cash", 0.0)),
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


def render_html(title: str, report: PayoffOptionBDiagnosticReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{html.escape(str(row['model_id']))}</td>"
        f"<td>{html.escape(str(row['health_status']))}</td>"
        f"<td>{float(row['train_test_action_accuracy']):.3f}</td>"
        f"<td>{int(row['validation_trades'])}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_final_balance']):.3f}</td>"
        f"<td>{int(row['test_trades'])}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_final_balance']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase155A payoff-target tensor + Option B diagnostic. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Rows</h2><table><thead><tr><th>ID</th><th>Model</th><th>Health</th><th>Test Acc</th><th>Val Trades</th><th>Val PF</th><th>Val Final</th><th>Test Trades</th><th>Test PF</th><th>Test Final</th><th>Transfer</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timeout_seconds = max(int(args.timeout_minutes_per_command), 5) * 60
    try:
        print("\n" + "=" * 74)
        print("  PHASE155A PAYOFF-TARGET OPTION B DIAGNOSTIC")
        print("=" * 74)
        candidates = parse_candidates(args.candidates)
        rows: list[PayoffOptionBDiagnosticRow] = []
        for candidate in candidates:
            slug = safe_slug(candidate.candidate_id)
            root = output_dir / slug
            build_dir = root / "build"
            health_dir = root / "health"
            train_dir = root / "train"
            validation_dir = root / "validation_backtest"
            test_dir = root / "test_backtest"
            for directory in (build_dir, health_dir, train_dir, validation_dir, test_dir):
                directory.mkdir(parents=True, exist_ok=True)
            tensor, meta, flat = candidate_paths(args, candidate)
            if args.skip_existing_tensors == "1" and tensor.exists() and meta.exists() and flat.exists():
                print(f"  [i] existing tensor found for {candidate.candidate_id}; skipping build")
            else:
                run_command(build_command(args, candidate, build_dir), timeout_seconds)
            run_command(health_command(args, candidate, build_dir, health_dir), timeout_seconds)
            if args.skip_training == "1":
                print(f"  [i] skip-training=1 for {candidate.candidate_id}")
            else:
                run_command(train_command(args, candidate, train_dir), timeout_seconds)
            run_command(backtest_command(args, candidate, "validation", validation_dir), timeout_seconds)
            run_command(backtest_command(args, candidate, "test", test_dir), timeout_seconds)
            rows.append(build_row(args, candidate, root))
        ranked = sorted(rows, key=lambda row: (row.transfer_pass_gate, row.validation_profit_factor, row.test_profit_factor), reverse=True)
        selected = ranked[0] if ranked else None
        row_dicts = [asdict(row) for row in ranked]
        output_csv = output_dir / "latest.csv"
        write_csv(output_csv, row_dicts)
        report = PayoffOptionBDiagnosticReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            candidates=[asdict(candidate) for candidate in candidates],
            completed_candidates=len(row_dicts),
            selected_candidate_id=selected.candidate_id if selected else "",
            selected_model_id=selected.model_id if selected else "",
            selected_validation_profit_factor=float(selected.validation_profit_factor) if selected else 0.0,
            selected_test_profit_factor=float(selected.test_profit_factor) if selected else 0.0,
            selected_test_final_balance=float(selected.test_final_balance) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            rows=row_dicts,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_csv=str(output_csv),
            production_status="BLOCKED — Phase155A research diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase155A payoff Option B diagnostic complete")
        print(f"  selected candidate : {report.selected_candidate_id or 'none'}")
        print(f"  selected val PF    : {report.selected_validation_profit_factor:.4f}")
        print(f"  selected test PF   : {report.selected_test_profit_factor:.4f}")
        print(f"  transfer pass      : {report.selected_transfer_pass_gate}")
        print(f"  output             : {report.output_json}")
        print(f"  elapsed            : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
