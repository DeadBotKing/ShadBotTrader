# PHASE170A — Broker Spread Capture / Cost Data Pipeline Report

## Summary

Phase170A has been implemented to capture or import real broker spread samples for XAUUSD and convert them into cost evidence.

The immediate purpose is to remove uncertainty around whether future research should use fixed spread, percent spread, session-aware spread or another explicit cost model.

No model is trained. No paper/live/production approval is granted.

## Implemented files

```text
scripts/capture_broker_spread_cost_pipeline.py
tests/unit/ai/test_broker_spread_capture_pipeline.py
```

GUI integration:

```text
CommandKind.CAPTURE_BROKER_SPREAD_COST_PIPELINE
GUI label: Capture broker spread / cost pipeline
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Capture mode

```text
--source-mode mt5
```

The script connects to MetaTrader 5 and samples `symbol_info_tick` bid/ask. It does not send orders.

Default capture settings:

```text
duration_seconds = 600
interval_seconds = 5
min_samples      = 20
point            = 0.01
digits           = 2
```

## Import mode

```text
--source-mode csv
--sample-path path\to\spread_sample.csv
```

Supported spread sample formats:

```text
bid + ask
spread
spread_price
spread_value
```

Optional fields:

```text
timestamp/time/datetime
point
digits
last/price/close
```

## Outputs

```text
run_logs\broker_spread_capture\latest.json
run_logs\broker_spread_capture\latest.html
run_logs\broker_spread_capture\latest_spread_samples.csv
run_logs\broker_spread_capture\latest_session_summary.csv
run_logs\broker_spread_capture\latest_timeframe_cost.csv
```

## Key report fields

```text
samples
sample_status
broker_cost_reality_gate
spread_price_median
spread_price_p90
spread_price_p99
spread_points_median
spread_points_p90
spread_points_p99
summary_rows
timeframe_cost_rows
```

## Recommended command

Dashboard:

```text
Capture broker spread / cost pipeline
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\capture_broker_spread_cost_pipeline.py `
  --source-mode mt5 `
  --symbol XAUUSD `
  --broker-symbol XAUUSD_i `
  --duration-seconds 600 `
  --interval-seconds 5 `
  --max-samples 0 `
  --min-samples 20 `
  --point 0.01 `
  --digits 2 `
  --timeframes 5M,1H `
  --m5-flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --h1-flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --max-median-spread-atr 0.12 `
  --storage-root datasets `
  --output-dir run_logs\broker_spread_capture `
  --report-title "Phase170A broker spread capture / cost data pipeline"
```

## Verification

```text
python -m py_compile scripts/capture_broker_spread_cost_pipeline.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_broker_spread_capture_pipeline.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_broker_spread_capture_pipeline.py tests/unit/ai/test_broker_cost_reality_research_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase170A broker spread/cost data only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner captured broker spread samples from MT5 / Alpari `XAUUSD_i`.

```text
samples                  : 121
sample_status            : PASS
broker_cost_reality_gate : 1
spread_price_median      : 0.3900000000003274
spread_price_p90         : 0.4000000000005457
spread_price_p99         : 0.41000000000058207
spread_points_median     : 39.00000000003274
```

Cost/ATR:

```text
5M median spread/ATR : 0.009875382083243615
1H median spread/ATR : 0.08347347500389216
```

Important correction:

```text
One invalid epoch tick was captured at 1970-01-01 with spread=0.
The script was patched to ignore invalid MT5 epoch ticks in future captures.
```

Detailed result:

```text
docs/Report/PHASE170A_BROKER_SPREAD_CAPTURE_COST_PIPELINE_RESULT.md
```
