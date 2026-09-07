# فاز ۱۰۷ — audit کامل trend_signal

**تاریخ:** 2026-09-07
**وضعیت:** ✅ کامل — script، GUI، metadata و تست انجام شد
**گزارش:** `docs/Report/PHASE107_TREND_SIGNAL_AUDIT_REPORT.md`

---

## هدف

قبل از retrain سنگین `gold_trend_signal_5m` باید بفهمیم target فعلی دقیقاً چه توزیعی دارد، چه مقدار ambiguous حذف می‌شود، baseline چیست و آیا validation folds نماینده هستند یا نه.

---

## خروجی اصلی فاز

فایل جدید:

```text
scripts/evaluate_trend_signal_5m.py
```

Command جدید GUI:

```text
Audit trend-signal labels
CommandKind.AUDIT_TREND_SIGNAL = "audit_trend_signal"
```

---

## ورودی‌های script/GUI

```text
--symbol XAUUSD
--timeframe 5M
--window 288
--label-horizon 288
--atr-mult 0.5
--folds 3
--val-size 0
--model-id gold_trend_signal_5m optional
--max-windows 5000
--storage-root datasets
```

---

## گزارش‌های label audit

Script چاپ می‌کند:

```text
candles count
تاریخ شروع/پایان
label distribution: SELL/HOLD/BUY
ambiguous samples count
warmup skipped count
partial-horizon near-tail count
first-hit distance stats
barrier distance stats
class ratios
majority baseline
always-HOLD baseline
```

---

## گزارش‌های feature/fold audit

```text
usable feature rows
feature columns
dropped warmup
excluded/skipped features
labelled windows
target column index
roll-forward fold train/val label balances
purged samples
```

---

## گزارش‌های model scoring اختیاری

اگر model artifact و TensorFlow موجود باشد:

```text
confusion matrix
precision/recall/F1 per class
macro-F1
weighted-F1
balanced accuracy
PR-AUC / average precision برای BUY و SELL
prediction probability spread
collapse check
```

اگر TensorFlow یا مدل موجود نباشد، script بدون crash فقط scoring را skip می‌کند و label audit کامل انجام می‌شود.

---

## تغییرات کد

### `target_builder.py`

به `TrendSignalLabels` اضافه شد:

```python
barrier_price_dist: List[float]
ambiguous_count: int
warmup_skipped: int
partial_horizon_count: int
examined_count: int
```

رفتار labelسازی تغییر نکرد؛ فقط metadata برای audit اضافه شد.

### `commands.py` / `handlers.py`

Command جدید GUI اضافه شد و از مسیر live log موجود `_run_script` استفاده می‌کند:

```text
scripts/evaluate_trend_signal_5m.py
```

---

## تست‌ها

```text
tests/unit/ai/test_trend_signal_labels.py
tests/integration/test_trend_signal_audit.py
tests/unit/presentation/test_commands.py
tests/integration/test_gui_coverage.py
```

نتیجه targeted:

```text
66 passed
```

Full pytest:

```text
python -m pytest -q
→ passed (TF tests طبق markerهای موجود skip شدند)
```

Targeted ruff/black روی فایل‌های تغییرکرده سبز شد. Full ruff/black/mypy هنوز همان خطاهای قدیمی خارج از این فاز را دارد.

Smoke test script روی `TESTSYM 5M` هم اجرا شد و imbalance/partial horizon را درست گزارش کرد.

---

## نکتهٔ مهم کشف‌شده

Target builder فعلی برای near-tail samples که horizon کامل ندارند، همچنان label می‌سازد. این رفتار در فاز ۱۰۷ تغییر داده نشد چون ممکن است رفتار آموزشی قبلی را بشکند، اما از این به بعد audit آن را صریح نشان می‌دهد:

```text
partial horizon labels exist near tail
```

در فازهای بعدی می‌توانیم با اجازه اپراتور گزینه‌ای مثل زیر اضافه کنیم:

```text
--drop-incomplete-label-horizon
```

---

## دستور اجرای CLI

```bash
PYTHONPATH=src python scripts/evaluate_trend_signal_5m.py \
  --symbol XAUUSD \
  --timeframe 5M \
  --window 288 \
  --label-horizon 288 \
  --atr-mult 0.5 \
  --folds 3 \
  --storage-root datasets
```

---

## اجرای واقعی اپراتور و follow-up fix

اپراتور audit را روی دیتای واقعی `XAUUSD 5M` اجرا کرد:

```text
candles=53,198
labels=52,881 accepted from 52,909 examined
SELL=40.0% | HOLD=24.0% | BUY=36.0%
majority baseline=40.0%
ambiguous=28
partial horizon accepted=287
first-hit median=104 bars
barrier median=$50.155
```

در بخش model scoring، مدل ذخیره‌شدهٔ قدیمی ورودی `(None, 150, 179)` می‌خواست ولی audit با `window=288` اجرا شده بود. این باعث crash شد. اصلاح شد: script حالا قبل از `model.predict`، window و feature count را چک می‌کند و در mismatch، scoring را skip می‌کند، نه اینکه crash کند.

## گام بعدی

Phase108:

```text
class weights + F1/PR-AUC برای trend_signal
```

با توجه به توزیع واقعی، target کلی قابل استفاده‌تر از score regression است، اما foldهای validation آخر regime-shift دارند؛ پس class weights و metricهای per-class الزامی‌اند.
