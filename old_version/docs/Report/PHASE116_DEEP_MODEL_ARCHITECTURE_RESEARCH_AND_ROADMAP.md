# فاز ۱۱۶ — جمع‌بندی سرچ عمیق معماری مدل‌ها و نقشهٔ اجرای مدل ترکیبی ShadBotTrader

**تاریخ:** 2026-09-08  
**وضعیت:** ✅ مستند شد / کدنویسی مدل‌های جدید هنوز شروع نشده  
**دامنه:** XAUUSD / Gold روی MT5 / Alpari، تایم‌فریم اصلی 5M، معماری Clean Architecture + DDD

---

## 1) اصل تصمیم

هدف ما دیگر «بزرگ کردن یک شبکه عصبی» نیست. تجربهٔ فاز ۱۰۰ نشان داد که پیش‌بینی عددی direction/score روز بعد، بدون context کافی، edge قابل اعتماد ندارد. مسیر بهتر برای ربات:

```text
چند مدل با وظیفه‌های جدا
+ کالیبراسیون احتمال
+ فیلتر range/risk
+ meta-label / no-trade gate
+ تست معنی‌داری آماری
```

یعنی سیستم نهایی باید یک **کمیتهٔ تصمیم‌گیری** باشد، نه یک مدل تنها.

---

## 2) دیتاست و وظیفهٔ فعلی

دیتاست اصلی فعلی اپراتور:

```text
Symbol      : XAUUSD / Gold
Broker      : Alpari / MetaTrader 5
Timeframe   : 5M
Candles     : ~53,198
Feature cols: 179
Window      : 288 bars = 24 hours
Label       : trend_signal سه‌کلاسه
```

label فعلی:

```text
SELL = اول barrier پایین (-0.5×ATR14) در 288 کندل آینده بخورد
BUY  = اول barrier بالا (+0.5×ATR14) در 288 کندل آینده بخورد
HOLD = هیچ barrier در horizon نخورد
```

این label شبیه ایدهٔ triple-barrier است، اما برای decision نهایی باید با TP/SL واقعی و range model کامل‌تر شود.

---

## 3) دارایی فعلی بسیار مهم ما: مدل‌های Range

اپراتور یادآوری کرد و این باید در roadmap مرکزی بماند:

### 3.1 مدل رنج 1D

```text
gold_range_1d
کارکرد: پیش‌بینی high/low فردا
استفادهٔ درست: daily envelope / محدودهٔ سقف و کف فردا / فیلتر ورود نزدیک سقف و کف روزانه
```

نقش این مدل در سیستم ترکیبی:

```text
- آیا برای فردا فضای حرکت کافی داریم؟
- آیا entry به سقف/کف پیش‌بینی‌شده خیلی نزدیک است؟
- آیا TP پیشنهادی خارج از envelope روزانه است؟
- آیا بازار daily range کافی برای پوشش spread/slippage دارد؟
```

### 3.2 مدل رنج 4H

```text
gold_range_4h
کارکرد: پیش‌بینی high/low چهار ساعت آینده
استفادهٔ درست: ساخت TP/SL محلی برای معاملهٔ بعدی
```

نقش این مدل در سیستم ترکیبی:

```text
BUY  → TP نزدیک high پیش‌بینی‌شدهٔ 4H، SL زیر low/entry با min distance
SELL → TP نزدیک low پیش‌بینی‌شدهٔ 4H، SL بالای high/entry با min distance
```

نتیجه: مدل direction نباید به تنهایی معامله باز کند. حتی اگر `trend_signal` بگوید BUY، اگر 4H range فضای سود کافی ندهد یا 1D envelope مخالف باشد، تصمیم باید `NO_TRADE` شود.

---

## 4) یافته‌های سرچ عمیق — فقط چیزهای واقعاً قابل استفاده برای ما

### 4.1 Qlib / مدل‌های Quant production-grade

Microsoft Qlib مدل‌های LightGBM، CatBoost، XGBoost، MLP، LSTM، GRU، ALSTM، GAT، SFM، TFT، TabNet، DoubleEnsemble، TCTS، Transformer، Localformer، TRA و TCN را در Model Zoo دارد. در benchmarkهای Qlib، LightGBM روی Alpha158/Alpha360 یکی از قوی‌ترین baselineهاست و در جدول CSI300/Alpha158 عملکرد بسیار قوی‌تر از Linear/MLP نشان داده است.

برای ما:

```text
اولویت بالا: LightGBM/CatBoost/XGBoost branch
```

