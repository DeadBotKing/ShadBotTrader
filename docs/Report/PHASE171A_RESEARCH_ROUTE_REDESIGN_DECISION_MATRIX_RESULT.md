# PHASE171A — Research Route Redesign Decision Matrix Result

## Status

```text
COMPLETED — next research route selected
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Top-level result

```text
route_reset_status        : CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED_BY_DOCUMENTED_RESULTS
broker_cost_status        : MISSING_PHASE170_USING_DOCUMENTED_MANUAL_VALUES
broker_spread_median      : 0.39
broker_spread_p90         : 0.40
broker_spread_p99         : 0.41
h1_median_spread_atr      : 0.08347
selected_research_route   : NEW_1H_COST_AWARE_TARGET_FAMILY
selected_required_phase   : Phase172A — Broker-cost-aware 1H target-family design audit
```

Important note:

```text
Phase170A/168A/166A/162A run_logs were missing on disk, so Phase171A used the documented/manual evidence already recorded in docs.
This is acceptable for owner-level decision routing, but future automated reports need the relevant run_logs present or re-exported.
```

## Decision matrix interpretation

### Mandatory decision — stop current locked routes

```text
route_id    : STOP_CURRENT_LOCKED_ROUTES
status      : MANDATORY
total_score : 94.0
rank        : 2
```

This means the rejection of the current routes is not optional:

```text
5M bottom-buy route remains rejected.
1H BRK_D1_FAST locked route remains rejected.
No patching / re-optimizing these rejected candidates.
```

It is ranked second only because it is already a mandatory reset action, not a new research lane.

### Selected next research lane

```text
route_id       : NEW_1H_COST_AWARE_TARGET_FAMILY
status         : RECOMMENDED_RESEARCH
total_score    : 87.0
rank           : 1
required_phase : Phase172A — Broker-cost-aware 1H target-family design audit
```

Rationale:

```text
1H had raw/test-side signal.
The previous locked rule failed stability.
Broker cost is now known approximately: fixed spread around 0.39–0.41.
A new target family may preserve useful 1H structure, but must include broker-realistic cost from the beginning.
```

Allowed next action:

```text
Build target audit only.
No model training until target/replay gates pass.
```

### Strong secondary option

```text
route_id    : HYBRID_REGIME_FIRST_REDESIGN
status      : SECONDARY_RESEARCH
total_score : 90.0
rank        : 3
```

This option scored high because failures were regime/month sensitive. It remains a strong backup route if Phase172A fails or if the owner prefers a regime-first architecture lane.

### Other options

```text
4H_1D_COST_FEASIBILITY:
  status      : SECONDARY_RESEARCH
  total_score : 73.0
  use only if owner wants fewer trades and higher timeframe exploration.

TRAIN_CURRENT_1H_LOCKED_RULE:
  status      : BLOCKED
  total_score : 0.0

PAPER_OR_LIVE:
  status      : BLOCKED
  total_score : 0.0
```

## Final decision

```text
Proceed to Phase172A only.
Do not train the current 1H locked rule.
Do not continue patching the rejected 5M/1H locked routes.
Do not start paper/live/Phase134.
```

## Recommended next phase

```text
Phase172A — Broker-cost-aware 1H target-family design audit
```

Phase172A must be diagnostic-only and must enforce:

```text
fixed spread around 0.4 or stress 0.4/0.5
no training
no paper/live
no reuse of rejected BRK_D1_FAST as a target
walk-forward/replay gates from the start
```

Suggested target-family direction:

```text
A new 1H cost-aware trade-outcome target that explicitly prices spread, TP/SL path, single-position behavior and monthly/fold stability before any model work.
```

Production remains blocked.
