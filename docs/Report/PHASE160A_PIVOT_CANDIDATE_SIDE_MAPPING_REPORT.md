# PHASE160A — Pivot Candidate Side-Mapping / Counterfactual Direction Audit Report

## Summary

Phase160A has been implemented to test whether tightened pivot candidate geometry from Phase159A fails because of side mapping or entry timing.

It does not train a model. It evaluates counterfactual mappings and delays directly on candidate events.

## Implemented files

```text
scripts/audit_pivot_candidate_side_mapping.py
tests/unit/ai/test_pivot_candidate_side_mapping.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_CANDIDATE_SIDE_MAPPING
GUI label: Audit pivot candidate side mapping
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Method

The script consumes the Phase159A grid:

```text
run_logs\pivot_candidate_geometry_tightening\latest_grid.csv
```

Then for the top geometry policies it tests:

```text
reversal     : top→SELL, bottom→BUY
breakout     : top→BUY,  bottom→SELL
top_sell     : top→SELL only
bottom_buy   : bottom→BUY only
top_buy      : top→BUY only
bottom_sell  : bottom→SELL only
all_buy      : all events BUY
all_sell     : all events SELL
```

Entry delays:

```text
0,1,2,3 bars
```

## Outputs

```text
run_logs\pivot_candidate_side_mapping\latest.json
run_logs\pivot_candidate_side_mapping\latest.html
run_logs\pivot_candidate_side_mapping\latest_grid.csv
```

## Recommended command

```powershell
python -u scripts\audit_pivot_candidate_side_mapping.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --geometry-grid-path run_logs\pivot_candidate_geometry_tightening\latest_grid.csv `
  --max-geometry-policies 30 `
  --side-mappings reversal,breakout,top_sell,bottom_buy,top_buy,bottom_sell,all_buy,all_sell `
  --entry-delays 0,1,2,3 `
  --storage-root datasets `
  --output-dir run_logs\pivot_candidate_side_mapping
```

## Verification

```text
python -m py_compile scripts/audit_pivot_candidate_side_mapping.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_candidate_side_mapping.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_candidate_side_mapping.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 53 passed
```

Full ruff/black unavailable in sandbox:

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
