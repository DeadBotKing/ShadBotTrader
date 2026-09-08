# فاز ۱۰۹ — threshold calibration و heatmap برای trend_signal

تاریخ: 2026-09-07
وضعیت: ✅ ابزار کالیبراسیون، GUI، ذخیره threshold و تست پیاده‌سازی شد. اجرای عملی نیازمند مدل train‌شدهٔ `trend_signal` با window سازگار است.

---

## 1) هدف

بعد از Phase108، مدل `trend_signal` خروجی احتمالاتی برای سه کلاس دارد:

```text
SELL / HOLD / BUY
```

اما تصمیم معاملاتی نباید با threshold حدسی گرفته شود. Phase109 ابزار می‌دهد تا thresholdهای BUY و SELL روی validation/holdout کالیبره شوند.

---

## 2) فایل جدید

```text
scripts/calibrate_trend_signal_thresholds.py
```

این script:

```text
- مدل ذخیره‌شدهٔ trend_signal را load می‌کند.
- feature matrix و labelهای trend_signal را با همان window/horizon می‌سازد.
- روی scope انتخاب‌شده prediction می‌گیرد.
- grid threshold BUY × SELL را اسکن می‌کند.
- برای هر ترکیب precision/recall/F1/coverage/trade counts می‌نویسد.
- CSV/HTML/JSON heatmap تولید می‌کند.
- در صورت درخواست، threshold منتخب را داخل ModelRecord ذخیره می‌کند.
```

---

## 3) ورودی‌های CLI

```text
--symbol XAUUSD
--timeframe 5M
--model-id gold_trend_signal_5m optional
--model-version 0       # 0 = latest
--window 288
--label-horizon 288
--atr-mult 0.5
--train-ratio 80
--scope auto|holdout|last-fold|all
--threshold-min 0.35
--threshold-max 0.95
--threshold-step 0.05
--min-margin 0
--min-trades 50
--precision-floor 0
--max-windows 8000
--save-record 1|0
```

---

## 4) Calibration scope

```text
auto:
  اگر train_ratio < 100 باشد → holdout
  وگرنه → last-fold

holdout:
  فقط sampleهایی که بعد از train_ratio cutoff هستند.

last-fold:
  validation slice آخر همان هندسهٔ roll-forward.

all:
  همهٔ labelled windows.
```

برای اجرای اپراتور که train_ratio=80 استفاده شد، scope پیش‌فرض `auto` یعنی `holdout` خواهد بود.

---

## 5) decision rule

برای هر sample:

```text
BUY اگر:
  buy_prob >= buy_threshold
  buy_prob - sell_prob >= min_margin
  buy_prob - hold_prob >= min_margin

SELL اگر:
  sell_prob >= sell_threshold
  sell_prob - buy_prob >= min_margin
  sell_prob - hold_prob >= min_margin

در غیر این صورت: NO_TRADE
```

اگر هر دو شرط BUY و SELL همزمان پاس شود، sample ambiguous/no-trade حساب می‌شود.

---

## 6) metricهای grid

برای هر threshold pair:

```text
samples
trades
buy_trades
sell_trades
correct
buy_correct
sell_correct
false_positive
ambiguous
no_trade
action_precision
buy_precision
sell_precision
action_recall
buy_recall
sell_recall
action_f1
coverage
score
```

فعلاً `score = action_f1` است، با constraintهای:

```text
trades >= min_trades
action_precision >= precision_floor
```

اگر constraintها پاس نشوند، score=-1 و برای انتخاب best جریمه می‌شود.

---

## 7) خروجی‌ها

در:

```text
run_logs/trend_signal_thresholds/
```

فایل‌های timestamped و latest ساخته می‌شود:

```text
{model_id}_v{version}_{scope}_{timestamp}.csv
{model_id}_v{version}_{scope}_{timestamp}.html
{model_id}_v{version}_{scope}_{timestamp}.json
latest.csv
latest.html
latest.json
```

HTML heatmap سلول‌ها را بر اساس `action_f1` رنگ می‌کند.

---

## 8) ذخیره در ModelRecord

به `ModelRecord` فیلد جدید اضافه شد:

```python
decision_thresholds: Dict[str, Any]
```

اگر `--save-record 1` باشد، threshold منتخب در `v*_training.json` ذخیره می‌شود:

```json
"decision_thresholds": {
  "buy_prob": 0.7,
  "sell_prob": 0.65,
  "min_margin": 0.0,
  "selected_by": "phase109_label_grid_action_f1",
  "action_precision": 0.0,
  "action_recall": 0.0,
  "action_f1": 0.0,
  "coverage": 0.0,
  "trades": 0,
  "samples": 0,
  "metadata": {...}
}
```

---

## 9) GUI

Command جدید:

```text
Calibrate trend-signal thresholds
CommandKind.CALIBRATE_TREND_SIGNAL = "calibrate_trend_signal"
```

فیلدها:

```text
symbol
dataset
model_id
window
label_horizon
atr_mult
train_ratio
scope
threshold_min
threshold_max
threshold_step
min_margin
min_trades
precision_floor
max_windows
save_record
timeout_minutes
```

از live log موجود `_run_script` استفاده می‌کند.

---

## 10) فایل‌های تغییرکرده/جدید

### جدید

```text
scripts/calibrate_trend_signal_thresholds.py
tests/unit/ai/test_threshold_calibration.py
tests/integration/test_trend_signal_calibration_gui.py
docs/Report/PHASE109_TREND_SIGNAL_THRESHOLD_CALIBRATION_REPORT.md
```

### تغییرکرده

```text
src/ShadBotTrader/infrastructure/ai/model_catalogue.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
docs/Phases/Phase109.md
docs/WORKLOG.md
docs/CURRENT_STATE.md
docs/SESSION_HANDOFF_2026-09-07.md
```

---

## 11) تست‌ها

```text
tests/unit/ai/test_threshold_calibration.py
  - decision rule threshold/margin
  - grid calibration best selection
  - ModelRecord decision_thresholds roundtrip

tests/integration/test_trend_signal_calibration_gui.py
  - descriptor fields
  - GUI args passed to script
```

Targeted:

```text
ruff/black روی فایل‌های تغییرکرده: OK
pytest threshold calibration + GUI: OK
```

---

## 12) اجرای پیشنهادی بعد از train مدل

بعد از اینکه اپراتور training `gold_trend_signal_5m` با window=288 و class weights را کامل کرد:

```powershell
python -u scripts/calibrate_trend_signal_thresholds.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --scope auto `
  --threshold-min 0.35 `
  --threshold-max 0.95 `
  --threshold-step 0.05 `
  --min-margin 0 `
  --min-trades 50 `
  --precision-floor 0 `
  --max-windows 8000 `
  --save-record 1 `
  --storage-root datasets
```

یا از GUI:

```text
Calibrate trend-signal thresholds
```

---

## 13) محدودیت مهم

Phase109 فعلاً label/probability calibration است، نه full PnL backtest با TP/SL. برای full profit-aware calibration باید بعداً این thresholdها به triple backtest وصل شوند. این بخش در Phase110/111/113 roadmap ادامه پیدا می‌کند.
