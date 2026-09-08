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
Phase107.md — audit کامل trend_signal — ✅ اجرا شد در همین ادامهٔ جلسه
Phase108.md — class weights + F1/PR-AUC برای trend_signal — ✅ اجرا شد
Phase109.md — threshold calibration و heatmap برای trend_signal — ✅ ابزار اجرا شد
Phase110.md — train-only feature selection
Phase111.md — POS/NEG binary event models
Phase112.md — two-branch returns+features benchmark
Phase113.md — random baseline / Monte Carlo / White Reality-style checks
Phase114.md — external/regime features مخصوص XAUUSD
Phase115.md — live decision audit کامل
```

---

## 5) اولویت پیشنهادی اجرای بعدی

Phase107 بعد از ساخت این handoff اجرا شد: script `scripts/evaluate_trend_signal_5m.py`
و GUI command `Audit trend-signal labels` اضافه شد. اپراتور audit واقعی XAUUSD 5M
را اجرا کرد: SELL=40.0%، HOLD=24.0%، BUY=36.0%، majority baseline=40.0%،
ambiguous=28، partial horizon accepted=287، first-hit median=104 bars. یک follow-up
fix هم انجام شد: اگر مدل ذخیره‌شده window متفاوت داشته باشد (مثلاً مدل قدیمی
window=150 در برابر audit window=288)، scoring حالا graceful skip می‌شود و crash
نمی‌کند. Phase108 هم اجرا شد: `--class-weight auto` برای trend_signal، metricهای
per-class F1/precision/recall/AP و GUI field اضافه شد.

ترتیب پیشنهادی از اینجا:

```text
1. Finish real trend_signal training with class_weight=auto and send QUALITY output
2. Run Phase109 calibration tool on that trained model and inspect thresholds
3. Phase 110: feature selection train-only
4. Phase 111: POS/NEG binary event models
5. Phase 113: significance checks
6. Phase 112: two-branch benchmark
7. Phase 114: external/regime features
8. Phase 115: live decision audit
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

---

## Addendum — 2026-09-08: deep architecture roadmap + GUI cleanup

اپراتور درخواست کرد مدل‌ها/معماری‌های بهتر از منابع GitHub/Google/کتاب‌ها دوباره بررسی شوند و فازها کامل‌تر شوند. نتیجه در گزارش زیر ثبت شد:

```text
docs/Report/PHASE116_DEEP_MODEL_ARCHITECTURE_RESEARCH_AND_ROADMAP.md
```

فازهای اضافه/به‌روزرسانی‌شده:

```text
Phase112: Branch benchmark — LightGBM/CatBoost/XGBoost + two-branch neural + MiniRocket/LITE
Phase116: Hybrid Range-Aware Decision Engine
Phase117: Advanced neural benchmarks — xLSTM-TS, TSMixer, PatchTST, Mamba, KAN
Phase118: Optional tick/order-book branch — DeepLOB/TLOB/LiT فقط با دادهٔ واقعی
Phase119: GUI cleanup — Advanced options collapse completed
```

اصل مسیر جدید:

```text
gold_trend_signal_5m + booster branches + BUY/SELL specialists
+ gold_range_1d daily envelope + gold_range_4h TP/SL bracket
+ meta-label / conformal uncertainty gate
=> BUY / SELL / NO_TRADE
```

وضعیت عملیاتی مهم: اپراتور هنوز training واقعی فاز ۱۰۸ را روی سیستم خودش اجرا می‌کند. فاز ۱۰۹ فقط از نظر ابزار/GUI آماده است و باید بعد از `SAVED/KEPT` شدن مدل جدید `gold_trend_signal_5m` اجرا شود.

GUI تغییر کرد، اما قابلیت‌ها حذف نشدند: fieldهای کم‌مصرف/حرفه‌ای با `CommandField.advanced=True` زیر `<details class="advanced-inputs">` نمایش داده می‌شوند و همچنان defaultشان submit می‌شود.

---

## Addendum — 2026-09-08: Phase120/121 after WaveNet trend_signal collapse

Real pilot logs showed WaveNet `gold_trend_signal_5m` was not producing a healthy 3-class model:

```text
class_weight auto → uniform probability collapse
class_weight off  → single-class collapse (always BUY/SELL depending on fold)
```

Implemented Phase120:

```text
val_action_min_f1, val_action_min_f1_supported, val_action_collapse,
val_predicted_class_count, per-class predicted counts
```

Implemented Phase121:

```text
scripts/train_trend_signal_boosters.py
src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py
Dashboard command: Train trend-signal booster
Optional deps: requirements-boosters.txt
```

Recommended next operator command after installing optional deps:

```powershell
pip install -r requirements-boosters.txt
python -u scripts/train_trend_signal_boosters.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --booster auto `
  --output-mode multiclass `
  --summary-mode basic `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --folds 3 `
  --val-size 2000 `
  --class-weight auto `
  --n-estimators 400 `
  --learning-rate 0.03 `
  --storage-root datasets
```

If multiclass collapses, run specialist branches with `--output-mode buy` and `--output-mode sell`.

---

## Addendum — 2026-09-08: Phase123 hybrid XGBoost matrix

Operator clarified the desired architecture: not a simple ensemble and not XGBoost as a differentiable layer inside WaveNet; instead, build a matrix from model outputs and feed that to XGBoost/LightGBM final head.

Implemented:

```text
scripts/build_hybrid_xgboost_matrix.py
CommandKind.BUILD_HYBRID_XGBOOST_MATRIX
GUI card: Build hybrid XGBoost matrix
docs/Phases/Phase123.md
```

Matrix columns include booster specialist probabilities, optional multiclass booster probabilities, optional WaveNet probabilities, and true range-model forecasts from `gold_range_1d` and `gold_range_4h` converted into up/down-room features. Range alignment is causal: only the latest closed 1D/4H bar is used for each 5M signal timestamp.

Recommended next run:

```powershell
python -u scripts/build_hybrid_xgboost_matrix.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --scope holdout `
  --max-windows 8000 `
  --summary-mode basic `
  --booster lightgbm `
  --include-specialists 1 `
  --include-multiclass-booster 1 `
  --include-wavenet 1 `
  --require-wavenet 0 `
  --include-range 1 `
  --require-range 1 `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --storage-root datasets
```

Output:

```text
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
run_logs/hybrid_xgboost_matrix/latest.json
```
