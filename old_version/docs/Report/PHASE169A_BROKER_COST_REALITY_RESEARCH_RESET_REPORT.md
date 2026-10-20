# PHASE169A — Broker Cost Reality + Research Lane Reset Audit Report

## Summary

Phase169A has been implemented to reset the current pivot research lane after Phase168A rejected the 1H locked-candidate/filter route.

The phase loads recent phase logs, records route decisions, audits spread/ATR economics, and optionally summarizes real broker spread samples.

No model is trained. No paper/live/production approval is granted.

## Implemented files

```text
scripts/audit_broker_cost_reality_research_reset.py
tests/unit/ai/test_broker_cost_reality_research_reset.py
```

GUI integration:

```text
CommandKind.AUDIT_BROKER_COST_REALITY_RESEARCH_RESET
GUI label: Audit broker cost reality / research reset
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Inputs

Default phase logs read:

```text
run_logs\pivot_bottom_buy_execution_gap\latest.json
run_logs\pivot_1h_entry_feasibility\latest.json
run_logs\pivot_1h_spread_bracket_sensitivity\latest.json
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest.json
run_logs\pivot_1h_locked_candidate_walk_forward\latest.json
run_logs\pivot_1h_locked_candidate_regime_failures\latest.json
run_logs\pivot_1h_predeclared_filter_confirmation\latest.json
```

Default OHLC paths:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
datasets\processed\XAUUSD\1H\v1.parquet
```

Default cost grids:

```text
fixed_spreads = 0.2,0.5,1.0,1.5,2.0
pct_spreads   = 0.01,0.02,0.03,0.06
max_median_spread_atr = 0.12
```

## Outputs

```text
run_logs\research_lane_reset_cost_audit\latest.json
run_logs\research_lane_reset_cost_audit\latest.html
run_logs\research_lane_reset_cost_audit\latest_route_decisions.csv
run_logs\research_lane_reset_cost_audit\latest_cost_assumptions.csv
run_logs\research_lane_reset_cost_audit\latest_dataset_health.csv
run_logs\research_lane_reset_cost_audit\latest_phase_sources.csv
run_logs\research_lane_reset_cost_audit\latest_spread_samples.csv
```

## Recommended command

Prefer the Dashboard command:

```text
Audit broker cost reality / research reset
```

Equivalent PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_broker_cost_reality_research_reset.py `
  --symbol XAUUSD `
  --timeframes 5M,1H `
  --m5-flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --h1-flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --fixed-spreads 0.2,0.5,1.0,1.5,2.0 `
  --pct-spreads 0.01,0.02,0.03,0.06 `
  --max-median-spread-atr 0.12 `
  --run-logs-root run_logs `
  --storage-root datasets `
  --output-dir run_logs\research_lane_reset_cost_audit `
  --report-title "Phase169A broker cost reality and research lane reset audit"
```

Optional broker spread sample:

```powershell
  --spread-sample-path path\to\alpari_xauusd_spread_sample.csv
```

## Expected interpretation

After Phase168A, the current expected route decision is:

```text
STOP_CURRENT_PIVOT_LOCKED_ROUTES
```

The expected blocked actions remain:

```text
training on rejected target
paper shadow
live trading
Phase134
```

## Verification

```text
python -m py_compile scripts/audit_broker_cost_reality_research_reset.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_broker_cost_reality_research_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_broker_cost_reality_research_reset.py tests/unit/ai/test_pivot_1h_filter_confirmation.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase169A research reset/cost audit only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase169A.

```text
route_decision             : INSUFFICIENT_ROUTE_EVIDENCE
broker_cost_reality_status : BROKER_SPREAD_SAMPLE_MISSING_OR_UNVERIFIED
recommended_next_phase     : Restore missing phase logs or run confirmation diagnostics
```

Why route_decision was insufficient:

```text
All expected Phase162A–Phase168A run_logs were missing on disk.
The script therefore could not automatically reconstruct route decisions.
```

Cost audit was still useful:

```text
5M dataset: PASS
1H dataset: PASS
1H fixed 0.2 and 0.5 are feasible by median spread/ATR gate.
1H fixed 1.0+ and percent 0.06 are not feasible.
No real broker spread sample was provided.
```

Detailed result:

```text
docs/Report/PHASE169A_BROKER_COST_REALITY_RESEARCH_RESET_RESULT.md
```
