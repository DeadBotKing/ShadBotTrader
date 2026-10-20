# فاز ۱۱۴ — پیشنهاد: external/regime features مخصوص XAUUSD

**وضعیت:** 🟡 پیشنهادی
**نوع:** Feature expansion، نیازمند proposal جدا برای data source
**اولویت:** متوسط/بالا

---

## دلیل

تحلیل فاز ۱۰۰ نشان داد price-only daily score حافظهٔ کمی دارد:

```text
corr(score_t, score_t+1) ≈ 0.0017
```

برای جهت طلا، فقط OHLCV طلا ممکن است کافی نباشد. باید regime/macro context وارد شود.

---

## featureهای پیشنهادی

```text
DXY returns/trend
US10Y yield / change
real yield proxy
VIX level/change
WTI/Brent oil returns/trend
Silver/XAGUSD یا SI futures returns/trend
COMEX session/calendar context
CPI/FOMC/NFP calendar flags
London/NY session flags
day-of-week
week-of-month
weekly close location
volatility regime
opening gap
previous-day close location
```

---

## منابع احتمالی

```text
Yahoo Finance برای proxyهای آزاد
FRED برای yield/real yield اگر دسترسی مجاز باشد
تقویم اقتصادی دستی/CSV برای event flags
MT5 symbols اگر broker ارائه دهد
```

---

## اصل معماری

این کار نباید featureهای external را مستقیم داخل model code hard-code کند. باید provider/resolver تمیز داشته باشد:

```text
Domain/Application دست‌نخورده
Infrastructure provider جدید
Feature catalogue extension
Causality audit الزامی
```

---

## معیار پذیرش

```text
- هر external feature timestamp-aligned و causal باشد.
- missing data policy صریح باشد.
- feature availability در live مشخص باشد.
- بدون data source معتبر، مدل نباید silently از مقدار fake استفاده کند.
```

---

## هشدار

این فاز نیاز به تصمیم اپراتور دارد چون ممکن است API/data source جدید یا فایل CSV خارجی لازم داشته باشد.
