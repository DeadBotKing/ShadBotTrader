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
let pricePan = 0;       // فاز ۹۱: جابجایی عمودی بر حسب $ (وقتی zoom > 1)
let viewStart = null;   // null = آخرین N کندل؛ عدد = شروعِ دستی
let dragX = null;

// فاز ۸۵-ب: مسیر پیش‌بینی رنج برای رسم روی چارت
let forecastPath = null;   // { localIdx, points: [{high, low}] }

// فاز ۸۶: ابزارهای ترسیم
let drawMode = null;       // 'trend' | 'hline' | 'vline' | null
let pendingPoint = null;   // نقطهٔ اول trend
let drawnLines = [];       // {type:'trend'|'h'|'v', x1,y1,x2,y2, price1, price2, t1, t2}

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
  const priceH = height - volumeH - 40;
  const padL = 8, padR = 66;

  ctx.clearRect(0, 0, width, height);

  // ── slice با ادامهٔ future برای forecast overlay ──
  let sliceEnd = CANDLES.length;
  if (viewStart !== null) {
    sliceEnd = Math.min(CANDLES.length, viewStart + visible);
  } else {
    sliceEnd = CANDLES.length;
  }
  const sliceStart = (viewStart !== null)
    ? Math.max(0, Math.min(viewStart, Math.max(0, CANDLES.length - visible)))
    : Math.max(0, CANDLES.length - visible);

  // اگر forecast داریم و anchor+horizon از sliceEnd رد می‌شود، گسترش بده
  let forecastFuture = 0;
  if (forecastPath && forecastPath.localIdx >= 0) {
    const needed = forecastPath.localIdx + forecastPath.points.length;
    if (needed > sliceEnd - sliceStart) forecastFuture = needed - (sliceEnd - sliceStart);
  }
  const totalSlots = (sliceEnd - sliceStart) + forecastFuture;

  const slice = [];
  for (let k = sliceStart; k < sliceEnd; k++) {
    if (k < CANDLES.length) slice.push(CANDLES[k]);
  }

  // future candles (واقعی، بعد از anchor) برای مقایسه با forecast
  let futureCandles = [];
  if (forecastPath && forecastPath.localIdx >= 0) {
    const anchorAbs = sliceStart + forecastPath.localIdx;
    const fStart = anchorAbs + 1;
    const fEnd = Math.min(CANDLES.length, anchorAbs + 1 + forecastPath.points.length);
    for (let k = fStart; k < fEnd; k++) {
      if (k < CANDLES.length) futureCandles.push({ idx: k - sliceStart, bar: CANDLES[k] });
    }
  }

  let hi = -Infinity, lo = Infinity, maxVol = 0;
  slice.forEach(c => {
    if (c.h > hi) hi = c.h;
    if (c.l < lo) lo = c.l;
    if (c.v > maxVol) maxVol = c.v;
  });
  // future candles هم در hi/lo شرکت کنند
  futureCandles.forEach(f => { if (f.bar.h > hi) hi = f.bar.h; if (f.bar.l < lo) lo = f.bar.l; });
  if (forecastPath) {
    forecastPath.points.forEach(p => {
      if (p.high > hi) hi = p.high;
      if (p.low < lo) lo = p.low;
    });
  }
  if (hi === lo) { hi += 1; lo -= 1; }

  // زوم قیمت
  if (priceZoom > 1.0) {
    const anchor = priceAnchor !== null ? priceAnchor : (hi + lo) / 2;
    let span = (hi - lo) / priceZoom;
    let hiZ = anchor + span / 2;
    let loZ = anchor - span / 2;
    if (pricePan !== 0) { hiZ += pricePan; loZ += pricePan; }
    hi = hiZ; lo = loZ;
  }

  const plotW = width - padL - padR;
  const step = plotW / Math.max(1, totalSlots);
  const bodyW = Math.max(1.5, Math.min(12, step * 0.66));
  const yP = p => 8 + (hi - p) / (hi - lo) * (priceH - 16);
  const xOf = i => padL + i * step + step / 2;

  // ── guides ──
  ctx.strokeStyle = 'rgba(38,45,56,.75)';
  ctx.fillStyle = '#8b949e';
  ctx.font = '10px ui-monospace, monospace';
  for (let k = 0; k <= 4; k++) {
    const price = lo + (hi - lo) * k / 4;
    const y = Math.round(yP(price)) + 0.5;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke();
    ctx.fillText(price.toFixed(2), width - padR + 6, y + 3);
  }

  // ── candles ──
  slice.forEach((c, i) => {
    const x = xOf(i);
    const colour = c.c >= c.o ? '#3fb950' : '#f85149';
    ctx.strokeStyle = colour; ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.moveTo(Math.round(x) + 0.5, yP(c.h));
    ctx.lineTo(Math.round(x) + 0.5, yP(c.l));
    ctx.stroke();
    const botY = yP(Math.min(c.o, c.c));
    const topY = yP(Math.max(c.o, c.c));
    ctx.fillRect(x - bodyW / 2, topY, bodyW, Math.max(1, botY - topY));
  });

  // ── future candles (hollow/outline برای تمایز از real past) ──
  futureCandles.forEach(f => {
    const c = f.bar;
    const x = xOf(f.idx);
    const colour = c.c >= c.o ? 'rgba(63,185,80,.5)' : 'rgba(248,81,73,.5)';
    ctx.strokeStyle = colour; ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.moveTo(Math.round(x) + 0.5, yP(c.h));
    ctx.lineTo(Math.round(x) + 0.5, yP(c.l));
    ctx.stroke();
    const top = yP(Math.max(c.o, c.c));
    const bot = yP(Math.min(c.o, c.c));
    // hollow body
    ctx.lineWidth = 1.2;
    ctx.strokeRect(x - bodyW / 2, top, bodyW, Math.max(1, bot - top));
    ctx.lineWidth = 1;
  });

  // ── forecast path ──
  if (forecastPath && forecastPath.points.length && forecastPath.localIdx >= 0) {
    const li = forecastPath.localIdx;
    // خط عمودی anchor
    const anchorX = xOf(li);
    ctx.strokeStyle = 'rgba(139,148,158,.5)';
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(Math.round(anchorX) + 0.5, 8);
    ctx.lineTo(Math.round(anchorX) + 0.5, priceH - 8);
    ctx.stroke();
    ctx.setLineDash([]);

    // خطوط high و low
    const drawPath = (key, colour) => {
      ctx.strokeStyle = colour;
      ctx.lineWidth = 1.6;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      forecastPath.points.forEach((pt, k) => {
        const x = xOf(li + k + 1);
        const y = yP(pt[key]);
        k === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
      forecastPath.points.forEach((pt, k) => {
        const x = xOf(li + k + 1);
        ctx.fillStyle = colour;
        ctx.beginPath();
        ctx.arc(x, yP(pt[key]), 2.5, 0, Math.PI * 2);
        ctx.fill();
      });
    };
    drawPath('high', 'rgba(63,185,80,.9)');
    drawPath('low', 'rgba(248,81,73,.9)');

    // ناحیهٔ بین‌شان
    ctx.fillStyle = 'rgba(94,200,232,.06)';
    ctx.beginPath();
    forecastPath.points.forEach((pt, k) => {
      const x = xOf(li + k + 1);
      k === 0 ? ctx.moveTo(x, yP(pt.high)) : ctx.lineTo(x, yP(pt.high));
    });
    for (let k = forecastPath.points.length - 1; k >= 0; k--) {
      ctx.lineTo(xOf(li + k + 1), yP(forecastPath.points[k].low));
    }
    ctx.closePath();
    ctx.fill();

    // برچسب آخرین نقطه
    if (step > 6 && forecastPath.points.length) {
      const lastPt = forecastPath.points[forecastPath.points.length - 1];
      const lx = xOf(li + forecastPath.points.length);
      ctx.font = '9px ui-monospace, monospace';
      ctx.fillStyle = 'rgba(63,185,80,.9)';
      ctx.fillText(lastPt.high.toFixed(1), lx + 3, yP(lastPt.high) + 3);
      ctx.fillStyle = 'rgba(248,81,73,.9)';
      ctx.fillText(lastPt.low.toFixed(1), lx + 3, yP(lastPt.low) + 3);
    }
  }

  // ── volume ──
  // ── فاز ۸۴: نقاط سیگنال ──
  if (currentSignals.length) {
    // c.i (سراسری از data_inspector) ↔ s.i (محلی نسبت به CANDLES)
    // → با اندیس سراسری match کن
    const indexOf = new Map();
    slice.forEach((c, i) => {
      if (c.i !== undefined) indexOf.set(c.i, i);       // سراسری
      else indexOf.set(i, i);                            // fallback
    });
    currentSignals.forEach(s => {
      const local = indexOf.get(s.i);
      if (local === undefined) return;
      const c = slice[local];
      const x = xOf(local);
      const buy = s.side === 'buy';
      ctx.beginPath();
      if (buy) {
        const y = yP(c.l) + 9;
        ctx.moveTo(x, y - 8); ctx.lineTo(x - 5, y + 4); ctx.lineTo(x + 5, y + 4);
        ctx.fillStyle = '#3fb950';
      } else {
        const y = yP(c.h) - 9;
        ctx.moveTo(x, y + 8); ctx.lineTo(x - 5, y - 4); ctx.lineTo(x + 5, y - 4);
        ctx.fillStyle = '#f85149';
      }
      ctx.closePath();
      ctx.fill();
    });
  }

  if (showVolume && maxVol > 0) {
    const base = height - 34;
    slice.forEach((c, i) => {
      const x = xOf(i);
      const h = (c.v / maxVol) * (volumeH - 10);
      ctx.fillStyle = c.c >= c.o ? 'rgba(63,185,80,.45)' : 'rgba(248,81,73,.45)';
      ctx.fillRect(x - bodyW / 2, base - h, bodyW, h);
    });
  }

  // ── خطوط ترسیمی (فاز ۸۶) ──
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
      ctx.moveTo(padL, line.y1);
      ctx.lineTo(width - padR, line.y1);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(240,166,60,.9)';
      ctx.font = '9px ui-monospace, monospace';
      ctx.fillText('$' + line.price1.toFixed(2), width - padR + 2, line.y1 + 3);
    } else if (line.type === 'v') {
      ctx.strokeStyle = 'rgba(240,166,60,.7)';
      ctx.setLineDash([6, 3]);
      ctx.beginPath();
      ctx.moveTo(line.x1, 8);
      ctx.lineTo(line.x1, height - volumeH - 14);
      ctx.stroke();
      ctx.setLineDash([]);
      if (line.t1) {
        ctx.fillStyle = 'rgba(240,166,60,.9)';
        ctx.font = '9px ui-monospace, monospace';
        ctx.fillText(line.t1.slice(5, 16), line.x1 + 3, height - volumeH - 18);
      }
    }
  });

  // ── time axis: تاریخ/ساعت روی محور ──
  ctx.fillStyle = '#8b949e';
  ctx.font = '9.5px ui-monospace, monospace';
  const timeStep = Math.max(1, Math.floor(slice.length / Math.min(8, slice.length)));
  for (let i = 0; i < slice.length; i += timeStep) {
    const c = slice[i];
    if (!c.t) continue;
    const x = xOf(i);
    const dt = c.t.replace('T', ' ').slice(5, 16);   // MM-DD HH:MM
    ctx.fillText(dt, x - 28, height - 8);
  }

  // ── stats ──
  const last = slice[slice.length - 1];
  if (last) {
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
        `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${pct.toFixed(2)}%)</div></div>` +
        `<div class="stat"><div class="k">Lines</div>` +
        `<div class="v">${drawnLines.length}</div></div>`;
    }
  }
}

