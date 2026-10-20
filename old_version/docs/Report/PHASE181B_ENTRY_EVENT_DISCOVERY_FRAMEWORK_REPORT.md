# PHASE181B — Entry Event Discovery Framework Report

## Summary

Phase181B implements the owner-approved shift from profit-target tuning to **entry-event discovery**.

The phase adds a diagnostic-only framework that separates:

```text
Entry Event
Entry Quality
Replay / Cost / Walk-forward validation
```

This is not model training and does not approve paper/live use.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Implemented files

```text
scripts/audit_entry_event_discovery.py
tests/unit/ai/test_entry_event_discovery.py
```

GUI integration:

```text
CommandKind.AUDIT_ENTRY_EVENT_DISCOVERY
GUI label: Audit entry event discovery
```

Updated GUI files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
tests/integration/test_gui_coverage.py
```

## Target families

Phase181B audits three entry families separately.

### E1 — Breakout Entry

Formula:

```text
Resistance = recent_high[t]
Support    = recent_low[t]
buffer     = buffer_atr * ATR[t]

BUY_TRIGGER  = Resistance + buffer
SELL_TRIGGER = Support - buffer
```

Trigger rule:

```text
BUY  if future high reaches BUY_TRIGGER within trigger_horizon
SELL if future low reaches SELL_TRIGGER within trigger_horizon
```

### E2 — Pullback / Rejection Entry

BUY setup:

```text
bullish trend
pullback into lower part of recent range
bullish rejection candle
BUY_TRIGGER = high[t] + buffer_atr * ATR[t]
```

SELL setup:

```text
bearish trend
pullback into upper part of recent range
bearish rejection candle
SELL_TRIGGER = low[t] - buffer_atr * ATR[t]
```

### E3 — Continuation / Impulse Entry

BUY setup:

```text
impulse candle closes above previous local high
body_atr >= min_body_atr
range expansion >= min_expansion_ratio
BUY_TRIGGER = high[t] + buffer_atr * ATR[t]
```

SELL setup:

```text
impulse candle closes below previous local low
abs(body_atr) >= min_body_atr
range expansion >= min_expansion_ratio
SELL_TRIGGER = low[t] - buffer_atr * ATR[t]
```

## Entry quality logic

Phase181B does not label an entry as good just because price eventually moved.
It records the trigger and then audits the path after entry.

BUY spread-adjusted entry:

```text
entry_price = trigger_price + spread_abs / 2
```

SELL spread-adjusted entry:

```text
entry_price = trigger_price - spread_abs / 2
```

Quality pass rule:

```text
MFE >= mfe_atr before MAE >= mae_atr
```

Default examples:

```text
E1/E2: MFE >= 1.5 ATR before MAE >= 0.75 ATR
E3   : MFE >= 1.2 ATR before MAE >= 0.75 ATR
```

## Gates

A family must pass all major gates to become discovery-ready:

```text
Event density gate
Direction balance gate
Temporal stability gate
MFE/MAE structure gate
Replay gate
Feature separability gate
Broker cost gate
Walk-forward gate
```

The decision matrix still blocks model training unless owner review explicitly approves a later model-design phase.

## Outputs

```text
run_logs\entry_event_discovery\latest.json
run_logs\entry_event_discovery\latest.html
run_logs\entry_event_discovery\latest_families.csv
run_logs\entry_event_discovery\latest_events.csv
run_logs\entry_event_discovery\latest_replay.csv
run_logs\entry_event_discovery\latest_splits.csv
run_logs\entry_event_discovery\latest_walkforward.csv
run_logs\entry_event_discovery\latest_mfe_mae.csv
run_logs\entry_event_discovery\latest_cost.csv
run_logs\entry_event_discovery\latest_feature_separability.csv
run_logs\entry_event_discovery\latest_decision_matrix.csv
```

## Verification

```text
python -m py_compile scripts/audit_entry_event_discovery.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Unavailable in sandbox:

```text
python -m ruff check .        → No module named ruff
python -m black --check .     → No module named black
python -m mypy src            → No module named mypy
```

## Recommended owner action

Run from GUI:

```text
AI → Audit entry event discovery
```

Then send:

```text
run_logs\entry_event_discovery\latest.json
```

## Production status

```text
BLOCKED — Phase181B is target discovery only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-03

The owner ran the official Phase181B command on `1H,4H,1D` using fixed spread `0.4`.

Result:

```text
ready_families                   : 0/9
selected_timeframe               : 1D
selected_family_id               : E3_CONTINUATION
entry_event_discovery_ready_gate : 0
```

Interpretation:

```text
Data health and broker cost passed.
The entry definitions were often temporally stable and feature-separable.
However, no family passed MFE/MAE, replay and walk-forward transfer gates.
```

Documented in:

```text
docs/Report/PHASE181B_ENTRY_EVENT_DISCOVERY_RESULT.md
```
