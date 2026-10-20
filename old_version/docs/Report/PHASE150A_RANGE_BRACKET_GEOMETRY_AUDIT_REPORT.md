# Phase150A Report — Range Bracket Geometry Audit

Date: 2026-09-20

## Goal

Build a diagnostic audit after Phase148C showed that current range-model TP/SL geometry fails badly on both train and validation.

The audit must not tune on test. It replays already-archived Phase148 predictions with alternative bracket policies.

## Implemented

```text
scripts/audit_pivot_sequence_range_bracket_geometry.py
GUI: Audit sequence range bracket geometry
```

## Inputs

```text
--predictions-path run_logs\pivot_pattern_sequence_wavenet_range_archive_validation\latest_predictions.parquet
--flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
```

## Functionality

The script:

```text
- loads Phase148 prediction archive
- keeps model-selected BUY/SELL actions fixed
- replays multiple TP/SL policies
- includes ATR-control mode
- tests range_capped policies with min TP/SL distance grids
- tests 1D TP cap on/off
- tests range fallback skip/atr
- records stop-loss/take-profit/timeout rates
- records invalid bracket counts and min-distance hits
- ranks candidate policies by score metric
```

## Outputs

```text
run_logs\pivot_sequence_range_bracket_geometry\latest.json
run_logs\pivot_sequence_range_bracket_geometry\latest.html
run_logs\pivot_sequence_range_bracket_geometry\latest_grid.csv
run_logs\pivot_sequence_range_bracket_geometry\latest_best_trades.csv
```

## GUI

Added dashboard command:

```text
Audit sequence range bracket geometry
```

## Interpretation rules

```text
- ATR mode is a control path.
- A validation-only best policy is not production approval.
- Test can only confirm one unchanged validation-selected policy.
- Walk-forward is required before any paper/live discussion.
```

## Verification

```text
python -m py_compile scripts/audit_pivot_sequence_range_bracket_geometry.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_range_bracket_geometry.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — research diagnostic only.
No Phase134.
No paper shadow.
No live trading.
```

## Phase150A range bracket geometry audit result — ATR control wins, range adds no edge — 2026-09-20

The owner ran Phase150A on the validation Phase148 prediction archive.

Input:

```text
predictions_path : run_logs\pivot_pattern_sequence_wavenet_range_archive_validation\latest_predictions.parquet
flat_path        : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
split_name       : validation
evaluated_rows   : 3264
policies         : 735
score_metric     : drawdown_adjusted
min_trades       : 30
```

Best policy:

```text
policy_key        : mode=atr|fallback=skip|use1d=0|min_tp=0.5|min_sl=0.5|max_tp_atr=0|max_sl_atr=0|min4h=0|min1d=0|same=stop_first
range_bracket_mode: atr
trades            : 110
BUY / SELL        : 70 / 40
wins / losses     : 62 / 48
win_rate          : 56.3636%
final_balance     : 108.7914207603
return_percent    : +8.7914207603%
total_cash_pnl    : +8.7914207603
profit_factor     : 1.2554081199
max_drawdown_cash : 5.9715931205
BUY PnL           : -1.8550476298
SELL PnL          : +10.6464683900
positive_months   : 2
negative_months   : 0
pass_gate         : 1
```

Baseline ATR policy is identical to the best policy:

```text
baseline_atr_policy.rank = 1
baseline_atr_policy.PF   = 1.2554081199
```

Top-15 policies were all ATR variants. The `min_tp_distance` / `min_sl_distance` values did not change the ATR result because actual ATR distances were already larger than those minima:

```text
avg_tp_distance    : 31.0171
avg_sl_distance    : 31.0171
median_tp_distance : 31.6098
median_sl_distance : 31.6098
min_sl_hits        : 0
min_tp_hits        : 0
```

Best non-ATR range-enhanced policy in top list:

