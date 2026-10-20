# Phase136A Report — Tensor Failure / Regime Diagnostics

Date: 2026-09-14

## Goal

Build a diagnostic report that explains why the 3D tensor WaveNet path failed Phase133B/C walk-forward validation.

This phase does not train a model and does not approve paper/live trading.

## Implemented files

```text
scripts/analyze_tensor_failure_regimes.py
tests/unit/ai/test_tensor_failure_regimes.py
```

GUI:

```text
Analyze tensor failure regimes
```

## Inputs

```text
flat_path:
  datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet

walk_forward_json:
  run_logs\hybrid_tensor_walk_forward_validation\latest.json
```

## Diagnostics produced

```text
run_logs\tensor_failure_regimes\latest.json
run_logs\tensor_failure_regimes\latest.html
run_logs\tensor_failure_regimes\latest_regimes.csv
run_logs\tensor_failure_regimes\latest_transfer.csv
```

## Analysis scope

Candidate-regime summaries:

```text
month
side
month_side
hour
side_hour
outcome
specialist_conflict
candidate_valid_range
candidate_valid_bracket
candidate_confidence quantiles
candidate_reward_risk quantiles
candidate_tp_distance quantiles
candidate_sl_distance quantiles
side_4h_room quantiles
side_1d_room quantiles
range_4h_width quantiles
range_1d_width quantiles
booster_entropy quantiles
booster_action_margin quantiles
specialist_max_prob quantiles
target_score_r bins for analysis only
```

Transfer diagnostics:

```text
fold
validation_months
test_month
selected_mode
selected_meta_threshold
selected_score_threshold
validation_score
validation_profit_factor
validation_max_drawdown
validation_trades
no_trade_selected
base_total_pnl
tensor_total_pnl
tensor_profit_factor
tensor_trades
transfer_status
```

## First command

```powershell
python -u scripts/analyze_tensor_failure_regimes.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --walk-forward-json run_logs\hybrid_tensor_walk_forward_validation\latest.json `
  --candidate-only 1 `
  --min-group-rows 20 `
  --top-n 12 `
  --quantile-bins 5 `
  --storage-root datasets
```

## Acceptance of this phase

The phase is accepted when it produces the diagnostic files and identifies actionable failure/regime hypotheses. It is not a strategy pass.

Production/paper remains blocked until a future strategy passes walk-forward validation.

## Operator result — 2026-09-14

Top-level candidate distribution:

```text
candidate_rows : 13757
months         : 10
total_pnl      : -43309.811259036884
win_rate       : 41.2663%
profit_factor  : 0.6215092452270718
worst_month    : 2026-02
best_month     : 2026-07
```

Transfer diagnostics:

```text
transfer_rows          : 6
transfer_total_pnl     : -32.83297738432884
transfer_profit_factor : 0.7655299301860462
no_trade_months        : 3
```

Risk flags:

```text
1 fold had positive validation quality but negative test PnL.
3 folds were blocked by validation no-trade gates.
1 active trading fold still lost money after gates.
Side BUY is negative in candidate distribution: -39003.71 raw PnL.
Side SELL is negative in candidate distribution: -4306.10 raw PnL.
```

Key failure regimes:

```text
stop_loss: rows=7256, share=52.7441%, total_pnl=-106988.0392
BUY: rows=8583, win_rate=35.7917%, total_pnl=-39003.7073, PF=0.5106
2026-02: rows=1945, win_rate=25.1414%, total_pnl=-21573.3665, PF=0.3872
candidate_sl_distance high bin: total_pnl=-22248.0623
range_1d_width high bin: total_pnl=-19492.4818
range_4h_width mid/high bins: -18473.0694 and -16979.6279
high candidate_confidence bin: total_pnl=-14063.6031
```

Best diagnostic pockets:

```text
2026-04 / SELL: total_pnl=+2682.8371, PF=2.1863
2026-03 / SELL: total_pnl=+2308.4453, PF=1.8384
2026-07 / SELL: total_pnl=+1963.2321, PF=1.4834
2026-06 / SELL: total_pnl=+669.4895, PF=1.2756
2026-08 / SELL: total_pnl=+469.5280, PF=1.6627
SELL / hour=9: total_pnl=+901.0482, PF=1.8986
SELL / hour=8: total_pnl=+640.0451, PF=1.3392
```

Interpretation:

```text
The most actionable hypothesis is SELL-focused filtering. BUY candidates are the main damage source. However, these are candidate-distribution diagnostics and not chronological replay. The next phase should test SELL-only and live-safe regime filters through chronological replay/walk-forward.
```
