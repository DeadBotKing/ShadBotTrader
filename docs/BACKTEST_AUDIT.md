# Backtest Audit Pipeline

## Stage 1 — Causality audit

The standard catalogue contains 109 definitions. The model/live path blocks 53:

- 9 future target shifts;
- 8 full-series wavelet filters;
- 16 full-series Fourier features;
- 7 batch PCA features;
- `chikou` with a future shift;
- 12 divergence features using centered future extrema.

The remaining model input is:

```text
14 raw/derived candle columns + 56 causal catalogue columns = 70 columns
```

The definitions remain in the research catalogue. `causal_only=True` excludes them from training, live matrices and model-driven backtests, and records the reason in `FeatureMatrix.excluded_features`.

`Audit causal features` in the dashboard prints the allow/block report without computing or deleting anything.

## Stage 2 — Causal matrix

Training and inference now build the matrix with the same causal filter. A model trained before this change with 123 input columns is incompatible and must be retrained; the schema check refuses a silent mismatch.

## Stage 3 — Transformers

Full-series PCA/Fourier are not fitted in the model path. They remain research-only. A future stateful transformer may fit on the training prefix and transform validation/test, but it must carry its fitted state with the model artifact before returning to production.

## Stage 4 — Purged walk-forward validation

Expanding folds now accept `purge_gap`. Model training uses at least `window_size - 1` gap between the last training window and the first validation window; finite-horizon range targets add the range horizon. This prevents adjacent stride-one windows from sharing input candles across the boundary.

## Stage 5 — Independent chronological test

The dashboard backtest exposes:

```text
Test holdout % (0 = all)
```

For example, `20` trades only the final 20% of the signal history. To make that a genuine unseen test, train the model with `Training prefix % = 80` first, then backtest with `Test holdout % = 20`.

## Stage 6/7 — Execution and costs

Bracket triggers account for executable bid/ask around candle mid high/low. Reports now separate:

- commission fees;
- spread cost;
- adverse slippage cost.

The dashboard and replay show initial equity, final equity, gross profit/loss before commission, net profit/loss after the complete round-trip commission, profit factor, net profit factor, expectancy, fees, spread and slippage. Entry and exit commissions are now both attached to the same `TradeRecord` and replay round-trip, so the trade statistics reconcile with final equity.

## Accounting reconciliation

A round trip pays commission on both the entry and the exit. The engine now
keeps both amounts on the same `TradeRecord` and the same replay round trip.
Therefore, when the tape ends flat:

```text
sum(net trade PnL) == final_equity - initial_equity
```

The dashboard reports gross PnL before commission, net PnL after complete
commission, and cost decomposition separately. An old result generated before
this correction must be rerun; its old expectancy/profit-factor fields may have
omitted entry commission.

## Replay consistency

`Run a backtest` records the exact tape and validates:

```text
engine final equity == replay final equity
engine closed trades == replay closed trades
```

If either check fails, the command fails and does not publish a misleading replay. `Record a replay` reuses the exact last tape by default.
