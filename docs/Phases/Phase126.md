# Phase126 — Chronological Hybrid Validation

**وضعیت:** Phase126A پیاده‌سازی شد
**نوع:** Chronological single-position replay / robustness validation
**هدف:** تبدیل تست مستقلِ هر سیگنال به replay واقعی‌تر حساب که کندل‌به‌کندل فقط یک پوزیشن هم‌زمان دارد.

---

## چرا لازم شد؟

Full streamed diagnostic قبلی روی کل تاریخ 5M با rule ثابت Phase125 شکست خورد:

```text
rows            : 52832
trades          : 13757
coverage        : 26.0391%
total_pnl       : -43309.811277104236
profit_factor   : 0.6215092452818565
max_drawdown    : 45887.011698256094
```

اما آن بک‌تست هنوز هر سیگنال را مثل یک trade مستقل حساب می‌کرد. در حساب واقعی، وقتی پوزیشن باز است نباید روی کندل‌های بعدی پوزیشن جدید باز شود. بنابراین قبل از walk-forward، باید نسخهٔ chronological ساخته شود.

---

## Phase126A — پیاده‌سازی‌شده

فایل جدید:

```text
scripts/replay_hybrid_chronological_backtest.py
```

GUI command جدید:

```text
Chronological hybrid replay
```

خروجی‌ها:

```text
run_logs/hybrid_chronological_backtest/latest.html
run_logs/hybrid_chronological_backtest/latest.json
run_logs/hybrid_chronological_backtest/latest.csv
```

---

## قانون replay

```text
for each signal row in chronological order:
  if a previous trade is still open:
      skip row as skipped_while_open
  else:
      score hybrid head
      apply saved Phase125 thresholds
      apply 1D/4H range room filters
      build TP/SL bracket
      simulate forward up to max_hold_bars
      set open_until_index = trade.exit_index
```

یعنی فقط یک پوزیشن هم‌زمان مجاز است:

```text
max concurrent positions = 1
```

---

## Threshold و rule فعلی

از رکورد مدل خوانده می‌شود:

```text
model_id       : gold_hybrid_lightgbm_head_5m
threshold_src  : model_record:gold_hybrid_lightgbm_head_5m:v1
buy_threshold  : 0.80
sell_threshold : 0.65
min_margin     : 0.05
```

TP/SL همان Phase125:

```text
BUY:
  TP = min(range_4h_high, range_1d_high)
  SL = range_4h_low

SELL:
  TP = max(range_4h_low, range_1d_low)
  SL = range_4h_high
```

---

## Memory-safe full mode

برای جلوگیری از پر شدن RAM:

```text
--source-mode stream
--stream-scope all
--stream-chunk-size 500
--stream-wavenet neutral
```

در این حالت matrix عظیم full-history ساخته نمی‌شود؛ feature rows در chunk ساخته و همان‌جا score/backtest می‌شوند.

---

## دستور پیشنهادی کاربر

```powershell
python -u scripts/replay_hybrid_chronological_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 500 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

---

## JSON مهم برای بررسی

بعد از اجرا باید این فایل بررسی شود:

```text
run_logs\hybrid_chronological_backtest\latest.json
```

فیلدهای مهم:

```text
summary.trades
summary.total_pnl
summary.profit_factor
summary.max_drawdown
summary.coverage
chronological.skipped_while_open
account.final_balance
account.would_breach_zero
monthly
```

---

## HTML replay

```text
run_logs\hybrid_chronological_backtest\latest.html
```

نمایش:

```text
slider کندل‌به‌کندل
دایره ورود
مربع خروج
خط زرد entry
خط سبز TP
خط قرمز SL
balance after closed trades
active trade details
```

---

## محدودیت

این هنوز walk-forward training نیست. مدل همچنان همان head نسخهٔ 1 است. Phase126A فقط execution chronology را واقعی‌تر می‌کند.

اگر Phase126A هنوز روی کل تاریخ شکست بخورد، گام بعدی Phase126B است:

```text
walk-forward:
  train on past
  calibrate on past validation
  test on next out-of-time block
```

هرگز نباید برای اعتبارسنجی، مدل را روی کل دیتاست train و بعد روی همان کل دیتاست backtest کرد؛ آن in-sample leakage است.
---

## GUI/operator execution requirement

این فاز قبلاً GUI command دارد و باید حفظ شود:

```text
CommandKind.REPLAY_HYBRID_CHRONOLOGICAL_BACKTEST
Dashboard label: Chronological hybrid replay
Handler: runs scripts/replay_hybrid_chronological_backtest.py
```

قاعده از اینجا به بعد: هر replay/backtest/train/audit که اپراتور باید اجرا کند، باید در Dashboard command داشته باشد و تست‌های GUI هم به‌روزرسانی شوند. CLI تنها کافی نیست.

---

## Full chronological execution result — 2026-09-10

کاربر Phase126A را روی کل 5M با `source_mode=stream`, `stream_scope=all`, `stream_wavenet=neutral`, `initial_capital=100`, `units=0.1` اجرا کرد.

```text
source_rows     : 52832
evaluated_rows  : 52832
threshold       : buy=0.80 sell=0.65 margin=0.05
trades          : 1693
buy/sell        : 1118 / 575
wins/losses     : 512 / 1181
win_rate        : 30.2422%
label_precision : 47.6669%
total_pnl       : -4590.797210656048
profit_factor   : 0.5787103197097719
max_drawdown    : 4590.797210656047
coverage        : 3.2045%
```

Chronological counters:

```text
no_trade_probability: 21949
skipped_while_open  : 17299
invalid_range       : 5357
invalid_bracket     : 6534
```

Account view:

```text
initial_capital   : 100
units             : 0.1
final_balance     : -359.0797210656049
max_drawdown_cash : 459.07972106560476
would_breach_zero : true
```

نتیجه:

```text
Base hybrid fixed-threshold حتی با single-position chronology روی کل تاریخ robust نیست.
این نتیجه اجرای Phase127/128/132/133 را ضروری می‌کند و live/paper جدی همچنان ممنوع است.
```
