# Project mistake review — 2026-10-14

This review checks the range-forecast lane against the code, not against the hope that the next model will work.

```text
No new training.
No paper. No live.
No claim that gold_range_4h is a trading model.
```

## 1. Three different questions were treated as one model

These are not the same target.

```text
envelope     : max(high[t+1..t+H]) and min(low[t+1..t+H])
per candle   : high/low of candle t+k, for each k
production   : if the tensor has more than one pair, keep max(high) and min(low)
```

Code:

```text
src/ShadBotTrader/infrastructure/ai/target_builder.py
  build_range_labels()          envelope
  build_range_labels_seq2seq()  per candle t+k

src/ShadBotTrader/infrastructure/ai/model_roles.py
  range_model_role description says "highest high and lowest low"
  that is the envelope sentence

src/ShadBotTrader/infrastructure/ai/dual_predictor.py
  RangePredictor.forecast
  n_pairs == 1: use that pair
  n_pairs > 1 : best_high = max(highs), best_low = min(lows)
```

The seq2seq trainer asks for per-candle offsets. The role text describes an envelope. The production reader throws the per-candle pairs away and rebuilds an envelope. Phase186A read the tensor directly, so the audit was the right reader. The trading path is not.

`build_range_labels` docstring also says `(high[t+k] - close[t]) / ATR`, but the function body uses `max`/`min` over the whole horizon. The docstring is wrong.

## 2. The loss is still calibrated for percent targets

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
RangeLoss delta = 0.005
weights         = 3*Huber + 6*MAE + 1*MSE
comment         = target magnitude +/-0.002, val_mae ~ 0.0017
```

Current range targets are ATR multiples, about 0.3 to 1.0, not 0.2 percent. With `delta=0.005`, Huber is in its linear MAE zone for almost every real residual. The comment that says this delta keeps the loss in MSE mode is false for `target_units=atr`.

The effective loss is therefore mostly MAE. MAE on a weak input is optimized by a constant near the median. That matches the Phase187A tensor: calibration bin edges differ by about `1e-14`.

This defect exists for the old horizon=1 models too. It did not by itself erase the old 4H ranking, so it is a training-scale mistake, not the only cause of the collapse.

## 3. Horizon=5 was trained with a horizon=1 loss

```text
seq2seq loss = 0.4 * all timesteps + 0.6 * last timestep
comment      = last timestep is "tomorrow"
```

For `horizon=5` the last timestep is ten numbers, `[high_1, low_1, ..., high_5, low_5]`, not tomorrow alone. Those ten numbers are averaged together. Step 5 residuals are about four times step 1 residuals, so they dominate the MAE. The optimizer can satisfy the loss with one static ATR vector and drop the step-1 ranking the old model had.

Measured comparison, same audit contract:

```text
gold_range_4h v3 step1 spearman          : 0.2740 / 0.3122 / 0.5897
gold_range_multistep_4h v1 step1 spearman: 0.0033 / 0.0031 / 0.0044
```

Changing only `horizon` was the wrong experiment. The loss, the Huber delta, and the production reader were still the horizon=1 design.

## 4. Median error was treated as skill

A constant ATR offset can have a median absolute error near `0.21` ATR and a within-0.50 rate near `0.80` while Spearman is zero. Phase185A 1D already showed this. Phase187A showed it again on both timeframes and all five steps.

Useful test:

```text
Spearman and calibration movement
```

Not useful alone:

```text
median_abs_error_atr
within_050_atr_rate
step_accuracy_gate when min_spearman is 0.10 and the other model is constant
```

`CANDLE_STEP1_HIGH_LOW=MEASURED_PASS` in the first Phase186A run only meant 4H cleared that loose gate. It was not a trading pass. The later multistep run correctly returned `MEASURED_FAIL`.

## 5. The range audits are not out-of-sample

`scripts/audit_range_model_reliability.py` and `scripts/audit_range_multistep_accuracy.py` score every window from `window_size-1` to the last label. There is no train/test cut.

The multistep collapse is still real: a constant on the full history, including rows the model was trained on, is worse than a test-only failure. The old 4H Spearman was measured the same way, so it can be inflated by in-sample fit. It is not a proven future edge.

The saved artifact is also the last roll-forward fold, not a walk-forward winner:

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
folds = folds[-self._max_folds :]
"the final fold's model is the one promoted to the artifact"
```

## 6. Per-window min-max still removes level

```text
src/ShadBotTrader/infrastructure/ai/data_windowing.py
minmax_scale_window
each column of the 150-row window is scaled to [-2, +2]
a constant column becomes 0
```