منبع:

```text
https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md
https://github.com/microsoft/qlib/blob/main/README.md
```

### 4.2 LARA — trade opportunity / noisy-label handling

LARA برای مشکل اصلی بازار ساخته شده: دادهٔ مالی نویزی است و labelها هم می‌توانند noisy باشند. LARA دو ایده دارد:

```text
LA-Attention: پیدا کردن نمونه‌های احتمالاً profitable
RA-Labeling : اصلاح/کم‌اثر کردن labelهای noisy
```

در نتایج paper، LARA روی stocks/crypto/ETF از LightGBM، DoubleEnsemble، TCTS، iTransformer، PatchTST و TimesNet بهتر گزارش شده است.

برای ما:

```text
بعد از calibration، noisy-label / confident-sample filter باید اضافه شود.
```

منبع:

```text
https://arxiv.org/html/2107.11972v4
```

### 4.3 TRA — Mixture-of-Experts برای رژیم‌های مختلف بازار

TRA یک router دارد که نمونه‌ها را به چند predictor متفاوت می‌فرستد. ایدهٔ آن برای طلا مهم است چون طلا در sessionها و رژیم‌های مختلف یکسان رفتار نمی‌کند:

```text
Asia quiet range
London open
New York volatility
FOMC/NFP/news spike
low-volatility chop
high-volatility trend
```

برای ما:

```text
Phase بعدی می‌تواند router سادهٔ rule-based/regime-based داشته باشد؛
بعداً اگر داده کافی بود TRA-style learned router.
```

منبع:

```text
https://arxiv.org/abs/2106.12950
```

### 4.4 Gradient Boosting + Tabular / AutoML

کتاب/ریپوی Machine Learning for Trading و benchmarkهای tabular نشان می‌دهند که برای featureهای مهندسی‌شده، CatBoost/LightGBM/XGBoost هنوز بسیار قوی هستند. AutoGluon هم با weighted ensemble چند مدل مختلف، معمولاً از مدل‌های تکی بهتر می‌شود.

برای ما:

```text
اول train-only feature summary بسازیم، بعد LGBM/CatBoost/XGBoost را کنار WaveNet بگذاریم.
```

منابع:

```text
https://github.com/stefan-jansen/machine-learning-for-trading
https://proceedings.mlr.press/v224/shchur23a.html
```

### 4.5 InceptionTime / MiniRocket / LITE

این‌ها برای time-series classification مناسب‌اند، نه فقط price regression. مزیت‌شان نسبت به WaveNet تنها:

```text
چند scale/pattern متفاوت را هم‌زمان می‌گیرند.
MiniRocket بسیار سریع است و برای benchmark کم‌هزینه خوب است.
```

برای ما:

```text
به عنوان benchmark بعد از branchهای tabular و POS/NEG اضافه شود.
```

منابع:

```text
https://ar5iv.labs.arxiv.org/html/1909.04939
https://research.monash.edu/en/publications/minirocket-a-very-fast-almost-deterministic-transform-for-time-se/
```

### 4.6 xLSTM-TS / TSMixer / PatchTST / Mamba / KAN

این‌ها ارزش تحقیقاتی دارند، ولی اولویتشان بعد از مدل‌های سبک‌تر است:

```text
xLSTM-TS + wavelet denoising: جذاب برای financial trend prediction
TSMixer/TiDE: سبک و جدی برای forecasting
PatchTST: transformer patch-based برای long lookback
Mamba: state-space sequence مدل سبک‌تر از attention کامل
KAN/KANsLTformer: gold-specific research جذاب، ولی جدید و نیازمند audit سنگین
```

برای ما:

```text
فقط به عنوان benchmark کنترل‌شده؛ نه جایگزینی فوری production.
```

منابع نمونه:

```text
https://arxiv.org/abs/2408.12408
https://arxiv.org/abs/2306.09364
https://github.com/yuqinie98/PatchTST
https://arxiv.org/abs/2402.18959
https://www.zgglkx.com/EN/abstract/abstract20218.shtml
```

### 4.7 DeepLOB / TLOB / LiT — فقط با tick/order-book

این‌ها برای Limit Order Book ساخته شده‌اند و روی LOB benchmarkها قوی‌اند، اما دیتای فعلی ما OHLCV/feature روی 5M است. بدون tick/bid/ask/DOM واقعی نباید این معماری‌ها را وارد کنیم.

برای ما:

```text
اگر MT5/Alpari tick + spread + depth قابل ذخیره‌سازی قابل اعتماد داد، فاز جدا باز شود.
```

