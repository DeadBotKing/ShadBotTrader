# PHASE155A — Payoff-Target Tensor + Diagnostic Option B Training Report

## Summary

Phase155A has been implemented to turn Phase154A payoff-stable targets into real tensors and diagnostic Option B models.

It does not approve production. It is an evidence-generating phase.

```text
No Phase134.
No paper shadow.
No live trading.
```

## Implemented files

```text
scripts/build_pivot_payoff_sequence_tensor.py
scripts/run_pivot_payoff_option_b_diagnostic.py
tests/unit/ai/test_pivot_payoff_sequence_tensor.py
tests/unit/ai/test_pivot_payoff_option_b_diagnostic.py
```

GUI integration:

```text
CommandKind.RUN_PIVOT_PAYOFF_OPTION_B_DIAGNOSTIC
GUI label: Run payoff-target Option B diagnostic
```

## Phase155A chain

The main wrapper runs the complete diagnostic chain for B4 and B2:

```text
build payoff tensor
→ tensor health audit
→ Option B train
→ validation backtest
→ test backtest
→ aggregate report
```

## Candidate priority

```text
B4 first:
  lookahead_bars = 24
  pivot_zone_atr = 0.35
  tp_atr         = 1.0
  sl_atr         = 0.5
  min_score_edge = 0.1

B2 backup:
  lookahead_bars = 24
  pivot_zone_atr = 0.25
  tp_atr         = 1.0
  sl_atr         = 0.75
  min_score_edge = 0.1
```

## Output paths

Aggregate:

```text
run_logs\pivot_payoff_option_b_diagnostic\latest.json
run_logs\pivot_payoff_option_b_diagnostic\latest.html
run_logs\pivot_payoff_option_b_diagnostic\latest.csv
```

Candidate tensors:

```text
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b4_latest.npy
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b4_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_flat_b4_latest.parquet

datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b2_latest.npy
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b2_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_flat_b2_latest.parquet
```

Models:

```text
datasets\models\gold_pivot_payoff_option_b_b4_5m\v*_model.keras
datasets\models\gold_pivot_payoff_option_b_b4_5m\v*_training.json

datasets\models\gold_pivot_payoff_option_b_b2_5m\v*_model.keras
datasets\models\gold_pivot_payoff_option_b_b2_5m\v*_training.json
```

## Verification

```text
python -m py_compile scripts/build_pivot_payoff_sequence_tensor.py scripts/run_pivot_payoff_option_b_diagnostic.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_sequence_tensor.py tests/unit/ai/test_pivot_payoff_option_b_diagnostic.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_sequence_tensor.py tests/unit/ai/test_pivot_payoff_option_b_diagnostic.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 48 passed
```

Full ruff/black were unavailable in this sandbox image:

```text
python -m ruff ... → No module named ruff
python -m black ... → No module named black
```

## Follow-up fixes after first owner runs

The first owner run built and health-audited the B4 tensor successfully, then crashed at Option B training with:

```text
IndexError: index 2 is out of bounds for axis 0 with size 1
```

First mitigation:

```text
Phase155A wrapper default class_weight changed from auto to off.
GUI field Class weights added with default off.
Option B trainer also detects target_mode=first_hit_payoff and disables class_weight=auto defensively.
```

The second owner run with `--class-weight off` still crashed with the same message. The actual root cause was then identified:

```text
Phase155A payoff tensors store scalar target metadata:
  target_mode = ["first_hit_payoff"]

The Option B trainer scoped every target_* key by sample indices.
That is valid for target_action and target_buy_r, but invalid for target_mode because it has size 1.
```

Final fix:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
  scoped_target_meta() now indexes only per-sample target_* arrays whose first axis matches tensor sample count.
  scalar target metadata such as target_mode is ignored for Keras targets.
```

Recovery recommendation:

```text
Rerun Phase155A with --skip-existing-tensors 1 and --class-weight off so the already-built B4 tensor is reused.
```

## Next owner action

Run from GUI:

```text
AI → Run payoff-target Option B diagnostic
```

or run the PowerShell command from `docs/Phases/Phase155.md`.

After completion, send:

```text
run_logs\pivot_payoff_option_b_diagnostic\latest.json
```
