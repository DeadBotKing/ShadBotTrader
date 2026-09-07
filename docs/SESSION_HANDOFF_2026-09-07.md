# SESSION HANDOFF — 2026-09-07

این سند برای این ساخته شد که اگر چت جدید باز شد، Agent دقیقاً بفهمد در این جلسه چه اتفاقی افتاد، الان کجای کاریم، و قدم بعدی چیست.

---

## 1) وضعیت کلی پروژه

```text
Project: ShadBotTrader
Architecture: Clean Architecture + DDD
Broker target: MetaTrader 5 / Alpari
Main symbol: XAUUSD
Language: Python
Current branch: main
Latest documented commit at handoff: f4592f2
```

قانون عملیاتی:

```text
کد = واقعیت
Docs = نیت/ثبت تصمیم
بدون redesign مگر با اجازه صریح اپراتور
بدون placeholder implementation
هر تغییر meaningful باید در docs/WORKLOG.md ثبت و commit شود
```

---

## 2) مدل‌های فعلی و نقش آن‌ها

```text
gold_signal_5m        → BUY/SELL binary first-passage signal؛ قدیمی و نیازمند retrain
gold_range_1d         → High/Low range؛ قدیمی/legacy pct، retrain لازم
gold_range_4h         → range/bracket بهتر، قبلاً baseline را حدود 4% زده
gold_trend_1d         → GREEN/RED candle color؛ edge ضعیف اما واقعی‌تر از score
gold_trend_score_1d   → regression score کندل واقعی بعدی؛ فعلاً research/secondary
gold_trend_signal_5m  → BUY/HOLD/SELL event classification؛ مسیر پیشنهادی اصلی بعدی
```

---

## 3) کارهای انجام‌شده در این جلسه

### Phase 100 — trend_score روی کندل واقعی 1D

- target برای `trend_score` روی 1D شد score کندل واقعی روز بعد:

```text
score = (close[D1] - open[D1]) / (high[D1] - low[D1])
```

- dataset سندباکس: Yahoo GC=F، 2,513 کندل روزانه 2016-09-06 تا 2026-09-04.
- `gold_trend_score_1d v1` train شد اما edge نداد:

```text
MAE model ≈ 0.5895 vs constant ≈ 0.5882 → skill -0.2%
prediction collapse به میانگین
```

- `gold_trend_1d v1` هم train شد:

```text
val_acc 55.7% vs majority baseline 54.3%
```

گزارش‌ها:

```text
docs/Report/PHASE100_REPORT.md
docs/Report/MODEL_CARD_trend_score_1d.html
docs/Phases/Phase100.md
```

---

### Phase 101 — رفع live log آموزش GUI روی Windows

مشکل: وقتی اپراتور از GUI train می‌زد، log چاپ نمی‌شد یا live panel نمی‌آمد.  
علت‌ها:

```text
race در dispatch_async
encoding/pipe مشکل‌دار روی Windows
باز نگه داشتن write handle فایل log در کل training
```

اصلاح‌ها:

```text
dispatch_async قبل از redirect busy را set می‌کند
subprocess با python -u و UTF-8 اجباری اجرا می‌شود
log با appendهای کوتاه نوشته می‌شود
```

Commit:

```text
e5ca863
```

گزارش فاز:

```text
docs/Phases/Phase101.md
```

---

### Phase 102 — MAE objective و val_mae monitor برای trend_score

اضافه شد:

```text
--trend-score-loss {composite,mae}
--monitor-metric {auto,val_loss,val_mae}
```

برای `trend_score`:

```text
monitor auto = val_mae
mae = MAE خالص با تمرکز seq2seq 40% کل sequence + 60% last timestep
```

Commit:

```text
3f4174a
```

گزارش فاز:

```text
docs/Phases/Phase102.md
```

---

### Phase 103 — audit target/normalization و حذف fake tail label

اپراتور شک کرد شاید محاسبات target یا normalization غلط است. بررسی شد:

```text
score formula درست بود
target داخل input نبود
feature scaling درست بود
```

اما bug واقعی پیدا شد:

```python
score_by_index.get(orig, 0.0)
```

یعنی rowهای بدون future با target جعلی `0.0` پر می‌شدند. اصلاح شد که tail بدون label حذف شود.

Commit:

```text
db515b4
```

گزارش فاز:

```text
docs/Phases/Phase103.md
```

---

### Phase 104 — input scaling مخصوص trend_score به [-1,+1]

اپراتور پیشنهاد داد چون target score در `[-1,+1]` است، input هم برای مدل score همین بازه باشد. انجام شد:

```text
trend_score input scale = [-1,+1]
range/signal/trend/trend_signal = [-2,+2]
```

در `ModelRole` و `ModelRecord` ثبت می‌شود:

```text
input_scale_range
```

resume از checkpoint با scale متفاوت رد می‌شود.

Audit عددی:

```text
gold_trend_score_1d scale (-1.0, 1.0), min=-1.0, max=1.0, target_col_excluded=True
gold_range_1d       scale (-2.0, 2.0), min=-2.0, max=2.0, target_col_excluded=True
```

Commit:

