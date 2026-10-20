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

## Full-history HTML report extension

A companion report script was added after the user requested a full 5M visual backtest before Phase115:

```text
scripts/report_hybrid_full_backtest.py
GUI command: Full hybrid 5M backtest report
```

It evaluates the saved Phase125 thresholds without threshold search and writes:

```text
run_logs/hybrid_full_backtest/latest.html
run_logs/hybrid_full_backtest/latest.json
run_logs/hybrid_full_backtest/latest.csv
```

For a true full 5M-history diagnostic, build the matrix with:

```text
scripts/build_hybrid_xgboost_matrix.py --scope all --max-windows 0 --output-name hybrid_xgboost_matrix_all_5m
```

Then run the report with:

```text
scripts/report_hybrid_full_backtest.py --matrix-path datasets\processed\XAUUSD\5M\hybrid_xgboost_matrix_all_5m.parquet --eval-frac 1.0
```

This full-history report is visual/diagnostic. It may include model training periods and therefore does not replace the Phase125 holdout plus Phase113 significance result.

## Candle replay and account-balance upgrade

After the user clarified that they want the old-style candle replay, the full report was upgraded:

```text
scripts/report_hybrid_full_backtest.py
  --initial-capital 100
  --units 1
```

The HTML now includes:

```text
candle-by-candle slider
entry circles
exit squares
yellow entry line
green TP line
red SL line
active trade details
balance after closed trades
```

Balance formula:

```text
final_balance = initial_capital + total_pnl * units
```

This is a sizing diagnostic, not a broker margin/liquidation simulator. With the validated Phase125 max drawdown around 347 per unit, a 100 USD account with units=1 would breach zero; use smaller sizing such as units=0.1 for a first visual sanity run.

## Holdout candle-replay run with 100 USD sizing view

The user ran the upgraded HTML replay report with `initial_capital=100` and `units=0.1`.

```text
matrix_rows         : 8000
evaluated_rows      : 2400
threshold_source    : model_record:gold_hybrid_lightgbm_head_5m:v1
threshold           : buy=0.80 sell=0.65 margin=0.05
trades              : 325
buy/sell            : 160 / 165
wins/losses         : 168 / 157
win_rate            : 51.6923%
label_precision     : 65.8462%
total_pnl           : +291.154987683185
profit_factor       : 1.2471739846573604
max_drawdown        : 347.044035279524
coverage            : 13.5417%
```

Sizing view:

```text
initial_capital     : 100
units               : 0.1
final_balance       : 129.1154987683185
net_profit          : +29.115498768318503
return_percent      : +29.115498768318504%
max_drawdown_cash   : 34.7044035279524
would_breach_zero   : false
```

The HTML replay contains 2440 candles and 325 trades. This is the validated holdout replay, not the full 5M history, because it used the existing 8000-row matrix with `eval_frac=0.30`.

## Replay bug fix and streamed full-history mode

The HTML replay initially rendered a black/empty chart. The root cause was JSON escaping inside a raw script block:

```text
<script type="application/json">{html.escape(json.dumps(...))}</script>
```

In a script raw-text element, `&quot;` remains literal text, so `JSON.parse` fails. The fix is `script_json()`, which writes JSON safely without HTML-escaping quotes and escapes only dangerous raw-script characters (`<`, `>`, `&`). The replay now also has a visible loading/error fallback.

A memory-safe full 5M mode was added to the same script:

```text
scripts/report_hybrid_full_backtest.py --source-mode stream --stream-scope all
```

This avoids the previous RAM spike from building one huge `--scope all --max-windows 0` hybrid matrix. It builds feature rows in chunks, scores the hybrid head, simulates the Phase125 TP/SL rule, and writes the same HTML/JSON/CSV outputs.

Recommended first full command:

```powershell
python -u scripts/report_hybrid_full_backtest.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 1000 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

`stream-wavenet=neutral` is the RAM-safe default and fills WaveNet features with a neutral 1/3 vector. This is acceptable for the first full diagnostic because the WaveNet branch previously showed no edge/collapse. If exact WaveNet outputs are required later, use `--stream-wavenet batch` with a small chunk size, accepting slower/heavier execution.

## Full streamed 5M robustness result

The user ran the memory-safe streamed full-history diagnostic:

```text
source_mode=stream
stream_scope=all
stream_chunk_size=500
stream_wavenet=neutral
rows=52832
threshold=buy 0.80 / sell 0.65 / margin 0.05
```

Result:

```text
trades           : 13757
buy/sell         : 8583 / 5174
win_rate         : 41.2663%
label_precision  : 51.1085%
total_pnl        : -43309.811277104236
avg_pnl          : -3.1482017356330765
profit_factor    : 0.6215092452818565
max_drawdown     : 45887.011698256094
coverage         : 26.0391%
```

Sizing view with `initial_capital=100`, `units=0.1`:

```text
final_balance      : -4230.981127710424
max_drawdown_cash  : 4588.701169825609
would_breach_zero  : true
```

Interpretation:

```text
The Phase116 runtime integration reproduces Phase125 on the validated holdout,
but the single saved head + fixed Phase125 thresholds are not robust across the
full historical regime range. The correct next step is walk-forward validation.
Training on the entire dataset and backtesting on the same data would be in-sample leakage.
```
