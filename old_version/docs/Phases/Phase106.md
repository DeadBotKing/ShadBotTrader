# فاز ۱۰۶ — بررسی Alpaca / ari99 / Onepagecode و خلوت‌سازی workspace

**تاریخ:** 2026-09-07
**وضعیت:** ✅ کامل — گزارش مستند شد و workspace خلوت شد
**Commit:** `f4592f2`
**گزارش:** `docs/Report/PHASE106_ALPACA_ARI99_ONEPAGECODE_REVIEW_AND_SHADBOT_PLAN.md`

---

## منابع بررسی‌شده

```text
https://alpaca.markets/learn/tensorflow-market-forecasting
https://github.com/ari99/algorithmic_trading
https://onepagecode.substack.com/p/an-algo-trading-framework-using-tensorflow
```

---

## کدی که وارد workspace شد

Repo زیر برای بررسی clone شد:

```text
/home/user/algorithmic_trading
commit: c8479f3
```

بعد از استخراج اطلاعات، برای خلوت‌کردن workspace حذف شد. اطلاعات لازم در گزارش Phase106 ثبت است.

---

## cleanup انجام‌شده

از top-level workspace حذف شدند:

```text
TensorFlow-stocks-prediction-Machine-learning-RealTime/
algorithmic_trading/
.keras/
ShadBotTrader*.zip های قدیمی
chart_price.png
chart_score_hist.png
chart_why.png
```

بعد از cleanup فقط موارد اصلی باقی ماندند:

```text
/home/user/ShadBotTrader
/home/user/uploads
zip نهایی همان فاز
```

---

## خلاصه Alpaca

- MLP آموزشی برای binary classification جهت روز بعد.
- featureها فقط RSI14/RSI50/STOCH K/D بودند.
- تأکید روی normalized indicators.
- نتیجهٔ مقاله: overfit و فقط کمی بهتر از random.
- پیشنهاد: featureهای بیشتر، windowهای زمانی، neutral class، thresholdهای بهتر، ML فقط به عنوان indicator کمکی.

نتیجه برای ما:

```text
trend_signal/HOLD/ATR barrier بهتر از close-to-close یا score regression است.
```

---

## خلاصه ari99

ایده‌های ارزشمند:

```text
- long/short models جدا
- longEntry/shortEntry برای periods 10/20/50/100
- feature shift(1) برای جلوگیری از leakage
- two-branch model: returns sequence + engineered features
- class weights و output bias
- threshold grid برای LongMin × ShortMin
- VectorBT backtest و heatmap
- random portfolio baseline
- Monte Carlo / White Reality Check
- paper trading audit idea
```

چیزهایی که مستقیم نباید کپی شود:

```text
vectorbtpro dependency
license نامشخص
notebook-heavy exploratory code
monitor train AUC به جای val metric
threshold optimization روی recent data برای live
Alpaca-specific execution
```

---

## خلاصه Onepagecode

- Alpha Vantage fetch + indicators + merge by date.
- preprocessing با ffill/bfill/zero fallback.
- chronological split.
- MinMaxScaler فقط روی train fit می‌شود؛ test transform می‌شود.
- MLP regression برای next adjusted close با MSE/relative error.
- source کامل پشت paywall بود.

نتیجه برای ما:

```text
برای مدل‌های tabular/MLP/tree آینده، train-only scaler مهم است.
اما price regression هدف مناسبی برای ما نیست.
```

---

## تصمیم roadmap بعد از فاز ۱۰۶

مسیر پیشنهادی:

```text
Phase 107: trend_signal audit
Phase 108: class weights + F1/PR-AUC
Phase 109: threshold calibration/heatmap
Phase 110: train-only feature selection
Phase 111: POS/NEG binary event models
Phase 112: two-branch benchmark
Phase 113: random/Monte Carlo/White significance
Phase 114: external/regime features for XAUUSD
Phase 115: live decision audit
```
