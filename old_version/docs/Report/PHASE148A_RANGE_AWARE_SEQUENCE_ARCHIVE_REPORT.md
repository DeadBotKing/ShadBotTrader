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

## Phase148B range-aware archive now supports train/validation splits — 2026-09-20

The owner proposed the correct next direction after the raw Option B rebuild showed validation-to-test transfer failure:

```text
Build/run a more realistic simulation backtest where TP and SL are derived from range forecasts.
Run it fully on train and validation first.
Then perform anti-overfit filtering/selection from those archive outputs before any test confirmation.
```

Assessment:

```text
This is the correct direction. The previous ATR-only PnL checks may be too crude for exit geometry, and test must be held back for confirmation rather than used for discovery.
```

Implementation update:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
GUI: Backtest pivot sequence WaveNet PnL
GUI: Backtest sequence WaveNet range-aware archive
```

Both backtest scripts now support:

```text
--eval-split train
```

Previously Phase148A range-aware archive supported only:

```text
test, validation, all, tail
```

Now the realistic range-aware archive can be generated separately for:

```text
train      → in-sample anatomy / diagnostics only
validation → discovery / filter selection
test       → confirmation only, not tuning
```

Anti-overfit rule:

```text
Do not use test for discovery.
Run train + validation range-aware archives first.
Discover candidate thresholds/filters from train/validation only.
Then run exactly one unchanged confirmation on test.
If test fails, reject.
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/handlers.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase148C range-aware train/validation archive result — range-model TP/SL failed badly — 2026-09-20

The owner ran the Phase148B range-aware archive on the rebuilt raw Option B 24k model using range-derived TP/SL from range models.

Common configuration:

```text
model_id            : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version       : 1
max_samples         : 24000
range_source        : auto → models
range_bracket_mode  : range_capped
range_fallback      : skip
range_1d_model_id   : gold_range_1d
range_4h_model_id   : gold_range_4h
use_1d_tp_cap       : 1
max_tp_atr          : 2.0
max_sl_atr          : 1.25
min_tp_distance     : 0.5
min_sl_distance     : 0.5
hold_bars           : 48
spread              : pct 0.06
same_bar_policy     : stop_first
```

Train archive result:

```text
eval_split        : train
evaluated period  : 2025-11-28 17:05:00+00:00 → 2026-05-25 19:15:00+00:00
evaluated_samples : 16800
trades            : 1176
BUY / SELL        : 547 / 629
wins / losses     : 392 / 784
win_rate          : 33.3333%
final_balance     : 6.5162807311
return_percent    : -93.4837192689%
total_cash_pnl    : -93.4837192689
profit_factor     : 0.6073804291
max_drawdown_cash : 93.5008911264
take_profit       : 356
stop_loss         : 769
timeout           : 51
invalid_bracket   : 1410
BUY PnL           : -28.2722708191
SELL PnL          : -65.2114484498
positive_months   : 0
negative_months   : 7
```

Train monthly summary:

```text
2025-11 :  -4.9010 / 5 trades
2025-12 : -45.9841 / 233 trades
2026-01 : -24.8121 / 215 trades
2026-02 :  -2.3687 / 167 trades
2026-03 :  -1.3067 / 176 trades
2026-04 :  -9.3004 / 215 trades
2026-05 :  -4.8107 / 165 trades
```

Validation archive result:

```text
eval_split        : validation
evaluated period  : 2026-05-28 09:20:00+00:00 → 2026-07-01 09:05:00+00:00
evaluated_samples : 3264
trades            : 250
BUY / SELL        : 151 / 99
wins / losses     : 53 / 197
win_rate          : 21.2000%
final_balance     : 27.1922217861
return_percent    : -72.8077782139%
total_cash_pnl    : -72.8077782139
profit_factor     : 0.3114226665
max_drawdown_cash : 76.6329350539
take_profit       : 49
stop_loss         : 194
timeout           : 7
invalid_bracket   : 392
BUY PnL           : -50.9467117142
SELL PnL          : -21.8610664997
positive_months   : 0
negative_months   : 2
```

Validation monthly summary:

```text
2026-05 :  -5.5864 / 16 trades
2026-06 : -67.2213 / 234 trades
```

Comparison to ATR validation for the same rebuilt model:

```text
ATR validation:
  final_balance : 108.7914
  PF            : 1.2554
  maxDD         : 5.9716
  BUY PnL       : -1.8550
  SELL PnL      : +10.6465

Range-aware validation:
  final_balance : 27.1922
  PF            : 0.3114
  maxDD         : 76.6329
  BUY PnL       : -50.9467
  SELL PnL      : -21.8611
```

Interpretation:

```text
The owner’s proposed workflow was correct: build/run realistic range-aware TP/SL archive before filtering.
The result shows the current range-model TP/SL geometry is unusable with this sequence model.
This is not a model-entry improvement; it is a bracket failure.
```

Key failure signatures:

```text
- range_source resolved to models, not flat cached range columns.
- Train and validation both collapse, so this is not only out-of-time overfit.
- Stop-loss rate is extremely high: train 769/1176, validation 194/250.
- Timeouts nearly disappear under range brackets, meaning trades are being resolved by TP/SL quickly, mostly by SL.
- Many invalid brackets occur: train 1410, validation 392.
- BUY and SELL are both negative under range-aware validation.
- Many preview trades show very tight stop distances, sometimes near min_sl_distance=0.5, combined with fixed risk sizing and stop_first same-bar policy.
```

Decision:

```text
Reject current Phase148 range-model TP/SL configuration as a viable simulation rule.
Do not use these range-aware train/validation archives for strategy filter selection yet; their base bracket geometry fails before filtering.
Do not run test range-aware confirmation for this configuration.
The next research should be bracket diagnostics/calibration, not signal filtering.
No Phase134. No paper shadow. No live trading.
```

Recommended next phase:

```text
Phase150A — Range bracket geometry audit for pivot sequence archive
```

Recommended controls for Phase150A:

```text
1. ATR mode control inside the same archive script:
   --range-bracket-mode atr
   This should roughly reproduce the ATR baseline and proves the archive/prediction path is not the source of damage.

2. Range model diagnostics:
   distribution of tp_distance/sl_distance, min-distance hits, same-bar stop rate, invalid bracket rate, side/month breakdown.

3. Validation-only bracket grid:
   min_sl_distance: 0.5, 2, 5, 10, 15
   min_tp_distance: 0.5, 2, 5
   max_tp_atr/max_sl_atr alternatives
   use_1d_tp_cap 0/1
   range_fallback skip/atr
   same_bar_policy stop_first/tp_first as sensitivity only

4. Test remains untouched until a validation-selected bracket policy exists.
```