// ── فاز ۸۶: تبدیل y → قیمت و x → کندل ──
function _currentScale() {
  if (!CANDLES.length) return null;
  const base = (viewStart !== null) ? viewStart : Math.max(0, CANDLES.length - visible);
  const slice = CANDLES.slice(base, base + visible);
  if (!slice.length) return null;
  let hi = -Infinity, lo = Infinity;
  slice.forEach(c => { if (c.h > hi) hi = c.h; if (c.l < lo) lo = c.l; });
  if (forecastPath) forecastPath.points.forEach(p => {
    if (p.high > hi) hi = p.high; if (p.low < lo) lo = p.low;
  });
  if (hi === lo) { hi += 1; lo -= 1; }
  if (priceZoom > 1.0) {
    const anchor = priceAnchor !== null ? priceAnchor : (hi + lo) / 2;
    const span = (hi - lo) / priceZoom;
    let hiZ = anchor + span / 2;
    let loZ = anchor - span / 2;
    if (pricePan !== 0) { hiZ += pricePan; loZ += pricePan; }
    hi = hiZ; lo = loZ;
  }
  const height = 460;
  const volumeH = showVolume ? 70 : 0;
  const priceH = height - volumeH - 40;
  return {
    hi, lo, priceH, plotW: canvas.clientWidth - 8 - 66,
    padL: 8, padR: 66, base, visible
  };
}

