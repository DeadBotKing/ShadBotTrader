# وضعیت فعلی پروژه — 2026-09-07

## سیستم

ShadBotTrader — Dual/Triple Model Trading System
- Signal model: 5M candles → BUY/SELL
- Range model: 1D/1H/4H candles → High/Low فردا → TP/SL (ATR-normalized)
- Trend model: 1D/4H candles → GREEN/RED رنگ کندل بعدی
- Trend-signal model: 5M candles → BUY/HOLD/SELL (rolling 288)
- Trend-score model: 5M candles → score روند (−1..+1) رگرسیون
- Strategy: Triple (5M signal · 4H bracket · 1D trend)
- Broker: Alpari (spread=0.06%, session-first MT5)

## مدل‌های AI

| مدل | تایم‌فریم | نوع | تارگت | وضعیت |
|-----|-----------|------|--------|--------|
| gold_signal_5m | 5M | 2-class | first-passage ±0.6% | آموزش‌دیده (77.1%) — قدیمی، نیاز به ریترین |
| gold_range_1d | 1D | رگرسیون | High/Low ATR-normalized | قدیمی (pct) — ریترین لازم |
| gold_range_4h | 4H | رگرسیون | High/Low ATR-normalized | v3 — BEATS baseline 4% |
| gold_trend_1d | 1D | 2-class | رنگ کندل بعدی | v1 — BEATS baseline 57% vs 53.2% |
| gold_trend_score_5m | 5M | رگرسیون | score=(C−O)/(H−L) ∈(−1,+1) | در حال آموزش (window=288, 4×3) |
| gold_trend_signal_5m | 5M | 3-class | first ±0.5×ATR(1D) | نیاز به ریترین (بعد از فیکس مانع روزانه) |

## استراتژی Triple (فاز ۹۷)

```
مجوز ۱: سیگنال 5M احتمال > آستانهٔ GUI
مجوز ۲: شیب روزانه — مدل رنج 1D پیش‌بینی D1 → شیب High/Low نسبت به D0
         حالت‌ها: both | either | high | low (GUI)
مجوز ۳: سمت TP (خرید: TP > ورود)
مجوز ۴: نزدیکی ورود به سطح روزانه ≤ max_entry_distance_atr × ATR14(1D)
مجوز ۵ (آینده): رنگ ترند از gold_trend_<tf>
براکت: TP/SL از مدل رنج 4H با fallback: D0 → 5M-امروز
SL نهایی: ≥ min_sl_distance (GUI) و ≥ 2×spread
اسپرد: درصدی (GUI) — برخورد TP/SL روی BID/ASK
```

## گیت‌های فیلتر

| فیلتر | توضیح |
|-------|-------|
| EMA50 daily | SHORT ممنوع وقتی قیمت بالای EMA50، LONG وقتی زیر |
| Session filter | فقط ساعت‌های مشخص UTC |
| Min SL dist | حداقل فاصلهٔ SL از ورود (بعد از fallback) |
| 0-bar filter | حذف ترید‌های بسته‌شده در همان کندل ورود |

## زیرساخت MT5

- Session-first: اول اتصال به ترمینال (بدون credential) — اکانت‌های OTP کار می‌کنند
- symbol_select: قبل از هر fetch — خطای قابل‌فهم برای نمونه غلط/حساس به حروف
- mapping: XAUUSD → XAUUSD_i (Alpari)

## مدل‌های score (فاز ۹۸-ب + فاز ۱۰۰)

```
gold_trend_score_5m: رگرسیون خالص — تارگت مصنوعی 288×5M (قدیمی)
gold_trend_score_1d: فاز ۱۰۰ — تارگت از کندل واقعی 1D فردا:
  score = (close[D1]−open[D1])/(high[D1]−low[D1]) ∈ (−1,+1)
خروجی: Dense(1, tanh) | loss: Huber | window=150×1D
پیش‌فرض خودکار: --label-horizon خالی → 1D:1 (واقعی)، بقیه: 288
معنی: +0.9 = صعود قوی، −0.9 = نزول قوی، ~0 = بی‌رون

v1 سندباکس (2026-09-06): آموزش روی 2,513 کندل واقعی Yahoo GC=F (10 سال):
بدون لبه (skill −0.2% vs ثابت) — رانش یک‌روزه از فیچر قیمتی خالص
غیرقابل‌پیش‌بینی است؛ دقیقاً انتظار مستند TREND_SCORE_1D_PROPOSAL.
لبه فقط از فیچر رژیم‌محور (DOW/vol-regime) یا فیلترهای session می‌آید.
gold_trend_1d v1 سندباکس (همان دیتا): val_acc 55.7% vs 54.3% (+1.4pp) —
سازگار با لبهٔ اثبات‌شدهٔ اپراتور (+3.8%)؛ kept در epoch 12.

## دستورات کلیدی

```bash
# آموزش trend_score — حالت کندل واقعی 1D (فاز ۱۰۰؛ label-horizon خودکار=1)
# فاز ۱۰۲: monitor خودکار score = val_mae؛ برای تست MAE خالص فلگ آخر را بگذار
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend_score --signal-timeframe 1D \
  --epochs 50 --folds 3 --window 150 \
  --learning-rate 0.0008 --trend-score-loss mae \
  --storage-root datasets

# ماشین کم‌رم (سندباکس/کانتینر 1GB): استریم اجباری
SHADBOT_STREAM_THRESHOLD_BYTES=1000000  # اختیاری

# audit trend_signal قبل از آموزش سنگین (فاز ۱۰۷)
python scripts/evaluate_trend_signal_5m.py --symbol XAUUSD \
  --timeframe 5M --window 288 --label-horizon 288 \
  --atr-mult 0.5 --folds 3 --storage-root datasets

# آموزش trend_signal (سه‌کلاسه)
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend_signal --range-timeframes 5M --signal-timeframe 5M \
  --epochs 50 --folds 3 --window 288 --learning-rate 0.0008 \
  --storage-root datasets

# آموزش trend رنگ (1D)
python scripts/run_dual_models.py --with-features --symbol XAUUSD \
  --model trend --range-timeframes 1D --signal-timeframe 1D \
  --epochs 50 --folds 3 --window 150 --learning-rate 0.0008 \
  --storage-root datasets

# بکتست triple
# GUI: strategy=triple | range_timeframe=4H | trend_filter=ema50
#      min_sl_dist=6 | atr_mult=0.5 | max_entry_distance_atr=0.25
```

## Phase roadmap handoff (به‌روزرسانی 2026-09-08)

- فازهای جدید در `docs/Phases` خرد شدند: `Phase100.md` تا `Phase119.md`.
- index سریع همچنان برای سازگاری در این مسیر است: `docs/Phases/README_PHASE100_115.md`، اما محتوایش تا فاز ۱۱۹ به‌روزرسانی شده است.
- گزارش سرچ عمیق معماری/مدل‌های بهتر: `docs/Report/PHASE116_DEEP_MODEL_ARCHITECTURE_RESEARCH_AND_ROADMAP.md`.
- handoff کامل جلسه قبلی: `docs/SESSION_HANDOFF_2026-09-07.md`.
- `Phase107` انجام شد: script و GUI جدید `Audit trend-signal labels` برای audit کامل
  `trend_signal_5m` اضافه شد.
- `Phase108` از نظر کد انجام شد و روی سیستم اپراتور تست عملیاتی شد. نتیجهٔ WaveNet
  برای `gold_trend_signal_5m` قابل قبول نبود: با `class_weight=auto` به uniform نزدیک شد و
  با `class_weight=off` به always-BUY/SELL collapse کرد. بنابراین WaveNet فعلاً core مسیر نیست.
- `Phase109` از نظر کد انجام شد، اما calibration اصلی WaveNet به دلیل no-edge/collapse اجرا/استفاده
  نشد. مسیر عملیاتی به booster-specialist calibration در فاز ۱۲۲ منتقل شد.
- `Phase119` انجام شد: GUI خلوت شد؛ پارامترهای کم‌مصرف/حرفه‌ای زیر `Advanced options`
  رفتند، بدون اینکه field یا قابلیت حذف شود.
- `Phase120` انجام شد: metricهای ضد-collapse اضافه شدند (`val_action_min_f1_supported`,
  `val_action_collapse`, predicted class counts) تا always-BUY/SELL گول‌زننده رد شود.
- `Phase121` انجام شد: branch مستقل `Train trend-signal booster` برای LightGBM/XGBoost/CatBoost
  روی خلاصهٔ causal پنجرهٔ 288 کندلی اضافه شد. اجرای واقعی نیازمند نصب optional dependencies است:
  `pip install -r requirements-boosters.txt`.
- `Phase122` انجام شد: script و GUI جدید `Calibrate booster specialists` برای کالیبراسیون مشترک
  BUY/SELL specialistها اضافه شد و threshold مشترک را در model record ذخیره می‌کند.
- `Phase123` انجام شد: script و GUI جدید `Build hybrid XGBoost matrix` ساخته شد. این ماتریس
  خروجی‌های BUY/SELL booster، multiclass booster، WaveNet اختیاری و پیش‌بینی‌های range_1d/range_4h
  را به featureهای آمادهٔ XGBoost/LightGBM تبدیل می‌کند.
- `Phase124` انجام شد: script جدید `train_hybrid_xgboost_head.py` برای آموزش head نهایی
  روی ماتریس فاز ۱۲۳ اضافه شد. خروجی هدف فعلاً SELL/HOLD/BUY است و HOLD نقش NO_TRADE دارد.
- قدم اجرایی بعدی: اول `Build hybrid XGBoost matrix` را اجرا کن تا فایل
  `datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet` ساخته شود؛ سپس `train_hybrid_xgboost_head.py` را اجرا کن.

## External TensorFlow/algo-trading references (فاز ۱۰۶)

- بررسی کامل سه منبع جدید در گزارش `docs/Report/PHASE106_ALPACA_ARI99_ONEPAGECODE_REVIEW_AND_SHADBOT_PLAN.md` ثبت شد.
- repo `ari99/algorithmic_trading` موقتاً برای بررسی clone شد (commit `c8479f3`) و بعد از ثبت گزارش برای خلوت‌کردن workspace حذف شد.
- نتیجهٔ roadmap: تمرکز بعدی باید روی `trend_signal` و event/action classification باشد: class weights، F1/PR-AUC، threshold calibration، feature selection، POS/NEG models و significance checks.
- کپی مستقیم کد توصیه نمی‌شود: Alpaca/Onepagecode آموزشی و TF1 هستند؛ ari99 وابسته به `vectorbtpro` و بدون license واضح است.

## External reference review: Leci37 (فاز ۱۰۵)

- repo مرجع Leci37 موقتاً برای بررسی clone شد (commit `7520351`) و بعد از ثبت گزارش برای خلوت‌کردن workspace حذف شد.
- گزارش کامل: `docs/Report/PHASE105_LECI37_CODE_REVIEW_AND_ADOPTION_PLAN.md`.
- نتیجهٔ تصمیم فنی: از پروژهٔ Leci37 کد را مستقیم وارد production نمی‌کنیم؛ ایده‌های
  event-based GT، POS/NEG binary models، feature selection، class weights/F1،
  threshold calibration، ensemble و profit-aware evaluation قابل استفاده‌اند.
- اولویت بعدی پیشنهادی: تقویت `trend_signal` به جای تکیه روی `trend_score` regression.

## trend_score input scaling (فاز ۱۰۴)

- مدل‌های range/signal/trend همان min-max قدیمی `[-2,+2]` را حفظ می‌کنند.
- `gold_trend_score_*` از این فاز input featureها را per-window به `[-1,+1]`
  scale می‌کند تا بازهٔ ورودی با target bounded score هماهنگ‌تر باشد.
- `input_scale_range` در `ModelRole` و `ModelRecord` ذخیره می‌شود؛ inference،
  `/data` و evaluation همان scale ذخیره‌شده را مصرف می‌کنند.
- resume از checkpoint قدیمی با scale متفاوت برای score رد می‌شود؛ بعد از این
  تغییر trend_score را از صفر train کن، نه resume از مدل `[-2,+2]`.

## trend_score target-integrity audit (فاز ۱۰۳)

- محاسبهٔ score و نرمال‌سازی بررسی شد: target از کندل واقعی بعدی ساخته می‌شود،
  featureها per-window به `[-2,+2]` scale می‌شوند، target داخل input نیست و خودش
  در `[-1,+1]` باقی می‌ماند.
- باگ tail fix شد: ردیف‌های بدون کندل آینده دیگر با `0.0` پر نمی‌شوند؛ با
  `attach_targets` حذف می‌شوند. این پاک‌سازی integrity است، نه ادعای edge جدید.

## trend_score MAE option (فاز ۱۰۲)

- `trend_score` حالا دو objective دارد: `composite` یعنی loss قبلی
  `3*Huber+6*MAE+1*MSE`، و `mae` یعنی MAE خالص.
- برای `trend_score`، monitor خودکار `val_mae` است؛ checkpoint/best epoch،
  EarlyStopping و ReduceLR روی همان MAE تصمیم می‌گیرند.
- GUI فیلد `Trend-score loss` دارد؛ فقط روی model=`trend_score` اثر دارد و
  range/signal/trend را تغییر نمی‌دهد.
- معیار نهایی همچنان باید با baseline ثابت، sign accuracy، corr و stdev خروجی
  سنجیده شود؛ MAE کمتر به‌تنهایی edge معاملاتی را ثابت نمی‌کند.

## GUI / لاگ زنده

- فاز ۱۰۱: Train a model از داخل Dashboard روی Windows دوباره live-log قابل‌اعتماد دارد.
- علت فیکس: `dispatch_async` قبل از redirect وضعیت busy را رزرو می‌کند؛ `_run_script`
  child را با `python -u` و UTF-8 اجباری اجرا می‌کند و فایل `run_logs/train_dual_models.log`
  را با appendهای کوتاه می‌نویسد تا `/api/log` بتواند وسط آموزش بخواند.
- فاز ۱۱۹: فرم‌های طولانی GUI خلوت شدند؛ fieldهای کم‌مصرف/حرفه‌ای حذف نشدند، فقط زیر
  `Advanced options` رفتند. این شامل Train/Retrain/Optimise/Backtest/Replay/Audit/Calibration است.
- اگر آموزش از GUI شروع شود، پنل live output باید ظرف چند ثانیه حداقل خط command،
  سربرگ TRAINING و batch/epoch progress را نشان دهد. اجرای دستی PowerShell همچنان
  جداست و لاگ Dashboard را پر نمی‌کند.

## مسائل شناخته‌شده

- trend_signal مانع باید از ATR(1D) باشد نه ATR(5M) — فیکس شد (فاز ۹۸-ب) ولی مدل باید ریترین شود
- score نزدیک صفر در random walk طبیعی است — لبه واقعی از فیچرها می‌آید
- gold_signal_5m فقط 10 epoch آموزش دیده — ریترین جدی لازم دارد
- ES patience=400 عملاً خاموش است — 15-30 کافی است

## نقشهٔ مدل ترکیبی فعلی

دارایی‌های فعلی که باید محور سیستم باشند:

```text
gold_range_1d  → سقف/کف فردا و daily envelope
gold_range_4h  → سقف/کف چهار ساعت آینده برای TP/SL محلی
gold_trend_signal_lightgbm_basic_5m → multiclass booster SELL/HOLD/BUY
gold_buy_lightgbm_basic_5m → BUY specialist
gold_sell_lightgbm_basic_5m → SELL specialist
gold_trend_signal_5m → WaveNet optional/diagnostic، نه core فعلی
```

مسیر عملیاتی فعلی:

```text
Boosters/Specialists + optional WaveNet + range_1d/range_4h
→ Phase123 hybrid_xgboost_matrix_latest.parquet
→ Phase124 final hybrid XGBoost/LightGBM head
→ Phase125 calibration/backtest با TP/SL واقعی
→ Phase113 significance checks
→ Phase116 live/range-aware integration
```

## آخرین اجرای عملیاتی ثبت‌شده

### Booster multiclass فاز ۱۲۱

```text
model      : gold_trend_signal_lightgbm_basic_5m v1
best strict score : val_action_min_f1_supported = 0.436703
collapse   : 0
```

### BUY/SELL specialists

```text
gold_buy_lightgbm_basic_5m v1:
  best F1=0.612355 · precision=51.98% · recall=74.51%

gold_sell_lightgbm_basic_5m v1:
  best F1=0.680203 · precision=61.03% · recall=76.82%
```

### Phase122 booster-specialist calibration روی holdout

```text
samples=8000
best buy_threshold=0.35
best sell_threshold=0.35
trades=7791
coverage=97.39%
action_precision=48.65%
action_recall=61.02%
action_f1=0.541351
```

نتیجه: threshold خام 0.35/0.35 برای trading نهایی بیش از حد aggressive است؛ نیاز به head نهایی/precision-aware calibration باقی است.

### Phase123 hybrid matrix

```text
path latest : datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
rows        : 8000
columns     : 45
scope       : holdout
labels      : sell=2687, hold=1789, buy=3524
warnings    : []
```

## آخرین اجرای عملیاتی فاز ۱۲۴

```text
model_id      : gold_hybrid_lightgbm_head_5m v1
matrix        : datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
rows/features : 8000 / 36
train/val     : 5600 / 2400
val_accuracy  : 43.79%
balanced_acc  : 46.23%
macro_f1      : 0.4380
buy_sell_f1   : 0.4570
action_min_f1 : 0.4517
action_collapse: 0
predicted classes: 3
SELL P/R/F1   : 48.68% / 44.02% / 0.4623
HOLD P/R/F1   : 30.93% / 56.59% / 0.4000
BUY  P/R/F1   : 55.49% / 38.09% / 0.4517
```

برداشت: مدل hybrid head collapse نکرد و هر سه کلاس را predict کرد. نسبت به booster-only strict score قبلی `0.4367`، معیار ضد-collapse به `0.4517` رسید. این بهبود بزرگ نیست، ولی مسیر hybrid را زنده نگه می‌دارد.

## گام بعدی

1. فاز ۱۲۵ را بسازیم/اجرا کنیم: calibration آستانه‌های hybrid head و backtest با TP/SL واقعی.
2. معیار فاز ۱۲۵ باید trading-aware باشد، نه فقط accuracy/F1:
   `action_precision`, `coverage`, `PnL`, `max_drawdown`, `range_4h TP/SL`, `range_1d envelope`.
3. اگر فاز ۱۲۵ نتیجهٔ مثبت داد، بعد فاز ۱۱۳ significance/random baseline و سپس اتصال production فاز ۱۱۶ انجام شود.

## Phase125 status

فاز ۱۲۵ پیاده‌سازی شد:

```text
scripts/backtest_hybrid_xgboost_head.py
GUI: Backtest hybrid XGBoost head
```

این فاز `gold_hybrid_lightgbm_head_5m` را با threshold grid و TP/SL مبتنی بر `range_4h` و فیلتر room مبتنی بر `range_1d` backtest می‌کند.

گام اجرایی بعدی:

```powershell
python -u scripts/backtest_hybrid_xgboost_head.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --eval-frac 0.30 `
  --threshold-min 0.35 `
  --threshold-max 0.95 `
  --threshold-step 0.05 `
  --min-margin 0 `
  --min-trades 30 `
  --score-metric total_pnl `
  --max-hold-bars 48 `
  --min-4h-room 0 `
  --min-1d-room 0 `
  --min-tp-distance 1 `
  --min-sl-distance 1 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --save-record 1 `
  --storage-root datasets
