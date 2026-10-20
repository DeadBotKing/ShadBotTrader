# PHASE187A — Range Multistep Forecast Accuracy Result

## Status

```text
COMPLETED — models emit 5 candle steps, but the forecasts have no ranking skill
Production — BLOCKED
```

The new artifacts were saved under new ids. The old range models were not overwritten.

```text
gold_range_4h : untouched
gold_range_1d : untouched
gold_range_multistep_4h v1 : audited
gold_range_multistep_1d v1 : audited
```

No production approval:

```text
No further training from this result.
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
multistep_timeframes           : 2
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
CANDLE_STEP1_HIGH_LOW          : MEASURED_FAIL
CANDLE_BY_CANDLE_FUTURE_STEPS  : PARTIAL_OR_FAILED
RANGE_AS_FUTURE_PRICE_ENGINE   : BLOCKED
PAPER_OR_LIVE                  : BLOCKED
```

`PARTIAL_OR_FAILED` here does not mean steps were missing. Both models emitted all 5 steps. It means the emitted steps failed the accuracy gates.

## Capability

The live tensor confirms a real multistep head. This is not a recursive rollout.

```text
gold_range_multistep_4h v1
gold_range_multistep_1d v1
target_units              : atr
record_horizon            : 5
window_size               : 150
keras_output_shape        : (None, 150, 10)
observed_output_shape     : batch=(1, 150, 10); sample=(150, 10)
output_layout             : seq2seq_last_timestep
model_output_horizon      : 5
requested_steps           : 5
missing_steps             : none
horizon_mismatch          : 0
production_contract_check : matched
capability_verdict        : MULTISTEP_COVERS_REQUEST
rows_skipped              : 0
```

Rows:

```text
4H : 33807
1D : 5479
```

The row counts are 4 below the horizon=1 audit because step 5 needs four extra future candles. That is expected.

`150` is still the input window. `10` is the forecast width: `[high_1, low_1, ..., high_5, low_5]`.

## Main conclusion

```text
The new models can emit five future candle high/low pairs.
They do not forecast those candles.
Every step is a near-constant ATR offset.
Spearman is about zero at every step on both timeframes.
Error grows with step because the constant offset does not widen with the realized range.
The old gold_range_4h step-1 ranking was better than this new model.
Do not replace gold_range_4h or gold_range_1d with these artifacts.
```

## Why the calibration bins are not five forecasts

For every timeframe and every step, the five calibration bins split one constant. The bin edges differ around `1e-14`. That is float noise, not a changing prediction.

4H step 1 high prediction:

```text
constant : 0.27565264701843 ATR
realized : moves by bin, about 0.49 to 0.52 ATR
```

1D step 1 high prediction:

```text
constant : 0.29214841127396 ATR
realized : moves by bin, about 0.50 to 0.54 ATR
```

The same pattern holds for low, and for steps 2..5. The model is static ATR climatology at every horizon.

## 4H degradation

```text
step  median_abs_high  median_abs_low  high_spearman  width_bias   containment
1     0.206555698526   0.206067499435  0.003304413109  -0.460476012  0.073387168338
2     0.431211581445   0.445092851243  0.001667438115  -0.486058166  0.023900375662
3     0.600583637892   0.606661318003  0.003892108495  -0.511347244  0.013222113763
4     0.743717098883   0.752352837245  0.005006233274  -0.523070583  0.007394918212
5     0.894231004260   0.891257217856  -0.002735430222 -0.543587230  0.005531398823
```

Error versus step 1:

```text
step2 : 2.087628588909
step3 : 2.907611081065
step4 : 3.600564420106
step5 : 4.329248772319
```

Mean predicted high offset stays near `0.26–0.28` ATR while mean realized high offset rises from `0.503730907944` to `0.566912771163`. Mean predicted low offset moves toward zero, from `-0.271353125572` to `-0.200115427375`, instead of following the realized low.

Step failures:

```text
step 1 : high_spearman_failed
step 2 : high_spearman_failed
step 3 : high_error_failed
step 4 : high_error_failed
step 5 : high_error_failed
```

## 1D degradation

```text
step  median_abs_high  median_abs_low  high_spearman   width_bias   containment
1     0.212543122014   0.211871289124  -0.025513595248  -0.438605273  0.027924803796
2     0.503785212118   0.490480446475   0.025343979097  -0.491235245  0.004562876437
3     0.683147001413   0.667026500056   0.022615478024  -0.529152742  0.002007665632
4     0.815673528271   0.802553227500  -0.017234666213  -0.574169426  0.000547545172
5     0.947386908286   0.922193049554   0.010802062537  -0.611040231  0.000365030115
```

Error versus step 1:

```text
step2 : 2.438979973503
step3 : 3.307325851028
step4 : 3.948927742450
step5 : 4.586592938592
```

Mean predicted high offset stays near `0.26–0.29` ATR. Mean realized high offset rises from `0.519216533432` to `0.662134600528`. Mean predicted low offset shrinks from `-0.278036683798` to `-0.145937472582`.

Step 5 containment is `0.000365030115`: about 2 rows out of 5479.

## Comparison with the old horizon=1 models

Old `gold_range_4h` v3, step 1 only:

```text
median_abs_high/low_error_atr : 0.219569039049 / 0.222159309562
high/low/width spearman       : 0.273987530779 / 0.312191463967 / 0.589662562278
width_bias_atr                : -0.282614759056
candle_containment_rate       : 0.121558072817
prediction                    : not constant; calibration bins moved
```

New `gold_range_multistep_4h` v1, step 1:

```text
median_abs_high/low_error_atr : 0.206555698526 / 0.206067499435
high/low/width spearman       : 0.003304413109 / 0.003058589523 / 0.004419906901
width_bias_atr                : -0.460476011758
candle_containment_rate       : 0.073387168338
prediction                    : constant +0.275652647018 / -0.271353125572 ATR
```

Median error is slightly smaller. Ranking is gone. The band is narrower. Containment is worse. The old 4H model remains the better next-candle magnitude context. The new model must not replace it.

Old `gold_range_1d` v2 was already a constant `+0.385315835476 / -0.358623474836` ATR offset with near-zero Spearman. The new 1D model is another constant, `+0.292148411274 / -0.278036683798`, still with no ranking, and with worse containment (`0.027924803796` versus `0.101221958782`).

## Regime check

The zero-ranking result is not one ATR regime. 4H step-1 Spearman stays near zero in `atr_low`, `atr_mid`, and `atr_high`. 1D step-1 high Spearman is slightly negative in all three regimes. Later steps do not recover a stable ranking in any regime.

## Decision

```text
Do not say these models forecast future candles one by one.
They emit the five pairs, but each pair is a static ATR offset.
Do not replace gold_range_4h or gold_range_1d.
Do not use either multistep artifact as a future-price, TP/SL, or entry engine.
Do not paper or live trade.
Do not start another training run from this result unless the owner explicitly changes the question.
```

Allowed reading:

```text
Output contract works: width 10, horizon 5, production reader matches.
Forecast skill does not.
Old 4H horizon=1 model still has the only weak ranking signal in this lane.
1D remains static ATR climatology.
```

## Production status

```text
BLOCKED
```
