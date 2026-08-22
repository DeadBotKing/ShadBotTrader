"""Replay player: watch a backtest bar by bar (Phase 19, section 8).

The View renders; it does not compute. Everything on the page comes from
a finished ``ReplayTape`` — the candles the engine processed, the fills it
produced and the equity it left behind. The player only *animates* that
recording; it never re-runs a strategy in the browser.

The page is self-contained on purpose: the chart is drawn on a canvas by
a small inline script, the data is embedded as JSON, and no font, style
or library is fetched. It therefore renders identically in a sandboxed
preview iframe, in a saved file opened offline, and behind a firewall.
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict, Optional

from ShadBotTrader.domain.simulation.performance import PerformanceMetrics
from ShadBotTrader.domain.simulation.replay import ReplayTape


def _e(value: object) -> str:
    return html.escape(str(value))


def _metric_payload(metrics: Optional[PerformanceMetrics]) -> Dict[str, Any]:
    """Flatten the metrics for the summary bar, keeping ``None`` as null.

    Undefined metrics stay undefined: the player prints ``n/a`` rather
    than a zero that would read like a real measurement.
    """
    if metrics is None:
        return {}
    hit = metrics.hit_rate
    profit_factor = metrics.profit_factor
    return {
        "trades": metrics.trade_count,
        "wins": metrics.win_count,
        "losses": metrics.loss_count,
        "hit_rate": None if hit is None else float(hit),
        "profit_factor": None if profit_factor is None else float(profit_factor),
        "total_return": float(metrics.total_return),
        "total_return_percent": float(metrics.total_return_percent),
        "max_drawdown_percent": float(metrics.max_drawdown_percent),
        "fees": float(metrics.total_fees),
        "spread_cost": float(metrics.spread_cost),
        "slippage_cost": float(metrics.slippage_cost),
    }


_STYLES = """
:root {
  --bg:#0e1117; --panel:#161b22; --border:#262d38; --text:#e6edf3; --muted:#8b949e;
  --up:#3fb950; --down:#f85149; --warning:#d29922; --accent:#58a6ff;
}
* { box-sizing:border-box; }
body { margin:0; padding:18px; background:var(--bg); color:var(--text);
  font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace; font-size:13px; }
header { border-bottom:1px solid var(--border); padding-bottom:12px; margin-bottom:14px; }
h1 { margin:0 0 4px; font-size:17px; letter-spacing:.5px; }
h2 { margin:0 0 10px; font-size:11px; text-transform:uppercase; letter-spacing:1px;
  color:var(--muted); font-weight:600; }
.sub { color:var(--muted); font-size:12px; }
.panel { background:var(--panel); border:1px solid var(--border); border-radius:8px;
  padding:14px; margin-bottom:14px; }
.chart-wrap { position:relative; }
canvas { width:100%; display:block; border-radius:6px; background:var(--bg); }
.controls { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:12px; }
button { background:var(--accent); color:#04101f; border:0; border-radius:5px;
  padding:7px 14px; font-family:inherit; font-size:12px; font-weight:600; cursor:pointer; }
button.ghost { background:transparent; color:var(--text); border:1px solid var(--border); }
button:hover { filter:brightness(1.15); }
input[type=range] { flex:1; min-width:180px; accent-color:var(--accent); }
select { background:var(--bg); color:var(--text); border:1px solid var(--border);
  border-radius:5px; padding:6px; font-family:inherit; font-size:12px; }
.stats { display:grid; gap:10px; grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
  margin-top:12px; }
.stat { background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:9px 11px; }
.stat .k { color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.5px; }
.stat .v { font-size:16px; font-weight:600; margin-top:3px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { text-align:left; color:var(--muted); font-size:10px; text-transform:uppercase;
  letter-spacing:.5px; padding:5px 8px 5px 0; border-bottom:1px solid var(--border); }
td { padding:5px 8px 5px 0; border-bottom:1px solid rgba(38,45,56,.5); white-space:nowrap; }
.up { color:var(--up); } .down { color:var(--down); }
.muted { color:var(--muted); } .warn { color:var(--warning); }
.log { max-height:260px; overflow-y:auto; }
.empty { color:var(--muted); font-style:italic; }
.legend { display:flex; gap:16px; flex-wrap:wrap; color:var(--muted);
  font-size:11px; margin-top:8px; }
.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px; }
footer { color:var(--muted); font-size:11px; border-top:1px solid var(--border);
  padding-top:10px; margin-top:6px; }