```

بعد از اجرا، فایل زیر باید ارسال شود:

```text
run_logs/hybrid_head_backtest/latest.json
```


## آخرین اجرای عملیاتی فاز ۱۲۵

### اجرای پایه با `score_metric=total_pnl`

```text
model      : gold_hybrid_lightgbm_head_5m v1
samples    : 2400
best th    : buy=0.80 sell=0.65 margin=0.00
trades     : 344 (coverage=14.33%)
buy/sell   : 170 / 174
wins/losses: 172 / 172
label_precision: 66.57%
total_pnl  : +266.03
avg_pnl    : +0.7733
profit_factor: 1.2199
max_drawdown : 355.58
```

### اجرای محافظه‌کارانه با room filters

تنظیمات:

```text
min_margin=0.05
min_4h_room=2
min_1d_room=5
min_tp_distance=2
min_sl_distance=2
precision_floor=0.55
```

اگر معیار انتخاب فقط `precision_then_pnl` باشد، بهترین منتخب precision بالا ولی PnL کمی منفی داشت:

```text
buy=0.95 sell=0.75
trades=90
label_precision=83.33%
total_pnl=-8.52
profit_factor=0.9719
```

اما بهترین ردیف معاملاتی مثبت در همان grid:

```text
buy=0.80 sell=0.65 margin=0.05
trades=325
win_rate=51.69%
label_precision=65.85%
total_pnl=+291.15
profit_factor=1.2472
max_drawdown=347.04
coverage=13.54%
```

برداشت فعلی: فاز ۱۲۵ edge اولیه نشان داده، اما قبل از live باید threshold مثبت با قیود precision/profit-factor ذخیره شود و سپس significance check اجرا شود.

گام اجرایی پیشنهادی بعدی:

```powershell
python -u scripts/backtest_hybrid_xgboost_head.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --eval-frac 0.30 `
  --threshold-min 0.45 `
  --threshold-max 0.95 `
  --threshold-step 0.05 `
  --min-margin 0.05 `
  --min-trades 100 `
  --precision-floor 0.60 `
  --min-profit-factor 1.05 `
  --score-metric total_pnl `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --save-record 1 `
  --storage-root datasets
```

## Phase125B saved threshold + Phase113 implementation status

کاربر rerun فاز ۱۲۵ را با قیود سخت‌تر اجرا کرد و خروجی نشان می‌دهد threshold سودده در رکورد مدل ذخیره شده است:

```text
model_id        : gold_hybrid_lightgbm_head_5m
model_version   : 1
matrix_rows     : 8000
eval_rows       : 2400
buy_threshold   : 0.80
sell_threshold  : 0.65
min_margin      : 0.05
trades          : 325
buy/sell        : 160 / 165
win_rate        : 51.6923%
label_precision : 65.8462%
total_pnl       : +291.154987683185
avg_pnl         : +0.8958615005636462
profit_factor   : 1.2471739846573604
max_drawdown    : 347.044035279524
coverage        : 13.5417%
record_path     : datasets\models\gold_hybrid_lightgbm_head_5m\v1_training.json
```

فاز ۱۱۳ اکنون برای همین مسیر پیاده‌سازی شده است:

```text
scripts/backtest_significance_check.py
GUI: Check hybrid significance
outputs:
  run_logs/significance_checks/latest.json
  run_logs/significance_checks/latest.csv
```

گام اجرایی فعلی روی ماشین کاربر:

```powershell
python -u scripts/backtest_significance_check.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --trials 1000 `
  --seed 42 `
  --white-check 1 `
  --candidate-rows-path run_logs/hybrid_head_backtest/latest.json `
  --storage-root datasets
```

بعد از اجرا باید `run_logs\significance_checks\latest.json` بررسی شود. اگر p-value بالا باشد، نتیجهٔ فاز ۱۲۵ هنوز فقط exploratory است؛ اگر p-value پایین باشد، قدم بعدی integration/paper در مسیر Phase116 است.

## Phase113 result — significance passed strongly

فاز ۱۱۳ روی threshold ذخیره‌شدهٔ مدل hybrid اجرا شد و نتیجه از random baseline و White-style max check عبور کرد:

```text
threshold_source: model_record:gold_hybrid_lightgbm_head_5m:v1
threshold       : buy=0.80 sell=0.65 margin=0.05
observed_pnl    : +291.154987683185
observed_pf     : 1.2471739846573604
observed_trades : 325
buy/sell        : 160 / 165
win_rate        : 51.6923%
label_precision : 65.8462%
random_mean     : -944.2369557544658
random_p95      : -665.0864972670641
random_p99      : -529.5757005996354
random_max      : -317.02241025066814
random_p_value  : 0.000999000999000999
white_candidates: 23
white_p99       : -128.05536537052174
white_max       : -28.658925889975762
white_p_value   : 0.000999000999000999
```

تصمیم فعلی:

```text
Phase113 برای این holdout پاس شد. گام بعدی مجاز: Phase116 integration برای hybrid range-aware decision path.
هنوز live واقعی مجاز نیست؛ بعد از integration باید Phase115 decision audit و paper/live shadow اجرا شود.
```

## Phase116 status — hybrid range-aware decision integration built

Phase116 v1 پیاده‌سازی شد. مسیر hybrid دیگر فقط research/backtest script نیست و وارد pipeline استاندارد trading decision شده است:

```text
HybridHeadPredictor
→ HybridHeadForecast
→ HybridRangeAwareStrategy
→ PositionAwareDecisionEngine
→ PolicyRiskGate
→ DefaultIntentFactory
→ audit JSON/CSV
```

فایل‌های مهم:

```text
src/ShadBotTrader/domain/ai/prediction_target.py
src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py
src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py
scripts/audit_hybrid_range_aware_decisions.py
```

GUI command جدید:

```text
Audit hybrid range-aware decisions
```

دستور اجرای sanity audit روی ماشین کاربر:

```powershell
python -u scripts/audit_hybrid_range_aware_decisions.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-windows 0 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --capital 10000 `
  --base-quantity 1 `
  --storage-root datasets
```

خروجی مورد انتظار اگر integration با Phase125 هم‌خوان باشد:

```text
trade_intents حدود 325
buy/sell حدود 160/165
label_precision حدود 65.85%
coverage حدود 13.54%
```

بعد از تأیید این audit، قدم بعدی Phase115 live decision audit / paper shadow است. live واقعی هنوز مجاز نیست.

## Phase116 audit result — matched Phase125 exactly

کاربر `scripts/audit_hybrid_range_aware_decisions.py` را اجرا کرد. خروجی runtime integration با Phase125 کاملاً هم‌خوان بود:

```text
threshold_source: model_record:gold_hybrid_lightgbm_head_5m:v1
threshold       : buy=0.80 sell=0.65 margin=0.05
rows            : 2400
trade_intents   : 325
no_trade        : 2075
buy/sell intents: 160 / 165
label_correct   : 214
label_precision : 0.6584615384615384
coverage        : 0.13541666666666666
```

این دقیقاً با بهترین candidate فاز ۱۲۵ یکی است:

```text
Phase125 trades/coverage/precision = 325 / 0.13541666666666666 / 0.6584615384615384
Phase116 intents/coverage/precision = 325 / 0.13541666666666666 / 0.6584615384615384
```

تصمیم فعلی:

```text
Phase116 PASS.
اکنون مسیر hybrid range-aware وارد pipeline واقعی تصمیم شده است.
قدم بعدی Phase115 live decision audit / paper shadow است؛ ارسال order واقعی هنوز مجاز نیست.
```

## Full 5M hybrid backtest report GUI

برای مشاهدهٔ کامل‌تر قبل از Phase115، command/script جدید اضافه شد:

```text
GUI: Full hybrid 5M backtest report
CLI: scripts/report_hybrid_full_backtest.py
outputs:
  run_logs/hybrid_full_backtest/latest.html
  run_logs/hybrid_full_backtest/latest.json
  run_logs/hybrid_full_backtest/latest.csv
```

این script threshold search نمی‌کند؛ threshold ذخیره‌شدهٔ فاز ۱۲۵ را fixed اجرا می‌کند. برای بک‌تست واقعی روی کل دیتای 5M، ابتدا matrix کامل باید ساخته شود:

```text
scripts/build_hybrid_xgboost_matrix.py --scope all --max-windows 0 --output-name hybrid_xgboost_matrix_all_5m
```

سپس report با:

```text
scripts/report_hybrid_full_backtest.py --matrix-path datasets\processed\XAUUSD\5M\hybrid_xgboost_matrix_all_5m.parquet --eval-frac 1.0
```

توجه: full-history report ممکن است in-sample باشد؛ برای تصمیم live، Phase125 holdout + Phase113 significance همچنان معیار اصلی‌اند.

## Full hybrid report now includes candle replay + account balance

`Full hybrid 5M backtest report` فقط summary نیست؛ اکنون در `latest.html` یک replay کندل‌به‌کندل دارد:

```text
slider candle-by-candle
entry marker = circle
exit marker = square
entry line = yellow
TP line = green
SL line = red
balance after closed trades
active trade details
```

پارامترهای سرمایه:

```text
--initial-capital 100
--units 1
```

محاسبه:

```text
final_balance = initial_capital + total_pnl * units
```

برای اکانت 100 دلاری، `units=1` احتمالاً بزرگ است چون max drawdown فاز ۱۲۵ حدود 347 دلار per unit بود. پیشنهاد تست نمایشی امن‌تر:

```text
--units 0.1
```

دستور پیشنهادی برای همان holdout معتبر 325 trade:

```powershell
python -u scripts/report_hybrid_full_backtest.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

خروجی:

```text
run_logs\hybrid_full_backtest\latest.html
run_logs\hybrid_full_backtest\latest.json
```

## Latest hybrid replay result — holdout visual backtest

کاربر HTML replay/full-report را با `initial_capital=100` و `units=0.1` اجرا کرد. این اجرا روی matrix موجود 8000-row و `eval_frac=0.30` بود؛ بنابراین همان holdout 2400-row معتبر است، نه کل تاریخ 5M.

نتیجه:

```text
trades          : 325
buy/sell        : 160 / 165
win_rate        : 51.6923%
label_precision : 65.8462%
total_pnl       : +291.154987683185
profit_factor   : 1.2471739846573604
max_drawdown    : 347.044035279524
coverage        : 13.5417%
```

با capital sizing:

```text
initial_capital   : 100
units             : 0.1
final_balance     : 129.1154987683185
net_profit        : +29.115498768318503
return_percent    : +29.115498768318504%
max_drawdown_cash : 34.7044035279524
would_breach_zero : false
```

خروجی replay:

```text
run_logs\hybrid_full_backtest\latest.html
replay.candles = 2440
replay.trades  = 325
```

تصمیم فعلی:

```text
برای مشاهده و sanity-check، replay holdout خوب است و با Phase125/116 match دارد.
برای بک‌تست کامل کل دیتای 5M، باید نسخهٔ memory-safe/chunked ساخته شود؛ نباید دوباره --scope all --max-windows 0 بدون chunk اجرا شود.
```

## Hybrid replay UI fixed + streamed full 5M mode

Replay HTML سیاه می‌شد چون JSON داخل script با `html.escape` نوشته شده بود و `JSON.parse` در مرورگر fail می‌کرد. رفع شد:

```text
scripts/report_hybrid_full_backtest.py
  script_json() without &quot;
  fallback loading/error SVG
  candle replay slider remains inline/offline
```

برای بک‌تست کامل 5M دیگر نباید matrix کامل با دستور سنگین ساخته شود. حالت stream اضافه شد:

```powershell
python -u scripts/report_hybrid_full_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 1000 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

تفاوت مهم:

```text
source-mode=matrix  → report روی matrix موجود
source-mode=stream  → ساخت/score/backtest chunked روی کل scope انتخابی، بدون ذخیرهٔ matrix عظیم
stream-wavenet=neutral → RAM-safe، WaveNet features = neutral 1/3 چون WaveNet قبلاً no-edge/collapse بود
stream-wavenet=batch   → دقیق‌تر نسبت به WaveNet، اما کندتر و ممکن است سنگین‌تر باشد
```

## Full streamed 5M result — robustness failed

کاربر full 5M streamed replay/backtest را اجرا کرد:

```text
source_mode=stream
stream_scope=all
stream_chunk_size=500
stream_wavenet=neutral
matrix/evaluated rows=52832/52832
threshold=buy 0.80 / sell 0.65 / margin 0.05
```

نتیجه:

```text
trades          : 13757
buy/sell        : 8583 / 5174
win_rate        : 41.2663%
label_precision : 51.1085%
total_pnl       : -43309.811277104236
profit_factor   : 0.6215092452818565
max_drawdown    : 45887.011698256094
coverage        : 26.0391%
```

با capital=100 و units=0.1:

```text
final_balance     : -4230.981127710424
net_profit        : -4330.981127710424
max_drawdown_cash : 4588.701169825609
would_breach_zero : true
```

Monthly فقط 2026-07 مثبت بود:

```text
2026-07 pnl=+2319.21 PF=1.3863
all other months negative
```

تصمیم فعلی:

```text
Fixed threshold/head روی کل تاریخ robustness ندارد.
نباید مدل را روی کل دیتاست train و روی همان data backtest کنیم؛ این leakage است.
گام بعدی درست: Phase126 walk-forward/out-of-time hybrid validation.
```

## Phase126A status — chronological single-position replay built

بعد از اینکه full streamed independent-trade test روی کل 5M شکست خورد، Phase126A پیاده‌سازی شد:

```text
scripts/replay_hybrid_chronological_backtest.py
GUI: Chronological hybrid replay
```

این نسخه با بک‌تست قبلی فرق دارد:

```text
قبلی: هر سیگنال به‌صورت trade مستقل حساب می‌شد.
جدید: کندل‌به‌کندل جلو می‌رود و فقط یک پوزیشن هم‌زمان باز است.
```

قانون:

```text
اگر پوزیشن باز است:
  سیگنال‌های بعدی skip می‌شوند و در chronological.skipped_while_open ثبت می‌شوند.
اگر پوزیشن بسته است:
  hybrid head + range_1d/4h gate ارزیابی می‌شود و در صورت عبور trade باز می‌شود.
```

دستور اجرای کامل memory-safe:

```powershell
python -u scripts/replay_hybrid_chronological_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 500 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

بعد از اجرا باید بررسی شود:

```text
run_logs\hybrid_chronological_backtest\latest.json
run_logs\hybrid_chronological_backtest\latest.html
```

اگر این هم روی کل تاریخ شکست بخورد، گام بعدی Phase126B walk-forward/out-of-time validation است.

## Roadmap locked before Phase127 implementation

ایدهٔ جدید کاربر به فازهای جداگانه تبدیل و ثبت شد تا چیزی گم نشود. مسیر آینده:

```text
Phase126A — chronological single-position replay   [implemented]
Phase127  — causal 3D telemetry tensor with Target C
Phase128  — LightGBM/CatBoost meta-labeler baseline
Phase129  — WaveNet/TCN on telemetry tensor
Phase130  — TSMixer benchmark
Phase131  — PatchTST benchmark
Phase132  — meta-filtered chronological backtest comparison
Phase133  — walk-forward/out-of-time validation
Phase134  — production consolidation / online bot assembly
Phase115  — live decision audit / paper shadow after consolidation
```

Key decisions:

```text
safe_lag = 48 bars
Target C = target_trade_win + target_trade_score_r + target_trade_pnl
3D tensor = [samples, tensor_window, channels]
4H/1D features enter as aligned channels, using only closed higher-timeframe candles
WaveNet phase exists as Phase129, but it is a new telemetry-target WaveNet/TCN, not the old collapsed trend_signal model
```

Production complexity concern:

```text
Phase134 is explicitly reserved for simplifying/consolidating the final online bot path. If a model stack passes validation, live code must be one narrow service/config path, not a pile of research scripts.
```

## GUI execution rule for all upcoming executable phases

از این نقطه به بعد، CLI-only برای فازهای اجرایی قابل قبول نیست. هر فاز آینده که نیاز به اجرای اپراتور دارد باید Dashboard/GUI command داشته باشد.

ثبت‌شده در:

```text
Phase115
Phase126
Phase127
Phase128
Phase129
Phase130
Phase131
Phase132
Phase133
Phase134
```

حداقل الزامات هر فاز اجرایی:

```text
CommandKind
CommandDescriptor
Handler
advanced fields برای پارامترهای تخصصی
unit/integration GUI tests
```

این قانون برای جلوگیری از پیچیده‌شدن workflow و وابستگی به دستورهای دستی ثبت شد.

## Phase127A built — causal telemetry tensor builder

Phase127A پیاده‌سازی شد:

```text
scripts/build_hybrid_telemetry_tensor.py
GUI: Build hybrid telemetry tensor
```

خروجی‌ها:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_v1.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
run_logs\hybrid_telemetry_tensor\latest.json
```

ویژگی‌ها:

```text
Target C: target_trade_win + target_trade_score_r + target_trade_pnl
safe_lag_bars=48
3D tensor: X=[samples, tensor_window, channels]
source-mode matrix|stream
max_tensor_mb guard
GUI command موجود است
```

اولین اجرای پیشنهادی کاربر باید matrix-mode باشد. بعد از دیدن `latest.json`، اگر shape/candidate/target stats درست بود، اجرای stream full با stride/max_samples انجام شود.

راهنمای کامل ترتیب اجرا:

```text
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

