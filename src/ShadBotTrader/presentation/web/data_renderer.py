"""Candlestick chart and dataset inspection page (Phase 34).

Answers three questions on one page, for each of the three data steps:

    Fetch market data      -> the candles that arrived
    Update features        -> which features were computed
    Build training dataset -> the 123 columns the models will read

Everything is inlined — canvas drawing, styles, data as embedded JSON —
so the page renders in a sandboxed preview, from a saved file, or with no
network at all. A View renders; it computes nothing (Phase 19 §8).
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict, Optional, Sequence

_STYLES = """
:root {
  --bg:#0e1117; --panel:#161b22; --border:#262d38; --text:#e6edf3; --muted:#8b949e;
  --up:#3fb950; --down:#f85149; --warning:#d29922; --accent:#58a6ff;
}
* { box-sizing:border-box; }
body { margin:0; padding:18px; background:var(--bg); color:var(--text);
  font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace; font-size:13px; }
header { border-bottom:1px solid var(--border); padding-bottom:12px; margin-bottom:16px; }
h1 { margin:0 0 4px; font-size:17px; letter-spacing:.5px; }
h2 { margin:0 0 12px; font-size:12px; text-transform:uppercase; letter-spacing:1px;
  color:var(--muted); font-weight:600; }
a { color:var(--accent); }
.sub { color:var(--muted); font-size:12px; }
.panel { background:var(--panel); border:1px solid var(--border); border-radius:8px;
  padding:16px; margin-bottom:16px; }
canvas { width:100%; display:block; border-radius:6px; background:var(--bg); }
.controls { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:12px; }
button, select { background:var(--panel); color:var(--text); border:1px solid var(--border);
  border-radius:5px; padding:6px 12px; font-family:inherit; font-size:12px; cursor:pointer; }
