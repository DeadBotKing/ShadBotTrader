# Phase185A — Range Model Reliability / Calibration / Decision-Utility Audit

## Status

```text
COMPLETED — owner run recorded
Result: reliable_timeframes=0/2, range is not a TP/SL or signal engine
Production — BLOCKED
```

Phase185A audits the current 4H and 1D range models before they are used as TP/SL engines, signal engines, or context features.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Purpose

Previous range-aware replay showed:

```text
ATR control won.
Range-based TP/SL did not add stable edge.
```

Phase185A answers the more basic reliability questions:

```text
1. Are 4H/1D range forecasts coherent?
2. How large are forecast errors in ATR units?
3. Are forecasts calibrated by predicted range bins?
4. Do predicted upside/downside rooms rank realized MFE/MAE?
5. Is range useful as a decision/filter proxy versus baseline?
6. Is range only a context feature, or not useful at all?
```

## Implemented command

GUI command:

```text
Audit range model reliability
```

Command kind:

```text
CommandKind.AUDIT_RANGE_MODEL_RELIABILITY
```

Script:

```text
scripts/audit_range_model_reliability.py
```

## Default model inputs

```text
range_4h_model_id : gold_range_4h
range_1d_model_id : gold_range_1d
version           : 0 means latest
source_mode       : models
```

The script also supports precomputed prediction files with:

```text
--source-mode predictions
--predictions-path <csv/parquet>
```

## Main outputs

```text
run_logs/range_model_reliability/latest.json
run_logs/range_model_reliability/latest.html
run_logs/range_model_reliability/latest_forecast_errors.csv
run_logs/range_model_reliability/latest_summary.csv
run_logs/range_model_reliability/latest_calibration_bins.csv
run_logs/range_model_reliability/latest_regime_breakdown.csv
run_logs/range_model_reliability/latest_decision_utility.csv
run_logs/range_model_reliability/latest_decision_matrix.csv
```

## Key metrics

Forecast errors are measured in ATR units:

```text
predicted_up_atr   = (predicted_high - close) / ATR
predicted_down_atr = (close - predicted_low) / ATR

realized_up_atr    = (future_high - close) / ATR
realized_down_atr  = (close - future_low) / ATR

high_error_atr     = predicted_up_atr - realized_up_atr
low_error_atr      = predicted_down_atr - realized_down_atr
```

Coherence:

```text
predicted_high >= close
predicted_low  <= close
predicted_high >= predicted_low
```

Calibration:

```text
Bin predictions by predicted_up_atr / predicted_down_atr.
For each bin compare mean predicted room vs mean realized room and hit rates.
```

Ranking:

```text
Spearman(predicted_up_atr, realized_up_atr)
Spearman(predicted_down_atr, realized_down_atr)
Spearman(predicted_width_atr, realized_width_atr)
```

Decision utility proxy:

```text
range_direction_score = predicted_up_atr - predicted_down_atr
BUY  if score >= decision_edge_atr
SELL if score <= -decision_edge_atr
```

Then checks whether selected direction has a simple favorable-vs-adverse quality edge.

## Gates

```text
coherence_gate
error_gate
ranking_gate
calibration_gate
decision_utility_gate
range_reliability_gate
```

A range model is not considered reliable unless all gates pass.

## Recommended GUI run

```text
AI → Audit range model reliability
```

Default fields:

```text
Symbol       : XAUUSD
Timeframes   : 4H,1D
Source mode  : models
4H model     : gold_range_4h
1D model     : gold_range_1d
Output dir   : run_logs/range_model_reliability
```

## CLI equivalent

```powershell
python -u scripts\audit_range_model_reliability.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --storage-root datasets `
  --output-dir run_logs\range_model_reliability
```

## Verification in sandbox

```text
python -m py_compile scripts/audit_range_model_reliability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_range_model_reliability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_range_model_reliability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — range reliability audit only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Performance hotfix — 2026-10-05

The first owner run with `--source-mode models` did not finish after many hours because the initial implementation called the range provider one row at a time through a path that re-created the predictor per forecast and did not print progress.

Fixed:

```text
scripts/audit_range_model_reliability.py
```

Changes:

```text
- loads each range model once per timeframe
- batches inference with --batch-size
- prints progress with --progress-every
- keeps full audit semantics unchanged
```

New operational fields:

```text
--batch-size 256
--progress-every 2000
```

Recommended retry command:

```powershell
python -u scripts\audit_range_model_reliability.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --batch-size 256 `
  --progress-every 2000 `
  --storage-root datasets `
  --output-dir run_logs\range_model_reliability
```

For a faster smoke audit before the full run:

```powershell
python -u scripts\audit_range_model_reliability.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --max-rows 3000 `
  --sample-stride 2 `
  --batch-size 256 `
  --progress-every 500 `
  --storage-root datasets `
  --output-dir run_logs\range_model_reliability_smoke
```

## Owner run result — 2026-10-06

Owner ran Phase185A on the current 4H and 1D range models.

Top-level result:

```text
evaluated_timeframes               : 2
reliable_timeframes                : 0
selected_timeframe                 : 4H
selected_reliability_gate          : 0
range_model_reliability_ready_gate : 0
no_training_gate                   : 1
no_paper_live_gate                 : 1
```

4H range result:

```text
model_id                  : gold_range_4h v3
horizon                   : 1
coherent_rate             : 1.0
median_abs_high_error_atr : 0.2196
median_abs_low_error_atr  : 0.2222
up_spearman               : 0.2740
down_spearman             : 0.3122
width_spearman            : 0.5897
calibration monotonicity  : 1.0 / 1.0
decision_proxy_trades     : 0
reliability_gate          : 0
primary_failure           : decision_utility_gate_failed
```

1D range result:

```text
model_id                  : gold_range_1d v2
horizon                   : 1
coherent_rate             : 1.0
median_abs_high_error_atr : 0.2269
median_abs_low_error_atr  : 0.2358
up_spearman               : 0.0008
down_spearman             : 0.0185
width_spearman            : 0.0186
decision_proxy_trades     : 0
reliability_gate          : 0
primary_failure           : ranking_gate_failed
```

Decision:

```text
RANGE_AS_TP_SL_ENGINE : BLOCKED
RANGE_AS_CONTEXT_FEATURE : DIAGNOSTIC_ONLY
PAPER_OR_LIVE : BLOCKED
```

Result report:

```text
docs/Report/PHASE185A_RANGE_MODEL_RELIABILITY_RESULT.md
```
