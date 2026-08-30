# فاز ۹۵ — گزارش: تارگت ATR-نرمال‌شدهٔ مدل رنج

**تاریخ:** 2026-08-30
**درخواست:** «تارگت رو با ATR هم اصلاح کن. بعد توی بکتست و هرجایی که قراره
قیمت رو پیش‌بینی کنیم نحوهٔ محاسبهٔ قیمت پیش‌بینی رو هم اصلاح کن.»

---

## ۱. مسئله

از تحلیل `RANGE_MODEL_CONSTANT_OFFSET_ROOT_CAUSE.md`:

| ورودی | تارگت قدیمی | نتیجه |
|-------|-------------|-------|
| minmax روی [-2,+2] — بدون مقیاس قیمت | `(high[t+k] − close[t]) / close[t]` — درصد خام | مدل میانگین ثابت دیتاست را خروجی می‌دهد: ±0.06% (1H) / ±0.60% (1D) برای همهٔ کندل‌ها |

## ۲. تارگت جدید (فاز ۹۵)

```
high_seq[t,k] = (high[t+k] − close[t]) / ATR14[t]
low_seq[t,k]  = (low[t+k]  − close[t]) / ATR14[t]
```

- مدل «چند ATR» یاد می‌گیرد، نه درصد خام.
- `atr_14` خودش جزو فیچرهای ورودی است → مدل می‌تواند رابطهٔ
  «رژیم نوسان ↔ دامنهٔ حرکت» را یاد بگیرد؛ خروجی دیگر ثابت نیست.
- ATR با `wilder_atr_series` ساخته می‌شود (علوی؛ expand-mean برای
  ۱۴ کندل اول، سپس هموارسازی Wilder). **همان تعریف** در آموزش
  (لیبل) و پیش‌بینی (de-normalize) استفاده می‌شود تا دو دنیا یکی بمانند.

## ۳. محاسبهٔ قیمت در مصرف — یک نقطه، همه‌جا درست

تبدیل فقط یک‌بار در `RangePredictor` انجام می‌شود:

```
price          = close + mult × ATR14(کندل مرجع)
high_offset(%) = mult × ATR / close   ← برای نمایش‌های درصدی قدیمی
```

`RangeForecast` در حالت atr قیمت را با فرمول ATR می‌سازد؛ پس
براکت TP/SL، بکتست، استراتژی و GUI همه **بدون هیچ تغییری** قیمتِ درست
می‌گیرند.

### سازگاری با مدل‌های قدیمی

- `ModelRecord.target_units`: `"pct"` (پیش‌فرض/قدیمی) یا `"atr"` (جدید).
- پیش‌بینی‌کنندهٔ pct دقیقاً رفتار قبل را دارد؛ رکوردهای قدیمی که فیلد
  ندارند هم pct خوانده می‌شوند.
- `atr_reference` فقط به پیش‌بینی‌کننده‌های ATR-unit پاس می‌شود — استاب‌ها
  و امضاهای قدیمی نمی‌شکنند. مدل ATR بدون ATR → `ValidationError` واضح
  (قیمت غلطِ خاموش ممنوع).

## ۴. فایل‌های تغییرکرده

| فایل | تغییر |
|------|-------|
| `infrastructure/ai/target_builder.py` | `wilder_atr_series` + `atr_from_candles` + پارامتر `units` در هر دو لیبل‌ساز رنج (پیش‌فرض `"atr"`) |
| `domain/ai/prediction_target.py` | `RangeForecast`: فیلدهای ATR + فرمول قیمت ATR-آگاه |
| `infrastructure/ai/dual_predictor.py` | `RangePredictor(target_units=…, atr_reference=…)` + تبدیل |
| `infrastructure/ai/model_catalogue.py` | `ModelRecord.target_units` + round-trip |
| `application/services/dual_model_service.py` | `PreparedDataset.target_units` + `hyperparameters["target_units"]` |
| `application/services/dual_model_backtest_service.py` | خواندن units از رکورد → predictor + source |
| `infrastructure/simulation/dual_model_prediction_source.py` | `range_target_units` + `_reference_atr` (علوی، memoized) |
| `presentation/gateway/range_forecast_inspector.py` | ATRِ کندل کلیک‌شده + نقاط `×ATR` در پاسخ |
| `presentation/web/data_renderer.py` | نمایش `2.13×ATR (0.62%)` در جدول forecast |
| `infrastructure/ai/live_matrix.py` | `LiveWindow.atr_reference` |
| `application/services/live_decision_service.py` | پاس‌دادن ATR فقط برای predictorهای ATR-unit |
| `scripts/run_dual_models.py` | سربرگ `target units`، sanity forecast در units درست، رکورد با `target_units` |
| `presentation/commands/handlers.py` | خط `range units` در خلاصهٔ بکتست |

## ۵. تست‌ها

- جدید: `test_atr_range_target.py` (13) — ATR دست‌محاسبه، علیت،
  round-trip دلاری، نشت افق، سری تخت، seq2seq.
- جدید: `test_range_predictor_atr.py` (9) — تبدیل دلار، سینکِ درصد،
  ردِ بدون-ATR، حفظ رفتار pct.
- جدید: `test_range_atr_wiring.py` (6) — پاس‌دادن ATR علوی در source،
  memoization، round-trip رکورد.
- بدهی فاز ۹۴: شمارنده‌های کاتالوگ (227→229 و ...) آپدیت شد.

**گیت کیفیت:** ruff ✅ · black ✅ · pytest **1532 passed, 54 skipped**

## ۶. گام بعدی (اپراتور)

1. **ریترین مدل رنج** با تارگت جدید (خودکار — پیش‌فرض جدید atr است):

```bash
python scripts/run_dual_models.py --with-features \
  --model range --range-timeframes 1H \
  --epochs 50 --folds 3 --window 150 --horizon 12 \
  --learning-rate 0.0005
```

2. در سربرگ آموزش باید ببینید: `target units: atr`.
3. بعد از آموزش، sanity forecast باید ضرایب **متفاوت** برای کندل‌های
   مختلف بدهد (نه عدد ثابت). با `/data` و کلیک روی چند کندل چک کنید —
   ستون `×ATR` باید بین کندل‌ها فرق کند.
4. بکتست با مدل جدید؛ در خلاصه، `range units: atr` ثبت می‌شود.
5. اگر خروجی باز هم تنوع کم داشت → گام بعدی طراحی: وزن‌دهی loss یا
   threshold سیگنال 0.3–0.4%.