```text
policy_key        : mode=range_capped|fallback=atr|use1d=0|min_tp=0.5|min_sl=15|max_tp_atr=2|max_sl_atr=1.25|min4h=0|min1d=0|same=stop_first
rank              : 16
trades            : 124
BUY / SELL        : 77 / 47
wins / losses     : 66 / 58
final_balance     : 106.7674592914
return_percent    : +6.7674592914%
profit_factor     : 1.1439634226
max_drawdown_cash : 9.7927443251
BUY PnL           : -5.2818947734
SELL PnL          : +12.0493540648
positive_months   : 1
negative_months   : 1
pass_gate         : 1
```

Interpretation:

```text
- The Phase148 prediction/archive replay path is healthy because ATR-control exactly reproduces the earlier positive validation ATR result.
- Current range-model TP/SL does not add edge on validation; the best overall policy is pure ATR, not range.
- A range_capped+ATR-fallback policy with min_sl=15 is less catastrophic than raw range, but it is still worse than ATR and still depends on SELL while BUY is negative.
- Since ATR-control is the validation-selected best policy and that same ATR policy already failed test, the candidate fails validation→test confirmation.
```

Existing test confirmation for the same ATR policy:

```text
ATR test for rebuilt raw Option B 24k:
  final_balance : 90.7052413035
  return        : -9.2947586965%
  PF            : 0.8270058072
  maxDD         : 10.7624722054
  BUY PnL       : -5.3900375011
  SELL PnL      : -3.9047211954
```

Decision:

```text
Reject the rebuilt raw Option B 24k candidate.
Reject current range-model TP/SL as an improvement over ATR.
Do not run paper/live/Phase134.
Do not proceed to signal-filtering on the failed range archive as if it were a viable base.
```

Allowed diagnostic if the owner wants to continue investigating range:

```text
Confirm the best non-ATR validation policy on test exactly once:
mode=range_capped, fallback=atr, use1d=0, min_tp=0.5, min_sl=15, max_tp_atr=2, max_sl_atr=1.25, same=stop_first.
This is diagnostic only because it was rank 16, not the best validation policy.
```

Recommended strategic next phase:

```text
Phase151A — Pivot sequence walk-forward / seed-repeatability validation
```

Rationale:

```text
The model shows validation-only edge and test failure. The next proof must be walk-forward/repeated-seed validation, not more test-aware tuning.
```

## Phase150A best non-ATR test confirmation failed — 2026-09-21

The owner ran the optional diagnostic test confirmation for the best non-ATR validation policy from Phase150A.

Policy:

```text
range_bracket_mode : range_capped
range_fallback     : atr
use_1d_tp_cap      : 0
min_tp_distance    : 0.5
min_sl_distance    : 15
max_tp_atr         : 2.0
max_sl_atr         : 1.25
same_bar_policy    : stop_first
```

Validation rank-16 result was:

```text
validation_final_balance : 106.7675
validation_PF            : 1.1440
validation_maxDD         : 9.7927
```

Test confirmation result:

```text
eval_split        : test
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
trades            : 157
BUY / SELL trades : 50 / 107
wins / losses     : 74 / 83
win_rate          : 47.1338%
final_balance     : 88.0744190317
return_percent    : -11.9255809683%
total_cash_pnl    : -11.9255809683
profit_factor     : 0.8215049757
max_drawdown_cash : 15.8457758848
BUY PnL           : -5.7357534232
SELL PnL          : -6.1898275451
monthly           : 2026-07 -8.6762935082, 2026-08 -3.2492874601
positive_months   : 0
negative_months   : 2
```

Comparison to ATR test for rebuilt raw Option B:

```text
ATR test:
  final_balance : 90.7052
  PF            : 0.8270
  maxDD         : 10.7625

Best non-ATR test:
  final_balance : 88.0744
  PF            : 0.8215
  maxDD         : 15.8458
```

Interpretation:

```text
The best non-ATR validation policy failed test and was slightly worse than ATR test.
This closes the current range-rescue attempt for the rebuilt Option B candidate.
```

Decision:

```text
Reject current range_capped + fallback=atr policy.
Range TP/SL is not a rescue path for this candidate.
No Phase134. No paper shadow. No live trading.
```
