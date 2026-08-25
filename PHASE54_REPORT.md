# فاز ۵۴ — Loss سه‌گانه + AdamW + ReduceLROnPlateau (از legacy)

**تاریخ:** 2026-08-25  
**وضعیت:** ✅ کامل  
**منبع:** `legacy/TimeSeriesPrediction2.py` (کد اصلی شما)

---

## آنچه از legacy کد یاد گرفتیم

### ۱. Loss سه‌گانه با وزن‌بندی

```python
# legacy (شما):
model.compile(
    loss=[CustomLossHuber, CustomLossMAE, CustomLossMSE],
    loss_weights=[30.0, 60.0, 10.0]  # 30*Huber + 60*MAE + 10*MSE
)

# فاز ۵۴ (ما):
class _RangeLoss(Loss):
    def call(y_true, y_pred):
        h = Huber(delta=0.005)(y_true, y_pred)
        m = MAE(y_true, y_pred)
        s = MSE(y_true, y_pred)
        return (3*h + 6*m + 1*s) / 10   # نسبت یکسان legacy
```

**چرا ترکیب بهتره:**
| Loss | نقش |
|------|-----|
| Huber (وزن 3) | outlier-robust، smooth gradient |
| MAE (وزن 6) | bias کم، gradient ملایم near-zero |
| MSE (وزن 1) | gradient قوی در ابتدای training |

### ۲. AdamW بجای Adam

```python
# legacy (شما):
optimizer = tf.keras.optimizers.experimental.AdamW(learning_rate=2.5e-5)

# فاز ۵۴ (ما): فقط برای regression
optimizer = tf.keras.optimizers.AdamW(
    learning_rate=learning_rate,
    weight_decay=1e-4,
)
```

**چرا AdamW بهتره از Adam+L2:**
- `Adam+L2`: regularization در gradient update مقیاس‌بندی میشه
- `AdamW`: weight decay مستقیم و مستقل از gradient → L2 واقعی

### ۳. ReduceLROnPlateau

```python
# legacy (شما):
ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.9,
    patience=30,       # 30 epoch صبر
    min_lr=2.5e-7,
)

# فاز ۵۴ (ما): patience کوتاه‌تر چون fold ها کمتر epoch دارن
ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.9,
    patience=max(3, epochs//8),   # ~12% epoch ها
    min_lr=lr * 1e-3,
)
```

---

## چه چیزی از legacy استفاده نکردیم

| ایده legacy | دلیل عدم استفاده |
|-------------|-----------------|
| SeparableConv با depth_multiplier=50 | خیلی گران (params 50× زیادتر) |
| seq2seq output | مدل ما scalar (high/low جداگانه) |
| Loss focus روی آخرین timestep | فقط در seq2seq معنی داره |
| EPOCHS=1000 + EarlyStopping | ما roll-forward داریم |

---

## فایل تغییر یافته

`src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py`
- تابع `_build_compiled`: loss→`_RangeLoss`, optimizer→`AdamW`
- تابع `train()`: `ReduceLROnPlateau` به callbacks اضافه شد

---

## انتظار از training

```
# قبل (فاز ۵۳):
epoch 1/40 | loss=0.000831 | val_loss=0.000593 | val_mae=0.001754

# بعد (فاز ۵۴):
epoch 1/40 | loss=0.000XXX | val_loss=0.000XXX | val_mae=0.00XXX
# loss scale متفاوته (3-way weighted) اما val_mae همون متریک اصلیه
# با AdamW + ReduceLROnPlateau انتظار: val_mae < 0.0015
```