"""

# The player: pure presentation. It walks the recorded tape forward and
# repaints; it never decides anything.
_SCRIPT = r"""
const TAPE = __TAPE__;
const METRICS = __METRICS__;

const bars = TAPE.bars || [];
const markersByBar = {};
(TAPE.markers || []).forEach(m => {
  (markersByBar[m.bar] = markersByBar[m.bar] || []).push(m);
});

const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');
const scrub = document.getElementById('scrub');
const playBtn = document.getElementById('play');
const speedSel = document.getElementById('speed');
const windowSel = document.getElementById('window');
const logBody = document.getElementById('log-body');

let cursor = 0;         // index of the last painted bar
let playing = false;
let timer = null;
let loggedTrips = 0;

scrub.max = Math.max(bars.length - 1, 0);

function fmt(value, digits) {
  if (value === null || value === undefined) return 'n/a';
  return Number(value).toFixed(digits === undefined ? 2 : digits);
}

function resize() {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = 420;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.height = height + 'px';
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

function visibleRange() {
  const size = parseInt(windowSel.value, 10);
  const end = cursor + 1;
  const start = Math.max(0, end - size);
  return [start, end];
}

function draw() {
  const width = canvas.clientWidth;
  const height = 420;
  const priceH = height * 0.72;
  const eqTop = priceH + 18;
  const eqH = height - eqTop - 6;
  const padL = 8, padR = 62;

  ctx.clearRect(0, 0, width, height);
  if (!bars.length) return;

  const [start, end] = visibleRange();
  const slice = bars.slice(start, end);
  if (!slice.length) return;

  let hi = -Infinity, lo = Infinity, eqHi = -Infinity, eqLo = Infinity;
  slice.forEach(b => {
    if (b.h > hi) hi = b.h;
    if (b.l < lo) lo = b.l;
    if (b.eq > eqHi) eqHi = b.eq;
    if (b.eq < eqLo) eqLo = b.eq;
  });
  if (hi === lo) { hi += 1; lo -= 1; }
  if (eqHi === eqLo) { eqHi += 1; eqLo -= 1; }

  const plotW = width - padL - padR;
  const step = plotW / slice.length;
  const bodyW = Math.max(1.5, Math.min(11, step * 0.62));
  const yPrice = p => 6 + (hi - p) / (hi - lo) * (priceH - 12);
  const yEquity = v => eqTop + (eqHi - v) / (eqHi - eqLo) * eqH;
  const xOf = i => padL + i * step + step / 2;

  // horizontal guides + price scale
  ctx.strokeStyle = 'rgba(38,45,56,.7)';
  ctx.fillStyle = '#8b949e';
  ctx.font = '10px ui-monospace, monospace';
  ctx.lineWidth = 1;
  for (let k = 0; k <= 4; k++) {
    const price = lo + (hi - lo) * k / 4;
    const y = Math.round(yPrice(price)) + 0.5;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke();
    ctx.fillText(price.toFixed(2), width - padR + 6, y + 3);
  }

  // candles
  slice.forEach((b, i) => {
    const x = xOf(i);
    const up = b.c >= b.o;
    const colour = up ? '#3fb950' : '#f85149';
    ctx.strokeStyle = colour;
    ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.moveTo(Math.round(x) + 0.5, yPrice(b.h));
    ctx.lineTo(Math.round(x) + 0.5, yPrice(b.l));
    ctx.stroke();
    const top = yPrice(Math.max(b.o, b.c));
    const bot = yPrice(Math.min(b.o, b.c));
    ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(1, bot - top));
  });

  // trade markers on the visible bars
  slice.forEach((b, i) => {
    const marks = markersByBar[b.i] || [];
    marks.forEach(m => {
      const x = xOf(i);
      const y = yPrice(m.price);
      const buy = m.side === 'buy';
      const exit = m.kind === 'exit';
      const won = m.net_pnl !== null && m.net_pnl > 0;
      ctx.fillStyle = exit ? (won ? '#3fb950' : '#f85149') : '#58a6ff';
      ctx.beginPath();
      if (exit) {
        ctx.arc(x, y, 5, 0, Math.PI * 2);
      } else if (buy) {
        ctx.moveTo(x, y - 9); ctx.lineTo(x - 5, y + 1); ctx.lineTo(x + 5, y + 1);
      } else {
        ctx.moveTo(x, y + 9); ctx.lineTo(x - 5, y - 1); ctx.lineTo(x + 5, y - 1);
      }
      ctx.closePath();
      ctx.fill();
    });
  });

  // equity strip
  ctx.strokeStyle = '#262d38';
  ctx.beginPath();
  ctx.moveTo(padL, eqTop - 8); ctx.lineTo(width - padR, eqTop - 8); ctx.stroke();
  ctx.fillStyle = '#8b949e';
  ctx.fillText('equity', padL, eqTop - 12);

  const startEq = TAPE.starting_equity;
  if (startEq >= eqLo && startEq <= eqHi) {
    const y = Math.round(yEquity(startEq)) + 0.5;
    ctx.strokeStyle = 'rgba(139,148,158,.45)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke();
    ctx.setLineDash([]);
  }

  const last = slice[slice.length - 1];
  ctx.strokeStyle = last.eq >= startEq ? '#3fb950' : '#f85149';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  slice.forEach((b, i) => {
    const x = xOf(i), y = yEquity(b.eq);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = '#8b949e';
  ctx.fillText(last.eq.toFixed(2), width - padR + 6, yEquity(last.eq) + 3);
}

function paintStats() {
  const b = bars[cursor];
  if (!b) return;
  const pnl = b.eq - TAPE.starting_equity;
  const pct = TAPE.starting_equity ? (pnl / TAPE.starting_equity) * 100 : 0;
  const position = b.pos > 0 ? 'LONG ' + fmt(b.pos, 2)
                 : b.pos < 0 ? 'SHORT ' + fmt(Math.abs(b.pos), 2)
                 : 'flat';
  document.getElementById('s-bar').textContent = (cursor + 1) + ' / ' + bars.length;
  document.getElementById('s-time').textContent = b.t.replace('T', ' ').slice(0, 19);
  document.getElementById('s-close').textContent = fmt(b.c);
  document.getElementById('s-pred').textContent = b.p === null ? 'warmup' : fmt(b.p, 4);
  const posEl = document.getElementById('s-pos');
  posEl.textContent = position;
  posEl.className = 'v ' + (b.pos > 0 ? 'up' : b.pos < 0 ? 'down' : 'muted');
  document.getElementById('s-eq').textContent = fmt(b.eq);
  const pnlEl = document.getElementById('s-pnl');
  pnlEl.textContent = (pnl >= 0 ? '+' : '') + fmt(pnl) + ' (' + fmt(pct) + '%)';
  pnlEl.className = 'v ' + (pnl > 0 ? 'up' : pnl < 0 ? 'down' : 'muted');
  document.getElementById('s-trades').textContent = loggedTrips;
}

function rowFor(trip, n) {
  const tr = document.createElement('tr');
  const win = trip.net_pnl !== null && trip.net_pnl > 0;
  const cls = trip.net_pnl === null ? 'muted' : (win ? 'up' : 'down');
  const cells = [
    ['', String(n)],
    [trip.direction === 'long' ? 'up' : 'down', trip.direction],
    ['muted', '#' + trip.entry_bar + ' ' + trip.entry_time.replace('T', ' ').slice(5, 16)],
    ['', fmt(trip.entry_price)],
    ['muted', '#' + trip.exit_bar + ' ' + trip.exit_time.replace('T', ' ').slice(5, 16)],
    ['', fmt(trip.exit_price)],
    ['muted', String(trip.bars_held)],
    ['muted', fmt(trip.fees, 4)],
    [cls, (trip.net_pnl >= 0 ? '+' : '') + fmt(trip.net_pnl, 4)],
    [cls, win ? 'WIN' : 'LOSS'],
  ];
  cells.forEach(([klass, text]) => {
    const td = document.createElement('td');
    if (klass) td.className = klass;
    td.textContent = text;
    tr.appendChild(td);
  });
  return tr;
}

function syncLog() {
  const trips = TAPE.round_trips || [];
  const due = trips.filter(t => t.exit_bar <= bars[cursor].i).length;
  if (due === loggedTrips) return;
  if (due < loggedTrips) {           // scrubbed backwards: rebuild
    logBody.innerHTML = '';
    loggedTrips = 0;
  }
  for (let n = loggedTrips; n < due; n++) {
    logBody.appendChild(rowFor(trips[n], n + 1));
  }
  loggedTrips = due;
  const wrap = document.getElementById('log');
  wrap.scrollTop = wrap.scrollHeight;
  const placeholder = document.getElementById('log-empty');
  if (placeholder) placeholder.style.display = loggedTrips ? 'none' : '';
}

function paint() {
  draw();
  paintStats();
  syncLog();
  scrub.value = String(cursor);
}

function stepForward() {
  if (cursor >= bars.length - 1) { pause(); return; }
  cursor += 1;
  paint();
}

function play() {
  if (!bars.length) return;
  if (cursor >= bars.length - 1) { cursor = 0; logBody.innerHTML = ''; loggedTrips = 0; }
  playing = true;
  playBtn.textContent = 'Pause';
  const delay = parseInt(speedSel.value, 10);
  timer = setInterval(stepForward, delay);
}

function pause() {
  playing = false;
  playBtn.textContent = 'Play';
  if (timer) { clearInterval(timer); timer = null; }
}

playBtn.addEventListener('click', () => playing ? pause() : play());
document.getElementById('step').addEventListener('click', () => { pause(); stepForward(); });
document.getElementById('back').addEventListener('click', () => {
  pause();
  if (cursor > 0) { cursor -= 1; paint(); }
});
document.getElementById('reset').addEventListener('click', () => {
  pause(); cursor = 0; logBody.innerHTML = ''; loggedTrips = 0; paint();
});
document.getElementById('end').addEventListener('click', () => {
  pause(); cursor = bars.length - 1; paint();
});
scrub.addEventListener('input', () => {
  pause();
  cursor = parseInt(scrub.value, 10);
  paint();
});
speedSel.addEventListener('change', () => { if (playing) { pause(); play(); } });
windowSel.addEventListener('change', draw);
window.addEventListener('resize', resize);
document.addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); playing ? pause() : play(); }
  if (e.code === 'ArrowRight') { pause(); stepForward(); }
  if (e.code === 'ArrowLeft') { pause(); if (cursor > 0) { cursor -= 1; paint(); } }
});

