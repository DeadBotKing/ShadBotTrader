# فاز ۵۱ — Resume Training (--resume) برای نت ضعیف

**تاریخ:** 2026-08-25  
**وضعیت:** ✅ کامل  
**مشکل:** اینترنت ضعیف → Colab وسط آموزش disconnect → همه چیز از دست میره

---

## ۱. مشکل

- آموزش range model با 30+ epoch روی Colab چند ساعت طول میکشه
- با نت ضعیف Colab disconnect میشه
- قبل از این فاز: هر disconnect = از صفر شروع
- حتی با checkpoint هر epoch، وزن‌ها روی disk بود ولی **راهی برای لود و ادامه نبود**

---

## ۲. راه‌حل: `--resume` flag

```bash
python scripts/run_dual_models.py --with-features --resume \
  --model range --epochs 40 --window 150 --learning-rate 3e-5
```

### چه اتفاقی می‌افته:

1. **`_load_resume_weights()`** آخرین `training.json` رو میخونه
2. `initial_epoch = record.epochs` (مثلاً ۲۰)
3. `.bin` artifact رو لود میکنه
4. `remaining = 40 - 20 = 20` epoch باقیمونده
5. آخرین fold با وزن‌های ذخیره‌شده warm-start میشه
6. `model.fit(..., initial_epoch=20, epochs=40)` — Keras فقط ۲۰ epoch میزنه

### چه چیزی تضمین میشه:

- **Walk-forward حفظ میشه:** فقط آخرین fold از checkpoint لود میکنه
- **Epoch counter درسته:** training.json همیشه epoch نهایی واقعی رو داره
- **معماری باید یکی باشه:** اگه مدل با پارامترهای متفاوت ساخته بشه → خطا میگیری و از صفر شروع میشه (crash نمیشه)
- **اگه checkpoint نباشه:** از صفر شروع میشه، بدون crash

---

## ۳. فایل‌های تغییر یافته

### الف) `scripts/run_dual_models.py`

```python
# ← آرگومان جدید:
parser.add_argument("--resume", action="store_true", ...)

# ← تابع جدید:
def _load_resume_weights(args, role) -> tuple:
    # reads training.json → gets initial_epoch
    # loads .bin artifact → returns (weights_bytes, initial_epoch)

# ← در train_one:
resume_weights, initial_epoch = _load_resume_weights(args, role)
remaining_epochs = args.epochs - initial_epoch
# پاس دادن به service.train:
outcome = service.train(..., initial_epoch=initial_epoch, resume_weights=resume_weights)
```

### ب) `src/.../dual_model_service.py`

```python
def train(..., initial_epoch=0, resume_weights=None):
def build_trainer(..., initial_epoch=0, resume_weights=None):
    return WavenetTrainer(..., initial_epoch=initial_epoch, resume_weights=resume_weights)
```

### ج) `src/.../wavenet/wavenet_trainer.py`

```python
def __init__(..., initial_epoch=0, resume_weights=None):
    self._initial_epoch = initial_epoch
    self._resume_weights = resume_weights

# در train() — آخرین fold:
if self._resume_weights and is_last_fold:
    _load_weights_into(model, self._resume_weights)

# در model.fit:
history = model.fit(...,
    initial_epoch=fit_initial_epoch,  # ← از جایی که موندیم
    epochs=self._epochs,
)

# تابع کمکی جدید:
def _load_weights_into(model, weights_bytes):
    saved_model = _deserialize_model(weights_bytes)
    model.set_weights(saved_model.get_weights())
```

---

## ۴. Colab Notebook — آپدیت

### مرحله ۶ج (بازنویسی شد):
- **بررسی checkpoint قبل از شروع:** نمایش epoch فعلی و باقیمونده
- **`--resume` flag** اضافه شد به command
- `RESUME_CONFIG['epochs']` = target نهایی (نه تعداد اضافه)

```
📊 Checkpoint موجود: epoch=20, score=0.001754
▶️  ادامه از epoch 20 → هدف 40 (20 epoch باقیمونده)
──────────────────────────────────────────────
🚀 شروع (با --resume) ...
  RESUME: loaded checkpoint v1 (epoch 20, val_mae 0.001754)
  RESUME: continuing from epoch 20 — 20 epoch(s) remaining
      [resume] weights loaded from checkpoint ✓
      [BEST so far] epoch 21/40 val_mae 0.001710 — saved as v1
      ...
```

### مرحله ۶د (جدید): Anti-disconnect
هر ۵ دقیقه یه ping میزنه تا Colab idle نشه.
در یه Tab جداگانه نگه دار.

---

## ۵. راهنمای استفاده بعد از disconnect

```
۱. Colab رو دوباره باز کن (Runtime → Run all تا مرحله ۴)
۲. مطمئن شو Drive وصله
۳. مرحله ۶ج رو اجرا کن (--resume)
۴. نتیجه: از epoch قبلی ادامه میده
```

---

## ۶. جمع‌بندی

| قبل از فاز ۵۱ | بعد از فاز ۵۱ |
|---|---|
| Disconnect = همه چیز از دست رفت | Disconnect = فقط epoch جاری |
| restart = از epoch 0 | restart = از آخرین epoch checkpoint |
| نت ضعیف = غیرممکن | نت ضعیف = کمی کندتر |

