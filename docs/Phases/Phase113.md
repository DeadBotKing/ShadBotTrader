# فاز ۱۱۳ — random baseline، Monte Carlo و White Reality-style checks

**وضعیت:** ✅ پیاده‌سازی‌شده برای مسیر hybrid-head/range-aware
**نوع:** Backtest significance / anti-data-snooping
**اولویت:** اجباری قبل از اتصال live/paper

---

## مسئله

بعد از تست چند مدل، feature set، threshold grid و ترکیب range-aware، بهترین ردیف backtest ممکن است فقط حاصل شانس یا data-snooping باشد. بنابراین نتیجهٔ مثبت فاز ۱۲۵ نباید مستقیم وارد live شود؛ باید با random baseline روی همان پنجرهٔ ارزیابی و همان منطق TP/SL مقایسه شود.

---

## پیاده‌سازی فعلی

فایل اجرایی:

```text
scripts/backtest_significance_check.py
```

GUI/Dashboard:

```text
Check hybrid significance
```

Command kind:

```text
check_hybrid_significance
```

خروجی‌ها:

```text
run_logs/significance_checks/latest.json
run_logs/significance_checks/latest.csv
```

---

## قاعدهٔ علی/معاملاتی

اسکریپت هیچ trade rule جدیدی اضافه نمی‌کند. منطق اصلی از فاز ۱۲۵ reuse می‌شود:

```text
hybrid head probabilities
+ selected BUY/SELL thresholds
+ range_4h / range_1d room filters
+ range TP/SL bracket
+ same spread/slippage/same-bar policy
+ same chronological eval slice
```

برای random baseline:

```text
- فقط روی همان eval slice انتخاب تصادفی انجام می‌شود.
- BUY و SELL candidateها فقط از بارهایی می‌آیند که با همان range filter و همان bracket قابل اجرا باشند.
- تعداد BUY و SELL دقیقاً با مدل مشاهده‌شده یکی می‌شود.
- روی یک bar هم‌زمان BUY و SELL تصادفی انتخاب نمی‌شود.
- PnL هر trade با همان تابع simulate_trade فاز ۱۲۵ حساب می‌شود.
```

---

## آمار تولیدی

برای random baseline اصلی:

```text
observed.total_pnl
random_baseline.mean
random_baseline.p95
random_baseline.p99
random_baseline.maximum
random_baseline.p_value
```

تعریف p-value:

```text
p_value = (1 + count(random_total_pnl >= observed_total_pnl)) / (trials + 1)
```

همچنین برای اصلاح تقریبی چندآزمونی:

```text
white_reality_style.p_value
```

در حالت White-style، اسکریپت ردیف‌های معتبر grid فاز ۱۲۵ را از فایل زیر می‌خواند:

```text
run_logs/hybrid_head_backtest/latest.json
```

و در هر trial بیشینهٔ PnL تصادفی بین candidateهای معتبر را با PnL مدل مقایسه می‌کند. این دقیقاً White Reality Check آکادمیک کامل نیست، اما یک کنترل عملی برای data-snooping روی همان threshold grid است.

---

## دستور پیشنهادی بعد از فاز ۱۲۵ ذخیره‌شده

با فرض اینکه فاز ۱۲۵ threshold زیر را در رکورد مدل ذخیره کرده باشد:

```text
buy_threshold  = 0.80
sell_threshold = 0.65
min_margin     = 0.05
```

دستور:

```powershell
python -u scripts/backtest_significance_check.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --trials 1000 `
  --seed 42 `
  --white-check 1 `
  --candidate-rows-path run_logs/hybrid_head_backtest/latest.json `
  --storage-root datasets
```

اگر بخواهیم threshold را صریح بدهیم و از رکورد مدل نخوانیم:

```powershell
python -u scripts/backtest_significance_check.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --eval-frac 0.30 `
  --buy-threshold 0.80 `
  --sell-threshold 0.65 `
  --min-margin 0.05 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --trials 1000 `
  --seed 42 `
  --white-check 1 `
  --candidate-rows-path run_logs/hybrid_head_backtest/latest.json `
  --storage-root datasets
```

---

## معیار پذیرش

```text
✅ هیچ trade rule تغییر نکرد.
✅ random baseline با همان هزینه‌ها، range filters و TP/SL اجرا می‌شود.
✅ تعداد BUY/SELL random با مدل match می‌شود.
✅ Monte Carlo p-value گزارش می‌شود.
✅ White-style max correction اختیاری پیاده‌سازی شده است.
✅ خروجی JSON/CSV قابل audit تولید می‌شود.
```

---

## تصمیم بعدی

اگر:

```text
random_baseline.p_value <= 0.05
white_reality_style.p_value <= 0.10  # ترجیحاً <= 0.05
```

آنگاه مسیر hybrid-head/range-aware ارزش رفتن به integration/paper را دارد. اگر p-valueها بالا باشند، نتیجهٔ فاز ۱۲۵ را باید «امیدوارکننده ولی غیرمعنادار» تلقی کنیم و قبل از live وارد بهینه‌سازی/اعتبارسنجی بیشتر شویم.

---

## نتیجهٔ اجرای کاربر — 2026-09-09

فاز ۱۱۳ روی threshold ذخیره‌شدهٔ فاز ۱۲۵ اجرا شد:

```text
threshold_source: model_record:gold_hybrid_lightgbm_head_5m:v1
buy_threshold   : 0.80
sell_threshold  : 0.65
min_margin      : 0.05
matrix_rows     : 8000
eval_rows       : 2400
trials          : 1000
seed            : 42
white_check     : 1
```

Observed:

```text
trades          : 325
buy/sell        : 160 / 165
win_rate        : 51.6923%
label_precision : 65.8462%
total_pnl       : +291.154987683185
avg_pnl         : +0.8958615005636462
profit_factor   : 1.2471739846573604
max_drawdown    : 347.044035279524
```

Random baseline:

```text
buy_candidates  : 960
sell_candidates : 1175
mean            : -944.2369557544658
p95             : -665.0864972670641
p99             : -529.5757005996354
maximum         : -317.02241025066814
positive_prob   : 0.0
p_value         : 0.000999000999000999
```

White Reality-style max check:

```text
candidate_count : 23
mean_max        : -346.06975128145194
p95             : -193.67326141904985
p99             : -128.05536537052174
maximum         : -28.658925889975762
positive_prob   : 0.0
p_value         : 0.000999000999000999
```

نتیجه:

```text
Phase113 برای همین holdout و همین rule/cost assumptions با قدرت پاس شد.
Observed PnL از بهترین random baseline حدود +608.18 دلار بهتر است:
+291.154987683185 - (-317.02241025066814) = +608.1773979338531
```

محدودیت: این نتیجه هنوز walk-forward/out-of-time مستقل نیست و برای live واقعی باید ابتدا Phase116 integration و بعد Phase115 live decision audit/paper validation انجام شود.