button:hover { border-color:var(--accent); }
button.on { background:var(--accent); color:#04101f; border-color:var(--accent); }
.stats { display:grid; gap:10px; grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  margin-top:12px; }
.stat { background:var(--bg); border:1px solid var(--border);
  border-radius:6px; padding:10px 12px; }
.stat .k { color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.5px; }
.stat .v { font-size:17px; font-weight:600; margin-top:4px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { text-align:left; color:var(--muted); font-size:10px; text-transform:uppercase;
  letter-spacing:.5px; padding:6px 10px 6px 0; border-bottom:1px solid var(--border);
  position:sticky; top:0; background:var(--panel); }
td { padding:5px 10px 5px 0; border-bottom:1px solid rgba(38,45,56,.5); white-space:nowrap; }
.scroll { max-height:460px; overflow:auto; }
.up{color:var(--up);} .down{color:var(--down);} .muted{color:var(--muted);}
.warn{color:var(--warning);} .accent{color:var(--accent);}
.badge { display:inline-block; padding:1px 7px; border-radius:9px; font-size:10px;
  border:1px solid currentColor; }
.empty { color:var(--muted); font-style:italic; padding:10px 0; }
.bar { height:6px; background:var(--bg); border-radius:3px; overflow:hidden; width:80px;
  display:inline-block; vertical-align:middle; }
.bar span { display:block; height:100%; background:var(--up); }
.grid2 { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }
footer { color:var(--muted); font-size:11px; border-top:1px solid var(--border);
  padding-top:10px; margin-top:8px; }
"""

_CHART_SCRIPT = r"""
const CANDLES = __CANDLES__;

const canvas = document.getElementById('chart');
const ctx = canvas && canvas.getContext('2d');
let showVolume = true;
let visible = 120;

// فاز ۸۲ — زوم قیمت و پن زمان (مثل ریپلی/متاتریدر)
let priceZoom = 1.0;
let priceAnchor = null;
let viewStart = null;   // null = آخرین N کندل؛ عدد = شروعِ دستی
let dragX = null;

function resize() {
  if (!canvas) return;
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = 460;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.height = height + 'px';
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

function draw() {
  if (!canvas || !CANDLES.length) return;
  const width = canvas.clientWidth;
  const height = 460;
  const volumeH = showVolume ? 70 : 0;
  const priceH = height - volumeH - 26;
  const padL = 8, padR = 66;

  ctx.clearRect(0, 0, width, height);

  const slice = (viewStart !== null)
    ? CANDLES.slice(
        Math.max(0, Math.min(viewStart, Math.max(0, CANDLES.length - visible))),
        Math.max(0, Math.min(viewStart, Math.max(0, CANDLES.length - visible))) + visible
      )
    : CANDLES.slice(-visible);
  let hi = -Infinity, lo = Infinity, maxVol = 0;
  slice.forEach(c => {
    if (c.h > hi) hi = c.h;
    if (c.l < lo) lo = c.l;
    if (c.v > maxVol) maxVol = c.v;
  });
  if (hi === lo) { hi += 1; lo -= 1; }

  // فاز ۸۲: زوم قیمت حول anchor
  if (priceZoom > 1.0) {
    const anchor = priceAnchor !== null ? priceAnchor : (hi + lo) / 2;
    const span = (hi - lo) / priceZoom;
    hi = anchor + span / 2;
    lo = anchor - span / 2;
  }

  const plotW = width - padL - padR;
  const step = plotW / slice.length;
  const bodyW = Math.max(1.5, Math.min(12, step * 0.66));
  const yP = p => 8 + (hi - p) / (hi - lo) * (priceH - 16);
  const xOf = i => padL + i * step + step / 2;

  ctx.strokeStyle = 'rgba(38,45,56,.75)';
  ctx.fillStyle = '#8b949e';
  ctx.font = '10px ui-monospace, monospace';
  for (let k = 0; k <= 4; k++) {
    const price = lo + (hi - lo) * k / 4;
    const y = Math.round(yP(price)) + 0.5;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke();
    ctx.fillText(price.toFixed(2), width - padR + 6, y + 3);
  }

  slice.forEach((c, i) => {
    const x = xOf(i);
    const colour = c.c >= c.o ? '#3fb950' : '#f85149';
    ctx.strokeStyle = colour; ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.moveTo(Math.round(x) + 0.5, yP(c.h));
    ctx.lineTo(Math.round(x) + 0.5, yP(c.l));
    ctx.stroke();
    const top = yP(Math.max(c.o, c.c));
    const bot = yP(Math.min(c.o, c.c));
    ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(1, bot - top));
  });

  if (showVolume && maxVol > 0) {
    const base = height - 20;
    slice.forEach((c, i) => {
      const x = xOf(i);
      const h = (c.v / maxVol) * (volumeH - 10);
      ctx.fillStyle = c.c >= c.o ? 'rgba(63,185,80,.45)' : 'rgba(248,81,73,.45)';
      ctx.fillRect(x - bodyW / 2, base - h, bodyW, h);
    });
    ctx.fillStyle = '#8b949e';
    ctx.fillText('volume', padL, height - 22 - volumeH + 10);
  }

  ctx.fillStyle = '#8b949e';
  if (slice.length) {
    ctx.fillText(slice[0].t.replace('T', ' ').slice(0, 16), padL, height - 6);
    const lastLabel = slice[slice.length - 1].t.replace('T', ' ').slice(0, 16);
    ctx.fillText(lastLabel, width - padR - 100, height - 6);
  }

  const last = slice[slice.length - 1];
  const first = slice[0];
  const change = last.c - first.o;
  const pct = first.o ? (change / first.o) * 100 : 0;
  const box = document.getElementById('chart-stats');
  if (box) {
    box.innerHTML =
      `<div class="stat"><div class="k">Showing</div><div class="v">${slice.length}</div></div>` +
      `<div class="stat"><div class="k">Last close</div>` +
      `<div class="v">${last.c.toFixed(2)}</div></div>` +
      `<div class="stat"><div class="k">High</div><div class="v">${hi.toFixed(2)}</div></div>` +
      `<div class="stat"><div class="k">Low</div><div class="v">${lo.toFixed(2)}</div></div>` +
      `<div class="stat"><div class="k">Change</div>` +
      `<div class="v ${change >= 0 ? 'up' : 'down'}">` +
      `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${pct.toFixed(2)}%)</div></div>`;
  }
}

const windowSelect = document.getElementById('window');
if (windowSelect) {
  windowSelect.addEventListener('change', () => {
    visible = parseInt(windowSelect.value, 10);
    viewStart = null;   // انتخاب تعداد کندل → زوم زمانی ریست
    draw();
  });
}
const volumeButton = document.getElementById('toggle-volume');
if (volumeButton) {
  volumeButton.addEventListener('click', () => {
    showVolume = !showVolume;
    volumeButton.classList.toggle('on', showVolume);
    draw();
  });
}

// ── فاز ۸۲: wheel = زوم قیمت · درگ = پن زمان · دکمهٔ ریست ──
if (canvas) {
  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = 460;
    const volumeH = showVolume ? 70 : 0;
    const priceH = height - volumeH - 26;
    const padL = 8, padR = 66;

    const slice = (viewStart !== null)
      ? CANDLES.slice(Math.max(0, Math.min(viewStart, CANDLES.length - visible)))
      : CANDLES.slice(-visible);
    if (!slice.length) return;
    let hi = -Infinity, lo = Infinity;
    slice.forEach(c => { if (c.h > hi) hi = c.h; if (c.l < lo) lo = c.l; });
    if (priceZoom > 1.0 && priceAnchor !== null) {
      const span = (hi - lo) / priceZoom;
      hi = priceAnchor + span / 2;
      lo = priceAnchor - span / 2;
    }

    const plotW = width - padL - padR;
    const rel = Math.min(1, Math.max(0, (e.clientX - rect.left - padL) / plotW));
    const mousePrice = hi - rel * (hi - lo);

    const factor = e.deltaY < 0 ? 1.25 : 1 / 1.25;
    priceZoom = Math.min(30, Math.max(1.0, priceZoom * factor));
    priceAnchor = mousePrice;
    if (priceZoom === 1.0) priceAnchor = null;
    draw();
  }, { passive: false });

  canvas.addEventListener('mousedown', e => { dragX = e.clientX; });
  canvas.addEventListener('mousemove', e => {
    if (dragX === null) return;
    const dx = e.clientX - dragX;
    if (Math.abs(dx) < 6) return;
    dragX = e.clientX;
    const plotW = canvas.clientWidth - 8 - 66;
    const stepPx = plotW / visible;
    const shift = Math.round(dx / stepPx);
    if (shift === 0) return;
    viewStart = Math.max(
      0,
      Math.min(
        CANDLES.length - visible,
        (viewStart !== null ? viewStart : CANDLES.length - visible) + shift
      )
    );
    draw();
  });
  canvas.addEventListener('mouseup', () => { dragX = null; });
  canvas.addEventListener('mouseleave', () => { dragX = null; });
}

