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
- `Phase108` از نظر کد انجام شد: training مدل `trend_signal` حالا گزینهٔ GUI/CLI برای
  `--class-weight auto` دارد، وزن کلاس‌ها per-fold train محاسبه می‌شود و metricهای
  F1/precision/recall/PR-AUC per-class ذخیره و چاپ می‌شوند. **وضعیت عملیاتی اپراتور:**
  آموزش واقعی فاز ۱۰۸ هنوز در حال اجراست و نتیجهٔ نهایی هنوز ارسال نشده است.
- `Phase109` از نظر کد انجام شد: script و GUI جدید `Calibrate trend-signal thresholds` برای
  grid کردن BUY/SELL probability thresholds و ذخیره `decision_thresholds` در model
  record اضافه شد. **وضعیت عملیاتی:** اجرای calibration منتظر پایان training فاز ۱۰۸ و
  ذخیره‌شدن مدل جدید `gold_trend_signal_5m` است.
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

## نقشهٔ مدل ترکیبی پیشنهادی

دارایی‌های فعلی که باید محور سیستم باشند:

```text
gold_range_1d  → سقف/کف فردا و daily envelope
gold_range_4h  → سقف/کف چهار ساعت آینده برای TP/SL محلی
gold_trend_signal_5m → احتمال SELL/HOLD/BUY
```

هدف بعدی این نیست که فقط یک مدل neural بزرگ‌تر بسازیم؛ هدف ساخت decision engine چندشاخه‌ای است:

```text
WaveNet trend_signal
+ LightGBM/CatBoost/XGBoost branch
+ BUY/SELL specialist models
+ 1D range envelope
+ 4H TP/SL range bracket
+ meta-label / uncertainty no-trade gate
=> BUY / SELL / NO_TRADE
```

ترتیب عملی جدید، با توجه به اینکه training فاز ۱۰۸ هنوز روی سیستم اپراتور تمام نشده:

```text
finish Phase108 trend_signal training → Phase109 calibration → Phase110 feature selection
→ Phase120 anti-collapse metrics → Phase121/112 booster branch benchmark
→ Phase111 BUY/SELL specialists → Phase110 feature selection for winning branches
→ Phase116 hybrid range-aware decision engine → Phase113 significance checks
→ Phase114 external/regime features → Phase117 advanced neural benchmarks
→ Phase115 live decision audit
```

## گام بعدی

1. روی سیستم اپراتور optional booster backend نصب شود:
   `pip install -r requirements-boosters.txt`
2. از GUI/CLI دستور `Build hybrid XGBoost matrix` اجرا شود تا خروجی booster/WaveNet/range به یک
   ماتریس نهایی برای XGBoost تبدیل شود.
3. اگر ساخت ماتریس با range_1d/range_4h موفق بود، فاز ۱۲۴ برای آموزش head نهایی XGBoost/LightGBM
   روی همین ماتریس اجرا شود.
4. اگر مدل‌های range در نام پیش‌فرض نبودند، `--range-1d-model-id` و `--range-4h-model-id` اصلاح شوند.
