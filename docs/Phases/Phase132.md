# Phase132 — Meta-Filtered Hybrid Chronological Backtest

**Status:** ✅ Phase132A implemented
**Type:** Strategy comparison / model selection by trading metrics
**Priority:** after Phase128 and at least one neural benchmark

---

## Goal

Compare the base hybrid head against meta-filtered variants in the same chronological single-position replay.

Base strategy:

```text
gold_hybrid_lightgbm_head_5m
+ Phase125 thresholds
+ range_1d/range_4h TP/SL
```

Meta-filtered strategy:

```text
base hybrid candidate
+ meta_win_prob / expected_score_r from Phase128/129/130/131
→ execute or skip
```

---

## Candidate filters

Potential models:

```text
gold_hybrid_meta_lightgbm_5m
gold_hybrid_score_lightgbm_5m
gold_hybrid_telemetry_wavenet_5m
gold_hybrid_telemetry_tsmixer_5m
gold_hybrid_telemetry_patchtst_5m
```

Potential gates:

```text
meta_win_prob >= 0.55 / 0.60 / 0.65
expected_score_r >= 0.05 / 0.10 / 0.20
combined: meta_win_prob and expected_score_r
```

---

## Backtest protocol

Use Phase126A chronological replay rules:

```text
one open position at a time
skip signals while position is open
same TP/SL and spread/slippage assumptions
same initial_capital and units
```

Do not compare independent-trade tests against chronological replay.

---

## Reports

```text
run_logs/hybrid_meta_backtest/latest.json
run_logs/hybrid_meta_backtest/latest.csv
run_logs/hybrid_meta_backtest/latest.html
```

Metrics:

```text
trades
coverage
win_rate
label_precision
total_pnl
avg_pnl
profit_factor
max_drawdown
final_balance
would_breach_zero
monthly pnl/PF
skipped_by_meta_filter
skipped_while_open
```

---

## Success condition

A meta-filter is useful only if it improves the base chronological result out-of-time:

```text
profit_factor higher
max_drawdown lower
final_balance better
monthly losses reduced
coverage not collapsed to nearly zero
```

A model with great precision but too few trades is not accepted unless the PnL/DD profile is clearly better.

---

## Acceptance criteria

```text
- Compares base hybrid vs every candidate meta-filter on identical periods.
- Uses chronological single-position replay.
- Produces HTML replay for the selected best candidate.
- Stores selected meta thresholds only if they pass out-of-time metrics.
```

---

## Next phase

```text
Phase133 — Walk-forward out-of-time validation.
```

---

## GUI/operator execution requirement

مقایسهٔ meta-filtered chronological backtest باید در Dashboard قابل اجرا و قابل مشاهده باشد.

حداقل command لازم:

```text
CommandKind.BACKTEST_META_FILTERED_HYBRID
Dashboard label: Backtest meta-filtered hybrid
Handler: runs scripts/backtest_meta_filtered_hybrid.py
```

فیلدهای مهم GUI:

```text
base_model_id
meta_model_id
score_model_id
meta_threshold
score_threshold
source_mode = matrix|stream
stream_chunk_size
initial_capital
units
same_bar_policy
storage_root
```

خروجی HTML/JSON/CSV باید از GUI قابل دسترسی باشد و تست descriptor/handler الزامی است.

---

## Phase132A implementation status

Implemented file:

```text
scripts/backtest_meta_filtered_hybrid.py
```

GUI command:

```text
Backtest meta-filtered hybrid
```

Tests:

```text
tests/unit/ai/test_meta_filtered_hybrid_comparison.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Capabilities:

```text
- compares base hybrid candidate replay vs multiple meta filters
- supports flat Phase128 models with payload['model']
- supports tensor Phase129/130/131 models with payload['model_bytes']
- candidate list is comma-separated
- optional candidate versions
- threshold grids: record and/or explicit meta thresholds
- decision modes for tensor models: meta|score|both
- same evaluation source rows for all candidates when tensor is available
- writes comparison CSV/JSON/HTML
- writes best_replay.html for the selected best candidate
- skips missing models by default so partial model sets can be compared
```

Outputs:

```text
run_logs/hybrid_meta_comparison/latest.json
run_logs/hybrid_meta_comparison/latest.csv
run_logs/hybrid_meta_comparison/latest.html
run_logs/hybrid_meta_comparison/best_replay.html
```

First recommended command after Phase128/129/130/131 models are trained:

```powershell
python -u scripts/backtest_meta_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --candidates base,gold_hybrid_meta_lightgbm_5m,gold_hybrid_telemetry_wavenet_5m,gold_hybrid_telemetry_tsmixer_5m,gold_hybrid_telemetry_patchtst_5m `
  --candidate-versions 0 `
  --decision-modes meta,both `
  --meta-thresholds record,0.55,0.60,0.65 `
  --score-thresholds 0,0.05,0.10 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --min-trades 10 `
  --score-metric total_pnl `
  --initial-capital 100 `
  --units 0.1 `
  --skip-missing 1 `
  --storage-root datasets
```

Important:

```text
Phase132 compares existing trained candidates. It does not train models.
If some model IDs do not exist yet, skip_missing=1 records them as skipped.
```

---

## Bugfix — 2026-09-10

اولین اجرای اپراتور برای Phase132A با خطای زیر متوقف شد:

```text
AttributeError: 'ComparisonRow' object has no attribute 'label_correct'
```

علت: `best_replay.html` می‌خواست `FixedBacktestSummary` را از `ComparisonRow` بازسازی کند، در حالی که `ComparisonRow` summary کامل نیست.

رفع:

```text
BestReplay now stores summary: FixedBacktestSummary
best_replay.html renders replay.summary directly
```

کاربر باید همان دستور Phase132A را دوباره اجرا کند.

---

## Operator comparison result — 2026-09-10

کاربر Phase132A را با `base,gold_hybrid_meta_lightgbm_5m` و threshold grid اجرا کرد.

Base:

```text
samples       : 7851
trades        : 219
win_rate      : 42.4658%
total_pnl     : +55.14647939801216
profit_factor : 1.0677528759144055
max_drawdown  : 98.2512731552124
coverage      : 2.7895%
```

Best meta:

```text
candidate      : gold_hybrid_meta_lightgbm_5m:meta:meta=record:score=0.0
version        : 1
meta_threshold : 0.55
trades         : 142
buy/sell       : 74 / 68
wins/losses    : 93 / 49
win_rate       : 65.4930%
total_pnl      : +502.82915729284286
profit_factor  : 2.5870741996012305
max_drawdown   : 91.44515466690063
coverage       : 1.8087%
final_balance  : 150.2829157292843
```

Threshold grid:

```text
0.55/record : +502.8292 PF=2.5871 trades=142 DD=91.4452
0.60        : +488.5258 PF=2.5521 trades=140 DD=91.4452
0.65        : +481.7925 PF=2.5413 trades=138 DD=89.2924
0.70        : +467.5121 PF=2.5073 trades=136 DD=89.2924
0.75        : +446.6142 PF=2.4499 trades=131 DD=89.2924
0.80        : +420.5321 PF=2.3652 trades=130 DD=89.2924
```

نتیجه:

```text
PASS as an in-dataset comparison. The meta-filter materially improves the 8000-row replay, but Phase133 walk-forward remains mandatory.
```