if (METRICS.trades !== undefined) {
  document.getElementById('m-hit').textContent =
    METRICS.hit_rate === null ? 'n/a' : fmt(METRICS.hit_rate, 3);
  document.getElementById('m-pf').textContent =
    METRICS.profit_factor === null ? 'n/a' : fmt(METRICS.profit_factor, 3);
}

resize();
paint();
"""


def render_replay(
    tape: ReplayTape,
    metrics: Optional[PerformanceMetrics] = None,
    autoplay: bool = False,
) -> str:
    """Render a replay tape as a standalone, self-contained HTML player."""
    payload = json.dumps(tape.to_dict(), separators=(",", ":"))
    metric_payload = json.dumps(_metric_payload(metrics), separators=(",", ":"))
    script = _SCRIPT.replace("__TAPE__", payload).replace("__METRICS__", metric_payload)
    if autoplay:
        script += "\nplay();\n"

    trips = tape.round_trips()
    wins = sum(1 for trip in trips if trip["result"] == "win")
    losses = sum(1 for trip in trips if trip["result"] == "loss")
    still_open = tape.open_position_at_end()

    open_note = ""
    if still_open is not None:
        open_note = (
            f'<p class="warn">Position still open when the data ended: '
            f'{_e(still_open["direction"])} {_e(still_open["quantity"])} @ '
            f'{_e(still_open["entry_price"])} (bar #{_e(still_open["entry_bar"])}). '
            f"It has no result yet, so it is not counted as a trade.</p>"
        )

    summary = ""
    if metrics is not None:
        summary = f"""
  <div class="stats">
    <div class="stat"><div class="k">Return</div>
      <div class="v {'up' if metrics.total_return >= 0 else 'down'}">
        {metrics.total_return:.4f} ({metrics.total_return_percent:.2f}%)</div></div>
    <div class="stat"><div class="k">Max drawdown</div>
      <div class="v">{metrics.max_drawdown_percent:.2f}%</div></div>
    <div class="stat"><div class="k">Hit rate</div><div class="v" id="m-hit">n/a</div></div>
    <div class="stat"><div class="k">Profit factor</div><div class="v" id="m-pf">n/a</div></div>
    <div class="stat"><div class="k">Fees</div><div class="v">{metrics.total_fees:.4f}</div></div>
    <div class="stat"><div class="k">Spread cost</div>
      <div class="v">{metrics.spread_cost:.4f}</div></div>
    <div class="stat"><div class="k">Slippage</div>
      <div class="v">{metrics.slippage_cost:.4f}</div></div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShadBotTrader — Backtest replay</title>
