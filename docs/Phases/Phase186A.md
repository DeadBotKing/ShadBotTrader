# Phase186A — Range Candle-by-Candle Forecast Accuracy Audit

## Status

```text
COMPLETED — owner run recorded
Result: current models emit step 1 only; steps 2..5 were not emitted
Production — BLOCKED
```

Owner result:

```text
docs/Report/PHASE186A_RANGE_MULTISTEP_ACCURACY_RESULT.md
```

Phase186A measures whether the current 4H and 1D range models can forecast future candles one by one.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
No architecture redesign.
```

## Why this phase exists

Phase185A measured range reliability, calibration, ranking, and a decision-utility proxy. It did not answer the candle-by-candle question.

```text
Phase185A scores the horizon envelope:
  realized_high = max(high[t+1 : t+1+H])
  realized_low  = min(low[t+1 : t+1+H])

Phase185A also collapses a seq2seq range vector to one pair:
  high = max(high_1 .. high_H)
  low  = min(low_1 .. low_H)

On the owner run, both models had horizon_bars=1, so that envelope happened to equal the next candle.
It still did not report steps 2..N, and it did not prove from the live output tensor whether later candles are emitted.
```

Phase186A scores each emitted pair against that exact future candle:

```text
step k predicted high/low  vs  candle t+k high/low
```

If the model does not emit step k, the audit records it as not auditable. It does not invent the missing step.

## What this phase does not do

```text
No recursive rollout.
No horizon-envelope metric.
Open and close are not model targets.
No TP/SL policy.
No entry policy.
No model training.
No paper/live approval.
```

`recursive_rollout_used` and `envelope_metric_used` are always 0.

## Forecast contract

The reader matches `RangePredictor.forecast`:

```text
seq2seq sample shape = [window, horizon*2]
forecast timestep    = last timestep only
layout               = [high_1, low_1, high_2, low_2, ..., high_H, low_H]
scalar shape         = [2] = step 1 only
```

Price conversion, same as training:

```text
target_units=atr : price = reference_close + raw_offset * ATR(14)
target_units=pct : price = reference_close * (1 + raw_offset)
```

ATR is the causal Wilder ATR used by `target_builder.wilder_atr_series`.

```text
TR[0] = high - low
TR[t] = max(high-low, |high-close[t-1]|, |low-close[t-1]|)
first period candles = expanding mean of TR
then ATR[t] = (ATR[t-1]*(period-1) + TR[t]) / period
```

Input scaling uses the model record `input_scale_range`. Current range models record `[-2, +2]`, which is the historical range-model scale.

## Error definition

Errors are candle-specific, not envelope errors.

```text
high_price_error_atr = (predicted_high - realized_high[t+k]) / ATR[t]
low_price_error_atr  = (predicted_low  - realized_low[t+k])  / ATR[t]
```

Sign:

```text
positive high_price_error_atr = predicted high is too high
positive low_price_error_atr  = predicted low is too high
```

Phase185A used a different low-side sign. For a horizon of 1 only:

```text
Phase185A high_error_atr == Phase186A high_price_error_atr
Phase185A low_error_atr  == Phase186A down_room_error_atr
                         == -Phase186A low_price_error_atr
