# فاز ۱۱۰ — پیشنهاد: feature selection مخصوص مدل و train-only

**وضعیت:** 🟡 پیشنهادی / آمادهٔ اجرا  
**نوع:** Feature engineering / anti-noise  
**اولویت:** بالا

---

## هدف

مدل‌های جهت احتمالاً با همهٔ 180+ feature بهتر نمی‌شوند. باید featureهای redundant/noisy حذف شوند، اما بدون leakage.

---

## اصل مهم

Feature selection خودش می‌تواند leakage ایجاد کند. پس:

```text
fit فقط روی train fold/prefix
apply روی validation/test/live
```

نه fit روی کل history.

---

## روش‌های پیشنهادی

```text
spearman_to_target
pearson_to_target
mutual_info_classif optional
extra_trees_importance optional
remove pairwise feature correlation > 0.90
hybrid_vote
```

---

## CLI/GUI

```text
--feature-select none|corr|tree|hybrid
--top-features 16|32|64|128
--max-feature-corr 0.90
```

---

## خروجی ذخیره‌شده در model record

```json
"feature_selection": {
  "method": "hybrid",
  "top_features": 64,
  "max_pairwise_corr": 0.90,
  "selected_features": ["rsi_14", "atr_14", "session_hour_sin", "..."],
  "removed_correlated": ["..."],
  "fit_scope": "train_fold_only"
}
```

---

## فایل پیشنهادی جدید

```text
src/ShadBotTrader/infrastructure/ai/feature_selection.py
```

---

## فایل‌های درگیر

```text
src/ShadBotTrader/application/services/dual_model_service.py
src/ShadBotTrader/infrastructure/ai/feature_matrix.py
scripts/run_dual_models.py
src/ShadBotTrader/presentation/commands/handlers.py
```

---

## معیار پذیرش

```text
- انتخاب feature روی validation/test fit نشود.
- نام featureهای انتخابی با مدل ذخیره شود.
- inference دقیقاً همان ستون‌ها را با همان order مصرف کند.
- اگر feature کم بود یا ستون missing بود، خطای قابل فهم بدهد.
```
