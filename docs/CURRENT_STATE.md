# وضعیت فعلی پروژه — 2026-08-30

## سیستم

ShadBotTrader — Dual Model Trading System
- Signal model: 5M candles → BUY/SELL
- Range model: 1D/1H candles → High/Low فردا → TP/SL
- Broker: Alpari Standard (spread=0.06%, commission=0)

## معماری فعلی

### Signal Model (gold_signal_5m):
```
window=300, n_layers=5, n_blocks=2, RF=249
loss: SparseCategoricalCrossentropy
optimizer: AdamW(lr=0.0001, wd=1e-5)
callbacks: ReduceLROnPlateau + EarlyStopping
```

### Range Model (gold_range_1d / gold_range_1h):
```
window=150, n_layers=4, n_blocks=2, horizon=12, seq2seq=True
loss: 3×Huber(δ=0.005) + 6×MAE + 1×MSE
optimizer: AdamW(lr=0.001, wd=1e-4)
callbacks: ReduceLROnPlateau + EarlyStopping

# فاز ۹۵ — تارگت ATR-نرمال‌شده:
target[t,k] = (high[t+k] − close[t]) / ATR14[t]
مصرف: price = close + mult × ATR14(کندل مرجع)
ModelRecord.target_units = "atr" (قدیمی‌ها "pct" — سازگار)
```

## وضعیت مدل‌ها

| مدل | وضعیت |
|-----|--------|
| gold_signal_5m v1 | val_accuracy 77.1% |
| gold_range_1d v2 | تارگت pct قدیمی — با تارگت ATR باید ریترین شود |
| gold_range_1h v1 | تارگت pct قدیمی — با تارگت ATR باید ریترین شود |

## بکتست

- engine=dual کار میکنه ✅
- آخرین نتیجهٔ صادقانه (فیلتر session + min SL $40 + R/R 1.2):
  264 trades, WR 20.1%, PnL −$17.41
- مشکل آفست ثابت مدل رنج ریشه‌یابی و در فاز ۹۵ حل شد (تارگت ATR)

## دستور آموزش

```bash
# Signal:
python scripts/run_dual_models.py --with-features \
  --model signal --signal-timeframe 5M \
  --epochs 50 --folds 3 --window 300 \
  --learning-rate 0.0001 --threshold 0.006

# Range (فاز ۹۵ — تارگت ATR خودکار فعال است):
python scripts/run_dual_models.py --with-features \
  --model range --range-timeframes 1H \
  --epochs 50 --folds 3 --window 150 --horizon 12 \
  --learning-rate 0.0005
```

در سربرگ آموزش رنج باید `target units: atr` ببینید؛ بعد از آموزش،
sanity forecast باید ضرایب ×ATR متفاوت برای هر کندل بدهد.

> **فاز ۵۹ (2026-08-26):** اندازهٔ اعتبارسنجی دیگر ۲٪ استخر لیبل نیست —
> پیش‌فرض **۱۰٪** شد (+ گارد اولین fold). کنترل دستی: `--val-size N` یا
> `--val-ratio 0.2`. سربرگ لاگ حالا `val fold size` را صریح چاپ می‌کند.
> جزئیات: `Report/PHASE59_REPORT.md`
>
> **فاز ۶۰ (2026-08-26):** ReduceLROnPlateau + EarlyStopping حالا واقعاً به
> مدل سیگنال هم وصل شدند (باگ سیم‌کشی `loss=None`) → اجرای signal حدود نصف
> زمان قبل. حکم QUALITY با baseline واقعی فولد ولید. جزئیات:
> `Report/PHASE60_REPORT.md`

## تنظیمات بکتست

```
Engine: auto | Range TF: 1D | Confidence: 60%
R/R: 1.0 | Spread: pct/0.06 | Commission: 0
```

## گام بعدی

1. ریترین مدل رنج (1H, horizon=12) با تارگت ATR فاز ۹۵
2. چک تنوع خروجی: forecast چند کندل → ضریب ×ATR باید فرق کند
3. بکتست با مدل جدید → بررسی اینکه آفست‌ها و براکت‌ها معنادار شدن
4. اگه expectancy هنوز منفی بود: فیلتر ترند EMA50 روزانه + R/R=1.0