The model does not see the dollar price. ATR targets removed the old percent-scale bug, but they did not give the network a raw volatility level inside the window. Phase 95 was necessary and not sufficient. `docs/Report/RANGE_MODEL_CONSTANT_OFFSET_ROOT_CAUSE.md` still says the next step is ATR normalization. That step already happened. The constant offset remains, now in ATR units:

```text
gold_range_1d v2              : +0.385315835476 / -0.358623474836
gold_range_multistep_4h step1 : +0.275652647018 / -0.271353125572
gold_range_multistep_1d step1 : +0.292148411274 / -0.278036683798
```

## 7. Research process

These routes were already closed before the multistep training:

```text
Phase150A : ATR control beat range TP/SL
Phase184A : FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
Phase185A : range_model_reliability_ready_gate=0
Option B  : pivot-sequence transfer failed
```

Phase187A then trained another range head on the same features and the same loss family. It answered the emit question and destroyed the only ranking signal. That training was an authorized experiment, but it should be the last one on this contract.

`RangePredictor` would also be the wrong consumer for a good multistep model. Fixing the reader without a model that ranks is not a strategy.

## 8. Documentation drift

These phase files still say `IMPLEMENTED — awaiting owner run` after the owner results were recorded elsewhere:

```text
docs/Phases/Phase181B.md
docs/Phases/Phase182A.md
docs/Phases/Phase183A.md
docs/Phases/Phase184A.md
docs/Phases/Phase185A.md
```

`docs/CURRENT_STATE.md` has the results. The phase headers do not. A later reader can follow the stale header.

## 9. Computational checks that were run

`tests/unit/ai/test_computational_contracts.py` locks these results:

```text
build_range_labels horizon=2 high = max of the two future highs
build_range_labels_seq2seq high_1 = only candle t+1
they are not equal
WindowGenerator seq2seq last-row label = the label stored on that same row
audit wilder_atr == target_builder.wilder_atr_series exactly
feature ATR ewm seed != Wilder seed at bar 14; they converge later
Huber delta=0.005 is outside the quadratic zone for 0.21/0.50/0.89 ATR residuals
close_rel is identically 0
volume_raw_log and volume_log are the same log1p(volume)
```

The feature ATR mismatch is real but small after the seed. On a 400-bar random path the late relative difference was about `1e-11`. It does not explain a 33,807-row constant output.

`RangePredictor.forecast` still does this when `n_pairs > 1`:

```text
best_high = max(high_1 .. high_H)
best_low  = min(low_1 .. low_H)
```

A good per-candle model would still be consumed as an envelope by the production path.

## 10. Calibration bug that hid the constant output

`nunique()` treated `0.27565264701843` and `0.27565264701846` as different forecasts. `qcut` then built five bins from float noise. That is why Phase187A reported `calibration_available=1` and monotonicity of `0.25` to `0.75` on a collapsed model.

Both audit scripts now refuse a prediction whose span is `<= 1e-8` or whose relative span is `<= 1e-6`. The owner JSON already recorded is unchanged. A rerun would show no calibration bins for those constant steps.

The only `shift(-...)` in `src/` is Ichimoku `chikou`, and that feature is marked non-causal and excluded. Span A/B use `shift(+kijun)`, which is a lag, not future data.

## What was not a mistake

```text
Phase186A read the live tensor instead of trusting record.horizon.
Production ids were not overwritten.
Option B was not grafted onto the range target.
Non-causal features are excluded from training.
The negative results were measured, not hidden.
```

## Decision

```text
Do not train another range horizon on this loss.
Do not replace gold_range_4h v3.
Do not use gold_range_multistep_* as a price, TP/SL, or entry engine.
Do not paper or live trade.
Do not follow the old ATR-retrain instruction. It is already done.
```

## Fixes applied — 2026-10-18

The owner asked to correct the proven bugs. Details:

```text
docs/Report/RANGE_CONTRACT_BUGFIX.md
```

Corrected in code:

```text
envelope docstring no longer claims the per-candle formula
role text no longer calls the seq2seq target an envelope
RangePredictor keeps step_high_raw / step_low_raw
the single band is still max/min when more than one pair is emitted
new ATR compiles use Huber delta=1.0; percent compiles stay at 0.005
saved models keep their serialized delta
inspector no longer IndexErrors when record.horizon exceeds tensor width
Phase181B-185A headers no longer say awaiting owner run
```

Not retuned:

```text
loss weights 3/6/1
40/60 last-row weight
pair-MAE regrouping is algebraically identical to flat MAE
input columns close_rel and the duplicate volume log
```

This fix does not create forecast skill and does not authorize a rerun.
