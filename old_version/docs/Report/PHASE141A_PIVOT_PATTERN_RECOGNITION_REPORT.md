# Phase141A Report — Pivot Pattern Recognition Walk-Forward

Date: 2026-09-16

## Owner request

Build a model that performs Pattern Recognition on gold:

```text
Recognize top zones before downside moves.
Recognize bottom zones before upside moves.
Use 5M patterns with 4H/1D context.
Train it, check useful features, backtest and walk-forward it.
```

## Implementation

Added:

```text
scripts/train_pivot_pattern_recognition.py
tests/unit/ai/test_pivot_pattern_recognition.py
```

GUI command:

```text
Train pivot pattern recognition
```

Updated GUI files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Dependency note:

```text
requirements-boosters.txt now includes scikit-learn>=1.4
```

The script still has a dependency-free centroid fallback, but the recorded real run used sklearn HGB.

## Model objective

Classes:

```text
SELL = top_zone reversal pattern
HOLD = no actionable pivot zone
BUY  = bottom_zone reversal pattern
```

Target construction:

```text
lookahead_bars     = 48
pivot_move_atr     = 0.75
pivot_zone_atr     = 0.35
recent_window_bars = 48
min_direction_edge = 1.10
```

Causality rule:

```text
5M input uses closed/current 5M information.
4H input uses previous closed 4H information.
1D input uses previous closed 1D information.
Entry is next 5M open.
Targets may look forward because they are labels, not input features.
```

## Data used for the real run

The public spot symbol `XAUUSD=X` was not available from Yahoo intraday, so the run used:

```text
GC=F — COMEX Gold Futures continuous contract
Source: Yahoo Finance chart API
```

Rows:

```text
1D rows : 1,258
4H rows : 3,721, resampled from 1H
5M rows : 13,509
```

Important limitation:

```text
GC=F is not Alpari XAUUSD.
Yahoo 5M data is recent-window only.
This is a real public-data experiment, not a broker-perfect production validation.
```

## Feature investigation

Total feature columns:

```text
57
```

Selected per fold:

```text
38
```

The top selected features were dominated by 5M structure/pattern features:

```text
m5_pos_in_range_48       selected=6 mean_rank=1.0  score=1.4635
m5_dist_high_48_atr      selected=6 mean_rank=2.0  score=1.3858
m5_dist_low_48_atr       selected=6 mean_rank=3.0  score=1.3058
m5_fast_mid_dist_atr     selected=6 mean_rank=4.7  score=1.2472
m5_price_z_96            selected=6 mean_rank=6.2  score=1.2238
m5_pos_in_range_24       selected=6 mean_rank=7.3  score=1.2078
m5_ret48                 selected=6 mean_rank=6.5  score=1.2071
m5_close_mid_dist_atr    selected=6 mean_rank=7.7  score=1.2010
m5_ret24                 selected=6 mean_rank=8.2  score=1.1841
m5_dist_high_24_atr      selected=6 mean_rank=9.7  score=1.1663
m5_pos_in_range_96       selected=6 mean_rank=10.0 score=1.1384
m5_mid_slow_dist_atr     selected=6 mean_rank=12.5 score=1.0954
m5_dist_low_24_atr       selected=6 mean_rank=12.5 score=1.0785
m5_rsi14                 selected=6 mean_rank=14.3 score=1.0205
m5_dist_high_96_atr      selected=6 mean_rank=15.0 score=0.9973
```

Interpretation:

```text
The feature selector correctly focuses on local 5M position inside recent ranges, distance from local highs/lows, momentum/EMA distance, and z-score. These are the right feature types for top/bottom recognition.
```

## Target distribution

```text
SELL/top_zone    : 1,368
HOLD/no pivot    : 10,764
BUY/bottom_zone  : 1,376
```

This is intentionally sparse: most bars should be HOLD/no-trade.

## Walk-forward method

```text
expanding train
5 trading-day validation
5 trading-day unseen test
4-hour purge before validation/test boundaries
threshold + TP/SL + max-hold selected on validation only
single-position chronological replay
initial_balance = $100
risk_per_trade = 1% current balance
spread = 0.06%
same_bar_policy = stop_first
```

## Aggregate result

```text
model_kind_used       : sklearn_hgb
folds                 : 6
trades                : 102
BUY / SELL trades     : 40 / 62
wins / losses         : 45 / 57
win_rate              : 44.1176%
initial_balance       : $100.00
final_balance         : $86.7906284989
net_profit            : -$13.2093715011
return                : -13.2094%
profit_factor         : 0.6737950152
max_drawdown_cash     : $15.0878759322
positive_folds        : 0
negative_folds        : 6
```

## Fold results

