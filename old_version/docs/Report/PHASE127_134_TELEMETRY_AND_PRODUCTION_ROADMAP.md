# Phase127–134 Roadmap — Telemetry Tensor, Meta Models, and Production Consolidation

Date: 2026-09-09

## Why this roadmap exists

The current useful model stack is:

```text
gold_range_1d
gold_range_4h
gold_buy_lightgbm_basic_5m
gold_sell_lightgbm_basic_5m
gold_trend_signal_lightgbm_basic_5m
gold_hybrid_lightgbm_head_5m
```

The hybrid head showed a positive, statistically significant holdout result, but the full-history streamed diagnostic failed. Therefore the next work must not jump to live execution. It must build a causal telemetry dataset, train meta-filters, and validate walk-forward.

## Phase order

```text
Phase126A — already implemented: chronological single-position replay
Phase127  — causal 3D telemetry tensor with Target C and safe_lag=48
Phase128  — LightGBM/CatBoost meta-labeler baseline
Phase129  — WaveNet/TCN on telemetry tensor
Phase130  — TSMixer benchmark
Phase131  — PatchTST benchmark
Phase132  — meta-filtered chronological backtest comparison
Phase133  — walk-forward out-of-time validation
Phase134  — production consolidation / online bot assembly
Phase115  — live decision audit / paper shadow after consolidation
```

## Key causal rule

At candle `i`, features may include only information available by that candle:

```text
candles <= i
model predictions computed from candles <= i
latest closed 4H/1D candles
trade telemetry whose outcome is already known
```

Backtest outcome telemetry must use:

```text
safe_lag = 48 bars
```

because the local range/TP/SL horizon is 4H:

```text
48 * 5 minutes = 4 hours
```

## Selected targets — Target C

```text
target_trade_win      = 1 if candidate trade pnl > 0 else 0
target_trade_score_r  = clip(realized_pnl / sl_distance, -3, +3)
target_trade_pnl      = realized pnl in price units
```

## Model order

First baseline:

```text
LightGBM/CatBoost meta-labeler
```

Then neural benchmarks:

```text
WaveNet/TCN
TSMixer
PatchTST
```

Image CNN/cat-dog style is not first priority because feature-column order is artificial and can create fake spatial patterns. Time-series-native models are preferred.

## Online bot consolidation

The user raised a valid concern: the research code is getting complex. Phase134 explicitly exists to collapse the winning path into a narrow production runtime:

```text
one selected model stack
one selected config
one online feature builder
one decision service
one paper/live audit schema
one guarded MT5 execution path
```

No production/live path should call training scripts, threshold-search scripts, or broad research utilities.
