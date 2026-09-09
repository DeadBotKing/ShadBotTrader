# فاز ۱۱۶ — Hybrid Range-Aware Decision Engine Integration

**وضعیت:** ✅ نسخهٔ اول پیاده‌سازی شد
**نوع:** Runtime decision integration / live-shadow audit path
**اولویت:** بعد از Phase125 + Phase113، قبل از Phase115 live decision audit

---

## هدف

نتیجهٔ مثبت فاز ۱۲۵ و تأیید آماری فاز ۱۱۳ را از حالت research script به مسیر تصمیم‌گیری استاندارد پروژه وصل کنیم؛ بدون redesign و بدون دور زدن معماری موجود.

مسیر جدید:

```text
hybrid head probabilities
+ saved Phase125 thresholds
+ range_1d daily envelope
+ range_4h TP/SL bracket
→ HybridRangeAwareStrategy
→ PositionAwareDecisionEngine
→ PolicyRiskGate
→ DefaultIntentFactory
→ audit JSON/CSV
```

این فاز هنوز order واقعی MT5 ارسال نمی‌کند. خروجی آن `TradingIntent` و لاگ کامل TRADE/NO_TRADE است تا قبل از live واقعی، Phase115 audit/paper اجرا شود.

---

## ورودی معتبر فعلی

Threshold ذخیره‌شده در مدل:

```text
model_id        : gold_hybrid_lightgbm_head_5m
model_version   : 1
buy_threshold   : 0.80
sell_threshold  : 0.65
min_margin      : 0.05
```

گیت‌های range-aware مطابق Phase125/Phase113:

```text
min_4h_room      = 2
min_1d_room      = 5
min_tp_distance  = 2
min_sl_distance  = 2
spread_mode      = pct
spread_value     = 0.06
slippage         = 0
```

---

## فایل‌های پیاده‌سازی‌شده

```text
src/ShadBotTrader/domain/ai/prediction_target.py
  + HybridSignalClass
  + HybridHeadForecast

src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py
  + HybridHeadPredictor
  + HybridHeadPayload

src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py
  + HybridRangeAwareConfig
  + HybridRangeAwareStrategy

scripts/audit_hybrid_range_aware_decisions.py
  + Phase116 integration audit CLI

src/ShadBotTrader/presentation/commands/commands.py
  + audit_hybrid_range_aware_decisions

src/ShadBotTrader/presentation/commands/handlers.py
  + GUI descriptor
  + handler method
```

Tests:

```text
tests/unit/ai/test_prediction_target.py
tests/unit/ai/test_hybrid_head_predictor.py
tests/unit/strategy/test_hybrid_range_aware_strategy.py
tests/unit/presentation/test_architecture_knobs_gui.py
tests/integration/test_gui_coverage.py
```

---

## قانون تصمیم نسخهٔ اول

### Hybrid probabilities

کلاس‌ها دقیقاً به ترتیب زیر هستند:

```text
0 = sell
1 = hold
2 = buy
```

### BUY

```text
BUY اگر:
  buy_probability >= buy_threshold
  buy_probability - sell_probability >= min_margin
  buy_probability - hold_probability >= min_margin
  range_4h.predicted_high - room_reference >= min_4h_room
  range_1d.predicted_high - room_reference >= min_1d_room
  TP = min(range_4h.predicted_high, range_1d.predicted_high)
  SL = range_4h.predicted_low
  TP > entry
  SL < entry
  TP distance >= min_tp_distance
  SL distance >= min_sl_distance
```

### SELL

```text
SELL اگر:
  sell_probability >= sell_threshold
  sell_probability - buy_probability >= min_margin
  sell_probability - hold_probability >= min_margin
  room_reference - range_4h.predicted_low >= min_4h_room
  room_reference - range_1d.predicted_low >= min_1d_room
  TP = max(range_4h.predicted_low, range_1d.predicted_low)
  SL = range_4h.predicted_high
  TP < entry
  SL > entry
  TP distance >= min_tp_distance
  SL distance >= min_sl_distance
```

در غیر این صورت:

```text
HOLD / NO_TRADE با reason دقیق
```

---

## نکتهٔ entry و room reference

برای سازگاری با Phase125:

```text
room_reference_price = close همان ردیف matrix
raw_entry_price      = next 5M open mid-price
entry BUY            = raw_entry + half_spread + slippage
entry SELL           = raw_entry - half_spread - slippage
```

در live/paper بعدی، `raw_entry_price` می‌تواند از quote فعلی broker/mid بیاید، ولی هنوز باید همین explainability keys ثبت شوند.

---

## Audit CLI

دستور پیشنهادی روی ماشین کاربر:

```powershell
python -u scripts/audit_hybrid_range_aware_decisions.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-windows 0 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --capital 10000 `
  --base-quantity 1 `
  --storage-root datasets
```

چون threshold در رکورد مدل ذخیره شده، پارامترهای زیر لازم نیست مگر برای override دستی:

```text
--buy-threshold
--sell-threshold
--min-margin
```

خروجی‌ها:

```text
run_logs/hybrid_decision_audit/latest.json
run_logs/hybrid_decision_audit/latest.csv
```

---

## خروجی مورد انتظار

اگر matrix/model/threshold همان Phase125 باشد، انتظار داریم audit مسیر runtime تقریباً همان تعداد intent تولید کند:

```text
trade_intents ≈ 325
buy_intents   ≈ 160
sell_intents  ≈ 165
coverage      ≈ 13.54%
label_precision ≈ 65.85%
```

اگر اختلاف بزرگ بود، integration با research backtest هم‌خوان نیست و قبل از Phase115 باید debug شود.

---

## محدودیت فعلی

```text
- این فاز order واقعی نمی‌فرستد.
- هنوز live quote / MT5 order placement به hybrid path وصل نشده است.
- هنوز Phase115 live decision audit/paper shadow انجام نشده است.
- هنوز walk-forward/out-of-time مستقل انجام نشده است.
```

---

## تصمیم بعدی

بعد از اجرای موفق `audit_hybrid_range_aware_decisions.py` و تأیید اینکه تعداد و دلایل با Phase125 هم‌خوان است، گام بعدی:

```text
Phase115 — live decision audit / paper shadow
```

در Phase115 باید هر tick زنده بدون ارسال order واقعی log شود:

```text
timestamp
symbol/timeframe
raw_entry_price / spread
hybrid sell/hold/buy probabilities
thresholds
range_1d high/low
range_4h high/low
TP/SL
TRADE یا NO_TRADE
reason
```

---

## نتیجهٔ اجرای audit کاربر — 2026-09-09

کاربر دستور audit فاز ۱۱۶ را اجرا کرد. خروجی:

```text
model_version  : 1
matrix_rows    : 8000
eval_rows      : 2400
threshold_src  : model_record:gold_hybrid_lightgbm_head_5m:v1
buy_threshold  : 0.80
sell_threshold : 0.65
min_margin     : 0.05
```

Summary:

```text
rows           : 2400
trade_intents  : 325
no_trade       : 2075
buy_intents    : 160
sell_intents   : 165
label_correct  : 214
label_precision: 0.6584615384615384
coverage       : 0.13541666666666666
```

Sanity-check با Phase125:

```text
Phase125 best trades     : 325
Phase116 runtime intents : 325
Phase125 buy/sell        : 160 / 165
Phase116 buy/sell        : 160 / 165
Phase125 precision       : 0.6584615384615384
Phase116 precision       : 0.6584615384615384
```

نتیجه:

```text
PASS — runtime decision integration با research backtest هم‌خوان است.
```

گام بعدی:

```text
Phase115 — live decision audit / paper shadow
```