```text
Fold 1:
  validation net=-3.3902 PF=0.6400 trades=21
  test       net=-2.6643 PF=0.5531 trades=11 win=45.45% buy/sell=0/11

Fold 2:
  validation net=-1.5733 PF=0.0805 trades=5
  test       net=-0.3089 PF=0.9124 trades=11 win=54.55% buy/sell=8/3

Fold 3:
  validation net=+3.5215 PF=2.7004 trades=7
  test       net=-3.1170 PF=0.5913 trades=12 win=33.33% buy/sell=0/12

Fold 4:
  validation net=-0.9011 PF=0.8524 trades=21
  test       net=-2.7775 PF=0.6993 trades=34 win=50.00% buy/sell=15/19

Fold 5:
  validation net=+6.7796 PF=1.6403 trades=47
  test       net=-4.1545 PF=0.1518 trades=12 win=25.00% buy/sell=3/9

Fold 6:
  validation net=+0.2669 PF=1.0544 trades=11
  test       net=-0.1872 PF=0.9797 trades=22 win=45.45% buy/sell=14/8
```

## Decision

```text
FAILED as a trading strategy.
```

Reason:

```text
All 6 unseen test folds were negative.
Final balance: $100 → $86.79.
Profit factor: 0.674.
Validation positives did not transfer robustly to test.
```

## What was learned

Good signs:

```text
The label design produces sparse top/bottom events.
Feature selection focused on the right pattern-recognition concepts.
The script now gives a repeatable owner-facing GUI command and report.
```

Bad signs:

```text
The first public-data model is not profitable.
Yahoo 5M history is too short for a serious deep pattern-recognition model.
GC=F is not identical to Alpari XAUUSD.
Validation transfer remains weak.
```

## Artifacts

```text
run_logs\pivot_pattern_recognition\latest.json
run_logs\pivot_pattern_recognition\latest.html
run_logs\pivot_pattern_recognition\latest_folds.csv
run_logs\pivot_pattern_recognition\latest_trades.csv
run_logs\pivot_pattern_recognition\latest_features.csv

datasets\models\gold_pivot_pattern_recognition_5m\v1_model.pkl
datasets\models\gold_pivot_pattern_recognition_5m\v1_training.json
```

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```

## Recommended next step

Before trying heavier neural pattern-recognition models, run this exact Phase141A command on broker-quality multi-year Alpari XAUUSD data:

```text
5M: at least 1-3 years
1H or 4H: at least matching period
1D: at least 5 years preferred
```

Then re-check:

```text
walk-forward profitability
positive/negative folds
feature stability
validation-to-test transfer
spread sensitivity
```

## Verification

Targeted verification on changed files:

```text
python -m ruff check scripts/train_pivot_pattern_recognition.py tests/unit/ai/test_pivot_pattern_recognition.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m black --check scripts/train_pivot_pattern_recognition.py tests/unit/ai/test_pivot_pattern_recognition.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/presentation/test_architecture_knobs_gui.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_recognition.py tests/unit/presentation/test_architecture_knobs_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full test suite:

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1874 tests collected
```

Known full-repository quality debt remains:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```

## Operator rerun result — Yahoo GC=F — 2026-09-16

The operator reran the same Phase141A Yahoo command on Windows.

Top-level result:

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

Walk-forward:

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

Conclusion:

```text
This rerun confirms the first Phase141A model is not tradeable on public Yahoo/GC=F data.
The result is worse than the sandbox run because Yahoo intraday data changes as new 5M bars arrive.
```

The operator also tried the file-source command for broker data and received:

```text
[X] RuntimeError: Input file does not exist: datasets\external\XAUUSD_1D.csv
```

Interpretation:

```text
The files-mode command is correct structurally, but the Alpari/XAUUSD CSV files do not exist in datasets\external yet.
```

## Storage-mode correction — 2026-09-16

The operator correctly objected that Phase141A should not require moving project data into `datasets\external`. The project already stores datasets under:

```text
datasets\processed\<SYMBOL>\<TIMEFRAME>\v*.parquet
```

Phase141A was corrected:

```text
--source-mode storage
```

Behavior:

```text
Read latest datasets\processed\XAUUSD\5M\v*.parquet
Read latest datasets\processed\XAUUSD\1D\v*.parquet
Read latest datasets\processed\XAUUSD\4H\v*.parquet if present
Otherwise read latest datasets\processed\XAUUSD\1H\v*.parquet and resample to 4H
```

Supported project parquet schema:

```text
open_time -> timestamp
symbol/timeframe columns are ignored safely
```

Dashboard correction:

```text
Train pivot pattern recognition now defaults to source_mode=storage.
```

Correct command for project-stored datasets:

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
