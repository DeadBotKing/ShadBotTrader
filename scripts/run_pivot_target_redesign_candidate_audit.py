"""Phase153A: build and audit pivot target redesign candidates.

This diagnostic phase turns the most stable label candidates from Phase152A into
real sequence-tensor artifacts, runs the official tensor health audit for each
artifact, then runs the label/target stability audit on the exact candidate flat
and metadata files.

Research-only. No paper/live/production approval.
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
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_target_redesign_candidates")
DEFAULT_CANDIDATES = "C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25"


@dataclass(frozen=True)
class PivotTargetCandidate:
    candidate_id: str
    label: str
    lookahead_bars: int
    pivot_move_atr: float
    pivot_zone_atr: float
    min_direction_edge: float

    @property
    def slug(self) -> str:
        return safe_slug(f"{self.candidate_id}_{self.label}")

    @property
    def output_name(self) -> str:
        return f"pivot_pattern_sequence_tensor_{self.slug}_latest"


@dataclass(frozen=True)
class CandidateAuditRow:
    candidate_id: str
    label: str
    output_name: str
    lookahead_bars: int
    pivot_move_atr: float
    pivot_zone_atr: float
    recent_window_bars: int
    min_direction_edge: float
    tensor_path: str
    meta_path: str
    flat_path: str
    build_output_dir: str
    health_output_dir: str
    stability_output_dir: str
    build_json: str
    health_json: str
    stability_json: str
    build_samples: int
    build_tensor_shape: str
    build_target_counts: str
    health_status: str
    health_nonfinite_cells: int
    health_max_abs: float
    health_errors: str
    health_warnings: str
    sampled_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    train_sell_rate: float
    train_hold_rate: float
    train_buy_rate: float
    validation_sell_rate: float
    validation_hold_rate: float
    validation_buy_rate: float
    test_sell_rate: float
    test_hold_rate: float
    test_buy_rate: float
    train_actionable_rate: float
    validation_actionable_rate: float
    test_actionable_rate: float
    validation_psi_vs_train: float
    test_psi_vs_train: float
    train_buy_r_mean: float
    validation_buy_r_mean: float
    test_buy_r_mean: float
    train_sell_r_mean: float
    validation_sell_r_mean: float
    test_sell_r_mean: float
    buy_r_sign_flip: int
    sell_r_sign_flip: int
    label_stability_pass_gate: int
    target_payoff_warning_gate: int
    candidate_ready_for_training_gate: int
    stability_warnings: str


@dataclass(frozen=True)
class PivotTargetRedesignReport:
    symbol: str
    timeframe: str
    candidates: list[dict[str, Any]]
    label_stability_psi_threshold: float
    health_required_status: str
    completed_candidates: int
    label_stable_candidates: int
    training_ready_candidates: int
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


def parse_candidates(text: str) -> list[PivotTargetCandidate]:
    """Parse semicolon-separated candidate specs.

    Format per item:

        ID:label:lookahead_bars:pivot_move_atr:pivot_zone_atr:min_direction_edge

    Example:

        C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25
    """
    candidates: list[PivotTargetCandidate] = []
    for raw_item in str(text or "").split(";"):
        item = raw_item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 6:
            raise RuntimeError(
                "candidate specs must use ID:label:lookahead:pivot_move_atr:pivot_zone_atr:min_edge; "
                f"got: {item!r}"
            )
        candidate = PivotTargetCandidate(
            candidate_id=parts[0].upper() or f"C{len(candidates) + 1}",
            label=safe_slug(parts[1]),
            lookahead_bars=max(int(parts[2]), 1),
            pivot_move_atr=max(float(parts[3]), 0.01),
            pivot_zone_atr=max(float(parts[4]), 0.01),
            min_direction_edge=max(float(parts[5]), 1.0),
        )
        if candidate.candidate_id in {existing.candidate_id for existing in candidates}:
            raise RuntimeError(f"duplicate candidate id: {candidate.candidate_id}")
        candidates.append(candidate)
    if not candidates:
        raise RuntimeError("At least one target candidate is required")
    return candidates


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and audit Phase153A pivot target redesign candidates.",
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
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--build-max-samples", type=int, default=0)
    parser.add_argument("--audit-max-samples", type=int, default=24000)
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
    parser.add_argument("--psi-warning-threshold", type=float, default=0.20)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--skip-existing-tensors", choices=("0", "1"), default="0")
    parser.add_argument("--skip-health-audit", choices=("0", "1"), default="0")
    parser.add_argument("--skip-stability-audit", choices=("0", "1"), default="0")
    parser.add_argument("--timeout-minutes-per-command", type=int, default=360)
    parser.add_argument("--report-title", default="Phase153A pivot target redesign candidate build/audit")
    return parser.parse_args(argv)


def output_paths(args: argparse.Namespace, candidate: PivotTargetCandidate) -> tuple[Path, Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.timeframe.upper()
    tensor_path = root / f"{candidate.output_name}.npy"
    meta_path = root / f"{candidate.output_name}_meta.npz"
    flat_path = root / f"{candidate.output_name.replace('sequence_tensor', 'sequence_flat')}.parquet"
    return tensor_path, meta_path, flat_path


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


def build_tensor_command(
    args: argparse.Namespace, candidate: PivotTargetCandidate, build_output_dir: Path
) -> list[str]:
    return [
        sys.executable,
        "-u",
        "scripts/build_pivot_pattern_sequence_tensor.py",
        "--source-mode",
        args.source_mode,
        "--symbol",
        args.symbol,
        "--yahoo-symbol",
        args.yahoo_symbol,
        "--daily-range",
        args.daily_range,
        "--hourly-range",
        args.hourly_range,
        "--five-range",
        args.five_range,
        "--five-timeframe",
        args.timeframe,
        "--hourly-timeframe",
        args.hourly_timeframe,
        "--h4-timeframe",
        args.h4_timeframe,
        "--daily-timeframe",
        args.daily_timeframe,
        "--daily-path",
        args.daily_path,
        "--hourly-path",
        args.hourly_path,
        "--h4-path",
        args.h4_path,
        "--five-path",
        args.five_path,
        "--lookahead-bars",
        str(candidate.lookahead_bars),
        "--pivot-move-atr",
        str(candidate.pivot_move_atr),
        "--pivot-zone-atr",
        str(candidate.pivot_zone_atr),
        "--recent-window-bars",
        str(args.recent_window_bars),
        "--min-direction-edge",
        str(candidate.min_direction_edge),
        "--window-size",
        str(args.window_size),
        "--sample-stride",
        str(args.sample_stride),
        "--max-samples",
        str(args.build_max_samples),
        "--include-source-5m-features",
        args.include_source_5m_features,
        "--source-5m-feature-path",
        args.source_5m_feature_path,
        "--max-features",
        str(args.max_features),
        "--dtype",
        args.dtype,
        "--axis-normalization",
        args.axis_normalization,
        "--feature-clip",
        str(args.feature_clip),
        "--chunk-size",
        str(args.chunk_size),
        "--max-tensor-mb",
        str(args.max_tensor_mb),
        "--storage-root",
        args.storage_root,
        "--output-dir",
        str(build_output_dir),
        "--output-name",
        candidate.output_name,
    ]


def health_command(
    args: argparse.Namespace,
    tensor_path: Path,
    meta_path: Path,
    flat_path: Path,
    builder_report: Path,
    health_output_dir: Path,
) -> list[str]:
    return [
        sys.executable,
        "-u",
        "scripts/audit_pivot_pattern_sequence_tensor.py",
        "--symbol",
        args.symbol,
        "--timeframe",
        args.timeframe,
        "--tensor-path",
        str(tensor_path),
        "--meta-path",
        str(meta_path),
        "--flat-path",
        str(flat_path),
        "--builder-report",
        str(builder_report),
        "--chunk-size",
        str(args.chunk_size),
        "--full-scan",
        args.health_full_scan,
        "--max-scan-samples",
        str(args.health_max_scan_samples),
        "--fail-on-reported-feature-nonfinite",
        "1",
        "--storage-root",
        args.storage_root,
        "--output-dir",
        str(health_output_dir),
    ]


def stability_command(
    args: argparse.Namespace,
    candidate: PivotTargetCandidate,
    flat_path: Path,
    meta_path: Path,
    stability_output_dir: Path,
) -> list[str]:
    return [
        sys.executable,
        "-u",
        "scripts/audit_pivot_label_target_stability.py",
        "--symbol",
        args.symbol,
        "--timeframe",
        args.timeframe,
        "--flat-path",
        str(flat_path),
        "--meta-path",
        str(meta_path),
        "--max-samples",
        str(args.audit_max_samples),
        "--train-frac",
        str(args.train_frac),
        "--val-frac",
        str(args.val_frac),
        "--purge-gap",
        str(args.purge_gap),
        "--window-size",
        str(args.window_size),
        "--lookahead-bars",
        str(candidate.lookahead_bars),
        "--pivot-move-atr",
        str(candidate.pivot_move_atr),
        "--pivot-zone-atr",
        str(candidate.pivot_zone_atr),
        "--recent-window-bars",
        str(args.recent_window_bars),
        "--min-direction-edge",
        str(candidate.min_direction_edge),
        "--sensitivity-lookahead-bars",
        str(candidate.lookahead_bars),
        "--sensitivity-pivot-move-atrs",
        str(candidate.pivot_move_atr),
        "--sensitivity-pivot-zone-atrs",
        str(candidate.pivot_zone_atr),
        "--sensitivity-min-direction-edges",
        str(candidate.min_direction_edge),
        "--max-sensitivity-combinations",
        "1",
        "--psi-warning-threshold",
        str(args.psi_warning_threshold),
        "--storage-root",
        args.storage_root,
        "--output-dir",
        str(stability_output_dir),
        "--report-title",
        f"Phase153A {candidate.candidate_id} pivot target stability audit",
    ]


def load_json(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Expected report not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def nested_report(path: Path) -> Mapping[str, Any]:
    payload = load_json(path)
    return payload.get("report", payload) if isinstance(payload, Mapping) else {}


def read_split_rows(path: Path) -> dict[str, Mapping[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {str(row.get("split", "")): row for row in reader}


def number(row: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def integer(row: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return int(default)


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


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def candidate_row(
    args: argparse.Namespace,
    candidate: PivotTargetCandidate,
    build_dir: Path,
    health_dir: Path,
    stability_dir: Path,
) -> CandidateAuditRow:
    tensor_path, meta_path, flat_path = output_paths(args, candidate)
    build_json = build_dir / "latest.json"
    health_json = health_dir / "latest.json"
    stability_json = stability_dir / "latest.json"
    build_report = nested_report(build_json)
    health_report = nested_report(health_json)
    stability_report = nested_report(stability_json)
    splits = read_split_rows(stability_dir / "latest_splits.csv")
    train = splits.get("train", {})
    validation = splits.get("validation", {})
    test = splits.get("test", {})

    build_shape = build_report.get("stored_x_shape", [])
    health_scan = health_report.get("scan", {}) if isinstance(health_report, Mapping) else {}
    train_buy_r = number(train, "buy_r_mean")
    validation_buy_r = number(validation, "buy_r_mean")
    test_buy_r = number(test, "buy_r_mean")
    train_sell_r = number(train, "sell_r_mean")
    validation_sell_r = number(validation, "sell_r_mean")
    test_sell_r = number(test, "sell_r_mean")
    buy_flip = sign_flip(train_buy_r, validation_buy_r, test_buy_r)
    sell_flip = sign_flip(train_sell_r, validation_sell_r, test_sell_r)
    health_status = str(health_report.get("status", "SKIPPED"))
    validation_psi = float(stability_report.get("validation_psi_vs_train", 0.0))
    test_psi = float(stability_report.get("test_psi_vs_train", 0.0))
    label_pass = int(
        health_status == "PASS"
        and validation_psi <= float(args.psi_warning_threshold)
        and test_psi <= float(args.psi_warning_threshold)
    )
    payoff_warning = int(buy_flip or sell_flip)
    training_ready = int(label_pass and not payoff_warning)

    train_hold = number(train, "hold_rate")
    validation_hold = number(validation, "hold_rate")
    test_hold = number(test, "hold_rate")
    return CandidateAuditRow(
        candidate_id=candidate.candidate_id,
        label=candidate.label,
        output_name=candidate.output_name,
        lookahead_bars=int(candidate.lookahead_bars),
        pivot_move_atr=float(candidate.pivot_move_atr),
        pivot_zone_atr=float(candidate.pivot_zone_atr),
        recent_window_bars=int(args.recent_window_bars),
        min_direction_edge=float(candidate.min_direction_edge),
        tensor_path=str(tensor_path),
        meta_path=str(meta_path),
        flat_path=str(flat_path),
        build_output_dir=str(build_dir),
        health_output_dir=str(health_dir),
        stability_output_dir=str(stability_dir),
        build_json=str(build_json),
        health_json=str(health_json),
        stability_json=str(stability_json),
        build_samples=int(build_report.get("samples", 0)),
        build_tensor_shape=json_text(build_shape),
        build_target_counts=json_text(build_report.get("target_counts", {})),
        health_status=health_status,
        health_nonfinite_cells=int(health_scan.get("nonfinite_cells", 0)),
        health_max_abs=float(health_scan.get("max_abs", 0.0)),
        health_errors=json_text(health_report.get("errors", [])),
        health_warnings=json_text(health_report.get("warnings", [])),
        sampled_rows=int(stability_report.get("sampled_rows", 0)),
        train_rows=int(stability_report.get("train_rows", 0)),
        validation_rows=int(stability_report.get("validation_rows", 0)),
        test_rows=int(stability_report.get("test_rows", 0)),
        train_sell_rate=number(train, "sell_rate"),
        train_hold_rate=train_hold,
        train_buy_rate=number(train, "buy_rate"),
        validation_sell_rate=number(validation, "sell_rate"),
        validation_hold_rate=validation_hold,
        validation_buy_rate=number(validation, "buy_rate"),
        test_sell_rate=number(test, "sell_rate"),
        test_hold_rate=test_hold,
        test_buy_rate=number(test, "buy_rate"),
        train_actionable_rate=max(0.0, 1.0 - train_hold),
        validation_actionable_rate=max(0.0, 1.0 - validation_hold),
        test_actionable_rate=max(0.0, 1.0 - test_hold),
        validation_psi_vs_train=validation_psi,
        test_psi_vs_train=test_psi,
        train_buy_r_mean=train_buy_r,
        validation_buy_r_mean=validation_buy_r,
        test_buy_r_mean=test_buy_r,
        train_sell_r_mean=train_sell_r,
        validation_sell_r_mean=validation_sell_r,
        test_sell_r_mean=test_sell_r,
        buy_r_sign_flip=buy_flip,
        sell_r_sign_flip=sell_flip,
        label_stability_pass_gate=label_pass,
        target_payoff_warning_gate=payoff_warning,
        candidate_ready_for_training_gate=training_ready,
        stability_warnings=json_text(stability_report.get("warnings", [])),
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: PivotTargetRedesignReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{html.escape(str(row['label']))}</td>"
        f"<td>{int(row['lookahead_bars'])}</td>"
        f"<td>{float(row['pivot_move_atr']):.3f}</td>"
        f"<td>{float(row['pivot_zone_atr']):.3f}</td>"
        f"<td>{float(row['min_direction_edge']):.3f}</td>"
        f"<td>{html.escape(str(row['health_status']))}</td>"
        f"<td>{float(row['validation_psi_vs_train']):.4f}</td>"
        f"<td>{float(row['test_psi_vs_train']):.4f}</td>"
        f"<td>{float(row['train_actionable_rate']):.3f}</td>"
        f"<td>{float(row['validation_actionable_rate']):.3f}</td>"
        f"<td>{float(row['test_actionable_rate']):.3f}</td>"
        f"<td>{int(row['target_payoff_warning_gate'])}</td>"
        f"<td>{int(row['candidate_ready_for_training_gate'])}</td></tr>"
        for row in report.rows
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1360px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:13px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
.badge {{ display:inline-block; border:1px solid #64748b; border-radius:999px; padding:4px 10px; margin:2px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase153A builds candidate target tensors C1/C2 and audits health + label stability. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Summary</h2>
<p><span class="badge">completed={report.completed_candidates}</span><span class="badge">label stable={report.label_stable_candidates}</span><span class="badge">training ready={report.training_ready_candidates}</span></p>
<p>Training-ready requires tensor health PASS, split-level label PSI under the configured threshold, and no validation-to-test payoff sign flip in this diagnostic.</p></section>
<section class="card"><h2>Candidate rows</h2><table><thead><tr><th>ID</th><th>Label</th><th>Lookahead</th><th>Move</th><th>Zone</th><th>Edge</th><th>Health</th><th>Val PSI</th><th>Test PSI</th><th>Train actionable</th><th>Val actionable</th><th>Test actionable</th><th>Payoff warning</th><th>Ready</th></tr></thead><tbody>{rows}</tbody></table></section>
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
        print("  PHASE153A PIVOT TARGET REDESIGN CANDIDATE BUILD/AUDIT")
        print("=" * 74)
        candidates = parse_candidates(args.candidates)
        print("  candidates  : " + ", ".join(candidate.candidate_id for candidate in candidates))
        rows: list[CandidateAuditRow] = []
        for candidate in candidates:
            print("\n" + "-" * 74)
            print(
                f"  {candidate.candidate_id} {candidate.label}: lookahead={candidate.lookahead_bars} "
                f"move={candidate.pivot_move_atr} zone={candidate.pivot_zone_atr} edge={candidate.min_direction_edge}"
            )
            candidate_root = output_dir / candidate.slug
            build_dir = candidate_root / "build"
            health_dir = candidate_root / "health"
            stability_dir = candidate_root / "stability"
            build_dir.mkdir(parents=True, exist_ok=True)
            health_dir.mkdir(parents=True, exist_ok=True)
            stability_dir.mkdir(parents=True, exist_ok=True)
            tensor_path, meta_path, flat_path = output_paths(args, candidate)
            if args.skip_existing_tensors == "1" and tensor_path.exists() and meta_path.exists() and flat_path.exists():
                print(f"  [i] existing candidate tensor found; skipping build: {tensor_path}")
                if not (build_dir / "latest.json").exists():
                    raise RuntimeError(
                        "skip-existing-tensors=1 needs the candidate build report too: "
                        f"{build_dir / 'latest.json'}"
                    )
            else:
                run_command(build_tensor_command(args, candidate, build_dir), timeout_seconds)
            if args.skip_health_audit == "1":
                print(f"  [i] skip-health-audit=1 for {candidate.candidate_id}")
            else:
                run_command(
                    health_command(
                        args,
                        tensor_path,
                        meta_path,
                        flat_path,
                        build_dir / "latest.json",
                        health_dir,
                    ),
                    timeout_seconds,
                )
            if args.skip_stability_audit == "1":
                print(f"  [i] skip-stability-audit=1 for {candidate.candidate_id}")
            else:
                run_command(
                    stability_command(args, candidate, flat_path, meta_path, stability_dir),
                    timeout_seconds,
                )
            rows.append(candidate_row(args, candidate, build_dir, health_dir, stability_dir))

        row_dicts = [asdict(row) for row in rows]
        output_csv = output_dir / "latest.csv"
        write_csv(output_csv, row_dicts)
        report = PivotTargetRedesignReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            candidates=[asdict(candidate) for candidate in candidates],
            label_stability_psi_threshold=float(args.psi_warning_threshold),
            health_required_status="PASS",
            completed_candidates=len(row_dicts),
            label_stable_candidates=sum(int(row.label_stability_pass_gate) for row in rows),
            training_ready_candidates=sum(int(row.candidate_ready_for_training_gate) for row in rows),
            rows=row_dicts,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_csv=str(output_csv),
            production_status="BLOCKED — Phase153A research target redesign audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase153A candidate build/audit complete")
        print(f"  completed       : {report.completed_candidates}")
        print(f"  label stable    : {report.label_stable_candidates}")
        print(f"  training ready  : {report.training_ready_candidates}")
        print(f"  output          : {report.output_json}")
        print(f"  elapsed         : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
