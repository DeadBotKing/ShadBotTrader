"""Phase132A: compare base hybrid vs meta-filtered chronological variants.

This script evaluates several candidate filters on the same Phase127 telemetry
rows. It writes a comparison table plus an HTML replay for the selected best
candidate. Missing optional models are skipped by default so the operator can
run the comparison as models become available.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import pickle
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from backtest_hybrid_meta_labeler import (
    MetaThresholdSpec,
    positive_scores,
)
from backtest_hybrid_meta_labeler import (
    backtest as backtest_flat_meta,
)
from backtest_hybrid_telemetry_wavenet import (
    TelemetryWaveNetThresholds,
    load_wavenet_artifact,
    normalize_with_payload,
)
from backtest_hybrid_telemetry_wavenet import (
    backtest as backtest_tensor_meta,
)
from report_hybrid_full_backtest import (
    DetailedTrade,
    FixedBacktestSummary,
    account_summary,
    load_candles,
    monthly_summary,
    render_html,
    replay_candles_for_indices,
)
from train_hybrid_telemetry_wavenet import default_tensor_path, load_tensor, prediction_arrays

from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_meta_comparison")
DEFAULT_CANDIDATES = (
    "base,"
    "gold_hybrid_meta_lightgbm_5m,"
    "gold_hybrid_telemetry_wavenet_5m,"
    "gold_hybrid_telemetry_tsmixer_5m,"
    "gold_hybrid_telemetry_patchtst_5m"
)
SCORE_METRICS = ("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted")
DECISION_MODES = ("meta", "score", "both")


@dataclass(frozen=True)
class CandidateSpec:
    model_id: str
    version: int

    @property
    def is_base(self) -> bool:
        return self.model_id == "base"


@dataclass(frozen=True)
class ComparisonRow:
    candidate: str
    model_id: str
    version: int
    model_type: str
    decision_mode: str
    meta_threshold: float
    score_threshold: float
    status: str
    warning: str
    samples: int
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    timeouts: int
    skipped_by_filter: int
    skipped_while_open: int
    win_rate: float
    label_precision: float
    total_pnl: float
    avg_pnl: float
    profit_factor: float
    max_drawdown: float
    coverage: float
    final_balance: float
    net_profit: float
    return_percent: float
    would_breach_zero: bool
    score: float


@dataclass(frozen=True)
class BestReplay:
    row: ComparisonRow
    summary: FixedBacktestSummary
    trades: list[DetailedTrade]
    source_indices: list[int]
    threshold: Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare base and meta-filtered hybrid chronological backtests.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--candidate-versions", default="0")
    parser.add_argument("--decision-modes", default="meta")
    parser.add_argument("--meta-thresholds", default="record")
    parser.add_argument("--score-thresholds", default="0")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--skip-missing", choices=("0", "1"), default="1")
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
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Hybrid meta-filter comparison")
    return parser.parse_args(argv)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def parse_candidates(text: str, versions: str) -> list[CandidateSpec]:
    names = [item.strip() for item in text.split(",") if item.strip()]
    raw_versions = [item.strip() for item in versions.split(",") if item.strip()]
    if not raw_versions:
        raw_versions = ["0"]
    specs: list[CandidateSpec] = []
    for index, name in enumerate(names):
        version_text = raw_versions[index] if index < len(raw_versions) else raw_versions[-1]
        try:
            version = int(version_text)
        except ValueError:
            version = 0
        specs.append(CandidateSpec(model_id=name, version=max(version, 0)))
    return specs


def parse_float_options(text: str, allow_record: bool) -> list[float | None]:
    values: list[float | None] = []
    for token in (item.strip().lower() for item in text.split(",")):
        if not token:
            continue
        if allow_record and token in ("record", "saved", "auto"):
            values.append(None)
            continue
        values.append(float(token))
    return values or ([None] if allow_record else [0.0])


def parse_modes(text: str) -> list[str]:
    modes = [item.strip().lower() for item in text.split(",") if item.strip()]
    return [mode for mode in modes if mode in DECISION_MODES] or ["meta"]


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def max_drawdown(pnls: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def score_value(summary: FixedBacktestSummary, account: Mapping[str, Any], metric: str) -> float:
    if metric == "profit_factor":
        return summary.profit_factor
    if metric == "final_balance":
        return float(account["final_balance"])
    if metric == "drawdown_adjusted":
        return summary.total_pnl - summary.max_drawdown
    return summary.total_pnl


def flat_by_source(frame: pd.DataFrame) -> dict[int, pd.Series]:
    return {int(row["source_index"]): row for _, row in frame.iterrows()}


def align_flat_to_sources(frame: pd.DataFrame, source_indices: Sequence[int]) -> pd.DataFrame:
    lookup = flat_by_source(frame)
    rows = [lookup[int(source)] for source in source_indices if int(source) in lookup]
    if not rows:
        raise RuntimeError("No flat telemetry rows matched the selected tensor source indices")
    return pd.DataFrame(rows).reset_index(drop=True)


def base_backtest(
    frame: pd.DataFrame,
) -> tuple[FixedBacktestSummary, Any, list[DetailedTrade], Any]:
    scores = np.ones(len(frame), dtype=np.float64)
    threshold = MetaThresholdSpec(0.0, 0.0, "base")
    summary, counters, trades = backtest_flat_meta(frame, scores, threshold, task="classifier")
    return summary, counters, trades, threshold


def load_pickle_payload(storage_root: Path, spec: CandidateSpec) -> tuple[dict[str, Any], int]:
    catalogue = ModelCatalogue(storage_root)
    version = spec.version if spec.version > 0 else catalogue.latest_version(spec.model_id)
    if version < 1:
        raise RuntimeError(f"No saved model record found for {spec.model_id}")
    artifact = FilesystemArtifactStore(storage_root).load(
        ModelId(spec.model_id), ModelVersion(version)
    )
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {spec.model_id} v{version}")
    try:
        payload = pickle.loads(artifact.payload)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Could not load {spec.model_id}; install optional model dependency: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"Unexpected artifact payload for {spec.model_id}")
    return dict(payload), version


def saved_thresholds(
    storage_root: Path,
    model_id: str,
    version: int,
    meta_override: float | None,
    score_threshold: float,
    mode: str,
) -> tuple[float, float, str]:
    if meta_override is not None:
        return float(meta_override), float(score_threshold), "cli"
    record = ModelCatalogue(storage_root).read(model_id, version)
    thresholds = record.decision_thresholds if record else {}
    try:
        meta = float((thresholds or {}).get("meta_threshold", 0.55))
    except (TypeError, ValueError):
        meta = 0.55
    try:
        score = float(
            score_threshold
            if score_threshold != 0.0
            else (thresholds or {}).get("score_threshold", 0.0)
        )
    except (TypeError, ValueError):
        score = float(score_threshold)
    return meta, score, f"model_record:{model_id}:v{version}:{mode}"


def run_flat_candidate(
    frame: pd.DataFrame,
    payload: Mapping[str, Any],
    storage_root: Path,
    spec: CandidateSpec,
    version: int,
    meta_threshold: float | None,
    score_threshold: float,
    mode: str,
) -> tuple[FixedBacktestSummary, Any, list[DetailedTrade], Any]:
    model = payload.get("model")
    features = payload.get("feature_names")
    if model is None or not isinstance(features, Sequence) or isinstance(features, str):
        raise RuntimeError("Flat meta artifact must contain model and feature_names")
    feature_names = [str(name) for name in features]
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise RuntimeError(f"Flat telemetry is missing model features: {missing[:5]}")
    task = str(payload.get("task", "classifier"))
    meta, score, source = saved_thresholds(
        storage_root, spec.model_id, version, meta_threshold, score_threshold, mode
    )
    threshold = MetaThresholdSpec(meta, score, source)
    scores = positive_scores(model, frame[feature_names].to_numpy(dtype=np.float32), task)
    summary, counters, trades = backtest_flat_meta(frame, scores, threshold, task=task)
    return summary, counters, trades, threshold


def run_tensor_candidate(
    data: Mapping[str, Any],
    selected: np.ndarray,
    flat_lookup: Mapping[int, pd.Series],
    payload: Mapping[str, Any],
    storage_root: Path,
    spec: CandidateSpec,
    version: int,
    meta_threshold: float | None,
    score_threshold: float,
    mode: str,
) -> tuple[FixedBacktestSummary, Any, list[DetailedTrade], Any]:
    model, loaded_payload, loaded_version = load_wavenet_artifact(
        storage_root, spec.model_id, version
    )
    payload = {**payload, **loaded_payload}
    task = str(payload.get("task", "multihead"))
    meta, score, source = saved_thresholds(
        storage_root, spec.model_id, loaded_version, meta_threshold, score_threshold, mode
    )
    threshold = TelemetryWaveNetThresholds(meta, score, mode, source)
    x_values = normalize_with_payload(np.asarray(data["X"], dtype=np.float32)[selected], payload)
    win_scores, score_scores = prediction_arrays(model, x_values, task)
    if task == "regressor":
        win_scores = np.ones_like(score_scores, dtype=np.float64)
    candidate_mask = np.asarray(
        data.get("candidate_mask", np.ones(len(data["X"]))), dtype=np.float32
    )[selected]
    source_indices = np.asarray(data["source_index"], dtype=np.int64)[selected]
    summary, counters, trades = backtest_tensor_meta(
        source_indices, candidate_mask, win_scores, score_scores, flat_lookup, threshold
    )
    return summary, counters, trades, threshold


def row_from_result(
    name: str,
    spec: CandidateSpec,
    version: int,
    model_type: str,
    mode: str,
    threshold: Any,
    summary: FixedBacktestSummary,
    counters: Any,
    account: Mapping[str, Any],
    metric: str,
) -> ComparisonRow:
    skipped_filter = int(
        getattr(counters, "skipped_by_meta", getattr(counters, "skipped_by_wavenet", 0))
    )
    return ComparisonRow(
        candidate=name,
        model_id=spec.model_id,
        version=version,
        model_type=model_type,
        decision_mode=mode,
        meta_threshold=float(getattr(threshold, "meta_threshold", 0.0)),
        score_threshold=float(getattr(threshold, "score_threshold", 0.0)),
        status="ok",
        warning="",
        samples=summary.samples,
        trades=summary.trades,
        buy_trades=summary.buy_trades,
        sell_trades=summary.sell_trades,
        wins=summary.wins,
        losses=summary.losses,
        timeouts=summary.timeouts,
        skipped_by_filter=skipped_filter,
        skipped_while_open=int(getattr(counters, "skipped_while_open", 0)),
        win_rate=summary.win_rate,
        label_precision=summary.label_precision,
        total_pnl=summary.total_pnl,
        avg_pnl=summary.avg_pnl,
        profit_factor=summary.profit_factor,
        max_drawdown=summary.max_drawdown,
        coverage=summary.coverage,
        final_balance=float(account["final_balance"]),
        net_profit=float(account["net_profit"]),
        return_percent=float(account["return_percent"]),
        would_breach_zero=bool(account["would_breach_zero"]),
        score=score_value(summary, account, metric),
    )


def skipped_row(spec: CandidateSpec, warning: str) -> ComparisonRow:
    return ComparisonRow(
        candidate=spec.model_id,
        model_id=spec.model_id,
        version=spec.version,
        model_type="unknown",
        decision_mode="",
        meta_threshold=0.0,
        score_threshold=0.0,
        status="skipped",
        warning=warning,
        samples=0,
        trades=0,
        buy_trades=0,
        sell_trades=0,
        wins=0,
        losses=0,
        timeouts=0,
        skipped_by_filter=0,
        skipped_while_open=0,
        win_rate=0.0,
        label_precision=0.0,
        total_pnl=0.0,
        avg_pnl=0.0,
        profit_factor=0.0,
        max_drawdown=0.0,
        coverage=0.0,
        final_balance=0.0,
        net_profit=0.0,
        return_percent=0.0,
        would_breach_zero=False,
        score=-1e18,
    )


def select_best(rows: Sequence[ComparisonRow], min_trades: int) -> ComparisonRow | None:
    candidates = [row for row in rows if row.status == "ok" and row.trades >= min_trades]
    return max(
        candidates, key=lambda row: (row.score, row.profit_factor, -row.max_drawdown), default=None
    )


def write_csv(path: Path, rows: Sequence[ComparisonRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def comparison_html(rows: Sequence[ComparisonRow], best: ComparisonRow | None, title: str) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.candidate)}</td>"
        f"<td>{html.escape(row.status)}</td>"
        f"<td>{html.escape(row.model_type)}</td>"
        f"<td>{html.escape(row.decision_mode)}</td>"
        f"<td>{row.trades:,}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        f"<td>{row.max_drawdown:.2f}</td>"
        f"<td>{row.final_balance:.2f}</td>"
        f"<td>{row.coverage:.2%}</td>"
        f"<td>{html.escape(row.warning)}</td>"
        "</tr>"
        for row in rows
    )
    best_text = "none" if best is None else best.candidate
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; background:#020617; color:#e2e8f0; padding:24px; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th,td {{ border-bottom:1px solid #1e293b; padding:8px; text-align:left; }}
th {{ color:#bae6fd; }}
.card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:14px; margin-bottom:16px; }}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="card">Best candidate: <b>{html.escape(best_text)}</b>. Open <code>best_replay.html</code> for the selected replay.</div>
<table><thead><tr><th>candidate</th><th>status</th><th>type</th><th>mode</th><th>trades</th><th>pnl</th><th>PF</th><th>DD</th><th>final</th><th>coverage</th><th>warning</th></tr></thead><tbody>{body}</tbody></table>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE132 META-FILTERED HYBRID COMPARISON")
        print(f"  flat        : {flat_path}")
        print(f"  tensor      : {tensor_path}")
        flat_all = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        data = load_tensor(tensor_path) if tensor_path.exists() else None
        if data is not None:
            selected = eval_indices(len(data["X"]), args.eval_frac, args.max_windows)
            source_indices = np.asarray(data["source_index"], dtype=np.int64)[selected]
            eval_flat = align_flat_to_sources(flat_all, source_indices)
        else:
            selected = np.asarray([], dtype=np.int64)
            source_indices = np.asarray([], dtype=np.int64)
            indices = eval_indices(len(flat_all), args.eval_frac, args.max_windows)
            eval_flat = flat_all.iloc[indices].copy().reset_index(drop=True)
        lookup = flat_by_source(flat_all)
        specs = parse_candidates(args.candidates, args.candidate_versions)
        meta_options = parse_float_options(args.meta_thresholds, allow_record=True)
        score_options = parse_float_options(args.score_thresholds, allow_record=False)
        modes = parse_modes(args.decision_modes)
        rows: list[ComparisonRow] = []
        best_replays: list[BestReplay] = []

        for spec in specs:
            try:
                if spec.is_base:
                    summary, counters, trades, threshold = base_backtest(eval_flat)
                    account = account_summary(summary, args.initial_capital, args.units)
                    row = row_from_result(
                        "base",
                        spec,
                        0,
                        "base",
                        "none",
                        threshold,
                        summary,
                        counters,
                        account,
                        args.score_metric,
                    )
                    rows.append(row)
                    best_replays.append(
                        BestReplay(
                            row,
                            summary,
                            trades,
                            eval_flat["source_index"].astype(int).tolist(),
                            threshold,
                        )
                    )
                    continue

                payload, version = load_pickle_payload(storage_root, spec)
                model_type = "tensor" if "model_bytes" in payload else "flat"
                if model_type == "tensor" and data is None:
                    raise RuntimeError("Tensor model comparison needs --tensor-path")
                for mode in (modes if model_type == "tensor" else ["meta"]):
                    for meta_threshold in meta_options:
                        for score_threshold in score_options:
                            if model_type == "flat":
                                summary, counters, trades, threshold = run_flat_candidate(
                                    eval_flat,
                                    payload,
                                    storage_root,
                                    spec,
                                    version,
                                    meta_threshold,
                                    float(score_threshold or 0.0),
                                    mode,
                                )
                                source_list = eval_flat["source_index"].astype(int).tolist()
                            else:
                                summary, counters, trades, threshold = run_tensor_candidate(
                                    data or {},
                                    selected,
                                    lookup,
                                    payload,
                                    storage_root,
                                    spec,
                                    version,
                                    meta_threshold,
                                    float(score_threshold or 0.0),
                                    mode,
                                )
                                source_list = source_indices.astype(int).tolist()
                            account = account_summary(summary, args.initial_capital, args.units)
                            name = f"{spec.model_id}:{mode}:meta={meta_threshold if meta_threshold is not None else 'record'}:score={score_threshold}"
                            row = row_from_result(
                                name,
                                spec,
                                version,
                                model_type,
                                mode,
                                threshold,
                                summary,
                                counters,
                                account,
                                args.score_metric,
                            )
                            rows.append(row)
                            best_replays.append(
                                BestReplay(row, summary, trades, source_list, threshold)
                            )
            except Exception as error:
                if args.skip_missing == "1":
                    rows.append(skipped_row(spec, f"{type(error).__name__}: {error}"))
                    continue
                raise

        if not rows:
            raise RuntimeError("No comparison rows were produced")
        best = select_best(rows, args.min_trades)
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        html_path = out_dir / "latest.html"
        best_replay_path = out_dir / "best_replay.html"
        write_csv(csv_path, rows)
        html_path.write_text(comparison_html(rows, best, args.report_title), encoding="utf-8")
        if best is not None:
            replay = next(item for item in best_replays if item.row == best)
            candles = load_candles(storage_root, args.symbol, args.timeframe)
            monthly = monthly_summary(replay.trades)
            best_replay_path.write_text(
                render_html(
                    f"{args.report_title} — best replay",
                    args,
                    tensor_path if best.model_type == "tensor" else flat_path,
                    best.version,
                    replay.threshold,
                    replay.summary,
                    replay.trades,
                    monthly,
                    replay_candles_for_indices(candles, replay.source_indices, replay.trades),
                ),
                encoding="utf-8",
            )
        payload = {
            "args": vars(args),
            "rows": [asdict(row) for row in rows],
            "best": asdict(best) if best else None,
            "files": {
                "csv": str(csv_path),
                "json": str(json_path),
                "html": str(html_path),
                "best_replay_html": str(best_replay_path),
            },
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rule("DONE")
        print(f"  rows        : {len(rows):,}")
        print(f"  best        : {best.candidate if best else 'none'}")
        if best is not None:
            print(f"  best pnl    : {best.total_pnl:+.2f}")
            print(f"  best PF     : {best.profit_factor:.3f}")
            print(f"  best trades : {best.trades:,}")
        print(f"  report      : {json_path}")
        print(f"  html        : {html_path}")
        print(f"  replay      : {best_replay_path}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
