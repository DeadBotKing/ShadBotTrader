# فاز ۶۰ — اتصال callbacks به مدل سیگنال + baseline صحیح حکم QUALITY

**تاریخ:** 2026-08-26
**وضعیت:** ✅ کامل (Quality Gate: ruff ✅ black ✅ pytest **1458 passed · 0 failed · 49 skipped**)
**کشف از:** اجرای ۱۰.۵ ساعتهٔ signal v1 کاربر (بهترین epoch همهٔ فولدها ≤ 19 ولی هر ۴ فولد تا 60 اجرا شد)

---

## ۱. باگ اصلی — ReduceLR + EarlyStopping هرگز به مدل سیگنال وصل نبودند

### ریشه

`DualModelService.build_trainer` برای مدل classification می‌فرستاد:

```python
loss=role.loss if is_regression else None,   # signal → None!
```

و گیتِ callbacks در `WavenetTrainer` چنین بود:

```python
if self._loss in ("huber", …, "sparse_categorical_crossentropy", …):
    # ReduceLROnPlateau (فاز ۵۴) + EarlyStopping (فاز ۵۷)
```

`None` با هیچ عضو لیست match نمی‌شود → **هر دو callback فقط به مدل range
وصل می‌شدند**، در حالی که گزارش فاز ۵۴/۵۷ ادعای «هر دو مدل» داشت و حتی
"sparse_categorical_crossentropy" در لیست گیت بود (نیت روشن، سیم‌کشی غلط).

### پیامد عملی (اجرای 2026-08-26)

- ۴ فولد × ۶۰ epoch کامل = 240 epoch، 10:22:30 ساعت CPU
- بهترین epoch هر فولد: 10 / 13 / 16 / 19 → ~۱۴۰ epoch آخر (~۷ ساعت) هدر رفت
- LR سیگنال ثابت 3e-4 ماند (بدون decay روی plateau)

### رفع

```python
loss=role.loss,      # همیشه — فاز ۶۰
metric=role.metric,
```

کامپایل مدل **هیچ تغییری نمی‌کند**: شاخهٔ classification در `_build_compiled`
خودش `SparseCategoricalCrossentropy + SparseCategoricalAccuracy("accuracy")`
را hard-code دارد؛ `weight_decay` هم با نام loss (نه None) همان 1e-5 می‌شود.
فقط گیتِ callbacks حالا match می‌شود.

### اثر مورد انتظار اجرای بعدی (epochs=60 → patience=12)

- EarlyStopping حدود epoch 22-31 هر فولد را می‌بندد → کل اجرا ~۵-۶ ساعت
- ReduceLR (patience=6, factor=0.85) روی plateau، LR را می‌شکند →
  کالیبراسیون احتمال‌ها بهتر (ببینید REVIEW اجرا: مدل به prior-match loss
  نمی‌رسید — بیش‌اعتمادی)

## ۲. باگ دوم — baseline غلط در حکم QUALITY

`print_quality` val_accuracy را با baseline **کل استخر** (50.3%) مقایسه
می‌کرد؛ ولی فولد آخرِ ولید در اجرای مذکور **65.2% sell** داشت (رژیم نزولی
انتهای دیتا) → «always-sell» روی همان ولید 65.2% می‌گرفت و حکمِ
«BETTER» برای 61.8% گمراه‌کننده بود.

**رفع:** `print_quality(..., val_baseline=...)` — baseline از توزیع لیبلِ
فولد آخرِ ولید (`signal_label_split_balance`) گرفته می‌شود؛ اگر با baseline
استخر فاصلهٔ معنادار (>2pp) داشته باشد، صریح چاپ می‌شود که فولد رژیم‌جابه‌جاست.

## ۳. تست‌ها

`tests/unit/ai/test_validation_geometry.py` (+۲ تست):

- `test_signal_role_receives_its_loss_string` — سیگنال باید
  `sparse_categorical_crossentropy` + `accuracy` بگیرد (قفلِ سیم‌کشی)
- `test_range_role_keeps_huber_loss` — مسیر regression دست‌نخورده

```
ruff ✅ black ✅ mypy (فایل‌های تغییر یافته ✅)
pytest 1458 passed, 49 skipped   (قبلاً 1456)
```

## ۴. یادداشت هماهنگی مستندات

گزارش `PHASE57_58_REPORT.md` («ReduceLROnPlateau/EarlyStopping برای هر دو
مدل اضافه شد») از این لحظه **صحیح** می‌شود — قبل از فاز ۶۰ فقط در کدِ نیت
بود، نه در رفتار واقعی سیگنال. طبق `AGENTOPERATINGRULE`: کد = واقعیت.
