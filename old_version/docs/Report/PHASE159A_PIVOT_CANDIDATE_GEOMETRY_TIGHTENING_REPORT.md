# PHASE159A — Pivot Candidate Geometry Tightening Audit Report

## Summary

Phase159A has been implemented to tighten live-known pivot candidate geometry after Phase158A showed the current zone definitions are too broad and negative-expectancy.

This phase does not train a model. It searches candidate geometry policies and evaluates first-hit payoff outcomes directly.

## Implemented files

```text
scripts/audit_pivot_candidate_geometry_tightening.py
tests/unit/ai/test_pivot_candidate_geometry_tightening.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_CANDIDATE_GEOMETRY_TIGHTENING
GUI label: Audit pivot candidate geometry tightening
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Method

Input:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
```

Optional sampled universe comes from:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
```

For each policy:

```text
1. Build live-known top/bottom geometry masks.
2. Score SELL events at top candidates and BUY events at bottom candidates using first-hit payoff rules.
3. Compute train/validation/test event count, event rate, mean R, profit factor and side preference.
4. Rank policies by validation only while reporting test confirmation.
```

## Outputs

```text
run_logs\pivot_candidate_geometry_tightening\latest.json
run_logs\pivot_candidate_geometry_tightening\latest.html
run_logs\pivot_candidate_geometry_tightening\latest_grid.csv
```

## Verification

```text
python -m py_compile scripts/audit_pivot_candidate_geometry_tightening.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_candidate_geometry_tightening.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_candidate_geometry_tightening.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 52 passed
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
