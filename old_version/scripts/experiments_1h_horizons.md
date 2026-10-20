# آزمایش‌های پیشنهادی 1H — پیدا کردن horizon بهینه

**هدف:** پیدا کردن horizon بهینه روی 1H برای براکت‌های معنادار
(حداقل $30-50 عرض تا داخل نویز 5M نیفتد).

**پیش‌فرض‌های همهٔ اجراها:** window=150 · 4×2 · folds=3 · train-ratio=80
· epochs=30 · LR=5e-4 · dیتای 50k کندل 1H.

---

## اجرای ۱ — horizon=12 (نیم‌روز) — 🥇 پیشنهاد اول

```bash
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model range --range-timeframes 1H --horizon 12 --epochs 30 --folds 3 \
  --window 150 --train-ratio 80.0 --learning-rate 0.0005 \
  --es-patience 12 --rlr-patience 5 \
  --storage-root datasets
```

انتظار: عرض براکت ~$25-40 (مرز ناحیهٔ طلایی).
val_mae انتظار: 0.002-0.004 (بزرگ‌تر از horizon=1 طبیعی است — مقایسه نکن).

## اجرای ۲ — horizon=24 (یک روز کامل) — 🥈 پیشنهاد دوم

```bash
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model range --range-timeframes 1H --horizon 24 --epochs 30 --folds 3 \
  --window 150 --train-ratio 80.0 --learning-rate 0.0005 \
  --es-patience 12 --rlr-patience 5 \
  --storage-root datasets
```

انتظار: عرض براکت ~$30-50 (هم‌ارز مدل 1D ولی ۲۴ بار در روز به‌روز).

## اجرای ۳ — horizon=6 (کنترل) — 🥉 اختیاری

```bash
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model range --range-timeframes 1H --horizon 6 --epochs 30 --folds 3 \
  --window 150 --train-ratio 80.0 --learning-rate 0.0005 \
  --es-patience 12 --rlr-patience 5 \
  --storage-root datasets
```

انتظار: عرض براکت $15-25 — مرزی.

## اجرای ۴ — horizon=1 (پایهٔ مقایسه — کنترل منفی)

```bash
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model range --range-timeframes 1H --horizon 1 --epochs 30 --folds 3 \
  --window 150 --train-ratio 80.0 --learning-rate 0.0005 \
  --storage-root datasets
```

انتظار: عرض براکت $5-15 — داخل نویز (آنچه الان دیدیم).

---

## بعد از هر اجرا

1. **بکتست با همان مدل** — Range timeframe=1H · confidence=60% · R/R=1.2
   · session filt=1 · min SL dist=0 (براکت‌ها خودشان درست اندازه‌اند)
2. **این سه سنجه را بنویس:**
   - تعداد ترید · WR · PnL
   - **expectancy** ← تنها معیار نهایی
   - TP hit rate
3. **مدل‌ها را قبل از اجرای بعدی کپی کن:** `datasets/models/` →
   `gold_range_1h v1` هر بار overwrite می‌شود!

## جدول مقایسهٔ نهایی

| horizon | val_mae | ترید | WR | TP hit | expectancy |
|---|---|---|---|---|---|
| 1 (کنترل) | | | | | |
| 6 | | | | | |
| 12 | | | | | |
| 24 | | | | | |

⚠️ **val_mae بین horizonها مقایسه نشود** — افق بزرگ‌تر = خطای بزرگ‌تر
طبیعی است. تنها معیار: expectancy بکتست.
