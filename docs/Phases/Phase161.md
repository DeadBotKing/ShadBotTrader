# Phase161A — Pivot Bottom-Buy Candidate Chronological Replay

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

But Phase160A was only event scoring. Phase161A converts that selected rule into a realistic chronological replay with spread, TP/SL path, risk sizing and monthly split summaries.

## Implemented executable

```text
scripts/replay_pivot_bottom_buy_candidate.py
```

## GUI command

```text
Replay pivot bottom-buy candidate
```

## Selected rule

```text
target_id              : B2
side_mapping           : bottom_buy only
entry_delay_bars       : 0
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
TP                     : 1.0 ATR
SL                     : 0.75 ATR
```

## Replay assumptions

```text
spread_mode       : pct
spread_value      : 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
hold_bars         : 48
single-position chronological replay
```

## Outputs

```text
run_logs\pivot_bottom_buy_chronological_replay\latest.json
run_logs\pivot_bottom_buy_chronological_replay\latest.html
run_logs\pivot_bottom_buy_chronological_replay\latest_summary.csv
run_logs\pivot_bottom_buy_chronological_replay\latest_trades.csv
```

## Recommended PowerShell command

```powershell
python -u scripts\replay_pivot_bottom_buy_candidate.py `
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
  --entry-delay-bars 0 `
  --tp-atr 1.0 `
  --sl-atr 0.75 `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --validation-min-trades 20 `
  --validation-min-profit-factor 1.05 `
  --test-min-trades 20 `
  --test-min-profit-factor 1.05 `
  --storage-root datasets `
  --output-dir run_logs\pivot_bottom_buy_chronological_replay
```

## Pass/fail logic

Validation and test gates require:

```text
trades >= min trades
profit_factor >= min PF
final_balance >= 100
```

Transfer pass requires validation and test both pass.

## Execution result

The owner ran Phase161A.

Result:

```text
validation_pass_gate : 0
test_pass_gate       : 0
transfer_pass_gate   : 0
```

Validation:

```text
candidate_rows    : 54
trades            : 30
total_cash_pnl    : -3.3832
final_balance     : 96.6168
profit_factor     : 0.7156
max_drawdown_cash : 5.9745
```

Test:

```text
candidate_rows    : 42
trades            : 21
total_cash_pnl    : -2.2486
final_balance     : 97.7514
profit_factor     : 0.6853
max_drawdown_cash : 2.7327
```

Decision:

```text
Phase161A failed. The Phase160A bottom-buy event-scoring edge did not survive chronological spread/risk replay.
```

Recommended next diagnostic:

```text
Phase162A — Pivot Bottom-Buy Execution Gap / Entry Timing Audit
```

## Verification

```text
python -m py_compile scripts/replay_pivot_bottom_buy_candidate.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_bottom_buy_replay.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_bottom_buy_replay.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 53 passed
```
