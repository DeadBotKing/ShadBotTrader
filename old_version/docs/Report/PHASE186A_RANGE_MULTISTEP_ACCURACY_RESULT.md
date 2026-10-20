# PHASE186A — Range Candle-by-Candle Forecast Accuracy Result

## Status

```text
COMPLETED — current range models do not emit candle-by-candle future forecasts
Production — BLOCKED
```

No production/paper/live approval:

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Top-level result

```text
symbol                         : XAUUSD
timeframes                     : 4H, 1D
source_mode                    : models
requested_steps                : 5
evaluated_timeframes           : 2
multistep_timeframes           : 0
ready_timeframes               : 0
selected_timeframe             : 4H
candle_forecast_ready_gate     : 0
no_training_gate               : 1
no_paper_live_gate             : 1
recursive_rollout_used         : 0
envelope_metric_used           : 0
```

Decision matrix:

```text
CANDLE_STEP1_HIGH_LOW          : MEASURED_PASS
CANDLE_BY_CANDLE_FUTURE_STEPS  : NOT_AVAILABLE
RANGE_AS_FUTURE_PRICE_ENGINE   : BLOCKED
PAPER_OR_LIVE                  : BLOCKED
```

`MEASURED_PASS` on step 1 means at least one timeframe cleared the diagnostic thresholds. That timeframe is 4H only. 1D `step1_accuracy_gate=0`.

## Owner answer

```text
4H: model_output_horizon=1. Only step 1 is auditable. Steps 2,3,4,5 were not emitted.
1D: model_output_horizon=1. Only step 1 is auditable. Steps 2,3,4,5 were not emitted.
There is no model evidence for candle-by-candle forecasts beyond the next candle.
```

## Capability proof

This is not an assumption carried forward from Phase185A. The live tensor says the same thing.

```text
4H gold_range_4h v3
1D gold_range_1d v2
target_units            : atr
record_horizon          : 1
window_size             : 150
input_scale             : [-2.0, +2.0]
keras_output_shape      : (None, 150, 2)
observed_output_shape   : batch=(1, 150, 2); sample=(150, 2)
output_layout           : seq2seq_last_timestep
forecast_timestep       : last
forecast_contract       : last_timestep_interleaved_high_low_pairs
model_output_horizon    : 1
multi_step_available    : 0
missing_steps           : 2,3,4,5
horizon_mismatch        : 0
production_contract_check : matched
rows_skipped            : 0
capability_verdict      : STEP1_ONLY
```

Rows measured:

```text
4H : 33811
1D : 5483
```

The `150` in `(None, 150, 2)` is the input window, not 150 future candles. The last dimension is `2`: one high and one low. A five-candle forecast would have needed width `10` (`high_1, low_1, ..., high_5, low_5`). That width is not present.

`production_contract_check=matched` means the per-step reader and the production max/min collapse read the same tensor. For width 2 those two reads are the same single pair.

No recursive rollout was used. Steps 2..5 were not imputed.

## Main conclusion

```text
The current range models cannot predict future candles one by one.
They emit only the next candle high/low.
4H has modest next-candle ranking, but the predicted candle is systematically too narrow.
1D is a constant ATR offset, not a dynamic candle forecast.
Neither result authorizes TP/SL, entry, paper, or live use.
```

## 4H step 1 — next candle only

```text
model_id                         : gold_range_4h
model_version                    : 3
rows                             : 33811
pair_coherent_rate               : 1.0
median_abs_high_error_atr        : 0.219569039049236
median_abs_low_error_atr         : 0.22215930956179186
p75_abs_high_error_atr           : 0.37634600772121063
p75_abs_low_error_atr            : 0.38571348146536155
p90_abs_high_error_atr           : 0.7179751450118719
p90_abs_low_error_atr            : 0.7478392177742353
p95_abs_high_error_atr           : 1.0900184584553356
p95_abs_low_error_atr            : 1.1350181297331552
high_bias_atr                    : -0.14439230602737527
low_bias_atr                     : 0.13822245302854452
width_bias_atr                   : -0.2826147590559198
mean_predicted_high_offset_atr   : 0.3593103427566965
mean_realized_high_offset_atr    : 0.5037026487840718
mean_predicted_low_offset_atr    : -0.36552708631447006
mean_realized_low_offset_atr     : -0.5037495393430147
high_spearman                    : 0.2739875307788664
low_spearman                     : 0.3121914639672305
width_spearman                   : 0.5896625622781124
high_monotonicity                : 1.0
low_monotonicity                 : 1.0
high_within_025_atr_rate         : 0.5618585667386353
low_within_025_atr_rate          : 0.557629173937476
high_within_050_atr_rate         : 0.8363550323859099
low_within_050_atr_rate          : 0.8283990417319808
candle_containment_rate          : 0.12155807281653899
close_inside_rate                : 0.5114016148590695
derived_midpoint_median_abs_error_atr : 0.22228928133834353
step_accuracy_gate               : 1
timeframe_primary_failure        : multistep_output_not_available
```