## Phase128A built — hybrid meta-labeler baseline

Phase128A پیاده‌سازی شد:

```text
scripts/train_hybrid_meta_labeler.py
scripts/backtest_hybrid_meta_labeler.py
GUI: Train hybrid meta-labeler
GUI: Backtest hybrid meta-labeler
```

پیش‌نیاز:

```text
Phase127A باید hybrid_telemetry_flat_latest.parquet را ساخته باشد.
```

مدل پیشنهادی اول:

```text
gold_hybrid_meta_lightgbm_5m
```

Target اول:

```text
target_trade_win
```

بعد از train، backtest meta-filtered روی telemetry candidates اجرا می‌شود و خروجی‌ها:

```text
run_logs\hybrid_meta_labeler\latest.json
run_logs\hybrid_meta_backtest\latest.json
run_logs\hybrid_meta_backtest\latest.html
run_logs\hybrid_meta_backtest\latest.csv
```

راهنمای اجرای ترتیب فردا:

```text
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

## Phase129A built — telemetry WaveNet/TCN

Phase129A پیاده‌سازی شد:

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
GUI: Train telemetry WaveNet/TCN
GUI: Backtest telemetry WaveNet/TCN
```

این فاز تکرار WaveNet قبلی نیست. ورودی آن Phase127 tensor است:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
```

قابلیت‌ها:

```text
task=classifier|regressor|multihead
causal dilated Conv1D/TCN
train-only scaler
purge_gap default=336
artifact format=pickle_keras with scaler metadata
backtest decision_mode=meta|score|both
```

برای اجرا باید TensorFlow نصب باشد:

```powershell
python -m pip install -r requirements-ai.txt
```

بعد از train/backtest باید این فایل‌ها ارسال شوند:

```text
run_logs\hybrid_telemetry_wavenet\latest.json
run_logs\hybrid_telemetry_wavenet_backtest\latest.json
```

راهنمای کامل اجرا:

```text
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

## Phase130A built — telemetry TSMixer benchmark

Phase130A پیاده‌سازی شد:

```text
scripts/train_hybrid_telemetry_tsmixer.py
scripts/backtest_hybrid_telemetry_tsmixer.py
GUI: Train telemetry TSMixer
GUI: Backtest telemetry TSMixer
```

ورودی:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

قابلیت‌ها:

```text
task=classifier|regressor|multihead
TSMixer time-mixing + feature-mixing blocks
train-only scaler
purge_gap default=336
backtest decision_mode=meta|score|both
```

بعد از train/backtest باید ارسال شود:

```text
run_logs\hybrid_telemetry_tsmixer\latest.json
run_logs\hybrid_telemetry_tsmixer_backtest\latest.json
```

راهنمای کامل اجرا:

```text
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

## Phase131A built — telemetry PatchTST benchmark

Phase131A پیاده‌سازی شد:

```text
scripts/train_hybrid_telemetry_patchtst.py
scripts/backtest_hybrid_telemetry_patchtst.py
GUI: Train telemetry PatchTST
GUI: Backtest telemetry PatchTST
```

ورودی:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

قابلیت‌ها:

```text
task=classifier|regressor|multihead
PatchTST temporal patches + Transformer encoder
train-only scaler
purge_gap default=336
backtest decision_mode=meta|score|both
```

بعد از train/backtest باید ارسال شود:

```text
run_logs\hybrid_telemetry_patchtst\latest.json
run_logs\hybrid_telemetry_patchtst_backtest\latest.json
```

راهنمای کامل اجرا:

```text
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

## Phase132A built — meta-filtered hybrid comparison

Phase132A پیاده‌سازی شد:

```text
scripts/backtest_meta_filtered_hybrid.py
GUI: Backtest meta-filtered hybrid
```

کاربرد:

```text
مقایسه base hybrid candidates با meta-filterهای Phase128/129/130/131 روی همان chronological replay.
```

خروجی‌ها:

```text
run_logs\hybrid_meta_comparison\latest.json
run_logs\hybrid_meta_comparison\latest.csv
run_logs\hybrid_meta_comparison\latest.html
run_logs\hybrid_meta_comparison\best_replay.html
```

ویژگی مهم:

```text
skip_missing=1 پیش‌فرض است، پس اگر هنوز بعضی مدل‌ها train نشده باشند comparison فقط آن‌ها را skipped ثبت می‌کند.
```

راهنمای اجرا:

```text
docs/Phases/PHASE127_134_EXECUTION_ORDER.md
```

## Phase133A built — flat meta-labeler walk-forward validation

Phase133A پیاده‌سازی شد:

```text
scripts/run_hybrid_walk_forward_validation.py
GUI: Run hybrid walk-forward validation
```

کاربرد:

```text
برای هر test month، فقط گذشته train می‌شود، فقط validation گذشته threshold انتخاب می‌کند، و ماه آینده test می‌شود.
```

محدودهٔ فعلی:

```text
flat telemetry booster meta-labeler از Phase128
```

خروجی:

```text
run_logs\hybrid_walk_forward_validation\latest.json
run_logs\hybrid_walk_forward_validation\latest.csv
run_logs\hybrid_walk_forward_validation\latest.html
```

اگر این مرحله شکست بخورد، Phase134/production نباید اجرا شود. باید برگردیم به feature/regime/threshold/model اصلاحی.

## Phase134A built — production validation + paper shadow scaffold

Phase134A پیاده‌سازی شد:

```text
src/ShadBotTrader/application/services/hybrid_production_service.py
scripts/validate_production_hybrid_stack.py
scripts/run_hybrid_paper_shadow.py
GUI: Validate production hybrid stack
GUI: Run hybrid paper shadow
```

خروجی validation:

```text
run_logs\hybrid_production_validation\latest.json
configs\hybrid_production_stack.json
```

خروجی paper shadow:

```text
run_logs\hybrid_paper_shadow\latest.json
run_logs\hybrid_paper_shadow\latest.csv
run_logs\hybrid_paper_shadow\latest.html
```

ایمنی:

```text
run_hybrid_paper_shadow.py هیچ order واقعی نمی‌فرستد و اگر config.mode=live باشد اجرا را رد می‌کند.
Live واقعی همچنان تا بعد از Phase115 ممنوع است.
```

Phase134A فعلاً scaffold است. بعد از Phase133 اگر یک candidate واقعاً قبول شود، همین config با مدل منتخب freeze می‌شود و سپس Phase115 live decision audit/paper shadow انجام می‌شود.

## Latest execution result — Phase126A failed; Phase127 timestamp bug fixed

Phase126A chronological full 5M result from user:

```text
rows            : 52832
trades          : 1693
buy/sell        : 1118 / 575
win_rate        : 30.2422%
label_precision : 47.6669%
total_pnl       : -4590.797210656048
profit_factor   : 0.5787103197097719
max_drawdown    : 4590.797210656047
coverage        : 3.2045%
final_balance   : -359.0797210656049  # initial=100, units=0.1
would_breach_zero: true
```

Conclusion:

```text
Base hybrid fixed-threshold fails full chronological replay. Continue with telemetry/meta-filter/walk-forward; do not go live.
```

Phase127A first matrix-mode run failed with:

```text
TypeError: '<' not supported between instances of 'str' and 'datetime.datetime'
```

Fix committed in `scripts/build_hybrid_telemetry_tensor.py`:

```text
matrix timestamp strings are converted to UTC pandas Timestamp before latest-closed 4H/1D lookup.
```

Next user action:

```text
rerun Phase127A matrix-mode command exactly as before.
Then send run_logs\hybrid_telemetry_tensor\latest.json
```

## Phase127A matrix-mode execution succeeded

کاربر Phase127A را با `source_mode=matrix` اجرا کرد و خروجی ساختاراً سالم بود:

```text
rows               : 8000
tensor_samples     : 7851
tensor_shape       : [7851, 150, 94]
channels           : 94
candidate_rows     : 2307
candidate_rate     : 28.8375%
target_win_rate    : 57.2605%
target_score_r_mean: +0.07910706847906113
target_pnl_sum     : +3714.10546875
warnings           : []
```

فایل‌های ساخته‌شده:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
```

تفسیر:

```text
Phase127A PASS از نظر data build. اما این matrix-mode فقط 8000 ردیف دارد و validation نیست. گام بعدی Phase128A است.
```

## Latest Phase128A train result — LightGBM meta-labeler v1

کاربر Phase128A classifier را train کرد:

```text
model_id       : gold_hybrid_meta_lightgbm_5m
version        : 1
rows           : 2307 candidate rows
features       : 94
train/val/test : 1614 / 346 / 347
record_path    : datasets\models\gold_hybrid_meta_lightgbm_5m\v1_training.json
```

نتیجه:

```text
validation AP  : 0.7864 vs base_rate 0.6445
validation precision/recall/F1 @0.55: 0.6572 / 0.9372 / 0.7726
validation positive_rate @0.55: 91.91%

test AP        : 0.6190 vs base_rate 0.4841
test precision/recall/F1 @0.55: 0.4955 / 0.9940 / 0.6614
test positive_rate @0.55: 97.12%
```

Interpretation:

```text
Ranking signal exists (AP > base_rate), but threshold=0.55 is too permissive and almost does not filter on test.
```

Next action:

```text
Run Phase128A backtest with saved threshold first, then Phase132A threshold grid.
```

## Latest Phase128A backtest result — positive but month-concentrated

کاربر Phase128A backtest را اجرا کرد:

```text
model              : gold_hybrid_meta_lightgbm_5m v1
threshold          : meta=0.55 from model_record
rows/evaluated     : 8000 / 8000
trades             : 143
buy/sell           : 74 / 69
win_rate           : 65.7343%
total_pnl          : +509.5359231829643
profit_factor      : 2.608242691826868
max_drawdown       : 91.44515466690063
coverage           : 1.7875%
final_balance      : 150.95359231829644  # initial=100, units=0.1
max_drawdown_cash  : 9.144515466690065
would_breach_zero  : false
```

Monthly:

```text
2026-07: +526.1065, 60/60 wins, PF=999
2026-08: -16.5706, 34/83 wins, PF=0.9477
```

Interpretation:

```text
Meta-filter is clearly useful on this 8000-row matrix, but profit is highly concentrated in July. Need Phase132 threshold grid and Phase133 walk-forward before trusting it.
```

Next action:

```text
Run Phase132A comparison/threshold grid.
```

## Phase132A best replay bug fixed

کاربر Phase132A را با candidates `base,gold_hybrid_meta_lightgbm_5m` اجرا کرد و خطا گرفت:

```text
AttributeError: 'ComparisonRow' object has no attribute 'label_correct'
```

رفع شد:

```text
BestReplay now stores the original FixedBacktestSummary.
best_replay.html uses replay.summary instead of reconstructing summary from ComparisonRow.
```

کاربر باید همان Phase132A command قبلی را دوباره اجرا کند و ارسال کند:

```text
run_logs\hybrid_meta_comparison\latest.json
```

## Latest Phase132A result — meta-filter strongly improves 8000-row replay

Phase132A threshold grid نتیجه داد:

```text
Base:
trades=219, win_rate=42.47%, total_pnl=+55.1465, PF=1.0678, DD=98.2513

Best meta:
candidate=gold_hybrid_meta_lightgbm_5m:meta:meta=record:score=0.0
threshold=0.55
trades=142, win_rate=65.49%, total_pnl=+502.8292, PF=2.5871, DD=91.4452
final_balance=150.2829 with initial=100 and units=0.1
```

Grid summary:

```text
0.55: +502.83 PF=2.587 trades=142
0.60: +488.53 PF=2.552 trades=140
0.65: +481.79 PF=2.541 trades=138
0.70: +467.51 PF=2.507 trades=136
0.75: +446.61 PF=2.450 trades=131
0.80: +420.53 PF=2.365 trades=130
```

Interpretation:

```text
Meta-filter works on the 8000-row matrix, but this is not final validation because it is not full-history walk-forward. Next build full stream telemetry, retrain meta, then run Phase133A walk-forward.
```

## Latest implementation fix — Phase127A stream same-bar-policy — 2026-09-12

The operator's full stream Phase127A run stopped after the first chunk:

```text
stream rows : 500/52,832
[X] AttributeError: 'Namespace' object has no attribute 'same_bar_policy'
```

Implemented fix:

```text
scripts/build_hybrid_telemetry_tensor.py
  added --same-bar-policy {stop_first,tp_first}, default=stop_first

Dashboard / GUI
  Build hybrid telemetry tensor now exposes Same-bar policy and forwards --same-bar-policy
