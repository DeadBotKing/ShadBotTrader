# فاز ۵۲ — فیلترهای Session و SL Minimum (از آنالیز بکتست)

**تاریخ:** 2026-08-25  
**وضعیت:** ✅ کامل — تست‌ها پاس  
**مبنا:** آنالیز 242 ترید (جولای–اوت ۲۰۲۶)

---

## ۱. یافته‌های آنالیز بکتست

| معیار | قبل از فیلتر | بعد از فیلتر |
|---|---|---|
| تعداد ترید | 242 | ~40–92 |
| Win Rate | 33.5% | **45–55%** |
| Net PnL | +0.91 | **+1.58–1.69** |

### ساعت‌های خوب UTC:
`2, 5, 6, 10, 14, 15, 16, 18` → WR=45.7%, net=+2.76

### ساعت‌های بد UTC:
`1, 3, 7, 9, 11, 19, 20` → WR<25%, ضررده

### SL Distance:
- SL < 3$ → WR=15%, 33 ترید ضررده
- SL ≥ 5$ → WR=40%+

---

## ۲. فیلترهای اضافه‌شده

### Gate 0: Session Filter
در `DualModelStrategy.evaluate()` — **اول از همه گیت‌ها** اجرا میشه
چون ارزون‌ترینه (inference مدل هنوز نشده).

```python
# قبل از پیش‌بینی مدل:
if self._allowed_hours is not None:
    bar_hour = context.timestamp.value.hour
    if bar_hour not in self._allowed_hours:
        return self._hold(context, f"session filter: hour {bar_hour:02d} UTC not in allowed hours")
```

### Gate 7: Min SL Distance
در `DualModelStrategy.evaluate()` — بعد از gate 6 (move fraction):

```python
if self._min_sl_distance > 0 and reference > 0:
    sl_distance_approx = risk * reference  # offset fraction → دلار
    if sl_distance_approx < self._min_sl_distance:
        return self._hold(context, f"predicted SL distance {sl_distance_approx:.2f} < min {self._min_sl_distance:.2f}")
```

**نکته:** `risk` = offset fraction (مثلاً 0.002174 = 0.2174%) است.
`sl_distance_approx = 0.002174 × 4116 = 8.95$`

---

## ۳. ثابت مفید: DEFAULT_GOOD_HOURS_UTC

```python
# در dual_model_strategy.py:
DEFAULT_GOOD_HOURS_UTC: FrozenSet[int] = frozenset({2, 5, 6, 10, 14, 15, 16, 18})
```

---

## ۴. فایل‌های تغییر یافته

### `dual_model_strategy.py`
- `__init__`: دو پارامتر جدید `allowed_hours_utc` و `min_sl_distance`
- `evaluate()`: دو گیت جدید (gate 0 و gate 7)
- `DEFAULT_GOOD_HOURS_UTC` constant

### `dual_model_backtest_service.py`
- `__init__`: دو پارامتر جدید
- `from_storage`: دو پارامتر جدید
- پاس دادن به `DualModelStrategy`

### `handlers.py` (GUI)
- دو فیلد جدید در `RUN_BACKTEST` و `RECORD_REPLAY`:
  - `session_filter`: select (0/1)
  - `min_sl_distance`: number (پیش‌فرض 0)
- summary log آپدیت شد

---

## ۵. نحوه استفاده در بکتست GUI

```
Session filter (hours UTC): 1   ← فیلتر ساعت
Min SL distance ($):        3   ← حداقل ۳ دلار
Confidence threshold:      75%  ← همیشه بوده
```

نتیجه انتظاری:
- ~40% ترید کمتر
- WR: 33.5% → ~50%+
- Net PnL بهتر با سرمایه کمتر در ریسک

---

## ۶. مقایسه سناریوها (از آنالیز بکتست واقعی)

| سناریو | تعداد | WR% | Net PnL |
|---|---|---|---|
| همه (base) | 242 | 33.5% | +0.91 |
| session_filter=1 | 92 | **45.7%** | **+2.76** |
| session+conf≥82% | 44 | **50.0%** | +1.58 |
| session+conf≥82%+sl≥3$ | 40 | **55.0%** | +1.69 |
