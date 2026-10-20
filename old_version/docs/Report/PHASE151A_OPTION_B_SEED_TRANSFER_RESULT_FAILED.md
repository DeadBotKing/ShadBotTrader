# Phase151A Result — Option B Seed Transfer Failed

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