```

Additional stream consistency correction:

```text
stream-mode lagged trade telemetry is recomputed globally after all chunks are concatenated,
so lagged_trade_count and rolling win-rate features do not reset every stream_chunk_size rows.
```

Verification status:

```text
Targeted ruff/black: PASS
Targeted tests: 65 passed
Full pytest: 1760 passed, 54 skipped
Full ruff/black/mypy: still fail from pre-existing repo debt.
```

Next required operator action remains:

```text
Rerun Phase127A full stream telemetry with the same command.
Optional explicit addition: --same-bar-policy stop_first
```

## Latest execution result — full stream telemetry + Phase133 walk-forward — 2026-09-12

Phase127A full stream telemetry succeeded:

```text
rows                : 52832
tensor_samples      : 10537
tensor_shape        : [10537, 150, 94]
candidate_rows      : 13757
candidate_rate      : 26.0391%
target_win_rate     : 41.2663%
target_score_r_mean : -0.23007889091968536
target_pnl_sum      : -43309.8125
warnings            : []
```

Phase128A retrain on full stream telemetry produced:

```text
model_id         : gold_hybrid_meta_lightgbm_5m
version          : 2
rows             : 13757
train/val/test   : 9629 / 2064 / 2064
val AP/base      : 0.6117950637217242 / 0.4806201550387597
test AP/base     : 0.7147311817866087 / 0.5184108527131783
test precision   : 0.6214614878209348
test recall      : 0.8822429906542056
```

Phase133A walk-forward result:

```text
folds                  : 6
positive_months        : 1
negative_months        : 4
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : -387.9482191801071
meta_profit_factor     : 0.764435361497561
meta_max_drawdown      : 460.49957263469696
meta_trades            : 288
meta_final_balance     : 61.20517808198929
meta_would_breach_zero : false
```

Current decision:

```text
Phase133A FAILED. The full-stream flat LightGBM meta-filter reduces losses versus base but does not generalize into a profitable out-of-time strategy.
No Phase134 paper shadow, no live trading, and no production acceptance from this candidate.
```

Recommended next research direction:

```text
1) Run a full-stream Phase132A comparison for v2 to confirm in-sample full-history behaviour.
2) Run Phase133A diagnostic variants with stricter meta_thresholds, class_weight=off, and drawdown_adjusted scoring.
3) If flat model still fails, evaluate Phase129/130/131 telemetry tensor models only in walk-forward mode before any deployment discussion.
```

## Latest implementation fix — negative score-threshold argv parsing — 2026-09-12

The first Phase133A regressor command failed before execution because the score-threshold grid started with a negative value:

```text
--score-thresholds -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
error: argument --score-thresholds: expected one argument
```

Fix implemented:

```text
scripts/run_hybrid_walk_forward_validation.py
scripts/backtest_meta_filtered_hybrid.py
```

Both scripts now normalize `--score-thresholds` / `--meta-thresholds` before argparse, so negative comma-separated threshold grids work in both CLI and Dashboard execution.

Immediate workaround for any checkout without this patch:

```powershell
--score-thresholds=-0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
```

## Latest execution result — Phase133A regressor walk-forward — 2026-09-12

The operator ran the next diagnostic Phase133A variant:

```text
task             : regressor
target           : target_trade_score_r
score_thresholds : -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
score_metric     : total_pnl
```

Aggregate result:

```text
folds                  : 6
positive_months        : 2
negative_months        : 3
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : +8.10892242193222
meta_profit_factor     : 1.0127550914970576
meta_max_drawdown      : 183.82112050056458
meta_trades            : 120
meta_avg_pnl           : +0.06757435351610183
meta_final_balance     : 100.81089224219322
meta_return_percent    : +0.8108922421932221%
meta_would_breach_zero : false
```

Decision:

```text
Phase133A regressor is materially better than the classifier and base hybrid, but it is still NOT accepted. It is near break-even, PF is only 1.0128, and month stability is weak.
No Phase134 paper shadow/live trading is allowed.
```

Owner-control documentation added:

```text
docs/PROJECT_OWNER_MAP.html
```

This is now the mandatory graphical owner-facing project map and must be updated after every meaningful code/result/phase/decision change.

## Latest implementation update — tensor visual inspector and full-window build command — 2026-09-12

A visual inspector was added so the owner can understand the Phase127A 3D telemetry tensor without reading raw `.npz` arrays:

```text
scripts/inspect_hybrid_telemetry_tensor.py
GUI: Inspect hybrid telemetry tensor
Output: run_logs\hybrid_tensor_inspector\latest.html
```

The inspector shows:

```text
- tensor shape / dtype / estimated uncompressed size
- axis meanings: samples × 150-candle time window × 94 channels
- channel groups
- selected samples as heatmap slices
- target values for each selected sample
```

Important tensor status clarification:

```text
The current tensor with shape [10537, 150, 94] spans all 52,832 5M rows, but it samples every fifth possible window because sample_stride=5.
A complete every-window tensor requires sample_stride=1 and max_samples=0, producing approximately [52683, 150, 94].
```

## Current tensor-to-WaveNet clarification — 2026-09-12

The full 3D telemetry tensor has now been built and inspected:

```text
X shape                  : [52683, 150, 94]
dtype                    : float16
estimated X size          : 1416.8363571166992 MiB
source rows               : 52832
sample_stride             : 1
max_samples               : 0
warnings                  : []
visual inspector output   : run_logs\hybrid_tensor_inspector\latest.html
```

The WaveNet model intended to consume this tensor is Phase129A:

```text
trainer      : scripts/train_hybrid_telemetry_wavenet.py
backtester   : scripts/backtest_hybrid_telemetry_wavenet.py
GUI train    : Train telemetry WaveNet/TCN
GUI backtest : Backtest telemetry WaveNet/TCN
model id     : gold_hybrid_telemetry_wavenet_5m
```

Target design:

```text
Recommended first task: multihead
head meta_win -> predicts target_trade_win
head score_r  -> predicts target_trade_score_r
```

Trading interpretation:

```text
target_trade_score_r is the more important target for execution quality because win-only classification failed Phase133A, while score_r regression reached near break-even. WaveNet should be trained multihead first, then backtested with decision_mode=score and decision_mode=both.
```

## Current WaveNet training status clarification — 2026-09-12

The operator started Phase129A WaveNet/TCN training on the full tensor with:

```text
tensor shape before candidate filter : [52683, 150, 94]
task                                 : multihead
candidate_only                        : 1
epochs                                : 500
early_stopping_patience               : 8
monitor                               : val_loss
observed model input shape             : [13692, 150, 94]
split                                 : 9584 / 1718 / 1718
```

Interpretation:

```text
The observed [13692, 150, 94] input shape is expected because candidate_only=1 keeps only trade-candidate windows from the full tensor.
The script is not monthly roll-forward. It is a chronological train/validation/test split with purge_gap=336.
This is acceptable for first artifact training, but not sufficient for production acceptance.
```

Required validation if initial WaveNet looks promising:

```text
Run backtest_hybrid_telemetry_wavenet.py first, then build/run tensor-model walk-forward validation before any Phase134/paper/live discussion.
```

## Latest execution result — Phase129A WaveNet/TCN v1 — 2026-09-12

The operator trained the Phase129A telemetry WaveNet/TCN on the full 3D tensor:

```text
model_id       : gold_hybrid_telemetry_wavenet_5m
version        : 1
task           : multihead
tensor_path    : datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
selected rows  : 13692 candidate tensor windows
tensor_window  : 150
channels       : 94
train/val/test : 9584 / 1718 / 1718
purge_gap      : 336
epochs arg     : 500
early stopping : 8
```

Key training metrics:

```text
val_meta_ap              : 0.5189458439202039
test_meta_ap             : 0.5377916962550442
val_meta_prob_stdev      : 0.2892801567904343
test_meta_prob_stdev     : 0.2399177476745701
val_meta_collapse        : 0.0
test_meta_collapse       : 0.0
val_score_mae            : 0.8421052456884921
test_score_mae           : 0.8726781023827808
val_score_pred_stdev     : 0.47359669000282073
test_score_pred_stdev    : 0.37248512880185
val_score_collapse       : 0.0
test_score_collapse      : 0.0
test_score_selected_rate : 0.27648428405122233
test_score_selected_target_mean : +0.1913444548845291
```

Initial score-mode full replay:

```text
script        : scripts/backtest_hybrid_telemetry_wavenet.py
decision_mode : score
score_threshold : 0
eval_frac     : 1.0
rows          : 52683 / 52683
trades        : 384
coverage      : 0.73%
skipped_nn    : 9520
total_pnl     : +1914.66
profit_factor : 2.604
final_balance : 291.47 with initial=100 and units=0.1
```

Interpretation:

```text
This is the first strong result from the 3D tensor path. The WaveNet did not collapse and the score head appears useful.
However, this is not final production proof because the replay used eval_frac=1.0 and therefore includes in-sample training-era windows. The next validation must isolate out-of-time windows and then implement tensor-model walk-forward validation if still promising.
```

## Latest execution result — WaveNet v1 full and last-15% replays — 2026-09-12

The operator sent the full JSON for Phase129A WaveNet/TCN v1 score-mode replay and a last-15% replay.

Full replay (`eval_frac=1.0`):

```text
rows/evaluated  : 52683 / 52683
trades          : 384
buy/sell        : 215 / 169
wins/losses     : 242 / 142
win_rate        : 63.0208%
total_pnl       : +1914.6646151691675
avg_pnl         : +4.986105768669707
profit_factor   : 2.603926956615171
max_drawdown    : 192.19346404075623
coverage        : 0.7289%
final_balance   : 291.46646151691675 at initial=100, units=0.1
```

Full replay monthly distribution:

```text
2025-12: +205.6134 PF=4.4145 trades=51
2026-01: +257.9868 PF=3.5067 trades=44
2026-02: +463.7281 PF=2.5933 trades=46
2026-03: +668.7947 PF=7.0685 trades=49
2026-04: +328.4646 PF=9.8534 trades=36
2026-05:   -4.2993 PF=0.9819 trades=63
2026-06:  -49.7058 PF=0.6996 trades=38
2026-07:  +78.6255 PF=1.5753 trades=48
2026-08:  -34.5435 PF=0.3365 trades=9
```

Last-15% replay (`eval_frac=0.15`):

```text
rows/evaluated  : 52683 / 7902
trades          : 29
buy/sell        : 6 / 23
wins/losses     : 16 / 13
win_rate        : 55.1724%
total_pnl       : +29.590763092041016
avg_pnl         : +1.0203711411048626
profit_factor   : 1.316544651614474
max_drawdown    : 52.06632328033447
coverage        : 0.3670%
final_balance   : 102.95907630920411 at initial=100, units=0.1
```

Last-15% monthly distribution:

```text
2026-07: +64.1343 PF=2.5486 trades=20
2026-08: -34.5435 PF=0.3365 trades=9
```

Interpretation:

```text
WaveNet v1 is promising: it did not collapse and the last-15% proxy remains positive with PF=1.3165. But it is fragile: only 29 trades, August is negative, and the full replay profit is heavily concentrated in the earlier train-era months. Production/paper remains blocked until threshold robustness and tensor walk-forward validation pass.
```

## Latest execution result — Phase129A WaveNet/TCN v2 long train — 2026-09-13

The operator ran a longer score-focused WaveNet/TCN configuration:

```text
model_id             : gold_hybrid_telemetry_wavenet_5m
version              : 2
task                 : multihead
rows                 : 13692 candidate tensor windows
train/val/test        : 9584 / 1718 / 1718
filters              : 64
n_layers             : 6
n_blocks             : 2
dense_units          : 96
dropout              : 0.25
learning_rate        : 0.0005
score_loss_weight    : 1.0
monitor_metric       : val_score_r_mae
early_stopping       : 25
```

Comparison against v1 key metrics:

```text
v1 test_meta_ap                      : 0.5377916962550442
v2 test_meta_ap                      : 0.4581884952337111

v1 test_score_mae                    : 0.8726781023827808
v2 test_score_mae                    : 0.9537305706318867

v1 test_score_selected_rate          : 0.27648428405122233
v2 test_score_selected_rate          : 0.459837019790454

v1 test_score_selected_target_mean   : +0.1913444548845291
v2 test_score_selected_target_mean   : -0.13298217952251434
```

Decision:

```text
v2 is worse than v1 on the test split. It did not collapse, but the score-selected test subset became negative and selected too many candidates. Treat as overfit/regime-mismatch until a threshold backtest proves otherwise. Do not replace v1 as the preferred WaveNet candidate.
```

Operator command error:

```text
backtest_hybrid_telemetry_wavenet.py: error: unrecognized arguments: -u scripts/backtest_hybrid_telemetry_wavenet.py
```

Cause:

```text
The second `python -u scripts/backtest_hybrid_telemetry_wavenet.py` command was accidentally pasted directly after `--storage-root datasets`, so argparse received it as extra arguments to the first script.
```

Correct action:

```text
Run one command at a time. To backtest v2 explicitly, use --model-version 2. To preserve the stronger v1 baseline, use --model-version 1 instead of --model-version 0, because 0 now resolves to latest=v2.
```

## Latest execution result — Phase129A WaveNet/TCN v2 last-15% backtest — 2026-09-13

The operator explicitly backtested `gold_hybrid_telemetry_wavenet_5m v2` on the last 15% of the tensor with score-mode:

```text
model_version  : 2
decision_mode  : score
score_threshold: 0.0
eval_frac      : 0.15
rows/evaluated : 52683 / 7902
```

Result:

```text
trades          : 89
buy/sell        : 58 / 31
wins/losses     : 29 / 60
timeouts        : 2
win_rate        : 32.5843%
total_pnl       : -178.49363827705383
avg_pnl         : -2.005546497494987
profit_factor   : 0.5542918793438448
max_drawdown    : 212.62753653526306
coverage        : 1.1263%
final_balance   : 82.15063617229461 at initial=100, units=0.1
```

Monthly:

```text
2026-07:   -3.3839 PF=0.9646 trades=31
2026-08: -168.3904 PF=0.4355 trades=56
2026-09:   -6.7193 PF=0.0000 trades=2
```

Comparison to v1 last-15%:

```text
v1 last-15%: +29.5908 raw PnL, PF=1.3165, trades=29, maxDD=52.0663
v2 last-15%: -178.4936 raw PnL, PF=0.5543, trades=89, maxDD=212.6275
```

Decision:

```text
REJECT v2 as the active WaveNet candidate. v2 overtrades and fails the out-of-time proxy. v1 remains the better WaveNet candidate, but still needs threshold robustness and tensor walk-forward validation before any production/paper step.
```

## Latest execution result — Phase132A WaveNet v1 threshold grid on last-15% — 2026-09-13

The operator ran Phase132A comparison on the last 15% tensor universe with:

```text
candidates          : base,gold_hybrid_telemetry_wavenet_5m
candidate_versions  : 0,1
decision_modes      : score,both
meta_thresholds     : record,0.55,0.60,0.65,0.70
score_thresholds    : -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50,0.75,1.00
eval_frac           : 0.15
samples             : 7902
score_metric        : total_pnl
```

Base result on the same last-15% universe:

```text
trades          : 195
buy/sell        : 127 / 68
wins/losses     : 67 / 128
win_rate        : 34.35897435897436%
total_pnl       : -247.1424761712551
profit_factor   : 0.70282875694799
max_drawdown    : 272.11317190527916
coverage        : 2.4677296886864084%
final_balance   : 75.28575238287449
```

Best WaveNet v1 threshold-grid result:

```text
candidate        : gold_hybrid_telemetry_wavenet_5m:score:meta=record:score=0.05
version          : 1
model_type       : tensor
decision_mode    : score
score_threshold  : 0.05
trades           : 22
buy/sell         : 5 / 17
wins/losses      : 14 / 8
win_rate         : 63.63636363636364%
total_pnl        : +42.78727626800537
avg_pnl          : +1.9448761940002441
profit_factor    : 1.6478747062665267
max_drawdown     : 32.968711853027344
coverage         : 0.27841052898000505%
final_balance    : 104.27872762680053
```

Threshold shape:

```text
score=-0.25 -> -117.3837, PF=0.6991, trades=91
score=-0.10 ->  -55.0679, PF=0.7756, trades=56
score= 0.00 ->  +29.5908, PF=1.3165, trades=29
score= 0.05 ->  +42.7873, PF=1.6479, trades=22  BEST
score= 0.10 ->  +35.4562, PF=1.7217, trades=18
score= 0.20 ->   +8.3745, PF=2.2427, trades=5   below min_trades
score>=0.35 -> too few trades / negative or zero
```

Interpretation:

```text
WaveNet v1 score filtering materially improves the base hybrid on the last-15% diagnostic window. The useful threshold region is narrow but intuitive: score_threshold around 0.00-0.10, with 0.05 best by total PnL and 0.10 lower drawdown.
```

Important caveats:

```text
- In decision_mode=score, meta_threshold is ignored by design; repeated score-mode rows across meta thresholds are expected duplicates.
- The best threshold was selected on the last-15% evaluation window, so this is a diagnostic threshold grid, not production validation.
- Only 22 trades at the best threshold; sample size is still small.
- Phase134 paper/live remains blocked until tensor walk-forward validation selects thresholds only from past validation data and passes out-of-time test months.
```

## Latest implementation update — Phase133B tensor walk-forward validation — 2026-09-13

Implemented the missing tensor-model walk-forward validation phase:

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
GUI: Run tensor walk-forward validation
```

Why:

```text
WaveNet v1 on the 3D telemetry tensor produced a strong diagnostic last-15% threshold-grid result, but the threshold was selected on the same evaluation slice. A true production gate needs threshold selection on past validation only and testing on unseen future months.
```

Current model family implemented:

```text
model_family=wavenet
```

Protocol:

```text
train fresh WaveNet/TCN per test month
train rows = only months before validation block
validation rows = immediate month(s) before test month
test rows = next unseen month
purge_gap_bars = 336
threshold grid selected only on validation replay
selected threshold evaluated on test replay
```

Outputs:

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
run_logs\hybrid_tensor_walk_forward_validation\latest.csv
run_logs\hybrid_tensor_walk_forward_validation\latest.html
```

Phase134 remains blocked until this passes.

## Latest execution result — Phase133B tensor WaveNet walk-forward FAILED — 2026-09-13

The operator ran the new tensor-model walk-forward validation:

```text
script             : scripts/run_hybrid_tensor_walk_forward_validation.py
model_family       : wavenet
task               : multihead
candidate_only     : 1
train_months_min   : 3
validation_months  : 1
purge_gap_bars     : 336
decision_modes     : score,both
score_thresholds   : -0.10,0,0.05,0.10,0.20
score_metric       : total_pnl
```

Aggregate result:

```text
folds                  : 6
test_months            : 6
positive_months        : 2
negative_months        : 3
base_total_pnl         : -1288.8456037938595
tensor_total_pnl       : -409.51990616321564
tensor_gross_profit    : 608.841717839241
tensor_gross_loss      : 1018.3616240024567
tensor_profit_factor   : 0.5978639645181408
tensor_max_drawdown    : 464.1122056245804
tensor_trades          : 200
tensor_avg_pnl         : -2.047599530816078
tensor_final_balance   : 59.04800938367843
tensor_return_percent  : -40.951990616321565%
tensor_would_breach_zero : false
best_month             : 2026-08
worst_month            : 2026-05
```

Fold results:

```text
2026-04: selected score 0.05, val=-102.5548, tensor=-144.8683, PF=0.3253, trades=35
2026-05: selected score -0.10, val= -42.2108, tensor=-270.3103, PF=0.5553, trades=115
2026-06: selected both meta=0.70 score=0.20, val=-107.0676, tensor= +7.8459, PF=1.0769, trades=25
2026-07: selected both meta=0.65 score=0.05, val= +26.0419, tensor=-23.4140, PF=0.4207, trades=8
2026-08: selected both meta=0.65 score=-0.10, val= +44.9376, tensor=+21.2268, PF=1.3981, trades=17
2026-09: selected score 0.20, val= +44.3921, tensor= +0.0000, PF=0.0000, trades=0
```

Decision:

```text
FAIL. The 3D tensor WaveNet v1 diagnostic signal did not generalize under true walk-forward retraining and validation-selected thresholds.
```

Interpretation:

```text
- The tensor model reduced base loss (-409.52 vs -1288.85), but remained strongly negative.
- It is worse than the flat LightGBM score_r walk-forward result (+8.11 raw, PF=1.0128).
- Several folds selected the least-bad threshold even when validation score was negative, then lost out-of-time.
- Fold 5 (2026-08) is the only meaningful positive transfer; fold 6 has only 7 candidates and zero trades.
- Phase134 paper/live remains blocked.
```

Immediate research implication:

```text
Do not train larger WaveNet blindly. The next possible research change is a validation no-trade/risk gate: if best validation score/PF is not good enough, the fold should select NO TRADE rather than forcing a threshold.
```

## Latest implementation update — Phase133C validation no-trade/risk gate — 2026-09-13

Implemented Phase133C as an extension of the tensor walk-forward validator:

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
GUI: Run tensor walk-forward validation
```

New flags:

```text
--allow-no-trade {0,1}
--min-validation-score FLOAT
--min-validation-profit-factor FLOAT
--max-validation-drawdown FLOAT
```

Purpose:

```text
If the best validation threshold is still weak, the fold can select NO_TRADE instead of forcing the least-bad trading threshold into the next test month.
```

Recommended Phase133C risk-gate settings:

```text
allow_no_trade                 : 1
min_validation_score           : 0
min_validation_profit_factor   : 1.10
max_validation_drawdown        : 120
```

Result schema now includes:

```text
selected_validation_profit_factor
selected_validation_max_drawdown
no_trade_selected
aggregate.no_trade_months
```

Phase134 remains blocked until a Phase133C run passes the out-of-time gates.

## Latest execution result — Phase133C validation no-trade gate FAILED as strategy — 2026-09-13

The operator ran Phase133C with the validation no-trade/risk gates enabled:

```text
allow_no_trade                 : 1
min_validation_score           : 0.0
min_validation_profit_factor   : 1.10
max_validation_drawdown        : 120.0
decision_modes                 : score,both
score_thresholds               : -0.10,0,0.05,0.10,0.20
```

Aggregate result:

```text
folds                    : 6
test_months              : 6
positive_months          : 0
negative_months          : 1
no_trade_months          : 3
base_total_pnl           : -1288.8456037938595
tensor_total_pnl         : -32.83297738432884
tensor_gross_profit      : 107.19759202003479
tensor_gross_loss        : 140.03056940436363
tensor_profit_factor     : 0.7655299301860462
tensor_max_drawdown      : 86.88896641135216
tensor_trades            : 35
tensor_avg_pnl           : -0.9380850681236812
tensor_final_balance     : 96.71670226156712
tensor_return_percent    : -3.283297738432878%
tensor_would_breach_zero : false
```

Fold decisions:

```text
2026-04: validation OK, selected both meta=0.55 score=0.05, test trades=0, tensor_pnl=0
2026-05: NO_TRADE because validation_score=-36.3806 < 0, tensor_pnl=0
2026-06: NO_TRADE because validation_score=-107.9652 < 0, tensor_pnl=0
2026-07: NO_TRADE because validation PF=1.0427 < 1.10, tensor_pnl=0
2026-08: validation OK, selected both meta=0.70 score=-0.10, test=-32.8330, PF=0.7655, trades=35
2026-09: validation OK, selected score=-0.10, test trades=0, tensor_pnl=0
```

Comparison:

```text
Phase133B tensor WF without no-trade gate : -409.5199 raw, PF=0.5979, trades=200
Phase133C tensor WF with no-trade gate    :  -32.8330 raw, PF=0.7655, trades=35
Base over same WF months                  : -1288.8456 raw
```

Decision:

```text
FAIL as a deployable strategy. The no-trade gate is useful damage control, but it did not create a profitable or stable walk-forward edge.
```

Important interpretation:

```text
Phase133C reduced losses by about 92% versus Phase133B and about 97% versus the base hybrid, but it still has negative total PnL, PF below 1, zero positive trading months, and only one month with trades. No Phase134 paper/live is allowed.
```