```

Do not compare the two low-error columns without that sign flip.

Reported per emitted step:

```text
median / p75 / p90 / p95 absolute error
bias and RMSE
Spearman of predicted vs realized high offset, low offset, and candle width
within 0.25 ATR and within 0.50 ATR rates
pair coherence: predicted_high >= predicted_low
candle containment and close-inside rate, diagnostic only
ATR-regime breakdown at the 33/66 percentiles of reference ATR
calibration bins of signed offsets
degradation curve versus step 1
```

Containment is not a pass/fail gate. A point forecast is not a confidence interval.

## Capability fields

The first result to read is capability, not the ready gate.

```text
model_output_horizon
requested_steps
multi_step_available          1 only if the model emits at least 2 steps
all_requested_steps_emitted
missing_steps
capability_verdict
record_horizon
horizon_mismatch
observed_output_shape
production_contract_check
```

Verdicts:

```text
STEP1_ONLY                 model emits only the next candle
PARTIAL_MULTISTEP          model emits some later candles, but not every requested step
MULTISTEP_COVERS_REQUEST   model emits at least the requested number of candle steps
NO_OUTPUT                  nothing measurable was emitted
```

The previous Phase185A owner run recorded `horizon_bars=1` for both `gold_range_4h` v3 and `gold_range_1d` v2. This phase does not hardcode that. The owner run must confirm it from the live tensor. If it is still 1, the honest result is:

```text
only step 1 is auditable
steps 2..requested_steps have no model evidence
candle_forecast_ready_gate = 0
primary_failure_reason = multistep_output_not_available
```

Step 1 is still measured. A horizon of 1 is not hidden behind an empty report.

## Gates

Diagnostic thresholds, not trading approval:

```text
min_rows                    30
min_pair_coherent_rate      0.98
max_median_abs_error_atr    0.50
min_spearman                0.10
```

A step passes `step_accuracy_gate` only when all of those pass.

`candle_forecast_ready_gate` passes only when every requested timeframe emits every requested step and every requested step passes the diagnostic thresholds.

Default `requested_steps=5`. A model that only emits the next candle cannot pass this gate, even if step 1 is accurate. That is intentional: the question is candle-by-candle future candles, not next-candle only.

`selected_timeframe` is the least-bad diagnostic row. It is not an approval.

Paper/live stays `BLOCKED` even if the diagnostic gate passes.

## Implemented command

GUI command:

```text
Audit range multistep accuracy
```

Command kind:

```text
CommandKind.AUDIT_RANGE_MULTISTEP_ACCURACY
```

Script:

```text
scripts/audit_range_multistep_accuracy.py
```

Default models:

```text
range_4h_model_id : gold_range_4h
range_1d_model_id : gold_range_1d
version           : 0 means latest
source_mode       : models
requested_steps   : 5
batch_size        : 256
progress_every    : 2000
```

`source_mode=models` loads candles through the range feature provider. The flat paths are used by `source_mode=predictions`, not by model inference.

Model inference is batched. Progress is printed. This follows the Phase185A performance fix so a full history run is not a silent row-by-row predict loop.

## Main outputs

```text
run_logs/range_multistep_accuracy/latest.json
run_logs/range_multistep_accuracy/latest.html
run_logs/range_multistep_accuracy/latest_model_capability.csv
run_logs/range_multistep_accuracy/latest_step_errors.csv
run_logs/range_multistep_accuracy/latest_step_summary.csv
run_logs/range_multistep_accuracy/latest_bias_by_step.csv
run_logs/range_multistep_accuracy/latest_calibration_by_step.csv
run_logs/range_multistep_accuracy/latest_degradation_curve.csv
run_logs/range_multistep_accuracy/latest_regime_breakdown.csv
run_logs/range_multistep_accuracy/latest_summary.csv
run_logs/range_multistep_accuracy/latest_decision_matrix.csv
```

Read `latest.json` fields in this order:

```text
owner_answer
capability_rows
step_summary_rows
summary_rows
decision_matrix
```

## Recommended GUI run

```text
AI → Audit range multistep accuracy
```

Default fields:

```text
Symbol                  : XAUUSD
Timeframes              : 4H,1D
Source mode             : models
4H model                : gold_range_4h
1D model                : gold_range_1d
Requested future candles: 5
Batch size              : 256
Progress every          : 2000
Output dir              : run_logs/range_multistep_accuracy
```

## CLI equivalent

```powershell
python -u scripts\audit_range_multistep_accuracy.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --requested-steps 5 `
  --atr-period 14 `
  --batch-size 256 `
  --progress-every 2000 `
  --storage-root datasets `
  --output-dir run_logs\range_multistep_accuracy
```

## Verification in sandbox

```text
python -m py_compile scripts/audit_range_multistep_accuracy.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_range_multistep_accuracy.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_range_multistep_accuracy.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 86 passed

python -m ruff / python -m black / python -m mypy
→ unavailable in this sandbox (No module named ruff/black/mypy)
```

The sandbox does not contain the `gold_range_4h` / `gold_range_1d` artifacts, so the owner run has not been executed here. No accuracy numbers are invented.

## Production status

```text
BLOCKED — candle-by-candle forecast accuracy audit only.
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```
