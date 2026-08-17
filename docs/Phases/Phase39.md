================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 39 — STORED MATRIX, DAILY TIMEFRAME, MODEL SELECTION

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    Four user instructions:
      1. read features from the store, with a test proving the loaded
         matrix is byte-for-byte identical to the computed one
      2. do for 1D everything already done for 1H: dataset, features,
         a high/low model, inspection, and retraining
      3. wipe the workspace and clone the repo (real MT5 data inside);
         never ship datasets inside the delivered archive again
      4. let the operator choose WHICH model and WHICH dataset to train,
         and fix training printing nothing in PowerShell

--------------------------------------------------------------------------------
1. READING FROM THE STORE
--------------------------------------------------------------------------------

  build_feature_matrix gained a `source` parameter. It changes only
  WHERE the feature columns come from. The scaling against close, the
  warm-up trim, the tail trim and the column order stay in one place,
  shared by both paths. That sharing is what makes the identity claim
  testable rather than aspirational.

  MEASURED ON THE USER'S REAL 1H DATA

      computed: 2897 x 123   in 3.31s
      loaded  : 2897 x 123   in 1.59s   (2.1x faster)
      BYTES identical : True   (2,850,648 bytes each)

  A DEFECT FOUND ON THE WAY

      The store did not persist `warmup`. It is not a value — it is how
      many leading rows have no honest value — and the matrix uses it to
      decide where to start. Losing it would have made a loaded matrix
      differ from a computed one SILENTLY. It now lives in the Parquet
      schema metadata.

  FOUR GUARDS, EACH FAILING CLOSED

      changed dataset      Phase 38 fingerprint -> None -> recompute
      length mismatch      that feature is refused, with a reason
      timestamp mismatch   refused; same length with different bars is
                           the most dangerous failure mode there is
      partial cache        the WHOLE matrix is recomputed rather than
                           quietly handing the model fewer columns

--------------------------------------------------------------------------------
2. THE DAILY TIMEFRAME
--------------------------------------------------------------------------------

  A broker usually serves 1D directly, so resampling is the fallback,
  not the plan. But the operator already had years of 1H history, and a
  daily bar is fully determined by the hours inside it.

      XAUUSD: 2,255 1D candles from 50,000 1H
        dropped: 2 incomplete buckets | continuity OK
        2017-11-16 O=1277.04  ..  2026-08-14 C=4376.25

  TWO RULES THAT ARE CHEAP TO SKIP AND EXPENSIVE TO MISS

      Incomplete buckets are dropped. The last "day" of an intraday
      series is usually six hours long; its high and low are not the
      day's high and low, and the row looks perfectly normal.

      Buckets are keyed by UTC calendar date, not by counting. A weekend
      therefore produces no bucket instead of welding Friday to Monday.

  EACH TIMEFRAME OWNS ITS MODEL ID

      gold_range_1h and gold_range_1d are different models answering
      different questions. Sharing "gold_range" would make the second
      training run overwrite the first, and the artifact store would
      return whichever was written last with no way to tell.

  FIRST MODEL TRAINED ON REAL GOLD PRICES

      val_mae 0.016225  ->  about 32.45 USD per bound at gold 2,000
      prediction: close 4376.25, high 4458.30, low 4315.72, R/R 1.36

--------------------------------------------------------------------------------
3. WHY POWERSHELL PRINTED NOTHING — TWO REAL CAUSES
--------------------------------------------------------------------------------

  Reproduced on the real data: 208 seconds, zero lines of output.

  CAUSE A — 24,976 FOLDS

      val_size=4, step=2 were sized for the few-hundred-row demo series.
      On 50,000 real candles the expanding split produces 24,976 folds,
      each a complete model fit. That is not a slow run; it is a run
      that never finishes. The geometry now scales with the data:

          val_size=999 step=999 min_train=640  ->  49 folds

  CAUSE B — TEN SILENT SECONDS BEFORE THE FIRST LINE

      Building 50,000 overlapping windows happened BEFORE
      on_train_begin, so the first sign of life came long after the
      button was pressed. It is announced now.

  AND PROGRESS INSIDE AN EPOCH

      An epoch over 50k samples is thousands of batches. A batch line
      updates in place with loss, mae and percentage.

  COMPATIBILITY NOTE

      The reporter contract grew. A reporter written against the older
      contract is still valid — it simply observes less — so missing
      hooks are skipped rather than raising. Observation must never be
      able to break training.

--------------------------------------------------------------------------------
4. VERIFICATION
--------------------------------------------------------------------------------

    black --check .                 clean
    ruff check .                    All checks passed
    mypy src --python-version 3.12  292 source files, no issues
    pytest                          1300 passed, 12 skipped
    RUN_TF=1 (four chunks)          110 + 168 + 592 + 442

  32 new tests. Three older tests were adjusted to the three-timeframe
  world — adjusted, not weakened.

--------------------------------------------------------------------------------
5. WHAT REMAINS HONEST DEBT
--------------------------------------------------------------------------------

  * The 5M signal model on 50k candles is still slow: 49 folds times
    ~6,200 batches per epoch runs for hours. The defaults are not yet
    tuned for data of this size; use --folds 2 for a real run.
  * The 1D range model has only 2,121 windows from nine years of daily
    history. That underfits, and val_mae of ~32 USD on gold at 2,000 is
    too wide to trade. Reported, not hidden.
  * The resampler covers 1H -> 4H/1D only. When the broker serves 1D
    directly, fetching it is better than reconstructing it.

================================================================================
