# PROJECT UNDERSTANDING — درک جامع سیستم ShadBotTrader

> **آخرین به‌روزرسانی:** 2026-08-26
> این سند «درک من» از کل پروژه را یکجا ثبت می‌کند تا برای ادامهٔ کار (توسط خودم،
> یک ایجنت دیگر، یا تو) فقط از همین + کد قابل بازیابی باشد. مبنای آن = خواندن
> اسناد + بازبینی ریزِ کد + اجرای تست + گزارش رسمی فاز ۵۷/۵۸.

---

## ۱. پروژه در یک جمله

**ShadBotTrader** یک پلتفرم معاملاتی AI سازمانی (Python) است: دیتای بازار از
MetaTrader5 → فیچر (۲۲۷ تا) → دو مدل (سیگنال 5M + رنج 1D) → بکتست دومدلی با
براکت TP/SL → (در آینده) حلقهٔ زنده. معماری: **Clean Architecture + DDD +
Dependency Inversion**؛ Domain مستقل از Infrastructure.

---

## ۲. زنجیرهٔ کامل ترید (بکتست دومدلی — قلب فعلی پروژه)

```text
5M window (300) → signal model → BUY/SELL + confidence
      ↓ (فقط اگر confidence ≥ آستانه)
1D window (150) → range model (seq2seq, horizon=1) → high/low فردا
      ↓
گیت‌های استراتژی → براکت TP/SL (SL ± spread)
      ↓
ورود next-open با typical price (O+H+L+C)/4
      ↓
خروج کندل‌به‌کندل (همان‌بار stop-first) → PnL → گزارش
```

**دو مدل:**
| مدل | تایم‌فریم | window | خروجی | loss | optimizer |
|-----|-----------|--------|-------|------|-----------|
| signal (`gold_signal_5m`) | 5M | 300 | BUY/SELL binary | SparseCategoricalCrossentropy | AdamW(lr=1e-4, wd=1e-5) |
| range (`gold_range_1d`) | 1D | 150 | high/low فردا (seq2seq) | 3·Huber+6·MAE+1·MSE | AdamW(lr=1e-3, wd=1e-4) |

هر دو: ReduceLROnPlateau + EarlyStopping.

---

## ۳. گیت‌های استراتژی (`dual_model_strategy.py`)

۱. session filter (ساعت‌های خوب UTC) · ۲. هر دو forecast موجود · ۳. اطمینان سیگنال ·
۴. انسجام range (high>low) · ۵. حرکت > هزینه · ۶. حداقل فاصلهٔ SL.

> ⚠️ گیت reward/risk در Strategy نیست؛ چون entry_price در لحظهٔ تصمیم معلوم نیست.
> اکنون در `TradeBracket.from_model_levels` با `reward_risk_multiplier` enforce می‌شود.

---

## ۴. ساختار کد (src/ShadBotTrader)

| لایه | فایل‌های کلیدی |
|---|---|
| core | container، event_bus، lifecycle، plugins، services، result |
| domain | market, trading, strategy, risk, portfolio, dataset, feature, ai, simulation, learning, deployment, account |
| application | bootstrap, runtime, ~۱۶ سرویس |
| infrastructure | data(parquet/MT5), feature(20 calculator/227 feat), ai(WaveNet+trainer+predictor), trading, simulation, persistence(SQLite), config, logging |
| presentation | داشبورد وب، Command bus، ریپلی، Gateway |
| project | Project Intelligence (scanner/builder/exporter) |

**تعداد (Statistics.json):** 317 فایل منبع · 47505 خط · 758 کلاس · 4239 تابع ·
121 فایل تست · 21051 خط تست.

---

## ۵. وضعیت تست (2026-08-26)

```
1449 passed · 0 failed · 49 skipped   (49 skip = تست‌های TensorFlow)
```
- **گیت تست سبز.** ۲۹ تستِ کهنه که با تغییرات عمدیِ فازهای ۵۲–۵۸ همگام نبودند،
  اصلاح شدند (عدد فیچر 109→227، Range 1H→1D، انتقال گیت R/R به Bracket، فرمت progress).
- یک تست واحد جدید برای گیت R/R در `tests/unit/simulation/test_bracket.py` اضافه شد.
- `ruff` و `black` سبز.

---

## ۶. تغییرات مهمی که در مستنداتِ قدیمی نیستند

- **فیچرها ۱۰۹ → ۲۲۷** (با `model_scope`: range≈182، signal≈177).
- **فازهای ۵۰–۵۸** بهینه‌سازی بکتست (گزارش‌ها در `docs/Report/PHASE50..58`).
- **فاز ۵۷:** spread برای گسترش SL، typical-price entry، EarlyStopping، resume همهٔ foldها.
- **فاز ۵۸:** معماری signal window=300.
- `CURRENT_STATE.md` بازنویسی شد (نسخهٔ زنده).

---

## ۷. نکته‌های فنی که باید یادت بماند

- **علیت (causal-only):** ماتریس فیچر فقط با `causal_only=True` و scope-aware ساخته می‌شود؛
  هیچ آینده‌ای به پنجره نشت نمی‌کند.
- **binary signal:** فقط SELL/BUY؛ HOLD تصمیمِ Strategy است نه خروجی مدل.
- **اسپرد آلپاری:** pct 0.06%، commission=0.
- **حسابداری:** fill-based؛ fees به کل round-trip می‌چسبد.
- **مدل‌های آموزش‌دیده:** signal v1 (~65-80%)، range_1d v3 (val_mae 0.000010).
- **گیت** (`--resume`) و checkpoint هر epoch برای نجات آموزش از قطعی.

---

## ۸. وضعیت «کجای کاریم» و گام بعدی

پروژه در فاز **۵۷/۵۸** است، وسطِ بهینه‌سازی بکتست. وضعیت مدل‌ها: هر دو train شده‌اند
ولی بکتست هنوز `trades=0` گزارش می‌دهد → مدل‌ها باید بهتر train شوند یا آستانه/تنظیمات
بکتست اصلاح شود.

**گام‌های پیشنهادی (طبق CURRENT_STATE کاربر):**
1. آموزش signal با window=300.
2. آموزش range با seq2seq (خوب شده؛ ارزیابی v3).
3. بکتست → بررسی `trades > 0`.
4. اگر trades>0: فعال‌کردن session filter.

---

*این سند نقطهٔ ورود سریع به پروژه است؛ جزئیات بیشتر در `WORKLOG.md`,
`IMPLEMENTATION_STATUS.md`, `STATUS_AUDIT_2026-08-26.md`, و گزارش‌های `docs/Report/`.*
