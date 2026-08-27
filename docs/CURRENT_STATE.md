# وضعیت فعلی پروژه — 2026-08-26

## سیستم

ShadBotTrader — Dual Model Trading System
- Signal model: 5M candles → BUY/SELL
- Range model: 1D candles → High/Low فردا → TP/SL
- Broker: Alpari Standard (spread=0.06%, commission=0)

## معماری فعلی

### Signal Model (gold_signal_5m):
```
window=300, n_layers=5, n_blocks=2, RF=249
loss: SparseCategoricalCrossentropy
optimizer: AdamW(lr=0.0001, wd=1e-5)
callbacks: ReduceLROnPlateau + EarlyStopping
```

### Range Model (gold_range_1d):
```
window=150, n_layers=4, n_blocks=2, horizon=1, seq2seq=True
loss: 3×Huber(δ=0.005) + 6×MAE + 1×MSE
optimizer: AdamW(lr=0.001, wd=1e-4)
callbacks: ReduceLROnPlateau + EarlyStopping
```

## وضعیت مدل‌ها

| مدل | وضعیت |
|-----|--------|
| gold_signal_5m | نیاز به train با window=300 |
| gold_range_1d | نیاز به train با seq2seq |

## بکتست

- engine=dual کار میکنه ✅
- trades=0 → مدل‌ها باید بهتر train بشن

## دستور آموزش

```bash
# Signal:
python scripts/run_dual_models.py --with-features \
  --model signal --signal-timeframe 5M \
  --epochs 50 --folds 3 --window 300 \
  --learning-rate 0.0001 --threshold 0.006

# Range:
python scripts/run_dual_models.py --with-features \
  --model range --range-timeframes 1D \
  --epochs 50 --folds 3 --window 150 \
  --learning-rate 0.001
```

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

1. آموزش signal با window=300
2. آموزش range با seq2seq
3. بکتست → بررسی trades > 0
4. اگه trades > 0: session filter فعال کن
