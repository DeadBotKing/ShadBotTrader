# Phase127 — Causal 3D Hybrid Telemetry Tensor

**Status:** ✅ Phase127A implemented
**Type:** Dataset/tensor engineering, leakage-safe online-compatible features
**Priority:** next after Phase126A chronological replay result

---

## Goal

Build a new training dataset from the current useful models and from causal backtest telemetry, without leaking future trade outcomes into features.

Current useful model inputs:

```text
gold_range_1d
gold_range_4h
gold_buy_lightgbm_basic_5m
gold_sell_lightgbm_basic_5m
gold_trend_signal_lightgbm_basic_5m
gold_hybrid_lightgbm_head_5m
```

The new matrix/tensor must be usable both in research and online mode.

---

## Core shape

Primary output is a 3D temporal tensor:

```text
X.shape = [samples, tensor_window, channels]
```

Recommended defaults:

```text
tensor_window = 288   # 24h of 5M candles
optional      = 150   # lighter experiment
safe_lag      = 48    # 4h = 48 * 5M bars
```

The third dimension is not image RGB. It is the feature/channel dimension:

```text
channel = 5M features + model probabilities + range context + lagged telemetry + aligned 4H/1D context
```

---

## Outputs

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_v1.npz
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
run_logs/hybrid_telemetry_tensor/latest.json
```

NPZ fields:

```text
X                       [N, window, channels]
target_trade_win        [N]
target_trade_score_r    [N]
target_trade_pnl        [N]
target_side             [N]
candidate_mask          [N]
source_index            [N]
timestamp               [N]
channel_names           [C]
```

---

## Target C — selected target set

The selected target set is C: build all targets.

### `target_trade_win`

```text
1 = candidate trade PnL > 0
0 = candidate trade PnL <= 0
```

Purpose:

```text
meta-label classifier: execute or skip this candidate?
```

### `target_trade_score_r`

```text
target_trade_score_r = clip(realized_pnl / sl_distance, -3, +3)
```

Purpose:

```text
continuous expected trade quality / R-multiple
```

### `target_trade_pnl`

```text
target_trade_pnl = realized pnl in XAUUSD price units
```

Purpose:

```text
analysis/ranking/calibration, not the first training objective
```

---

## Causal rule — critical

Forbidden:

```text
Using the outcome of a trade opened at candle i as a feature for candle i.
```

Allowed at candle `i`:

```text
- candles/features known up to i
- model predictions computed using data <= i
- range forecasts based on latest closed 4H/1D candle
- closed-trade/backtest telemetry whose outcome is known before i
```

Default lag rule:

```text
Only virtual-trade outcomes with source_index <= i - 48 can be feature inputs.
```

Stricter optional rule:

```text
Only outcomes with exit_index < i can be feature inputs.
```

Why 48?

```text
range_4h horizon = 4h = 48 candles of 5M.
```

---

## Feature groups

### 5M compact features

Do not dump the entire huge feature catalog into the first tensor. Start compact:

```text
5m_return_1
5m_body_pct
5m_range_pct
5m_upper_wick_pct
5m_lower_wick_pct
5m_close_position
5m_atr_proxy
session/time features
```

### Model output features

```text
buy_specialist_prob
sell_specialist_prob
specialist_buy_minus_sell
specialist_conflict
booster_sell_prob
booster_hold_prob
booster_buy_prob
booster_entropy
hybrid_sell_prob
hybrid_hold_prob
hybrid_buy_prob
hybrid_action_margin
```

### Range/bracket features

```text
range_1d_high
range_1d_low
range_1d_up_room
range_1d_down_room
range_1d_width
range_4h_high
range_4h_low
range_4h_up_room
range_4h_down_room
range_4h_width
tp_distance
sl_distance
reward_risk
```

### Lagged backtest telemetry

Only lagged/known outcomes:

```text
rolling_12_trades_win_rate_lag48
rolling_24_trades_win_rate_lag48
rolling_48_trades_win_rate_lag48
rolling_12_trades_avg_pnl_lag48
rolling_24_trades_avg_pnl_lag48
rolling_profit_factor_lag48
rolling_tp_rate_lag48
rolling_sl_rate_lag48
rolling_timeout_rate_lag48
last_closed_trade_pnl_lag48
bars_since_last_closed_trade
recent_buy_win_rate_lag48
recent_sell_win_rate_lag48
```

### Aligned 4H/1D context in channel dimension

Use only latest closed higher-timeframe candle:

```text
4H close_time <= 5M candle time
1D close_time <= 5M candle time
```

Suggested channels:

```text
4h_return_1
4h_body_pct
4h_range_pct
4h_close_position
4h_atr_proxy
4h_last_closed_age_5m
1d_return_1
1d_body_pct
1d_range_pct
1d_close_position
1d_atr_proxy
1d_last_closed_age_5m
```

---

## What to exclude in v1

```text
- full raw feature catalog dump
- thousands of tabular summary features
- unlagged outcome telemetry
- price-level raw values without normalization/context
- anything not available in live mode
```

---

## Acceptance criteria

```text
- Tensor shape and channel names are written to JSON.
- Target C is present.
- safe_lag=48 is enforced by tests.
- Higher timeframe features use latest closed candles only.
- A flat parquet projection exists for LightGBM baseline.
- Output can be built in chunks without RAM spike.
- No future outcome is present as a same-row feature.
```

---

## Next phase

```text
Phase128 — LightGBM/CatBoost meta-labeler baseline on the flat telemetry projection.
```

---

## GUI/operator execution requirement

هر چیزی که در این فاز ساخته می‌شود و قرار است اپراتور اجرا کند، باید همزمان GUI/Dashboard command داشته باشد. فقط CLI کافی نیست.

برای این فاز، حداقل GUI باید اضافه کند:

```text
CommandKind.BUILD_HYBRID_TELEMETRY_TENSOR
Dashboard label: Build hybrid telemetry tensor
Handler: runs scripts/build_hybrid_telemetry_tensor.py
```

Dashboard باید فیلدهای اصلی را نشان دهد:

```text
symbol
timeframe
tensor_window
safe_lag_bars
telemetry_lag_mode
source_mode/chunk_size
include_4h_context
include_1d_context
target_set = C
storage_root
```

تست الزامی:

```text
tests/unit/presentation/test_architecture_knobs_gui.py
```

باید ثابت کند command در GUI وجود دارد و همهٔ flagهای مهم به script پاس می‌شوند.

---

## Phase127A implementation status

Implemented file:

```text
scripts/build_hybrid_telemetry_tensor.py
```

GUI command:

```text
Build hybrid telemetry tensor
```

Tests:

```text
tests/unit/ai/test_hybrid_telemetry_tensor.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Implemented outputs:

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_v1.npz
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
run_logs/hybrid_telemetry_tensor/latest.json
```

Implemented modes:

```text
source-mode=matrix  # safest first run, uses existing hybrid matrix
source-mode=stream  # chunked row construction, memory safer than one huge matrix
```

Important RAM guard:

```text
--max-tensor-mb
```

If requested tensor exceeds this estimate, the script refuses and tells the operator to use a larger sample stride, smaller tensor window, max samples, or a higher memory limit.

---

## Bugfix after first operator run — 2026-09-10

اولین اجرای matrix-mode کاربر با خطای زیر شکست خورد:

```text
TypeError: '<' not supported between instances of 'str' and 'datetime.datetime'
```

علت:

```text
matrix timestampها string بودند، اما latest closed 4H/1D context با datetime end_times مقایسه می‌شد.
```

رفع:

```text
build_htf_lookup -> end_times as UTC pandas Timestamp
latest_closed    -> converts input timestamp with comparable_timestamp()
```

تست اضافه شد:

```text
test_latest_closed_accepts_iso_timestamp_strings
```

کاربر باید Phase127A matrix-mode را دوباره اجرا کند.

---

## Matrix-mode execution result — 2026-09-10

بعد از timestamp fix، کاربر Phase127A را با matrix-mode اجرا کرد:

```text
rows               : 8000
tensor_samples     : 7851
tensor_window      : 150
channels           : 94
tensor_shape       : [7851, 150, 94]
candidate_rows     : 2307
candidate_rate     : 28.8375%
target_win_rate    : 57.2605%
target_score_r_mean: +0.07910706847906113
target_pnl_sum     : +3714.10546875
safe_lag_bars      : 48
lag_mode           : fixed
warnings           : []
```

خروجی‌ها:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
```

