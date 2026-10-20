# فاز ۱۱۵ — پیشنهاد: live decision audit کامل

**وضعیت:** 🟡 پیشنهادی
**نوع:** Observability / execution safety
**اولویت:** متوسط، قبل از live جدی الزامی

---

## هدف

هر تصمیم live یا backtest مهم باید قابل بازسازی باشد. اگر بعداً پرسیده شود چرا trade باز شد/نشد، باید همهٔ ورودی‌ها و licenseها ثبت باشند.

---

## اطلاعاتی که باید برای هر decision ثبت شود

```text
timestamp
symbol
timeframe
broker/account profile
model_id/model_version برای همه مدل‌ها
feature fingerprint
input window range
prediction probabilities/scores
thresholds calibrated/default
range_1d forecast high/low/ATR و فاصله تا سقف/کف فردا
range_4h forecast high/low/ATR و TP/SL پیشنهادی چهار ساعت آینده
trend color
trend_signal probabilities
booster/POSNEG/meta probabilities در صورت فعال بودن
licenses pass/fail با reason
spread/slippage
entry/TP/SL پیشنهادی
order intent
broker response
position state before/after
```

---

## خروجی پیشنهادی

```text
run_logs/live_decisions.jsonl
یا table جدید در shadbot.db: decision_audit
```

برای شروع کم‌ریسک‌تر:

```text
JSONL اول، بعد اگر لازم شد DB table
```

---

## فایل‌های درگیر

```text
src/ShadBotTrader/application/services/dual_model_backtest_service.py
src/ShadBotTrader/infrastructure/simulation/dual_model_prediction_source.py
src/ShadBotTrader/execution_cli.py یا execution services
src/ShadBotTrader/dashboard_cli.py optional display
```

---

## معیار پذیرش

```text
- برای هر NO_TRADE reason ثبت شود.
- برای هر TRADE همهٔ مدل‌ها و thresholdها ثبت شوند.
- log قابل parse باشد.
- اطلاعات محرمانه account/password هرگز ثبت نشود.
```
---

## GUI/operator execution requirement

این فاز حتماً باید از Dashboard قابل اجرا باشد، چون اپراتور نباید live/paper audit را با دستورهای دستی و طولانی اجرا کند.

حداقل command لازم:

```text
CommandKind.RUN_HYBRID_LIVE_DECISION_AUDIT
Dashboard label: Run hybrid live decision audit
Handler/application service: runs paper/shadow decisions without real orders
```

GUI باید نشان دهد:

```text
latest candle/quote
hybrid probabilities
meta probabilities if enabled
range_1d/range_4h forecasts
TP/SL
TRADE/NO_TRADE reason
paper/live mode
execution disabled/enabled flag
```

تا وقتی این GUI/audit وجود ندارد، real live trading مجاز نیست.
