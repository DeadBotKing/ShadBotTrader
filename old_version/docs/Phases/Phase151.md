# Phase151 — Option B Seed Transfer / Repeatability Validation

**Status:** ✅ Phase151A implemented  
**Type:** Research-only validation-to-test repeatability audit  
**Production status:** BLOCKED — no paper/live

## Why this phase exists

The raw Option B sequence model repeatedly showed validation-only edge and test failure:

```text
Validation ATR:
  final_balance = 108.7914
  PF            = 1.2554

Test ATR:
  final_balance = 90.7052
  PF            = 0.8270
```

Phase150A also showed that range-model TP/SL does not beat ATR. Therefore the next question is:

```text
Is the Option B edge reproducible across explicit random seeds?
Does a seed selected only by validation survive test confirmation?
```

## Implemented script

```text
scripts/run_pivot_sequence_option_b_seed_transfer_validation.py
```

GUI command:

```text
Run Option B seed transfer validation
```

## Protocol

For each seed:

```text
1. Train raw Option B with explicit --random-seed.
2. Backtest validation with fixed ATR rules.
3. Backtest test with the same fixed ATR rules.
4. Select the seed only by validation score.
5. Report whether the validation-selected seed passes test confirmation.
```

No threshold/filter is chosen from test.

## Default seeds

```text
20260919,20260920,20260921
```

## Outputs

```text
run_logs\pivot_sequence_option_b_seed_transfer\latest.json
run_logs\pivot_sequence_option_b_seed_transfer\latest.html
run_logs\pivot_sequence_option_b_seed_transfer\latest.csv
```

Per-seed child outputs are under:

```text
run_logs\pivot_sequence_option_b_seed_transfer\seed_<SEED>\train\latest.json
run_logs\pivot_sequence_option_b_seed_transfer\seed_<SEED>\validation_backtest\latest.json
run_logs\pivot_sequence_option_b_seed_transfer\seed_<SEED>\test_backtest\latest.json
```

## Recommended command

```powershell
python -u scripts\run_pivot_sequence_option_b_seed_transfer_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id-prefix gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m `
  --seeds 20260919,20260920,20260921 `
  --max-samples 24000 `
  --epochs 80 `
  --early-stopping-patience 8 `
  --learning-rate 0.0005 `
  --batch-size 16 `
  --selection-metric drawdown_adjusted `
  --validation-min-trades 30 `
  --validation-min-profit-factor 1.05 `
  --validation-min-final-balance 100 `
  --test-min-profit-factor 1.05 `
  --test-min-final-balance 100 `
  --storage-root datasets `
  --output-dir run_logs\pivot_sequence_option_b_seed_transfer
```

## Anti-overfit rule

```text
Validation selects.
Test confirms or rejects.
No test tuning.
If this fails, raw Option B should not continue to Step 4/production.
```

## Verification

```text
python -m py_compile scripts/run_pivot_sequence_option_b_seed_transfer_validation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py

python -m pytest tests/unit/ai/test_pivot_sequence_option_b_seed_transfer.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
```

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase151A trainer report bug fixed / resume existing seed models — 2026-09-20

The owner started Phase151A. The first seed model (`20260919`) trained and saved its model artifacts, but the trainer crashed while building the JSON report:

```text
[X] TypeError: OptionBReport.__init__() missing 1 required positional argument: 'random_seed'
```

Root cause:

```text
Phase147E added `random_seed` to the OptionBReport dataclass, but one report construction path did not pass `random_seed=int(args.random_seed)`.
```

Important state:

```text
The model artifact was saved before the report crash:
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m_seed_20260919\v1_model.keras
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m_seed_20260919\v1_training.json
```

Fixes implemented:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
  - OptionBReport construction now includes random_seed.

scripts/run_pivot_sequence_option_b_seed_transfer_validation.py
  - added --skip-existing-models {0,1}, default=1.
  - If a seed model already has v*_training.json, Phase151A skips retraining that seed and runs validation/test backtests.
```

GUI update:

```text
Run Option B seed transfer validation
  Skip existing models = 1/0
```

Recommended recovery action:

```text
Replace with the fixed zip and rerun the same Phase151A command.
The script should detect the existing seed_20260919 model and continue without retraining it.
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/run_pivot_sequence_option_b_seed_transfer_validation.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_seed_transfer.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Phase151A execution result — seed transfer failed — 2026-09-21

The owner ran Phase151A with three explicit seeds:

```text
20260919
20260920
20260921
```

The validation-selected seed was:

```text
selected_seed     : 20260921
selected_model_id : gold_pivot_pattern_sequence_wavenet_option_b_seed_audit_5m_seed_20260921
selection_metric  : drawdown_adjusted
```

Selected seed validation result:

```text
validation_trades          : 103
validation_final_balance   : 107.4354957611
validation_return_percent  : +7.4354957611%
validation_profit_factor   : 1.2310390020
validation_max_drawdown    : 5.5600713875
validation_total_cash_pnl  : +7.4354957611
validation_buy_cash_pnl    : +0.1865227161
validation_sell_cash_pnl   : +7.2489730450
validation_positive_months : 1
validation_negative_months : 2
validation_pass_gate       : 1
```

Selected seed test result:

```text
test_trades          : 104
test_final_balance   : 93.2596575995
test_return_percent  : -6.7403424005%
test_profit_factor   : 0.8213467893
test_max_drawdown    : 10.0037166505
test_total_cash_pnl  : -6.7403424005
test_buy_cash_pnl    : -1.3009957153
test_sell_cash_pnl   : -5.4393466852
test_positive_months : 1
test_negative_months : 1
test_pass_gate       : 0
transfer_pass_gate   : 0
```

All seed results:

```text
seed 20260921:
  validation PF/final : 1.2310 / 107.4355
  test PF/final       : 0.8213 / 93.2597
  transfer_pass       : 0

seed 20260920:
  validation PF/final : 1.0051 / 100.2053
  test PF/final       : 0.9510 / 97.7156
  transfer_pass       : 0

seed 20260919:
  validation PF/final : 0.9919 / 99.6772
  test PF/final       : 0.8707 / 93.9395
  transfer_pass       : 0
```

Interpretation:

```text
Phase151A failed. The best validation seed did not transfer to test.
The only seed with validation pass gate (20260921) failed test badly.
No seed passed transfer_pass_gate.
```

Decision:

```text
Reject raw Option B 24k seed-repeatability route as a trading candidate.
Do not continue with Step 4 archive/filtering for this Option B family as a production path.
Any future pivot-sequence work needs target/label/architecture or walk-forward redesign, not more blind seed retrains.
No Phase134. No paper shadow. No live trading.
```