function _priceAtY(y) {
  const s = _currentScale();
  if (!s) return null;
  return s.hi - (y - 8) / (s.priceH - 16) * (s.hi - s.lo);
}

function _barAtX(x) {
  const s = _currentScale();
  if (!s) return null;
  const rel = (x - s.padL) / s.plotW;
  const absIdx = Math.floor(rel * s.visible);
  return Math.max(0, Math.min(CANDLES.length - 1, s.base + absIdx));
}


// ── فاز ۸۴: سیگنال‌های first-passage روی همان کندل‌های چارت ──
// قانون دقیقاً مثل آموزش: اولین close که ±threshold را بزند؛
// BUY معتبر تا وقتی Low زیر Lowِ کندل شروع نرود (و برعکس برای SELL).
function computeSignals(threshold) {
  const signals = [];   // {i: سراسری, side}
  const n = CANDLES.length;
  if (!n) return signals;
  const base = CANDLES[0].i !== undefined ? CANDLES[0].i : 0;
  for (let start = 0; start < n - 1; start++) {
    const c0 = CANDLES[start];
    const upper = c0.c * (1 + threshold);
    const lower = c0.c * (1 - threshold);
    let label = null;
    for (let k = start + 1; k < n; k++) {
      const c = CANDLES[k];
      const buyHit = c.c >= upper;
      const buyInvalid = c.l < c0.l;
      const sellHit = c.c <= lower;
      const sellInvalid = c.h > c0.h;
      if (buyHit && (!sellHit || !sellInvalid)) { label = 'buy'; break; }
      if (sellHit && (!buyHit || !buyInvalid)) { label = 'sell'; break; }
      if (buyInvalid && sellInvalid) break;
      if (buyInvalid) break;
      if (sellInvalid) break;
    }
    if (label) signals.push({ i: base + start, side: label });
  }
  return signals;
}

