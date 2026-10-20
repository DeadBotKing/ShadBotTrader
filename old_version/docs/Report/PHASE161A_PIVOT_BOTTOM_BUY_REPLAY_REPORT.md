# PHASE161A — Pivot Bottom-Buy Chronological Replay Report

## Summary

Phase161A has been implemented to convert the Phase160A positive event-scoring diagnostic into a realistic chronological replay.

It does not approve production. It produces evidence about whether the selected bottom-buy rule survives spread, single-position execution, risk sizing, drawdown and monthly split reporting.

## Implemented files

```text
scripts/replay_pivot_bottom_buy_candidate.py
tests/unit/ai/test_pivot_bottom_buy_replay.py
```

GUI integration:

```text
CommandKind.REPLAY_PIVOT_BOTTOM_BUY_CANDIDATE
GUI label: Replay pivot bottom-buy candidate
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Replay rule

```text
target_id              : B2
side                   : BUY only
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
entry_delay_bars       : 0
TP                     : 1.0 ATR
SL                     : 0.75 ATR
```

## Outputs

```text
run_logs\pivot_bottom_buy_chronological_replay\latest.json
run_logs\pivot_bottom_buy_chronological_replay\latest.html
run_logs\pivot_bottom_buy_chronological_replay\latest_summary.csv
run_logs\pivot_bottom_buy_chronological_replay\latest_trades.csv
```

## Recommended command

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
  --tp-atr 1.0 `
  --sl-atr 0.75 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --storage-root datasets `
  --output-dir run_logs\pivot_bottom_buy_chronological_replay
```

## Verification

```text
python -m py_compile scripts/replay_pivot_bottom_buy_candidate.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_bottom_buy_replay.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_bottom_buy_replay.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 53 passed
```

Full ruff/black unavailable in sandbox:

```text
No module named ruff
No module named black
```

## Production status

```text
BLOCKED — chronological replay diagnostic only
No Phase134.
No paper shadow.
No live trading.
```
