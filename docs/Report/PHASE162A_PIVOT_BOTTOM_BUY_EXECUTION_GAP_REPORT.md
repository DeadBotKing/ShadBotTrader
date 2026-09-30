# PHASE162A — Pivot Bottom-Buy Execution Gap Audit Report

## Summary

Phase162A has been implemented as a research-only diagnostic after Phase161A rejected the strict bottom-buy pivot rule in chronological replay.

The script explains where Phase160A event scoring and Phase161A replay differ:

```text
Phase160A: independent first-hit event score from candidate/close-style assumptions
Phase161A: next-bar open entry, spread, trade_path, risk sizing, single-position chronological replay
```

Phase162A does not train a model and does not approve production.

## Implemented files

```text
scripts/audit_pivot_bottom_buy_execution_gap.py
tests/unit/ai/test_pivot_bottom_buy_execution_gap.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_BOTTOM_BUY_EXECUTION_GAP
GUI label: Audit pivot bottom-buy execution gap
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## What the audit measures

```text
candidate close vs next-open gap:
  raw_close_to_next_open_gap_atr
  adjusted_entry_gap_atr
  adverse_adjusted_gap_rate

spread/no-spread sensitivity:
  spread_values default 0,0.06

independent event scoring:
  event_mean_atr
  event_profit_factor
  event_take_profits / event_stop_losses / event_timeouts
  event_ambiguous

independent replay path:
  independent_replay_mean_atr
  independent_replay_profit_factor
  independent_replay_take_profits / stop_losses / timeouts

path difference:
  event_to_independent_mean_delta_atr
  path_disagreement_rate
  event_tp_to_replay_sl
  event_sl_to_replay_tp
  event_timeout_to_replay_tp
  event_timeout_to_replay_sl

chronological replay:
  chronological_trades
  chronological_total_cash_pnl
  chronological_profit_factor
  chronological_final_balance
  max_drawdown

skipped event attribution:
  skipped_while_open
  skipped_winners
  skipped_losers
  skipped_timeouts
  skipped_independent_sum_atr
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

## GUI command fields

Key defaults:

```text
target_id              : B2
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
entry_delays           : 0,1,2,3
same_bar_policies      : stop_first,tp_first
spread_mode            : pct
spread_values          : 0,0.06
tp_atr                 : 1.0
sl_atr                 : 0.75
event_lookahead_bars   : 24
hold_bars              : 48
max_samples            : 24000
```

## Recommended command

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

## Verification

```text
python -m py_compile scripts/audit_pivot_bottom_buy_execution_gap.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_bottom_buy_execution_gap.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_bottom_buy_execution_gap.py tests/unit/ai/test_pivot_bottom_buy_replay.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black were not run in this sandbox because the modules are unavailable here:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase162A execution-gap diagnostic only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran the audit on the full local XAUUSD 5M dataset.

```text
evaluated_configs       : 16
validation_pass_configs : 4
transfer_pass_configs   : 0
selected_config         : delay=0 / stop_first / spread=0.0
selected_validation_PF  : 1.203013055453164
selected_test_PF        : 0.9105459631947063
selected_transfer_gate  : 0
```

Key conclusion:

```text
Phase162A did not find a transferable execution fix.
The strict B2 bottom-buy rule remains rejected.
```

Detailed result document:

```text
docs/Report/PHASE162A_PIVOT_BOTTOM_BUY_EXECUTION_GAP_RESULT.md
```
