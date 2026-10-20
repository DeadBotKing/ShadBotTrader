# ShadBotTrader — active path

نسخهٔ فعال فقط برای چک کردن این چهار بخش است:

```text
1. دریافت دیتا از MetaTrader 5
2. ساخت دیتاست
3. ساخت فیچر
4. مدل رنج
```

نسخهٔ قبلی کامل پروژه اینجاست و با کد قدیمی خودت قاطی نشده:

```text
old_version/   نسخهٔ قبلی ShadBotTrader
legacy/        کد قدیمی خود مالک؛ دست نخورده
```

Paper/live همچنان بسته است. این خلوت‌کردن edge جدید نساخته است.

## MetaTrader

روی ویندوز، ترمینال MT5 باید باز باشد.

```text
python -m ShadBotTrader.data_cli mt5-check
python -m ShadBotTrader.data_cli mt5-resolve --symbol XAUUSD
python -m ShadBotTrader.data_cli mt5-ingest --symbol XAUUSD --timeframe 4H --bars 50000 --storage-root datasets
python -m ShadBotTrader.data_cli mt5-ingest --symbol XAUUSD --timeframe 1D --bars 10000 --storage-root datasets
```

CSV:

```text
python -m ShadBotTrader.data_cli ingest --csv PATH --symbol XAUUSD --timeframe 4H --storage-root datasets
```

## Dataset و features

```text
python scripts/run_training_dataset.py --status --storage-root datasets
python scripts/run_features.py
```

## بررسی دیتاست و فیچر

```text
python scripts/inspect_dataset_features.py --storage-root datasets --port 8765
```

بعد در مرورگر باز کن: `http://127.0.0.1:8765`

این صفحه دیتاست Parquet را لیست می‌کند، کندل‌ها را رسم می‌کند، و `FXTradingFeatureSetV1` را با همان calculatorهای پروژه حساب می‌کند. چیزی را train یا ذخیره نمی‌کند.

## Range model

آموزش مدل رنج، بدون overwrite کردن idهای محافظت‌شده، از همین اسکریپت‌هاست:

```text
scripts/run_dual_models.py
scripts/train_range_multistep.py
```

`run_dual_models.py` هنوز شاخهٔ signal/trend را داخل همان فایل دارد، چون trainer رنج همان‌جاست. پکیج‌های backtest، live، pivot، hybrid و GUI به `old_version/` منتقل شده‌اند.

Audit رنج:

```text
scripts/audit_range_model_reliability.py
scripts/audit_range_multistep_accuracy.py
```

## حکم

```text
FREEZE_RANGE_MULTISTEP_ROUTE
gold_range_4h / gold_range_1d : جایگزین نشوند
PAPER_OR_LIVE : BLOCKED
```
