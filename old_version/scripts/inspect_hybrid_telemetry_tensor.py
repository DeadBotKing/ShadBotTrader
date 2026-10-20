"""Inspect and visualize the Phase127 hybrid telemetry 3D tensor.

The tensor is too large to understand as raw numbers. This script turns a small
set of selected tensor samples into a self-contained HTML report with axis
metadata, target values, channel grouping and per-sample heatmaps.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import html
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_tensor_inspector")

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise RuntimeError("Install numpy before inspecting telemetry tensors") from exc


@dataclass(frozen=True)
class TensorInspectionReport:
    tensor_path: str
    flat_path: str
    shape: list[int]
    dtype: str
    samples: int
    tensor_window: int
    channels: int
    estimated_uncompressed_mb: float
    selected_sample_indices: list[int]
    channel_group_counts: dict[str, int]
    output_html: str
    output_json: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a visual HTML report for the Phase127 3D telemetry tensor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument(
        "--sample-indices",
        default="first,middle,last",
        help="Comma list of sample indices or aliases: first,middle,last.",
    )
    parser.add_argument("--time-buckets", type=int, default=50)
    parser.add_argument("--max-samples", type=int, default=6)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_tensor_latest.npz"


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def load_tensor(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Tensor file not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def channel_names(data: Mapping[str, Any]) -> list[str]:
    raw = data.get("channel_names")
    if raw is None:
        x_values = np.asarray(data["X"])
        return [f"channel_{index}" for index in range(int(x_values.shape[2]))]
    return [str(value) for value in list(raw)]


def target_array(data: Mapping[str, Any], name: str, default: float = 0.0) -> np.ndarray:
    x_values = np.asarray(data["X"])
    raw = data.get(name)
    if raw is None:
        return np.full(int(x_values.shape[0]), default, dtype=np.float64)
    return np.asarray(raw)


def parse_sample_indices(text: str, samples: int, max_samples: int) -> list[int]:
    aliases = {
        "first": 0,
        "start": 0,
        "middle": max(samples // 2, 0),
        "mid": max(samples // 2, 0),
        "last": max(samples - 1, 0),
        "end": max(samples - 1, 0),
    }
    selected: list[int] = []
    for token in (part.strip().lower() for part in text.split(",")):
        if not token:
            continue
        if token in aliases:
            index = aliases[token]
        else:
            try:
                index = int(token)
            except ValueError:
                continue
        if 0 <= index < samples and index not in selected:
            selected.append(index)
    if not selected and samples > 0:
        selected = [0]
    limit = max(int(max_samples), 1)
    return selected[:limit]


def group_for_channel(name: str) -> str:
    if name.startswith("5m_"):
        return "5M candle"
    if name.startswith("session_"):
        return "Session/time"
    if name.startswith("4h_"):
        return "Closed 4H context"
    if name.startswith("1d_"):
        return "Closed 1D context"
    if name.startswith("buy_specialist") or name.startswith("sell_specialist"):
        return "Specialist model probabilities"
    if name.startswith("specialist_"):
        return "Specialist derived features"
    if name.startswith("booster_"):
        return "Trend booster probabilities"
    if name.startswith("wavenet_"):
        return "WaveNet channels"
    if name.startswith("range_1d_"):
        return "1D range model"
    if name.startswith("range_4h_"):
        return "4H range model"
    if name.startswith("candidate_"):
        return "Hybrid candidate / bracket"
    if name.startswith("rolling_") or name.startswith("recent_") or name.startswith("lagged_"):
        return "Lagged trade telemetry"
    if name.startswith("last_closed_") or name.startswith("bars_since_"):
        return "Lagged trade telemetry"
    return "Other"


def grouped_channels(names: Sequence[str]) -> dict[str, list[tuple[int, str]]]:
    groups: dict[str, list[tuple[int, str]]] = {}
    for index, name in enumerate(names):
        groups.setdefault(group_for_channel(name), []).append((index, name))
    return groups


def bucket_series(values: np.ndarray, buckets: int) -> np.ndarray:
    bucket_count = max(int(buckets), 1)
    if len(values) <= bucket_count:
        return values.astype(float, copy=False)
    return np.asarray([float(np.mean(chunk)) for chunk in np.array_split(values, bucket_count)])


def heat_color(value: float, center: float, scale: float) -> str:
    if not np.isfinite(value):
        value = 0.0
    safe_scale = max(float(scale), 1e-9)
    ratio = float(np.clip((value - center) / (safe_scale * 2.5), -1.0, 1.0))
    if ratio >= 0:
        intensity = int(34 + ratio * 160)
        return f"rgb({intensity}, {92 + int(ratio * 120)}, 90)"
    ratio = abs(ratio)
    intensity = int(38 + ratio * 145)
    return f"rgb(50, {82 + int(ratio * 110)}, {intensity + 70})"


def heatmap_html(
    sample: np.ndarray,
    names: Sequence[str],
    time_buckets: int,
) -> str:
    groups = grouped_channels(names)
    parts: list[str] = []
    for group, items in groups.items():
        rows: list[str] = []
        for channel_index, channel_name in items:
            series = bucket_series(np.asarray(sample[:, channel_index], dtype=float), time_buckets)
            center = float(np.nanmedian(series)) if len(series) else 0.0
            spread = float(np.nanstd(series)) if len(series) else 1.0
            cells = "".join(
                f'<td style="background:{heat_color(float(value), center, spread)}" '
                f'title="{html.escape(channel_name)} bucket={bucket} value={float(value):.6g}"></td>'
                for bucket, value in enumerate(series)
            )
            rows.append(
                "<tr>"
                f'<th title="{html.escape(channel_name)}">{html.escape(channel_name)}</th>'
                f"{cells}</tr>"
            )
        parts.append(
            f"<details open><summary>{html.escape(group)} — {len(items)} channels</summary>"
            '<table class="heatmap"><tbody>' + "".join(rows) + "</tbody></table></details>"
        )
    return "".join(parts)


def sample_meta(data: Mapping[str, Any], sample_index: int) -> dict[str, Any]:
    def value(name: str, default: Any = "") -> Any:
        raw = data.get(name)
        if raw is None:
            return default
        array = np.asarray(raw)
        if sample_index >= len(array):
            return default
        item = array[sample_index]
        if hasattr(item, "item"):
            try:
                return item.item()
            except ValueError:
                return item
        return item

    return {
        "sample_index": sample_index,
        "source_index": value("source_index", -1),
        "timestamp": str(value("timestamp", "")),
        "candidate_mask": float(value("candidate_mask", 0.0)),
        "target_trade_win": float(value("target_trade_win", 0.0)),
        "target_trade_score_r": float(value("target_trade_score_r", 0.0)),
        "target_trade_pnl": float(value("target_trade_pnl", 0.0)),
        "target_side": float(value("target_side", 0.0)),
        "target_exit_index": int(value("target_exit_index", -1)),
        "target_outcome_code": float(value("target_outcome_code", 0.0)),
    }


def html_page(
    report: TensorInspectionReport,
    data: Mapping[str, Any],
    names: Sequence[str],
    time_buckets: int,
) -> str:
    x_values = np.asarray(data["X"])
    groups = grouped_channels(names)
    sample_sections: list[str] = []
    for sample_index in report.selected_sample_indices:
        meta = sample_meta(data, sample_index)
        sample = np.asarray(x_values[sample_index], dtype=np.float32)
        sample_sections.append(
            '<section class="card">'
            f"<h2>Sample {sample_index:,}</h2>"
            f"<pre>{html.escape(json.dumps(meta, indent=2, ensure_ascii=False))}</pre>"
            '<div class="hint">Each row is one feature channel. Columns move from older candles to newer candles inside the 150-candle window. Color is normalized per channel for visual reading, not for trading decisions.</div>'
            + heatmap_html(sample, names, time_buckets)
            + "</section>"
        )
    group_rows = "".join(
        f"<tr><td>{html.escape(group)}</td><td>{len(items)}</td><td>"
        + ", ".join(html.escape(name) for _, name in items[:8])
        + (" ..." if len(items) > 8 else "")
        + "</td></tr>"
        for group, items in groups.items()
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hybrid Telemetry Tensor Inspector</title>
  <style>
    body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma, Segoe UI, Arial, sans-serif; line-height:1.7; }}
    main {{ max-width:1500px; margin:0 auto; padding:24px; }}
    .hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:20px; padding:18px; margin:16px 0; box-shadow:0 18px 40px rgba(0,0,0,.25); }}
    h1,h2,h3 {{ margin:0 0 10px; }}
    code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; color:#dbeafe; }}
    code {{ padding:2px 6px; }} pre {{ padding:12px; overflow:auto; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
    .metric span {{ display:block; color:#94a3b8; font-size:13px; }}
    .metric strong {{ direction:ltr; text-align:left; display:block; font-size:22px; color:#7dd3fc; }}
    table {{ border-collapse:collapse; width:100%; direction:ltr; text-align:left; font-size:12px; }}
    th,td {{ border-bottom:1px solid #1e293b; padding:6px; vertical-align:middle; }}
    th {{ color:#bae6fd; }}
    .heatmap th {{ width:260px; max-width:260px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; position:sticky; left:0; background:#020617; z-index:1; }}
    .heatmap td {{ width:12px; min-width:12px; height:13px; padding:0; border:1px solid rgba(15,23,42,.55); }}
    details {{ margin:10px 0; border:1px solid #1e293b; border-radius:14px; padding:10px; background:#02061766; }}
    summary {{ cursor:pointer; color:#fcd34d; font-weight:700; }}
    .hint {{ border-right:4px solid #38bdf8; background:#0ea5e91a; border-radius:10px; padding:10px; margin:10px 0; color:#dbeafe; }}
    .warn {{ border-right:4px solid #f59e0b; background:#f59e0b1a; border-radius:10px; padding:10px; margin:10px 0; color:#fef3c7; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:12px; }} }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <h1>Hybrid Telemetry 3D Tensor Inspector</h1>
    <p>این گزارش یک برش ملموس از tensor سه‌بعدی Phase127A نشان می‌دهد. محور اول sample، محور دوم زمان 150 کندلی، و محور سوم کانال‌های فیچر است.</p>
    <div class="grid">
      <div class="metric"><span>Shape</span><strong>{report.shape}</strong></div>
      <div class="metric"><span>DType</span><strong>{html.escape(report.dtype)}</strong></div>
      <div class="metric"><span>Channels</span><strong>{report.channels}</strong></div>
      <div class="metric"><span>Uncompressed estimate</span><strong>{report.estimated_uncompressed_mb:.1f} MB</strong></div>
    </div>
    <div class="warn">این heatmap برای فهم بصری است. رنگ هر کانال جداگانه normalize می‌شود، پس رنگ‌ها بین دو feature مختلف معنای عددی مستقیم ندارند.</div>
  </section>

  <section class="card">
    <h2>Axis meaning</h2>
    <table><tbody>
      <tr><th>Axis 0</th><td>samples = rolling windows selected from the 5M stream</td><td>{report.samples:,}</td></tr>
      <tr><th>Axis 1</th><td>time = candles inside each sample window</td><td>{report.tensor_window:,} bars</td></tr>
      <tr><th>Axis 2</th><td>channels = online-safe features per candle</td><td>{report.channels:,}</td></tr>
    </tbody></table>
  </section>

  <section class="card">
    <h2>Channel groups</h2>
    <table><thead><tr><th>Group</th><th>Count</th><th>Examples</th></tr></thead><tbody>{group_rows}</tbody></table>
  </section>

  {''.join(sample_sections)}
</main>
</body>
</html>"""


