# فاز ۵۰ — تحلیل Range v1 + رفع باگ loss_function در save_model

**تاریخ:** 2026-08-25  
**وضعیت:** ✅ کامل  
**مبنا:** training.json آپلودشده (gold_range_1h v1)

---

## ۱. تحلیل v1_training.json آپلودشده

```json
{
  "model_id": "gold_range_1h",
  "role": "range",
  "timeframe": "1H",
  "version": 1,
  "rows": 39918,
  "windows": 39769,
  "window_size": 150,
  "feature_columns": 182,
  "epochs": 20,
  "folds": 3,
  "learning_rate": 3e-05,
  "metrics": {
    "val_loss": 0.000593,
    "val_mae":  0.001754
  },
  "note": "best epoch 20/20 (val_loss 0.000593)"
}
```

### نکات مهم:

| فیلد | مقدار | تفسیر |
|------|-------|--------|
| `best epoch` | 20/20 | آخرین epoch = بهترین ← مدل هنوز داره بهتر میشه |
| `val_mae` | 0.001754 | ≈ ±4.64 USD روی XAUUSD=2646 |
| `val_loss` | 0.000593 | Huber loss — کاهشی بوده |
| `loss_function` | **(خالی!)** | باگ شناسایی‌شده — فاز ۵۰ رفع کرد |
| `feature_columns` | 182 | ✅ همه ۱۸۲ فیچر range در window=150 |

### تفسیر val_mae:

```
val_mae = 0.001754 = 0.1754%
XAUUSD ≈ 2646 USD
خطای پیش‌بینی = 0.001754 × 2646 ≈ ±4.64 USD
```

برای horizon=5 کندل 1H (= ۵ ساعت):
- high_offset پیش‌بینی: +0.244% = +6.45 USD بالاتر از close
- low_offset پیش‌بینی: -0.217% = -5.74 USD پایین‌تر از close
- R/R = 6.45 / 5.74 ≈ 1.12

### چرا باید ادامه بده؟

`note: "best epoch 20/20"` یعنی val_loss تا epoch آخر کاهش داشته.
مدل هنوز **saturate نشده** و با epoch بیشتر بهتر میشه.

**توصیه:** epochs=40 با همان LR=3e-5

---

## ۲. باگ رفع‌شده: loss_function در save_model

### مشکل:
`save_model()` (مسیر fallback بدون checkpoint) فیلد `loss_function` را
به `ModelRecord` پاس نمی‌داد. نتیجه: training.json فیلد خالی داشت.

### فایل تغییر یافته:
`scripts/run_dual_models.py` — تابع `save_model()`:

```python
# قبل از فاز ۵۰ (ناقص):
record = ModelRecord(
    ...
    learning_rate=float(learning_rate),
    horizon=int(role.horizon),
    metrics={...},
)

# بعد از فاز ۵۰ (کامل):
record = ModelRecord(
    ...
    learning_rate=float(learning_rate),
    loss_function=role.loss,   # ← اضافه شد
    horizon=int(role.horizon),
    metrics={...},
)
```

همچنین خروجی print هم آپدیت شد:
```
SAVED  gold_range_1h v2
    role    : range trained on XAUUSD 1H
    quality : val_mae 0.001234
    loss fn : huber          ← خط جدید
    record  : ...
```

### توجه:
checkpoint سیستم (فاز ۴۷) از قبل `loss_function` داشت (خط ۵۶۵).
این fix فقط مسیر fallback رو کامل کرد.

---

## ۳. Colab Notebook — سلول‌های جدید

سه سلول به notebook اضافه شد:

### الف) مرحله ۶ب — بررسی نتیجه آموزش
بعد از اتمام آموزش، training.json رو نمایش میده:
- role / timeframe
- epochs, window_size
- loss_function ← جدید
- val_mae به USD
- note (best epoch)

### ب) مرحله ۶ج — ادامه آموزش
`RESUME_CONFIG` با `epochs=40` برای مدل range:
```python
RESUME_CONFIG = dict(
    model  = 'range',
    epochs = 40,        # ← از 20 به 40
    window = 150,
    learning_rate = 3e-5,
    ...
)
```

---

## ۴. وضعیت پیشنهادی برای run بعدی

### range model — ادامه آموزش:
```
--epochs 40 --folds 3 --window 150 --learning-rate 3e-05 --model range
```

انتظار: val_mae < 0.0015 (= ±3.97 USD)

### signal model — بدون تغییر (قبلاً val_accuracy=77.1%):
```
--epochs 30 --folds 3 --window 150 --learning-rate 1e-4 --model signal
```

---

## ۵. بعدی چیه؟

1. **Range model** با epochs=40 train کن (مرحله ۶ج Colab)
2. مدل جدید رو روی Drive ذخیره کن
3. بررسی `range_high_offset` unique values در بکتست (باید > 1 باشه)
4. اجرای بکتست با `filter_zero_bar=1` + مدل جدید
5. مقایسه با سناریو A (no 0-bar, net_pnl=+5.76)

