================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 30 — TRAINING DATASET & LIVE MARKET BUFFER

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-16

AUTHORISED BY:
    Explicit user requirement. Extends Phases 11-13 and 29. Does NOT
    redesign them; Phase 26 (Freeze v1.0) is respected.

--------------------------------------------------------------------------------
PURPOSE
--------------------------------------------------------------------------------

    دو مخزن داده با دو عمر کاملاً متفاوت:

        TRAINING DATASET — ۱۰۰٬۰۰۰ کندل روی دیسک، دائمی
        LIVE BUFFER      — ۸۰۰ کندل در حافظه، چرخشی

    هر دو یک شکل ورودی به مدل می‌دهند: ماتریس (500, 123).

--------------------------------------------------------------------------------
1. THE TWO STORES — AND WHY THEY ARE NOT THE SAME THING
--------------------------------------------------------------------------------

  ASPECT          | TRAINING DATASET        | LIVE BUFFER
  ----------------|-------------------------|-------------------------
  size            | 100,000 candles         | 800 candles
  lifetime        | permanent, on disk      | in memory, transient
  timeframes      | 5M and 1H (both)        | 5M and 1H (both)
  features        | computed AND STORED     | computed on each tick
  refresh         | weekly, full recompute  | every 5 minutes, 1 candle
  feeds           | model training, backtest| live decision only
  window role     | 500 slides across it    | last 500 rows, once

CRITICAL: the 500-row window is NEVER stored in either place. It is the
*shape of a model input*, produced on demand. Materialising 99,500
windows of 500x123 float32 would need 23 GB; the flat matrix needs 46 MB.

--------------------------------------------------------------------------------
2. THE INPUT MATRIX — 123 COLUMNS
--------------------------------------------------------------------------------

Audit of the current implementation found raw market prices were NOT in
the model input. The catalogue contains ``high_filter``, ``close_filter``
and friends, but those are *wavelet noise-filtered* prices, not the real
ones. Phase 30 adds the raw prices back.

  GROUP                    | COUNT | NOTES
  -------------------------|-------|--------------------------------
  raw price columns  (NEW) |     8 | open, high, low, close, volume,
                           |       | hl2, hlc3, ohlc4
  candle-derived           |     6 | return_1, range_pct, body_pct,
                           |       | upper/lower wick, volume_log
  feature catalogue        |   109 | Phase 12 standard set
  -------------------------|-------|--------------------------------
  TOTAL                    |   123 |

2.1 STATIONARITY OF THE RAW PRICES

    Raw prices are NOT fed as absolute numbers. Each is divided by the
    current close:

        high_rel = high / close - 1
        open_rel = open / close - 1
        ...

    Volume uses log1p, as before.

    RATIONALE (same as Phase 29 §2.1): gold at 2000 and gold at 3000
    must be one problem, not two. A model trained on absolute levels
    stops working the instant the market leaves its training range. The
    information is fully preserved — the ratio is reversible given the
    close, which the model also receives as ``close_rel`` (always 0) and
    which the caller keeps alongside the window.

    NOTE: ``close_rel`` is identically zero by construction. It is kept
    so the column count is stable and self-documenting rather than
    silently dropping a column the user asked for.

--------------------------------------------------------------------------------
3. ROLL-FORWARD OVER 500-ROW WINDOWS
--------------------------------------------------------------------------------

Explicit user requirement: the roll-forward advances ONE CANDLE AT A
TIME across 500-row windows.

    window 0 : rows [    0 ..  499 ]   label at 499 + horizon
    window 1 : rows [    1 ..  500 ]   label at 500 + horizon
    window 2 : rows [    2 ..  501 ]
    ...
    window k : rows [    k .. k+499 ]

Consecutive windows overlap by 499 rows (99.8%). That is intentional:
stride 1 extracts every available training example, and it is what
"یدونه کندل یدونه کندل جلو بره" means.

3.1 WHY A GENERATOR IS MANDATORY

    100,000 rows - 500 window - 5 horizon = 99,495 windows
    99,495 x 500 x 123 x 4 bytes          = 24.5 GB

    Windows are therefore produced lazily, batch by batch, from the flat
    46 MB matrix. Nothing is duplicated in memory. This is not an
    optimisation; it is the difference between the feature working and
    not working.

