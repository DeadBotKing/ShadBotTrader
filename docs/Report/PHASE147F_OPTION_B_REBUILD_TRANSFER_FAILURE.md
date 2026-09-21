# Phase147F Report — Option B Rebuild Validation-to-Test Transfer Failure

## Phase147F raw Option B 24k rebuild validation-vs-test transfer failure — 2026-09-20

The owner ran the validation ATR PnL check for the rebuilt raw Option B 24k model after its test PnL failed.

Validation replay configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version     : 1
eval_split        : validation
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-05-28 09:20:00+00:00 → 2026-07-01 09:05:00+00:00
buy/sell threshold: 0.34 / 0.34
min_margin        : 0
tp/sl multiplier  : 0.75 / 0.75
hold_bars         : 48
spread            : pct 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Validation result:

```text
trades             : 110
BUY / SELL trades  : 70 / 40
wins / losses      : 62 / 48
win_rate           : 56.3636%
final_balance      : 108.7914207603
return_percent     : +8.7914207603%
total_cash_pnl     : +8.7914207603
gross_profit       : 43.2124907078
gross_loss         : 34.4210699475
profit_factor      : 1.2554081199
max_drawdown_cash  : 5.9715931205
take_profit        : 33
stop_loss          : 25
timeout            : 52
BUY PnL            : -1.8550476298
SELL PnL           : +10.6464683900
monthly            : 2026-05 +1.1865238507, 2026-06 +7.6048969096
positive_months    : 2
negative_months    : 0
```

Same rebuilt model on test:

```text
trades             : 135
final_balance      : 90.7052413035
return_percent     : -9.2947586965%
profit_factor      : 0.8270058072
max_drawdown_cash  : 10.7624722054
BUY PnL            : -5.3900375011
SELL PnL           : -3.9047211954
monthly            : 2026-07 -3.6628516601, 2026-08 -5.6319070363
positive_months    : 0
negative_months    : 2
```

Interpretation:

```text
This is a clear validation-to-test transfer failure.
The model has strong validation PnL, but that edge is almost entirely SELL-side and does not survive the later test regime.
Validation: BUY is negative, SELL is strongly positive.
Test: both BUY and SELL are negative.
```

Decision:

```text
Do not promote the rebuilt raw Option B 24k model.
Do not run Step 4/range-aware archive on this model as if it is the historical winner.
The correct next phase is a controlled anti-overfit validation-to-test audit: discover only on validation, confirm on test, and later walk-forward.
No Phase134. No paper shadow. No live trading.
```

Recommended next research phase:

```text
Phase150A — Option B validation-to-test transfer / seed-threshold audit
```

Required anti-overfit rules for Phase150A:

```text
- validation is for discovery only
- test is confirmation only
- no threshold/filter chosen from test
- if validation-selected candidate fails test, reject it
- if test passes, still require walk-forward before paper/live
```

## Phase148B range-aware archive now supports train/validation splits — 2026-09-20

The owner proposed the correct next direction after the raw Option B rebuild showed validation-to-test transfer failure:

```text
Build/run a more realistic simulation backtest where TP and SL are derived from range forecasts.
Run it fully on train and validation first.
Then perform anti-overfit filtering/selection from those archive outputs before any test confirmation.
```

Assessment:

```text
This is the correct direction. The previous ATR-only PnL checks may be too crude for exit geometry, and test must be held back for confirmation rather than used for discovery.
```

Implementation update:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
GUI: Backtest pivot sequence WaveNet PnL
GUI: Backtest sequence WaveNet range-aware archive
```

Both backtest scripts now support:

```text
--eval-split train
```

Previously Phase148A range-aware archive supported only:

```text
test, validation, all, tail
```

Now the realistic range-aware archive can be generated separately for:

```text
train      → in-sample anatomy / diagnostics only
validation → discovery / filter selection
test       → confirmation only, not tuning
```

Anti-overfit rule:

```text
Do not use test for discovery.
Run train + validation range-aware archives first.
Discover candidate thresholds/filters from train/validation only.
Then run exactly one unchanged confirmation on test.
If test fails, reject.
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/handlers.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```