Recommended next research:

```text
Stop bigger WaveNet training. Build failure/regime diagnostics to identify why validation-positive folds fail in the next month and which side/session/range contexts drive losses.
```

## Latest implementation update — Phase136A tensor failure/regime diagnostics — 2026-09-14

Implemented Phase136A:

```text
scripts/analyze_tensor_failure_regimes.py
GUI: Analyze tensor failure regimes
```

Purpose:

```text
Analyze why Phase133B/C tensor WaveNet validation failed instead of training bigger models blindly.
```

Inputs:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
run_logs\hybrid_tensor_walk_forward_validation\latest.json
```

Outputs:

```text
run_logs\tensor_failure_regimes\latest.json
run_logs\tensor_failure_regimes\latest.html
run_logs\tensor_failure_regimes\latest_regimes.csv
run_logs\tensor_failure_regimes\latest_transfer.csv
```

Diagnostics:

```text
validation-to-test transfer table
per-month candidate outcomes
per-side BUY/SELL outcomes
month × side outcomes
session/hour outcomes
range room bins
candidate confidence bins
candidate reward/risk bins
specialist conflict buckets
booster entropy/margin bins
worst/best candidate regimes
```

Current production status remains:

```text
No paper shadow
No live trading
No production acceptance
```

## Latest execution result — Phase136A tensor failure/regime diagnostics — 2026-09-14

The operator ran Phase136A:

```text
script            : scripts/analyze_tensor_failure_regimes.py
flat_path         : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
walk_forward_json : run_logs\hybrid_tensor_walk_forward_validation\latest.json
candidate_only    : 1
candidate_rows    : 13757
```

Top-level candidate distribution:

```text
candidate_rows : 13757
months         : 10
total_pnl      : -43309.811259036884
win_rate       : 41.26626444719052%
profit_factor  : 0.6215092452270718
worst_month    : 2026-02
best_month     : 2026-07
```

Validation-to-test transfer from Phase133C:

```text
transfer_rows         : 6
transfer_total_pnl    : -32.83297738432884
transfer_profit_factor: 0.7655299301860462
no_trade_months       : 3
```

Risk flags:

```text
1 fold had positive validation quality but negative test PnL.
3 folds were blocked by validation no-trade gates.
1 active trading fold still lost money after gates.
Side BUY is negative in candidate distribution: -39003.71 raw PnL.
Side SELL is negative in candidate distribution: -4306.10 raw PnL.
```

Most important regime finding:

```text
BUY side is the main damage source:
BUY  rows=8583, win_rate=35.7917%, total_pnl=-39003.7073, PF=0.5106
SELL rows=5174, total_pnl=-4306.10
```

Worst candidate regimes:

```text
stop_loss outcome: rows=7256, share=52.7441%, total_pnl=-106988.0392
2026-02 month: rows=1945, win_rate=25.1414%, total_pnl=-21573.3665, PF=0.3872
wide/large SL-distance bin (23.56,124.647]: total_pnl=-22248.0623
range_1d_width (126.848,168.247]: total_pnl=-19492.4818
range_4h_width (33.305,46.57]: total_pnl=-18473.0694
range_4h_width (46.57,136.906]: total_pnl=-16979.6279
high candidate_confidence (0.938,0.973]: total_pnl=-14063.6031
```

Positive pockets found in candidate diagnostics:

```text
2026-04 / SELL: rows=568, win_rate=66.3732%, total_pnl=+2682.8371, PF=2.1863
2026-03 / SELL: rows=398, win_rate=53.0151%, total_pnl=+2308.4453, PF=1.8384
2026-07 / SELL: rows=1185, win_rate=59.5781%, total_pnl=+1963.2321, PF=1.4834
2026-06 / SELL: rows=571, win_rate=62.3468%, total_pnl=+669.4895, PF=1.2756
2026-08 / SELL: rows=256, win_rate=57.4219%, total_pnl=+469.5280, PF=1.6627
SELL / hour=9: rows=235, win_rate=54.0426%, total_pnl=+901.0482, PF=1.8986
SELL / hour=8: rows=348, win_rate=56.0345%, total_pnl=+640.0451, PF=1.3392
```

Interpretation:

```text
Phase136A does not approve a strategy. It shows that the current hybrid candidate generator is structurally bad on BUYs and stop-loss-heavy regimes. SELL has positive pockets, especially in certain months/hours, but these are candidate-outcome diagnostics, not chronological replay. The next valid research step is to build a regime-filtered replay/walk-forward phase that tests SELL-only and live-safe filters under chronological rules.
```

Production decision remains:

```text
No paper shadow.
No live trading.
No Phase134 acceptance.
```

## Latest implementation update — Phase137A regime-filtered hybrid replay — 2026-09-14

Implemented Phase137A:

```text
scripts/backtest_regime_filtered_hybrid.py
GUI: Backtest regime-filtered hybrid
```

Purpose:

```text
Test Phase136A hypotheses through chronological replay, including SELL-only, BUY-only, mixed, and stricter-BUY filters.
```

Important project decision:

```text
BUY is not removed from the project. Phase137A default is allowed_sides=BUY,SELL. SELL-only is only a diagnostic hypothesis, and BUY can be kept with stricter side-specific gates.
```

Outputs:

```text
run_logs\regime_filtered_hybrid\latest.json
run_logs\regime_filtered_hybrid\latest.html
run_logs\regime_filtered_hybrid\latest.csv
```

Recommended first diagnostic commands:

```text
1) SELL-only replay.
2) BUY,SELL replay with strict BUY gates.
```

No Phase134/paper/live permission is implied.

## Latest execution result — Phase137A regime-filtered replay diagnostics — 2026-09-14

The operator ran two Phase137A diagnostic replays.

### 1) SELL-only diagnostic replay

Configuration:

```text
allowed_sides : SELL
eval_frac     : 1.0
```

Result:

```text
source_candidates    : 13757
kept_candidates      : 5174
removed_candidates   : 8583
base_total_pnl       : -4590.797205492854
filtered_total_pnl   : -848.8386568725109
filtered_profit_factor : 0.7290926647116155
filtered_max_drawdown  : 1040.8391872644424
filtered_trades        : 581
filtered_win_rate      : 35.28399311531842%
filtered_final_balance : 15.116134312748898
would_breach_zero      : true
```

Monthly:

```text
2026-01:   -0.8822 PF=0.9943 trades=20
2026-02: -430.7218 PF=0.3631 trades=62
2026-03:  -53.4108 PF=0.8580 trades=61
2026-04:  +40.9952 PF=1.1149 trades=83
2026-05: -423.1884 PF=0.5078 trades=162
2026-06:  -16.2552 PF=0.9340 trades=61
2026-07:  +87.4448 PF=1.2510 trades=103
2026-08:  -52.8203 PF=0.5398 trades=29
```

Interpretation:

```text
SELL-only greatly reduces damage versus base, but is still a failed strategy. The main damage remains concentrated in 2026-02 and 2026-05. It is not enough to simply block BUY.
```

### 2) Mixed BUY,SELL with initial strict BUY gates

Configuration:

```text
allowed_sides          : BUY,SELL
buy_min_confidence     : 0.98
buy_min_side_4h_room   : 5.0
buy_min_side_1d_room   : 10.0
buy_max_sl_distance    : 20.0
```

Result:

```text
source_candidates      : 13757
kept_candidates        : 6360
removed_candidates     : 7397
base_total_pnl         : -4590.797205492854
filtered_total_pnl     : -2018.1994965970516
filtered_profit_factor : 0.585046282276268
filtered_max_drawdown  : 2100.639673948288
filtered_trades        : 883
filtered_win_rate      : 27.18006795016987%
filtered_final_balance : -101.81994965970517
would_breach_zero      : true
```

Interpretation:

```text
The first strict-BUY configuration is not sufficient and is worse than SELL-only. BUY is not removed from the architecture, but current BUY gates are not robust. BUY needs separate analysis/rework, not blind inclusion.
```

Current decision:

```text
No Phase134/paper/live. Next diagnostic should test focused SELL pockets from Phase136A, especially SELL hours 8 and 9, and possibly month-range restrictions, through chronological replay.
```

## Latest execution result — Phase137A SELL hours 8/9 focused replay — 2026-09-14

The operator ran the focused SELL-hours replay suggested by Phase136A:

```text
allowed_sides      : SELL
sell_allowed_hours : 8,9
eval_frac          : 1.0
```

Result:

```text
source_candidates       : 13757
kept_candidates         : 583
removed_candidates      : 13174
kept_rate               : 4.237842552882169%
base_total_pnl          : -4590.797205492854
filtered_total_pnl      : +16.920441061258316
filtered_profit_factor  : 1.037288325923403
filtered_max_drawdown   : 89.34972810745239
filtered_trades         : 77
filtered_win_rate       : 38.961038961038966%
filtered_final_balance  : 101.69204410612583
would_breach_zero       : false
```

Monthly:

```text
2026-01: +18.0882 PF=2.1592 trades=5
2026-02: -44.2072 PF=0.5853 trades=7
2026-03: +38.7940 PF=1.7817 trades=8
2026-04: +52.3129 PF=2.5081 trades=9
2026-05: -71.4458 PF=0.5502 trades=24
2026-06: +21.1881 PF=1.5779 trades=11
2026-07:  +0.1820 PF=1.0035 trades=11
2026-08:  +2.0082 PF=6.8089 trades=2
```

Interpretation:

```text
This is the first manual regime-filtered replay that is positive on full history, but it is weak and not accepted. PF=1.037 is below the 1.10 guideline, total PnL is small, and losses remain concentrated in 2026-02 and 2026-05. It is a useful hypothesis, not a deployable strategy.
```

Next diagnostic:

```text
Keep SELL h8/9 and add live-safe loss-control filters, starting with max SL distance or range width filters. Do not use month exclusion as a production rule.
```

## Latest execution result — Phase137A SELL h8/9 + max SL distance — 2026-09-14

The operator added a live-safe SL-distance cap to the weak-positive SELL h8/9 replay:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
eval_frac            : 1.0
```

Result:

```text
source_candidates       : 13757
kept_candidates         : 503
removed_candidates      : 13254
kept_rate               : 3.656320418695937%
base_total_pnl          : -4590.797205492854
filtered_total_pnl      : +23.147499471902847
filtered_profit_factor  : 1.0608648649692447
filtered_max_drawdown   : 89.64815473556519
filtered_trades         : 73
filtered_win_rate       : 36.98630136986301%
filtered_final_balance  : 102.31474994719028
would_breach_zero       : false
```

Comparison against previous SELL h8/9:

```text
SELL h8/9 only       : +16.9204 raw, PF=1.0373, trades=77, maxDD=89.3497
SELL h8/9 + SL<=23.56: +23.1475 raw, PF=1.0609, trades=73, maxDD=89.6482
```

Monthly:

```text
2026-01: +18.0882 PF=2.1592 trades=5
2026-02: -51.4716 PF=0.0000 trades=5
2026-03: +53.9956 PF=2.4144 trades=7
2026-04: +46.0941 PF=2.4267 trades=8
2026-05: -66.9372 PF=0.5663 trades=24
2026-06: +21.1881 PF=1.5779 trades=11
2026-07:  +0.1820 PF=1.0035 trades=11
2026-08:  +2.0082 PF=6.8089 trades=2
```

Interpretation:

```text
The SL-distance cap improved total PnL and PF, but the result is still below the PF>1.10 acceptance guideline and remains too weak for any production/paper discussion. Losses still concentrate in 2026-02 and 2026-05. Next diagnostic should add a 4H range-width cap while keeping SELL h8/9 and SL<=23.56.
```

## Latest execution result — Phase137A SELL h8/9 + SL cap + 4H width cap worsened — 2026-09-14

The operator tested the next live-safe filter combination:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
max_range_4h_width   : 33.305
eval_frac            : 1.0
```

Result:

```text
source_candidates       : 13757
kept_candidates         : 428
removed_candidates      : 13329
kept_rate               : 3.1111434178963438%
base_total_pnl          : -4590.797205492854
filtered_total_pnl      : -26.330932468175888
filtered_profit_factor  : 0.8915300951853891
filtered_max_drawdown   : 89.88325047492981
filtered_trades         : 50
filtered_win_rate       : 42.0%
filtered_final_balance  : 97.3669067531824
would_breach_zero       : false
```

Comparison:

```text
SELL h8/9 only                  : +16.9204 raw, PF=1.0373, trades=77
SELL h8/9 + SL<=23.56           : +23.1475 raw, PF=1.0609, trades=73
SELL h8/9 + SL<=23.56 + 4H<=33.305: -26.3309 raw, PF=0.8915, trades=50
```

Monthly:

```text
2026-04: +34.4846 PF=999.0 trades=3
2026-05: -66.9372 PF=0.5663 trades=24
2026-06:  +3.9314 PF=1.1072 trades=10
2026-07:  +0.1820 PF=1.0035 trades=11
2026-08:  +2.0082 PF=6.8089 trades=2
```

Interpretation:

```text
The broad max_range_4h_width=33.305 cap is rejected. It removed profitable January/March exposure but did not remove the main May loss. The current best manual filter remains SELL h8/9 + SL<=23.56, although it is still below acceptance.
```

Next diagnostic:

```text
Do not use the broad 4H width cap. If testing 4H width, test the exact positive Phase136A pocket: min_range_4h_width=21.741 and max_range_4h_width=26.928, while keeping SELL h8/9 and SL<=23.56.
```

## Latest execution result — Phase137A exact 4H width pocket — 2026-09-14

The operator tested the exact positive 4H width pocket from Phase136A while keeping the current SELL h8/9 + SL cap hypothesis:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
min_range_4h_width   : 21.741
max_range_4h_width   : 26.928
eval_frac            : 1.0
```

Result:

```text
source_candidates      : 13757
kept_candidates        : 166
removed_candidates     : 13591
kept_rate              : 1.2066584284364324%
base_total_pnl         : -4590.797205492854
filtered_total_pnl     : +11.376214891672134
filtered_profit_factor : 1.1828907946231388
filtered_max_drawdown  : 19.283453941345215
filtered_trades        : 14
filtered_win_rate      : 57.14285714285714%
filtered_final_balance : 101.13762148916722
would_breach_zero      : false
```

Monthly:

```text
2026-04:  +6.8169 PF=999.0 trades=1
2026-05:  +6.6403 PF=1.3561 trades=3
2026-06: +12.7187 PF=1.8103 trades=4
2026-07: -16.8079 PF=0.3891 trades=4
2026-08:  +2.0082 PF=6.8089 trades=2
```

Comparison:

```text
SELL h8/9 + SL<=23.56                       : +23.1475 raw, PF=1.0609, trades=73, maxDD=89.6482
SELL h8/9 + SL<=23.56 + exact 4H pocket     : +11.3762 raw, PF=1.1829, trades=14, maxDD=19.2835
```

Interpretation:

```text
The exact 4H pocket improves quality and drawdown, and PF finally exceeds 1.10. However, trade count is very small and total PnL is low. This is a promising micro-regime, not a deployable strategy. It needs recent-holdout and walk-forward validation.
```

Next diagnostic:

```text
Run the exact same filter with eval_frac=0.15. If the recent holdout fails, the micro-regime is not robust enough. If it remains positive, build a Phase137B/138 walk-forward filter-validation step.
```

## Latest execution result — Phase137A exact 4H pocket recent holdout FAILED — 2026-09-14

The operator reran the exact 4H pocket filter on the recent 15% slice:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
min_range_4h_width   : 21.741
max_range_4h_width   : 26.928
eval_frac            : 0.15
```

Result:

```text
evaluated_rows         : 7924
source_candidates      : 1445
kept_candidates        : 70
kept_rate              : 4.844290657439446%
base_total_pnl         : -241.5674167573452
filtered_total_pnl     : -17.275230020284653
filtered_profit_factor : 0.11992036742639664
filtered_max_drawdown  : 19.283453941345215
filtered_trades        : 4
filtered_win_rate      : 25.0%
filtered_final_balance : 98.27247699797154
would_breach_zero      : false
```

Monthly:

```text
2026-07: -19.2835 PF=0.0 trades=2
2026-08:  +2.0082 PF=6.8089 trades=2
```

Decision:

```text
Reject the exact 4H pocket as a robust filter. It looked acceptable on full history but failed the recent holdout with only 4 trades and negative PnL.
```

Current best manual regime remains:

```text
SELL h8/9 + sell_max_sl_distance=23.56
full-history: +23.1475 raw, PF=1.0609, trades=73
```

Next final sanity check:

```text
Run the current best manual regime on eval_frac=0.15. If it also fails or is only near-zero, stop manual filtering and move to formal walk-forward filter validation / BUY-side rework.
```

## Latest execution result — Phase137A current-best SELL filter recent holdout FAILED — 2026-09-14

The operator tested the current best less-restrictive manual filter on the recent 15% slice:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
eval_frac            : 0.15
```

Result:

```text
evaluated_rows         : 7924
source_candidates      : 1445
kept_candidates        : 104
kept_rate              : 7.197231833910035%
base_total_pnl         : -241.5674167573452
filtered_total_pnl     : -22.4049571454525
filtered_profit_factor : 0.40983705655862596
filtered_max_drawdown  : 37.618305921554565
filtered_trades        : 8
filtered_win_rate      : 25.0%
filtered_final_balance : 97.75950428545475
would_breach_zero      : false
```

Monthly:

```text
2026-07: -24.41318106651306 PF=0.3510 trades=6
2026-08:  +2.008223921060562 PF=6.8089 trades=2
```

Comparison with full-history current-best manual filter:

```text
Full history SELL h8/9 + SL<=23.56 : +23.1475 raw, PF=1.0609, trades=73
Recent 15% same filter              : -22.4050 raw, PF=0.4098, trades=8
```

Decision:

```text
Reject the current-best manual SELL regime as robust. Manual SELL h8/9 filtering does not survive recent holdout.
```

Interpretation:

```text
Phase137A manual filters are useful diagnostics but not deployable. The apparent full-history SELL pocket does not persist in the recent slice. Do not continue blindly adding hand filters. The next work should shift to TP/SL and trade anatomy diagnostics, especially BUY-side damage and stop-loss concentration.
```

Production decision remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Latest implementation update — Phase138A trade anatomy / TP-SL failure analysis — 2026-09-14

Implemented Phase138A:

```text
scripts/analyze_trade_anatomy.py
GUI: Analyze trade anatomy
```

