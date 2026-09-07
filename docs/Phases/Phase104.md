# فاز ۱۰۴ — input scaling مخصوص trend_score به [-1,+1]

**تاریخ:** 2026-09-07
**وضعیت:** ✅ کامل
**Commit:** `fd4a190`

---

## مسئله

اپراتور پیشنهاد داد چون target مدل score خودش در بازهٔ `[-1,+1]` است، بهتر است input featureها هم برای این مدل در همین بازه min-max شوند. مدل range همچنان از `[-2,+2]` استفاده کند.

---

## تصمیم

```text
range/signal/trend/trend_signal → input scale [-2,+2]
trend_score                    → input scale [-1,+1]
```

---

## تغییرات

### `data_windowing.py`

اضافه شد:

```python
DEFAULT_SCALE_RANGE = (-2.0, 2.0)
TREND_SCORE_SCALE_RANGE = (-1.0, 1.0)
normalize_scale_range(...)
input_scale_range_for_model(...)
scale_window_for_model(...)
```

`minmax_scale_window` و sample builders حالا `scale_range` می‌گیرند.

### `model_roles.py`

فیلد جدید در `ModelRole`:

```python
input_scale_range: tuple[float, float] = (-2.0, 2.0)
```

در `trend_score_model_role`:

```python
input_scale_range=(-1.0, 1.0)
```

### `wavenet_trainer.py` و `window_generator.py`

هم مسیر in-memory و هم streamed training scale range نقش مدل را مصرف می‌کنند.

### inference/evaluation

این مسیرها scale ذخیره‌شدهٔ مدل را مصرف می‌کنند:

```text
scripts/run_dual_models.py sanity prediction
scripts/evaluate_trend_score_1d.py
ModelEvaluationService
RangeForecastInspector
presentation/web/server.py
WavenetPredictor
```

### `ModelRecord`

فیلد جدید:

```python
input_scale_range: [-2.0, 2.0] یا [-1.0, 1.0]
```

مدل‌های قدیمی که این فیلد را ندارند، برای سازگاری `[-2,+2]` فرض می‌شوند.

### resume safety

اگر checkpoint قدیمی با scale متفاوت باشد:

```text
resume رد می‌شود و آموزش از صفر شروع می‌شود
```

برای جلوگیری از مخلوط شدن وزن‌های مدل `[-2,+2]` با input جدید `[-1,+1]`.

---

## audit عددی

روی دیتای سندباکس:

```text
gold_trend_score_1d scale (-1.0, 1.0) shape (150, 182) min -1.0 max 1.0 target_col_excluded True
gold_range_1d       scale (-2.0, 2.0) shape (150, 182) min -2.0 max 2.0 target_col_excluded True
```

یعنی همهٔ featureهای score، شامل قیمت‌های اصلی، بعد از scaling داخل `[-1,+1]` هستند و target داخل input نیست.

---

## لاگ آموزش بعد از فاز

برای trend_score باید دیده شود:

```text
input scale: minmax [-1, +1] per feature/window
scale audit: trend_score feature windows stay inside [-1,+1]
```

---

## هشدار عملی

بعد از این فاز، `trend_score` را از صفر train کن:

```text
resume = 0
```

چون وزن‌های قبلی با scale متفاوت train شده‌اند.
