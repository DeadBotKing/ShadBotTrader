# Phase141 — Pivot Pattern Recognition Stack

**Status:** ✅ Phase141A implemented and executed
**Type:** Research model / top-bottom reversal-zone pattern recognition
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

After Phase140A showed that simple side flip and entry delay do not create a profitable strategy, the project moved to a new candidate-generation idea requested by the project owner:

```text
Build a Pattern Recognition model that learns top/bottom reversal zones:
- Where is price likely near a top before a downside move?
- Where is price likely near a bottom before an upside move?
- Where should the system stay flat?
```

This is not a patch on the old hybrid head. It is a research lane for a new candidate-generation concept.

---

## Implemented file

```text
scripts/train_pivot_pattern_recognition.py
```

GUI command:

```text
Train pivot pattern recognition
```

Test file:

```text
tests/unit/ai/test_pivot_pattern_recognition.py
```

---

## What the model learns

The model is trained with three classes:

```text
SELL = top_zone pattern
HOLD = no actionable pivot zone
BUY  = bottom_zone pattern
```

Target labels are made from future-only supervision, while input features remain causal:

```text
Input at 5M bar t:
  current closed 5M pattern features
  previous closed 4H context
  previous closed 1D context

Target after t:
  whether price moves down enough from a top zone
  whether price moves up enough from a bottom zone
  otherwise HOLD
```

Default label settings:

```text
lookahead_bars       : 48
pivot_move_atr       : 0.75
pivot_zone_atr       : 0.35
recent_window_bars   : 48
min_direction_edge   : 1.10
```

---

## Feature families checked

The script builds and ranks feature usefulness fold-by-fold using only the training slice.

Feature families:

```text
5M pattern:
  returns, candle body/range/wicks, ATR distance, RSI, EMA distances,
  position inside 24/48/96-bar ranges, distance from local high/low,
  price z-score and volatility.

4H context:
  previous closed 4H returns, candle shape, ATR, EMA distances,
  RSI, room-up/room-down.

1D context:
  previous closed 1D returns, candle shape, ATR, EMA distances,
  RSI, room-up/room-down.

Session/time:
  hour sin/cos, day-of-week sin/cos.
```

Top selected features from the first real run were mainly 5M local-structure features:

```text
m5_pos_in_range_48
m5_dist_high_48_atr
m5_dist_low_48_atr
m5_fast_mid_dist_atr
m5_price_z_96
m5_pos_in_range_24
m5_ret48
m5_close_mid_dist_atr
m5_ret24
m5_dist_high_24_atr
```

---

## Learner

Default mode:

```text
--model-kind auto
```

If `scikit-learn` is installed, auto uses:

```text
HistGradientBoostingClassifier
```

If sklearn is unavailable, the script falls back to a dependency-free trainable baseline:

```text
CentroidPatternModel
```

The recorded real run used:

```text
model_kind_used = sklearn_hgb
```

`requirements-boosters.txt` now includes `scikit-learn>=1.4` so the recorded run can be reproduced.

---

## Outputs

```text
run_logs\pivot_pattern_recognition\latest.json
run_logs\pivot_pattern_recognition\latest.html
run_logs\pivot_pattern_recognition\latest_folds.csv
run_logs\pivot_pattern_recognition\latest_trades.csv
run_logs\pivot_pattern_recognition\latest_features.csv
```

Research model artifact:

```text
datasets\models\gold_pivot_pattern_recognition_5m\v1_model.pkl
datasets\models\gold_pivot_pattern_recognition_5m\v1_training.json
```

---

## First real-data execution

Command executed:

```powershell
python -u scripts/train_pivot_pattern_recognition.py `
  --source-mode yahoo `
  --symbol XAUUSD `
  --yahoo-symbol GC=F `
  --daily-range 5y `
  --hourly-range 730d `
  --five-range 60d `
  --model-id gold_pivot_pattern_recognition_5m `
  --model-kind auto `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --max-features 38 `
  --train-days-min 20 `
  --validation-days 5 `
  --test-days 5 `
  --purge-hours 4 `
  --buy-thresholds 0.45,0.55,0.65 `
  --sell-thresholds 0.45,0.55,0.65 `
  --margins 0,0.05 `
  --tp-multipliers 0.75,1.0,1.25 `
  --sl-multipliers 0.50,0.75 `
  --hold-bars 24,48 `
  --min-validation-trades 5 `
  --score-metric net_profit `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --save-model 1 `
  --save-data 1 `
  --storage-root datasets
```

Data source:

```text
Yahoo Finance GC=F gold futures proxy
1D rows  : 1,258
4H rows  : 3,721, resampled from 1H
5M rows  : 13,509
```

Important limitation:

```text
GC=F is a public futures proxy, not broker-perfect Alpari XAUUSD.
Yahoo 5M data is only recent-window data, not multi-year 5M history.
```

---

## Real walk-forward result — 2026-09-16

```text
model_kind_used       : sklearn_hgb
feature_rows          : 13,509
feature_columns_total : 57
selected_features     : 38
target_counts         : SELL=1,368 / HOLD=10,764 / BUY=1,376
folds                 : 6
trades                : 102
BUY / SELL trades     : 40 / 62
wins / losses         : 45 / 57
win_rate              : 44.1176%
initial_balance       : $100.00
final_balance         : $86.7906
net_profit            : -$13.2094
return                : -13.2094%
profit_factor         : 0.6738
max_drawdown_cash     : $15.0879
positive_folds        : 0
negative_folds        : 6
```

