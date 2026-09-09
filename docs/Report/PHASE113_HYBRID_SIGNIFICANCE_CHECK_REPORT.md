# Phase 113 Report — Hybrid-head significance/random baseline

Date: 2026-09-09

## Context

Phase 125 produced and saved the current practical hybrid-head/range-aware threshold:

```text
buy_threshold  = 0.80
sell_threshold = 0.65
min_margin     = 0.05
trades         = 325
buy/sell       = 160 / 165
win_rate       = 51.6923%
label_precision= 65.8462%
total_pnl      = +291.154987683185
profit_factor  = 1.2471739846573604
max_drawdown   = 347.044035279524
```

Because many model/threshold paths were tested, this result must be checked against random before live/paper integration.

## Implemented files

```text
scripts/backtest_significance_check.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_significance_check.py
tests/unit/presentation/test_architecture_knobs_gui.py
docs/Phases/Phase113.md
docs/Phases/Phase125.md
docs/Phases/README_PHASE100_115.md
docs/CURRENT_STATE.md
docs/WORKLOG.md
```

## Method

The script reloads the hybrid head and applies the selected Phase 125 thresholds. It then builds random BUY/SELL pools from the same evaluation slice. A random trade candidate is included only if it passes the same range availability/room filters and can execute through the same TP/SL bracket construction as the model.

Random trials match:

```text
same eval slice
same spread/slippage/same-bar policy
same max-hold bars
same range filters
same TP/SL construction
same BUY count
same SELL count
no duplicate entry bar within a trial
```

Monte Carlo p-value:

```text
p_value = (1 + count(random_total_pnl >= observed_total_pnl)) / (trials + 1)
```

White Reality-style check:

```text
For each trial:
  sample random performance for every valid Phase 125 candidate row
  take max(random_total_pnl)
Compare that max distribution with observed best total_pnl.
```

This is a practical max-test over the actual Phase 125 grid; it is not a full academic White Reality Check implementation.

## User command

```powershell
python -u scripts/backtest_significance_check.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --trials 1000 `
  --seed 42 `
  --white-check 1 `
  --candidate-rows-path run_logs/hybrid_head_backtest/latest.json `
  --storage-root datasets
```

## Output files

```text
run_logs/significance_checks/latest.json
run_logs/significance_checks/latest.csv
```

## Interpretation rule

```text
If random_baseline.p_value <= 0.05:
  model beats simple same-count random baseline.

If white_reality_style.p_value <= 0.10, preferably <= 0.05:
  the result is more robust to threshold-grid data-snooping.

If either p-value is high:
  Phase 125 remains exploratory and should not go live.
```

## User run result

The user ran the command on the saved Phase 125 threshold. Result:

```text
observed_total_pnl       : +291.154987683185
observed_profit_factor   : 1.2471739846573604
observed_trades          : 325
observed_buy_sell        : 160 / 165
observed_win_rate        : 51.6923%
observed_label_precision : 65.8462%
random_mean              : -944.2369557544658
random_p95               : -665.0864972670641
random_p99               : -529.5757005996354
random_max               : -317.02241025066814
random_p_value           : 0.000999000999000999
white_candidate_count    : 23
white_p95                : -193.67326141904985
white_p99                : -128.05536537052174
white_max                : -28.658925889975762
white_p_value            : 0.000999000999000999
```

Interpretation:

```text
PASS: observed PnL beats every random trial and every White-style max random trial.
The p-value is the minimum observable with 1000 trials: 1 / 1001 = 0.000999.
```

Next allowed engineering step:

```text
Phase116 hybrid range-aware integration, followed by Phase115 live decision audit/paper validation.
```
