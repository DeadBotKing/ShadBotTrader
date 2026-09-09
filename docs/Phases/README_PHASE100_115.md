# فهرست فازهای ۱۰۰ تا ۱۱۹

> نام فایل برای سازگاری با handoff قبلی همان `README_PHASE100_115.md` مانده، اما محتوا تا فاز ۱۱۹ به‌روزرسانی شده است.

این فایل index سریع فازهای بعد از مدل score، بررسی منابع خارجی، مسیر `trend_signal`، و نقشهٔ مدل ترکیبی است.

---

## وضعیت عملیاتی فعلی

نکتهٔ مهم: از نظر کدنویسی، ابزارهای فازهای ۱۰۸ و ۱۰۹ آماده‌اند؛ اما روی سیستم اپراتور هنوز training واقعی فاز ۱۰۸ در حال اجراست. بنابراین فاز ۱۰۹ فعلاً **پیاده‌سازی‌شده ولی اجرا/کالیبراسیون عملیاتی آن منتظر پایان آموزش فاز ۱۰۸ است**.

```text
وضعیت runtime اپراتور: Phase108 training in progress
گام بعدی بعد از پایان train: Phase109 calibration روی همان مدل ذخیره‌شده
```

---

## فازهای انجام‌شده/آماده

| فاز | وضعیت | خلاصه | فایل |
|---|---|---|---|
| 100 | ✅ کامل | `trend_score` روی کندل واقعی 1D، آموزش v1، model card و verdict بدون edge | `Phase100.md` |
| 101 | ✅ کامل | رفع live log آموزش GUI روی Windows | `Phase101.md` |
| 102 | ✅ کامل | گزینهٔ MAE برای `trend_score` و monitor روی `val_mae` | `Phase102.md` |
| 103 | ✅ کامل | audit محاسبه/normalization score و حذف fake tail label | `Phase103.md` |
| 104 | ✅ کامل | input scaling مخصوص `trend_score` به `[-1,+1]` | `Phase104.md` |
| 105 | ✅ کامل/docs | بررسی پروژه Leci37 و استخراج الگوهای قابل استفاده | `Phase105.md` |
| 106 | ✅ کامل/docs | بررسی Alpaca، ari99، Onepagecode و cleanup workspace | `Phase106.md` |
| 107 | ✅ کامل | audit کامل `trend_signal` و label distribution/roll-forward folds + GUI | `Phase107.md` |
| 108 | ✅ کد کامل / 🟡 آموزش واقعی در حال اجرا | class weights + per-class F1/PR-AUC برای `trend_signal` + GUI؛ اپراتور هنوز training این فاز را تمام نکرده | `Phase108.md` |
| 109 | ✅ کد کامل / ⏳ اجرای عملیاتی بعد از train | threshold calibration و heatmap برای `trend_signal` آماده است؛ فقط بعد از ذخیره‌شدن مدل جدید فاز ۱۰۸ اجرا شود | `Phase109.md` |
| 119 | ✅ کامل | GUI cleanup: پارامترهای پیشرفته زیر `Advanced options` رفتند، بدون حذف قابلیت‌ها | `Phase119.md` |
| 120 | ✅ کامل | Anti-collapse metrics برای جلوگیری از always-BUY/always-SELL و monitoring سخت‌گیرانه‌تر | `Phase120.md` |
| 121 | ✅ زیرساخت کامل | Tabular Booster Branch برای `trend_signal`: LightGBM/XGBoost/CatBoost + GUI | `Phase121.md` |
| 122 | ✅ کامل | Calibration برای BUY/SELL booster specialists و ذخیرهٔ threshold مشترک | `Phase122.md` |
| 123 | ✅ ماتریس کامل | ساخت ماتریس نهایی XGBoost از خروجی booster/WaveNet و مدل‌های range 1D/4H | `Phase123.md` |
| 124 | ✅ CLI کامل | آموزش head نهایی XGBoost/LightGBM روی ماتریس hybrid فاز ۱۲۳ | `Phase124.md` |
| 125 | ✅ CLI/GUI کامل | calibration و backtest معاملاتی hybrid head با TP/SL از range_4h و فیلتر range_1d | `Phase125.md` |

---

## فازهای پیشنهادی مدل/استراتژی