Why:

```text
Phase137A manual regime filters failed recent holdout. The next issue to inspect is trade construction: TP/SL placement, bracket width, stop-loss concentration, BUY/SELL asymmetry and hold-time behavior.
```

Outputs:

```text
run_logs\trade_anatomy\latest.json
run_logs\trade_anatomy\latest.html
run_logs\trade_anatomy\latest_anatomy.csv
```

The report analyzes:

```text
side/outcome/month/hour buckets
TP and SL distance bins
reward/risk bins
hold bars
action-side 4H/1D room
range width
candidate confidence
stop-loss and timeout rates
```

No production/paper permission is implied.

## Latest execution result — Phase138A trade anatomy / TP-SL failure analysis — 2026-09-15

The operator ran Phase138A on the full candidate telemetry matrix:

```text
candidate_rows : 13757
months         : 10
total_pnl      : -43309.811259036884
win_rate       : 41.26626444719052%
profit_factor  : 0.6215092452270718
max_drawdown   : 45887.01167863794
```

Core outcome anatomy:

```text
take_profit_rate : 37.38460420149742%
stop_loss_rate   : 52.74405757069128%
timeout_rate     : 9.871338227811297%
```

Side anatomy:

```text
BUY rows              : 8583
BUY total_pnl         : -39003.70734734554
BUY profit_factor     : 0.5106436955011304
BUY stop_loss_rate    : 59.07025515554002%
BUY avg_sl_distance   : 17.62240083711894

SELL rows             : 5174
SELL total_pnl        : -4306.103911691345
SELL profit_factor    : 0.8759889582324059
SELL stop_loss_rate   : 42.24971008890607%
SELL avg_sl_distance  : 17.539608476089555
```

Worst anatomy findings:

```text
stop_loss outcome       : rows=7256, total_pnl=-106988.03918242455, avg_hold_bars=12.2172
BUY / stop_loss         : rows=5070, total_pnl=-75934.2055940628
SELL / stop_loss        : rows=2186, total_pnl=-31053.83358836174
SL distance high bin    : (23.56,124.647], rows=2752, total_pnl=-22248.062289144844, PF=0.5144
Worst month             : 2026-02, total_pnl=-21573.36649065558, stop_loss_rate=66.4267%
Worst month_side buckets: 2026-02 / BUY and 2026-03 / BUY
```

Important TP/SL insight:

```text
Stop-loss candidates have avg_tp_distance=22.5691 and avg_sl_distance=14.7448 with avg_reward_risk=2.8001.
Take-profit candidates have avg_tp_distance=13.0167 and avg_sl_distance=20.5877 with avg_reward_risk=0.8209.
```

Interpretation:

```text
Higher nominal reward/risk is not helping; it is associated with stop-loss failures. The current bracket appears to often set TP too far relative to market path, while SL is hit quickly. Average stop-loss hold time is only ~12 bars. This points to TP/SL bracket construction and side-specific bracket policy, not just classifier/model quality.
```

Decision:

```text
No Phase134 / no paper / no live. Manual filters are not robust and Phase138A indicates the next engineering work should be TP/SL bracket recalibration replay, not another bigger model.
```

Recommended next phase:

```text
Phase139A — TP/SL Bracket Recalibration Replay
```

Scope:

```text
- simulate alternative TP/SL policies on the same candidate stream
- cap TP distance / cap SL distance
- side-specific BUY/SELL TP/SL caps
- test lower reward/risk caps rather than only minimum reward/risk
- compare same_bar_policy sensitivity
- chronological replay and recent-holdout report
```

## Latest implementation update — Phase139A TP/SL bracket recalibration replay — 2026-09-15

Implemented Phase139A:

```text
scripts/backtest_bracket_recalibration.py
GUI: Backtest bracket recalibration
```

Purpose:

```text
Re-simulate alternative TP/SL geometry on the existing candidate stream without training a model.
```

Why:

```text
Phase138A showed high nominal reward/risk and far TP candidates are often stop-loss failures. Bracket geometry must be tested directly.
```

Supported caps:

```text
--max-tp-distances
--max-sl-distances
--max-reward-risks
--buy-max-tp-distance / --sell-max-tp-distance
--buy-max-sl-distance / --sell-max-sl-distance
--buy-max-reward-risk / --sell-max-reward-risk
```

Outputs:

```text
run_logs\bracket_recalibration\latest.json
run_logs\bracket_recalibration\latest.html
run_logs\bracket_recalibration\latest.csv
run_logs\bracket_recalibration\best_trades.csv
```

No Phase134/paper/live permission is implied.

## Latest execution result — Phase139A global TP/SL bracket recalibration FAILED — 2026-09-15

The operator ran Phase139A on the full candidate stream:

```text
allowed_sides      : BUY,SELL
max_tp_distances   : original,12,14,16,18
max_sl_distances   : original,20,23.56,30
max_reward_risks   : original,1,1.5,2
eval_frac          : 1.0
same_bar_policy    : stop_first
```

Best selected policy:

```text
policy              : tp=original:sl=original:rr=original
trades              : 1693
buy/sell            : 1118 / 575
wins/losses         : 512 / 1181
win_rate            : 30.2422%
total_pnl           : -4590.797210656048
profit_factor       : 0.5787103197097719
max_drawdown        : 4590.797210656047
final_balance       : -359.0797210656049
would_breach_zero   : true
```

Interpretation:

```text
All tested global TP/SL/RR caps were worse than the original bracket. Simple global bracket caps do not solve the edge problem. Capping TP or SL often shortened trade duration and allowed more low-quality candidates to enter, increasing total loss.
```

Important conclusion:

```text
The issue is not fixed by naive TP/SL cap recalibration. Candidate direction/entry quality and side-specific bracket geometry remain the likely problems, especially BUY-side behavior.
```

Next diagnostic if continuing:

```text
Run Phase139A side-specific grids separately:
1) SELL-only bracket recalibration
2) BUY-only bracket recalibration

If both fail, stop bracket tweaking and move to candidate-generation / target-definition rework.
```

Production decision remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Latest execution result — Phase139A side-specific bracket grids FAILED — 2026-09-15

The operator ran side-specific Phase139A bracket recalibration grids after the global grid failed.

### SELL-only bracket recalibration

Configuration:

```text
allowed_sides    : SELL
max_tp_distances : original,10,12,14,16
max_sl_distances : original,16,20,23.56
max_reward_risks : original,0.8,1,1.5
eval_frac        : 1.0
```

Best SELL-only policy:

```text
policy            : tp=14:sl=original:rr=original
trades            : 633
buy/sell          : 0 / 633
wins/losses       : 262 / 371
win_rate          : 41.3902%
total_pnl         : -664.0531247957406
avg_pnl           : -1.0490570691875838
profit_factor     : 0.7939690496760271
max_drawdown      : 846.2230220278584
final_balance     : 33.594687520425936
would_breach_zero : false
```

Comparison to original SELL-only:

```text
original SELL-only : -848.8387 raw, PF=0.7291, trades=581
best SELL policy   : -664.0531 raw, PF=0.7940, trades=633
```

SELL monthly under best policy:

```text
2026-01:   +2.3453 PF=1.0152 trades=24
2026-02: -330.3915 PF=0.5612 trades=80
2026-03:  +35.8600 PF=1.1081 trades=72
2026-04:  +12.4742 PF=1.0345 trades=87
2026-05: -414.8800 PF=0.5398 trades=172
2026-06:   -6.3987 PF=0.9736 trades=61
2026-07:  +89.8878 PF=1.2475 trades=108
2026-08:  -52.9502 PF=0.5387 trades=29
```

Decision:

```text
SELL bracket caps reduce loss but do not create an edge. SELL remains below PF=1 and far below deployable quality.
```

### BUY-only bracket recalibration

Configuration:

```text
allowed_sides    : BUY
max_tp_distances : original,8,10,12,14
max_sl_distances : original,12,16,20
max_reward_risks : original,0.8,1,1.5
eval_frac        : 1.0
```

Best BUY-only policy:

```text
policy            : tp=original:sl=16:rr=original
trades            : 1253
buy/sell          : 1253 / 0
wins/losses       : 305 / 948
win_rate          : 24.3416%
total_pnl         : -3667.8429958516326
avg_pnl           : -2.9272489990835058
profit_factor     : 0.5476443218994678
max_drawdown      : 3668.8183342898155
final_balance     : -266.7842995851633
would_breach_zero : true
```

Comparison to original BUY-only:

```text
original BUY-only : -3838.3925 raw, PF=0.5142, trades=1129
best BUY policy   : -3667.8430 raw, PF=0.5476, trades=1253
```

BUY monthly under best policy:

```text
Every reported month is negative.
Worst months include 2026-03 (-1016.33), 2026-02 (-669.01), 2025-12 (-584.76), 2026-01 (-448.75), 2026-06 (-338.13), 2026-04 (-261.77), 2026-08 (-170.76).
```

Decision:

```text
BUY is not fixed by the tested TP/SL caps. BUY should not be deleted from the architecture, but the current BUY candidate generation/entry direction is not tradeable.
```

Overall conclusion:

```text
Phase139A side-specific grids failed. Simple bracket caps cannot rescue the current candidate stream. The next diagnostic should test candidate direction/entry quality directly, including counterfactual side flip and entry-delay analysis.
```

Recommended next phase:

```text
Phase140A — Candidate Direction / Counterfactual Entry Audit
```

Production remains blocked.

## Latest implementation update — Phase140A candidate direction / counterfactual entry audit — 2026-09-16

Implemented Phase140A after Phase139A failed to rescue the candidate stream with TP/SL caps.

```text
scripts/audit_candidate_direction_entry.py
GUI: Audit candidate direction/entry
```

Purpose:

```text
Audit whether current hybrid candidates are failing because direction is inverted/contrarian, because entry is too early, or because candidate generation has no stable edge.
```

The audit tests:

```text
side_mode        : original, flipped
entry_delay_bars : 0,1,2,3
execution_mode   : independent, chronological
```

Output files:

```text
run_logs\candidate_direction_entry_audit\latest.json
run_logs\candidate_direction_entry_audit\latest.html
run_logs\candidate_direction_entry_audit\latest.csv
run_logs\candidate_direction_entry_audit\latest_groups.csv
run_logs\candidate_direction_entry_audit\best_chronological_trades.csv
```

First command to run:

```powershell
python -u scripts/audit_candidate_direction_entry.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --entry-delays 0,1,2,3 `
  --side-modes original,flipped `
  --execution-modes independent,chronological `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

Interpretation:

```text
If flipped side improves materially, direction/target sign may be contrarian or inverted.
If entry delay improves materially, entry timing may be too early.
If neither helps, current candidate generation is probably no-edge and target/candidate definitions need rework.
```

BUY is not removed. Phase140A explicitly compares BUY original vs BUY flipped-to-SELL as a diagnostic, not as a permanent deletion of BUY.

Production decision remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Latest execution result — Phase140A candidate direction / entry audit FAILED as strategy — 2026-09-16

The operator ran Phase140A and provided:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

Configuration:

```text
evaluated_rows  : 52,832
candidate_rows  : 13,757
side_modes      : original,flipped
entry_delays    : 0,1,2,3
execution_modes : independent,chronological
```

Top-level result:

```text
best_independent_scenario        : independent:flipped:delay=0
best_independent_total_pnl       : -37,742.8296
best_independent_profit_factor   : 0.6561

best_chronological_scenario      : chronological:original:delay=3
best_chronological_total_pnl     : -3,123.7836
best_chronological_profit_factor : 0.6512
```

Original vs flipped:

```text
independent original delay=0    : -43,309.8113
independent flipped delay=0     : -37,742.8296
chronological original delay=0  : -4,590.7972
chronological flipped delay=0   : -4,113.8428
```

Entry delay effect in chronological original mode:

```text
delay=0  -4590.7972  PF=0.5787
delay=1  -4245.3885  PF=0.5962
delay=2  -3921.5867  PF=0.5985
delay=3  -3123.7836  PF=0.6512
```

Side diagnosis:

```text
BUY original      : -39,003.7074  PF=0.5106
BUY flipped→SELL  : -15,831.0041  PF=0.7545
SELL original     : -4,306.1039   PF=0.8760
SELL flipped→BUY  : -21,911.8255  PF=0.5157
```

Decision:

```text
Phase140A failed as a strategy. No scenario is profitable. However, it produced useful diagnosis:
- global flip is not the solution
- BUY candidates show strong contrarian/inversion symptoms but flipped BUY is still negative
- SELL direction is not inverted and should not be flipped globally
- entry delay helps materially but does not create edge
```

Recommended next diagnostic:

```text
Phase141A — Side-Transform / Delay Policy Grid
```

Purpose:

```text
Test side-specific actions chronologically:
BUY action  = original, flipped_to_sell, skip
SELL action = original, flipped_to_buy, skip
BUY delay   = 0,1,2,3
SELL delay  = 0,1,2,3
```

Production decision remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Latest implementation/result — Phase141A pivot pattern recognition built and failed first real walk-forward — 2026-09-16

The owner requested a new model that performs Pattern Recognition for gold top/bottom reversal zones:

```text
Detect approximate tops before downside.
Detect approximate bottoms before upside.
Use 5M patterns with 4H/1D context.
Train, select useful features, then backtest/walk-forward.
```

Implemented:

```text
scripts/train_pivot_pattern_recognition.py
GUI: Train pivot pattern recognition
```

The model target is:

```text
SELL = top_zone reversal pattern
HOLD = no actionable pivot zone
BUY  = bottom_zone reversal pattern
```

Real-data run used public Yahoo data:

```text
market_symbol : GC=F
note          : public COMEX gold futures proxy, not broker-perfect Alpari XAUUSD
1D rows       : 1,258
4H rows       : 3,721, resampled from 1H
5M rows       : 13,509
```

Feature engineering/selection:

```text
feature_columns_total : 57
selected_features     : 38 per fold
target_counts         : SELL=1,368 / HOLD=10,764 / BUY=1,376
model_kind_used       : sklearn_hgb
```

Top selected feature families were mostly 5M structure/pattern features:

```text
m5_pos_in_range_48
m5_dist_high_48_atr
m5_dist_low_48_atr
m5_fast_mid_dist_atr
m5_price_z_96
m5_pos_in_range_24
m5_ret48
m5_close_mid_dist_atr
m5_ret24
m5_dist_high_24_atr
```

Walk-forward result:

```text
folds             : 6
trades            : 102
BUY / SELL trades : 40 / 62
wins / losses     : 45 / 57
win_rate          : 44.1176%
initial_balance   : $100.00
final_balance     : $86.7906
net_profit        : -$13.2094
return            : -13.2094%
profit_factor     : 0.6738
max_drawdown_cash : $15.0879
positive_folds    : 0
negative_folds    : 6
```

Decision:

```text
Phase141A built the requested model and produced a real walk-forward report, but it failed as a trading strategy.
```

Artifacts:

```text
run_logs\pivot_pattern_recognition\latest.json
run_logs\pivot_pattern_recognition\latest.html
run_logs\pivot_pattern_recognition\latest_folds.csv
run_logs\pivot_pattern_recognition\latest_trades.csv
run_logs\pivot_pattern_recognition\latest_features.csv

datasets\models\gold_pivot_pattern_recognition_5m\v1_model.pkl
datasets\models\gold_pivot_pattern_recognition_5m\v1_training.json
```

Production decision remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

Next useful direction:

```text
Run Phase141A on broker-quality multi-year Alpari XAUUSD data, then test stricter pivot labels/no-trade gates before moving to heavier sequence/CNN pattern models.
```

## Latest operator rerun — Phase141A Yahoo GC=F confirms failure — 2026-09-16

The operator reran Phase141A on Windows with `source_mode=yahoo` and `yahoo_symbol=GC=F`.

Result:

```text
1D rows              : 1,258
4H rows              : 3,722
5M rows              : 13,555
feature_rows         : 13,555
target_counts        : SELL=1,385 / HOLD=10,782 / BUY=1,387
model_kind_used      : sklearn_hgb
folds                : 6
trades               : 92
BUY / SELL trades    : 39 / 53
wins / losses        : 33 / 59
win_rate             : 35.8696%
initial_balance      : $100.00
final_balance        : $79.0053
net_profit           : -$20.9947
return               : -20.9947%
profit_factor        : 0.5344
max_drawdown_cash    : $23.1522
positive_folds       : 0
negative_folds       : 6
```

Decision:

```text
The operator rerun confirms Phase141A fails as a strategy on public Yahoo/GC=F data.
No production/paper/live permission.
```

The operator then tried broker-file mode:

```powershell
--source-mode files
--daily-path datasets\external\XAUUSD_1D.csv
--hourly-path datasets\external\XAUUSD_1H.csv
--five-path datasets\external\XAUUSD_5M.csv
```

Error:

```text
[X] RuntimeError: Input file does not exist: datasets\external\XAUUSD_1D.csv
```

Interpretation:

```text
This is only a missing-file error. The Alpari/XAUUSD CSV files must be exported/copied into datasets\external before files mode can run.
```

## Latest implementation correction — Phase141A reads project storage directly — 2026-09-16

The owner correctly pointed out that Phase141A should read the project's existing datasets instead of requiring files to be copied into `datasets\external`.

Correction implemented:

```text
scripts/train_pivot_pattern_recognition.py
--source-mode storage
```

Storage mode reads from the canonical project layout:

```text
datasets\processed\XAUUSD\5M\v*.parquet
datasets\processed\XAUUSD\1D\v*.parquet
```

For 4H context:

```text
1. Use datasets\processed\XAUUSD\4H\v*.parquet if it exists.
2. Otherwise use datasets\processed\XAUUSD\1H\v*.parquet and resample it to 4H.
```

Project parquet schema is now handled:

```text
open_time -> timestamp
```

GUI default changed:

```text
Train pivot pattern recognition
source_mode default = storage
```

This fixes the earlier missing-file confusion:

```text
datasets\external\XAUUSD_1D.csv is no longer required for normal project runs.
```

Correct next command uses `--source-mode storage`, not `--source-mode files`.

## Latest implementation update — Phase142A/142B 3D Pivot Tensor + Keras WaveNet — 2026-09-16

The owner clarified that the intended pattern model must be a true 3D TensorFlow/Keras WaveNet model, not a flat sklearn baseline.

Shape clarification:

```text
Stored tensor X shape       : [samples, 288, channels]
Keras runtime batch X shape : [batch, 288, channels]
```

