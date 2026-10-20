================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 32 — ACCOUNT PROFILES & COMPLETE GUI CONTROL

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    Explicit user requirement after the first successful MT5 connection
    (Alpari-MT5-Demo, 882 symbols, 1046 tests green on Windows).
    Extends Phases 19 and 32; changes no frozen contract.

--------------------------------------------------------------------------------
PURPOSE
--------------------------------------------------------------------------------

    سه نیاز:

        1. تعویض اکانت (login / server / password) از داخل GUI
        2. نام نماد در هر بروکر فرق می‌کند: XAUUSD در یکی، XAUUSD_i در دیگری
        3. همهٔ ران‌ها فقط از طریق GUI اجرا شوند

--------------------------------------------------------------------------------
1. THE GAP
--------------------------------------------------------------------------------

  CAPABILITY                     | BEFORE PHASE 32
  -------------------------------|--------------------------------------
  Several broker accounts        | ABSENT. Credentials were CLI flags,
                                 | lost the moment the command ended.
  Per-broker symbol names        | ABSENT. mt5_symbol_resolver could
                                 | *suggest* a name, but nothing stored
                                 | the decision or applied it to a run.
  Every run in the GUI           | PARTIAL. 18 scripts, 8 buttons.
                                 | Ten operations were terminal-only.

--------------------------------------------------------------------------------
2. ACCOUNT PROFILES
--------------------------------------------------------------------------------

A profile bundles everything one account needs:

    name           a short handle, also used as a filename fragment
    login          the MT5 account number
    server         e.g. Alpari-MT5-Demo
    terminal_path  optional, when several terminals are installed
    symbol_map     canonical name -> this broker's name
    is_demo        demo or live

2.1 PASSWORDS ARE NEVER STORED

    The profile records only WHICH environment variable holds the
    password:

        SHADBOT_MT5_PASSWORD_{PROFILE}

    RATIONALE: a credential in a JSON file next to the code is one
    screenshot, one screen-share or one zip away from being public. The
    profile store can therefore be backed up and diffed safely.

    Resolution order at connect time:

        1. a password typed for this session
        2. SHADBOT_MT5_PASSWORD_{PROFILE}
        3. SHADBOT_MT5_PASSWORD  (shared fallback)
        4. None -> reuse the terminal's existing session

    Option 4 is the normal case: MetaTrader is usually already logged in,
    so the platform never needs the password at all.

--------------------------------------------------------------------------------
3. PER-ACCOUNT SYMBOL MAPPING
--------------------------------------------------------------------------------

The platform speaks ONE canonical name internally and each profile
translates on the way out:

    canonical  XAUUSD
      Alpari   -> XAUUSD
      Broker B -> XAUUSD_i
      Broker C -> GOLD

WHY THIS MATTERS: without it, the same instrument produces three
datasets, three feature matrices and three sets of models that cannot be
compared. Switching brokers would silently restart the learning history.

The alias map is per profile because the difference IS per broker; a
global map would be wrong for whichever account it was not written for.

3.1 DETECTION, NOT GUESSING

    "Detect symbol names" asks the broker for its symbol list and
    proposes a mapping using the Phase 32 resolver. Suggestions are
    APPLIED ONLY ON CONFIRMATION. Silently binding a dataset to a guessed
    instrument is precisely the failure this mechanism exists to prevent.

--------------------------------------------------------------------------------
4. COMPLETE GUI CONTROL
--------------------------------------------------------------------------------

Every platform operation is now a button, grouped so twenty-one controls
read as a panel rather than a wall:

    Accounts    add / switch / check / map symbol / detect / remove
    Data        fetch / features / build dataset / weekly update
    AI          retrain direction model / train both models
    Simulation  backtest / replay / optimisation
    Trading     trading cycle / execution demo / one live tick
    Operations  backup / health / refresh project state

4.1 SCRIPTS DELIBERATELY NOT IN THE GUI

    run_dashboard.py   starts the GUI itself
    run_service.py     the supervisor that would host the GUI
    parquet_view.py    a file inspector, not a platform run
    run_pip.py         identical to "Refresh project state"
    run_persistence.py a storage demo, superseded by real runs
    run_real_data.py   guided wizard, replaced by Accounts + Fetch

    Each exclusion is recorded in a test, so the list cannot quietly
    become a place to hide a missing button.

4.2 LONG RUNS EXECUTE IN A SUBPROCESS

    Dataset builds and training run as child processes: a crash inside
    one cannot take the dashboard down, and each has a time limit.

--------------------------------------------------------------------------------
5. ARCHITECTURE PLACEMENT
--------------------------------------------------------------------------------

    domain/account/profile.py          NEW  AccountProfile, SymbolMap,
                                            AccountBook
    infrastructure/account/
        profile_store.py               NEW  persistence + connection
    presentation/commands/
        commands.py                    MOD  13 new CommandKinds, groups
        handlers.py                    MOD  AccountCommandHandlers
    presentation/web/
        renderer.py                    MOD  grouped actions, account panel
        server.py                      MOD  account store wiring

DEPENDENCY DIRECTION: unchanged; the architecture test still enforces it.

--------------------------------------------------------------------------------
6. WHAT THIS PHASE DOES NOT DO
--------------------------------------------------------------------------------

    - No OS keychain integration. An environment variable is the right
      level for a single-machine install; a keyring adds a dependency
      and a failure mode for no real gain here.
    - No dashboard authentication. The GUI binds to localhost by default;
      exposing it to a network needs auth first, and that is a separate
      decision.
    - Symbol detection does not auto-apply. Confirmation is required.

================================================================================
END OF PHASE 32
================================================================================