<style>{_STYLES}</style>
</head>
<body>
<header>
  <h1>Backtest replay — {_e(tape.symbol)} {_e(tape.timeframe)}</h1>
  <div class="sub">session {_e(tape.session_id)} · {len(tape.bars)} bars ·
    {len(trips)} completed trades ({wins} win / {losses} loss) ·
    starting equity {tape.starting_equity}</div>
</header>

<section class="panel chart-wrap">
  <canvas id="chart" height="420"></canvas>
  <div class="controls">
    <button id="play" type="button">Play</button>
    <button id="back" class="ghost" type="button">&#8592; Bar</button>
    <button id="step" class="ghost" type="button">Bar &#8594;</button>
    <button id="reset" class="ghost" type="button">Restart</button>
    <button id="end" class="ghost" type="button">Jump to end</button>
    <input id="scrub" type="range" min="0" max="0" value="0" step="1"
           aria-label="Bar position">
    <select id="speed" aria-label="Speed">
      <option value="400">Slow</option>
      <option value="120" selected>Normal</option>
      <option value="40">Fast</option>
      <option value="8">Turbo</option>
    </select>
    <select id="window" aria-label="Visible bars">
      <option value="60">60 bars</option>
      <option value="120" selected>120 bars</option>
      <option value="250">250 bars</option>
      <option value="10000">All</option>
    </select>
  </div>
  <div class="legend">
    <span><span class="dot" style="background:#58a6ff"></span>entry fill</span>
    <span><span class="dot" style="background:#3fb950"></span>exit — profit</span>
    <span><span class="dot" style="background:#f85149"></span>exit — loss</span>
    <span>Space = play/pause · &#8592; &#8594; = one bar</span>
  </div>
  <div class="stats">
    <div class="stat"><div class="k">Bar</div><div class="v" id="s-bar">-</div></div>
    <div class="stat"><div class="k">Time</div><div class="v" id="s-time">-</div></div>
    <div class="stat"><div class="k">Close</div><div class="v" id="s-close">-</div></div>
    <div class="stat"><div class="k">Prediction</div><div class="v" id="s-pred">-</div></div>
    <div class="stat"><div class="k">Position</div><div class="v" id="s-pos">-</div></div>
    <div class="stat"><div class="k">Equity</div><div class="v" id="s-eq">-</div></div>
    <div class="stat"><div class="k">P&amp;L</div><div class="v" id="s-pnl">-</div></div>
    <div class="stat"><div class="k">Closed trades</div><div class="v" id="s-trades">0</div></div>
  </div>
</section>

<section class="panel">
  <h2>Trades — filled in as the replay reaches them</h2>
  <div class="log" id="log">
    <table>
      <thead><tr>
        <th>#</th><th>Side</th><th>Opened</th><th>Entry</th><th>Closed</th><th>Exit</th>
        <th>Bars</th><th>Fees</th><th>Net P&amp;L</th><th>Result</th>
      </tr></thead>
      <tbody id="log-body"></tbody>
    </table>
    <p class="empty" id="log-empty">No trade closed yet — press Play.</p>
  </div>
  {open_note}
</section>

<section class="panel">
  <h2>Final result of the whole run</h2>
  {summary or '<p class="empty">No metrics were supplied with this tape.</p>'}
</section>

<footer>
  Presentation only. Every candle, fill and equity value shown here was
  produced by the backtest engine — the page replays the recording, it does
  not trade, predict or recompute anything.
</footer>
<script>{script}</script>
</body>
</html>"""
