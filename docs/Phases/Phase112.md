# فاز ۱۱۲ — پیشنهاد: Branch Benchmark و مدل‌های مکمل کنار WaveNet

**وضعیت:** 🟡 پیشنهادی / بعد از فاز ۱۰۹ و ترجیحاً بعد از فاز ۱۱۰  
**نوع:** Model benchmark / ensemble research، بدون جایگزینی فوری WaveNet  
**اولویت:** بالا برای branchهای tabular، متوسط/بالا برای two-branch neural

---

## هدف

الان مدل اصلی `trend_signal` ما یک WaveNet/TCN-like classifier است. برای رسیدن به سیستم دقیق‌تر نباید فقط همان مدل را بزرگ‌تر کنیم. باید چند مدل با **inductive bias متفاوت** بسازیم و روی یک معیار مشترک مقایسه کنیم:

```text
WaveNet/TCN branch
+ Tabular Boosting branch
+ POS/NEG specialist branch
+ optional two-branch neural
```

این فاز فقط benchmark/branch اضافه می‌کند؛ تصمیم نهایی در فاز ۱۱۶ با range و meta-filter ترکیب می‌شود.

---

## 1) Branch اول: Tabular Boosters

### مدل‌ها

```text
gold_trend_signal_lgbm_5m
gold_trend_signal_catboost_5m
gold_trend_signal_xgboost_5m
```

### چرا اولویت بالا دارد؟

دیتای ما الان tabular/engineered-feature قوی دارد:

```text
~53k samples
179 engineered features
3-class SELL/HOLD/BUY label
```

برای چنین دیتایی، LightGBM/CatBoost/XGBoost در منابع Quant و tabular benchmarkها معمولاً baselineهای بسیار قوی هستند. این branch سریع‌تر از neural benchmarkها train می‌شود و اگر edge واقعی در featureها باشد، زودتر خودش را نشان می‌دهد.

### ورودی پیشنهادی

نباید کل tensor خام `(288,179)` را flatten کنیم. بهتر است از هر window خلاصهٔ causal بسازیم:

```text
last(feature)
mean/std/min/max over 1h, 4h, 12h, 24h
slope over 1h/4h/24h
feature change/delta
ATR-relative distances
session/time flags
```

### خروجی

```text
softmax probability: SELL/HOLD/BUY
```

یا برای POS/NEG:

```text
sigmoid: BUY vs NOT_BUY
sigmoid: SELL vs NOT_SELL
```

---

## 2) Branch دوم: Two-branch neural مدل الهام‌گرفته از ari99

repo `ari99/algorithmic_trading` ایدهٔ دو ورودی داشت:

```text
Returns sequence branch + engineered features branch
```

برای ما نسخهٔ تمیزتر:

```text
Input A: returns sequence, shape [window, 1]
  → causal Conv1D یا GRU/LSTM کوچک

Input B: selected engineered features
  → Dense + BatchNorm + Dropout

concat
→ Dense
→ output softmax 3-class یا sigmoid binary
```

مزیت:

```text
حرکت خام قیمت و featureهای مهندسی‌شده جدا پردازش می‌شوند.
```

این branch بعد از Tabular Boosters تست شود، چون پیاده‌سازی و training سنگین‌تر است.

---

## 3) Branch سوم: Time-series classifiers سبک

پس از branchهای بالا:

```text
MiniRocket / MultiRocket
LITE / LITEMV
InceptionTime
```

مزیت:

```text
چند scale/pattern زمانی را سریع‌تر از Transformerهای سنگین تست می‌کنند.
```

این‌ها برای `SELL/HOLD/BUY` classification مناسب‌اند، اما باید همان roll-forward/purge و calibration را رعایت کنند.

---

## 4) اصل مقایسه

همهٔ مدل‌ها باید با همان شرایط مقایسه شوند:

```text
same symbol/timeframe
same window/horizon/barrier
same train_ratio
same roll-forward/purge
same validation folds
same metric report
same threshold calibration
same backtest cost model
```

---

## CLI/GUI پیشنهادی

```text
--model-family wavenet|lgbm|catboost|xgboost|two_branch|minirocket|lite|inception
--window-summary off|basic|multi_scale
--branch-output multiclass|buy|sell
```

برای GUI:

```text
Train benchmark model
  Basic fields: symbol, dataset, model_family, label, window, horizon, barrier
  Advanced options: hyperparameters, feature summary, folds, timeouts
```

---

## فایل‌های پیشنهادی

```text
src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py
src/ShadBotTrader/infrastructure/ai/tabular_booster_trainer.py
src/ShadBotTrader/infrastructure/ai/two_branch_model.py
src/ShadBotTrader/infrastructure/ai/two_branch_trainer.py
scripts/run_model_benchmark.py
scripts/compare_model_branches.py
```

در ابتدا می‌توان `scripts/experiments/` ساخت، اما اگر artifact قرار است در production استفاده شود باید از همان ModelCatalogue/ModelRecord رسمی استفاده کند.

---

## معیار پذیرش

```text
- هیچ مدل جدیدی بدون roll-forward validation پذیرفته نشود.
- feature summary فقط از گذشتهٔ window ساخته شود.
- scaler/selector فقط روی train fit شود.
- خروجی probability قابل calibration باشد.
- گزارش واحد برای همهٔ branchها تولید شود.
- اگر branch از WaveNet بهتر نبود، وارد decision نهایی نشود.
```

---

## ارتباط با فاز ۱۱۶

این فاز مدل‌های branch را تولید و مقایسه می‌کند. فاز ۱۱۶ خروجی بهترین branchها را با مدل‌های range موجود ترکیب می‌کند:

```text
trend branch + booster branch + POS/NEG branch + range_1d + range_4h + meta-filter
```
