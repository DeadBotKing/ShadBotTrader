# فاز ۱۱۱ — پیشنهاد: مدل‌های binary POS/NEG برای event trading

**وضعیت:** 🟡 پیشنهادی / آمادهٔ اجرا
**نوع:** Model family / target variant
**اولویت:** بالا بعد از فاز ۱۰۸ و ۱۰۹

---

## هدف

به جای یک softmax سه‌کلاسه، BUY و SELL جداگانه train شوند. این ایده در Leci37 و ari99 هر دو دیده شد و برای imbalance مفید است.

---

## مدل‌های پیشنهادی

```text
gold_buy_event_5m
  output: sigmoid
  target: BUY vs NOT_BUY

gold_sell_event_5m
  output: sigmoid
  target: SELL vs NOT_SELL
```

یا به عنوان option در trend_signal:

```text
--event-mode multiclass|buy|sell
```

---

## target

از labelهای موجود `trend_signal`:

```text
BUY_EVENT  = 1 اگر class=BUY، وگرنه 0
SELL_EVENT = 1 اگر class=SELL، وگرنه 0
```

یا در آینده targetهای جدا:

```text
first hit +X*ATR → BUY_EVENT
first hit -X*ATR → SELL_EVENT
```

---

## decision logic

```text
اگر buy_prob >= buy_threshold و sell_prob < sell_block_threshold → BUY candidate
اگر sell_prob >= sell_threshold و buy_prob < buy_block_threshold → SELL candidate
اگر هر دو بالا → ambiguous / no trade
اگر هر دو پایین → HOLD / no trade
```

Candidate هنوز معاملهٔ نهایی نیست. در فاز ۱۱۶ باید با مدل‌های range ترکیب شود:

```text
BUY candidate  + range_4h فضای TP بدهد + range_1d سقف روزانه اجازه بدهد → BUY
SELL candidate + range_4h فضای TP بدهد + range_1d کف روزانه اجازه بدهد → SELL
```

---

## مزیت

```text
- کنترل بهتر imbalance
- threshold جدا برای BUY و SELL
- تشخیص حالت ambiguous وقتی هر دو مدل strong هستند
- سازگاری با ensemble/consensus
```

---

## فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/model_roles.py
src/ShadBotTrader/infrastructure/ai/target_builder.py
src/ShadBotTrader/application/services/dual_model_service.py
src/ShadBotTrader/presentation/gateway/range_forecast_inspector.py
scripts/run_dual_models.py
```

---

## معیار پذیرش

```text
- مدل‌ها با ModelCatalogue دیده شوند.
- predictor خروجی sigmoid probability بدهد.
- threshold calibration جدا برای buy/sell داشته باشند.
- triple backtest بتواند از آنها به عنوان license استفاده کند.
```
