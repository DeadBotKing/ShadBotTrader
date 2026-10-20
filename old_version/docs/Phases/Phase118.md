# فاز ۱۱۸ — پیشنهاد اختیاری: Tick / Spread / Order-Book Branch

**وضعیت:** 🟡 اختیاری / نیازمند دیتای واقعی بروکر  
**نوع:** Market microstructure / high-frequency branch  
**اولویت:** فقط اگر MT5/Alpari دیتای لازم را قابل اعتماد بدهد

---

## هدف

استفاده از اطلاعات microstructure برای بهبود سیگنال‌های کوتاه‌مدت XAUUSD.

مدل‌هایی مثل DeepLOB، TransLOB، TLOB و LiT برای دادهٔ Limit Order Book ساخته شده‌اند، نه برای OHLCV معمولی. بنابراین تا وقتی فقط candleهای 5M داریم، این فاز نباید اجرا شود.

---

## دیتای لازم

حداقل:

```text
tick time
bid
ask
spread
last price optional
volume/tick_volume
```

اگر broker بدهد:

```text
Depth of Market / DOM
best bid/ask levels
bid/ask volume per level
order book snapshots
```

---

## معماری‌های قابل بررسی

```text
DeepLOB: CNN + Inception + LSTM
TransLOB: causal CNN + masked self-attention
TLOB/LiT: structured patches + spatial/temporal attention
MLPLOB: ساده‌تر اما در بعضی benchmarkها قوی
```

---

## ارتباط با سیستم فعلی

این branch نباید جایگزین سیستم 5M شود. خروجی آن فقط یک input اضافی به decision engine فاز ۱۱۶ است:

```text
microstructure_branch_prob
spread_regime
execution_quality_score
short-term adverse-selection risk
```

مثال:

```text
trend_signal BUY است
range_4h TP/SL خوب است
ولی spread/tick branch می‌گوید adverse selection بالاست
=> NO_TRADE یا size کمتر
```

---

## هشدار leakage/latency

```text
- tickها باید دقیقاً تا قبل از decision timestamp باشند.
- هیچ snapshot بعد از کندل تصمیم نباید وارد feature شود.
- latency اجرای MT5 باید اندازه‌گیری شود.
- spread واقعی باید در backtest لحاظ شود.
```

---

## معیار پذیرش

```text
- ذخیرهٔ tick/order-book با timestamp دقیق و timezone روشن
- feature causality audit
- backtest با spread واقعی/متغیر
- مقایسه با سیستم بدون microstructure
- اگر فقط ML metric بهتر شد ولی PnL بهتر نشد، branch رد شود.
```