Implemented:

```text
scripts/build_pivot_pattern_tensor.py
scripts/train_pivot_pattern_wavenet.py
scripts/backtest_pivot_pattern_wavenet.py
scripts/run_pivot_pattern_wavenet_walk_forward.py
```

GUI commands added:

```text
Build pivot pattern tensor
Train pivot WaveNet pattern model
Backtest pivot WaveNet pattern model
Run pivot WaveNet walk-forward
```

Tensor outputs:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz
datasets\processed\XAUUSD\5M\pivot_pattern_flat_latest.parquet
run_logs\pivot_pattern_tensor\latest.json
run_logs\pivot_pattern_tensor\latest.html
```

WaveNet training outputs:

```text
datasets\models\gold_pivot_pattern_wavenet_5m\v*_model.keras
datasets\models\gold_pivot_pattern_wavenet_5m\v*_training.json
run_logs\pivot_pattern_wavenet\latest.json
run_logs\pivot_pattern_wavenet\latest.html
```

Backtest/walk-forward outputs:

```text
run_logs\pivot_pattern_wavenet_backtest\latest.json
run_logs\pivot_pattern_wavenet_walk_forward\latest.json
```

Important execution note:

```text
TensorFlow/Keras is required for training/backtest/walk-forward.
Install with: python -m pip install -r requirements-ai.txt
```

Implementation verification:

```text
targeted ruff  → passed
targeted black → passed
targeted tests → passed
```

Full real XAUUSD WaveNet training was not executed in this sandbox because the complete XAUUSD 5M/1H project-storage dataset and TensorFlow runtime are on the operator machine. The operator should run the commands in docs/Phases/Phase142.md.

Production status remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Latest correction — Phase143A 4D Pivot Image Tensor for Conv2D/Conv3D — 2026-09-16

The owner clarified that the intended dataset should be 4D for Conv2D/Conv3D, not the previous 3D sequence tensor.

Implemented:

```text
scripts/build_pivot_pattern_image_tensor.py
scripts/train_pivot_pattern_image_cnn.py
```

GUI commands:

```text
Build pivot image tensor
Train pivot image CNN
```

Correct layout:

```text
Stored X      : [samples, WindowSize, Features_5M, Features_4H_1D]
Conv2D batch  : [batch, WindowSize, Features_5M, Features_4H_1D]
Conv3D batch  : [batch, WindowSize, Features_5M, Features_4H_1D, 1]
```

Default rolling setup:

```text
WindowSize = 100
sample_stride = 1
```

Tensor cell semantics:

```text
X[t, f5, htf] = feature_5M[t, f5] * feature_4H_1D[t, htf]
```

Bias features preserve pure 5M and pure HTF information.

Smoke result:

```text
TESTSYM stored X      : [160, 20, 5, 4]
TESTSYM Conv2D batch  : [batch, 20, 5, 4]
TESTSYM Conv3D batch  : [batch, 20, 5, 4, 1]
```

Production remains blocked until real training/backtest/walk-forward proves edge.

## Latest correction — Phase143A feature-axis budget increased — 2026-09-17

The owner correctly objected that the first 4D image tensor defaults were too small:

```text
13 5M-axis entries including bias
9 HTF-axis entries including bias
```

Defaults were increased for serious pattern-recognition training:

```text
max_5m_features  : 24 + bias = 25
max_htf_features : 16 + bias = 17
max_tensor_mb    : 8192
```

Approximate full-size tensor if XAUUSD 5M has ~53,198 rows and `WindowSize=100`:

```text
samples ≈ 53,099
shape   ≈ [53,099, 100, 25, 17]
size    ≈ 4.3 GB float16
```

The operator can still increase the feature axes manually if hardware allows.

## Latest operator result — Phase143A Conv2D sanity training selected no trades — 2026-09-17

The operator trained the Phase143A Conv2D image CNN on a 12,000-sample subset of the 4D tensor.

```text
stored_x_shape  : [12,000, 100, 32, 23]
keras_batch     : [batch, 100, 32, 23]
train/val/test  : 8,400 / 1,464 / 1,464
epochs          : 10
```

Metrics:

```text
val_action_accuracy  : 0.1441
test_action_accuracy : 0.3743
val_top_ap           : 0.1158
test_top_ap          : 0.1217
val_bottom_ap        : 0.0777
test_bottom_ap       : 0.1012
val_selected_rate    : 0.0000
test_selected_rate   : 0.0000
```

Decision:

```text
Phase143A Conv2D sanity training ran, but failed as an actionable model.
The default gate selected zero trades. No paper/live permission.
```

Next action:

```text
Do not run full training blindly yet. First run a lower-threshold diagnostic / probability-distribution diagnostic to see whether the model has usable probability spread or is collapsing to HOLD/low-confidence outputs.
```

## Latest correction — Phase143A tensor overflow/scaler NaN fixed — 2026-09-17

The operator inspected `gold_pivot_pattern_image_cnn_5m v1_training.json` and found:

```text
scaler_mean contains Infinity
scaler_std contains NaN
```

Root cause:

```text
Raw 5M × 4H/1D interaction products overflowed when cast to float16.
The trainer then fitted scaler statistics on an already poisoned tensor.
```

Decision:

```text
gold_pivot_pattern_image_cnn_5m v1 is invalid/rejected.
Do not backtest or continue training v1.
```

Fix implemented:

```text
build_pivot_pattern_image_tensor.py:
  --axis-normalization robust
  --feature-clip 8
  --interaction-clip 32
  stores nonfinite diagnostics in latest.json/meta

train_pivot_pattern_image_cnn.py:
  sanitizes old tensor nonfinite values before scaler fitting
  saves finite scaler_mean/scaler_std
  saves model architecture and summary files
```

Architecture output paths:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_architecture.json
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_summary.txt
run_logs\pivot_pattern_image_cnn\latest_architecture.json
run_logs\pivot_pattern_image_cnn\latest_summary.txt
```

Next required action:

```text
Rebuild the 4D image tensor with sanitization, then retrain Conv2D v2+.
```

## Latest implementation update — Phase143A official tensor-health audit added — 2026-09-17

The manual dataset-health test was promoted into project code:

```text
scripts/audit_pivot_pattern_image_tensor.py
GUI: Audit pivot image tensor health
```

The audit validates the 4D tensor before training:

```text
shape/rank
metadata alignment
sample_indices/timestamps
target arrays
axis scaler arrays
full finite scan
interaction clip bounds
builder diagnostics
```

Output:

```text
run_logs\pivot_pattern_image_tensor_health\latest.json
run_logs\pivot_pattern_image_tensor_health\latest.html
```

Operator statement:

```text
The dataset health test was run and the dataset was healthy.
```

Next action:

```text
Train a new sanitized Conv2D model version. Do not use v1 because v1 had Infinity/NaN scaler values.
```

## Latest implementation correction — Phase143A image CNN epoch checkpoints — 2026-09-17

The operator reported that one epoch completed but no model appeared in `datasets\models`.

Explanation:

```text
The old trainer saved final model artifacts only after all epochs completed.
```

Fix:

```text
scripts/train_pivot_pattern_image_cnn.py
--checkpoint-each-epoch 1
```

Now training creates the model directory before the first epoch and saves:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_architecture.json
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_summary.txt
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_epoch_checkpoint.keras
```

Final artifacts still appear only when training finishes:

```text
vN_model.keras
vN_training.json
```

## Latest implementation update — Phase144A advanced 4D Pivot Image WaveNet — 2026-09-17

The owner rejected the simple Conv2D baseline as insufficient and requested the real architecture with:

```text
Residual connections
SE/Attention blocks
dilated conv over time
separate 5M/HTF branches
temporal attention
multi-scale kernels
activation=tanh
```

Implemented:

```text
scripts/train_pivot_pattern_image_wavenet.py
GUI: Train advanced pivot image WaveNet
```

Architecture:

```text
Input [WindowSize, Features_5M, Features_4H_1D]
→ separate pure 5M branch
→ separate pure 4H/1D branch
→ TimeDistributed spatial multi-scale Conv2D over feature interaction image
→ branch fusion
→ gated tanh-sigmoid causal dilated WaveNet residual blocks
→ squeeze-excitation channel attention
→ temporal MultiHeadAttention
→ avg/max/last-state pooling
→ action/top/bottom/buy_r/sell_r heads
```

Tanh decision:

```text
Uses WaveNet-style tanh(filter) * sigmoid(gate).
Default --activation tanh.
```

Output paths:

```text
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_model.keras
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_training.json
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_architecture.json
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_summary.txt
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_epoch_checkpoint.keras
run_logs\pivot_pattern_image_wavenet\latest.json
run_logs\pivot_pattern_image_wavenet\latest_summary.txt
```

Production remains blocked until real train/backtest/walk-forward proves edge.

## Latest implementation correction — RAM-safe stream loader for 4D image trainers — 2026-09-17

The operator reported RAM usage around 27GB on a 32GB system. The issue was caused by loading the selected 4D tensor subset into RAM and creating a second normalized copy.

Fix:

```text
--loader-mode stream
--stream-chunk-size 256
```

Applies to:

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
```

Effect:

```text
Dataset stays on disk as .npy memmap.
Scaler is computed chunk-by-chunk.
Only the current batch is loaded and normalized.
The dataset/model are not made smaller.
```

## Latest implementation update — Stream loader prevents full tensor RAM copy — 2026-09-17

Both 4D image trainers now default to RAM-safe streaming:

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
--loader-mode stream
--stream-chunk-size 256
```

This keeps the `.npy` tensor memory-mapped on disk and only loads/normalizes the current batch. It does not reduce dataset size or model architecture.

Full pytest remains passing:

```text
python -m pytest -q → passed
python -m pytest --collect-only → 1909 tests collected
```

## Latest implementation update — batch-level training logs for long 4D training — 2026-09-17

The operator requested visibility during long epochs. Both 4D image trainers now support per-batch logging:

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
--batch-log-every N
--batch-log-file PATH
```

Default JSONL outputs:

```text
run_logs\pivot_pattern_image_cnn\latest_batch_log.jsonl
run_logs\pivot_pattern_image_wavenet\latest_batch_log.jsonl
```

Use:

```text
--batch-log-every 1
```

to print every batch to console and write every batch metric to the JSONL file.

## Latest implementation update — Phase145A Pivot Sequence Tensor + Advanced Conv1D WaveNet — 2026-09-17

Implemented Option A proposed by the owner:

```text
Stored tensor X = [samples, WindowSize, Features]
Keras batch     = [batch, WindowSize, Features]
```

Implemented files:

```text
scripts/build_pivot_pattern_sequence_tensor.py
scripts/train_pivot_pattern_sequence_wavenet.py
```

GUI commands:

```text
Build pivot sequence tensor
Train pivot sequence WaveNet
```

Feature policy:

```text
Features = generated 5M + closed 4H + closed 1D + session/time + optional source 5M numeric features.
```

Source 5M numeric features are included with prefix:

```text
src5m_
```

This allows the operator's larger historical 5M feature set to be preserved without the 4D feature-interaction explosion.

Architecture:

```text
Input [WindowSize, Features]
→ separate 5M branch
→ separate HTF branch
→ all-feature branch
→ multi-scale temporal Conv1D kernels
→ gated tanh-sigmoid dilated WaveNet residual blocks
→ SE/channel attention
→ temporal self-attention
→ avg/max/last pooling
→ action/top/bottom/buy_r/sell_r heads
```

Default training mode:

```text
--loader-mode stream
```

Smoke result on TESTSYM:

```text
X shape     : [160, 20, 57]
Keras batch : [batch, 20, 57]
```

Production remains blocked until real train/backtest/walk-forward proves edge.

## Phase144A operator result — advanced 4D Image WaveNet v1 — 2026-09-19

The owner supplied `run_logs\pivot_pattern_image_wavenet\latest.json` for the first full operator-machine run of the advanced 4D Image WaveNet.

Run configuration summary:

```text
model_id          : gold_pivot_pattern_image_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
stored_x_shape    : [12000, 100, 32, 23]
keras_batch_shape : [batch, 100, 32, 23]
loader_mode       : stream
batch_size        : 8
epochs requested  : 20
learning_rate     : 0.0005
nonfinite_input_values : 0
```

Validation metrics:

```text
val_action_accuracy : 0.5628415301
val_top_ap          : 0.2038051024
val_bottom_ap       : 0.1501470022
val_buy_r_mae       : 0.6300964952
val_sell_r_mae      : 0.6807333231
val_selected_rate   : 0.4187158470
```

Test metrics:

```text
test_action_accuracy : 0.5969945355
test_top_ap          : 0.2327647696
test_bottom_ap       : 0.2356605000
test_buy_r_mae       : 0.6400972009
test_sell_r_mae      : 0.6506559253
test_selected_rate   : 0.4009562842
```

Interpretation:

```text
GOOD:
- The sanitized/streamed 4D pipeline is numerically healthy: nonfinite_input_values=0.
- The advanced WaveNet is not a dead/no-trade model: selected_rate is ~41.87% validation and ~40.10% test.
- Action/top/bottom heads materially improved versus the rejected simple Conv2D sanity run.

LIMITS:
- This is still a research classifier/pattern model, not a trading system.
- No PnL, spread/slippage, TP/SL, max-hold, or walk-forward trading validation is present in this report.
- The gate is intentionally loose: buy_threshold=0.34, sell_threshold=0.34, min_margin=0, min_buy_r=-999, min_sell_r=-999.
- R-head MAE did not materially improve; buy_r/sell_r heads are not yet reliable as trading filters.
- The run uses max_samples=12000, not the full tensor.
```

Decision:

```text
Phase144A v1 is a useful research improvement over the simple Conv2D baseline, but production remains BLOCKED.
Next required evidence is backtest/walk-forward or comparison against Phase145A Option A sequence WaveNet.
No Phase134. No paper shadow. No live trading.
```

## Phase145A operator result — Option A sequence WaveNet v1 — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet\latest.json` for the first operator-machine run of Phase145A Option A.

Run configuration summary:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [24000, 100, 57]
keras_batch_shape : [batch, 100, 57]
feature_count     : 57
m5_feature_count  : 35
htf_feature_count : 22
other_feature_count : 0
loader_mode       : stream
batch_size        : 16
epochs requested  : 80
learning_rate     : 0.0005
nonfinite_input_values : 0
```

Validation metrics:

```text
val_action_accuracy : 0.4604779412
val_top_ap          : 0.2414809241
val_bottom_ap       : 0.1344216114
val_buy_r_mae       : 0.6942731142
val_sell_r_mae      : 0.6847920418
val_selected_rate   : 0.5836397059
```

Test metrics:

```text
test_action_accuracy : 0.4791666667
test_top_ap          : 0.2453369099
test_bottom_ap       : 0.1816515898
test_buy_r_mae       : 0.6652074456
test_sell_r_mae      : 0.6756162643
test_selected_rate   : 0.5719975490
```

Comparison against Phase144A 4D Image WaveNet v1 supplied earlier:

```text
Action accuracy:
  4D Image WaveNet      : val=0.5628, test=0.5970
  Option A Sequence     : val=0.4605, test=0.4792
  Current read          : 4D is stronger on action classification.

Top AP:
  4D Image WaveNet      : val=0.2038, test=0.2328
  Option A Sequence     : val=0.2415, test=0.2453
  Current read          : Option A is slightly stronger on top-zone ranking.

Bottom AP:
  4D Image WaveNet      : val=0.1501, test=0.2357
  Option A Sequence     : val=0.1344, test=0.1817
  Current read          : 4D is stronger on bottom-zone ranking.

Selected rate:
  4D Image WaveNet      : val=0.4187, test=0.4010
  Option A Sequence     : val=0.5836, test=0.5720
  Current read          : Option A is much more aggressive and may over-select.
```

Interpretation:

```text
GOOD:
- Numerically healthy: nonfinite_input_values=0.
- Option A built the intended WaveNet-native tensor: [samples, WindowSize, Features].
- Memory pressure is lower than the 4D interaction tensor.
- Top-zone ranking is slightly better than 4D in this run.

LIMITS:
- Action accuracy is materially lower than the Phase144A 4D Image WaveNet result.
- Bottom-zone AP is lower than 4D.
- selected_rate around 57% is high under the loose diagnostic gate.
- buy_r/sell_r MAE did not improve; R-heads are not yet reliable trading gates.
- The report has no PnL, profit factor, drawdown, spread/slippage, or walk-forward trading validation.
- This is not an apples-to-apples comparison because Phase144A used 12000 samples while Phase145A used 24000 samples and a different feature layout/capacity.
- Feature count is 57. If the owner expected the large historical 5M feature set, the Phase145A tensor build report must be checked for `source_5m_feature_count`.
```

Decision:

```text
Phase145A Option A v1 is technically healthy but not better overall than Phase144A 4D v1 on classifier metrics.
It remains useful as a lower-dimensional research lane, especially for top-zone ranking and RAM efficiency.
Production remains BLOCKED until backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Phase145A source-feature discovery fix — 2026-09-19

The owner supplied the Phase145A sequence tensor build report. It confirmed:

```text
features                  : 57
generated_feature_count   : 57
source_5m_feature_count   : 0
source_5m_feature_path    : not previously reported
```

Interpretation:

```text
The first Option A tensor was technically valid, but it did not include the larger historical 5M feature set.
It was therefore an Option A generated-feature run, not the intended full-source-feature Option A run.
```

Root cause fixed in the builder:

```text
scripts/build_pivot_pattern_sequence_tensor.py
```

New behavior:

```text
--include-source-5m-features 1
```

now auto-probes, in storage mode, before falling back to the plain OHLCV `v*.parquet` file:

```text
datasets\processed\<SYMBOL>\<TF>\hybrid_telemetry_flat_latest.parquet
datasets\processed\<SYMBOL>\<TF>\hybrid_xgboost_matrix_latest.parquet
datasets\processed\<SYMBOL>\<TF>\hybrid_xgboost_matrix_all_5m.parquet
hybrid_*flat*.parquet
hybrid_*matrix*.parquet
plain storage OHLCV v*.parquet
```

Added explicit override:

```text
--source-5m-feature-path PATH
```

GUI update:

```text
Build pivot sequence tensor → Optional source 5M feature parquet/csv
```

Leakage/metadata safeguards:

```text
Blocked source columns include OHLCV identifiers, source_index/tensor_index/sample_index/row_id, target_*, future_*, candidate_*, prediction_*, pred_*, prob_*.
```

