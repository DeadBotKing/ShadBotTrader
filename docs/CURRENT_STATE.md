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