const zoomResetBtn = document.getElementById('zoom-reset');
if (zoomResetBtn) {
  zoomResetBtn.addEventListener('click', () => {
    priceZoom = 1.0; priceAnchor = null; viewStart = null; draw();
  });
}
window.addEventListener('resize', resize);
resize();
"""


def _e(value: object) -> str:
    return html.escape(str(value))


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{_e(empty)}</p>'
    head = "".join(f"<th>{_e(name)}</th>" for name in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def render_candle_section(info: Dict[str, Any]) -> str:
    """The chart plus the facts about the stored candle series."""
    if not info.get("exists"):
        return """<section class="panel">
  <h2>Candles</h2>
  <p class="empty">No candles stored for this symbol and timeframe yet.</p>
  <p>Use <b>Data &rarr; Fetch market data</b> on the dashboard.</p>
</section>"""

    continuity = info.get("continuity") or {}
    gap_count = continuity.get("gap_count", 0)
    continuity_badge = (
        '<span class="up">continuous</span>'
        if continuity.get("continuous")
        else f'<span class="warn">{gap_count} gap(s), '
        f'{continuity.get("missing_candles", 0):,} candles missing</span>'
    )
    calendar = (continuity.get("calendar") or {}).get("description", "unknown")

    return f"""<section class="panel">
  <h2>Candles — {_e(info["symbol"])} {_e(info["timeframe"])}</h2>
  <canvas id="chart" height="460"></canvas>
  <div class="controls">
    <select id="window">
      <option value="60">60 candles</option>
      <option value="120" selected>120 candles</option>
      <option value="200">200 candles</option>
      <option value="300">300 candles</option>
    </select>
    <button id="toggle-volume" class="on" type="button">Volume</button>
    <button id="zoom-reset" class="ghost" type="button">&#8634; Reset zoom</button>
    <span style="color:#8b949e;align-self:center;font-size:12px">
      wheel = زوم قیمت · درگ = جابجایی زمان
    </span>
    <span class="sub">green = close above open</span>
  </div>
  <div class="stats" id="chart-stats"></div>
  <div class="stats">
    <div class="stat"><div class="k">Stored candles</div>
      <div class="v">{info["count"]:,}</div></div>
    <div class="stat"><div class="k">First</div>
      <div class="v" style="font-size:12px">{_e((info.get("first_time") or "")[:16])}</div></div>
    <div class="stat"><div class="k">Last</div>
      <div class="v" style="font-size:12px">{_e((info.get("last_time") or "")[:16])}</div></div>
    <div class="stat"><div class="k">Span</div>
      <div class="v">{info.get("span_days") or "?"} d</div></div>
  </div>
  <p class="sub" style="margin-top:12px">
    continuity: {continuity_badge} &nbsp;·&nbsp; market {_e(calendar)}
  </p>
</section>"""


def render_matrix_section(matrix: Dict[str, Any]) -> str:
    """The training matrix: how many rows, and every column described."""
    if not matrix.get("exists"):
        return """<section class="panel">
  <h2>Training matrix</h2>
  <p class="empty">No training matrix built yet.</p>
  <p>Use <b>Data &rarr; Build training dataset</b> on the dashboard.</p>
