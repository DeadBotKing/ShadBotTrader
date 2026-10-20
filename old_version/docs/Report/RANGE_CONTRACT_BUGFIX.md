# Range contract bugfix — 2026-10-18

Owner asked to fix the proven bugs. This is not a new training run and not a new research phase.

```text
No model training.
No replacement of gold_range_4h or gold_range_1d.
No Phase134.
No paper. No live.
No gate relaxation.
```

## Fixed

```text
build_range_labels docstring
  was: (high[t+k] - close[t]) / ATR
  is : max(high[t+1..t+H]) and min(low[t+1..t+H])
  per-candle labels stay in build_range_labels_seq2seq

range_model_role description
  was: "highest high and lowest low" while seq2seq=True
  is : per-candle offsets; the trading band is a separate reduction

RangePredictor.forecast
  still returns one band
  n_pairs == 1 -> that pair, band_reduction=single_pair
  n_pairs  > 1 -> max(high), min(low), band_reduction=envelope_max_min
  step_high_raw / step_low_raw keep every emitted pair
  horizon=1 production numbers do not change

Huber delta for new compiles
  pct -> 0.005
  atr -> 1.0
  function: range_huber_delta
  saved models keep the delta stored in their loss config
  the local _RangeLoss inside _build_compiled was removed
  it hard-coded delta=0.005 and re-registered a class custom_objects does not export

range forecast inspector
  a record horizon larger than the tensor width used to IndexError
  the path length is now the emitted pair count
  a mismatch is a warning, not an exception

audit range_raw_pair
  a [1, width] row now uses the same envelope reduction as RangePredictor
  it no longer keeps only the first pair

Phase181B-185A headers
  they said "awaiting owner run" after the owner results were already recorded
```

## Not changed, on purpose

```text
3*Huber + 6*MAE + 1*MSE weights
  MAE weight 6 still pulls a weak model toward the median
  retuning the weights would be a new objective, not an arithmetic correction

40/60 last-row loss weight
  the last row is the decision candle, not "tomorrow"
  averaging pair-MAEs is algebraically identical to flat MAE when every
  pair has two columns
  test_pair_mae_average_is_identical_to_flat_mae locks that identity

close_rel = 0 and the duplicate volume log
  removing them changes input width and breaks saved models

per-window min-max
  not redesigned

gold_range_4h v3 and gold_range_1d v2
  not replaced
  their saved loss still has delta=0.005
  loading them for inference does not recompile the loss

trend_score
  dataset.target_units is stored as pct, so a Huber compile still uses 0.005
  its target is a score in (-1, +1), not an ATR multiple
  that scale was not measured here and was not retuned
```

## What this does not do

```text
It does not create forecast skill.
It does not make gold_range_multistep_4h or gold_range_multistep_1d tradable.
It does not authorize another horizon=5 training run.
PAPER_OR_LIVE remains BLOCKED.
FREEZE_RANGE_MULTISTEP_ROUTE remains in force.
FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE remains in force.
```

## Tests

```text
python -m pytest
  tests/unit/ai/test_computational_contracts.py
  tests/unit/ai/test_range_predictor_atr.py
  tests/unit/ai/test_range_multistep_accuracy.py
  tests/unit/ai/test_range_model_reliability.py
  tests/unit/ai/test_prediction_target.py
  tests/unit/ai/test_range_multistep_training.py
  tests/unit/ai/test_range_loss_serialization.py
  tests/unit/simulation/test_dual_model_backtest.py
  tests/unit/simulation/test_range_atr_wiring.py
  tests/unit/ai/test_model_roles_knobs.py
  tests/unit/presentation/test_all_range_models.py
→ passed
TF serialization tests skipped: tensorflow is not installed here

python -m ruff / black / mypy
→ unavailable in this sandbox (No module named ruff/black/mypy)
python -m py_compile on the edited modules → passed
```
