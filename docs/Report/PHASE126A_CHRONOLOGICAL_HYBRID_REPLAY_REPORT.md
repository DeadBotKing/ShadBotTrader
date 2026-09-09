# Phase126A Report — Chronological Hybrid Single-Position Replay

Date: 2026-09-09

## Context

The streamed full-history independent-trade diagnostic failed:

```text
rows          : 52832
trades        : 13757
total_pnl     : -43309.811277104236
profit_factor : 0.6215092452818565
coverage      : 26.0391%
```

That test treated every signal row as an independent trade. A real account cannot open a new trade on every signal while the previous bracket is still active. Phase126A implements a more realistic chronological replay.

## Implemented path

```text
stream/matrix hybrid rows
→ hybrid head probabilities
→ saved Phase125 thresholds
→ range_1d/range_4h filters
→ TP/SL/timeout simulation
→ one open position at a time
→ HTML replay + JSON + CSV
```

## Files

```text
scripts/replay_hybrid_chronological_backtest.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_hybrid_chronological_replay.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase126.md
```

## Rule

```text
for each signal row chronologically:
  if source_index <= open_until_index:
      skipped_while_open += 1
      continue

  evaluate hybrid threshold gate
  evaluate 1D/4H range filters
  simulate trade over future candles up to max_hold_bars
  append trade
  open_until_index = trade.exit_index
```

## Outputs

```text
run_logs/hybrid_chronological_backtest/latest.html
run_logs/hybrid_chronological_backtest/latest.json
run_logs/hybrid_chronological_backtest/latest.csv
```

The JSON includes:

```text
summary.trades
summary.total_pnl
summary.profit_factor
summary.max_drawdown
chronological.skipped_while_open
account.final_balance
account.would_breach_zero
monthly
```

## Recommended command

```powershell
python -u scripts/replay_hybrid_chronological_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 500 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Next decision

If chronological replay still fails across full history, do not proceed to live/paper. Build Phase126B walk-forward/out-of-time validation:

```text
train on past
calibrate on past validation
test on next unseen block/month
```

Do not train on the full dataset and backtest on the same full dataset; that is in-sample leakage.
