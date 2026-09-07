# فاز ۱۰۷ — گزارش پیاده‌سازی audit کامل trend_signal

تاریخ: 2026-09-07
وضعیت: ✅ کامل — script، GUI، metadata، تست و مستندسازی انجام شد.

---

## 1) هدف فاز

قبل از retrain سنگین `gold_trend_signal_5m`، باید بدانیم target فعلی دقیقاً چه وضعی دارد:

```text
SELL/HOLD/BUY distribution
ambiguous samples
warmup skipped rows
near-tail partial horizon labels
barrier distance stats
first-hit distance stats
roll-forward fold label balance
majority / always-HOLD baseline
```

و اگر model artifact موجود بود، همان script باید بدون training مدل را score کند و metricهای per-class بدهد.

---

## 2) فایل‌های تغییرکرده/جدید

### جدید

```text
scripts/evaluate_trend_signal_5m.py
tests/integration/test_trend_signal_audit.py
docs/Report/PHASE107_TREND_SIGNAL_AUDIT_REPORT.md
```

### تغییرکرده

```text
src/ShadBotTrader/infrastructure/ai/target_builder.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_trend_signal_labels.py
docs/Phases/Phase107.md
docs/WORKLOG.md
docs/CURRENT_STATE.md
docs/SESSION_HANDOFF_2026-09-07.md
```

---

## 3) تغییرات target_builder

در `TrendSignalLabels` metadataهای audit اضافه شد:

```python
barrier_price_dist: List[float]
ambiguous_count: int
warmup_skipped: int
partial_horizon_count: int
examined_count: int
```

رفتار labelها عوض نشده، فقط اطلاعات audit اضافه شده است.

### counters جدید

```text
warmup_skipped:
  تعداد startهایی که daily-range proxy هنوز آماده نیست یا scale<=0 دارد.

ambiguous_count:
  تعداد کندل‌هایی که در همان future bar هم upper و هم lower barrier را زده‌اند.

partial_horizon_count:
  تعداد startهای نزدیک tail که کمتر از horizon کامل آینده دارند.

examined_count:
  تعداد startهای بعد از warmup که واقعاً بررسی شده‌اند.

barrier_price_dist:
  فاصله واقعی barrier از close[t] به واحد قیمت/دلار.
```

نکته: فیلد قدیمی `barrier_dist` برای سازگاری باقی ماند.

---

## 4) script جدید

فایل:

```text
scripts/evaluate_trend_signal_5m.py
```

نمونه اجرا:

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

### خروجی‌های script

#### RAW LABEL AUDIT

```text
candles count + date range
labels accepted / examined starts
warmup skip
ambiguous count
partial horizon count
SELL/HOLD/BUY counts + percentage
majority baseline
always-HOLD baseline
label distance all stats
first-hit distance stats
barrier distance stats
```

#### FEATURE MATRIX / WINDOWS

```text
usable rows
feature columns
dropped warmup
excluded/skipped features
labelled windows
target column
```

#### ROLL-FORWARD FOLD AUDIT

همان هندسه expanding roll-forward training بازسازی می‌شود و برای foldهای آخر چاپ می‌شود:

```text
train range + SELL/HOLD/BUY count
validation range + SELL/HOLD/BUY count
purged samples
```

#### MODEL SCORE — اگر مدل و TensorFlow موجود باشد

```text
confusion matrix
accuracy
balanced accuracy
macro F1
weighted F1
SELL/BUY average precision
precision/recall/F1 per class
probability mean/stdev/min/max per class
collapse check
```

اگر TensorFlow یا artifact موجود نباشد، scoring با پیام قابل فهم skip می‌شود؛ label audit همچنان کامل اجرا می‌شود.

---

## 5) JSON output

به طور پیش‌فرض script خلاصه machine-readable می‌نویسد:

```text
run_logs/trend_signal_audit_latest.json
```

می‌توان خاموش کرد:

```bash
--json-out ""
```

---

## 6) GUI جدید

Command جدید اضافه شد:

```text
CommandKind.AUDIT_TREND_SIGNAL = "audit_trend_signal"
```

در Dashboard یک کارت جدید در گروه AI:

```text
Audit trend-signal labels
```

فیلدها:

```text
symbol
dataset
window
label_horizon
atr_mult
folds
val_size
model_id
max_windows
timeout_minutes
```

این command از مسیر live log موجود استفاده می‌کند و اجرا می‌کند:

```text
scripts/evaluate_trend_signal_5m.py
```

---

## 7) تست‌ها

### تست‌های جدید/آپدیت‌شده

```text
tests/unit/ai/test_trend_signal_labels.py
  test_audit_counts_ambiguous_and_warmup_rows

tests/integration/test_trend_signal_audit.py
  test_script_exposes_phase107_metrics_helpers
  test_average_precision_is_reported_without_sklearn
  test_audit_command_has_gui_fields
  test_audit_command_passes_expected_script_args
```