نتیجه:

```text
PASS — tensor و flat projection ساخته شدند. گام بعدی Phase128A train/backtest است.
```

---

## Stream-mode bugfix after full-history operator run — 2026-09-12

Operator command:

```text
source_mode=stream
stream_scope=all
stream_chunk_size=500
stream_wavenet=neutral
sample_stride=5
max_samples=12000
tensor_window=150
safe_lag_bars=48
```

Observed failure after the first streamed chunk:

```text
stream rows : 500/52,832
[X] AttributeError: 'Namespace' object has no attribute 'same_bar_policy'
```

Cause:

```text
Phase127 reused simulate_trade() from the hybrid head backtester. simulate_trade() needs args.same_bar_policy, but the Phase127 parser did not define it.
```

Fix:

```text
scripts/build_hybrid_telemetry_tensor.py now defines:
  --same-bar-policy {stop_first,tp_first}, default=stop_first

Dashboard command updated:
  Build hybrid telemetry tensor -> Same-bar policy
```

Additional consistency fix:

```text
In stream mode, lagged trade telemetry is now recomputed once globally after all chunks are concatenated. This prevents lagged_trade_count / rolling win-rate features from resetting at each stream_chunk_size boundary.
```

Verification:

```text
Targeted ruff/black: PASS
Targeted Phase127 + GUI tests: 65 passed
Full pytest: 1760 passed, 54 skipped
Full ruff/black/mypy: still red from pre-existing repo debt, not from this patch.
```

Rerun command can be the same as before. Optional explicit field:

```powershell
--same-bar-policy stop_first
```

---

## Full stream telemetry execution result — 2026-09-12

After the same-bar-policy fix, the operator reran Phase127A in full stream mode:

```text
source_mode        : stream
stream_scope       : all
stream_chunk_size  : 500
stream_wavenet     : neutral
sample_stride      : 5
max_samples        : 12000
tensor_window      : 150
safe_lag_bars      : 48
same_bar_policy    : stop_first
```

Result:

```text
rows                  : 52832
tensor_samples        : 10537
tensor_shape          : [10537, 150, 94]
channels              : 94
candidate_rows        : 13757
candidate_rate        : 26.0391429436705%
target_win_rate       : 41.266265511512756%
target_score_r_mean   : -0.23007889091968536
target_pnl_sum        : -43309.8125
warnings              : []
```

Interpretation:

```text
PASS as a full-history telemetry build. The output now covers the full 52,832-row 5M stream.
The label distribution confirms the previously observed base-hybrid weakness on full history:
13,757 candidates, only 41.27% winners, negative mean R-score, and -43,309.81 raw PnL before position-size scaling.
This dataset is suitable for full-history Phase128 retraining and Phase133 walk-forward validation.
```
