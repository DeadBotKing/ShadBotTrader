# فاز ۶۲ — پیچ‌های فاز ۵۹/۶۱ در GUI (سه مسیر داشبورد)

**تاریخ:** 2026-08-27 · **وضعیت:** ✅ کامل (pytest 1471 passed · 49 skipped · ruff/black ✅)

## انگیزه

پرسش کاربر: «توی GUI هم اضافه کردی؟» — فازهای ۵۹–۶۱ فقط CLI بودند؛ سه مسیر
داشبورد که `run_dual_models.py` را اجرا می‌کنند بدون این تنظیمات ماندند.

## تغییرات (`presentation/commands/handlers.py`)

| مسیر | فیلدهای جدید | فلگ پاس‌شده |
|---|---|---|
| **Train a model** | WaveNet layers × block · WaveNet blocks · Validation samples per fold | `--n-layers` · `--n-blocks` · `--val-size` |
| **Retrain a saved model** | همان سه فیلد | همان سه + `--resume` قبلی |
| **Find best learning rate** | دو فیلد معماری | `--n-layers` · `--n-blocks` |

قاعده: **0 = پیش‌فرض/auto و فلگ اصلاً پاس نمی‌شود** — یعنی رفتار پیش‌فرض
فاز ۵۹ (۱۰٪ ولید) و ۶۱ (معماری نقش) بدون دست‌زدن کاربر برقرار است.

hint فیلدها راهنمای RF دارند (مثال 150+4×2 → RF=121) تا دامِ «RF > window»
که فاز ۶۱ هشدارش را در سربرگ لاگ می‌دهد، از همان فرم قابل پیشگیری باشد.

## تست‌ها

`tests/unit/presentation/test_architecture_knobs_gui.py` (۷ تست):
- هر سه descriptor فیلدها را دارند
- train_dual_models مقادیر را پاس می‌دهد · با 0 فلگ حذف می‌شود
- retrain (train_model) با کاتالوگ minimal پاس می‌دهد
- optimise_learning_rate معماری را پاس می‌دهد

## یادداشت

۱۰ خطای ruff از قبل در handlers.py بود (E501 در hintهای فارسی + F401
traceback) — به این فاز مربوط نیست؛ ثبت برای تمیزکاری بعدی.
