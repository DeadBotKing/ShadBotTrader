# فاز ۳۶ — دیدن روند آموزش، در همان لحظه

**تاریخ:** 2026-08-17
**وضعیت:** ✅ کامل — Quality Gate سبز
**گزارش کاربر:**

> «الان موقعی ک توی Train both models ران رو میزنم، نه توی پاورشل نه توی
> صفحه وب چیزی از روند آموزش بهم نشون نمیده که دقت و درصدو این چیزا رو ببینم»

سه علت جدا داشت، نه یکی. به‌علاوه یک باگ چهارم که موقع تست زندهٔ همین فاز
پیدا شد.

---

## ۱. چهار علت

### باگ ۲۴ — خروجی تا پایان کار buffer می‌شد

`_run_script` از `subprocess.run(capture_output=True)` استفاده می‌کرد:

```python
completed = subprocess.run([...], capture_output=True, text=True, timeout=timeout)
output = completed.stdout.strip().splitlines()   # فقط بعد از exit
```

`subprocess.run` تا **خاتمهٔ پروسه** برنمی‌گردد. یعنی یک آموزش بیست‌دقیقه‌ای
هیچ چیزی نشان نمی‌داد و بعد یکجا ۲۰ خط چاپ می‌کرد. صفحهٔ وب هم می‌گفت
«reload the page to check progress» — ولی reload همان هیچ را نشان می‌داد،
چون خروجی هنوز وجود نداشت.

### باگ ۲۵ — گزارشگر پیشرفت ساخته شده بود و هیچ‌کس صدایش نمی‌زد

`infrastructure/ai/training_progress.py` از فاز ۱۳ یک `ConsoleProgressReporter`
کامل دارد: نوار پیشرفت، ETA، loss و accuracy هر epoch. ولی:

```python
self._progress: TrainingProgressReporter = progress or NullProgressReporter()
```

و هیچ فراخوانی‌ای `progress=` را پاس نمی‌داد. پس همیشه `NullProgressReporter`
فعال بود — کلاسی که همهٔ متدهایش `return None` هستند. یعنی حتی در پاورشل هم
چیزی چاپ نمی‌شد. `verbose=0` کراس هم مزید بر علت بود.

### باگ ۲۶ — accuracy محاسبه می‌شد و دور ریخته می‌شد

```python
val_loss = float(history.history["val_loss"][-1])
self.fold_history.append(val_loss)     # فقط همین
```

کراس هر epoch مقدار `accuracy`، `val_accuracy`، `mae` را حساب می‌کرد و
trainer فقط `val_loss` را نگه می‌داشت. پس سؤال «مدل چقدر خوبه؟» در هیچ
جای سیستم جواب نداشت — نه در CLI، نه در API، نه در دیتابیس.

### باگ ۲۷ — `--storage-root` داشبورد به اسکریپت‌ها نمی‌رسید

این را موقع تست زندهٔ فاز ۳۶ پیدا کردم. داشبورد را با
`--storage-root /tmp/live36` بالا آوردم، دکمه را زدم، و گرفتم:

```
[X] No stored candles for XAUUSD 1H.
    symbols on disk: P24DEMO, P24WK, P30TEST, P31DEMO, XAUUSD_I
```

هندلرهایی که مستقیم با store کار می‌کنند `self._storage_root` را رعایت
می‌کردند، ولی **چهار دکمه‌ای که اسکریپت اجرا می‌کنند** آن را پاس نمی‌دادند،
پس اسکریپت سراغ `datasets/` پیش‌فرض مخزن می‌رفت. کاربر در `/data` هزاران
کندل می‌دید و آموزش می‌گفت «کندلی نیست».

---

## ۲. چه چیزی حالا هست

### پاورشل: لاگ هر epoch

