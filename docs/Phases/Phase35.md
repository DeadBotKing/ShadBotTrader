================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 35 — DUAL-TIMEFRAME DATASETS & REAL DATA ONLY

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    User question: "why doesn't Build training dataset care about the
    timeframe? shouldn't we have two datasets, one 5-minute and one
    1-hour?" followed by four explicit instructions:
      1. fetch both and build two separate datasets
      2. never generate samples; drop rows that have no data, but only
         at the START of the dataset, because of indicators like SMA
      3. real data only — samples are for the agent's own testing
      4. unify XAUUSD and XAUUSD_i into one dataset

--------------------------------------------------------------------------------
1. THE GAP
--------------------------------------------------------------------------------

  The platform ALREADY built two datasets. DatasetSpec.timeframes has
  defaulted to ("5M", "1H") since Phase 30 and TrainingDataService.build
  loops over them, writing 5M_matrix.npz and 1H_matrix.npz side by side.
  So the answer to the user's question was "it does" — but three
  defects made that untrue in practice.

  DEFECT A — ONE TIMEFRAME IN, TWO NEEDED
      "Fetch market data" had a single Timeframe field defaulting to 5M.
      An operator following the documented sequence fetched 5M, then
      pressed Build, which required 1H as well.

  DEFECT B — SILENT SYNTHETIC SUBSTITUTION
      load_candles() in run_training_dataset.py:

          if len(candles) < wanted:
              generate_sample(args.symbol, timeframe, wanted, sample)
              service.ingest(args.symbol, timeframe, str(sample))

      A sine wave was written into the store under the REAL symbol. One
      run later nothing distinguishes it from broker history. The range
      model would train on it and report a loss curve that looks fine.
      This violates DEVELOPMENT_RULES.md ("never build fake
      implementations") in its most damaging form: fake DATA.

  DEFECT C — ROWS COULD BE CUT FROM THE MIDDLE
      build_feature_matrix skipped any row where any feature was None:

          for feature_id in ...:
              if value is None or not isfinite(value):
                  usable = False
          if not usable:
              continue

      Warm-up rows are at the front, so in practice this mostly cut the
      front — but nothing GUARANTEED it. A NaN at row 4,000 removed row
      4,000 and welded 3,999 to 4,001. The stride-1 roll-forward would
      then step across market it never saw, and no test would notice.

  DEFECT D — ONE INSTRUMENT, TWO DATASETS
      Fetch stored candles under the broker's spelling; everything else
      read the canonical one:

          fetch  -> processed/XAUUSD_I/5M/v1.parquet
          build  -> looks in processed/XAUUSD/5M/     (empty)
                 -> falls through to Defect B

--------------------------------------------------------------------------------
2. THE RULES THIS PHASE ADDS
--------------------------------------------------------------------------------

  RULE 1 — THE TRAINING TIMEFRAMES TRAVEL TOGETHER

      TRAINING_TIMEFRAMES = ("5M", "1H")

      5M feeds the signal model; 1H feeds the range model. Building with
      only one of them is not a smaller dataset, it is a missing model.
      The Fetch button therefore takes a LIST and defaults to "5M,1H";
      each timeframe is merged independently, so one refusal does not
      roll back the other.

  RULE 2 — NO GENERATED CANDLE IS EVER STORED UNDER A REAL SYMBOL

      Missing data is an error with an instruction, never a silent
      substitution:

          [X] No stored candles for XAUUSD 5M.
              symbols on disk: none
              Fix it from the dashboard: Data -> Fetch market data
              with Timeframes = 5M,1H. Sample data is deliberately not
              generated any more (Phase 35).

      The demo scripts still generate candles — that is what they are
      for — but under DEMOXAU, a symbol that is not an alias of anything
      real. A test enforces this: any script calling generate_sample()
      must not name a gold symbol.

  RULE 3 — ROWS LEAVE ONLY FROM THE ENDS

      Three structurally different situations, three different answers:

        WHERE       EXAMPLE                    ACTION
        ----------- -------------------------- ----------------------
        front       SMA 200 before candle 200  drop rows (warm-up)
        tail        chikou, *_target_p1        drop rows (forward)
        interior    a NaN mid-series           drop the COLUMN

      The front and tail cuts keep survivors consecutive. An interior
      hole is the only case that would break that, so it costs a column
      instead. FeatureMatrix.is_contiguous makes the guarantee explicit
      and TimeframeSlice records it in the manifest.

      Measured on 1,000 candles with the full 109-feature catalogue:
          front cut 77 | tail cut 26 | 897 rows x 123 cols | contiguous

  RULE 4 — FETCH UNDER THE BROKER'S NAME, STORE UNDER OURS

          fetched as    : XAUUSD_i
          stored as     : XAUUSD (canonical)

      DatasetUpdateService.fetch_and_update(..., store_as=...) relabels
      the candles before merging. Gap backfill still ASKS MetaTrader
      using the broker spelling, because that is the only name MT5
      knows, and relabels the answer.

      History written the old way stays reachable: symbol_scope.py
      searches the canonical name first, then every profile alias, and
      SAYS SO when it falls back. Silence would repeat the original
      mistake.

--------------------------------------------------------------------------------
3. WHAT WAS BUILT
--------------------------------------------------------------------------------

  NEW
      infrastructure/data/symbol_scope.py
          StoredSymbol, alias_candidates, resolve_stored_symbol,
          stored_symbols
      tests/integration/test_dual_timeframe_datasets.py
          23 regression tests, one class per defect

  CHANGED
      infrastructure/ai/feature_matrix.py
          _first_valid_index / _last_valid_index / _has_hole;
          holed_features, dropped_tail, is_contiguous
      domain/dataset/training_dataset.py
          TimeframeSlice.contiguous / tail_dropped / holed_features;
          three new warnings
      application/services/training_data_service.py
          passes the new fields into the slice
      application/services/dataset_update_service.py
          store_as, _relabel, broker-aware backfill
      presentation/commands/handlers.py
          parse_timeframes, TRAINING_TIMEFRAMES, multi-timeframe fetch,
          missing_timeframes pre-check, no sample fallback
      scripts/run_training_dataset.py, run_dual_models.py,
      run_weekly_update.py, run_live_loop.py
          NoRealData instead of generate_sample; alias resolution
      scripts/run_{ai,backtest,features,data,optimisation,replay,
      dashboard,execution,persistence,trading}.py
          demo symbol XAUUSD_i -> DEMOXAU
      src/ShadBotTrader/*_cli.py
          defaults XAUUSD_i -> XAUUSD (real) or DEMOXAU (sample command)

--------------------------------------------------------------------------------
4. WHAT THIS PHASE DELIBERATELY DID NOT DO
--------------------------------------------------------------------------------

  * run_live_loop.py --demo still fabricates candles. It exists to
    exercise the wiring, and the fabrication is now IN MEMORY ONLY —
    it never touches the store.
  * The other demo scripts still call generate_sample(). They are demos.
    They now write under DEMOXAU, so they cannot contaminate a real
    dataset, and a test keeps it that way.
  * No timeframe field was added to "Build training dataset". Offering
    one would let an operator build 5M against a stale 1H, and the two
    models would then be trained on histories ending at different
    moments. The pair is the unit.

--------------------------------------------------------------------------------
5. VERIFICATION
--------------------------------------------------------------------------------

    black --check .                 407 files unchanged
    ruff check .                    All checks passed
    mypy src --python-version 3.12  288 source files, no issues
    pytest                          1205 passed, 12 skipped
    RUN_TF=1 (three chunks)         278 + 344 + 592

    Demo run twice; second run added 0 candles and produced identical
    digests for both slices.

================================================================================
