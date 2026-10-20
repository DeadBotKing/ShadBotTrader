================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 29 — DUAL PREDICTIVE MODEL ARCHITECTURE

CURRENT CONTRACT UPDATE (2026-08-19):
    The signal model is binary SELL/BUY only. Any HOLD/no-trade mentioned
    in the historical design below belongs to the strategy/risk layer,
    not to the neural-network output.

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-16

AUTHORISED BY:
    Explicit user requirement. This phase extends Phases 12-13; it does
    NOT redesign them. Phase 26 (Freeze v1.0) is respected: every new
    contract is added alongside the existing ones, and no existing port,
    entity or dependency direction is altered.

--------------------------------------------------------------------------------
PURPOSE
--------------------------------------------------------------------------------

    طراحی و پیاده‌سازی دو مدل پیش‌بینی مجزا که در کنار هم کار می‌کنند:

        1. RANGE MODEL   — پیش‌بینی سقف و کف قیمت تا N کندل آینده
        2. SIGNAL MODEL  — پیش‌بینی جهت معامله همراه با درصد احتمال

    هر دو با روش roll-forward آموزش می‌بینند و از کل کاتالوگ ۱۰۹ فیچر
    به‌همراه قیمت خام بازار استفاده می‌کنند.

--------------------------------------------------------------------------------
1. WHY THIS PHASE EXISTS — GAP ANALYSIS
--------------------------------------------------------------------------------

An audit of the implementation against Phases 12-13 found the following.
The AI Platform is real and working, but it solves exactly one problem:
binary next-bar direction, from four hand-written features.

  CAPABILITY                        | BEFORE PHASE 29
  ----------------------------------|--------------------------------------
  Multi-horizon high/low regression | ABSENT. `_build_compiled` hardcodes
                                    | SparseCategoricalCrossentropy, so a
                                    | regression head cannot be produced.
  Signal probability output         | PARTIAL. The network emits a softmax
                                    | vector, but `WavenetPredictor.predict`
                                    | collapses it to a single float and the
                                    | class probabilities are discarded.
  Full 109-feature catalogue        | ABSENT. `build_direction_series`
                                    | produces 4 columns; the catalogue built
                                    | in Phase 12 was never wired to the AI
                                    | Platform.
  Per-timeframe model roles         | ABSENT. No concept of "this model is
                                    | for 1H, that one is for 5M".
  Roll-forward training             | PRESENT and correct. Reused unchanged.
  Leakage protection                | PRESENT (`drop_target_column`).
                                    | Must be extended to horizon > 0.

CONCLUSION:
    A new phase is required. Extending Phase 13 in place would break the
    freeze and the existing direction model.

--------------------------------------------------------------------------------
2. THE TWO MODELS
--------------------------------------------------------------------------------

2.1 RANGE MODEL (price extremes)

    QUESTION ANSWERED:
        "Over the next N candles, what is the highest and the lowest
         price the market is likely to reach?"

    TARGETS (two continuous values):
        future_high = max(high[t+1 .. t+N])
        future_low  = min(low[t+1  .. t+N])

    TARGET ENCODING:
        Absolute prices are NOT predicted. The targets are expressed as
        a fraction of the current close:

            high_offset = (future_high - close[t]) / close[t]
            low_offset  = (future_low  - close[t]) / close[t]

        RATIONALE: gold at 2000 and gold at 3000 must not be two
        different problems. A ratio is stationary; a price is not. A
        model trained on absolute prices silently stops working the
        moment the market leaves its training range.

    OUTPUT: 2 continuous units, linear activation, MSE loss.

    DEFAULT TIMEFRAME: 1H
        Per user requirement. Hourly bars carry enough structure for a
        multi-bar range to be meaningful; 5M extremes are dominated by
        microstructure noise.

    DEFAULT HORIZON: 5 candles.