The build report now records:

```text
source_5m_feature_path
source_5m_total_columns
source_5m_numeric_candidate_count
source_5m_feature_count
```

Required rerun:

```powershell
python -u scripts\build_pivot_pattern_sequence_tensor.py `
  --source-mode storage `
  --symbol XAUUSD `
  --five-timeframe 5M `
  --hourly-timeframe 1H `
  --h4-timeframe 4H `
  --daily-timeframe 1D `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --window-size 100 `
  --sample-stride 1 `
  --max-samples 0 `
  --include-source-5m-features 1 `
  --max-features 0 `
  --dtype float16 `
  --axis-normalization robust `
  --feature-clip 8 `
  --chunk-size 512 `
  --max-tensor-mb 8192 `
  --output-name pivot_pattern_sequence_tensor_latest `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_tensor
```

If `source_5m_feature_count` remains `0`, then the large 5M feature file is not in the auto-probed project-storage locations and the operator must provide its exact path through the new GUI field or `--source-5m-feature-path`.

Decision:

```text
The previous Phase145A v1 model result should be treated as underfed / generated-feature-only.
Do not compare it as the final full-feature Option A result until the tensor is rebuilt with source_5m_feature_count > 0.
Production remains BLOCKED.
```

Verification in sandbox:

```text
python -m py_compile scripts/build_pivot_pattern_sequence_tensor.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 41 passed

python -m pytest -q
→ blocked in sandbox collection because optional dependencies pyarrow/pywt are not installed here.

python -m ruff / python -m black
→ unavailable in this sandbox image.
```

## Phase145A PowerShell empty optional path fix — 2026-09-19

The owner ran the new Phase145A tensor build command in PowerShell with:

```text
--source-5m-feature-path "" `
```

PowerShell/native argv handling dropped the empty string, so `argparse` saw `--source-5m-feature-path` without a value and failed:

```text
build_pivot_pattern_sequence_tensor.py: error: argument --source-5m-feature-path: expected one argument
```

Fix implemented:

```text
scripts/build_pivot_pattern_sequence_tensor.py
```

The argument now uses:

```text
nargs="?"
const=""
default=""
```

So both forms are safe:

```powershell
# recommended: omit the optional path for auto-probe
--include-source-5m-features 1

# also accepted now if a shell drops the empty value
--source-5m-feature-path
```

Documentation command snippets were updated to omit `--source-5m-feature-path ""` unless an explicit path is actually needed.

Recommended rerun is the same tensor build command, but without the empty path line. If auto-probe still reports `source_5m_feature_count=0`, rerun with an actual feature parquet/csv path.

## Phase143A 4D image tensor health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_image_tensor_health\latest.json` after running the official tensor health audit for the rebuilt 4D pivot image tensor.

Audit command inputs:

```text
tensor_path    : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
meta_path      : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
flat_path      : datasets\processed\XAUUSD\5M\pivot_pattern_image_flat_latest.parquet
builder_report : run_logs\pivot_pattern_image_tensor\latest.json
full_scan      : 1
chunk_size     : 256
```

Result:

```text
status       : PASS
tensor_shape : [53098, 100, 32, 23]
dtype        : float16
flat_rows    : 53197
sample index : min=99 max=53196 step=1
first time   : 2025-11-28 17:05:00+00:00
last time    : 2026-09-02 10:25:00+00:00
```

Full tensor scan:

```text
scanned_cells     : 3,908,012,800
chunks            : 208
nonfinite_cells   : 0
min_value         : -32.0
max_value         : 32.0
max_abs           : 32.0
interaction_clip  : 32.0
warnings          : []
errors            : []
```

Target counts on sampled windows:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Interpretation:

```text
- The 4D image tensor is structurally healthy.
- The full tensor scan found no NaN/Inf cells.
- max_abs equals interaction_clip, so clipping is active and within the configured bound.
- sample_indices are strictly contiguous with stride=1 from 99 to 53196.
- feature_5m_names length matches axis 2: 32.
- feature_htf_names length matches axis 3: 23.
```

Note on target-count difference versus builder report:

```text
Builder target_counts were computed on the flat frame after target availability.
Health-audit target_counts are computed on the sampled tensor windows.
Because window_size=100, the first 99 flat rows are not tensor samples, so small count differences are expected and not an error.
```

Decision:

```text
Phase143A rebuilt 4D pivot image tensor is accepted as healthy for research training.
It is safe to train Phase144A advanced 4D Image WaveNet on this tensor.
Production remains BLOCKED until model backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Phase145A full-source sequence tensor build + health audit command — 2026-09-19

The owner rebuilt the Option A sequence tensor after the source-feature discovery fix. The new build report confirms the intended 3D tensor layout:

```text
stored_x_shape      : [53098, 100, 140]
keras_batch_shape   : [batch, 100, 140]
dtype               : float16
estimated_size_mb   : 1417.8696
samples             : 53098
window_size         : 100
features            : 140
generated_features  : 57
source_5m_features  : 83
source_5m_path      : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
source_total_cols   : 105
source_numeric_candidates : 83
nonfinite_feature_values  : 0
```

Target counts on the flat target-available frame:

```text
SELL : 5,392
HOLD : 43,342
BUY  : 4,463
```

Interpretation:

```text
- This is the intended Option A tensor: [X, Y, Z] = [samples, WindowSize, Features].
- Source 5M features are now included: source_5m_feature_count=83.
- Total feature count is 140 = 57 generated/context features + 83 source 5M features.
- The tensor is much smaller than the 4D interaction tensor: about 1.42 GB float16 versus about 7.45 GB for [53098,100,32,23].
```

Implemented official health audit for the Option A tensor:

```text
scripts/audit_pivot_pattern_sequence_tensor.py
GUI: Audit pivot sequence tensor health
```

The audit checks:

```text
3D rank/shape: [samples, window, features]
metadata/sample alignment
sample_indices monotonicity
timestamp monotonicity
target array presence/length/finite values
feature_names and feature_groups alignment
source_5m feature count consistency
feature scaler finite checks
full tensor NaN/Inf scan
max_abs <= feature_clip
builder report shape/count consistency
```

Command to run on the operator machine:

```powershell
python -u scripts\audit_pivot_pattern_sequence_tensor.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --builder-report run_logs\pivot_pattern_sequence_tensor\latest.json `
  --chunk-size 512 `
  --full-scan 1 `
  --max-scan-samples 0 `
  --fail-on-reported-feature-nonfinite 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_tensor_health
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_tensor_health\latest.json
run_logs\pivot_pattern_sequence_tensor_health\latest.html
```

Verification in sandbox:

```text
python -m py_compile scripts/audit_pivot_pattern_sequence_tensor.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 45 passed
```

Decision:

```text
The full-source Option A sequence tensor build is structurally correct from the builder report.
Run the new health audit before retraining gold_pivot_pattern_sequence_wavenet_5m.
Previous Sequence WaveNet v1 trained on [24000,100,57] remains underfed and should not be treated as final Option A.
Production remains BLOCKED.
No Phase134. No paper shadow. No live trading.
```

## Phase145A full-source sequence tensor health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_tensor_health\latest.json` after running the official Phase145A Option A sequence tensor health audit.

Audit command inputs:

```text
tensor_path    : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta_path      : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
flat_path      : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
builder_report : run_logs\pivot_pattern_sequence_tensor\latest.json
full_scan      : 1
chunk_size     : 512
```

Result:

```text
status            : PASS
tensor_shape      : [53098, 100, 140]
keras_batch_shape : [batch, 100, 140]
dtype             : float16
samples           : 53098
window_size       : 100
features          : 140
flat_rows         : 53197
sample index      : min=99 max=53196 step=1
first time        : 2025-11-28 17:05:00+00:00
last time         : 2026-09-02 10:25:00+00:00
```

Feature composition:

```text
generated_5m_feature_count : 31
source_5m_feature_count    : 83
session_feature_count      : 4
htf_feature_count          : 22
other_feature_count        : 0
source_5m_feature_path     : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
source_5m_numeric_candidates : 83
```

Full tensor scan:

```text
scanned_cells   : 743,372,000
chunks          : 104
nonfinite_cells : 0
min_value       : -8.0
max_value       : 8.0
max_abs         : 8.0
feature_clip    : 8.0
warnings        : []
errors          : []
```

Target counts on sampled tensor windows:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Interpretation:

```text
- This is the intended Option A tensor layout: [X, Y, Z] = [samples, WindowSize, Features].
- The full-source tensor is healthy: rank=3, shape=[53098,100,140], source_5m=83, no NaN/Inf cells.
- max_abs equals feature_clip, so robust normalization/clipping is active and within configured bounds.
- sample_indices are contiguous with stride=1 from 99 to 53196.
- The previous Sequence WaveNet v1 trained on [24000,100,57] is underfed and should not be treated as the final Option A result.
```

Decision:

```text
Phase145A full-source sequence tensor is accepted as healthy for research training.
Next valid training should use this tensor [samples,100,140], not the old [samples,100,57] tensor.
Production remains BLOCKED until backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Gitignore heavy artifact guard — 2026-09-19

The owner asked to prevent heavy local research artifacts from entering git. `.gitignore` was updated and the malformed `config.inirun_logs/` line was corrected to `config.ini`.

New/confirmed ignore coverage includes:

```text
*.npy
*.keras
*.ckpt
*.weights.h5
*.pkl / *.pickle / *.joblib
*.onnx / *.pb / *.tflite
*.feather / *.arrow / *.orc / *.avro / *.zarr/
*.zip / *.7z / *.rar / *.tar / *.tar.gz / *.tgz / *.xz
datasets/raw/
datasets/external/
datasets/processed/
datasets/models/
run_logs/
logs/
```

Verification examples:

```text
datasets/processed/XAUUSD/5M/pivot_pattern_sequence_tensor_latest.npy → ignored
datasets/models/gold_pivot_pattern_sequence_wavenet_5m/v1_model.keras → ignored
run_logs/pivot_pattern_sequence_wavenet/latest.json → ignored
*.zip project snapshots → ignored
```

Note:

```text
Already-tracked small legacy artifacts are not automatically removed by .gitignore.
New heavy tensors/models/run logs will stay out of git.
```

## Phase145A full-source sequence WaveNet training result — 2026-09-19

The owner supplied the completed `run_logs\pivot_pattern_sequence_wavenet\latest.json`, model summary, and batch/epoch logs for the first full-source Option A training run.

Training input:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [24000, 100, 140]
keras_batch_shape : [batch, 100, 140]
feature_count     : 140
m5_feature_count  : 118
htf_feature_count : 22
other_feature_count : 0
loader_mode       : stream
batch_size        : 16
epochs requested  : 80
early_stopping_patience : 8
nonfinite_input_values  : 0
```

Final report metrics, after Keras restored the best `val_loss` weights:

```text
val_action_accuracy : 0.7239583333
val_top_ap          : 0.3654971900
val_bottom_ap       : 0.3324869559
val_buy_r_mae       : 0.6672694683
val_sell_r_mae      : 0.6664603949
val_selected_rate   : 0.2821691176

test_action_accuracy : 0.6200980392
test_top_ap          : 0.2709324875
test_bottom_ap       : 0.3336111266
test_buy_r_mae       : 0.7359182239
test_sell_r_mae      : 0.7348573208
test_selected_rate   : 0.3609068627
```

Important epoch-end observations from `latest_batch_log.jsonl`:

```text
epoch 1 : val_loss=1.9548627, val_action_acc=0.4316789
epoch 2 : val_loss=1.6995431, val_action_acc=0.5508578
epoch 3 : val_loss=1.8116363, val_action_acc=0.5713848
epoch 4 : val_loss=1.6853775, val_action_acc=0.6583946
epoch 5 : val_loss=1.4642649, val_action_acc=0.7239583  ← best val_loss / restored final weights
epoch 6 : val_loss=1.5603150, val_action_acc=0.7110907
epoch 7 : val_loss=1.8318611, val_action_acc=0.6522672
epoch 8 : val_loss=2.0280118, val_action_acc=0.6197917
epoch 9 : val_loss=1.9110000, val_action_acc=0.6666667
epoch 10: val_loss=1.8384161, val_action_acc=0.6727941
epoch 11: val_loss=1.8083678, val_action_acc=0.7086397
epoch 12: val_loss=1.7787350, val_action_acc=0.7037377
epoch 13: val_loss=1.6534641, val_action_acc=0.7414216
```

Architecture confirmation from the model summary:

```text
Input                  : [batch, 100, 140]
5M branch              : [batch, 100, 118]
HTF branch             : [batch, 100, 22]
All-feature branch     : [batch, 100, 140]
Branch fusion          : [batch, 100, 432]
WaveNet temporal core  : 2 residual blocks × dilations 1,2,4,8,16,32
Attention              : temporal_self_attention
Pooling                : avg + max + last
Heads                  : action/top/bottom/buy_r/sell_r
Trainable params       : 1,256,435
Total params reported  : 3,769,307 including optimizer slots
```

Comparison to the underfed Sequence WaveNet v1 `[24000,100,57]`:

```text
Action accuracy:
  underfed sequence : val=0.4605, test=0.4792
  full-source seq   : val=0.7240, test=0.6201

Top AP:
  underfed sequence : val=0.2415, test=0.2453
  full-source seq   : val=0.3655, test=0.2709

Bottom AP:
  underfed sequence : val=0.1344, test=0.1817
  full-source seq   : val=0.3325, test=0.3336

Selected rate:
  underfed sequence : val=0.5836, test=0.5720
  full-source seq   : val=0.2822, test=0.3609
```

Comparison to Phase144A 4D Image WaveNet v1 `[12000,100,32,23]`:

```text
Action accuracy:
  4D image WaveNet  : val=0.5628, test=0.5970
  full-source seq   : val=0.7240, test=0.6201

Top AP:
  4D image WaveNet  : val=0.2038, test=0.2328
  full-source seq   : val=0.3655, test=0.2709

Bottom AP:
  4D image WaveNet  : val=0.1501, test=0.2357
  full-source seq   : val=0.3325, test=0.3336
```

Interpretation:

```text
GOOD:
- Full-source Option A is a material improvement over the underfed 57-feature sequence run.
- It also beats the earlier 4D Image WaveNet classification/AP metrics in this non-identical comparison.
- selected_rate is lower and more controlled than the underfed run.
- No NaN/Inf was reported.
- The architecture is the intended advanced Conv1D/WaveNet adaptation of the 4D model.

LIMITS:
- Training loss kept improving while validation loss bottomed at epoch 5; overfitting after epoch 5 is visible.
- R-head test MAE is still weak: buy_r≈0.736, sell_r≈0.735.
- This is still a classifier/pattern report, not a trading proof.
- No PnL, profit factor, drawdown, spread/slippage, or walk-forward trading validation is present.
- 4D and sequence runs used different sample counts and layouts, so comparison is directional, not final proof.
```

Decision:

```text
Phase145A full-source sequence WaveNet is the strongest pivot-pattern research model so far by classification/AP diagnostics.
It is NOT production-approved.
Next required phase: backtest/PnL audit on sequence WaveNet predictions, followed by walk-forward if backtest is promising.
No Phase134. No paper shadow. No live trading.
```

## Phase146A sequence WaveNet PnL audit implemented — 2026-09-19

Implemented the first research-only PnL audit/backtest for the Phase145A full-source sequence WaveNet.

Implemented files:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
docs/Phases/Phase146.md
docs/Report/PHASE146A_SEQUENCE_WAVENET_BACKTEST_REPORT.md
tests/unit/ai/test_pivot_sequence_wavenet_backtest.py
```

GUI command:

```text
Backtest pivot sequence WaveNet PnL
```

Purpose:

```text
Convert action/top/bottom/buy_r/sell_r predictions into BUY/SELL candidates and run a research-only ATR TP/SL replay with spread, same-bar policy, max-hold, initial capital, and risk-per-trade.
```

Recommended first audit command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_backtest `
  --report-title "Phase146A sequence WaveNet PnL audit"
```

Outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_backtest\latest.json
run_logs\pivot_pattern_sequence_wavenet_backtest\latest.html
run_logs\pivot_pattern_sequence_wavenet_backtest\latest_trades.csv
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 49 passed
```

Production remains blocked until PnL/walk-forward prove edge.

## Phase146A Lambda deserialization fix — 2026-09-19

The owner's first Phase146A run failed while loading the trained Keras model:

```text
ValueError: Requested the deserialization of a `Lambda` layer whose `function` is a Python lambda.
Keras disallowed it by default; use safe_mode=False or enable unsafe deserialization.
```

Root cause:

```text
The Phase145A sequence WaveNet architecture intentionally uses Keras Lambda layers for feature slicing:
- gather_5m_features
- gather_htf_features
- gather_all_features
- last_temporal_state
```

Fix implemented in:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
```

The Phase146A loader now explicitly trusts local project-generated research artifacts:

```python
tf.keras.models.load_model(model_path, safe_mode=False)
```

with a fallback for older tf.keras versions:

```python
tf.keras.config.enable_unsafe_deserialization()
tf.keras.models.load_model(model_path)
```

Scope:

```text
Research-only local artifacts generated by this project.
Do not use this loader for untrusted downloaded Keras models.
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 50 passed
```

The same Phase146A PowerShell command can be rerun after replacing the project with the fixed zip.

## Phase146A Lambda shape-load fallback — 2026-09-19

The owner reran Phase146A after `safe_mode=False`. Keras then passed Lambda security but failed shape inference while deserializing the project-owned Lambda layers:

```text
NotImplementedError: We could not automatically infer the shape of the Lambda's output.
Please specify the output_shape argument for this Lambda layer.
```

Fix implemented:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/train_pivot_pattern_sequence_wavenet.py
```

Changes:

```text
1. Future Phase145A models now save Lambda layers with explicit output_shape for:
   - gather_5m_features
   - gather_htf_features
   - gather_all_features
   - last_temporal_state

2. Phase146A backtest now has a fallback loader for existing saved models:
   - first tries load_model(..., safe_mode=False, compile=False)
   - if Lambda shape inference still fails, rebuilds the architecture from vN_training.json + meta
   - extracts and loads weights from the .keras archive
```

This preserves the architecture while avoiding a retrain just to make the current v1 model loadable.

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```

The same Phase146A PowerShell command should now load the existing v1 model through the fallback path and proceed to prediction/backtest.