let currentSignals = [];

function renderSignals() {
  const box = document.getElementById('show-signals');
  const thEl = document.getElementById('sig-threshold');
  const summary = document.getElementById('sig-summary');
  if (!box || !thEl) return;
  if (!box.checked) { currentSignals = []; summary.textContent = ''; draw(); return; }
  const th = parseFloat(thEl.value) / 100;
  if (!(th > 0)) return;
  currentSignals = computeSignals(th);
  const buys = currentSignals.filter(s => s.side === 'buy').length;
  const sells = currentSignals.length - buys;
  summary.textContent =
    `${currentSignals.length} signals · ${buys} \u25b2 · ${sells} \u25bc` +
    ` (th ${thEl.value}%)`;
  draw();
}

const sigBox = document.getElementById('show-signals');
const sigTh = document.getElementById('sig-threshold');
if (sigBox) sigBox.addEventListener('change', renderSignals);
let sigThTimer = null;
if (sigTh) sigTh.addEventListener('input', () => {
  clearTimeout(sigThTimer);
  sigThTimer = setTimeout(renderSignals, 250);
});

// ── فاز ۸۵: dropdown مدل رنج + کلیک روی کندل → پیش‌بینی ──
const RANGE_MODELS = __RANGE_MODELS__;
const rfModel = document.getElementById('rf-model');
const rfStatus = document.getElementById('rf-status');
const rfPanel = document.getElementById('rf-panel');

