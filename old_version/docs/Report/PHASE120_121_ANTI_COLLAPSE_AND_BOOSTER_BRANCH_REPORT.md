# گزارش فاز ۱۲۰/۱۲۱ — Anti-collapse metrics و Trend-signal Booster Branch

**تاریخ:** 2026-09-08  
**وضعیت:** پیاده‌سازی شد  
**دامنه:** جلوگیری از فریب metricها بعد از collapse مدل WaveNet و ساخت branch بوستر مستقل برای `trend_signal`.

---

## 1) علت شروع این فاز

pilotهای واقعی اپراتور نشان دادند:

```text
class_weight auto → uniform probability collapse نزدیک 33/33/33
class_weight off  → single-class collapse مثل always-BUY یا always-SELL
```

در نتیجه `val_buy_sell_f1` به‌تنهایی کافی نبود؛ چون اگر فقط یک سمت action را predict کنیم، میانگین F1 خرید/فروش می‌تواند عدد ظاهراً قابل قبول بدهد.

---

## 2) فاز ۱۲۰ — متریک‌های ضد collapse

در مسیر metricهای classification اضافه شد:

```text
val_sell_predicted
val_hold_predicted
val_buy_predicted
val_predicted_class_count
val_single_class_collapse
val_action_min_f1
val_action_min_recall
val_action_min_f1_supported
val_action_min_recall_supported
val_action_supported_class_count
val_action_predicted_supported_count
val_action_collapse
```

فایل اصلی:

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
```

`print_quality` هم این‌ها را نمایش می‌دهد و اگر action collapse رخ دهد هشدار می‌دهد.

فایل:

```text
scripts/run_dual_models.py
```

---

## 3) مانیتور جدید

`--monitor-metric` حالا علاوه بر metricهای قبلی این‌ها را هم قبول می‌کند:

```text
val_action_min_f1
val_action_min_f1_supported
```

برای trend_signal، monitor سخت‌گیرانه‌تر پیشنهادی:

```text
--monitor-metric val_action_min_f1_supported
```

چون اگر BUY یا SELL supported باشد ولی مدل آن را predict نکند، این metric صفر می‌شود.

---

## 4) فاز ۱۲۱ — Booster branch

فایل‌های جدید:

```text
src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py
scripts/train_trend_signal_boosters.py
requirements-boosters.txt
```

GUI command جدید:

```text
Train trend-signal booster
```

Action:

```text
train_trend_signal_booster
```

---

## 5) روش Booster branch

به جای tensor سه‌بعدی WaveNet:

```text
[window=288, features=179]
```

برای هر پنجره یک ردیف tabular ساخته می‌شود:

```text
last
basic: last + delta_1 + mean/std/delta برای scaleهای 12/48/288
multi_scale: min/max/slope هم اضافه می‌کند
```

مدل‌های قابل استفاده:

```text
LightGBM
XGBoost
CatBoost
```

dependencyها optional هستند:

```text
pip install -r requirements-boosters.txt
```

---

## 6) دستور پیشنهادی مرحله بعد

اول `requirements-boosters.txt` را نصب کن، بعد:

```powershell
python -u scripts/train_trend_signal_boosters.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --booster auto `
  --output-mode multiclass `
  --summary-mode basic `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --folds 3 `
  --val-size 2000 `
  --class-weight auto `
  --n-estimators 400 `
  --learning-rate 0.03 `
  --storage-root datasets
```

اگر multiclass باز collapse کرد، specialistها را جدا تست کن:

```text
--output-mode buy
--output-mode sell
```

---

## 7) معیار پذیرش

برای multiclass:

```text
val_action_collapse = 0
val_action_min_f1_supported > 0
val_predicted_class_count >= 2
sell_f1 و buy_f1 هر دو غیرصفر وقتی هر دو support دارند
```

برای binary specialist:

```text
val_event_f1
val_event_precision
val_event_recall
val_event_ap
```

---

## 8) تست‌ها

اضافه/به‌روزرسانی شد:

```text
tests/unit/ai/test_classification_weights_metrics.py
tests/unit/ai/test_tabular_window_summary.py
tests/unit/ai/test_trend_signal_booster_script.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

`pytest` کامل پاس شد.
