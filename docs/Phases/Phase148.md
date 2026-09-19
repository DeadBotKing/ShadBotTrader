# Phase148 — Range-aware Prediction/Backtest Archive

**Status:** ✅ Phase148A implemented  
**Type:** Step 4 research archive and range-aware trade simulation  
**Production status:** BLOCKED — no paper/live permission

---

## Why this phase exists

The owner requested Step 4 while Step 3 full Option B training is running:

```text
ذخیره کامل prediction/backtest archive
TP و SL از مدل‌های range حساب شود
بعداً از خروجی برای فیلترسازی استفاده کنیم
```

The first Phase146/147 PnL audits used ATR-based brackets:

```text
TP = ATR * tp_multiplier
SL = ATR * sl_multiplier
```

Phase148A adds a more realistic research archive that can use range forecasts for TP/SL.

---

## Implemented file

```text
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
```

GUI command:

```text
Backtest sequence WaveNet range-aware archive
```

Tests:

```text
tests/unit/ai/test_pivot_sequence_range_archive.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

---

## Inputs

```text
Sequence tensor : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
Meta            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
Flat parquet    : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
Model           : Option A or Option B sequence WaveNet .keras + vN_training.json
```

The script supports both:

```text
Option A single-input sequence WaveNet
Option B grouped-input sequence WaveNet
```

---

## Range source modes

```text
--range-source auto
--range-source flat
--range-source models
```

### flat

Reads range columns from the sequence flat file. Both raw and `src5m_`-prefixed names are supported:

```text
range_4h_high_price / src5m_range_4h_high_price
range_4h_low_price  / src5m_range_4h_low_price
range_1d_high_price / src5m_range_1d_high_price
range_1d_low_price  / src5m_range_1d_low_price
range_4h_up_room / down_room
range_1d_up_room / down_room
```

### models

Uses project range models:

```text
gold_range_4h
gold_range_1d
```

via the same project `RangeFeatureProvider` mechanism used in prior hybrid telemetry tooling.

### auto

Uses flat range columns if available; otherwise attempts range models.

---

## Range-aware bracket logic

For BUY:

```text
TP candidate = range_4h_high_price
Optional 1D cap = min(range_4h_high_price, range_1d_high_price)
SL = range_4h_low_price
```

For SELL:

```text
TP candidate = range_4h_low_price
Optional 1D cap = max(range_4h_low_price, range_1d_low_price)
SL = range_4h_high_price
```

Then safety bounds are applied:

```text
--min-tp-distance
--min-sl-distance
--max-tp-atr
--max-sl-atr
```

Modes:

```text
range        : raw range distances with min distance only
range_capped : range distances capped by ATR
atr          : old ATR-only fallback logic
```

Fallback:

```text
--range-fallback skip
--range-fallback atr
```

---

## Archive outputs

```text
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest.json
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest.html
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_predictions.parquet
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_predictions.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_trades.parquet
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_trades.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_monthly.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_side.csv
```

The archive stores per-sample fields needed for Step 5 filtering:

```text
timestamp
row_id
model probabilities
selected action
decision reason
range high/low/room values
TP/SL distances
bracket source
trade outcome
PnL
side/month summaries
```

---

## First recommended command

Use the currently better Option B model id and evaluate the test split first:

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

---

## Verification

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 60 passed
```

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```