2.2 SIGNAL MODEL (direction with probability)

    QUESTION ANSWERED:
        "Should I buy, sell or stay out — and how confident is that?"

    TARGET: three mutually exclusive classes

        BUY   (2) — forward return exceeds  +threshold
        SELL  (0) — forward return falls below -threshold
        HOLD  (1) — the move stays inside the neutral band

    WHY THREE CLASSES AND NOT TWO:
        A binary up/down model is forced to take a side on every bar,
        including bars where nothing happens. Most bars are noise. The
        HOLD class lets the model say "no trade", which is the single
        most valuable output a trading model can produce.

    THRESHOLD:
        Expressed in price fraction (default 0.0008 = 8 basis points)
        and configurable. It MUST exceed the round-trip cost, or the
        model is being trained to chase moves that cannot be captured
        after spread and commission.

    OUTPUT: 3 probability units, softmax, categorical cross-entropy.
            The full probability vector is preserved end to end — this
            is what produces "90% buy".

    DEFAULT TIMEFRAME: 5M
        Per user requirement.

--------------------------------------------------------------------------------
3. FEATURE INPUT — THE FULL CATALOGUE
--------------------------------------------------------------------------------

Both models consume:

    raw OHLCV        — open, high, low, close, volume (normalised)
    109 features     — the complete Phase 12 standard catalogue

STATIONARITY RULE:
    Price-valued features (moving averages, bands, envelopes) are
    converted to a ratio against the current close before entering the
    model, for the reason given in 2.1. Oscillators already bounded
    (RSI, stochastic) pass through unchanged.

WARM-UP RULE:
    A feature needing k bars of history is undefined for the first k
    rows. Those rows are DROPPED, never zero-filled. Filling them
    invents data the market never produced.

--------------------------------------------------------------------------------
4. LEAKAGE PROTECTION (NON-NEGOTIABLE)
--------------------------------------------------------------------------------

Both targets look into the future by construction. Three guarantees:

    R1. The label for row t is computed from bars t+1 .. t+N. Row t
        itself contributes NOTHING to its own label beyond close[t],
        which is known at decision time.

    R2. The last N rows of any series have an incomplete future window
        and are DROPPED. They are never padded, clipped or approximated.

    R3. Target columns are removed from the feature matrix before
        windowing (`drop_target_column`), so the model cannot read the
        answer off its own input.

    A dedicated test asserts each of these. R2 in particular is the
    mistake that makes a backtest look profitable and live trading lose.

--------------------------------------------------------------------------------
5. TRAINING METHOD
--------------------------------------------------------------------------------

Roll-forward (walk-forward) for BOTH models, reusing the existing
`roll_forward_split` / `expanding_split` from Phase 13 unchanged.

    fold k:  train [start, train_end)   validate [train_end, +val_size)
    window advances by `step`

No shuffling. No random split. Ever.

--------------------------------------------------------------------------------
6. ARCHITECTURE PLACEMENT
--------------------------------------------------------------------------------

    domain/ai/
        prediction_target.py   NEW  PredictionTarget, TargetKind,
                                    RangeForecast, SignalForecast
    infrastructure/ai/
        target_builder.py      NEW  future high/low + 3-class labelling
        feature_matrix.py      NEW  109 features + OHLCV -> numeric matrix
        model_roles.py         NEW  binds a role to timeframe + horizon
    application/services/
        dual_model_service.py  NEW  composition root for both models

    MODIFIED (additively, no behaviour change for existing callers):
        wavenet_trainer.py     task-aware loss selection
        wavenet.py             linear output activation permitted

DEPENDENCY DIRECTION: unchanged. Domain gains no outward imports; the
architecture test continues to enforce this.

--------------------------------------------------------------------------------
7. WHAT THIS PHASE DELIBERATELY DOES NOT DO
--------------------------------------------------------------------------------

    - It does not guarantee profitability. It provides the two models
      the user asked for, trained honestly. Whether the market is
      predictable at these horizons is an empirical question the
      backtester answers.
    - It does not tune hyperparameters. Search belongs to Phase 17.
    - It does not remove the momentum baseline. A transparent baseline
      remains essential for attributing backtest results.
    - It does not fabricate confidence. Where a value is undefined it is
      reported as undefined, per DEVELOPMENT_RULES.md.

================================================================================
END OF PHASE 29
================================================================================
