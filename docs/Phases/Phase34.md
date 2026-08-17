================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 34 — DATA INSPECTION & CANDLESTICK CHART

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    User requirement: see the candles as a chart, and see what a dataset
    actually contains (how many candles, which columns) after each of
    Fetch market data / Update features / Build training dataset.

--------------------------------------------------------------------------------
1. THE GAP
--------------------------------------------------------------------------------

  QUESTION AFTER A RUN            | BEFORE PHASE 34
  --------------------------------|-------------------------------------
  what do the candles look like?  | only the backtest replay showed a
                                  | chart, and only for a simulated run
  how many candles are stored?    | a number in a command result that
                                  | scrolled away
  which columns does the dataset  | nowhere. The 123 columns were a
  have?                           | claim in a report, not inspectable
  are any columns broken?         | unanswerable without a terminal

--------------------------------------------------------------------------------
2. ONE PAGE, THREE SOURCES
--------------------------------------------------------------------------------

    GET /data       the page
    GET /api/data   the same content as JSON

  SECTION            | SOURCE                    | ANSWERS
  -------------------|---------------------------|--------------------
  Candles            | ParquetCandleStore        | Fetch market data
  Computed features  | ParquetFeatureStore       | Update features
  Training matrix    | TrainingDataService       | Build training dataset

2.1 THE CHART

    Candlestick with a volume strip, drawn on a canvas by inlined
    JavaScript. Green when the close is above the open. The visible
    window is selectable (60/120/200/300) and volume can be hidden.

    The chart is capped at 300 candles while the *count* is reported in
    full. A 100,000-candle dataset must not become a 100,000-point web
    page; truncating the drawing while lying about the total would be
    worse than either.

2.2 COLUMN INSPECTION

    Every column of the stored matrix is listed with:

        kind        raw price | candle shape | feature | target
        coverage    percentage of rows that hold a finite value
        min / max   the observed range
        latest      the most recent value
        flags       "gaps" when incomplete, "constant" when it never varies

    A constant column is flagged because it teaches a model nothing —
    ``close_rel`` is zero by construction and the page says so rather
    than letting it look like a real input.

    Columns are sampled (every Nth row, up to 2000) so a 100k x 123
    matrix summarises instantly; the row total is reported honestly
    alongside the sample.

--------------------------------------------------------------------------------
3. IT READS, IT DOES NOT COMPUTE
--------------------------------------------------------------------------------

``DataInspector`` is a Gateway in the Phase 19 sense: it queries the
stores and shapes the result for display. Every number on the page was
read from storage. If the page and a run disagree, the run is wrong —
the page cannot invent a different answer.

An unreadable or absent store yields an empty result rather than an
exception: a dashboard that crashes because nothing has been fetched yet
is useless precisely when the operator is trying to find that out.

--------------------------------------------------------------------------------
4. ARCHITECTURE PLACEMENT
--------------------------------------------------------------------------------

    presentation/gateway/data_inspector.py   NEW  reads the three stores
    presentation/web/data_renderer.py        NEW  chart + tables
    presentation/web/server.py               MOD  /data and /api/data
    presentation/web/renderer.py             MOD  header link

DEPENDENCY DIRECTION: unchanged.

--------------------------------------------------------------------------------
5. WHAT THIS PHASE DOES NOT DO
--------------------------------------------------------------------------------

    - No zoom or pan. The window selector covers the need; a full
      charting library is a dependency this page does not justify.
    - No indicator overlays on the price chart. Feature values are listed
      numerically; drawing 109 of them over candles would be unreadable.
    - No editing. The page is strictly read-only, like the dashboard.

================================================================================
END OF PHASE 34
================================================================================
