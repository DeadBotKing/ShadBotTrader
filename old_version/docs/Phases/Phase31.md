================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 31 — LIVE DECISION LOOP & MODEL-DRIVEN BACKTEST

CURRENT CONTRACT UPDATE (2026-08-19):
    The signal model is binary SELL/BUY only. HOLD/no-trade is a
    strategy-level gate outcome, not a third model class.

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-16

AUTHORISED BY:
    Agreed continuation (option A then B). Completes the chain begun in
    Phases 29-30. Extends; does not redesign. Phase 26 freeze respected.

--------------------------------------------------------------------------------
PURPOSE
--------------------------------------------------------------------------------

    Phases 29-30 built the models and the data. Nothing joined them to
    trading. This phase closes both loops:

        A. LIVE   — every 5 minutes, decide and act
        B. TEST   — replay history through the same models

--------------------------------------------------------------------------------
1. THE GAP THIS PHASE CLOSES
--------------------------------------------------------------------------------

  COMPONENT                        | BEFORE PHASE 31
  ---------------------------------|------------------------------------
  800-candle rolling buffer        | built (Phase 30), never read
  (500, 123) live matrix           | built (Phase 30), never consumed
  range + signal models            | trained (Phase 29), never consulted
  strategy reading BOTH models     | ABSENT — AiDirectionalStrategy reads
                                   | a single float
  five-minute decision service     | ABSENT
  backtest driven by the model     | ABSENT — MomentumPredictionSource
                                   | was still the predictor

--------------------------------------------------------------------------------
2. PART A — THE LIVE LOOP
--------------------------------------------------------------------------------

One tick:

    fetch 1 x 5M candle + 1 x 1H candle
      -> RollingCandleBuffer (800 each, self-evicting)
      -> recompute features over the whole buffer
      -> newest 500 rows -> (500, 123)
      -> range model  (1H) -> predicted high / low
      -> signal model (5M) -> buy / sell / hold + probabilities
      -> DualModelStrategy -> TradingSignal
      -> risk gate         -> TradingIntent
      -> execution         -> Fill

2.1 WHY FEATURES ARE RECOMPUTED OVER ALL 800 ROWS

    EMA, MACD and ATR are recursive. A value derived from a one-bar
    update is NOT the value the training pipeline produced, so the model
    would see a different world at inference than it learned from. 800
    rows costs well under a second — far cheaper than a mismatch.

2.2 A TICK MUST NEVER RAISE

    An unattended five-minute loop that dies on a broker hiccup is an
    outage. Every failure becomes a ``TickResult`` with:

        status  : traded | no_trade | skipped | failed
        reason  : always populated

    "Nothing happened" is a first-class, explainable outcome.

--------------------------------------------------------------------------------
3. THE DUAL-MODEL STRATEGY — SIX GATES
--------------------------------------------------------------------------------

The signal model proposes a direction; the range model decides whether
it is worth taking. A 90%-confident buy with 2 dollars of upside and 20
of downside is a bad trade, and only the second model can say so.

    1. both forecasts present            else HOLD
    2. signal model not saying HOLD      else HOLD
    3. confidence >= min_confidence      else HOLD
    4. range forecast coherent           else HOLD
    5. reward/risk >= min_reward_risk    else HOLD
    6. predicted move >= cost floor      else HOLD

3.1 REWARD AND RISK SWAP FOR A SHORT

    For a long, reward is the upside and risk the downside; for a short
    they invert. ``RangeForecast.reward_risk()`` is the long-oriented
    view, so the strategy computes the direction-aware ratio itself and
    reports THAT — printing the raw property would contradict the gate
    that just passed the trade.

3.2 EVERY REJECTION EXPLAINS ITSELF

    A silent rejection is as bad as a wrong trade: neither can be
    diagnosed at 3am. Each HOLD carries its reason and the numbers
    behind it.

--------------------------------------------------------------------------------
4. PART B — MODEL-DRIVEN BACKTEST
--------------------------------------------------------------------------------

``ModelPredictionSource`` implements the existing ``PredictionSource``
port, so the engine is unchanged: it still walks candle 0 to N one at a
time.

4.1 CAUSALITY IS THE WHOLE POINT

    A source that lets the model glimpse bar t+1 while deciding at bar t
    produces a beautiful equity curve and loses money live.

    * the source keeps its OWN rolling window and appends only the bar
      the engine has already delivered — nothing else is reachable
    * until ``window_size`` bars have arrived it returns None (abstain)
      rather than padding: a padded window is invented history

4.2 THREE CLASSES ONTO ONE AXIS

    The port contract is a single float in [0, 1]. The three-class
    forecast is projected using DIRECTIONAL confidence — buy renormalised
    against sell, ignoring hold — so 0.45/0.10/0.45 reads as 0.5
    (undecided) rather than a weak buy. A HOLD forecast is pulled toward
    neutral so the strategy's own gate sees an unattractive signal.

    The full forecast stays reachable via ``last_forecast``.

4.3 RECOMPUTE INTERVAL

    A 500x123 forward pass on every one of 100,000 bars is impractical.
    ``recompute_every`` reuses the previous forecast on skipped bars —
    reuse, never a fresh guess.

--------------------------------------------------------------------------------
5. ARCHITECTURE PLACEMENT
--------------------------------------------------------------------------------

    infrastructure/trading/
        dual_model_strategy.py        NEW  both models -> one signal
    infrastructure/simulation/
        model_prediction_source.py    NEW  trained model drives backtest
    application/services/
        live_decision_service.py      NEW  the five-minute tick

DEPENDENCY DIRECTION: unchanged; the architecture test still enforces it.

--------------------------------------------------------------------------------
6. WHAT THIS PHASE DOES NOT DO
--------------------------------------------------------------------------------

    - It does not schedule itself. The loop runs on demand or under an
      external scheduler; Windows service installation is Phase 24.
    - It does not place real broker orders. Execution still goes to the
      simulated venue; a live venue adapter is a separate decision with
      real money attached.
    - It does not claim profitability. The chain is complete and honest;
      whether the models are any good is an empirical question that real
      data will answer.

================================================================================
END OF PHASE 31
================================================================================
