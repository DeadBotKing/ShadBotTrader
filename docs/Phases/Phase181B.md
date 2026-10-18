# Phase181B — Entry Event Discovery Framework

## Status

```text
IMPLEMENTED — awaiting owner run
Production — BLOCKED
```

This phase starts the owner-approved route change from profit-target tuning to **entry-event discovery**.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Purpose

Previous target families repeatedly asked variants of:

```text
Did price later move enough?
```

Phase181B instead asks:

```text
Did a valid entry setup form at candle t?
Did a trigger occur after that setup?
Was the triggered entry clean enough after broker costs?
```

The key separation is:

```text
Entry Target != Profit Target
```

## Implemented command

GUI command:

```text
Audit entry event discovery
```

Command kind:

```text
CommandKind.AUDIT_ENTRY_EVENT_DISCOVERY
```

Script:

```text
scripts/audit_entry_event_discovery.py
```

## Default entry families

### E1 — Breakout Entry

BUY setup/trigger:

```text
Resistance = recent_high[t]
Trigger    = Resistance + buffer_atr * ATR[t]
BUY trigger occurs if high[t+1 ... t+H] >= Trigger
```

SELL setup/trigger:

```text
Support = recent_low[t]
Trigger = Support - buffer_atr * ATR[t]
SELL trigger occurs if low[t+1 ... t+H] <= Trigger
```

### E2 — Pullback / Rejection Entry

BUY setup:

```text
bullish trend
price pulls back into lower part of recent range
bullish rejection candle
Trigger = high[t] + buffer_atr * ATR[t]
```

SELL setup:

```text
bearish trend
price pulls back into upper part of recent range
bearish rejection candle
Trigger = low[t] - buffer_atr * ATR[t]
```

### E3 — Continuation / Impulse Entry

BUY setup:

```text
impulse candle closes above prior local structure
body_atr >= min_body_atr
range expansion >= min_expansion_ratio
Trigger = high[t] + buffer_atr * ATR[t]
```

SELL setup:

```text
impulse candle closes below prior local structure
abs(body_atr) >= min_body_atr
range expansion >= min_expansion_ratio
Trigger = low[t] - buffer_atr * ATR[t]
```

## Entry quality formula

After a trigger, Phase181B computes spread-adjusted entry price and audits MFE/MAE.

BUY entry:

```text
entry_price = trigger_price + spread_abs / 2
```

SELL entry:

```text
entry_price = trigger_price - spread_abs / 2
```

Spread:

```text
fixed: spread_abs = spread_value
pct  : spread_abs = price * spread_value / 100
```

BUY MFE/MAE:

```text
MFE = max(high - exit_half_spread - entry_price) / ATR[t]
MAE = max(entry_price - (low - exit_half_spread)) / ATR[t]
```

SELL MFE/MAE:

```text
MFE = max(entry_price - (low + exit_half_spread)) / ATR[t]
MAE = max((high + exit_half_spread) - entry_price) / ATR[t]
```

Quality pass:

```text
MFE >= mfe_atr before MAE >= mae_atr
```

Default quality examples:

```text
E1/E2: MFE >= 1.5 ATR before MAE >= 0.75 ATR
E3   : MFE >= 1.2 ATR before MAE >= 0.75 ATR
```

## Default timeframes

```text
1H,4H,1D
```

Interpretation:

```text
1D  -> macro regime context
4H  -> structure
1H  -> setup discovery
5M  -> later execution refinement, not first discovery
```

## Main outputs

```text
run_logs/entry_event_discovery/latest.json
run_logs/entry_event_discovery/latest.html
run_logs/entry_event_discovery/latest_families.csv
run_logs/entry_event_discovery/latest_events.csv
run_logs/entry_event_discovery/latest_replay.csv
run_logs/entry_event_discovery/latest_splits.csv
run_logs/entry_event_discovery/latest_walkforward.csv
run_logs/entry_event_discovery/latest_mfe_mae.csv
run_logs/entry_event_discovery/latest_cost.csv
run_logs/entry_event_discovery/latest_feature_separability.csv
run_logs/entry_event_discovery/latest_decision_matrix.csv
```

## Gates

Phase181B is a target-discovery audit. A family is not considered ready unless it passes:

```text
Event density gate
Direction balance gate
Temporal stability gate
MFE/MAE structure gate
Replay gate
Feature separability gate
Cost gate
Walk-forward gate
```

Even if a family passes, this phase does **not** approve model training automatically. It only creates evidence for owner review.

## Recommended GUI run

```text
AI → Audit entry event discovery
```

Default important fields:

```text
Symbol       : XAUUSD
Timeframes   : 1H,4H,1D
Spread mode  : fixed
Spread value : 0.4
Output dir   : run_logs/entry_event_discovery
```

## CLI equivalent

```powershell
python -u scripts\audit_entry_event_discovery.py `
  --symbol XAUUSD `
  --timeframes "1H,4H,1D" `
  --h1-flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --spread-mode fixed `
  --spread-value 0.4 `
  --same-bar-policy stop_first `
  --output-dir run_logs\entry_event_discovery
```

## Verification in sandbox

```text
python -m py_compile scripts/audit_entry_event_discovery.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black/mypy are not available in the sandbox image.

## Production status

```text
BLOCKED — target discovery only
No model training
No Phase134
No paper shadow
No live trading
```

## Owner run result — 2026-10-03

Owner ran Phase181B on `1H,4H,1D` with fixed spread `0.4`.

Top-level result:

```text
evaluated_timeframes             : 3
evaluated_families               : 9
ready_families                   : 0
selected_timeframe               : 1D
selected_family_id               : E3_CONTINUATION
selected_family_type             : continuation
selected_family_ready_gate       : 0
entry_event_discovery_ready_gate : 0
no_training_gate                 : 1
no_paper_live_gate               : 1
```

Key findings:

```text
Data health       : PASS on 1H, 4H, 1D
Cost feasibility  : PASS on all splits
Dominant failures : MFE/MAE, replay, walk-forward
```

Selected best failed row:

```text
1D | E3_CONTINUATION
train/validation/test events       : 301 / 65 / 74
train/validation/test quality pass : 0.3189 / 0.2923 / 0.4459
train/validation/test replay PF    : 0.7631 / 0.6793 / 1.2878
walk-forward pass                  : 0/4
ready_gate                         : 0
```

Decision:

```text
No entry family passed.
Do not train.
Do not paper/live.
Continue only with diagnostic failure attribution if owner approves.
```

Recommended next diagnostic:

```text
Phase182A — Entry Event Failure Attribution / Quality Geometry Redesign Decision
```

Result report:

```text
docs/Report/PHASE181B_ENTRY_EVENT_DISCOVERY_RESULT.md
```
