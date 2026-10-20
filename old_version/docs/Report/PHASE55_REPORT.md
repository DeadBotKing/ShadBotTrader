# فاز ۵۵ — Seq2Seq Range Model (رفع Collapse)

**تاریخ:** 2026-08-25  
**وضعیت:** ✅ کامل

---

## مشکل قبلی (Scalar)

مدل range در بکتست collapse شد:
```
range_high_offset: همیشه 0.002444 (ثابت!)
range_low_offset:  همیشه -0.002174 (ثابت!)
```

**چرا؟** با scalar output (فقط 2 عدد خروجی)، مدل ساده‌ترین راه رو پیدا کرد: همیشه میانگین بده.

---

## راه‌حل: Seq2Seq Output

| معیار | Scalar (قبلی) | Seq2Seq (فاز ۵۵) |
|-------|--------------|-----------------|
| خروجی | `[batch, 2]` | `[batch, window, horizon*2]` |
| gradient signal | 2 عدد | **150×10 = 1500 عدد** |
| collapse risk | بالا | خیلی پایین |
| supervision | ضعیف | قوی |

---

## معماری جدید

```
Input [batch, 150, 182]
  ↓ WaveNet Blocks (causal)
  ↓ Skip connections
  ↓ SeparableConv1D(relu) [causal]
  ↓ SeparableConv1D(linear, filters=horizon*2) [causal]
Output [batch, 150, 10]   ← horizon=5, 10 = 5 high + 5 low

channel layout per timestep:
  [high_1, low_1, high_2, low_2, ..., high_5, low_5]
```

---

## Loss Seq2Seq-Aware

```python
def call(y_true, y_pred):
    # loss کل sequence (gradient قوی)
    loss_all = weighted(huber + mae + mse)(y_true, y_pred)
    # loss آخرین horizon (هدف اصلی — وزن بیشتر)
    loss_tgt = weighted(huber + mae + mse)(y_true[:,-H:,:], y_pred[:,-H:,:])
    return 0.4 * loss_all + 0.6 * loss_tgt
```

این دقیقاً همون ایده `CustomLossHuber` از `legacy/TimeSeriesPrediction2.py` هست!

---

## Labels جدید

```python
# قبلی: یک عدد برای کل horizon
high_offset = (max_high_next_5 - close) / close   # scalar

# جدید: یک عدد به ازای هر کندل
high_seq[k] = (high[t+k] - close[t]) / close[t]   # k=1..5
low_seq[k]  = (low[t+k]  - close[t]) / close[t]
```

---

## Predictor

```python
# خروجی seq2seq: آخرین timestep → آخرین horizon step
last_step = output[-1]                          # [horizon*2]
highs = [last_step[k*2]     for k in range(H)] # high برای هر کندل آینده
lows  = [last_step[k*2+1]   for k in range(H)] # low برای هر کندل آینده
best_high = max(highs)   # بدترین حالت high
best_low  = min(lows)    # بدترین حالت low
```

---

## فایل‌های تغییر یافته

| فایل | تغییر |
|------|-------|
| `target_builder.py` | `build_range_labels_seq2seq()` + `RangeLabelsSeq2Seq` |
| `wavenet.py` | seq2seq head: `SeparableConv1D(horizon*2, causal)` |
| `wavenet_trainer.py` | `seq2seq` پارامتر + loss seq2seq-aware |
| `dual_model_service.py` | seq2seq labels در `prepare()` |
| `model_roles.py` | `seq2seq=True` در `range_model_role()` |
| `dual_predictor.py` | handle خروجی `[batch, window, H*2]` |
