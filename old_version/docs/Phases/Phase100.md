# فاز ۱۰۰ — trend_score روی کندل واقعی 1D + آموزش و مدل‌کارت

**تاریخ:** 2026-09-06
**وضعیت:** ✅ کامل — پیاده‌سازی، آموزش، ارزیابی، مستندسازی و zip انجام شد
**Commitهای اصلی:** `08b596d`, `d6ac7c7`

---

## هدف

اپراتور گفت: «مدل رو بساز اول — ما باید اول یه تخمین درست‌حسابی از روند آینده بدست بیاریم». هدف فاز این بود که مدل `trend_score` از حالت تارگت مصنوعی مبهم خارج شود و روی **score کندل واقعی روز بعد** train شود.

---

## تعریف تارگت

برای هر کندل تصمیم `t`:

```text
score[t] = (close[t+1] - open[t+1]) / (high[t+1] - low[t+1])
```

بازه:

```text
-1 تا +1
+1 نزدیک close در سقف کندل آینده
-1 نزدیک close در کف کندل آینده
0 یعنی کندل بدون جهت واضح
```

روی تایم‌فریم 1D:

```text
--label-horizon خودکار = 1
یعنی score از کندل واقعی روز بعد، نه کندل مصنوعی 288×5M
```

---

## دیتاست استفاده‌شده در سندباکس

منبع:

```text
Yahoo Finance GC=F — proxy آزاد COMEX gold futures، نه XAUUSD spot بروکر
```

آمار:

```text
2,513 کندل واقعی روزانه
2016-09-06 تا 2026-09-04
```

مسیر:

```text
datasets/processed/XAUUSD/1D/v1.parquet
```

یادآوری مهم:

```text
datasets/ gitignored است؛ مدل‌ها/دیتا داخل zip تحویل داده می‌شوند، نه git.
```

---

## تغییرات کد

فایل‌ها:

```text
scripts/run_dual_models.py
src/ShadBotTrader/infrastructure/ai/model_roles.py
src/ShadBotTrader/infrastructure/ai/target_builder.py
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
src/ShadBotTrader/presentation/commands/handlers.py
scripts/fetch_1d_gold_yahoo.py
scripts/evaluate_trend_score_1d.py
```

تغییرات کلیدی:

```text
- --label-horizon default=0 به معنی auto
- trend_score روی 1D → label_horizon=1
- trend_score روی غیر 1D → label_horizon=288
- sanity prediction برای trend_score جدا شد تا وارد RangePredictor دوخروجی نشود
- SHADBOT_STREAM_THRESHOLD_BYTES برای ماشین کم‌رم اضافه شد
- GUI فیلد label_horizon خالی/0 = auto شد
- گزارش QUALITY مخصوص score اضافه شد
```

---

## معماری مدل gold_trend_score_1d v1

```text
Input: 150 × 182
Output: 150 × 1 seq2seq
Parameters: 290,209
Activation output: tanh
```

Trunk:

```text
ZeroPadding
SeparableConv1D(288=48×6, kernel=10, linear)
Dropout(0.10)
8 residual blocks: dilations 1,2,4,8 ×2
هر block:
  causal Conv1D(96=48×2, kernel=5, linear)
  GatedActivationUnit = tanh(first half) * sigmoid(second half)
  Conv1D(48, 1×1)
  Dropout(0.10)
  Add skip
SeparableConv1D(48,k=5,relu)
Conv1D(48,1×1,relu)
SeparableConv1D(48,k=3,relu)
SeparableConv1D(1,k=3,tanh)
```

Receptive field:

```text
RF=121 یعنی 81% از window=150
```

Loss اولیه:

```text
RangeLoss = (3×Huber(delta=0.005) + 6×MAE + 1×MSE) / 10
seq2seq: 40% کل sequence + 60% آخرین timestep
```

---

## اجرای آموزش trend_score

Command:

```bash
PYTHONPATH=src SHADBOT_STREAM_THRESHOLD_BYTES=1000000 TF_ENABLE_ONEDNN_OPTS=0 \
TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1 OMP_NUM_THREADS=1 MALLOC_ARENA_MAX=2 \
python3 scripts/run_dual_models.py --model trend_score --signal-timeframe 1D \
  --symbol XAUUSD --with-features --epochs 40 --folds 2 --window 150 --storage-root datasets
```

آمار:

```text
40 epoch × 2 fold = 80 epoch
زمان: حدود 19:55
batch=8
2,287 windows
input: 150×182
```

نتایج:

```text
Fold 1: val_loss 0.415812, val_mae 0.5992
Fold 2: val_loss 0.396486, val_mae 0.588512
train loss: 0.820 → 0.372
train MAE: حدود 0.546
constant baseline: 0.5705
```

ارزیابی کامل:

```text
MAE model 0.5895 vs const 0.5882 → skill -0.2%
sign accuracy 52.0% ≈ dominant baseline
corr(pred, actual)=nan چون pred stdev≈0
live pred +0.0008 → بی‌رون
```

حکم صادقانه:

```text
مدل trend_score_1d v1 edge قابل معامله نشان نداد؛ به میانگین collapse کرد.
```

---

## sister model: gold_trend_1d

همان دیتای 1D برای مدل رنگ کندل train شد:

```text
label: GREEN/RED
input: 150×177
params: 138,290
best kept epoch: 12/40
val_acc: 55.7% vs majority baseline 54.3% (+1.4pp)
transient peaks: 57.7% تا 59.4%
final sanity: sell 50.8%, buy 49.2% — غیرقابل اقدام
```

---

## نتیجه مفهومی

چرا range بهتر از score است؟

```text
corr(ATR_t, ATR_t+1) = +0.9972  → volatility حافظه دارد
corr(score_t, score_t+1) = +0.0017 → direction روزانه حافظه ندارد
```

پس range model عرض براکت را از volatility clustering می‌آموزد؛ score دقیقاً بخش direction را isolate می‌کند که روی daily gold price-only تقریباً noise است.

---

## خروجی‌های مستند

```text
docs/Report/PHASE100_REPORT.md
docs/Report/MODEL_CARD_trend_score_1d.html
scripts/fetch_1d_gold_yahoo.py
scripts/evaluate_trend_score_1d.py
```

---

## بدهی‌ها بعد از فاز ۱۰۰

```text
- trend_score_1d بدون edge؛ فقط research/secondary
- trend_signal_5m باید retrain شود
- gold_signal_5m قدیمی است و نیاز به retrain جدی دارد
- مجوزهای trend/trend_signal هنوز کامل به triple backtest وصل نشده‌اند
```