if (rfModel) {
  RANGE_MODELS.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.model_id;
    // فاز ۹۶-و/۹۸: تایم‌فریم + kind — trend یعنی رنگ کندل بعدی
    const tf = m.timeframe || '?';
    const tag = m.kind === 'trend' ? ' [trend: color]' : '';
    opt.textContent = `${m.model_id} v${m.version} · h${m.horizon} · ${tf} · ${m.trained_at}${tag}`;
    rfModel.appendChild(opt);
  });
}

function updateRfStatus(text) {
  if (rfStatus) rfStatus.textContent = text;
}

async function fetchForecast(barIndex, symbol, timeframe, localIdx) {
  const modelId = rfModel ? rfModel.value : '';
  if (!modelId) return;
  updateRfStatus('predicting…');
  // فاز ۹۸-ب: مدل ترند → جدا fetch می‌شود (fetchTrendColor مستقیم)
  // فاز ۹۹: فقط gold_trend_1d/4h (رنگ) → fetchTrendColor
  // gold_trend_score_* و gold_trend_signal_* مسیر range معمولی
  const isColorModel = modelId.startsWith('gold_trend_')
    && !modelId.startsWith('gold_trend_score_')
    && !modelId.startsWith('gold_trend_signal_');
  if (isColorModel) {
    if (rfPanel) rfPanel.style.display = '';
    await fetchTrendColor(barIndex, symbol, timeframe, modelId);
    forecastPath = null; draw();
    updateRfStatus('');
    return;
  }
  const params = new URLSearchParams({
    symbol, timeframe, model: modelId, bar: String(barIndex),
  });
  try {
    const res = await fetch(`/api/range-forecast?${params}`);
    const data = await res.json();
    if (data.error) {
      updateRfStatus(`[X] ${data.error}`);
      if (rfPanel) rfPanel.style.display = 'none';
      return;
    }
    // فاز ۹۹: مدل‌های score و signal خروجی متفاوت دارند
    if (data.target_units === 'score' || data.target_units === 'trend_signal') {
      renderTrendModel(data);
      updateRfStatus('');
      return;
    }
    renderForecast(data, localIdx);
    updateRfStatus('');
  } catch (err) {
    updateRfStatus(`[X] ${err.message}`);
  }
}

function renderTrendModel(data) {
  if (!rfPanel) return;
  rfPanel.style.display = '';
  const header = document.getElementById('rf-header');
  if (data.target_units === 'score') {
    header.innerHTML = '<th>Score</th><th>Direction</th>';
  } else {
    header.innerHTML = '<th>Signal</th><th>Probabilities</th>';
  }
  document.getElementById('rf-stats').innerHTML =
    `<div class="stat"><div class="k">Model</div>` +
    `<div class="v">${data.model_id} v${data.model_version}</div></div>`;
  const rows = document.getElementById('rf-rows');
  rows.innerHTML = '';
  const pts = data.points || [];
  pts.forEach(p => {
    const tr = document.createElement('tr');
    if (p.score !== undefined) {
      const dir = p.direction || '';
      const colour = p.score > 0.1 ? '#3fb950' : (p.score < -0.1 ? '#f85149' : '#8b949e');
      tr.innerHTML = `<td style="color:${colour};font-weight:600">${p.score.toFixed(4)}</td>` +
        `<td colspan="4" style="color:${colour}">${dir}</td>`;
    } else if (p.signal !== undefined) {
      tr.innerHTML = `<td style="font-weight:600">${p.signal}</td>` +
        `<td colspan="4">SELL ${((p.sell_p||0)*100).toFixed(1)}% · ` +
        `HOLD ${((p.hold_p||0)*100).toFixed(1)}% · ` +
        `BUY ${((p.buy_p||0)*100).toFixed(1)}%</td>`;
    }
    rows.appendChild(tr);
  });
  forecastPath = null; draw();
}