| فاز | وضعیت | خلاصه | اولویت |
|---|---|---|---|
| 110 | 🟡 پیشنهادی | feature selection مخصوص مدل و train-only، بدون leakage | خیلی بالا |
| 111 | 🟡 پیشنهادی | مدل‌های BUY/SELL binary specialist (`gold_buy_event_5m`, `gold_sell_event_5m`) | خیلی بالا |
| 112 | 🟡 پیشنهادی | Branch benchmark: LightGBM/CatBoost/XGBoost، two-branch neural، MiniRocket/LITE/InceptionTime | خیلی بالا برای boosters |
| 113 | ✅ CLI/GUI کامل | random baseline، Monte Carlo و White Reality-style max check برای hybrid-head/range-aware | قبل از live الزامی |
| 114 | 🟡 پیشنهادی | external/regime features مخصوص XAUUSD: DXY، US10Y، VIX، Oil، Silver، calendar/news | بالا بعد از baseline |
| 115 | 🟡 پیشنهادی | live decision audit کامل برای هر TRADE/NO_TRADE | قبل از live جدی الزامی |
| 116 | ✅ CLI/GUI integration audit | Hybrid Range-Aware Decision Engine: hybrid head + saved thresholds + `range_1d`/`range_4h` وارد Strategy/Decision/Risk/Intent path شد | قبل از Phase115 |
| 117 | 🟡 پیشنهادی | Advanced neural benchmarks: xLSTM-TS، TSMixer، PatchTST، Mamba، KANsLTformer | متوسط/تحقیقاتی |
| 118 | 🟡 اختیاری | Tick/order-book branch: DeepLOB/TLOB/LiT فقط اگر دیتای microstructure واقعی داشته باشیم | مشروط |

---

## ترتیب اجرای عملی پیشنهادی از همین‌جا

این ترتیب مهم‌تر از شمارهٔ فایل‌هاست:

```text
A) صبر برای پایان training فعلی trend_signal
B) اجرای Phase109 calibration روی همان مدل
C) Phase120: anti-collapse معیارها برای رد always-BUY/always-SELL
D) Phase121/112A: LightGBM/CatBoost/XGBoost branch benchmark
E) Phase111/121: BUY/SELL specialist binary models
F) Phase122: calibration مشترک BUY/SELL booster specialists
G) Phase123: ساخت Hybrid XGBoost matrix با خروجی WaveNet/Boosters/Range
H) Phase124: آموزش XGBoost/LightGBM head نهایی روی ماتریس hybrid
I) Phase125: range-aware TP/SL backtest و ذخیرهٔ threshold سودده
J) Phase113: significance / random / Monte Carlo checks
K) Phase116: range-aware hybrid decision engine integration اگر significance تأیید شد
L) Phase110: train-only feature selection برای branchهای برنده
M) Phase114: external/regime features اگر baseline ارزشمند بود
N) Phase117: advanced neural benchmarks
O) Phase115: live decision audit کامل قبل از live جدی
P) Phase118: order-book/tick فقط در صورت داشتن دیتای واقعی
```

---

## طرح ترکیب نهایی مدل‌ها

دارایی‌های فعلی که باید محور باشند:

```text
gold_range_1d  → high/low فردا، daily envelope
gold_range_4h  → high/low چهار ساعت آینده، TP/SL محلی
gold_trend_signal_5m → SELL/HOLD/BUY probability
```

طرح هدف:

```text
XAUUSD 5M features
        |
        |------------------------------
        |              |               |
     WaveNet       Boosters        POS/NEG specialists
 trend_signal   LGBM/CAT/XGB      buy_event/sell_event
        |              |               |
        -------- calibrated probabilities
                       |
        Range filters: 1D envelope + 4H TP/SL
                       |
         Meta-label / uncertainty / no-trade gate
                       |
               BUY / SELL / NO_TRADE
```

---

## دلیل این ترتیب

```text
1. اول باید target/metric/calibration درست باشد؛ فازهای 107-109 همین کار را کردند.
2. بعد باید noise featureها کم شود؛ Phase110.
3. بعد سریع‌ترین benchmark قوی را اضافه می‌کنیم؛ LightGBM/CatBoost/XGBoost.
4. بعد BUY و SELL را جدا متخصص می‌کنیم؛ Phase111.
5. بعد همه را با range_1d/range_4h به decision واقعی وصل می‌کنیم؛ Phase116.
6. بعد ثابت می‌کنیم نتیجه شانسی نیست؛ Phase113.
7. بعد features بیرونی/regime و مدل‌های پیشرفته را اضافه می‌کنیم؛ Phase114/117.
```

---

## گزارش سرچ عمیق جدید

جزئیات منابع، مدل‌های بررسی‌شده و تصمیم نهایی در این گزارش ثبت شد:

```text
docs/Report/PHASE116_DEEP_MODEL_ARCHITECTURE_RESEARCH_AND_ROADMAP.md
```

گزارش اجرای فازهای ضد-collapse و booster branch:

```text
docs/Report/PHASE120_121_ANTI_COLLAPSE_AND_BOOSTER_BRANCH_REPORT.md
```

---

## handoff کامل

برای شروع چت جدید:

```text
docs/SESSION_HANDOFF_2026-09-07.md
docs/CURRENT_STATE.md
docs/Phases/README_PHASE100_115.md
```
