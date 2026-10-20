# PHASE185A — Range Model Reliability / Calibration / Decision-Utility Result

## Status

```text
COMPLETED — range models are not approved as TP/SL or signal engines
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
symbol                              : XAUUSD
timeframes                           : 4H, 1D
source_mode                          : models
evaluated_timeframes                 : 2
reliable_timeframes                  : 0
selected_timeframe                   : 4H
selected_reliability_gate            : 0
range_model_reliability_ready_gate   : 0
no_training_gate                     : 1
no_paper_live_gate                   : 1
```

Decision matrix:

```text
RANGE_AS_TP_SL_ENGINE   : BLOCKED
RANGE_AS_CONTEXT_FEATURE: DIAGNOSTIC_ONLY
PAPER_OR_LIVE           : BLOCKED
```

## Main conclusion

```text
The current 4H and 1D range models are not reliable enough to use as TP/SL engines, signal engines, paper/live decision inputs, or execution authority.
```

They may still have limited diagnostic/context value, especially the 4H model as a weak range-magnitude context feature, but this requires owner review and must not be used for trade execution.

## 4H range model result

```text
model_id       : gold_range_4h
model_version  : 3
target_units   : atr
horizon_bars   : 1
rows           : 33811
```

Forecast coherence:

```text
coherent_rate       : 1.0000
high_coherent_rate  : 1.0000
low_coherent_rate   : 1.0000
coherence_gate      : 1
```

Forecast error:

```text
median_abs_high_error_atr : 0.2196
median_abs_low_error_atr  : 0.2222
p90_abs_high_error_atr    : 0.7180
p90_abs_low_error_atr     : 0.7478
high_bias_atr             : -0.1444
low_bias_atr              : -0.1382
high_rmse_atr             : 0.5337
low_rmse_atr              : 0.5607
error_gate                : 1
```

Ranking / calibration:

```text
up_spearman       : 0.2740
down_spearman     : 0.3122
width_spearman    : 0.5897
up_monotonicity   : 1.0000
down_monotonicity : 1.0000
ranking_gate      : 1
calibration_gate  : 1
```

Decision utility:

```text
decision_proxy_trades        : 0
decision_proxy_rate          : 0.0
decision_proxy_quality_rate  : 0.0
decision_proxy_mean_score    : 0.0
baseline_buy_quality_rate    : 0.1180
baseline_sell_quality_rate   : 0.1255
decision_utility_gate        : 0
range_reliability_gate       : 0
primary_failure_reason       : decision_utility_gate_failed
```

Interpretation:

```text
The 4H range model is coherent, calibrated by bins, and has meaningful ranking signal for realized range magnitude.
However, it produced no directional decision events under the configured decision edge and therefore has no demonstrated decision utility.
It should not be used as a TP/SL or signal engine.
It may be considered only as a weak context/range-magnitude feature after owner review.
```

## 4H calibration detail

Predicted 4H upside bins are monotonic:

```text
up bin 0 mean_pred=0.2821 -> mean_realized=0.3490
up bin 1 mean_pred=0.2976 -> mean_realized=0.3833
up bin 2 mean_pred=0.3356 -> mean_realized=0.4425
up bin 3 mean_pred=0.4042 -> mean_realized=0.5815
up bin 4 mean_pred=0.4770 -> mean_realized=0.7622
```

Predicted 4H downside bins are also monotonic:

```text
down bin 0 mean_pred=0.2763 -> mean_realized=0.3275
down bin 1 mean_pred=0.2942 -> mean_realized=0.3345
down bin 2 mean_pred=0.3381 -> mean_realized=0.4550
down bin 3 mean_pred=0.4175 -> mean_realized=0.6106
down bin 4 mean_pred=0.5016 -> mean_realized=0.7912
```

Important caveat:

```text
The model generally underpredicts realized extremes. Even the highest predicted bins reach 1.0 ATR only about 26–28% of the time and 1.5 ATR only about 12–14% of the time.
```

## 1D range model result

```text
model_id       : gold_range_1d
model_version  : 2
target_units   : atr
horizon_bars   : 1
rows           : 5483
```

Forecast coherence:

```text
coherent_rate       : 1.0000
high_coherent_rate  : 1.0000
low_coherent_rate   : 1.0000
coherence_gate      : 1
```

Forecast error:

```text
median_abs_high_error_atr : 0.2269
median_abs_low_error_atr  : 0.2358
p90_abs_high_error_atr    : 0.7139
p90_abs_low_error_atr     : 0.7434
high_bias_atr             : -0.1336
low_bias_atr              : -0.1313
high_rmse_atr             : 0.4641
low_rmse_atr              : 0.5019
error_gate                : 1
```

Ranking / calibration:

```text
up_spearman       : 0.0008
down_spearman     : 0.0185
width_spearman    : 0.0186
up_monotonicity   : 0.5000
down_monotonicity : 0.5000
ranking_gate      : 0
calibration_gate  : 1
```

Decision utility:

```text
decision_proxy_trades        : 0
decision_proxy_rate          : 0.0
decision_proxy_quality_rate  : 0.0
decision_proxy_mean_score    : 0.0
baseline_buy_quality_rate    : 0.1255
baseline_sell_quality_rate   : 0.1156
decision_utility_gate        : 0
range_reliability_gate       : 0
primary_failure_reason       : ranking_gate_failed
```

Interpretation:

```text
The 1D range model is coherent and has low median error, but it has almost no ranking skill.
Predicted upside/downside values are effectively near-constant across calibration bins.
This behaves like a static ATR climatology estimate, not a dynamic range forecast.
It should not be used as TP/SL engine, signal engine, or decision authority.
```

## 1D calibration observation

The 1D predicted upside is essentially constant:

```text
predicted_up_atr ≈ 0.3853 across all bins
```

The 1D predicted downside is also essentially constant:

```text
predicted_down_atr ≈ 0.3586 across all bins
```

Therefore:

```text
The 1D model is not dynamically ranking future range. It is mostly outputting a stable average-range estimate.
```

## Decision utility observation

Both models produced:

```text
decision_proxy_trades = 0
```

under:

```text
decision_edge_atr = 0.25
```

This means:

```text
The current range forecasts do not create a usable directional edge signal.
```

## Final decision

```text
Do not use range models as TP/SL engines.
Do not use range models as signal engines.
Do not use range models for paper/live decisions.
Do not open Phase134.
```

Allowed interpretation:

```text
4H range model may be kept as a weak range-magnitude/context feature candidate.
1D range model should be treated mostly as static ATR-climatology context unless redesigned.
```

## Recommended next step

A model-training phase is not justified.

Recommended owner decision:

```text
Option A — Keep 4H range as diagnostic context only and do not use 1D range dynamically.
Option B — Run a small Phase186A range-context filter audit, not TP/SL usage.
Option C — Freeze range-model usage entirely and move to regime/external-context research.
```

If continuing, Phase186A should be:

```text
Phase186A — 4H Range Context Filter Utility Audit
```

Purpose:

```text
Check whether 4H predicted range magnitude improves or filters other strategies as context only.
Do not use range predictions as TP/SL or entry signals.
```

## Production status

```text
BLOCKED — Phase185A is range reliability audit only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```
