# فاز ۱۱۳ — پیشنهاد: random baseline، Monte Carlo و White Reality-style checks

**وضعیت:** 🟡 پیشنهادی  
**نوع:** Backtest significance / anti-data-snooping  
**اولویت:** بالا بعد از threshold calibration

---

## مسئله

اگر چندین مدل، feature subset و threshold تست کنیم، بهترین نتیجه ممکن است صرفاً شانسی باشد. باید بررسی کنیم نتیجهٔ backtest واقعاً از random بهتر است یا نه.

---

## الهام

از repo ari99:

```text
Random portfolios
Monte Carlo detrended returns
White's Reality Check
```

---

## روش پیشنهادی برای ShadBotTrader

### 1) Random signal baseline

با همان تعداد trade و همان session distribution، سیگنال‌های random بساز:

```text
trade_count_model = N
randomly choose N entry times from eligible bars
same TP/SL/spread/slippage rules
```

### 2) Permutation test

```text
entries ثابت، returns یا labels shuffle/permutation
```

### 3) Monte Carlo p-value

```text
p_value = P(random_return >= model_return)
```

### 4) White Reality-style correction

برای بهترین مدل/threshold از بین candidateهای زیاد:

```text
آیا بهترین candidate بعد از multiple-testing correction هنوز معنادار است؟
```

---

## خروجی

```text
run_logs/significance_checks/{run_id}.json
run_logs/significance_checks/{run_id}.csv
docs/Report/SIGNIFICANCE_{date}.md optional
```

Metrics:

```text
model_return
random_mean
random_p95
random_p99
p_value
num_random_trials
```

---

## فایل پیشنهادی

```text
scripts/backtest_significance_check.py
src/ShadBotTrader/application/services/significance_service.py
```

---

## معیار پذیرش

```text
- هیچ trade rule تغییر نکند؛ فقط مقایسه اضافه شود.
- random baseline با همان هزینه‌ها و spread اجرا شود.
- نتیجه اگر معنی‌دار نبود، صریح گزارش شود.
```
