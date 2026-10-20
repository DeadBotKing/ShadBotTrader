# Causal features not used in range training

Source: `standard_feature_set()` in `src/ShadBotTrader/infrastructure/feature/standard_catalog.py`.

Counted on 2026-10-07 from the current catalogue:

```text
catalogue features          : 229
causal live features        : 176
used by range training      : 170 causal features + raw OHLCV
causal but not used by range: 6
non-causal, used by nobody  : 53
```

Range training uses `causal_only=True` and `model_role=range`. That keeps `ModelScope.BOTH` and `ModelScope.RANGE`. It drops non-causal features and signal-only features.

The matrix also always includes these candle-derived columns. They are not catalogue features:

```text
open_rel, high_rel, low_rel, close_rel, hl2_rel, hlc3_rel, ohlc4_rel, volume_raw_log
return_1, range_pct, body_pct, upper_wick_pct, lower_wick_pct, volume_log
```

## Causal features excluded from range training

These 6 are causal and live-compatible, but `model_scope=SIGNAL`. The range matrix records them as `model_scope=signal_not_for_range`.

- `session_asian`
- `session_london`
- `session_ny`
- `session_overlap`
- `hour_sin`
- `hour_cos`

They are session/clock features. The signal model can use them. The current 4H/1D range models do not.

They were not added to the new multistep model. Adding them would change the input contract, so a horizon result would no longer be comparable with `gold_range_4h` / `gold_range_1d`.

## Causal features used by range, not by signal

These 11 are causal and are used by range training. They are listed so they are not mistaken for missing features.

- `spana`
- `spanb`
- `tenkan`
- `kijun`
- `gaussian3_14`
- `hurst_20`
- `fractal_dim_20`
- `vol_of_vol`
- `decycler`
- `rolling_sharpe`
- `rolling_calmar`

## Non-causal features excluded from all training

These are not causal. They are excluded because `is_live_compatible` is false. They are not the unused-causal list, but they are the other features the trainer refuses.

### FULL_SERIES_WAVELET (8)

- `open_filter`
- `close_filter`
- `low_filter`
- `high_filter`
- `hl2_filter`
- `hlc3_filter`
- `hlcc4_filter`
- `ohlc4_filter`

### FUTURE_SHIFT (1)

- `chikou`

### FUTURE_VALUE (9)

- `open_target_p1`
- `close_target_p1`
- `low_target_p1`
- `high_target_p1`
- `hl2_target_p1`
- `hlc3_target_p1`
- `hlcc4_target_p1`
- `ohlc4_target_p1`
- `volume_target_p1`

### FULL_SERIES_FOURIER_FIT (16)

- `sin_open`
- `cos_open`
- `sin_close`
- `cos_close`
- `sin_low`
- `cos_low`
- `sin_high`
- `cos_high`
- `sin_hl2`
- `cos_hl2`
- `sin_hlc3`
- `cos_hlc3`
- `sin_hlcc4`
- `cos_hlcc4`
- `sin_ohlc4`
- `cos_ohlc4`

### FULL_SERIES_PCA_FIT (7)

- `pca0`
- `pca1`
- `pca2`
- `pca3`
- `pca4`
- `pca5`
- `pca6`

### CENTERED_FUTURE_EXTREMA (12)

- `macdh_buy_primary`
- `macdh_buy_secondry`
- `macds_sell_secondry`
- `macd_sell_primary`
- `stochastic_d_buy_primary`
- `stochastic_k_sell_secondry`
- `stochastic_k_sell_primary`
- `stochastic_k_buy_secondry`
- `rsi_buy_primary`
- `rsi_sell_secondry`
- `rsi_sell_primary`
- `rsi_buy_secondry`

