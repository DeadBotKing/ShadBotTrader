# Phase160A — Pivot Candidate Side-Mapping / Counterfactual Direction Audit

## Status

```text
IMPLEMENTED — research/diagnostic only
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase159A tightened pivot candidate geometry enough to reduce candidate rate to about 3%, but expectancy remained negative under the existing reversal mapping.

Selected Phase159A policy:

```text
B2|rw=48|zone=0.05|top=0.85|bottom=0.15|exclude_both=1|minw=1|maxw=0
validation_mean_r = -0.00505
test_mean_r       = -0.02723
best side         = BUY in both validation and test
```

Phase160A tests whether the issue is side mapping / entry timing rather than the candidate geometry itself.

## Implemented executable

```text
scripts/audit_pivot_candidate_side_mapping.py
```

## GUI command

```text
Audit pivot candidate side mapping
```

## Inputs

Default Phase159 grid:

```text
run_logs\pivot_candidate_geometry_tightening\latest_grid.csv
```

If the grid file is absent, the script falls back to:

```text
B4:24:1.0:0.5
B2:24:1.0:0.75
```

with a Phase159-like geometry.

## Side mappings

Default grid:

```text
reversal     : top→SELL, bottom→BUY
breakout     : top→BUY,  bottom→SELL
top_sell     : top→SELL only
bottom_buy   : bottom→BUY only
top_buy      : top→BUY only
bottom_sell  : bottom→SELL only
all_buy      : all zone events BUY
all_sell     : all zone events SELL
```

Entry delays:

```text
0,1,2,3 bars
```

## Outputs

```text
run_logs\pivot_candidate_side_mapping\latest.json
run_logs\pivot_candidate_side_mapping\latest.html
run_logs\pivot_candidate_side_mapping\latest_grid.csv
```

## Recommended PowerShell command

```powershell
python -u scripts\audit_pivot_candidate_side_mapping.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --geometry-grid-path run_logs\pivot_candidate_geometry_tightening\latest_grid.csv `
  --fallback-targets "B4:24:1.0:0.5;B2:24:1.0:0.75" `
  --max-geometry-policies 30 `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --side-mappings reversal,breakout,top_sell,bottom_buy,top_buy,bottom_sell,all_buy,all_sell `
  --entry-delays 0,1,2,3 `
  --same-bar-policy stop_first `
  --timeout-score-mode zero `
  --zone-logic and `
  --min-validation-events 30 `
  --min-test-events 30 `
  --max-validation-event-rate 0.35 `
  --max-test-event-rate 0.35 `
  --min-validation-mean-r 0 `
  --min-test-mean-r 0 `
  --score-metric mean_r `
  --storage-root datasets `
  --output-dir run_logs\pivot_candidate_side_mapping
```

## Gate logic

Validation pass:

```text
validation_events >= min_validation_events
validation_event_rate <= max_validation_event_rate
validation_mean_r >= min_validation_mean_r
```

Test pass:

```text
test_events >= min_test_events
test_event_rate <= max_test_event_rate
test_mean_r >= min_test_mean_r
```

Transfer pass:

```text
validation pass
test pass
no validation-to-test mean-R sign flip
```

This phase is still diagnostic. A pass would justify a later candidate-model phase, not production.

## Execution result

The owner ran Phase160A.

Top-level result:

```text
geometry_policies_loaded      : 2
evaluated_rows                : 64
validation_pass_rows          : 14
transfer_pass_rows            : 3
selected_side_mapping         : bottom_buy
selected_entry_delay_bars     : 0
selected_validation_mean_r    : +0.0277777780
selected_test_mean_r          : +0.0773809552
selected_validation_PF        : 1.2
selected_test_PF              : 5.3333
selected_transfer_pass_gate   : 1
```

Selected policy:

```text
target_id              : B2
side_mapping           : bottom_buy
entry_delay_bars       : 0
recent_window_bars     : 48
pivot_zone_atr         : 0.05
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
```

Decision:

```text
This is the first positive transfer diagnostic in the recent pivot route.
It is still not production proof because it is event scoring, not full chronological trading replay.
```

Recommended next phase:

```text
Phase161A — Pivot Bottom-Buy Candidate Chronological Replay
```

## Verification

```text
python -m py_compile scripts/audit_pivot_candidate_side_mapping.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_candidate_side_mapping.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_candidate_side_mapping.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 53 passed
```
