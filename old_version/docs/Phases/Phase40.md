================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 40 — MODEL SELECTION, PERSISTENCE, AND A CLEAN WORKSPACE

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    User instructions:
      1. make the model type a dropdown (price prediction vs signal)
      2. remove the Signal dataset / Range dataset(s) fields
      3. one dropdown listing the datasets we actually have (5M/1H/1D)
      4. save the model under its role and the dataset it learned from
      5. let "Retrain" pick from a dropdown of saved models and datasets
      6. empty the workspace of real data; generate small test data
         instead, and never ship data inside the delivered archive

--------------------------------------------------------------------------------
1. WHAT INSTRUCTION 4 EXPOSED
--------------------------------------------------------------------------------

  run_dual_models.py NEVER SAVED THE MODEL.

  It fitted a network, printed a prediction, and exited.

      $ ls datasets/models
      ls: cannot access 'datasets/models': No such file or directory
      $ find . -name "*.bin"
      (nothing)

  Every training run since Phase 29 was discarded at process exit —
  including the daily range model trained on real gold the day before,
  which reported val_mae 0.0164. Only the number survived, in a report.

  The defect was invisible until the user asked for a list of saved
  models: the list was always empty, and an empty list looks like "you
  have not trained anything yet" rather than "the save step does not
  exist".

  A SECOND DEFECT, FOUND WHILE TESTING

      train_model lived on CommandHandlers; _run_script lived only on
      AccountCommandHandlers. Pressing "Retrain" would have raised
      AttributeError immediately. AccountCommandHandlers now INHERITS
      from CommandHandlers, which makes the class of mistake impossible
      rather than merely fixing this instance of it.

--------------------------------------------------------------------------------
2. THE RULES THIS PHASE ADDS
--------------------------------------------------------------------------------

  RULE 1 — A DROPDOWN MAY ONLY OFFER WHAT EXISTS

      The dataset list is built from datasets/processed/, and the saved
      model list from datasets/models/. Offering a timeframe with no
      candles would be offering a guaranteed failure three minutes into
      a subprocess. An empty options tuple falls back to a text input:
      an empty dropdown is not a choice, it is a dead end.

  RULE 2 — A SAVED MODEL RECORDS WHAT PRODUCED IT

      model_id alone implies its dataset by convention. The sidecar
      states it:

          role       range | signal
          timeframe  the dataset it trained on
          symbol     the instrument
          rows/windows/feature_columns
          metrics    the final fold's val_loss / val_mae / val_accuracy

      That record is what fills the dropdown, so the list can never
      advertise a model whose files are gone.

  RULE 3 — RETRAINING ADDS A VERSION, IT DOES NOT REPLACE ONE

      Artifacts are immutable. The only honest way to keep both the old
      and the new weights is to renumber the new ones, so
      ModelArtifact.with_version() copies the artifact under a new
      number with payload and checksum untouched.

  RULE 4 — THE ROLE COMES FROM THE RECORD, NOT THE FILENAME

      Retraining reads the stored role, so a range model is always
      retrained as a range model. Choosing a different dataset than the
      original is ALLOWED but warned about: changing the market rhythm a
      model learned is the operator's decision, not an error, and
      silently permitting it would hide a real change.

  RULE 5 — GENERATED DATA CANNOT WEAR A REAL NAME

      scripts/make_test_data.py writes under TESTSYM, which is not an
      alias of any real instrument, and produces 600 candles — enough to
      exercise the pipeline, far too few to be mistaken for history.

--------------------------------------------------------------------------------
3. WHAT WAS BUILT
--------------------------------------------------------------------------------

  NEW
      infrastructure/ai/model_catalogue.py   ModelRecord, ModelCatalogue
      scripts/make_test_data.py              small synthetic series
      tests/integration/test_model_selection.py   30 tests

  CHANGED
      presentation/commands/commands.py    CommandField.kind="select"
      presentation/web/renderer.py         _render_field -> <select>
      presentation/commands/handlers.py    dropdowns; train/retrain
                                           handlers; inheritance fix
      domain/ai/model_artifact.py          with_version()
      scripts/run_dual_models.py           save_model()

--------------------------------------------------------------------------------
4. VERIFICATION
--------------------------------------------------------------------------------

    black --check .                 clean
    ruff check .                    All checks passed
    mypy src --python-version 3.12  293 source files, no issues
    pytest                          1330 passed, 12 skipped
    RUN_TF=1 (three chunks)         278 + 472 + 592

  LIVE

      <select name="saved_model"> [gold_range_1d selected]
      <select name="dataset">     [5M selected] [1H] [1D]
      <select name="model">       [all] [range selected] [signal]

      train -> SAVED gold_range_1d v1
      retrain from the dashboard -> v3, with v1 and v2 intact
      data files in the delivered zip: 0

--------------------------------------------------------------------------------
5. HONEST DEBT
--------------------------------------------------------------------------------

  * 'all' still trains the signal model on 5M regardless of the chosen
    dataset. Deliberate: a signal model on daily candles is a different
    product, not a setting, and changing it silently would be worse than
    constraining it. Pick Model type = signal to choose its dataset.
  * model_id does not include the symbol, so training gold_range_1d on
    TESTSYM and then on XAUUSD produces two VERSIONS of one model rather
    than two models. Multi-symbol support needs the id to carry it.
  * Only the latest version of each model is offered in the dropdown.
    Older versions remain on disk but cannot be selected from the GUI.

================================================================================