```
==========================================================================
  TRAINING  signal v1
==========================================================================
  framework      : tensorflow 2.21.0
  learning rate  : 0.00015
  epochs / fold  : 2
  folds          : 2  (roll-forward)
  total epochs   : 4
  batch size     : 8
  window x feats : 40 x 14
  samples        : 956
  seed           : 42
--------------------------------------------------------------------------
fold   1/2 | train[0:950] (950 samples) -> val[950:954] (4 samples)
  epoch 1/2 | loss 0.7538 | val_loss 0.2911 | acc 0.8874 | val_acc 1.0000 | lr 1.50e-04
  epoch 2/2 | loss 0.3478 | val_loss 0.1891 | acc 0.9421 | val_acc 1.0000 | lr 1.50e-04
[##############--------------]  50.0% | fold 1/2 | val_loss 0.1891 | 11.6s/fold | elapsed 11s | eta 11s
fold   2/2 | train[0:952] (952 samples) -> val[952:956] (4 samples)
  epoch 1/2 | loss 0.7496 | val_loss 0.2624 | acc 0.8950 | val_acc 1.0000 | lr 1.50e-04
  epoch 2/2 | loss 0.3380 | val_loss 0.1794 | acc 0.9422 | val_acc 1.0000 | lr 1.50e-04
[############################] 100.0% | fold 2/2 | val_loss 0.1794 | 10.7s/fold | elapsed 22s | eta 0s
--------------------------------------------------------------------------
  folds 2 | val_loss best 0.1794 / mean 0.1843 / worst 0.1891
  total training time: 22s
==========================================================================
```

`--quiet` خاموشش می‌کند.

### صفحهٔ وب: لاگ زنده، هر ۲ ثانیه

بنر «Running» حالا یک `<pre>` دارد که از `/api/log` می‌خواند:

```
Running: train_dual_models  34s
Live output below, refreshed every 2 seconds.
┌──────────────────────────────────────────────────────────┐
│ fold   1/1 | train[0:854] (854 samples) -> val[854:858]  │
│   epoch 1/1 | loss 0.6680 | val_loss 0.1956 | acc 0.9110 │
│ [######################] 100.0% | 11.0s/fold | eta 0s    │
└──────────────────────────────────────────────────────────┘
```

جزئیاتی که واقعاً «زنده» بودن را ممکن کرد:

| مشکل | راه‌حل |
|---|---|
| `subprocess.run` تا پایان برنمی‌گردد | `Popen` + خواندن خط‌به‌خط |
| پایتون وقتی مقصد pipe است ۸KB بافر می‌کند | `PYTHONUNBUFFERED=1` در محیط زیرپروسه |
| بافر سمت خودمان | `bufsize=1` با `text=True` |
| کاربر باید reload می‌زد | JS هر ۲ ثانیه poll می‌کند و در پایان یک‌بار reload |

اسکرول هوشمند است: اگر پایین باشی با لاگ می‌آید، اگر بالا رفته باشی برای
خواندن، جایت را نگه می‌دارد.

خروجی در `run_logs/{command}.log` هم می‌ماند تا اگر مرورگر بسته شد، از دست
نرود.

### سنجهٔ کیفیت — با معیار مقایسه

`fold_metrics` حالا آخرین مقدار هر سنجه را برای هر fold نگه می‌دارد و
اسکریپت آن را تفسیر می‌کند:

```
  QUALITY (final fold)
    accuracy        : 0.911007
    loss            : 0.668049
    val_accuracy    : 1.000000
    val_loss        : 0.195611

    val_accuracy 100.0% vs majority-class baseline 47.4%
    -> the model is BETTER than always predicting the commonest class.
```

**چرا baseline مهم است:** در یک مسئلهٔ ۳ کلاسه که ۷۰٪ نمونه‌ها HOLD هستند،
مدلی که همیشه HOLD بگوید ۷۰٪ دقت می‌گیرد و هیچ چیز یاد نگرفته. عدد خام
گمراه‌کننده است؛ مقایسه با baseline نیست. اگر مدل baseline را نزده باشد،
صریح می‌گوید `NO BETTER than`.

برای مدل رنج، خطا به دلار ترجمه می‌شود:

```
    val_mae 0.001000 — average error of the predicted high/low offsets,
    as a fraction of price.
    On gold at 2,000 that is about 2.00 USD per bound.
```

