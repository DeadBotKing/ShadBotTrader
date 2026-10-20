================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 38 — FEATURE CACHING BY DATASET FINGERPRINT

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    User instruction: "as long as the dataset has not been updated there
    is no need to recompute the features — read them from the store. But
    when the dataset IS updated, the features must be recomputed from
    scratch and stored again."

    Plus an angry and entirely fair question: "are the features actually
    used in the data given to the model for training? I told you before!
    So what matrix are you giving the model?"

--------------------------------------------------------------------------------
1. THE QUESTION, ANSWERED WITH A MEASUREMENT
--------------------------------------------------------------------------------

  The catalogue HAS been in the training matrix since Phase 29:

      matrix given to the model: 297 rows x 123 cols
        candle-derived columns : 14
        CATALOGUE features     : 109

  123 = 14 + 109, and the GUI's training button passes --with-features,
  so the dashboard path always produces the 123-column form.

  WHY THE USER BELIEVED OTHERWISE — THE AGENT'S OWN FAULT

      The Phase 37 report said:

          "the stored features are not read by anyone yet"

      True but misleading. It meant the PARQUET FILES have no consumer.
      It read as "the features are not used".

          features present in the training matrix   YES (109)
          features read from the parquet store      NO (recomputed
                                                    in memory each time)

      The model always received them; the work was merely repeated. The
      sentence conflated the storage layer with the feature values.

      The lesson recorded here: when writing "X is unused", name exactly
      which X. A status document that is technically true and practically
      misleading is worse than one that is silent.

  The claim is now pinned by tests, so neither prose nor code can drift:

      test_the_matrix_carries_all_109_catalogue_features
      test_named_indicators_are_present_by_name
      test_the_prepared_training_dataset_is_123_columns_wide
      test_without_the_catalogue_it_is_only_14_columns
      test_the_gui_training_button_asks_for_the_catalogue
      test_both_timeframes_get_the_full_width

  And the build output now states it outright:

      columns = 14 candle-derived + 109 catalogue features

--------------------------------------------------------------------------------
2. THE RULES THIS PHASE ADDS
--------------------------------------------------------------------------------

  RULE 1 — REUSE WHILE THE SERIES IS UNCHANGED

      Recomputing 109 features over identical candles produces identical
      numbers. Doing it anyway is pure waste, and it fills the store with
      duplicate versions. A cache hit writes nothing at all.

  RULE 2 — A CHANGED SERIES MEANS A FULL RECOMPUTE, NEVER AN APPEND

      EMA, MACD, ATR and every other recursive indicator carry state from
      the first candle. The value computed over 100,000 candles is NOT
      what you get by continuing from candle 99,000 — the difference is
      small, invisible, and caught by no test. So the whole series is
      recomputed, every time anything about it changes.

      Verified: after growing 300 -> 350 candles, the stored result has
      350 points, not 50.

  RULE 3 — DETECT CHANGE BY FINGERPRINT, NOT BY TIMESTAMP

      Modification times lie: a file can be rewritten with identical
      content, or edited in place with the same size and count. The
      fingerprint covers everything that could change a feature value:

          * candle count, first and last open time
          * a digest of EVERY OHLCV value
          * feature-set name and version
          * the list of 109 feature ids

      An in-place edit keeps the count identical, so hashing the count
      alone would have missed it. Hashing the values catches it.

  RULE 4 — WHAT CANNOT BE VOUCHED FOR IS RECOMPUTED

      A corrupt or unreadable fingerprint returns None and forces a full
      recompute. It never raises, and it never silently reuses values
      whose provenance is unknown.

  RULE 5 — THE OPERATOR IS TOLD WHY

      A run that was expected to be instant and instead churns through
      109 features must explain itself:

          recompute : candle count changed: 1,000 -> 1,200
                      (the dataset was updated)

--------------------------------------------------------------------------------
3. WHAT WAS BUILT
--------------------------------------------------------------------------------

  NEW
      infrastructure/feature/feature_cache.py
          FeatureFingerprint, FeatureCache, candles_digest
      tests/integration/test_feature_cache.py
          21 tests: 6 fingerprint, 8 caching rule, 6 catalogue proof

  CHANGED
      application/services/feature_computation_service.py
          force parameter, cache check, _result_from_cache,
          from_cache / reused_count on the result
      infrastructure/feature/feature_progress.py
          on_cache_hit, reason on on_set_begin
      presentation/commands/handlers.py
          REUSED vs recomputed reporting, "Force recompute" field
      scripts/run_training_dataset.py
          prints the 14 + 109 split
      tests/integration/test_feature_visibility.py
          one Phase 37 test adjusted to the new rule (not weakened)

--------------------------------------------------------------------------------
4. VERIFICATION
--------------------------------------------------------------------------------

    black --check .                 clean
    ruff check .                    All checks passed
    mypy src --python-version 3.12  290 source files, no issues
    pytest                          1267 passed, 13 skipped
    RUN_TF=1 (three chunks)         278 + 410 + 592

  MEASURED CACHE BEHAVIOUR

    1. first run (1000 candles)        reused=  0/109  1.54s
    2. same candles again              reused=109/109  0.53s
    3. same candles a third time       reused=109/109  0.52s
    4. AFTER dataset update (1100)     reused=  0/109  1.63s
    5. same 1100 again                 reused=109/109  0.53s

    versions on disk: v1, v2 — repeated runs add nothing.

  LIVE DASHBOARD

    run 1:  5M: 109/109 recomputed over 1,000 candles
    run 2:  5M: 109 feature(s) REUSED — the dataset has not changed
    after updating the dataset to 1,200 candles:
            5M: 109/109 recomputed over 1,200 candles
            log: "candle count changed: 1,000 -> 1,200"

--------------------------------------------------------------------------------
5. THE DEBT THIS PHASE DELIBERATELY DID NOT PAY
--------------------------------------------------------------------------------

  THE TRAINING MATRIX STILL DOES NOT READ THE PARQUET STORE.

  The cache covers FeatureComputationService — the "Update features"
  button. build_feature_matrix, which produces the model's input, still
  computes independently in memory. So "Build training dataset" still
  costs about two minutes per 100k candles even when the features were
  just computed.

  WHY IT WAS NOT CONNECTED HERE

      The model matrix normalises price-valued features against the
      close of their own row (is_price_scaled); the store holds raw
      values. Wiring them together means moving that normalisation, and
      getting it wrong trains the model on the wrong scale — silently.

      That deserves its own phase with a test asserting the loaded
      matrix is byte-identical to the computed one, not a hurried patch
      at the end of this one.

  Also unchanged: the cache ignores dataset_version and looks only at
  candle content. Deliberate — a version can increment without any
  number changing.

================================================================================