منابع:

```text
https://arxiv.org/abs/1808.03668
https://arxiv.org/html/2502.15757v3
```

---

## 5) معماری ترکیبی پیشنهادی نهایی

```text
XAUUSD 5M candles/features
        |
        |------------------------------
        |              |              |
  WaveNet/TCN    Tabular Boosters   Time-series classifiers
 trend_signal    LGBM/CAT/XGB       MiniRocket/LITE later
        |              |              |
        -------- calibrated probabilities
                       |
          POS/NEG specialist models
          buy_event + sell_event
                       |
       Range branch: 1D envelope + 4H TP/SL
                       |
       Meta-label / LARA-style trade filter
                       |
       Conformal/Bayesian uncertainty gate
                       |
              BUY / SELL / NO_TRADE
```

---

## 6) ترتیب اجرای پیشنهادی از همین‌جا

### قدم صفر — وضعیت عملیاتی فعلی اپراتور

از نظر کد، فازهای ۱۰۸ و ۱۰۹ آماده‌اند؛ اما اپراتور هنوز مدل `trend_signal` را با تنظیمات فاز ۱۰۸ train می‌کند و نتیجهٔ نهایی ارسال نشده است. بنابراین ترتیب واقعی همین است:

```text
current Phase108 trend_signal training finish
→ QUALITY / SAVED / KEPT metrics
→ Phase109 calibration روی همان مدل جدید
```

اگر `val_buy_sell_f1` و calibration action_precision افتضاح بود، قبل از مدل جدید باید target/horizon/barrier را بازتنظیم کنیم.

### قدم 1 — Phase 110

```text
Train-only feature selection
```

هدف: حذف noise و redundancy از 179 feature بدون leakage.

### قدم 2 — Phase 112A

```text
Tabular booster branch:
LightGBM / CatBoost / XGBoost
```

هدف: سریع‌ترین benchmark قوی برای featureهای مهندسی‌شده.

### قدم 3 — Phase 111

```text
BUY/SELL binary specialists
```

هدف: دو مدل جدا برای تشخیص BUY و SELL، با threshold جدا.

### قدم 4 — Phase 116

```text
Hybrid range-aware decision engine
```

اینجا مدل‌های direction با مدل‌های range موجود ترکیب می‌شوند:

```text
trend_signal/booster/POSNEG → side confidence
1D range → daily envelope / no-trade zone
4H range → TP/SL local bracket
meta/conformal → trade/no-trade
```

### قدم 5 — Phase 113

```text
Significance checks
```

هدف: بفهمیم نتیجه از random بهتر است یا فقط حاصل data-snooping است.

### قدم 6 — Phase 114

```text
External/regime features
```

DXY، US10Y، VIX، Oil، Silver، calendar/news flags.

### قدم 7 — Phase 117

```text
Advanced neural benchmarks
```

MiniRocket/LITE، xLSTM-TS، TSMixer، PatchTST، Mamba/KANsLTformer.

### قدم 8 — Phase 115

```text
Live decision audit
```

قبل از live جدی، هر decision باید قابل بازسازی باشد.

### قدم اختیاری — Phase 118

```text
Tick/order-book branch
```

فقط اگر دیتای واقعی microstructure قابل اعتماد داشته باشیم.

---

## 7) تصمیم درباره GUI

در همین فاز، GUI بدون حذف قابلیت‌ها خلوت شد:

```text
- پارامترهای پرریسک/کم‌مصرف زیر Advanced options رفتند.
- فرم‌های Train/Retrain/Optimise/Backtest/Replay/Audit/Calibration ساده‌تر شدند.
- handlerها همان defaults را می‌گیرند؛ رفتار training/backtest عوض نشده.
```

اصل تصمیم:

```text
GUI ساده برای کار روزانه، ولی کنترل‌های expert حذف نشوند.
```

---

## 8) معیار انتخاب «بهتر از مدل فعلی»

هیچ مدل جدیدی صرفاً چون اسمش modern است وارد production نمی‌شود. باید این‌ها را روی همان splitها ببرد:

```text
val_buy_sell_f1
val_macro_f1
BUY precision/recall/F1
SELL precision/recall/F1
action_precision بعد از calibration
coverage/trade_count
PnL با spread/slippage
max drawdown
Monte Carlo p-value / random baseline
```

اگر فقط train بهتر بود ولی validation/calibration/backtest بهتر نشد، مدل رد می‌شود.
