# فاز ۶۱ — پیچ‌های معماری (n-layers/n-blocks) + چاپ RF در سربرگ

**تاریخ:** 2026-08-27 · **وضعیت:** ✅ کامل (pytest 1464 passed · 49 skipped · ruff/black ✅)

## انگیزه

پرسش کاربر: «window رو بذارم 150 اوکیه؟» — بررسی کد نشان داد `--window`
فقط `window_size` را عوض می‌کند و معماری پیش‌فرض فاز ۵۸ (۵×۲، RF=249)
می‌ماند → RF=166% پنجره: لایه‌های بیرونی فقط pad صفر می‌بینند.

## تغییرات

1. `model_roles.py`:
   - `signal_model_role(..., n_layers_per_block=None, n_blocks=None)` —
     None = پیش‌فرض فاز ۵۸ (۵×۲)
   - `range_model_role(..., n_layers_per_block=None, n_blocks=None)` —
     None = پیش‌فرض ۴×۲
   - تابع جدید `receptive_field(layers, blocks, kernel=5)`:
     `1 + blocks×(kernel−1)×(2^layers−1)` → 5×2=249 · 4×2=121 · 5×1=125
2. `run_dual_models.py`:
   - آپشن‌های `--n-layers` / `--n-blocks` (0 = پیش‌فرض نقش)
   - سربرگ هر آموزش حالا چاپ می‌کند:
     `architecture : window=150 · 4 layers × 2 blocks · RF=121 (81% of window)`
   - اگر RF > window شد، هشدار صریح با پیشنهاد اصلاح چاپ می‌شود.
3. تست‌ها: `tests/unit/ai/test_model_roles_knobs.py` (۶ تست) — پیش‌فرض‌ها
   دست‌نخورده، override، فرمول RF، ورودی نامعتبر.

## جفت‌سازی پیشنهادی

| window | layers×blocks | RF | پوشش |
|---|---|---|---|
| 300 (فاز ۵۸) | 5×2 | 249 | 83% |
| **150** | **4×2** | **121** | **81%** |
| 150 (بدون override — هشدار می‌دهد) | 5×2 | 249 | 166% ❌ |
