# Phase169A — Broker Cost Reality + Research Lane Reset Audit

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

The recent pivot research lane reached clear stop decisions:

```text
5M strict bottom-buy route:
  failed realistic replay and execution-gap diagnostics.

1H locked breakout route:
  passed static lockdown diagnostics,
  failed walk-forward anti-overfit,
  failed predeclared filter confirmation.
```

Phase169A resets the research lane and audits broker-cost reality assumptions before any future target/model work.

## Implemented executable

```text
scripts/audit_broker_cost_reality_research_reset.py
```

## GUI command

```text
Audit broker cost reality / research reset
```

## What it does

```text
1. Loads key phase run logs from run_logs:
   Phase162A through Phase168A.

2. Builds route decision rows:
   5M pivot bottom-buy
   1H locked breakout BRK_D1_FAST
   1H cost model

3. Audits OHLC/ATR health for selected timeframes:
   default: 5M,1H

4. Computes spread/ATR economics for fixed and percent spread assumptions:
   fixed spreads default: 0.2,0.5,1.0,1.5,2.0
   percent spreads default: 0.01,0.02,0.03,0.06

5. Optionally summarizes real broker spread samples if a spread sample file is provided.

6. Produces a reset recommendation for the next research direction.
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

## Recommended GUI action

Use the Dashboard command:

```text
Audit broker cost reality / research reset
```

## Equivalent PowerShell command

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

If you have an exported broker spread sample file, add:

```powershell
  --spread-sample-path path\to\alpari_xauusd_spread_sample.csv
```

Supported spread sample columns:

```text
spread
spread_value
or bid + ask
```

## Decision after owner run

Expected decision if Phase168A logs are present:

```text
STOP_CURRENT_PIVOT_LOCKED_ROUTES
```

Expected next step depends on spread sample availability:

```text
If no real spread sample exists:
  Phase170A — Broker Spread Capture / Cost Data Pipeline

If real spread sample exists and confirms costs:
  new target/candidate family design only, not patching rejected rules
```

## Verification

Sandbox targeted verification:

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

## Owner execution result

The owner ran Phase169A.

Top-level:

```text
route_decision             : INSUFFICIENT_ROUTE_EVIDENCE
broker_cost_reality_status : BROKER_SPREAD_SAMPLE_MISSING_OR_UNVERIFIED
recommended_next_phase     : Restore missing phase logs or run confirmation diagnostics
```

Important note:

```text
Phase169A did not find Phase162A–Phase168A run_logs on disk.
This is why automatic route decisions were marked UNKNOWN/INSUFFICIENT.
The previously pasted and documented phase results still remain the project record.
```

Dataset health:

```text
5M: PASS, rows=53197, no nonfinite/invalid OHLC/ATR errors
1H: PASS, rows=50000, no nonfinite/invalid OHLC/ATR errors
```

Cost reality result:

```text
1H fixed 0.2 median spread/ATR = 0.0428 -> feasible
1H fixed 0.5 median spread/ATR = 0.1070 -> feasible
1H fixed 1.0 median spread/ATR = 0.2140 -> not feasible
1H pct 0.06 median spread/ATR  = 0.2478 -> not feasible
```

Broker spread sample:

```text
NOT_PROVIDED
```

Decision:

```text
Phase169A completed the cost audit but could not auto-confirm route decisions due to missing run_logs.
Based on documented Phase162A–Phase168A results, current 5M/1H locked pivot routes remain rejected.
```

Recommended next action:

```text
Phase170A — Broker Spread Capture / Cost Data Pipeline
```

Purpose:

```text
Capture real Alpari XAUUSD bid/ask/spread samples and remove uncertainty around fixed-vs-percent cost assumptions.
```
