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
