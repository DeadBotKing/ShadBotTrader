# فاز ۴۳ — رفع کرش «The dataset is infinite»

**تاریخ:** 2026-08-18
**وضعیت:** ✅ کامل — Quality Gate سبز

---

## کرش تو

```
File "wavenet_trainer.py", line 289, in train
    total_batches=max(1, -(-len(train_x) // max(self._batch_size, 1))),
                            ^^^^^^^^^^^^
TypeError: The dataset is infinite.
```

روی دیتاست واقعی 5M با ۴۷٬۸۸۶ پنجرهٔ آموزشی، بعد از ۱۴۵ ثانیه.

## این باگ را خودم ساختم

باگی نبود که از قبل باشد — **در فاز ۴۱ خودم آن را وارد کردم** و ندیدمش،
چون در سندباکس با `NullProgressReporter` تست کردم که این callback را
اصلاً نمی‌سازد. تو با گزارشگر واقعی اجرا کردی و بلافاصله خورد به آن.

### زنجیرهٔ علت

۱. فاز ۴۱ فولدهای بزرگ را **استریم** کرد تا رم ۱۲ گیگابایتی نخواهد.
۲. برای اینکه epoch دوم خالی نماند، دیتاست `repeat()` شد — یعنی **بی‌نهایت**.
۳. ولی callback پیشرفت هنوز `len(train_x)` را می‌پرسید.
۴. یک دیتاست بی‌نهایت طول ندارد → `TypeError`.

اثبات مستقل:
```python
tf.data.Dataset.from_tensor_slices([1,2,3]).repeat()  →  len() raises
"The dataset is infinite."
```

### رفع

تعداد batch از **هندسهٔ fold** می‌آید نه از خود دیتاست. این عدد از قبل
محاسبه شده بود (`train_steps`) و فقط استفاده نمی‌شد:

```python
batches_per_epoch = train_steps or max(1, -(-train_size // batch_size))
```

`len(train_x)` و `len(val_x)` کاملاً از کد حذف شدند.

---

## تأیید روی همان مسیری که کرش می‌کرد

بازتولید با ۲۰٬۰۰۰ سطر × ۱۲۳ ستون و پنجرهٔ ۵۰۰ (همان مسیر استریم):

```
=== progress the operator would see ===
   [--------------------]   0.2% | batch 1/594 | loss 0.0386 | mae 0.0480
   [############--------]  62.5% | batch 371/594 | loss 0.0062 | mae 0.0032
   [####################] 100.0% | batch 594/594 | loss 0.0052 | mae 0.0022
   epoch 1/1 | loss 0.0052 | val_loss 0.0033 | lr 1.50e-04

NO CRASH. peak RSS 966 MB in 511s
```

و کل مسیر از داشبورد:
```
[12s] busy=True lines=46 epochs=1
[24s] busy=True lines=81 epochs=4
succeeded | Trained range on 1D
SAVED → datasets/models/gold_range_1d/v1.bin + v1_training.json
```

---

## ورک‌اسپیس

کامل پاک شد و از گیت‌هاب کلون تازه گرفته شد (`d14b5f5 Update Web Show Train`).
دیتای تست مصنوعی زیر `TESTSYM` ساخته شد. **دیتا در zip نیست.**

---

## تأیید

```
black ✅  ruff ✅  mypy (293 files) ✅
pytest 1361 passed, 12 skipped   (قبلاً 1354)
RUN_TF=1 (ai + streaming + progress): 141 passed
```
**۷ تست جدید**، از جمله یکی که با `ast` کد را پارس می‌کند و مطمئن می‌شود
`len()` هرگز روی یک متغیر دیتاست صدا زده نشود — یعنی این باگ نمی‌تواند
با یک ویرایش بی‌دقت برگردد.

---

## درسی که ثبت می‌کنم

مسیر استریم را با `NullProgressReporter` تست کردم، و آن reporter اصلاً
callback را نمی‌سازد. یعنی **مسیری که کاربر واقعاً اجرا می‌کند تست نشده
بود**. تست جدید عمداً با `ConsoleProgressReporter` اجرا می‌شود.

## بدهی

هشدار `shuffle=True was passed, but will be ignored` از Keras باقی است.
بی‌ضرر است (دیتای سری‌زمانی نباید shuffle شود) ولی در لاگ نویز ایجاد
می‌کند؛ خاموش‌کردنش یک تغییر جدا می‌خواهد.