def write_outputs(args: argparse.Namespace, report: TensorInspectionReport, page: str) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(report.output_html).write_text(page, encoding="utf-8")
    Path(report.output_json).write_text(
        json.dumps({"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def inspect_tensor(args: argparse.Namespace, data: Mapping[str, Any]) -> TensorInspectionReport:
    storage_root = Path(args.storage_root)
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(storage_root, args.symbol, args.timeframe)
    )
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    if "X" not in data:
        raise RuntimeError("Tensor archive does not contain X")
    x_values = np.asarray(data["X"])
    if x_values.ndim != 3:
        raise RuntimeError(f"Expected X to be 3D [samples, window, channels], got {x_values.shape}")
    names = channel_names(data)
    if len(names) != int(x_values.shape[2]):
        raise RuntimeError(
            f"channel_names length {len(names)} does not match X channels {x_values.shape[2]}"
        )
    selected = parse_sample_indices(args.sample_indices, int(x_values.shape[0]), args.max_samples)
    groups = grouped_channels(names)
    out_dir = Path(args.output_dir)
    html_path = out_dir / "latest.html"
    json_path = out_dir / "latest.json"
    return TensorInspectionReport(
        tensor_path=str(tensor_path),
        flat_path=str(flat_path),
        shape=[int(value) for value in x_values.shape],
        dtype=str(x_values.dtype),
        samples=int(x_values.shape[0]),
        tensor_window=int(x_values.shape[1]),
        channels=int(x_values.shape[2]),
        estimated_uncompressed_mb=float(x_values.nbytes / (1024 * 1024)),
        selected_sample_indices=selected,
        channel_group_counts={group: len(items) for group, items in groups.items()},
        output_html=str(html_path),
        output_json=str(json_path),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        data = load_tensor(
            Path(args.tensor_path)
            if args.tensor_path
            else default_tensor_path(Path(args.storage_root), args.symbol, args.timeframe)
        )
        report = inspect_tensor(args, data)
        names = channel_names(data)
        page = html_page(report, data, names, args.time_buckets)
        write_outputs(args, report, page)
        print("\n" + "=" * 74)
        print("  HYBRID TELEMETRY TENSOR INSPECTOR")
        print("=" * 74)
        print(f"  tensor      : {report.tensor_path}")
        print(f"  shape       : {report.shape}")
        print(f"  dtype       : {report.dtype}")
        print(f"  selected    : {report.selected_sample_indices}")
        print(f"  html        : {report.output_html}")
        print(f"  json        : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
