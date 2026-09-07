# فاز ۱۱۲ — پیشنهاد: benchmark مدل دو-شاخه returns + engineered features

**وضعیت:** 🟡 پیشنهادی / بعد از فاز ۱۰۸-۱۱۱
**نوع:** Architecture benchmark، بدون جایگزینی فوری WaveNet
**اولویت:** متوسط/بالا

---

## الهام

repo `ari99/algorithmic_trading` یک مدل دو ورودی داشت:

```text
Returns sequence branch + engineered features branch
```

این ایده برای ما benchmark خوبی است تا بفهمیم ضعف احتمالی از معماری WaveNet است یا target/feature.

---

## معماری پیشنهادی برای ShadBotTrader

```text
Input A: returns sequence, shape [window, 1]
  → causal Conv1D یا GRU/LSTM کوچک

Input B: selected engineered features
  → Dense + BatchNorm + Dropout

concat
→ Dense
→ output softmax 3-class یا sigmoid binary
```

---

## ورودی returns branch

برای هر window:

```text
return_1 sequence
یا log_return sequence
یا normalized close-to-close return
```

---

## چرا بعداً نه الآن؟

اول باید target، class weights، F1 و threshold calibration درست شوند. اگر این‌ها خراب باشند، مدل دو-شاخه هم همان مشکل را فقط پیچیده‌تر تکرار می‌کند.

---

## فایل‌های پیشنهادی

```text
src/ShadBotTrader/infrastructure/ai/two_branch_model.py
src/ShadBotTrader/infrastructure/ai/two_branch_trainer.py
```

یا بهتر: ابتدا در scripts/experiments بدون واردکردن به production.

---

## معیار پذیرش

```text
- benchmark کنار WaveNet train شود، نه جایگزین آن.
- همان roll-forward/purge را رعایت کند.
- همان metrics trend_signal را گزارش کند.
- اگر بهتر نبود، حذف/غیرفعال بماند.
```
