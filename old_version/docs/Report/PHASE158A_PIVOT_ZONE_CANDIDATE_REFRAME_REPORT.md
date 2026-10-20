# PHASE158A — Pivot Zone Candidate / Actionability Reframe Audit Report

## Summary

Phase158A has been implemented to reframe the pivot payoff problem around a live-known candidate universe instead of full-universe SELL/HOLD/BUY classification.

This phase is diagnostic only and does not train a production model.

## Implemented files

```text
scripts/audit_pivot_zone_candidate_reframe.py
tests/unit/ai/test_pivot_zone_candidate_reframe.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_ZONE_CANDIDATE_REFRAME
GUI label: Audit pivot-zone candidate reframe
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Method

The script consumes the payoff target tensors from Phase155A:

```text
pivot_payoff_sequence_tensor_b4_latest
pivot_payoff_sequence_tensor_b2_latest
```

It uses target metadata created by the payoff target builder:

```text
target_top_zone
target_bottom_zone
target_buy_trade_r
target_sell_trade_r
target_action
```

Candidate-event construction:

```text
If target_top_zone == 1:
  create SELL candidate event with score target_sell_trade_r

If target_bottom_zone == 1:
  create BUY candidate event with score target_buy_trade_r
```

The audit then reports event count, event win rate, event mean R, side-specific statistics, and transparent centroid-baseline learnability.

## Outputs

```text
run_logs\pivot_zone_candidate_reframe\latest.json
run_logs\pivot_zone_candidate_reframe\latest.html
run_logs\pivot_zone_candidate_reframe\latest_candidates.csv
run_logs\pivot_zone_candidate_reframe\latest_splits.csv
```

## Recommended command

```powershell
python -u scripts\audit_pivot_zone_candidate_reframe.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --candidates B4,B2 `
  --max-samples 24000 `
  --summary-mode basic `
  --storage-root datasets `
  --output-dir run_logs\pivot_zone_candidate_reframe
```

## Verification

```text
python -m py_compile scripts/audit_pivot_zone_candidate_reframe.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_zone_candidate_reframe.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_zone_candidate_reframe.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 52 passed
```

Full ruff/black unavailable in this sandbox image:

```text
No module named ruff
No module named black
```

## Production status

```text
BLOCKED — diagnostic only
No Phase134.
No paper shadow.
No live trading.
```