async function fetchTrendColor(barIndex, symbol, timeframe, modelOverride) {
  const trendBox = document.getElementById('trend-color');
  if (!trendBox) return;
  trendBox.innerHTML = '<span style="color:#8b949e">trend: …</span>';
  // فاز ۹۸-ب: اگر کاربر مدل ترند انتخاب کرده از همان استفاده کن؛
  // وگرنه مدل هم‌تایم‌فریم با سری فعال (gold_trend_${tf})
  const trendModelId = modelOverride || `gold_trend_${(timeframe || '').toLowerCase()}`;
  const params = new URLSearchParams({
    symbol, timeframe, model: trendModelId, bar: String(barIndex),
  });
  try {
    const res = await fetch(`/api/trend-forecast?${params}`);
    const data = await res.json();
    if (data.error) {
      // فاز ۹۸-ب: پیام واقعی سرور را نشان بده — نه پیام هاردکد
      const savedTrend = RANGE_MODELS.filter(m => m.kind === 'trend')
        .map(m => m.model_id).join(', ') || 'هیچ';
      trendBox.innerHTML =
        `<span style="color:#f85149">trend: ${data.error}</span>` +
        ` <span style="color:#8b949e">(saved trend models: ${savedTrend})</span>`;
      return;
    }
    const green = data.color === 'GREEN';
    const colour = green ? '#3fb950' : '#f85149';
    const pct = ((green ? data.green_probability : data.red_probability) * 100).toFixed(1);
    trendBox.innerHTML =
      `<span style="color:${colour};font-weight:600">` +
      `${green ? '▲' : '▼'} ${data.color} (${pct}%)</span>` +
      ` <span style="color:#8b949e">— روند پیش‌بینی ${data.trend}` +
      ` · ${data.model_id} v${data.model_version}</span>`;
  } catch (err) {
    trendBox.innerHTML = `<span style="color:#8b949e">trend: ${err.message}</span>`;
  }
}

function renderForecast(f, localIdx, symbolTf) {
  if (!rfPanel) return;
  rfPanel.style.display = '';
  const anchorTime = f.anchor_time.replace('T', ' ').slice(0, 16);
  let statsHtml =
    `<div class="stat"><div class="k">Model</div>` +
    `<div class="v">${f.model_id} v${f.model_version}</div></div>` +
    `<div class="stat"><div class="k">Anchor</div>` +
    `<div class="v">${anchorTime}</div></div>` +
    `<div class="stat"><div class="k">Anchor close</div>` +
    `<div class="v">${f.anchor_close.toFixed(2)}</div></div>` +
    `<div class="stat"><div class="k">Horizon</div>` +
    `<div class="v">${f.horizon} × ${f.timeframe}</div></div>`;
  statsHtml +=
    `<div class="stat"><div class="k">Base price</div>` +
    `<div class="v">${f.reference_close.toFixed(2)}</div></div>`;
  // فاز ۹۵: مدل ATR — واحد و ATR مرجع را نشان بده
  if (f.target_units === 'atr') {
    statsHtml +=
      `<div class="stat"><div class="k">Units</div>` +
      `<div class="v">ATR mult</div></div>` +
      `<div class="stat"><div class="k">ATR(14)</div>` +
      `<div class="v">${Number(f.atr_reference || 0).toFixed(2)}</div></div>`;
  }
  document.getElementById('rf-stats').innerHTML = statsHtml;
  const rows = document.getElementById('rf-rows');
  rows.innerHTML = '';
  const offText = (p, key, multKey) => {
    if (p[multKey] !== undefined && p[multKey] !== null) {
      return `${p[multKey].toFixed(2)}×ATR (${(p[key]*100).toFixed(2)}%)`;
    }
    return `(${(p[key]*100).toFixed(2)}%)`;
  };
  f.points.forEach(p => {
    const tr = document.createElement('tr');
    [[`+${p.k}`], [`${p.high.toFixed(2)} ${offText(p, 'high_offset', 'high_atr_mult')}`],
     [`${p.low.toFixed(2)} ${offText(p, 'low_offset', 'low_atr_mult')}`]].forEach(([text]) => {
      const td = document.createElement('td');
      td.textContent = text;
      tr.appendChild(td);
    });
    rows.appendChild(tr);
  });

  // فاز ۹۲: مسیر را برای رسم روی چارت آماده کن
  if (localIdx !== undefined && localIdx >= 0) {
    forecastPath = {
      localIdx: localIdx,
      points: f.points.map(p => ({ high: p.high, low: p.low })),
    };
    // فاز ۹۵-ه: بدون draw() مسیر فقط با بلور بعدی (اسکرول/زوم) ظاهر
    // می‌شد — اپراتور فقط جدول عددی می‌دید.
    draw();
  }
}

