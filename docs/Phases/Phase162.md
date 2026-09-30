# Phase162A — Pivot Bottom-Buy Execution Gap / Entry Timing Audit

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

Phase160A found the first positive pivot transfer diagnostic:

```text
target_id          : B2
side_mapping       : bottom_buy
entry_delay_bars   : 0
validation_mean_r  : +0.0277778
test_mean_r        : +0.077381
transfer_pass_gate : 1
```

Phase161A then replayed the same strict bottom-buy rule chronologically and failed:

```text
validation PF : 0.7156
validation PnL: -3.3832
test PF       : 0.6853
test PnL      : -2.2486
transfer_pass : 0
```

Phase162A does not search a new model. It decomposes the execution gap between Phase160A event scoring and Phase161A replay.

## Implemented executable

```text
scripts/audit_pivot_bottom_buy_execution_gap.py
```

## GUI command

```text
Audit pivot bottom-buy execution gap
```

## Diagnostic scope

Phase162A measures:

```text
1. candidate close → next-open BUY entry gap
2. no-spread vs spread sensitivity
3. independent event scoring vs independent replay path
4. chronological one-position replay vs independent event counting
5. skipped_while_open winners/losses/timeouts
6. entry_delay grid: 0,1,2,3 by default
7. same_bar_policy grid: stop_first,tp_first
8. event-scoring TP/SL/timeout path vs replay TP/SL/timeout path
9. monthly train/validation/test breakdown
```

## Default audited policy

```text
target_id              : B2
side_mapping           : bottom_buy only
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
TP                     : 1.0 ATR
SL                     : 0.75 ATR
event_lookahead_bars   : 24
replay_hold_bars       : 48
spread_values          : 0,0.06
same_bar_policies      : stop_first,tp_first
entry_delays           : 0,1,2,3
```

## Outputs

```text
run_logs\pivot_bottom_buy_execution_gap\latest.json
run_logs\pivot_bottom_buy_execution_gap\latest.html
run_logs\pivot_bottom_buy_execution_gap\latest_grid.csv
run_logs\pivot_bottom_buy_execution_gap\latest_selection.csv
run_logs\pivot_bottom_buy_execution_gap\latest_monthly.csv
run_logs\pivot_bottom_buy_execution_gap\latest_events.csv
```

## Recommended PowerShell command

Prefer running from the Dashboard via:

```text
Audit pivot bottom-buy execution gap
```

Equivalent PowerShell command:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_pivot_bottom_buy_execution_gap.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --target-id B2 `
  --recent-window-bars 48 `
  --pivot-zone-atr 0.05 `
  --top-position-threshold 0.85 `
  --bottom-position-threshold 0.15 `
  --exclude-both-zones 1 `
  --min-range-width-atr 1.0 `
  --max-range-width-atr 0 `
  --entry-delays 0,1,2,3 `
  --same-bar-policies stop_first,tp_first `
  --spread-mode pct `
  --spread-values 0,0.06 `
  --tp-atr 1.0 `
  --sl-atr 0.75 `
  --event-lookahead-bars 24 `
  --hold-bars 48 `
  --timeout-score-mode zero `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --validation-min-trades 20 `
  --validation-min-profit-factor 1.05 `
  --test-min-trades 20 `
  --test-min-profit-factor 1.05 `
  --score-metric chronological_pnl `
  --max-event-rows 20000 `
  --storage-root datasets `
  --output-dir run_logs\pivot_bottom_buy_execution_gap `
  --report-title "Phase162A pivot bottom-buy execution gap audit"
```

## Selection protocol

The script ranks execution configurations by validation-only diagnostics:

```text
transfer_pass_gate
validation_pass_gate
validation_score
validation_chronological_profit_factor
```

Test is confirmation-only. A positive test row without validation pass is not a production approval.

## Decision rule after owner run

If Phase162A shows no robust validation-selected replay configuration that confirms on test, the strict pivot bottom-buy route remains rejected and the pivot route should pause.

If Phase162A identifies a robust execution adjustment, the next step is still only another walk-forward/replay confirmation. No paper/live approval follows from Phase162A alone.

## Verification

Implemented and locally verified in sandbox:

```text
python -m py_compile scripts/audit_pivot_bottom_buy_execution_gap.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_bottom_buy_execution_gap.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_bottom_buy_execution_gap.py tests/unit/ai/test_pivot_bottom_buy_replay.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Owner execution result

The owner ran Phase162A on the full local dataset.

Top-level:

```text
evaluated_configs       : 16
validation_pass_configs : 4
transfer_pass_configs   : 0
selected_config         : delay=0, same_bar=stop_first, spread=0.0
selected_validation_PF  : 1.203013055453164
selected_validation_PnL : +1.9564356399935086
selected_test_PF        : 0.9105459631947063
selected_test_PnL       : -0.5422007496410663
selected_transfer_gate  : 0
```

Main diagnostic findings:

```text
1. No configuration transferred from validation to test.
2. The validation-selected no-spread row failed test confirmation.
3. The realistic spread=0.06 row reproduced Phase161A failure:
   validation PF=0.7156, test PF=0.6853.
4. Spread turns BUY entry gap adverse almost always:
   validation adverse adjusted gap rate ≈ 98.15%
   test adverse adjusted gap rate = 100.0%
5. Single-position replay skips many winners in test:
   selected no-spread test skipped winners/losses = 15/7
   skipped independent sum = +5.0221 ATR
   executed independent mean = -0.0184 ATR
6. same_bar_policy is not the issue because event_ambiguous=0 and stop_first/tp_first are identical.
```

Decision:

```text
Phase162A failed.
No execution timing/spread/same-bar adjustment rescued the B2 strict bottom-buy candidate.
Reject the current bottom-buy rule as a trading candidate.
```

Production status remains:

```text
BLOCKED — no Phase134, no paper shadow, no live trading
```
