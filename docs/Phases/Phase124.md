# فاز ۱۲۴ — Train Hybrid XGBoost/LightGBM Head

**وضعیت:** ✅ زیرساخت CLI پیاده‌سازی شد  
**نوع:** Final meta-model head روی ماتریس فاز ۱۲۳  
**تاریخ:** 2026-09-08

---

## هدف

فاز ۱۲۳ فقط ماتریس می‌سازد. فاز ۱۲۴ روی همان ماتریس یک مدل نهایی train می‌کند تا یاد بگیرد خروجی مدل‌های قبلی را چطور ترکیب کند:

```text
BUY/SELL specialist probabilities
+ multiclass booster probabilities
+ optional WaveNet probabilities
+ range_1d room
+ range_4h room
→ final SELL/HOLD/BUY
```

در اجراهای بعدی، `HOLD` در خروجی نهایی به معنی `NO_TRADE` است.

---

## فایل جدید

```text
scripts/train_hybrid_xgboost_head.py
```

---

## ورودی

پیش‌فرض:

```text
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
```

یا دستی:

```text
--matrix-path path/to/matrix.parquet
```

---

## مدل‌ها

```text
--booster auto|lightgbm|xgboost|catboost
```

پیش‌فرض `auto` است و از اولین backend نصب‌شده استفاده می‌کند.

---

## Feature selection اولیه

برای جلوگیری از وابستگی زیاد به price level، پیش‌فرض این است:

```text
--drop-price-levels 1
```

یعنی ستون‌های زیر از training head حذف می‌شوند:

```text
close
*_price
```

ولی ستون‌های room/pct/width/probability حفظ می‌شوند.

---

## Split

چون ماتریس معمولاً از `scope=holdout` ساخته می‌شود، فاز ۱۲۴ داخل همان ماتریس یک split زمانی انجام می‌دهد:

```text
first 70% → train meta-head
last 30%  → validation
```

پارامتر:

```text
--train-frac 0.70
```

---

## خروجی

```text
datasets/models/gold_hybrid_lightgbm_head_5m/vN.bin
datasets/models/gold_hybrid_lightgbm_head_5m/vN.json
datasets/models/gold_hybrid_lightgbm_head_5m/vN_training.json
run_logs/hybrid_xgboost_head/latest.json
```

---

## دستور پیشنهادی

```powershell
python -u scripts/train_hybrid_xgboost_head.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --booster auto `
  --train-frac 0.70 `
  --drop-price-levels 1 `
  --class-weight auto `
  --n-estimators 500 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --storage-root datasets
```

---

## معیار پذیرش

مدل نهایی فقط وقتی قابل ادامه است که:

```text
val_action_collapse = 0
val_action_min_f1_supported > booster-only baseline
SELL و BUY هر دو F1 غیرصفر داشته باشند
HOLD/NO_TRADE رفتار معقول داشته باشد
```

اگر head نهایی فقط یک کلاس را بزند، رد می‌شود.

---

## گام بعد

اگر فاز ۱۲۴ بهتر از booster-only شد:

```text
Phase125 — Calibrate Hybrid Head Thresholds / Backtest with range TP/SL
```

و بعد:

```text
Phase113 significance checks
Phase116 live range-aware decision integration
```
