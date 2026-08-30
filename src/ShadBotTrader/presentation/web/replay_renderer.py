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
        "net_profit_factor": (
            None if metrics.net_profit_factor is None else float(metrics.net_profit_factor)
        ),
        "gross_profit": float(metrics.gross_profit),
        "gross_loss": float(metrics.gross_loss),
        "net_profit": float(metrics.net_profit),
        "net_loss": float(metrics.net_loss),
        "expectancy": None if metrics.expectancy is None else float(metrics.expectancy),
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
// فاز ۶۵: نقاط انتخاب مدل سیگنال — BUY سبز / SELL قرمز؛
// توپر = ترید واقعاً باز شد، توخالی = گیت/براکت رد کرد
const signalsByBar = {};
(TAPE.signal_points || []).forEach(s => {
  (signalsByBar[s.bar] = signalsByBar[s.bar] || []).push(s);
});
const signalCounts = { buy: 0, sell: 0, filled: 0, rejected: 0 };
(TAPE.signal_points || []).forEach(s => {
  signalCounts[s.side] += 1;
  if (s.outcome === 'filled') signalCounts.filled += 1;
  if (s.outcome === 'rejected') signalCounts.rejected += 1;
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

// فاز ۸۱ — زوم قیمت و زمان (مثل متاتریدر)
// priceZoom: ضریب بزرگ‌نمایی قیمت حول priceAnchor
// viewStart: کندلِ اولِ پنجرهٔ دید (وقتی کاربر درگ/زوم زمانی کرده)
let priceZoom = 1.0;
let priceAnchor = null;    // قیمتِ زیر موس هنگام wheel
let pricePan = 0;          // فاز ۹۱: پن عمودی ($)
let viewStart = null;      // null = از windowSel پیروی کن
let dragX = null;

// فاز ۸۶: ابزارهای ترسیم
let drawMode = null;
let pendingPoint = null;
let drawnLines = []; // {type, x1, y1, x2, y2, price1, t1}

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
  const end = cursor + 1;
  if (viewStart !== null) {
    // حالت زوم/درگ دستی — تا وقتی reset نشده، همان پنجره می‌ماند
    const size = parseInt(windowSel.value, 10);
    const start = Math.max(0, Math.min(viewStart, Math.max(0, bars.length - size)));
    return [start, Math.min(bars.length, start + size)];
  }
  const size = parseInt(windowSel.value, 10);
  const start = Math.max(0, end - size);
  return [start, end];
}

function resetZoom() {
  priceZoom = 1.0;
  priceAnchor = null;
  pricePan = 0;
  viewStart = null;
  draw();
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

  // فاز ۸۱: زوم قیمت — باند را حول priceAnchor به نسبت priceZoom جمع کن
  if (priceZoom > 1.0) {
    const anchor = priceAnchor !== null ? priceAnchor : (hi + lo) / 2;
    const span = (hi - lo) / priceZoom;
    let hiZ = anchor + span / 2;
    let loZ = anchor - span / 2;
    if (pricePan !== 0) { hiZ += pricePan; loZ += pricePan; }
    hi = hiZ; lo = loZ;
  }

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

  // ── فاز ۸۶: زمان روی محور X ──
  ctx.fillStyle = '#8b949e';
  ctx.font = '9.5px ui-monospace, monospace';
  const timeStep = Math.max(1, Math.floor(slice.length / Math.min(8, slice.length)));
  for (let i = 0; i < slice.length; i += timeStep) {
    const b = slice[i];
    if (!b.t) continue;
    const x = xOf(i);
    const dt = b.t.replace('T', ' ').slice(5, 16);
    ctx.fillText(dt, x - 28, height - 8);
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

  // signal-model selection points (فاز ۶۵) + TP/SL (فاز ۶۶)
  slice.forEach((b, i) => {
    const sigs = signalsByBar[b.i] || [];
    sigs.forEach((s, k) => {
      const x = xOf(i) + (k - (sigs.length - 1) / 2) * Math.max(6, bodyW);
      const buy = s.side === 'buy';
      const filled = s.outcome === 'filled';
      const y = buy ? yPrice(b.l) + 12 : yPrice(b.h) - 12;
      // ── سطوح TP/SL مدل: خط‌چین افقی کوتاه — سبز TP، قرمز SL ──
      if (s.tp && s.sl) {
        const tpY = yPrice(s.tp), slY = yPrice(s.sl);
        const halfW = Math.max(5, bodyW * 2.2);
        const alpha = filled ? 0.95 : 0.6;
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1.2;
        ctx.strokeStyle = `rgba(63,185,80,${alpha})`;
        ctx.beginPath();
        ctx.moveTo(x - halfW, Math.round(tpY) + 0.5);
        ctx.lineTo(x + halfW, Math.round(tpY) + 0.5);
        ctx.stroke();
        ctx.strokeStyle = `rgba(248,81,73,${alpha})`;
        ctx.beginPath();
        ctx.moveTo(x - halfW, Math.round(slY) + 0.5);
        ctx.lineTo(x + halfW, Math.round(slY) + 0.5);
        ctx.stroke();
        ctx.setLineDash([]);
        // اتصال عمودی کوتاه مثلث ↔ سطوح
        ctx.strokeStyle = `rgba(139,148,158,${alpha * 0.6})`;
        ctx.setLineDash([2, 3]);
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, tpY); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, slY); ctx.stroke();
        ctx.setLineDash([]);
        // قیمت‌ها فقط وقتی جا هست (کندل‌های بزرگ)
        if (step > 8) {
          ctx.font = '9px ui-monospace, monospace';
          ctx.fillStyle = `rgba(63,185,80,${alpha})`;
          ctx.fillText(s.tp.toFixed(1), x + halfW + 3, tpY + 3);
          ctx.fillStyle = `rgba(248,81,73,${alpha})`;
          ctx.fillText(s.sl.toFixed(1), x + halfW + 3, slY + 3);
        }
      }
      ctx.beginPath();
      if (buy) {
        ctx.moveTo(x, y - 8); ctx.lineTo(x - 5, y + 4); ctx.lineTo(x + 5, y + 4);
      } else {
        ctx.moveTo(x, y + 8); ctx.lineTo(x - 5, y - 4); ctx.lineTo(x + 5, y - 4);
      }
      ctx.closePath();
      if (filled) {
        ctx.fillStyle = buy ? '#3fb950' : '#f85149';
        ctx.fill();
      } else {
        ctx.strokeStyle = buy ? 'rgba(63,185,80,.85)' : 'rgba(248,81,73,.85)';
        ctx.lineWidth = 1.6;
        ctx.stroke();
      }
    });
  });

  // ── فاز ۸۶: خطوط ترسیمی ──
  drawnLines.forEach(line => {
    ctx.lineWidth = 1.5;
    if (line.type === 'trend') {
      ctx.strokeStyle = '#5ec8e8';
      ctx.beginPath();
      ctx.moveTo(line.x1, line.y1);
      ctx.lineTo(line.x2, line.y2);
      ctx.stroke();
    } else if (line.type === 'h') {
      ctx.strokeStyle = 'rgba(240,166,60,.7)';
      ctx.setLineDash([6, 3]);
      ctx.beginPath();
      ctx.moveTo(8, line.y1);
      ctx.lineTo(canvas.clientWidth - 62, line.y1);
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (line.type === 'v') {
      ctx.strokeStyle = 'rgba(240,166,60,.7)';
      ctx.setLineDash([6, 3]);
      ctx.beginPath();
      ctx.moveTo(line.x1, 8);
      ctx.lineTo(line.x1, priceH - 8);
      ctx.stroke();
      ctx.setLineDash([]);
      if (line.t1) {
        ctx.fillStyle = 'rgba(240,166,60,.9)';
        ctx.font = '9px ui-monospace, monospace';
        ctx.fillText(line.t1.replace('T',' ').slice(5, 16), line.x1 + 3, priceH - 12);
      }
    }
    ctx.lineWidth = 1;
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
  const meta = trip.entry_metadata || {};
  const probability = value => value === undefined || value === null || value === ''
    ? 'n/a' : fmt(Number(value) * 100, 1) + '%';
  const cells = [
    ['', String(n)],
    [trip.direction === 'long' ? 'up' : 'down', trip.direction],
    ['muted', probability(meta.sell_probability)],
    ['muted', probability(meta.buy_probability)],
    ['muted', probability(meta.confidence)],
    ['muted', '#' + trip.entry_bar + ' ' + trip.entry_time.replace('T', ' ').slice(5, 16)],
    ['', fmt(trip.entry_price)],
    ['muted', '#' + trip.exit_bar + ' ' + trip.exit_time.replace('T', ' ').slice(5, 16)],
    ['', fmt(trip.exit_price)],
    ['muted', String(trip.bars_held)],
    ['muted', trip.bracket && trip.bracket.take_profit !== undefined
      ? fmt(trip.bracket.take_profit) : 'n/a'],
    ['muted', trip.bracket && trip.bracket.stop_loss !== undefined
      ? fmt(trip.bracket.stop_loss) : 'n/a'],
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
// ── فاز ۸۶: ابزارهای ترسیم ──
function setTool(tool) {
  drawMode = (drawMode === tool) ? null : tool;
  pendingPoint = null;
  document.querySelectorAll('#tool-trend,#tool-hline,#tool-vline')
    .forEach(b => b.classList.remove('on'));
  if (drawMode) {
    const suffix = drawMode === 'trend' ? 'trend' : drawMode === 'hline' ? 'hline' : 'vline';
    const btn = document.getElementById('tool-' + suffix);
    if (btn) btn.classList.add('on');
  }
}
['trend','hline','vline'].forEach(suffix => {
  const btn = document.getElementById('tool-' + suffix);
  if (btn) btn.addEventListener('click', () => setTool(suffix));
});
const clearBtn = document.getElementById('tool-clear');
if (clearBtn) clearBtn.addEventListener('click', () => { drawnLines = []; draw(); });

canvas.addEventListener('click', e => {
  if (!drawMode) return;
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  if (drawMode === 'hline') {
    drawnLines.push({ type: 'h', y1: my });
    draw();
  } else if (drawMode === 'vline') {
    const [start, end] = visibleRange();
    const slice = bars.slice(start, end);
    const plotW = canvas.clientWidth - 8 - 62;
    const stepW = plotW / Math.max(1, slice.length);
    const rel = (mx - 8) / stepW;
    const barIdx = start + Math.floor(rel);
    const bar = bars[barIdx];
    drawnLines.push({ type: 'v', x1: mx, t1: bar ? bar.t : '' });
    draw();
  } else if (drawMode === 'trend') {
    if (!pendingPoint) { pendingPoint = { x: mx, y: my }; return; }
    drawnLines.push({ type: 'trend', x1: pendingPoint.x, y1: pendingPoint.y, x2: mx, y2: my });
    pendingPoint = null;
    draw();
  }
});
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
windowSel.addEventListener('change', () => { viewStart = null; draw(); });
window.addEventListener('resize', resize);

// ── فاز ۸۱: تعاملات موس (زوم قیمت با wheel، پن زمان با درگ) ──
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const [start, end] = visibleRange();
  const size = end - start;

  // فاز ۹۰/۹۱: wheel روی محور قیمت (سمت راست) = زوم یا پن عمودی
  const rect0 = canvas.getBoundingClientRect();
  const onPriceAxis = (e.clientX - rect0.left) > (canvas.clientWidth - 62);

  // فاز ۹۱: اگر زوم فعال و بدون Ctrl → پن عمودی
  if (onPriceAxis && priceZoom > 1.0 && !e.ctrlKey) {
    let hi = -Infinity, lo = Infinity;
    const [s0, e0] = visibleRange();
    bars.slice(s0, e0).forEach(b => { if (b.h > hi) hi = b.h; if (b.l < lo) lo = b.l; });
    if (priceZoom > 1.0) {
      const span = (hi - lo) / priceZoom;
      const anchor = priceAnchor !== null ? priceAnchor : (hi + lo) / 2;
      hi = anchor + span / 2 + pricePan;
      lo = anchor - span / 2 + pricePan;
    }
    const curSpan = (hi - lo) / 4 || 10;
    pricePan += (e.deltaY < 0 ? 1 : -1) * curSpan;
    draw();
    return;
  }

  if (e.ctrlKey || onPriceAxis) {
    const rect = canvas.getBoundingClientRect();
    const slice = bars.slice(start, end);
    if (!slice.length) return;
    const priceH = 420 * 0.72;
    let hi = -Infinity, lo = Infinity;
    slice.forEach(b => { if (b.h > hi) hi = b.h; if (b.l < lo) lo = b.l; });
    if (priceZoom > 1.0 && priceAnchor !== null) {
      const span = (hi - lo) / priceZoom;
      hi = priceAnchor + span / 2;
      lo = priceAnchor - span / 2;
    }
    const plotW = rect.width - 8 - 62;
    const rel = Math.min(1, Math.max(0, (e.clientX - rect.left - 8) / plotW));
    const mousePrice = hi - rel * (hi - lo);

    const factor = e.deltaY < 0 ? 1.25 : 1 / 1.25;
    priceZoom = Math.min(30, Math.max(1.0, priceZoom * factor));
    priceAnchor = mousePrice;
    if (priceZoom === 1.0) priceAnchor = null;
    draw();
    return;
  }

  // فاز ۸۲: wheel = اسکرول زمان (مثل متاتریدر) — جلو/عقب بین کندل‌ها
  const step = Math.max(1, Math.round(size / 15));
  const shift = (e.deltaY < 0 ? -1 : 1) * step;
  if (viewStart === null) viewStart = start;
  viewStart = Math.max(0, Math.min(bars.length - size, viewStart + shift));
  draw();
}, { passive: false });

canvas.addEventListener('mousedown', e => { dragX = e.clientX; });
canvas.addEventListener('mousemove', e => {
  if (dragX === null) return;
  const dx = e.clientX - dragX;
  if (Math.abs(dx) < 6) return;         // آستانهٔ درگ
  dragX = e.clientX;
  const size = parseInt(windowSel.value, 10);
  const [start, end] = visibleRange();
  const plotW = canvas.clientWidth - 8 - 62;
  const stepPx = plotW / Math.max(1, end - start);
  const shift = Math.round(dx / stepPx);
  if (shift === 0) return;
  viewStart = Math.max(0, Math.min(bars.length - size, (viewStart ?? start) + shift));
  draw();
});
canvas.addEventListener('mouseup', () => { dragX = null; });
canvas.addEventListener('mouseleave', () => { dragX = null; });

// دکمهٔ ریست زوم
document.getElementById('zoom-reset').addEventListener('click', resetZoom);
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

    # فاز ۶۵: شمارش نقاط سیگنال برای legend
    signal_counts = {"buy": 0, "sell": 0, "filled": 0, "rejected": 0}
    for point in tape.signal_points:
        signal_counts[point.side] = signal_counts.get(point.side, 0) + 1
        if point.outcome in ("filled", "rejected"):
            signal_counts[point.outcome] += 1

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
        net_profit_factor = (
            metrics.net_profit_factor if metrics.net_profit_factor is not None else "n/a"
        )
        net_expectancy = metrics.expectancy if metrics.expectancy is not None else "n/a"
        summary = f"""
  <div class="stats">
    <div class="stat"><div class="k">Return</div>
      <div class="v {'up' if metrics.total_return >= 0 else 'down'}">
        {metrics.total_return:.4f} ({metrics.total_return_percent:.2f}%)</div></div>
    <div class="stat"><div class="k">Max drawdown</div>
      <div class="v">{metrics.max_drawdown_percent:.2f}%</div></div>
    <div class="stat"><div class="k">Hit rate</div><div class="v" id="m-hit">n/a</div></div>
    <div class="stat"><div class="k">Profit factor</div><div class="v" id="m-pf">n/a</div></div>
    <div class="stat"><div class="k">Net profit factor</div>
      <div class="v">{net_profit_factor}</div></div>
    <div class="stat"><div class="k">Net expectancy</div>
      <div class="v">{net_expectancy}</div></div>
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
  <div class="controls" style="margin-top:6px">
    <button id="zoom-reset" class="ghost" type="button">&#8634; Reset zoom</button>
    <span style="color:#8b949e;align-self:center;font-size:12px">
      wheel = اسکرول زمان · Ctrl+wheel = زوم قیمت · درگ = جابجایی
    </span>
  </div>
  <div class="controls" style="margin-top:4px">
    <button id="tool-trend" class="ghost" type="button" title="خط روند">╱ Trend</button>
    <button id="tool-hline" class="ghost" type="button" title="خط افقی">─ H-Line</button>
    <button id="tool-vline" class="ghost" type="button" title="خط عمودی">│ V-Line</button>
    <button id="tool-clear" class="ghost" type="button">&#10005; Clear</button>
  </div>
  <div class="legend">
    <span><span class="dot" style="background:#58a6ff"></span>entry fill</span>
    <span><span class="dot" style="background:#3fb950"></span>&#9650; signal BUY
      ({signal_counts["buy"]})</span>
    <span><span class="dot" style="background:#f85149"></span>&#9660; signal SELL
      ({signal_counts["sell"]})</span>
    <span><span class="dot" style="background:#8b949e"></span>hollow = rejected
      ({signal_counts["rejected"]}) · solid = traded ({signal_counts["filled"]})</span>
    <span><span class="dot" style="background:#3fb950"></span>&#9472;&#9472; TP
      model</span>
    <span><span class="dot" style="background:#f85149"></span>&#9472;&#9472; SL
      model</span>
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
        <th>#</th><th>Side</th><th>Sell %</th><th>Buy %</th><th>Conf.</th>
        <th>Opened</th><th>Entry</th><th>Closed</th><th>Exit</th>
        <th>Bars</th><th>TP</th><th>SL</th><th>Fees</th><th>Net P&amp;L</th><th>Result</th>
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
