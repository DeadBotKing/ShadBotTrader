# Phase152 — Pivot Label / Target Stability Audit

**Status:** ✅ Phase152A implemented  
**Type:** Research-only label/target stability diagnostic  
**Production status:** BLOCKED — no paper/live

## Why this phase exists

Phase151A showed that raw Option B does not transfer from validation to test across seeds. Before training more models, we need to audit the target definitions themselves:

```text
Are pivot labels stable across train/validation/test?
Do BUY/SELL/top/bottom labels drift by month?
Do buy_r/sell_r distributions change by regime?
Are current pivot label parameters too regime-specific?
```

## Implemented script

```text
scripts/audit_pivot_label_target_stability.py
```

GUI command:

```text
Audit pivot label/target stability
```

## Inputs

Default flat file:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
```

Optional meta file to audit the exact sampled tensor universe:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
```

## What it audits

```text
- action label distribution: SELL/HOLD/BUY
- top_zone / bottom_zone rates
- future_up_r and future_down_r distribution
- target_buy_r and target_sell_r distribution
- train / validation / test drift
- monthly drift
- PSI vs train for action distribution
- sensitivity to label parameters:
  lookahead_bars
  pivot_move_atr
  pivot_zone_atr
  min_direction_edge
```

## Outputs

```text
run_logs\pivot_label_target_stability\latest.json
run_logs\pivot_label_target_stability\latest.html
run_logs\pivot_label_target_stability\latest_splits.csv
run_logs\pivot_label_target_stability\latest_monthly.csv
run_logs\pivot_label_target_stability\latest_sensitivity.csv
```

## Recommended command

```powershell
python -u scripts\audit_pivot_label_target_stability.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --window-size 100 `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --sensitivity-lookahead-bars 24,48,72 `
  --sensitivity-pivot-move-atrs 0.5,0.75,1.0 `
  --sensitivity-pivot-zone-atrs 0.25,0.35,0.5 `
  --sensitivity-min-direction-edges 1.0,1.1,1.25 `
  --max-sensitivity-combinations 40 `
  --psi-warning-threshold 0.20 `
  --storage-root datasets `
  --output-dir run_logs\pivot_label_target_stability `
  --report-title "Phase152A pivot label target stability audit"
```

## Anti-overfit rule

This phase is diagnostic. It does not approve a strategy. If labels are unstable, future work should redesign targets before more model training.

## Verification

```text
python -m py_compile scripts/audit_pivot_label_target_stability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py

python -m pytest tests/unit/ai/test_pivot_label_target_stability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
```

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```

## Phase152A result — action labels stable, payoff targets drift by regime — 2026-09-21

The owner ran Phase152A on the exact Option B 24k sampled universe from `pivot_pattern_sequence_tensor_latest_meta.npz`.

Input/universe:

```text
flat_path        : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
meta_path        : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
sampled_universe : meta_sample_indices
flat_rows        : 53197
sampled_rows     : 24000
train/val/test   : 16800 / 3264 / 3264
period           : 2025-11-28 17:05:00+00:00 → 2026-08-06 19:20:00+00:00
```

Current label config:

```text
lookahead_bars     : 48
pivot_move_atr     : 0.75
pivot_zone_atr     : 0.35
recent_window_bars : 48
min_direction_edge : 1.10
```

Current target counts:

```text
SELL : 2411
HOLD : 19605
BUY  : 1984
```

Action-label distribution by split:

```text
Train      SELL=10.1369%  HOLD=82.0357%  BUY=7.8274%
Validation SELL= 9.1299%  HOLD=82.9044%  BUY=7.9657%
Test       SELL=10.7537%  HOLD=78.6765%  BUY=10.5699%
```

Action-label drift:

```text
validation_psi_vs_train = 0.0011693337
test_psi_vs_train       = 0.0100065951
```

Interpretation:

```text
The action labels themselves are not showing severe split-level drift. SELL/HOLD/BUY proportions are broadly stable from train to validation/test. The very high `max_monthly_psi_vs_train=2.0860` comes from 2025-11, which is only a tiny partial month at the start of the sampled window and should not be overinterpreted alone.
```

The important target drift is in the payoff targets:

```text
Top sensitivity rows show:
train_buy_r_mean      ≈ -0.0352
validation_buy_r_mean ≈ -0.0586
test_buy_r_mean       ≈ +0.0167

train_sell_r_mean      ≈ +0.0352
validation_sell_r_mean ≈ +0.0586
test_sell_r_mean       ≈ -0.0167
```

Interpretation:

```text
The market regime flips from train/validation being slightly SELL-favorable to test being slightly BUY-favorable in the continuous R targets, even though categorical label counts look stable. This explains the repeated pattern:
validation SELL edge looks good, then test SELL edge fails.
```

Sensitivity result:

```text
Most stable label configs are dominated by lookahead_bars=24 rather than the current 48.
The lowest drift row:
  lookahead_bars      : 24
  pivot_move_atr      : 0.75
  pivot_zone_atr      : 0.25
  min_direction_edge  : 1.0
  train actionable    : 6.6845%
  validation actionable: 6.8627%
  test actionable      : 7.6593%
  drift_score          : 0.1591275985

A denser but still stable candidate:
  lookahead_bars      : 24
  pivot_move_atr      : 0.5
  pivot_zone_atr      : 0.5
  min_direction_edge  : 1.25
  train actionable    : 23.7381%
  validation actionable: 23.0392%
  test actionable      : 26.8689%
  drift_score          : 0.1592708572
```

Decision:

```text
Phase152A does not approve any strategy.
It shows the current label counts are reasonably stable, but the payoff/R-target regime changes sign between validation and test.
More blind training of the same target is not justified.
```

Recommended next phase:

```text
Phase153A — Pivot Target Redesign Candidate Build/Audit
```

Recommended target candidates:

```text
Candidate C1 conservative:
  lookahead_bars     = 24
  pivot_move_atr     = 0.75
  pivot_zone_atr     = 0.25
  min_direction_edge = 1.0
  Expected: fewer but more stable actionable labels.

Candidate C2 denser stable:
  lookahead_bars     = 24
  pivot_move_atr     = 0.5
  pivot_zone_atr     = 0.5
  min_direction_edge = 1.25
  Expected: more actionable labels while keeping low drift.
```

Required anti-overfit rule:

```text
Build tensors for C1/C2, run health audits, train only as diagnostic, and evaluate validation/test transfer. Do not tune on test. No Phase134/paper/live.
```