</section>"""

    groups: Dict[str, int] = {}
    for column in matrix["columns"]:
        groups[column["kind"]] = groups.get(column["kind"], 0) + 1
    group_text = " · ".join(f"{count} {kind}" for kind, count in groups.items())

    rows = []
    for column in matrix["columns"]:
        coverage = column["coverage"]
        flags = []
        if not column["complete"]:
            flags.append('<span class="warn">gaps</span>')
        if column["constant"]:
            flags.append('<span class="warn">constant</span>')
        rows.append(
            [
                _e(column["name"]),
                f'<span class="muted">{_e(column["kind"])}</span>',
                f'<span class="bar"><span style="width:{coverage:.0f}%"></span></span> '
                f"{coverage:.0f}%",
                "—" if column["min"] is None else f'{column["min"]:.4g}',
                "—" if column["max"] is None else f'{column["max"]:.4g}',
                "—" if column["sample"] is None else f'{column["sample"]:.4g}',
                " ".join(flags),
            ]
        )

    warnings = "".join(f'<p class="warn">[!] {_e(item)}</p>' for item in matrix.get("warnings", []))

    return f"""<section class="panel">
  <h2>Training matrix — {_e(matrix["symbol"])} {_e(matrix["timeframe"])}</h2>
  <div class="stats">
    <div class="stat"><div class="k">Rows</div><div class="v">{matrix["rows"]:,}</div></div>
    <div class="stat"><div class="k">Columns</div>
      <div class="v">{matrix["column_count"]}</div></div>
    <div class="stat"><div class="k">Revision</div>
      <div class="v">{_e(matrix.get("revision") or "—")}</div></div>
    <div class="stat"><div class="k">Digest</div>
      <div class="v" style="font-size:12px">{_e(matrix.get("digest") or "—")}</div></div>
  </div>
  <p class="sub" style="margin:10px 0">{_e(group_text)}
     &nbsp;·&nbsp; built {_e((matrix.get("built_at") or "—")[:19])}</p>
  {warnings}
  {_table(
      ["Column", "Kind", "Coverage", "Min", "Max", "Latest", ""],
      rows,
      "No columns.",
  )}
</section>"""


def render_features_section(features: Dict[str, Any]) -> str:
    """Which catalogue features have been computed and stored."""
    if not features.get("exists"):
        return """<section class="panel">
  <h2>Computed features</h2>
  <p class="empty">No features computed yet.</p>
  <p>Use <b>Data &rarr; Update features</b> on the dashboard.</p>
</section>"""

    rows = [
        [
            _e(item["feature_id"]),
            _e(item.get("series", "?")),
            f'v{item["latest_version"]}',
            str(item["versions"]),
            f'{item["size_kb"]:.1f} KB',
        ]
        for item in features["features"]
    ]
    note = '<p class="sub">Showing the first 200.</p>' if features.get("truncated") else ""

    return f"""<section class="panel">
  <h2>Computed features</h2>
  <div class="stats">
    <div class="stat"><div class="k">Stored features</div>
      <div class="v">{features["count"]}</div></div>
  </div>
  {note}
  {_table(["Feature", "Series", "Latest", "Versions", "Size"], rows, "None stored.")}
</section>"""


def render_data_page(
    candles: Dict[str, Any],
    matrix: Dict[str, Any],
    features: Dict[str, Any],
    series: Sequence[Dict[str, str]] = (),
    selected: Optional[Dict[str, str]] = None,
) -> str:
    """The complete data-inspection page."""
    chart_data = json.dumps(candles.get("chart", []), separators=(",", ":"))
    script = _CHART_SCRIPT.replace("__CANDLES__", chart_data)

    options = []
    current = selected or {}
    for item in series:
        label = f'{item["symbol"]} {item["timeframe"]}'
        active = item["symbol"] == current.get("symbol") and item["timeframe"] == current.get(
            "timeframe"
        )
        options.append(
            f'<option value="{_e(item["symbol"])}|{_e(item["timeframe"])}"'
            f'{" selected" if active else ""}>{_e(label)}</option>'
        )

    picker = ""
    if options:
        picker = f"""<form method="get" action="/data" class="controls">
  <select name="series" onchange="this.form.submit()">{"".join(options)}</select>
  <noscript><button type="submit">Show</button></noscript>
</form>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShadBotTrader — Data</title>
<style>{_STYLES}</style>
</head>
<body>
<header>
  <h1>Data inspector</h1>
  <div class="sub">
    what is stored, what it looks like, and which columns exist
    &nbsp;·&nbsp; <a href="/">&#8592; dashboard</a>
    &nbsp;·&nbsp; <a href="/replay">replay</a>
  </div>
</header>
{picker}
{render_candle_section(candles)}
<div class="grid2">
  {render_matrix_section(matrix)}
  {render_features_section(features)}
</div>
<footer>
  Read-only. Every number here was read from storage, not recalculated.
</footer>
<script>{script}</script>
</body>
</html>"""