```text
fd4a190
```

گزارش فاز:

```text
docs/Phases/Phase104.md
```

---

### Phase 105 — بررسی پروژه Leci37

منبع:

```text
https://github.com/Leci37/TensorFlow-stocks-prediction-Machine-learning-RealTime
```

Repo موقتاً clone شد، بررسی شد، بعد برای خلوت‌سازی workspace حذف شد.

نتیجه فنی:

```text
کپی مستقیم نه؛ ایده‌ها بله:
event-based GT
POS/NEG binary models
feature selection
class weighting
threshold calibration
ensemble
profit-aware evaluation
```

گزارش:

```text
docs/Report/PHASE105_LECI37_CODE_REVIEW_AND_ADOPTION_PLAN.md
docs/Phases/Phase105.md
```

---

### Phase 106 — بررسی Alpaca / ari99 / Onepagecode + cleanup

منابع:

```text
https://alpaca.markets/learn/tensorflow-market-forecasting
https://github.com/ari99/algorithmic_trading
https://onepagecode.substack.com/p/an-algo-trading-framework-using-tensorflow
```

Repo `ari99/algorithmic_trading` موقتاً clone شد، commit `c8479f3`، بررسی شد، بعد حذف شد.

نتیجه مشترک منابع:

```text
روی regression قیمت/score گیر نکن.
event/action classification + class weights + threshold calibration + profit-aware backtest مسیر عملی‌تر است.
```

Workspace خلوت شد؛ فقط ShadBotTrader و uploads و zip نهایی باقی ماند.

گزارش:

```text
docs/Report/PHASE106_ALPACA_ARI99_ONEPAGECODE_REVIEW_AND_SHADBOT_PLAN.md
docs/Phases/Phase106.md
```

Commit نهایی docs/cleanup references:

```text
f4592f2
```

---

## 4) فازهای پیشنهادی آماده اجرا

فازهای زیر در `docs/Phases` اضافه شده‌اند:

```text
Phase107.md — audit کامل trend_signal
Phase108.md — class weights + F1/PR-AUC برای trend_signal
Phase109.md — threshold calibration و heatmap backtest
Phase110.md — train-only feature selection
Phase111.md — POS/NEG binary event models
Phase112.md — two-branch returns+features benchmark
Phase113.md — random baseline / Monte Carlo / White Reality-style checks
Phase114.md — external/regime features مخصوص XAUUSD
Phase115.md — live decision audit کامل
```

---

## 5) اولویت پیشنهادی اجرای بعدی

ترتیب پیشنهادی:

```text
1. Phase 107: trend_signal audit
2. Phase 108: class weights + F1/PR-AUC
3. Phase 109: threshold calibration/heatmap
4. Phase 110: feature selection train-only
5. Phase 111: POS/NEG binary event models
6. Phase 113: significance checks
7. Phase 112: two-branch benchmark
8. Phase 114: external/regime features
9. Phase 115: live decision audit
```

دلیل:

```text
اول باید target/metric/evaluation درست شود؛ بعد architecture/model جدید.
```

---

## 6) دستور مهم برای اجرای trend_score بعد از Phase104

اگر هنوز خواستی score را تست کنی:

```powershell
python -u scripts/run_dual_models.py `
  --with-features `
  --symbol XAUUSD `
  --model trend_score `
  --signal-timeframe 1D `
  --epochs 50 `
  --folds 3 `
  --window 150 `
  --train-ratio 80 `
  --learning-rate 0.0008 `
  --trend-score-loss mae `
  --storage-root datasets
```

اما باید از صفر باشد، نه resume از مدل قدیمی:

```text
resume = 0
```

---

## 7) دستور مهم برای GUI

اگر Dashboard باز بود و کد جدید جایگزین شد:

```powershell
Ctrl+C
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
```

برای trend_score باید در live log دیده شود:

```text
training: trend_score(1D)
TREND_SCORE MODEL
objective: mae
monitor  : val_mae (minimize)
input scale: minmax [-1, +1] per feature/window
```

---

## 8) بدهی‌ها و هشدارها

```text
- trend_score هنوز edge ثابت‌شده ندارد؛ research/secondary بماند.
- gold_trend_signal_5m باید با target/metrics بهتر retrain شود.
- gold_signal_5m قدیمی است و retrain جدی لازم دارد.
- range_4h/1d برای bracket همچنان مهم‌ترین نقطه قوت است.
- featureهای external/regime برای جهت طلا احتمالاً لازم‌اند.
- هر تغییر معماری جدید نیاز به approval دارد.
```

---

## 9) Quality gate وضعیت آخرین فازهای docs

برای تغییرات code phases 101-104 تست‌های مرتبط و full pytest در همان زمان اجرا شد.  
برای فازهای review/docs، تغییرات production code نداشتند. وضعیت شناخته‌شده gate:

```text
full pytest: در محیط قبلی سبز شد
ruff/black/mypy کامل پروژه: خطاهای قدیمی/pre-existing خارج از تغییرات وجود داشتند
```

در هر فاز اجرایی بعدی دوباره باید gate کامل یا حداقل targeted + documented full gate اجرا شود.
