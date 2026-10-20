# Phase148C Report — Range-Aware Archive Result Failed

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