Fold-level test result:

```text
Fold 1: test net=-2.6643 PF=0.5531 trades=11
Fold 2: test net=-0.3089 PF=0.9124 trades=11
Fold 3: test net=-3.1170 PF=0.5913 trades=12
Fold 4: test net=-2.7775 PF=0.6993 trades=34
Fold 5: test net=-4.1545 PF=0.1518 trades=12
Fold 6: test net=-0.1872 PF=0.9797 trades=22
```

---

## Decision

```text
Phase141A built the requested pattern-recognition model, but the real walk-forward result failed.
```

The model found meaningful-looking pivot labels and selected sensible 5M structure features, but validation choices did not transfer strongly enough into unseen test folds.

Production status remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

---

## Next engineering interpretation

The concept is better aligned with the owner's idea than the old hybrid-head patching path, but it needs better data and stronger validation before it can be useful.

Recommended next research work:

```text
1. Run Phase141A on broker-quality Alpari XAUUSD 5M/1H/4H/1D data.
2. Use at least 1-3 years of 5M data; Yahoo 5M is too short.
3. Test stricter pivot labels and no-trade gates.
4. Consider sequence encoders after label/feature validation:
   TCN / InceptionTime / PatchTST / CNN image branch.
5. Keep HOLD/no-trade as a first-class class.
```

---

## Operator rerun result — Yahoo GC=F — 2026-09-16

The operator reran Phase141A from Windows using the Yahoo/GC=F source.

Configuration:

```text
source_mode          : yahoo
market_symbol        : GC=F
1D rows              : 1,258
4H rows              : 3,722
5M rows              : 13,555
feature_rows         : 13,555
feature_columns      : 57
selected_features    : 38
model_kind_used      : sklearn_hgb
target_counts        : SELL=1,385 / HOLD=10,782 / BUY=1,387
```

Walk-forward result:

```text
folds                : 6
trades               : 92
BUY / SELL trades    : 39 / 53
wins / losses        : 33 / 59
win_rate             : 35.8696%
initial_balance      : $100.00
final_balance        : $79.0053
net_profit           : -$20.9947
return               : -20.9947%
profit_factor        : 0.5344
max_drawdown_cash    : $23.1522
positive_folds       : 0
negative_folds       : 6
```

Fold test results:

```text
Fold 1: net=-2.5993  PF=0.5655  trades=11
Fold 2: net=-0.0843  PF=0.9679  trades=10
Fold 3: net=-3.9539  PF=0.3038  trades=11
Fold 4: net=-9.1807  PF=0.4637  trades=30
Fold 5: net=-1.8003  PF=0.2853  trades=6
Fold 6: net=-3.3761  PF=0.6976  trades=24
```

Decision:

```text
The operator rerun confirms Phase141A still fails as a strategy on public Yahoo/GC=F data.
$100 became $79.01. All 6 test folds were negative.
```

The operator then tried files mode with Alpari-style paths, but the input files did not exist:

```text
[X] RuntimeError: Input file does not exist: datasets\external\XAUUSD_1D.csv
```

This is not a model error. It only means the external CSV files have not been placed at the requested paths yet.

---

## Storage-mode correction — 2026-09-16

The first files-mode command caused owner confusion because it asked for:

```text
datasets\external\XAUUSD_1D.csv
datasets\external\XAUUSD_1H.csv
datasets\external\XAUUSD_5M.csv
```

That was not the best default for this project. The project already has a canonical dataset storage layout:

```text
datasets\processed\<SYMBOL>\<TIMEFRAME>\v*.parquet
```

Phase141A was corrected to support direct project-storage reads:

```text
--source-mode storage
```

In storage mode the script reads the latest versioned parquet files automatically:

```text
datasets\processed\XAUUSD\5M\v*.parquet
datasets\processed\XAUUSD\1D\v*.parquet
```

For 4H context:

```text
If datasets\processed\XAUUSD\4H\v*.parquet exists, it is loaded directly.
Otherwise, datasets\processed\XAUUSD\1H\v*.parquet is loaded and resampled to 4H.
```

The project parquet schema is supported directly, including:

```text
open_time -> timestamp
```

Correct command for the project dataset:

```powershell
python -u scripts/train_pivot_pattern_recognition.py `
  --source-mode storage `
  --symbol XAUUSD `
  --five-timeframe 5M `
  --hourly-timeframe 1H `
  --h4-timeframe 4H `
  --daily-timeframe 1D `
  --model-id gold_pivot_pattern_recognition_5m `
  --model-kind auto `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --max-features 38 `
  --train-days-min 120 `
  --validation-days 20 `
  --test-days 20 `
  --purge-hours 4 `
  --buy-thresholds 0.45,0.55,0.65 `
  --sell-thresholds 0.45,0.55,0.65 `
  --margins 0,0.05 `
  --tp-multipliers 0.75,1.0,1.25 `
  --sl-multipliers 0.50,0.75 `
  --hold-bars 24,48 `
  --min-validation-trades 10 `
  --score-metric net_profit `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --save-model 1 `
  --save-data 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_recognition `
  --report-title "Pivot pattern recognition project-storage XAUUSD walk-forward"
```

GUI default was also changed:

```text
Train pivot pattern recognition -> source_mode default = storage
```