### targeted tests اجراشده

```bash
python -m pytest \
  tests/unit/ai/test_trend_signal_labels.py \
  tests/integration/test_trend_signal_audit.py \
  tests/unit/presentation/test_commands.py \
  tests/integration/test_gui_coverage.py -q
```

نتیجه:

```text
66 passed
```

Full pytest نیز اجرا شد:

```text
python -m pytest -q
→ passed (در این محیط، تست‌های TensorFlow طبق markerهای موجود skip شدند)
```

### script smoke test اجراشده

روی دیتای تست موجود:

```bash
PYTHONPATH=src python scripts/evaluate_trend_signal_5m.py \
  --symbol TESTSYM --timeframe 5M --window 50 --label-horizon 20 \
  --atr-mult 0.5 --folds 2 --max-windows 0 --storage-root datasets \
  --json-out run_logs/test_trend_signal_audit.json
```

خلاصه خروجی:

```text
candles: 500
labels: 211 accepted from 211 examined starts
warmup skip: 288
ambiguous: 0
partial horizon: 19 examined near-tail starts; 19 accepted labels have less than full horizon
SELL: 0
HOLD: 211
BUY: 0
majority baseline: 100%
always-HOLD base: 100%
feature columns: 179
labelled windows: 211
```

این نشان داد script درست هشدار imbalance شدید و partial horizon را چاپ می‌کند.

---

## 8) نکتهٔ کشف‌شده در audit

در target builder فعلی، نمونه‌های نزدیک tail که horizon کامل آینده ندارند، همچنان label می‌گیرند. این رفتار قبلاً در تست‌ها پذیرفته شده بود و در Phase107 تغییر داده نشد؛ فقط audit آن را صریح گزارش می‌کند:

```text
partial horizon labels exist near tail
```

این موضوع برای Phase108/Training باید جدی گرفته شود. گزینهٔ آینده:

```text
--drop-incomplete-label-horizon
```

یا حذف tail horizon در train/evaluation.

---

## 9) اجرای واقعی اپراتور روی XAUUSD 5M

خروجی واقعی ارسال‌شده توسط اپراتور:

```text
candles    : 53,198 (2025-11-28T08:50:00 .. 2026-09-02T10:30:00)
labels     : 52,881 accepted from 52,909 examined starts
warmup skip: 288
ambiguous  : 28
partial hz : 287 examined near-tail starts; 287 accepted labels have less than full horizon
SELL       : 21,130 (40.0%)
HOLD       : 12,715 (24.0%)
BUY        : 19,036 (36.0%)
majority baseline: 40.0%
always-HOLD base : 24.0%
label distance median: 140 bars
first-hit distance median: 104 bars
barrier distance median: 50.155 USD
```

تفسیر:

```text
- توزیع کلی بسیار بهتر از حالت HOLD-dominant است؛ majority baseline فقط 40% است.
- HOLD فقط 24% است، پس target فعلی بیش از حد بی‌حرکت نیست.
- validation foldهای آخر نسبت به کل دیتا BUY-heavy هستند؛ برای Phase108 باید per-fold class weights و per-class metrics داشته باشیم.
- partial horizon فقط 287 از 52,881 label است (~0.54%)، اما باید در گزارش باقی بماند.
```

## 10) رفع follow-up بعد از اجرای اپراتور

اجرای اپراتور بعد از audit هنگام model scoring کرش کرد:

```text
expected shape=(None, 150, 179), found shape=(32, 288, 179)
```

علت: مدل ذخیره‌شدهٔ `gold_trend_signal_5m` با window=150 ساخته شده بود، اما audit برای پیکربندی جدید با window=288 اجرا شد.

اصلاح:

```text
score_model حالا قبل از model.predict، هم window size و هم feature count را با input_shape مدل مقایسه می‌کند.
در mismatch، model scoring را skip می‌کند و پیام قابل فهم می‌دهد.
label/fold audit بالا همچنان معتبر است.
```

اگر کسی بخواهد همان مدل قدیمی را score کند باید audit را با window مدل اجرا کند:

```bash
python scripts/evaluate_trend_signal_5m.py --symbol XAUUSD --timeframe 5M --window 150 \
  --label-horizon 288 --atr-mult 0.5 --storage-root datasets
```

اما برای train جدید پیشنهادی ما، window=288 مناسب‌تر است.

## 11) گام بعدی

Phase108:

```text
class weights + F1/PR-AUC برای trend_signal
```

با توجه به خروجی واقعی، class weights باید per-fold محاسبه شود چون توزیع validation در foldهای آخر regime-shift دارد.
