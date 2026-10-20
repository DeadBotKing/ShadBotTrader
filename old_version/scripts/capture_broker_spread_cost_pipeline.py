"""Phase170A: broker spread capture / cost data pipeline.

This phase captures or imports real broker bid/ask spread samples and converts
that evidence into session summaries and spread/ATR cost tables. It is designed
to remove guesswork around XAUUSD cost assumptions before any future research
lane or target/model design.

Research-only. The script never sends orders and does not approve paper/live
trading.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_pivot_1h_entry_feasibility import read_ohlc_frame  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/broker_spread_capture")


@dataclass(frozen=True)
class SpreadSample:
    timestamp: str
    source_mode: str
    symbol: str
    broker_symbol: str
    bid: float
    ask: float
    last: float
    point: float
    digits: int
    spread_price: float
    spread_points: float
    session_utc: str
    weekday_utc: str
    raw_time: str


@dataclass(frozen=True)
class SpreadSummaryRow:
    group: str
    bucket: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    spread_price_mean: float
    spread_price_median: float
    spread_price_p90: float
    spread_price_p95: float
    spread_price_p99: float
    spread_points_mean: float
    spread_points_median: float
    spread_points_p90: float
    spread_points_p95: float
    spread_points_p99: float


@dataclass(frozen=True)
class TimeframeCostRow:
    timeframe: str
    flat_path: str
    status: str
    rows: int
    atr_mean: float
    atr_median: float
    atr_p90: float
    sample_spread_median: float
    sample_spread_p90: float
    sample_spread_p99: float
    median_spread_atr_median: float
    p90_spread_atr_median: float
    p99_spread_atr_median: float
    median_spread_atr_p90: float
    feasible_gate: int
    notes: str


@dataclass(frozen=True)
class Phase170Report:
    symbol: str
    broker_symbol: str
    source_mode: str
    generated_at_utc: str
    samples: int
    min_samples: int
    capture_duration_seconds: float
    interval_seconds: float
    first_timestamp: str
    last_timestamp: str
    spread_price_median: float
    spread_price_p90: float
    spread_price_p99: float
    spread_points_median: float
    spread_points_p90: float
    spread_points_p99: float
    sample_status: str
    broker_cost_reality_gate: int
    route_decision_context: str
    summary_rows: list[dict[str, Any]]
    timeframe_cost_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_samples_csv: str
    output_session_summary_csv: str
    output_timeframe_cost_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture/import broker XAUUSD spread samples and summarize cost reality.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--source-mode", choices=("mt5", "csv"), default="mt5")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--broker-symbol", default="")
    parser.add_argument("--sample-path", default="")
    parser.add_argument("--duration-seconds", type=float, default=600.0)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--mt5-terminal-path", default="")
    parser.add_argument("--mt5-login", type=int, default=0)
    parser.add_argument("--mt5-server", default="")
    parser.add_argument("--mt5-password-env", default="")
    parser.add_argument("--point", type=float, default=0.01)
    parser.add_argument("--digits", type=int, default=2)
    parser.add_argument("--m5-flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--h1-flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--h4-flat-path", default="datasets/processed/XAUUSD/4H/v1.parquet")
    parser.add_argument("--d1-flat-path", default="datasets/processed/XAUUSD/1D/v1.parquet")
    parser.add_argument("--timeframes", default="5M,1H")
    parser.add_argument("--max-median-spread-atr", type=float, default=0.12)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase170A broker spread capture / cost data pipeline")
    return parser.parse_args(argv)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        return result if np.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def session_utc(timestamp: pd.Timestamp | str) -> str:
    ts = pd.to_datetime(timestamp, utc=True, errors="coerce")
    if pd.isna(ts):
        return "unknown"
    hour = int(ts.hour)
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london_morning"
    if 13 <= hour < 17:
        return "london_ny_overlap"
    if 17 <= hour < 21:
        return "ny_late"
    return "rollover"


def weekday_utc(timestamp: pd.Timestamp | str) -> str:
    ts = pd.to_datetime(timestamp, utc=True, errors="coerce")
    if pd.isna(ts):
        return "unknown"
    return str(ts.day_name())


def normalize_sample(
    raw: Mapping[str, Any],
    source_mode: str,
    symbol: str,
    broker_symbol: str,
    default_point: float,
    default_digits: int,
) -> SpreadSample | None:
    timestamp_value = raw.get("timestamp", raw.get("time", raw.get("datetime", "")))
    if timestamp_value in {None, ""}:
        timestamp = pd.Timestamp.utcnow()
    else:
        timestamp = pd.to_datetime(timestamp_value, utc=True, errors="coerce")
        if pd.isna(timestamp):
            timestamp = pd.Timestamp.utcnow()
    if str(source_mode).lower() == "mt5" and timestamp < pd.Timestamp("2000-01-01", tz="UTC"):
        return None
    bid = safe_float(raw.get("bid"), np.nan)
    ask = safe_float(raw.get("ask"), np.nan)
    last = safe_float(raw.get("last", raw.get("price", raw.get("close"))), np.nan)
    point = safe_float(raw.get("point"), default_point)
    digits = safe_int(raw.get("digits"), default_digits)
    has_bid_ask = "bid" in raw and "ask" in raw
    spread_from_column = safe_float(raw.get("spread_price", raw.get("spread", raw.get("spread_value"))), np.nan)
    if np.isfinite(bid) and np.isfinite(ask) and ask >= bid and bid > 0 and ask > 0:
        spread_price = ask - bid
    else:
        spread_price = spread_from_column
    if has_bid_ask and (not np.isfinite(spread_from_column)) and (not np.isfinite(bid) or not np.isfinite(ask) or bid <= 0 or ask <= 0 or ask < bid):
        return None
    if not np.isfinite(spread_price) or spread_price < 0:
        return None
    spread_points = safe_float(raw.get("spread_points"), np.nan)
    if not np.isfinite(spread_points):
        spread_points = spread_price / max(point, 1e-12) if point > 0 else 0.0
    if not np.isfinite(last):
        last = (bid + ask) / 2.0 if np.isfinite(bid) and np.isfinite(ask) else 0.0
    ts_iso = pd.Timestamp(timestamp).isoformat()
    return SpreadSample(
        timestamp=ts_iso,
        source_mode=str(source_mode),
        symbol=str(symbol),
        broker_symbol=str(broker_symbol or symbol),
        bid=float(bid) if np.isfinite(bid) else 0.0,
        ask=float(ask) if np.isfinite(ask) else 0.0,
        last=float(last) if np.isfinite(last) else 0.0,
        point=float(point),
        digits=int(digits),
        spread_price=float(spread_price),
        spread_points=float(spread_points),
        session_utc=session_utc(timestamp),
        weekday_utc=weekday_utc(timestamp),
        raw_time=str(timestamp_value),
    )


def load_csv_samples(args: argparse.Namespace) -> list[SpreadSample]:
    path = Path(str(args.sample_path))
    if not path.exists():
        raise RuntimeError(f"spread sample CSV/parquet not found: {path}")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    samples: list[SpreadSample] = []
    broker_symbol = str(args.broker_symbol or args.symbol)
    for row in frame.to_dict(orient="records"):
        sample = normalize_sample(row, "csv", str(args.symbol), broker_symbol, float(args.point), int(args.digits))
        if sample is not None:
            samples.append(sample)
    return samples


def capture_mt5_samples(args: argparse.Namespace) -> list[SpreadSample]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("MetaTrader5 package is required for --source-mode mt5") from exc

    initialize_kwargs: dict[str, Any] = {}
    if str(args.mt5_terminal_path).strip():
        initialize_kwargs["path"] = str(args.mt5_terminal_path).strip()
    if not mt5.initialize(**initialize_kwargs):
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    try:
        if int(args.mt5_login) > 0:
            password = os.environ.get(str(args.mt5_password_env), "") if str(args.mt5_password_env).strip() else ""
            if not password:
                raise RuntimeError("--mt5-login requires --mt5-password-env to point to a populated environment variable")
            if not mt5.login(int(args.mt5_login), password=password, server=str(args.mt5_server)):
                raise RuntimeError(f"mt5.login failed: {mt5.last_error()}")
        broker_symbol = str(args.broker_symbol or args.symbol)
        if not mt5.symbol_select(broker_symbol, True):
            raise RuntimeError(f"mt5.symbol_select failed for {broker_symbol}: {mt5.last_error()}")
        info = mt5.symbol_info(broker_symbol)
        point = float(getattr(info, "point", args.point) or args.point) if info is not None else float(args.point)
        digits = int(getattr(info, "digits", args.digits) or args.digits) if info is not None else int(args.digits)
        samples: list[SpreadSample] = []
        start = time.monotonic()
        while True:
            tick = mt5.symbol_info_tick(broker_symbol)
            now = pd.Timestamp.utcnow()
            if tick is not None:
                tick_time = getattr(tick, "time_msc", 0)
                if tick_time:
                    timestamp = pd.to_datetime(int(tick_time), unit="ms", utc=True, errors="coerce")
                else:
                    timestamp = pd.to_datetime(getattr(tick, "time", now.timestamp()), unit="s", utc=True, errors="coerce")
                raw = {
                    "timestamp": timestamp if not pd.isna(timestamp) else now,
                    "bid": getattr(tick, "bid", np.nan),
                    "ask": getattr(tick, "ask", np.nan),
                    "last": getattr(tick, "last", np.nan),
                    "point": point,
                    "digits": digits,
                }
                sample = normalize_sample(raw, "mt5", str(args.symbol), broker_symbol, point, digits)
                if sample is not None:
                    samples.append(sample)
            if int(args.max_samples) > 0 and len(samples) >= int(args.max_samples):
                break
            if time.monotonic() - start >= float(args.duration_seconds):
                break
            time.sleep(max(float(args.interval_seconds), 0.1))
        return samples
    finally:
        mt5.shutdown()


def percentile(values: np.ndarray, pct: float) -> float:
    clean = values[np.isfinite(values)]
    if len(clean) == 0:
        return 0.0
    return float(np.percentile(clean, pct))


def spread_summary(samples: Sequence[SpreadSample], group: str, bucket_getter) -> list[SpreadSummaryRow]:
    buckets: dict[str, list[SpreadSample]] = {}
    for sample in samples:
        buckets.setdefault(str(bucket_getter(sample)), []).append(sample)
    rows: list[SpreadSummaryRow] = []
    for bucket, items in sorted(buckets.items()):
        prices = np.asarray([item.spread_price for item in items], dtype=np.float64)
        points = np.asarray([item.spread_points for item in items], dtype=np.float64)
        timestamps = sorted(item.timestamp for item in items)
        rows.append(
            SpreadSummaryRow(
                group=group,
                bucket=bucket,
                rows=len(items),
                first_timestamp=timestamps[0] if timestamps else "",
                last_timestamp=timestamps[-1] if timestamps else "",
                spread_price_mean=float(np.mean(prices)) if len(prices) else 0.0,
                spread_price_median=percentile(prices, 50),
                spread_price_p90=percentile(prices, 90),
                spread_price_p95=percentile(prices, 95),
                spread_price_p99=percentile(prices, 99),
                spread_points_mean=float(np.mean(points)) if len(points) else 0.0,
                spread_points_median=percentile(points, 50),
                spread_points_p90=percentile(points, 90),
                spread_points_p95=percentile(points, 95),
                spread_points_p99=percentile(points, 99),
            )
        )
    return rows


def timeframe_path(args: argparse.Namespace, timeframe: str) -> Path:
    tf = timeframe.upper()
    if tf == "5M":
        return Path(args.m5_flat_path)
    if tf == "1H":
        return Path(args.h1_flat_path)
    if tf == "4H":
        return Path(args.h4_flat_path)
    if tf == "1D":
        return Path(args.d1_flat_path)
    return Path(args.storage_root) / "processed" / str(args.symbol).upper() / tf / "v1.parquet"


def parse_timeframes(text: str) -> list[str]:
    values = [item.strip().upper() for item in str(text or "").replace(";", ",").split(",") if item.strip()]
    return values or ["5M", "1H"]


def timeframe_cost_rows(args: argparse.Namespace, samples: Sequence[SpreadSample]) -> list[TimeframeCostRow]:
    spreads = np.asarray([sample.spread_price for sample in samples], dtype=np.float64)
    spread_median = percentile(spreads, 50)
    spread_p90 = percentile(spreads, 90)
    spread_p99 = percentile(spreads, 99)
    rows: list[TimeframeCostRow] = []
    for timeframe in parse_timeframes(str(args.timeframes)):
        path = timeframe_path(args, timeframe)
        if not path.exists():
            rows.append(
                TimeframeCostRow(
                    timeframe=timeframe,
                    flat_path=str(path),
                    status="MISSING",
                    rows=0,
                    atr_mean=0.0,
                    atr_median=0.0,
                    atr_p90=0.0,
                    sample_spread_median=spread_median,
                    sample_spread_p90=spread_p90,
                    sample_spread_p99=spread_p99,
                    median_spread_atr_median=0.0,
                    p90_spread_atr_median=0.0,
                    p99_spread_atr_median=0.0,
                    median_spread_atr_p90=0.0,
                    feasible_gate=0,
                    notes="timeframe flat path missing",
                )
            )
            continue
        try:
            frame = read_ohlc_frame(path, 0)
            atr = resolve_atr(frame)
            atr_clean = atr[np.isfinite(atr) & (atr > 0)]
            atr_median = percentile(atr_clean, 50)
            atr_p90 = percentile(atr_clean, 90)
            median_ratio = spread_median / max(atr_median, 1e-9)
            rows.append(
                TimeframeCostRow(
                    timeframe=timeframe,
                    flat_path=str(path),
                    status="PASS",
                    rows=int(len(frame)),
                    atr_mean=float(np.mean(atr_clean)) if len(atr_clean) else 0.0,
                    atr_median=atr_median,
                    atr_p90=atr_p90,
                    sample_spread_median=spread_median,
                    sample_spread_p90=spread_p90,
                    sample_spread_p99=spread_p99,
                    median_spread_atr_median=median_ratio,
                    p90_spread_atr_median=spread_p90 / max(atr_median, 1e-9),
                    p99_spread_atr_median=spread_p99 / max(atr_median, 1e-9),
                    median_spread_atr_p90=spread_median / max(atr_p90, 1e-9),
                    feasible_gate=int(median_ratio <= float(args.max_median_spread_atr)),
                    notes="",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive CLI behavior.
            rows.append(
                TimeframeCostRow(
                    timeframe=timeframe,
                    flat_path=str(path),
                    status="ERROR",
                    rows=0,
                    atr_mean=0.0,
                    atr_median=0.0,
                    atr_p90=0.0,
                    sample_spread_median=spread_median,
                    sample_spread_p90=spread_p90,
                    sample_spread_p99=spread_p99,
                    median_spread_atr_median=0.0,
                    p90_spread_atr_median=0.0,
                    p99_spread_atr_median=0.0,
                    median_spread_atr_p90=0.0,
                    feasible_gate=0,
                    notes=f"{type(exc).__name__}: {exc}",
                )
            )
    return rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase170Report) -> str:
    summary_rows = "".join(
        f"<tr><td>{html.escape(str(row['group']))}</td>"
        f"<td>{html.escape(str(row['bucket']))}</td>"
        f"<td>{int(row['rows'])}</td>"
        f"<td>{float(row['spread_price_median']):.5f}</td>"
        f"<td>{float(row['spread_price_p90']):.5f}</td>"
        f"<td>{float(row['spread_price_p99']):.5f}</td>"
        f"<td>{float(row['spread_points_median']):.2f}</td></tr>"
        for row in report.summary_rows
    )
    cost_rows = "".join(
        f"<tr><td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['atr_median']):.5f}</td>"
        f"<td>{float(row['sample_spread_median']):.5f}</td>"
        f"<td>{float(row['median_spread_atr_median']):.5f}</td>"
        f"<td>{float(row['p90_spread_atr_median']):.5f}</td>"
        f"<td>{int(row['feasible_gate'])}</td></tr>"
        for row in report.timeframe_cost_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase170A broker spread capture and cost data pipeline. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'samples': report.samples,
        'sample_status': report.sample_status,
        'broker_cost_reality_gate': report.broker_cost_reality_gate,
        'spread_price_median': report.spread_price_median,
        'spread_price_p90': report.spread_price_p90,
        'spread_points_median': report.spread_points_median,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Spread summaries</h2><table><thead><tr><th>Group</th><th>Bucket</th><th>Rows</th><th>Median</th><th>P90</th><th>P99</th><th>Median points</th></tr></thead><tbody>{summary_rows}</tbody></table></section>
<section class="card"><h2>Spread / ATR by timeframe</h2><table><thead><tr><th>TF</th><th>Status</th><th>ATR median</th><th>Spread median</th><th>Median/ATR</th><th>P90/ATR</th><th>Gate</th></tr></thead><tbody>{cost_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE170A BROKER SPREAD CAPTURE / COST DATA PIPELINE")
        print("=" * 74)
        if str(args.source_mode) == "csv":
            samples = load_csv_samples(args)
        else:
            samples = capture_mt5_samples(args)
        if not samples:
            raise RuntimeError("No valid spread samples captured/imported")
        prices = np.asarray([sample.spread_price for sample in samples], dtype=np.float64)
        points = np.asarray([sample.spread_points for sample in samples], dtype=np.float64)
        timestamps = sorted(sample.timestamp for sample in samples)
        summary_rows = []
        summary_rows.extend(spread_summary(samples, "all", lambda _sample: "all"))
        summary_rows.extend(spread_summary(samples, "session_utc", lambda sample: sample.session_utc))
        summary_rows.extend(spread_summary(samples, "weekday_utc", lambda sample: sample.weekday_utc))
        cost_rows = timeframe_cost_rows(args, samples)
        sample_status = "PASS" if len(samples) >= int(args.min_samples) else "LOW_SAMPLE_COUNT"
        broker_cost_gate = int(sample_status == "PASS" and any(row.feasible_gate for row in cost_rows if row.status == "PASS"))
        samples_csv = output_dir / "latest_spread_samples.csv"
        summary_csv = output_dir / "latest_session_summary.csv"
        cost_csv = output_dir / "latest_timeframe_cost.csv"
        write_csv(samples_csv, [asdict(sample) for sample in samples])
        write_csv(summary_csv, [asdict(row) for row in summary_rows])
        write_csv(cost_csv, [asdict(row) for row in cost_rows])
        report = Phase170Report(
            symbol=str(args.symbol),
            broker_symbol=str(args.broker_symbol or args.symbol),
            source_mode=str(args.source_mode),
            generated_at_utc=pd.Timestamp.utcnow().isoformat(),
            samples=int(len(samples)),
            min_samples=int(args.min_samples),
            capture_duration_seconds=float(args.duration_seconds),
            interval_seconds=float(args.interval_seconds),
            first_timestamp=timestamps[0] if timestamps else "",
            last_timestamp=timestamps[-1] if timestamps else "",
            spread_price_median=percentile(prices, 50),
            spread_price_p90=percentile(prices, 90),
            spread_price_p99=percentile(prices, 99),
            spread_points_median=percentile(points, 50),
            spread_points_p90=percentile(points, 90),
            spread_points_p99=percentile(points, 99),
            sample_status=sample_status,
            broker_cost_reality_gate=broker_cost_gate,
            route_decision_context="Current 5M/1H locked pivot routes are rejected by documented prior results; this phase only validates broker cost reality.",
            summary_rows=[asdict(row) for row in summary_rows],
            timeframe_cost_rows=[asdict(row) for row in cost_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_samples_csv=str(samples_csv),
            output_session_summary_csv=str(summary_csv),
            output_timeframe_cost_csv=str(cost_csv),
            production_status="BLOCKED — Phase170A broker spread/cost data only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase170A broker spread capture complete")
        print(f"  samples          : {report.samples}")
        print(f"  sample status    : {report.sample_status}")
        print(f"  median spread    : {report.spread_price_median:.5f}")
        print(f"  p90 spread       : {report.spread_price_p90:.5f}")
        print(f"  median points    : {report.spread_points_median:.2f}")
        print(f"  cost gate        : {report.broker_cost_reality_gate}")
        print(f"  output           : {report.output_json}")
        print(f"  elapsed          : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
