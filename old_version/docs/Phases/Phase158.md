# Phase158A — Pivot Zone Candidate / Actionability Reframe Audit

## Status

```text
IMPLEMENTED — research/diagnostic only
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase157A showed that full-universe payoff targets are too sparse and HOLD-dominant:

```text
B4 actionable ≈ 4%
B2 actionable ≈ 3–4%
full 3-class baselines collapsed to always-HOLD
```

But Phase157A also showed high candidate-only BUY-vs-SELL AP. Therefore the bottleneck is not side ranking after a candidate exists; it is candidate/actionability discovery.

Phase158A reframes the problem:

```text
Do not ask the model to classify every 5M row as SELL/HOLD/BUY.
First define live-known pivot-zone candidates.
Then audit payoff/actionability/side behavior inside that candidate universe.
```

## Implemented executable

```text
scripts/audit_pivot_zone_candidate_reframe.py
```

## GUI command

```text
Audit pivot-zone candidate reframe
```

## Candidate universe

For each sampled row:

```text
target_top_zone    → create one SELL candidate event
target_bottom_zone → create one BUY candidate event
```

If both top and bottom zone are true, both side-events are represented separately.

Each event stores:

```text
side       : SELL or BUY
score_r    : target_sell_trade_r or target_buy_trade_r
win        : score_r > 0
matched    : whether target_action equals that side
features   : sequence summary + side indicator
```

## Diagnostics

For each candidate target set, default B4 and B2:

```text
1. Zone-event counts by train/validation/test.
2. Event win rate and mean R by split.
3. Side-specific BUY/SELL win rate and mean R.
4. Validation-to-test mean-R sign flip.
5. Candidate event win learnability using centroid baseline.
6. Side preference stability between validation and test.
```

## Outputs

```text
run_logs\pivot_zone_candidate_reframe\latest.json
run_logs\pivot_zone_candidate_reframe\latest.html
run_logs\pivot_zone_candidate_reframe\latest_candidates.csv
run_logs\pivot_zone_candidate_reframe\latest_splits.csv
```

## Recommended PowerShell command

```powershell
python -u scripts\audit_pivot_zone_candidate_reframe.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --candidates B4,B2 `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --summary-mode basic `
  --chunk-size 512 `
  --min-validation-events 100 `
  --min-test-events 100 `
  --min-validation-mean-r 0 `
  --min-test-mean-r 0 `
  --min-event-ap-lift 0.03 `
  --min-event-balanced-accuracy 0.53 `
  --storage-root datasets `
  --output-dir run_logs\pivot_zone_candidate_reframe
```

## Gate interpretation

```text
enrichment_gate:
  enough validation/test zone events
  validation/test mean R positive
  no mean-R sign flip

event_learnability_gate:
  validation event-win AP improves over base rate
  validation balanced accuracy exceeds threshold

side_preference_stable_gate:
  validation best side and test best side agree

candidate_reframe_gate:
  all above gates pass
```

If Phase158A fails:

```text
The live-known pivot-zone candidate universe is not stable enough.
Do not train another deep model.
```

If Phase158A passes:

```text
The next phase can build a two-stage candidate model:
  candidate-zone filter / event scorer
  side/payoff scorer inside the candidate universe
```

## Execution result

The owner ran Phase158A on B4/B2.

Top-level result:

```text
completed_candidates     : 2
reframe_ready_candidates : 0
best_candidate_id        : B2
best_candidate_reason    : no gate pass; best diagnostic score only
```

B4:

```text
validation zone_event_rate : 90.5025%
test zone_event_rate       : 89.0931%
validation event_win_rate  : 5.3487%
test event_win_rate        : 4.8831%
validation event_mean_r    : -0.0680433
test event_mean_r          : -0.0689477
validation best side       : SELL
test best side             : BUY
candidate_reframe_gate     : 0
```

B2:

```text
validation zone_event_rate : 70.2206%
test zone_event_rate       : 69.0870%
validation event_win_rate  : 5.9773%
test event_win_rate        : 5.1885%
validation event_mean_r    : -0.0272688
test event_mean_r          : -0.0402439
validation best side       : SELL
test best side             : BUY
candidate_reframe_gate     : 0
```

Decision:

```text
Phase158A failed.
Current pivot-zone candidate definitions are too broad and negative-expectancy.
Do not train another deep model on this candidate universe.
```

Recommended next phase:

```text
Phase159A — Pivot Candidate Geometry Tightening Audit
```

## Verification

```text
python -m py_compile scripts/audit_pivot_zone_candidate_reframe.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_zone_candidate_reframe.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_zone_candidate_reframe.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 52 passed
```
