# فاز ۵۶ — Range Model نهایی: horizon=1 روی 1D

**تاریخ:** 2026-08-25  
**وضعیت:** ✅ کامل

---

## استراتژی نهایی

```
Range model  →  1D candles, horizon=1, seq2seq
                پیش‌بینی: high و low فردا

Signal model →  5M candles
                پیش‌بینی: BUY یا SELL با confidence

ترکیب:
  signal=BUY + confidence>75% → entry در 5M
    TP = predicted_high (فردا)
    SL = predicted_low  (فردا)
  
  signal=SELL + confidence>75% → entry در 5M
    TP = predicted_low  (فردا)
    SL = predicted_high (فردا)
```

---

## چرا horizon=1 بهتره از horizon=5

| | horizon=5 (قبلی) | horizon=1 (جدید) |
|--|-----------------|-----------------|
| target | max_high_5_days | high_tomorrow |
| دقت | پایین (5 روز خطا) | بالا (فردا) |
| ambiguity | بالا | صفر |
| target variance | کم (mean collapse) | بالا (هر روز فرق) |
| collapse risk | بالا | پایین |

---

## تغییرات

| فایل | تغییر |
|------|-------|
| `model_roles.py` | `horizon=1`, `timeframe="1D"`, `window_size=150` |
| `run_dual_models.py` | `--horizon 1`, `--range-timeframes 1D` |
| `handlers.py` (GUI) | range timeframe default: 1H → 1D |
| `dual_predictor.py` | `horizon=1` → مستقیم `raw[-1,0]` و `raw[-1,1]` |
| `Colab notebook` | CONFIG: 1D, epochs=50 |

---

## دستور آموزش نهایی

```bash
# Range model (1D, horizon=1):
python scripts/run_dual_models.py --with-features \
  --model range --range-timeframes 1D \
  --epochs 50 --folds 3 --window 150 \
  --learning-rate 3e-5 --horizon 1

# Signal model (5M):
python scripts/run_dual_models.py --with-features \
  --model signal --signal-timeframe 5M \
  --epochs 30 --folds 3 --window 150 \
  --learning-rate 1e-4 --threshold 0.006
```

---

## انتظار از training

```
val_mae هدف: < 0.005 (= +-0.5% = +-13$ روی XAUUSD=2650)
val_mae فعلی (horizon=5): 0.001754 (ولی collapse شده!)
val_mae هدف (horizon=1): 0.003-0.006 (متنوع و واقعی)
```

---

## تفسیر خروجی inference

```python
# seq2seq output: [batch, window, 2]
# آخرین timestep:
high_offset_tomorrow = model.predict(x)[0, -1, 0]
low_offset_tomorrow  = model.predict(x)[0, -1, 1]

predicted_high = current_close * (1 + high_offset_tomorrow)
predicted_low  = current_close * (1 + low_offset_tomorrow)
```
