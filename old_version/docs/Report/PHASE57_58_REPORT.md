# فاز ۵۷-۵۸ — بهبودهای جامع سیستم

**تاریخ:** 2026-08-26  
**وضعیت:** ✅ کامل

---

## ۱. Signal Model — تغییرات معماری (فاز ۵۸)

### قبل:
- window=150, n_layers=3, n_blocks=2, RF=57

### بعد:
- window=300 (25 ساعت = یه روز کامل)
- n_layers=5, n_blocks=2
- RF=249 (21 ساعت = 83% coverage از window)

### دلیل:
signal model باید الگوهای یه روز کامل رو ببینه. با window=150 فقط 12.5 ساعت context داشت.

---

## ۲. Signal Model — بهبود Training

- **ReduceLROnPlateau**: اضافه شد (قبلاً فقط برای range بود)
- **EarlyStopping**: اضافه شد
- **AdamW**: بجای Adam (weight_decay=1e-5)
- **label_smoothing**: اضافه شد ولی بعداً حذف شد چون SparseCategoricalCrossentropy آن را ساپورت نمیکند

---

## ۳. Backtest — باگ‌های رفع‌شده

### باگ اصلی: `configuration` variable scoping
- در `dual_model_backtest_service.py`، متغیر `configuration` در `run()` shadow میشد
- Python آن را unbound local میدید
- **Fix:** نام به `_active_config` تغییر کرد

### باگ دوم: `spread=configuration.spread`
- قبل از assignment از `configuration` استفاده میشد
- **Fix:** به `self._configuration.spread` تغییر کرد

---

## ۴. Backtest — ویژگی‌های جدید

### Model Log در خروجی:
```
--- models loaded ---
  gold_signal_5m v1 | signal/5M | val_accuracy 80.0% | epochs=20 | trained=2026-08-26
  gold_range_1d v3  | range/1D  | val_mae 0.000010   | epochs=137 | trained=2026-08-25
---
```

### Disk Log:
هر بکتست در `run_logs/backtest_run.log` ذخیره میشه.

### Spread درصدی:
- فیلد جدید "Spread type" (pct/fixed)
- آلپاری Standard: Spread=0.06%, Commission=0

### SL adjustment با spread:
- SL برای BUY: predicted_low - spread
- SL برای SELL: predicted_high + spread

### Entry price = typical (OHLC/4):
- بجای open کندل بعدی

---

## ۵. Range Model — seq2seq

- output: [batch, window, 2] بجای [batch, 2]
- gradient 150× قوی‌تر
- collapse جلوگیری میکنه

---

## ۶. وضعیت مدل‌ها

| مدل | آخرین version | val metric |
|-----|--------------|------------|
| gold_signal_5m | v1 | val_accuracy ~65-80% |
| gold_range_1d | v1-v3 | val_mae ~0.000079-0.001178 |

---

## ۷. تنظیمات بکتست صحیح (آلپاری)

```
Engine:          auto
Range TF:        1D
Confidence:      60%
R/R:             1.0
Spread type:     pct
Spread value:    0.06
Commission:      0
Session filter:  خاموش (برای شروع)
```
