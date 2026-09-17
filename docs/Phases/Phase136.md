# Phase136 — Tensor Failure / Regime Diagnostics

**Status:** ✅ Phase136A implemented
**Type:** Research diagnostic / failure analysis
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

Phase133B and Phase133C proved that the 3D tensor + WaveNet path is not robust enough yet:

```text
Phase133B tensor WF : -409.5199 raw PnL, PF=0.5979
Phase133C tensor WF :  -32.8330 raw PnL, PF=0.7655
```

Phase133C reduced losses through a validation no-trade gate, but did not create a profitable edge.

The next engineering question is no longer:

```text
Can a bigger WaveNet train longer?
```

It is:

```text
Where and why does validation-to-test transfer fail?
```

---

## Implemented file

```text
scripts/analyze_tensor_failure_regimes.py
```

GUI command:

```text
Analyze tensor failure regimes
```

---

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
run_logs\hybrid_tensor_walk_forward_validation\latest.json
```

The flat telemetry contains candidate outcome/regime features. The walk-forward JSON contains Phase133B/C fold-level validation-to-test transfer.

---

## What it analyzes

Phase136A produces:

```text
- validation-to-test transfer table
- month candidate distribution
- side BUY/SELL candidate distribution
- month × side distribution
- session/hour distribution
- side × hour distribution
- range_4h / range_1d side-aware room bins
- candidate_confidence bins
- candidate_reward_risk bins
- TP/SL distance bins
- booster entropy / margin bins
- specialist conflict buckets
- worst and best candidate regimes
```

Important:

```text
Regime rows are candidate-outcome diagnostics, not chronological replay. They help generate hypotheses; they do not approve a live filter by themselves.
```

---

## Outputs

```text
run_logs\tensor_failure_regimes\latest.json
run_logs\tensor_failure_regimes\latest.html
run_logs\tensor_failure_regimes\latest_regimes.csv
run_logs\tensor_failure_regimes\latest_transfer.csv
```

---

## First command

```powershell
python -u scripts/analyze_tensor_failure_regimes.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --walk-forward-json run_logs\hybrid_tensor_walk_forward_validation\latest.json `
  --candidate-only 1 `
  --min-group-rows 20 `
  --top-n 12 `
  --quantile-bins 5 `
  --storage-root datasets
```

Send back:

```text
run_logs\tensor_failure_regimes\latest.json
```

Open:

```text
run_logs\tensor_failure_regimes\latest.html
```

---

## Pass/fail interpretation

Phase136A itself is not a pass/fail trading gate. It is a diagnostic gate.

A useful Phase136A output should identify clear candidate hypotheses such as:

```text
SELL-only vs BUY-only edge difference
session/hour failure concentration
range-room failure concentration
specialist conflict failure concentration
validation-positive / test-negative fold pattern
```

If no stable hypothesis appears, the current model path should not continue with larger training runs.

---

## Operator result — 2026-09-14

Phase136A was executed on the full candidate telemetry matrix and the latest Phase133C walk-forward JSON.

Top-level result:

```text
candidate_rows : 13757
months         : 10
total_pnl      : -43309.811259036884
win_rate       : 41.2663%
profit_factor  : 0.6215092452270718
worst_month    : 2026-02
best_month     : 2026-07
```

Transfer summary:

```text
transfer_rows          : 6
transfer_total_pnl     : -32.83297738432884
transfer_profit_factor : 0.7655299301860462
no_trade_months        : 3
```

Risk flags:

```text
- 1 fold had positive validation quality but negative test PnL.
- 3 folds were blocked by validation no-trade gates.
- 1 active trading fold still lost after gates.
- BUY side is heavily negative: -39003.71 raw PnL.
- SELL side is also negative overall: -4306.10 raw PnL, but much less bad than BUY.
```

Most important finding:

```text
The base hybrid candidate stream is primarily damaged by BUY candidates and stop-loss concentration.
```

Worst regimes:

```text
stop_loss outcome share: 52.7441%, total_pnl=-106988.0392
BUY side: total_pnl=-39003.7073, PF=0.5106
2026-02: total_pnl=-21573.3665, PF=0.3872
large SL distance bin: total_pnl=-22248.0623
wide 1D/4H range-width bins: strongly negative
high candidate_confidence bin: -14063.6031
```

Potential positive pockets:

```text
2026-04 / SELL: +2682.8371, PF=2.1863
2026-03 / SELL: +2308.4453, PF=1.8384
2026-07 / SELL: +1963.2321, PF=1.4834
2026-06 / SELL: +669.4895, PF=1.2756
2026-08 / SELL: +469.5280, PF=1.6627
SELL / hour=9: +901.0482, PF=1.8986
SELL / hour=8: +640.0451, PF=1.3392
```

Decision:

```text
Phase136A generated a clear hypothesis: block or heavily penalize BUY candidates and test SELL-focused live-safe filters. This hypothesis must be validated through chronological replay/walk-forward before any production discussion.
```
