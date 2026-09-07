# فهرست فازهای ۱۰۰ تا ۱۱۵

این فایل index سریع فازهای جدیدی است که بعد از کار روی مدل score و بررسی منابع خارجی ثبت شدند.

---

## فازهای انجام‌شده

| فاز | وضعیت | خلاصه | فایل |
|---|---|---|---|
| 100 | ✅ کامل | trend_score روی کندل واقعی 1D، آموزش v1، model card و verdict بدون edge | `Phase100.md` |
| 101 | ✅ کامل | رفع live log آموزش GUI روی Windows | `Phase101.md` |
| 102 | ✅ کامل | گزینهٔ MAE برای trend_score و monitor روی val_mae | `Phase102.md` |
| 103 | ✅ کامل | audit محاسبه/normalization score و حذف fake tail label | `Phase103.md` |
| 104 | ✅ کامل | input scaling مخصوص trend_score به `[-1,+1]` | `Phase104.md` |
| 105 | ✅ کامل/docs | بررسی پروژه Leci37 و استخراج الگوهای قابل استفاده | `Phase105.md` |
| 106 | ✅ کامل/docs | بررسی Alpaca، ari99، Onepagecode و cleanup workspace | `Phase106.md` |

---

## فازهای پیشنهادی آماده اجرا

| فاز | وضعیت | خلاصه | اولویت |
|---|---|---|---|
| 107 | 🟡 پیشنهادی | audit کامل trend_signal و label distribution/metrics | بسیار بالا |
| 108 | 🟡 پیشنهادی | class weights + F1/PR-AUC برای trend_signal | بسیار بالا |
| 109 | 🟡 پیشنهادی | threshold calibration و heatmap backtest | بالا |
| 110 | 🟡 پیشنهادی | feature selection train-only | بالا |
| 111 | 🟡 پیشنهادی | مدل‌های POS/NEG binary event | بالا |
| 112 | 🟡 پیشنهادی | benchmark مدل دو-branch returns+features | متوسط/بالا |
| 113 | 🟡 پیشنهادی | random baseline، Monte Carlo، White Reality-style checks | بالا |
| 114 | 🟡 پیشنهادی | external/regime features مخصوص XAUUSD | متوسط/بالا |
| 115 | 🟡 پیشنهادی | live decision audit کامل | متوسط، قبل از live جدی الزامی |

---

## ترتیب اجرای پیشنهادی

```text
107 → 108 → 109 → 110 → 111 → 113 → 112 → 114 → 115
```

دلیل: اول target/metric/evaluation درست شود، بعد feature/model جدید و در نهایت live audit.

---

## handoff کامل

برای شروع چت جدید، اول این فایل را بخوان:

```text
docs/SESSION_HANDOFF_2026-09-07.md
```

بعد اگر فاز اجرایی می‌خواهی، از `Phase107.md` شروع کن.
