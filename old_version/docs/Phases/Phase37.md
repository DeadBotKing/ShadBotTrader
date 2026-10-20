================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 37 — FEATURE VISIBILITY & PER-SERIES STORAGE

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    Two user requests:
      1. "when I run Update features, show me which feature is being
         computed right now, how many are done, how many are left"
      2. "and check that features are computed and stored SEPARATELY
         for 5M and 1H"

    The second was a question, not a change request. Answering it
    honestly required admitting a defect: computed yes, stored no.

--------------------------------------------------------------------------------
1. THE GAP
--------------------------------------------------------------------------------

  GAP A — NO PROGRESS OUTPUT

      Computing 109 catalogue features over 100,000 candles takes
      minutes and printed nothing. Same blindness Phase 36 removed from
      training, still present one button to the left.

  GAP B — ONE DIRECTORY FOR EVERY SERIES  (defect)

      The store wrote to:

          features/{feature_id}/v{version}.parquet

      No symbol. No timeframe. So:

          atr_14 for XAUUSD 5M  ->  features/atr_14/v1.parquet
          atr_14 for XAUUSD 1H  ->  features/atr_14/v2.parquet

      Two different quantities — one averaged over five minutes, one
      over an hour — in the same folder, sharing a version counter, with
      nothing recording which was which. load("atr_14", 1) could not say
      what it had returned. The repository contained 22 such anonymous
      versions per feature.

      WHY THIS HAD NOT YET CAUSED A DISASTER

          The models never read this store. build_feature_matrix
          recomputes every feature in memory at training time, so
          training was unaffected and the stored copies were, in
          practice, write-only. The defect was a loaded gun rather than
          a fired one — but /data already read it, and every future
          consumer would have too.

--------------------------------------------------------------------------------
2. THE RULES THIS PHASE ADDS
--------------------------------------------------------------------------------

  RULE 1 — STORED DATA MUST CARRY ITS OWN IDENTITY

          features/{symbol}/{timeframe}/{feature_id}/v{n}.parquet

      A stored series now says what it is from its path alone. Each
      (symbol, timeframe) owns an independent version counter, so
      computing 5M then 1H produces v1 in each rather than v1 and v2 in
      a shared directory.

  RULE 2 — SCOPE THE INSTANCE, NOT THE FROZEN PORT

      FeatureRepository is frozen (Phase 26) and its methods take only
      (feature_id, version). Widening the port would ripple through
      every implementation and every test for a storage concern that
      does not belong in the domain contract. Instead the scope binds to
      the instance:

          store.for_series("XAUUSD", "5M")

      for_series returns a NEW instance rather than mutating: a service
      holding a store must never have its scope changed underneath it by
      an unrelated caller.

  RULE 3 — AN OBSERVER MAY NOT CHANGE WHAT IT OBSERVES

      The reporter contract mirrors ai/training_progress.py on purpose:
      two long-running operations in one product should not report
      progress in two different shapes. A test asserts that running with
      and without a reporter produces byte-identical outcomes.

  RULE 4 — DATA OF UNKNOWN PROVENANCE IS LABELLED, NOT HIDDEN

      Pre-Phase-37 directories cannot have their timeframe recovered —
      and guessing is exactly the error this phase exists to correct.
      /data lists them as "legacy (no timeframe recorded)" so they are
      visible and distrusted rather than silently mixed in.

--------------------------------------------------------------------------------
3. WHAT WAS BUILT
--------------------------------------------------------------------------------

  NEW
      infrastructure/feature/feature_progress.py
          FeatureProgressReporter, NullFeatureProgress,
          ConsoleFeatureProgress
      tests/integration/test_feature_visibility.py
          19 tests across storage, service, progress, button and /data

  CHANGED
      infrastructure/feature/parquet_feature_store.py
          per-series layout, for_series(), scope, root, path sanitising
      application/services/feature_computation_service.py
          progress parameter; scopes the repository per compute_set
      presentation/commands/handlers.py
          compute_features: multi-timeframe, live log, per-series summary
      presentation/gateway/data_inspector.py
          walks the new layout, labels legacy directories
      presentation/web/data_renderer.py
          Series column
      tests/integration/test_feature_pipeline.py
      tests/unit/presentation/test_commands.py
          updated to the new contract (adjusted, not weakened)

--------------------------------------------------------------------------------
4. VERIFICATION
--------------------------------------------------------------------------------

    black --check .                 clean
    ruff check .                    All checks passed
    mypy src --python-version 3.12  289 source files, no issues
    pytest                          1247 passed, 12 skipped
    RUN_TF=1 (three chunks)         278 + 389 + 592

  BEFORE THE FIX (reproduction)

      files under features/atr_14 : ['v1.parquet', 'v2.parquet']
      -> no symbol or timeframe anywhere in the path or the file.

  AFTER THE FIX

      features/XAUUSD/5M/atr_14/v1.parquet    first value 2.7312
      features/XAUUSD/1H/atr_14/v1.parquet    first value 6.5696

  LIVE DASHBOARD TEST

      POST /run command=compute_features timeframe=5M,1H

      succeeded | XAUUSD: features computed for 5M, 1H
        5M: 109/109 stored over 1,000 candles (0 quarantined, 32 research-only)
        1H: 109/109 stored over 1,000 candles (0 quarantined, 32 research-only)

      on disk: 109 feature directories under each of 5M and 1H
      run log: 218 "stored v1" lines (109 x 2)

--------------------------------------------------------------------------------
5. WHAT THIS PHASE DELIBERATELY DID NOT DO
--------------------------------------------------------------------------------

  * The existing datasets/features/ tree was NOT deleted. Deleting a
    user's data without asking is not the agent's call; the provenance
    of those files is unrecoverable; and /data now labels them.
  * Nothing was made to READ the feature store. Training still
    recomputes in memory. Connecting the two is a separate architectural
    decision — recomputation is safer, reading is faster — and pretending
    to have chosen would be worse than leaving it explicit.
  * No progress WITHIN a single feature. A calculator that takes two
    minutes on 100k candles holds one line for two minutes. Granularity
    is per-feature.

================================================================================
