# وضعیت فعلی — 2026-10-20

مسیر فعال خلوت شد. train جدید اجرا نشد.

```text
active : MetaTrader ingest, dataset, features, range model
moved  : old_version/
untouched : legacy/
```

```text
FREEZE_RANGE_MULTISTEP_ROUTE
FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
gold_range_4h / gold_range_1d : untouched
PAPER_OR_LIVE : BLOCKED
```

نسخهٔ قبلی کامل، شامل GUI و backtest و pivot و hybrid، در `old_version/` است.
`legacy/` کد قدیمی خود مالک است و جابه‌جا نشده.

گزارش خلوت‌کردن: `docs/ACTIVE_SCOPE.md`.

بررسی دیتاست و فیچر:

```text
python scripts/inspect_dataset_features.py --storage-root datasets --port 8765
```
