# Phase148A Report — Range-aware Sequence WaveNet Archive

Date: 2026-09-19

## Goal

Implement Step 4 of the owner roadmap:

```text
ذخیره کامل prediction/backtest archive
TP و SL از مدل‌های range حساب شود
بعداً از خروجی برای فیلترسازی استفاده کنیم
```

The prior Phase146/147 PnL audits used ATR-only brackets. Phase148A adds range-aware brackets and full archive outputs for later anti-overfit filtering.

## Implemented

```text
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
```

GUI:

```text
Backtest sequence WaveNet range-aware archive
```

## Capabilities

```text
Supports Option A and Option B sequence WaveNet records
Loads model predictions
Reads range forecasts from flat source features or range models
Builds TP/SL from range high/low predictions
Simulates trades with spread, same-bar policy, max hold, and risk sizing
Writes full predictions archive
Writes full trades archive
Writes monthly and side summaries
```

## Range bracket modes

```text
range        : use range forecast distances directly
range_capped : use range forecast distances capped by ATR
atr          : old ATR-only behavior
```

For BUY:

```text
TP = range high
SL = range low
```

For SELL:

```text
TP = range low
SL = range high
```

With optional 1D TP cap and ATR caps.

## Archive files

```text
latest.json
latest.html
latest_predictions.parquet / latest_predictions.csv
latest_trades.parquet / latest_trades.csv
latest_monthly.csv
latest_side.csv
```

These are intended for Step 5 filtering.

## First command

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet_range.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 0 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --range-source auto `
  --range-bracket-mode range_capped `
  --range-fallback skip `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --range-1d-version 0 `
  --range-4h-version 0 `
  --use-1d-tp-cap 1 `
  --min-range-4h-room 0 `
  --min-range-1d-room 0 `
  --min-tp-distance 0.5 `
  --min-sl-distance 0.5 `
  --max-tp-atr 2.0 `
  --max-sl-atr 1.25 `
  --atr-tp-multiplier 0.75 `
  --atr-sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_range_archive `
  --report-title "Phase148A range-aware sequence WaveNet archive"
```

## Verification

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 60 passed
```

## Production status

```text
BLOCKED — research archive only.
No Phase134.
No paper shadow.
No live trading.
```