Bias sign:

```text
high_bias_atr < 0 : predicted high is too low
low_bias_atr  > 0 : predicted low is too high
width_bias_atr < 0 : predicted candle is too narrow
```

Mean candle width:

```text
predicted width : 0.7248374290711666 ATR
realized width  : 1.0074521881270865 ATR
```

The model ranks next-candle width (`width_spearman=0.5897`) and the calibration bins are monotonic, but it does not reach the realized extreme. In the top high bin, mean predicted offset is `0.47701654400972904` ATR and mean realized offset is `0.762208599213673` ATR.

`candle_containment_rate=0.1216` means the predicted high/low band contains the whole next candle on only 12.16% of rows. `close_inside_rate=0.5114` is about a coin flip for the next close.

`step_accuracy_gate=1` only means the loose diagnostic thresholds passed:

```text
median abs error <= 0.50 ATR
spearman >= 0.10
pair coherence >= 0.98
rows >= 30
```

It is not a trading-quality pass. p90 absolute error is about `0.72–0.75` ATR and p95 exceeds `1.0` ATR.

ATR regimes do not remove the 4H ranking signal:

```text
atr_low  high/low spearman : 0.2749642018001769 / 0.31898241351030626
atr_mid  high/low spearman : 0.30801977192729674 / 0.336093517474839
atr_high high/low spearman : 0.23563008079138817 / 0.27933494115393437
```

## 1D step 1 — constant ATR offset

```text
model_id                         : gold_range_1d
model_version                    : 2
rows                             : 5483
pair_coherent_rate               : 1.0
median_abs_high_error_atr        : 0.226872601072356
median_abs_low_error_atr         : 0.23584258332283253
p90_abs_high_error_atr           : 0.7139057801411965
p90_abs_low_error_atr            : 0.743384698373485
p95_abs_high_error_atr           : 0.9661975675331131
p95_abs_low_error_atr            : 1.0319742057702361
high_bias_atr                    : -0.13364452609817495
low_bias_atr                     : 0.13128957338791983
width_bias_atr                   : -0.26493409948609475
mean_predicted_high_offset_atr   : 0.38531583547592163
mean_realized_high_offset_atr    : 0.5189603615740965
mean_predicted_low_offset_atr    : -0.35862347483634954
mean_realized_low_offset_atr     : -0.48991304822426934
high_spearman                    : 0.000832207690797381
low_spearman                     : 0.018488786566680078
width_spearman                   : 0.018602155506388697
high_monotonicity                : 0.5
low_monotonicity                 : 0.5
high_within_050_atr_rate         : 0.824548604778406
low_within_050_atr_rate          : 0.8240014590552617
candle_containment_rate          : 0.10122195878168885
close_inside_rate                : 0.49261353273755243
step_accuracy_gate               : 0
step_primary_failure             : high_spearman_failed
timeframe_primary_failure        : multistep_output_not_available
```

The five 1D calibration bins are not five forecasts. High prediction stays at `0.38531583547592` ATR. The bin edges differ only around `1e-14`, which is float noise. Low prediction stays at `-0.35862347483635` ATR. Realized means still move. The model does not.

Mean candle width:

```text
predicted width : 0.7439393103122712 ATR
realized width  : 1.0088734097983658 ATR
```

`within_050_atr_rate≈0.824` is not skill. A near-constant offset can land inside 0.50 ATR often while Spearman stays at zero. Ranking is the skill test, and 1D fails it in every ATR regime:

```text
atr_low  high/low spearman : -0.008498918377209392 / 0.01622523805696572
atr_mid  high/low spearman : 0.002155882757654893 / 0.004762029959037058
atr_high high/low spearman : 0.015746627827772357 / 0.03345171306519535
```

## Cross-check against Phase185A

Step-1 rows, median errors, and Spearman values match the Phase185A owner run to numerical noise. Examples:

```text
4H rows                         : 33811 = 33811
4H median_abs_high_error_atr    : 0.219569039049236 ≈ 0.21956903904923597
4H high_spearman                : 0.2739875307788664 ≈ 0.27398753438518514
1D high_spearman                : 0.000832207690797381 = 0.000832207690797381
1D constant high offset         : 0.38531583547592 = Phase185A predicted_up ≈ 0.3853
```

Phase186A did not discover a different step-1 model. It proved that the live output has no further steps, and it added the too-narrow bias and containment numbers.

## Decision

```text
Do not say these models predict all future candles.
Do not use them as a future-price engine.
Do not use them as TP/SL or entry authority.
Do not paper or live trade from this result.
Do not impute steps 2..5 by recursive rollout unless that method is explicitly authorized as a separate diagnostic.
Do not train a multi-step range model unless training is explicitly authorized.
```

Allowed reading:

```text
4H may remain a weak next-candle magnitude context only.
1D is static ATR climatology.
Multi-step candle forecast from the current artifacts is unavailable.
```

## Production status

```text
BLOCKED
```
