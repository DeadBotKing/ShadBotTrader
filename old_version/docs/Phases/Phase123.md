# فاز ۱۲۳ — Hybrid XGBoost Matrix: WaveNet + Range + Booster outputs

**وضعیت:** ✅ زیرساخت ساخت ماتریس پیاده‌سازی شد  
**نوع:** Meta-feature matrix برای XGBoost/LightGBM نهایی  
**تاریخ:** 2026-09-08

---

## ایدهٔ اصلی

در pilotها مشخص شد WaveNet خام روی 179 feature برای `trend_signal` خروجی خوبی نمی‌دهد و collapse می‌کند. بنابراین قرار نیست XGBoost به‌صورت differentiable داخل WaveNet کاشته شود؛ چون XGBoost/LightGBM درختی است و gradient از آن عبور نمی‌کند.

اما ایدهٔ درست و عملیاتی اپراتور این است:

```text
خروجی مدل‌های موجود → یک ماتریس جدید → XGBoost/LightGBM نهایی
```

یعنی مدل نهایی XGBoost به جای اینکه فقط raw feature ببیند، این‌ها را می‌بیند:

```text
BUY specialist probability
SELL specialist probability
multiclass booster probabilities
optional WaveNet probabilities
range_1d forecast room
range_4h forecast room
true trend_signal label
```

---

## چرا این بهتر از WaveNet خام است؟

WaveNet خام مجبور بود از 179 feature و 288 کندل خودش جهت را کشف کند. اما ماتریس فاز ۱۲۳ وظیفه را ساده‌تر می‌کند:

```text
- boosterها الگوی tabular را استخراج می‌کنند؛
- WaveNet اگر سالم باشد فقط به عنوان feature probabilistic وارد می‌شود؛
- range_1d می‌گوید فردا فضای حرکت بالا/پایین هست یا نه؛
- range_4h می‌گوید برای TP/SL چهار ساعت آینده جا داریم یا نه؛
- XGBoost نهایی یاد می‌گیرد کدام ترکیب واقعاً قابل اعتماد است.
```

---

## فایل جدید

```text
scripts/build_hybrid_xgboost_matrix.py
```

---

## GUI جدید

Command:

```text
Build hybrid XGBoost matrix
```

Action:

```text
build_hybrid_xgboost_matrix
```

---

## ستون‌های خروجی

ستون‌های پایه:

```text
timestamp
source_index
sample_end
label
close
```

خروجی specialistها:

```text
buy_specialist_prob
sell_specialist_prob
specialist_buy_minus_sell
specialist_sell_minus_buy
specialist_conflict
specialist_max_prob
```

خروجی multiclass booster:

```text
booster_sell_prob
booster_hold_prob
booster_buy_prob
booster_action_margin
booster_entropy
```

خروجی WaveNet، اگر موجود و compatible باشد:

```text
wavenet_sell_prob
wavenet_hold_prob
wavenet_buy_prob
wavenet_action_margin
wavenet_entropy
```

خروجی مدل‌های range:

```text
range_1d_available
range_1d_high_price
range_1d_low_price
range_1d_up_room
range_1d_down_room
range_1d_up_room_pct
range_1d_down_room_pct
range_1d_width
range_1d_width_pct

range_4h_available
range_4h_high_price
range_4h_low_price
range_4h_up_room
range_4h_down_room
range_4h_up_room_pct
range_4h_down_room_pct
range_4h_width
range_4h_width_pct
```

---

## نکتهٔ علیت / leakage

برای range features، فقط آخرین کندل بسته‌شدهٔ 1D یا 4H قبل از timestamp سیگنال استفاده می‌شود:

```text
latest range candle where range_open_time + range_delta <= signal_time
```

بنابراین کندل 4H/1D که هنوز بسته نشده وارد ماتریس نمی‌شود.

---

## خروجی فایل

```text
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_v1.parquet
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
run_logs/hybrid_xgboost_matrix/latest.json
```

---

## دستور پیشنهادی

```powershell
python -u scripts/build_hybrid_xgboost_matrix.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --scope holdout `
  --max-windows 8000 `
  --summary-mode basic `
  --booster lightgbm `
  --include-specialists 1 `
  --include-multiclass-booster 1 `
  --include-wavenet 1 `
  --require-wavenet 0 `
  --include-range 1 `
  --require-range 1 `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --storage-root datasets
```

---

## پیش‌نیازها

برای booster artifacts:

```text
gold_buy_lightgbm_basic_5m
gold_sell_lightgbm_basic_5m
gold_trend_signal_lightgbm_basic_5m
```

برای range features:

```text
gold_range_1d
gold_range_4h
```

اگر مدل range در مسیر/نام دیگری ذخیره شده، باید `--range-1d-model-id` یا `--range-4h-model-id` را عوض کرد.

---

## گام بعد

فاز بعدی باید از این ماتریس، یک head نهایی XGBoost/LightGBM بسازد:

```text
Phase124 — Train Hybrid XGBoost Head
```

هدف آن head:

```text
BUY / SELL / NO_TRADE
```

و معیار نهایی باید precision-aware و profit-aware باشد، نه صرفاً accuracy.
