# Phase140A Report — Candidate Direction / Counterfactual Entry Audit

Date: 2026-09-16

## Goal

After Phase139A failed on global and side-specific TP/SL bracket recalibration, Phase140A audits whether the current hybrid candidate stream is wrong because of direction, timing, or no-edge candidate generation.

This phase is diagnostic only:

```text
No model training.
No production approval.
No paper shadow.
No live trading.
```

## Implemented files

```text
scripts/audit_candidate_direction_entry.py
tests/unit/ai/test_candidate_direction_entry_audit.py
```

GUI:

```text
Audit candidate direction/entry
```

GUI integration files updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

## Audit dimensions

```text
side_mode:
  original = execute candidate side as stored
  flipped  = BUY candidate executed as SELL, SELL candidate executed as BUY

entry_delay_bars:
  0, 1, 2, 3 by default

execution_mode:
  independent   = candidate-by-candidate diagnostic, no one-position overlap filtering
  chronological = one-position-at-a-time replay, strategy-style overlap filtering
```

The flipped-side replay mirrors the stored TP/SL distances around the delayed entry price. This keeps the risk geometry comparable while isolating side direction and entry timing.

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
5M candles from datasets
```

## Outputs

```text
run_logs\candidate_direction_entry_audit\latest.json
run_logs\candidate_direction_entry_audit\latest.html
run_logs\candidate_direction_entry_audit\latest.csv
run_logs\candidate_direction_entry_audit\latest_groups.csv
run_logs\candidate_direction_entry_audit\best_chronological_trades.csv
```

## First operator command

```powershell
python -u scripts/audit_candidate_direction_entry.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --entry-delays 0,1,2,3 `
  --side-modes original,flipped `
  --execution-modes independent,chronological `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

## What to inspect in `latest.json`

Top-level report:

```text
report.best_independent_scenario
report.best_chronological_scenario
report.original_delay0_independent_pnl
report.flipped_delay0_independent_pnl
report.original_delay0_chronological_pnl
report.flipped_delay0_chronological_pnl
report.diagnostic_findings
```

Scenario table:

```text
scenarios[*].execution_mode
scenarios[*].side_mode
scenarios[*].entry_delay_bars
scenarios[*].trades
scenarios[*].total_pnl
scenarios[*].profit_factor
scenarios[*].max_drawdown
```

Group table:

```text
group_rows where section = original_side
group_rows where section = month_original_side
group_rows where section = original_side_hour
```

## Interpretation gates

```text
If flipped side improves materially:
  candidate direction may be contrarian/inverted.

If entry delay improves materially:
  entry timing may be too early.

If neither flip nor delay helps:
  candidate generation itself likely has no stable edge under the current definition.
```

## Acceptance of implementation

Implementation acceptance means:

```text
script exists
GUI command exists
unit tests exist
HTML/JSON/CSV output paths are defined
owner map/current state/worklog are updated
```

It does **not** mean the trading strategy is accepted.

## Current status

```text
Phase140A implementation is ready for operator execution.
Awaiting real XAUUSD latest.json result.
Production remains blocked.
```

## Implementation verification

```text
python -m ruff check scripts/audit_candidate_direction_entry.py tests/unit/ai/test_candidate_direction_entry_audit.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/audit_candidate_direction_entry.py tests/unit/ai/test_candidate_direction_entry_audit.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_candidate_direction_entry_audit.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1867 tests collected
```

Known repository-wide debt remains unchanged:

```text
python -m ruff check .  → 219 pre-existing errors
python -m black --check . → 21 pre-existing files would be reformatted
python -m mypy src → 28 pre-existing errors in 10 files
```

## Operator result — full audit completed — 2026-09-16

Input file reviewed:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

Configuration:

```text
evaluated_rows  : 52,832
candidate_rows  : 13,757
side_modes      : original,flipped
entry_delays    : 0,1,2,3
execution_modes : independent,chronological
```

### Aggregate result

```text
best_independent_scenario        : independent:flipped:delay=0
best_independent_total_pnl       : -37,742.8296
best_independent_profit_factor   : 0.6561

best_chronological_scenario      : chronological:original:delay=3
best_chronological_total_pnl     : -3,123.7836
best_chronological_profit_factor : 0.6512
```

Baseline comparison:

```text
independent original delay=0     : -43,309.8113  PF=0.6215
independent flipped delay=0      : -37,742.8296  PF=0.6561
improvement                      : +5,566.9816, still negative

chronological original delay=0   : -4,590.7972   PF=0.5787
chronological flipped delay=0    : -4,113.8428   PF=0.6542
improvement                      : +476.9544, still negative

chronological original delay=3   : -3,123.7836   PF=0.6512
improvement vs original delay=0  : +1,467.0136, still negative
```

### Direction diagnosis

BUY side:

```text
BUY original      : -39,003.7074  PF=0.5106
BUY flipped→SELL  : -15,831.0041  PF=0.7545
```

Interpretation:

```text
BUY candidates have a strong contrarian/inversion symptom, but flipping BUY is still not profitable. So the project should not simply invert BUY and deploy it.
```

SELL side:

```text
SELL original     : -4,306.1039   PF=0.8760
SELL flipped→BUY  : -21,911.8255  PF=0.5157
```

Interpretation:

```text
SELL direction is not inverted. Flipping SELL is destructive.
```

### Entry timing diagnosis

Chronological original side by delay:

```text
delay=0  pnl=-4590.7972  PF=0.5787  trades=1693
delay=1  pnl=-4245.3885  PF=0.5962  trades=1523
delay=2  pnl=-3921.5867  PF=0.5985  trades=1393
delay=3  pnl=-3123.7836  PF=0.6512  trades=1305
```

Interpretation:

```text
Entry delay reduces damage, especially delay=3, which indicates the original entries are often too early. But delay alone does not create a tradeable strategy.
```

### Best chronological scenario side split

For `chronological:original:delay=3`:

```text
BUY→BUY    trades=842  pnl=-2765.11  PF=0.562  win=32.2%
SELL→SELL  trades=463  pnl=-358.67   PF=0.864  win=41.5%
```

Interpretation:

```text
Most remaining damage still comes from BUY. SELL is much less bad and has positive month pockets, but is still negative overall.
```

### Decision

```text
Phase140A result: FAIL as strategy, useful as diagnosis.
```

What was learned:

```text
Global flip is not the fix.
BUY has contrarian/inversion symptoms.
SELL must not be flipped.
Delay helps, but does not solve alpha.
The next diagnostic should test side-specific transforms and delays in one chronological policy grid.
```

Recommended next phase:

```text
Phase141A — Side-Transform / Delay Policy Grid
```

Candidate policy space:

```text
BUY action  : original, flipped_to_sell, skip
SELL action : original, flipped_to_buy, skip
BUY delay   : 0,1,2,3
SELL delay  : 0,1,2,3
execution   : chronological only for policy scoring, independent diagnostics optional
```

Expected purpose:

```text
Verify whether the best interpretable combination is something like:
BUY = skip or flip-to-SELL
SELL = original
BUY delay = 2/3
SELL delay = 2/3
```

Production remains blocked.