if (rfModel) {
  rfModel.addEventListener('change', () => {
    forecastPath = null; draw();
    if (rfPanel) rfPanel.style.display = 'none';
  });
}

const windowSelect = document.getElementById('window');
if (windowSelect) {
  windowSelect.addEventListener('change', () => {
    visible = parseInt(windowSelect.value, 10);
    viewStart = null;
    forecastPath = null;   // کندل‌ها عوض شدند → forecast کهنه
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

    // فاز ۹۰: wheel روی محور قیمت (سمت راست چارت) = زوم قیمت همیشه
    const canvasRightEdge = canvas.clientWidth - 66;
    const rect = canvas.getBoundingClientRect();
    const onPriceAxis = e.clientX - rect.left > canvasRightEdge;

    // فاز ۹۱: wheel روی محور قیمت و زوم فعال → پن عمودی (جابجایی بالا/پایین)
    if (onPriceAxis && priceZoom > 1.0 && !e.ctrlKey) {
      // محدودهٔ فعلی (با زوم و پن قبلی)
      let hi = -Infinity, lo = Infinity;
      const slice = (viewStart !== null)
        ? CANDLES.slice(Math.max(0, Math.min(viewStart, CANDLES.length - visible)))
        : CANDLES.slice(-visible);
      slice.forEach(c => { if (c.h > hi) hi = c.h; if (c.l < lo) lo = c.l; });
      if (priceZoom > 1.0) {
        const span = (hi - lo) / priceZoom;
        const anchor = priceAnchor !== null ? priceAnchor : (hi + lo) / 2;
        hi = anchor + span / 2 + pricePan;
        lo = anchor - span / 2 + pricePan;
      }
      const curSpan = (hi - lo) / 4 || 10;
      pricePan += (e.deltaY < 0 ? 1 : -1) * curSpan;

      // قیمتِ زیر موس برای آپدیت anchor
      const priceH = 460 * 0.72;
      const rel = Math.min(1, Math.max(0, (e.clientY - rect.top - 8) / (priceH - 16)));
      priceAnchor = (hi - rel * (hi - lo)) - pricePan;

      draw();
      return;
    }

    if (e.ctrlKey || onPriceAxis) {
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
      return;
    }

    // فاز ۸۲: wheel = اسکرول زمان (مثل متاتریدر)
    const step = Math.max(1, Math.round(visible / 15));
    const shift = (e.deltaY < 0 ? -1 : 1) * step;
    if (viewStart === null) {
      viewStart = (viewStart !== null) ? viewStart : Math.max(0, CANDLES.length - visible);
    }
    viewStart = Math.max(0, Math.min(CANDLES.length - visible, viewStart + shift));
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
const tt = document.getElementById('tool-trend');
const th = document.getElementById('tool-hline');
const tv = document.getElementById('tool-vline');
const tc = document.getElementById('tool-clear');
if (tt) tt.addEventListener('click', () => setTool('trend'));
if (th) th.addEventListener('click', () => setTool('hline'));
if (tv) tv.addEventListener('click', () => setTool('vline'));
if (tc) tc.addEventListener('click', () => { drawnLines = []; draw(); });

// ── فاز ۸۵: کلیک روی کندل → fetch forecast (اگر مدل انتخاب شده) ──
const chartCanvas = document.getElementById('chart');
if (chartCanvas) {
  chartCanvas.addEventListener('click', e => {
    if (!CANDLES.length || !rfModel || !rfModel.value) return;
    // درگ را نادیده بگیر (فقط کلیک ساده)
    const rect = chartCanvas.getBoundingClientRect();
    const width = chartCanvas.clientWidth;
    const padL = 8, padR = 66;
    const plotW = width - padL - padR;
    const rel = Math.min(1, Math.max(0, (e.clientX - rect.left - padL) / plotW));
    const base = (viewStart !== null)
      ? Math.max(0, Math.min(viewStart, Math.max(0, CANDLES.length - visible)))
      : Math.max(0, CANDLES.length - visible);
    const idx = Math.min(CANDLES.length - 1, base + Math.floor(rel * visible));
    const bar = CANDLES[idx];
    if (!bar) return;

    let symbol = 'XAUUSD', timeframe = '1H';
    const symSel = document.querySelector('select[name="series"]');
    if (symSel && symSel.value.includes('|')) {
      [symbol, timeframe] = symSel.value.split('|');
    }
    updateRfStatus(`bar #${bar.i ?? idx} — predicting…`);
    // فاز ۹۵-ه: localIdx باید «موقعیت در slice» باشد نه اندیس گلوبال —
    // draw() با xOf(localIdx) رسم می‌کند و گلوبال مسیر را بیرون بوم
    // می‌برد و totalSlots را منفجر می‌کرد.
    const localIdx = idx - base;
    window._clickedLocalIdx = localIdx;
    fetchForecast(bar.i !== undefined ? bar.i : idx, symbol, timeframe, localIdx);
  });
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
      <option value="120" selected>120 candles</option>
      <option value="300">300 candles</option>
      <option value="500">500 candles</option>
      <option value="1000">1,000 candles</option>
      <option value="2000">2,000 candles</option>
      <option value="5000">5,000 candles</option>
    </select>
    <button id="toggle-volume" class="on" type="button">Volume</button>
    <button id="zoom-reset" class="ghost" type="button">&#8634; Reset zoom</button>
    <label style="display:inline-flex;align-items:center;gap:6px;color:#8b949e;font-size:12px">
      <input id="show-signals" type="checkbox"> Show signals
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;color:#8b949e;font-size:12px">
      threshold %
      <input id="sig-threshold" type="number" step="0.05" min="0.05" value="0.6"
             style="width:70px;background:#0d1117;color:#dce3f2;
                    border:1px solid #2a3348;border-radius:4px;padding:2px 6px">
    </label>
    <span id="sig-summary" style="color:#8b949e;font-size:12px"></span>
    <span style="width:1px;height:20px;background:#2a3348;align-self:center"></span>
    <button id="tool-trend" class="ghost" type="button" title="خط روند">╱ Trend</button>
    <button id="tool-hline" class="ghost" type="button" title="خط افقی">─ H-Line</button>
    <button id="tool-vline" class="ghost" type="button" title="خط عمودی">│ V-Line</button>
    <button id="tool-clear" class="ghost" type="button" title="پاک کردن همه">&#10005; Clear</button>
    <span style="color:#8b949e;align-self:center;font-size:12px">
      wheel = اسکرول زمان · Ctrl+wheel = زوم قیمت · درگ = پن
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
    range_models: Sequence[Dict[str, Any]] = (),
) -> str:
    """The complete data-inspection page."""
    chart_data = json.dumps(candles.get("chart", []), separators=(",", ":"))
    models_data = json.dumps(list(range_models), separators=(",", ":"))
    script = _CHART_SCRIPT.replace("__CANDLES__", chart_data).replace(
        "__RANGE_MODELS__", models_data
    )

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
<section class="panel">
  <h2>Range model forecast</h2>
  <p class="sub">
    یک کندل روی چارت کلیک کن تا پیش‌بینی رنجِ مدل برای کندل‌های بعدی دیده شود.
    پنجرهٔ مدل فقط کندل‌های قبل از آن نقطه را می‌بیند (علیت حفظ می‌شود).
  </p>
  <div class="controls" style="margin-bottom:10px">
    <label style="color:#8b949e;font-size:12px">Range model
      <select id="rf-model" style="background:#0d1117;color:#dce3f2;
              border:1px solid #2a3348;border-radius:4px;padding:3px 8px"></select>
    </label>
    <span id="rf-status" style="color:#8b949e;font-size:12px"></span>
    <span style="color:#8b949e;font-size:11px;margin-right:8px">
      (فقط مدل‌های هم‌تایم‌فریم با سری انتخابی نمایش داده می‌شوند)
    </span>
  </div>
  <div id="rf-panel" style="display:none">
    <div id="trend-color" style="padding:6px 0;font-size:13px"></div>
    <div class="stats" id="rf-stats"></div>
    <table class="scroll" id="rf-table">
      <thead><tr id="rf-header"></tr></thead>
      <tbody id="rf-rows"></tbody>
    </table>
  </div>
</section>
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