---

## ۳. فایل‌ها

### جدید
| فایل | نقش |
|---|---|
| `tests/integration/test_training_visibility.py` | ۲۳ تست رگرسیون، یک کلاس برای هر باگ |

### تغییر کرده
| فایل | تغییر |
|---|---|
| `presentation/commands/handlers.py` | `_run_script` با `Popen` و استریم؛ `RUN_LOG_DIR`، `run_log_path`، `read_run_log`؛ `--storage-root` به هر چهار دکمهٔ اسکریپتی |
| `presentation/web/server.py` | مسیر `GET /api/log` |
| `presentation/web/renderer.py` | پنل لاگ زنده + JS polling + استایل `.runlog` |
| `infrastructure/ai/wavenet/wavenet_trainer.py` | `fold_metrics` |
| `application/services/dual_model_service.py` | عبور `fold_metrics` در خروجی |
| `scripts/run_dual_models.py` | `ConsoleProgressReporter`، `--quiet`، `print_quality()` |
| `.gitignore` | `run_logs/` |

---

## ۴. تأیید

```
black --check .                 ✅
ruff check .                    ✅
mypy src --python-version 3.12  ✅ 288 files
pytest                          ✅ 1228 passed, 12 skipped   (قبلاً 1205)
RUN_TF=1                        ✅ 278 + 370 + 592
```
**۲۳ تست جدید.**

### تست زندهٔ داشبورد

داشبورد روی پورت ۸۰۹۹ بالا آمد، دکمهٔ `Train both models` از طریق
`POST /run` زده شد، و `/api/log` هر ۸ ثانیه poll شد:

```
[8s]  busy=True   lines=32
[16s] busy=True   lines=33
[24s] busy=True   lines=63
[32s] busy=True   lines=77
[40s] busy=False  (finished)
```

لاگ **حین اجرا** رشد کرد — دقیقاً چیزی که قبلاً ممکن نبود. نتیجهٔ نهایی:

```
succeeded | Both models trained
  epoch 1/1 | loss 0.6680 | val_loss 0.1956 | acc 0.9110 | val_acc 1.0000
  QUALITY (final fold): val_accuracy 1.000000
  val_accuracy 100.0% vs majority-class baseline 47.4%
  -> the model is BETTER than always predicting the commonest class.
```

---

## ۵. نکتهٔ صادقانه دربارهٔ همین اعداد

`val_accuracy 100%` روی **۴ نمونهٔ اعتبارسنجی** به‌دست آمده و دیتا هم موج
سینوسی ساختگی بود (دیتای واقعی MT5 فقط روی ویندوز در دسترس است). چهار نمونه
یعنی هر نمونه ۲۵٪ وزن دارد؛ این عدد کیفیت مدل را نشان نمی‌دهد، فقط نشان
می‌دهد **مسیر گزارش‌دهی درست کار می‌کند**.

روی دیتای واقعی با `--folds 20` و `val_size` بزرگ‌تر، انتظار عدد بسیار
پایین‌تری داشته باش. اگر آنجا هم ۱۰۰٪ دیدی، آن نشانهٔ نشت داده است نه
موفقیت.

---

## ۶. آنچه هنوز باز است

- **پیشرفت درون یک epoch** دیده نمی‌شود. برای دیتای واقعی که هر epoch ممکن
  است چند دقیقه طول بکشد، یک callback در سطح batch لازم است. فعلاً
  ریزدانگی در حد epoch است.
- `fold_metrics` در دیتابیس ذخیره نمی‌شود؛ فقط در خروجی اجرا می‌آید.
  مقایسهٔ کیفیت بین دو آموزش هنوز دستی است.
- لاگ‌ها هر اجرا **بازنویسی** می‌شوند (یک فایل به‌ازای هر دکمه). آرشیو
  تاریخی عمداً ساخته نشد؛ سؤال «الان چه خبر است» با انبوه فایل قدیمی
  سخت‌تر می‌شود نه آسان‌تر.
