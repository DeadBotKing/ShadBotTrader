================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 33 — INCREMENTAL DATASET UPDATES & CONTINUITY

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    User question that exposed a defect: "does Fetch market data append to
    the dataset, keep the last 100,000, and verify the candles join with
    no hole in between?" The answer was no on all three counts.

--------------------------------------------------------------------------------
1. THE DEFECT
--------------------------------------------------------------------------------

  EXPECTED                        | ACTUAL BEFORE PHASE 33
  --------------------------------|-------------------------------------
  new candles appended            | a NEW VERSION was written and query()
                                  | read only the latest -> 200 stored
                                  | candles plus 50 new ones left 50
  rolling 100,000 limit           | no such concept existed
  continuity across updates       | no check at all; QualityAnalyzer saw
                                  | gaps only WITHIN one version, never
                                  | between the stored and the new data

Demonstrated, not assumed:

    ingest #1 : v1  candles stored=200
    ingest #2 : v2  candles stored=50     <-- history destroyed

--------------------------------------------------------------------------------
2. THE HARD PART: A GAP IS NOT ALWAYS A GAP
--------------------------------------------------------------------------------

Markets close. "No candle on Saturday" is normal; "no candle on Tuesday"
is missing data. A naive check would either flag every weekend or miss
every real hole.

2.1 THE CALENDAR IS LEARNED, NOT DECLARED

    From the stored history:

        if every Saturday in the history had no candles,
        Saturday is a closed day

    Evidence for gold, read off 40 candles:

        Mon (10,10) Tue (10,10) Wed (10,10) Thu (10,10) Fri (10,10)
        Sat  (0,10) Sun  (0,10)          -> closed on Sat, Sun

    A hard-coded calendar would be wrong for crypto, wrong for a broker
    in another timezone, and stale within a year. A learned one adapts to
    any instrument automatically and its evidence is inspectable.

2.2 RESULT

    last stored candle: Tuesday 9 July

        next trading day      -> joins cleanly
        3 days later          -> 2 candles missing
        one month later       -> 21 missing (not 30: weekends excluded)

--------------------------------------------------------------------------------
3. UPDATE PIPELINE
--------------------------------------------------------------------------------

    load stored history
      -> fetch new candles
      -> check the join (closed days excluded)
      -> BACKFILL the gap from the broker when there is one
      -> merge, de-duplicate, keep the newest N
      -> verify continuity
      -> write

3.1 VERIFY BEFORE WRITING

    A failed update must leave the previous dataset exactly as it was.
    Writing first and validating afterwards would leave a corrupt dataset
    behind on every failure.

3.2 THE INCOMING CANDLE WINS A COLLISION

    A re-fetched bar is a correction: the current 1H candle is read many
    times before it closes, and the newest read is the accurate one.

3.3 REFUSAL IS THE DEFAULT

    An unrepairable gap refuses the update. Joining across a hole teaches
    the model a price move that never happened, and no test downstream
    would ever catch it. ``allow_gap`` exists for the operator who
    understands the trade-off and accepts it deliberately.

--------------------------------------------------------------------------------
4. ARCHITECTURE PLACEMENT
--------------------------------------------------------------------------------

    domain/dataset/continuity.py             NEW  MarketCalendar, Gap,
                                                  analyse_continuity,
                                                  check_join, merge_candles
    application/services/
        dataset_update_service.py            NEW  the update pipeline
    presentation/commands/handlers.py        MOD  Fetch now appends

DEPENDENCY DIRECTION: unchanged.

--------------------------------------------------------------------------------
5. WHAT THIS PHASE DOES NOT DO
--------------------------------------------------------------------------------

    - It does not invent missing candles. Interpolating a price the
      market never printed is worse than an honest refusal.
    - It does not use an external holiday calendar. The learned one is
      derived from the broker's own data, which is the only authority
      that matters here.

================================================================================
END OF PHASE 33
================================================================================
