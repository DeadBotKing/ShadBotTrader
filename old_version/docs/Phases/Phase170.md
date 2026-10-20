# Phase170A — Broker Spread Capture / Cost Data Pipeline

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

Phase169A showed that the current pivot research routes are rejected by documented evidence, but broker cost reality is still unverified:

```text
broker_cost_reality_status = BROKER_SPREAD_SAMPLE_MISSING_OR_UNVERIFIED
```

Phase170A captures or imports real broker spread data so future research does not rely on guessed spread units such as `0.06%` or `fixed 0.2`.

## Implemented executable

```text
scripts/capture_broker_spread_cost_pipeline.py
```

## GUI command

```text
Capture broker spread / cost pipeline
```

## Supported modes

### MT5 capture mode

```text
--source-mode mt5
```

This connects to an already running MetaTrader 5 terminal/session, selects the broker symbol and samples bid/ask ticks.

The script does not send orders.

Optional login support exists only via an environment variable:

```text
--mt5-login <login>
--mt5-server <server>
--mt5-password-env SHADBOT_MT5_PASSWORD_...
```

### CSV/parquet import mode

```text
--source-mode csv
--sample-path path\to\spread_sample.csv
```

Supported columns:

```text
timestamp/time/datetime
bid + ask
or spread / spread_price / spread_value
point
digits
```

## Outputs

```text
run_logs\broker_spread_capture\latest.json
run_logs\broker_spread_capture\latest.html
run_logs\broker_spread_capture\latest_spread_samples.csv
run_logs\broker_spread_capture\latest_session_summary.csv
run_logs\broker_spread_capture\latest_timeframe_cost.csv
```

## What it reports

```text
sample count
median / p90 / p99 spread in price units
median / p90 / p99 spread in broker points
session summaries:
  asia
  london_morning
  london_ny_overlap
  ny_late
  rollover
weekday summaries
spread/ATR by timeframe
cost reality gate
```

## Recommended GUI action

Use the Dashboard command:

```text
Capture broker spread / cost pipeline
```

For a first real capture, recommended fields:

```text
source_mode      : mt5
symbol           : XAUUSD
broker_symbol    : XAUUSD_i   # if Alpari account maps XAUUSD this way
duration_seconds : 600
interval_seconds : 5
min_samples      : 20
```

## Equivalent PowerShell command — MT5 capture

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

If the active broker symbol is not `XAUUSD_i`, change `--broker-symbol` accordingly.

## Equivalent PowerShell command — CSV import

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\capture_broker_spread_cost_pipeline.py `
  --source-mode csv `
  --symbol XAUUSD `
  --broker-symbol XAUUSD_i `
  --sample-path path\to\alpari_xauusd_spread_sample.csv `
  --point 0.01 `
  --digits 2 `
  --timeframes 5M,1H `
  --m5-flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --h1-flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-median-spread-atr 0.12 `
  --storage-root datasets `
  --output-dir run_logs\broker_spread_capture
```

## Decision after owner run

If the captured median/p90 spread confirms fixed spread around `0.2`, future research can use that as a documented cost assumption.

If captured spread is closer to `0.5` or higher, the previous 1H locked-candidate result remains too fragile and should not be used for model training.

If spread is strongly session-dependent, future target/candidate design must be session-aware from the beginning.

## Verification

Sandbox targeted verification:

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

## Owner execution result

The owner ran Phase170A in MT5 mode against Alpari symbol `XAUUSD_i`.

Top-level:

```text
samples                  : 121
sample_status            : PASS
broker_cost_reality_gate : 1
spread_price_median      : 0.3900000000003274
spread_price_p90         : 0.4000000000005457
spread_price_p99         : 0.41000000000058207
spread_points_median     : 39.00000000003274
spread_points_p90        : 40.00000000005457
spread_points_p99        : 41.00000000005821
```

One invalid placeholder tick was present:

```text
timestamp : 1970-01-01T00:00:00+00:00
spread    : 0.0
```

A code patch was applied after this result so future MT5 captures ignore invalid epoch ticks.

Cost/ATR:

```text
5M median spread/ATR : 0.009875382083243615
1H median spread/ATR : 0.08347347500389216
```

Decision:

```text
Broker spread reality is now sampled.
Realistic spread is around fixed 0.39–0.41, not fixed 0.2.
Future research must use fixed spread around 0.4 or stress around 0.4/0.5.
Do not revive the rejected 1H locked candidate that only passed at fixed 0.2.
```
