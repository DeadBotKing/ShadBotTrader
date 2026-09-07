# فاز ۱۰۲ — گزینهٔ MAE برای trend_score و monitor روی val_mae

**تاریخ:** 2026-09-07  
**وضعیت:** ✅ کامل  
**Commit:** `3f4174a`

---

## مسئله

اپراتور مشاهده کرد `val_mae` عدد اصلی قضاوت مدل score است و پیشنهاد داد training/optimization روی MAE انجام شود. قبل از این فاز loss فعلی score همان loss ترکیبی range بود:

```text
RangeLoss = 3*Huber + 6*MAE + 1*MSE
```

ولی checkpoint/EarlyStopping/ReduceLR عمدتاً `val_loss` را monitor می‌کردند.

---

## تصمیم

برای جلوگیری از خراب‌کردن مدل‌های range:

```text
فقط trend_score گزینهٔ MAE بگیرد.
range/signal/trend/trend_signal دست‌نخورده بمانند.
```

---

## تغییرات CLI

در `scripts/run_dual_models.py` اضافه شد:

```text
--trend-score-loss {composite,mae}
--monitor-metric {auto,val_loss,val_mae}
```

رفتار:

```text
trend_score + composite → loss قبلی
trend_score + mae       → MAE خالص
غیر trend_score         → این فلگ نادیده گرفته می‌شود
```

`monitor_metric=auto` برای score:

```text
val_mae
```

برای مدل‌های دیگر:

```text
val_loss
```

---

## تغییرات trainer

فایل:

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
```

- `monitor_metric` به trainer اضافه شد.
- `ReduceLROnPlateau` و `EarlyStopping` از monitor انتخاب‌شده استفاده می‌کنند.
- MAE خالص برای seq2seq با همان تمرکز قبلی ساخته شد:

```text
40% loss کل sequence + 60% loss آخرین timestep
```

---

## تغییرات service/model record

فایل:

```text
src/ShadBotTrader/application/services/dual_model_service.py
```

- `loss_name` و `monitor_metric` به train/build_trainer اضافه شد.
- hyperparameters مدل loss و monitor را ذخیره می‌کنند.

---

## تغییرات GUI

فایل:

```text
src/ShadBotTrader/presentation/commands/handlers.py
```

فیلد جدید:

```text
Trend-score loss = composite / mae
```

این فیلد فقط وقتی model=`trend_score` است به CLI پاس می‌شود:

```text
--trend-score-loss mae
```

---

## نحوه استفاده

GUI:

```text
Train a model
model = trend_score
dataset = 1D
Trend-score loss = mae
resume = 0
```

CLI:

```bash
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend_score --signal-timeframe 1D \
  --epochs 50 --folds 3 --window 150 \
  --learning-rate 0.0008 --trend-score-loss mae \
  --storage-root datasets
```

در لاگ باید دیده شود:

```text
objective: mae
monitor  : val_mae (minimize)
```

---

## نکته تفسیری

MAE کمتر به تنهایی edge معاملاتی را ثابت نمی‌کند. باید بعد از training بررسی شود:

```text
MAE vs constant baseline
sign accuracy
corr(pred, actual)
prediction stdev / collapse
profit-aware backtest
```
