# Phase 116 Report — Hybrid Range-Aware Decision Integration

Date: 2026-09-09

## Trigger

Phase 125 found a profitable range-aware threshold for the hybrid head:

```text
buy_threshold  = 0.80
sell_threshold = 0.65
min_margin     = 0.05
trades         = 325
buy/sell       = 160 / 165
total_pnl      = +291.154987683185
profit_factor  = 1.2471739846573604
```

Phase 113 then confirmed the result against random and White-style max baselines:

```text
random_p_value      = 0.000999000999000999
white_style_p_value = 0.000999000999000999
```

Phase 116 integrates that rule into the standard decision pipeline instead of leaving it as a research-only backtest script.

## Implemented path

```text
HybridHeadPredictor
→ HybridHeadForecast
→ HybridRangeAwareStrategy
→ PositionAwareDecisionEngine
→ PolicyRiskGate
→ DefaultIntentFactory
→ audit files
```

No order is sent to MT5 in this phase.

## Files

```text
src/ShadBotTrader/domain/ai/prediction_target.py
src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py
src/ShadBotTrader/infrastructure/trading/hybrid_range_aware_strategy.py
src/ShadBotTrader/infrastructure/trading/__init__.py
scripts/audit_hybrid_range_aware_decisions.py
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/ai/test_prediction_target.py
tests/unit/ai/test_hybrid_head_predictor.py
tests/unit/strategy/test_hybrid_range_aware_strategy.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

## Runtime gates

BUY:

```text
buy_probability >= 0.80
buy_probability - sell_probability >= 0.05
buy_probability - hold_probability >= 0.05
4H up room >= 2
1D up room >= 5
TP = min(range_4h_high, range_1d_high)
SL = range_4h_low
TP distance >= 2
SL distance >= 2
```

SELL:

```text
sell_probability >= 0.65
sell_probability - buy_probability >= 0.05
sell_probability - hold_probability >= 0.05
4H down room >= 2
1D down room >= 5
TP = max(range_4h_low, range_1d_low)
SL = range_4h_high
TP distance >= 2
SL distance >= 2
```

## User command

```powershell
python -u scripts/audit_hybrid_range_aware_decisions.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 0.30 `
  --max-windows 0 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --capital 10000 `
  --base-quantity 1 `
  --storage-root datasets
```

## Output

```text
run_logs/hybrid_decision_audit/latest.json
run_logs/hybrid_decision_audit/latest.csv
```

The expected sanity check is close to the Phase 125 selection:

```text
trade_intents ≈ 325
buy/sell      ≈ 160 / 165
label_precision ≈ 65.85%
coverage      ≈ 13.54%
```

## Quality gate

Targeted checks passed:

```text
ruff touched files: PASS
black touched files: PASS
pytest targeted: 91 passed
pytest full: 1685 passed, 54 skipped
mypy src/ShadBotTrader/infrastructure/ai/hybrid_head_predictor.py: PASS
```

Full repository gate remains red due to pre-existing issues:

```text
ruff full: 219 old lint errors
black full: 21 old files would be reformatted
mypy full: 28 old errors in 10 files
```

## Next

Run the Phase116 audit command on the user's Windows dataset. If it reproduces the Phase125 trade-intent counts, proceed to Phase115 live decision audit / paper shadow. Do not send real orders yet.

## User audit result

The user ran `scripts/audit_hybrid_range_aware_decisions.py` against the saved Phase 125 threshold.

```text
model_version       : 1
matrix_rows         : 8000
eval_rows           : 2400
threshold_source    : model_record:gold_hybrid_lightgbm_head_5m:v1
buy_threshold       : 0.80
sell_threshold      : 0.65
min_margin          : 0.05
trade_intents       : 325
no_trade            : 2075
buy_intents         : 160
sell_intents        : 165
label_correct       : 214
label_precision     : 0.6584615384615384
coverage            : 0.13541666666666666
```

This exactly matches the Phase 125 selected candidate:

```text
Phase125 trades/coverage/precision = 325 / 0.13541666666666666 / 0.6584615384615384
Phase116 intents/coverage/precision = 325 / 0.13541666666666666 / 0.6584615384615384
```

Conclusion:

```text
PASS — the runtime Strategy -> DecisionEngine -> RiskGate -> IntentFactory path reproduces the Phase 125 decisions.
```

Next step:

```text
Phase115 live decision audit / paper shadow, still without real-money execution.
```