3.2 FOLD STRUCTURE (unchanged from Phase 13)

    Training still walks forward in folds: train on a block, validate on
    the block immediately after, advance. No shuffling, ever. Stride 1
    governs window extraction *inside* a fold; the folds themselves
    still move forward in time.

--------------------------------------------------------------------------------
4. TRAINING DATASET — CONSTRUCTION AND WEEKLY REFRESH
--------------------------------------------------------------------------------

4.1 BUILD

    ingest 100,000 candles (5M)   -> parquet, versioned, immutable
    ingest 100,000 candles (1H)   -> parquet, versioned, immutable
    compute all features on each  -> stored as a feature matrix
    record a manifest             -> what, when, how many, checksum

4.2 WEEKLY REFRESH — FULL RECOMPUTE, NOT INCREMENTAL

    Explicit user requirement: when the dataset is updated, the features
    are recomputed FROM SCRATCH.

    RATIONALE: many indicators are recursive (EMA, MACD, ATR). Appending
    a value computed from a truncated history produces a subtly wrong
    series that no test would catch. A full recompute costs ~2.2 minutes
    per 100k candles, which is nothing next to silently corrupt features.

        fetch new candles   -> append to the store (new version)
        recompute ALL features from candle 0
        reload the existing models
        continue training on the refreshed dataset
        save as a new model version

    Models are LOADED and continue learning; they are not retrained from
    random initialisation. The previous version is never overwritten.

--------------------------------------------------------------------------------
5. LIVE BUFFER — 800 CANDLES, SELF-MAINTAINING
--------------------------------------------------------------------------------

Every 5 minutes the platform fetches ONE 5M candle and ONE 1H candle.
The buffer:

    - keeps exactly the most recent 800 candles per timeframe
    - evicts the oldest automatically (ring behaviour)
    - rejects an out-of-order candle rather than corrupting the series
    - replaces (does not duplicate) a candle whose timestamp already
      exists — the current 1H bar is re-fetched many times before it
      closes, and appending it 12 times would fabricate 12 hours
    - recomputes all features over the 800 rows
    - exposes the LAST 500 rows as the model input

5.1 WHY 800 AND NOT 500

    Features need warm-up. The catalogue's longest declared lookback is
    51, so ~749 usable rows remain from 800 — comfortably above 500.

    The buffer VERIFIES this at runtime instead of assuming it. If a
    future feature with a longer warm-up reduces the usable rows below
    500, the buffer reports it and refuses to emit a short window. A
    silently truncated input would be a model reading garbage.

--------------------------------------------------------------------------------
6. BACKTEST RUNS ON THE TRAINING DATASET
--------------------------------------------------------------------------------

Explicit user requirement. The backtester already walks candle 0 to N
one at a time through the production trading chain (Phase 16), so no
engine change is required — only the ability to point it at the 100k
dataset.

--------------------------------------------------------------------------------
7. ARCHITECTURE PLACEMENT
--------------------------------------------------------------------------------

    domain/dataset/
        training_dataset.py    NEW  DatasetManifest, DatasetSpec
    infrastructure/data/
        live_buffer.py         NEW  RollingCandleBuffer (ring, ordered)
        dataset_builder_100k.py NEW build + weekly refresh
    infrastructure/ai/
        window_generator.py    NEW  lazy stride-1 windows
        feature_matrix.py      MOD  + 8 raw price columns (123 total)
    application/services/
        training_data_service.py NEW composition root

DEPENDENCY DIRECTION: unchanged; the architecture test still enforces it.

--------------------------------------------------------------------------------
8. WHAT THIS PHASE DOES NOT DO
--------------------------------------------------------------------------------

    - It does not promise 100k real candles exist. MT5 history depth is
      broker-dependent; the builder reports what it actually got rather
      than padding to a round number.
    - It does not schedule itself. A script and a dashboard button are
      provided; wiring them to Windows Task Scheduler belongs to Phase 24.
    - It does not tune the models. That is Phase 17.

================================================================================
END OF PHASE 30
================================================================================
