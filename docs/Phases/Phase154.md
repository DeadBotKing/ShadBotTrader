# Phase154A — Pivot Payoff / Trade-Outcome Target Redesign Audit

## Status

```text
IMPLEMENTED — research/diagnostic only
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase153A built C1/C2 target tensors and proved that label-count stability alone is not enough:

```text
C1/C2 tensor health: PASS
C1/C2 label PSI   : PASS
C1/C2 payoff/R sign flip: still present
training_ready_candidates: 0
```

Therefore the next target redesign must change the payoff/trade-outcome definition itself, not only the pivot zone/action-label density.

## Implemented executable

```text
scripts/audit_pivot_payoff_target_redesign.py
```

## GUI command

```text
Audit pivot payoff target redesign
```

## Target idea

Instead of assigning BUY/SELL from only future max/min magnitude, Phase154A audits first-hit/barrier trade-outcome targets:

```text
BUY target wins  if upside TP barrier hits before downside SL barrier.
SELL target wins if downside TP barrier hits before upside SL barrier.
HOLD if neither side wins, the side is not near the pivot zone, or the score edge is insufficient.
```

For each row, Phase154A computes two hypothetical trade scores:

```text
target_buy_trade_r
target_sell_trade_r
```

These are measured in ATR units:

```text
+tp_atr  if target barrier hits first
-sl_atr  if stop barrier hits first
0        if timeout with timeout_score_mode=zero
```

## Default candidate grid

Candidate format:

```text
ID:label:lookahead_bars:pivot_zone_atr:tp_atr:sl_atr:min_score_edge
```

Default candidates:

```text
B1:balanced_24_rr1:24:0.35:0.75:0.75:0.0
B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1
B3:dense_24_half_atr:24:0.50:0.50:0.50:0.0
B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1
B5:short_12_rr1:12:0.35:0.75:0.75:0.0
B6:wide_36_rr1:36:0.35:0.75:0.75:0.0
```

## Outputs

```text
run_logs\pivot_payoff_target_redesign\latest.json
run_logs\pivot_payoff_target_redesign\latest.html
run_logs\pivot_payoff_target_redesign\latest_candidates.csv
run_logs\pivot_payoff_target_redesign\latest_splits.csv
run_logs\pivot_payoff_target_redesign\latest_monthly.csv
```

## Gate logic

Per candidate, the audit reports:

```text
label_stability_pass_gate
payoff_stability_pass_gate
candidate_ready_for_tensor_gate
buy_score_sign_flip
sell_score_sign_flip
```

Candidate is ready for tensor build/training only if:

```text
label PSI is stable
train/validation/test actionable rates are not too sparse
buy/sell trade-outcome score means do not flip sign from validation to test
```

## Recommended PowerShell command

```powershell
python -u scripts\audit_pivot_payoff_target_redesign.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --candidates "B1:balanced_24_rr1:24:0.35:0.75:0.75:0.0;B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1;B3:dense_24_half_atr:24:0.50:0.50:0.50:0.0;B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1;B5:short_12_rr1:12:0.35:0.75:0.75:0.0;B6:wide_36_rr1:36:0.35:0.75:0.75:0.0" `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --window-size 100 `
  --recent-window-bars 48 `
  --same-bar-policy stop_first `
  --timeout-score-mode zero `
  --psi-warning-threshold 0.20 `
  --min-train-actionable-rate 0.02 `
  --min-validation-actionable-rate 0.02 `
  --min-test-actionable-rate 0.02 `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_target_redesign `
  --report-title "Phase154A pivot payoff target redesign audit"
```

## Execution result

The owner ran Phase154A.

Top-level result:

```text
completed_candidates      : 6
label_stable_candidates   : 6
payoff_stable_candidates  : 2
tensor_ready_candidates   : 2
best_candidate_id         : B4
```

Training-ready candidates:

```text
B4 asym_24_tp1_sl05:
  lookahead_bars     : 24
  pivot_zone_atr     : 0.35
  tp_atr             : 1.0
  sl_atr             : 0.5
  min_score_edge     : 0.1
  actionable train/val/test : 3.8333% / 4.8407% / 4.3505%
  buy/sell score sign flip  : 0 / 0

B2 conservative_24_tp1_sl075:
  lookahead_bars     : 24
  pivot_zone_atr     : 0.25
  tp_atr             : 1.0
  sl_atr             : 0.75
  min_score_edge     : 0.1
  actionable train/val/test : 3.1607% / 4.1973% / 3.5846%
  buy/sell score sign flip  : 0 / 0
```

Rejected candidates due to payoff sign flip:

```text
B1, B3, B5, B6
```

## Decision

```text
Proceed to Phase155A with B4 first.
Keep B2 as conservative backup.
Do not train B1/B3/B5/B6 now.
```

Critical caveat:

```text
Phase154A is still a target audit, not a trained model/backtest proof.
No production/paper/live approval.
```

## Next phase

```text
Phase155A — Build payoff-target tensor + diagnostic Option B training for B4/B2
```

## Verification

Implemented and verified in sandbox:

```text
python -m py_compile scripts/audit_pivot_payoff_target_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 48 passed
```
