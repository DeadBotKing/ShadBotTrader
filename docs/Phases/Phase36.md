================================================================================

SHADBOTTRADER — ENTERPRISE AI TRADING PLATFORM

================================================================================

PHASE 36 — TRAINING VISIBILITY

================================================================================

STATUS:
    ARCHITECTURE DESIGN + IMPLEMENTATION

DATE:
    2026-08-17

AUTHORISED BY:
    User report: "when I press Train both models, neither PowerShell nor
    the web page shows me anything about the training — no accuracy, no
    percentage."

--------------------------------------------------------------------------------
1. THE GAP
--------------------------------------------------------------------------------

  One symptom, four independent causes. Each would have been enough on
  its own to produce total silence, which is why fixing any single one
  would not have helped.

  CAUSE A — THE OUTPUT WAS BUFFERED UNTIL THE PROCESS EXITED

      completed = subprocess.run([...], capture_output=True, text=True)
      output = completed.stdout.strip().splitlines()

      subprocess.run does not return until the child exits. A twenty
      minute training run therefore produced nothing for twenty minutes
      and then twenty lines at once. The dashboard told the operator to
      "reload the page to check progress" — and reloading showed the
      same emptiness, because the output did not exist yet.

  CAUSE B — THE PROGRESS REPORTER WAS NEVER PASSED

      infrastructure/ai/training_progress.py has contained a complete
      ConsoleProgressReporter since Phase 13: progress bar, ETA, and
      per-epoch loss and accuracy. But:

          self._progress = progress or NullProgressReporter()

      and no caller ever supplied progress=. Every run used the null
      reporter, whose methods all `return None`. Keras verbose=0
      completed the silence.

  CAUSE C — ACCURACY WAS COMPUTED AND THROWN AWAY

          val_loss = float(history.history["val_loss"][-1])
          self.fold_history.append(val_loss)

      Keras produced accuracy, val_accuracy and mae every epoch; the
      trainer kept the loss and discarded the rest. "Is the model any
      good?" had no answer anywhere in the system — not in the CLI, not
      in the API, not in the database.

  CAUSE D — THE DASHBOARD'S STORAGE ROOT NEVER REACHED THE SCRIPTS

      Found while verifying this phase against a live server. Handlers
      that talk to the store directly honoured self._storage_root, but
      the four buttons that shell out to a script did not pass it, so
      those scripts silently used the repository default. The operator
      saw thousands of candles on /data and "no stored candles" from
      training, at the same moment.

--------------------------------------------------------------------------------
2. THE RULES THIS PHASE ADDS
--------------------------------------------------------------------------------

  RULE 1 — A LONG RUN MUST BE OBSERVABLE WHILE IT RUNS

      Silence and a hang are indistinguishable to an operator. Scripts
      are now launched with Popen and read line by line into
      run_logs/{command}.log, which the dashboard polls.

      Three details are each individually necessary:

        PYTHONUNBUFFERED=1   Python buffers 8 KB of stdout when the far
                             end is a pipe rather than a terminal. Without
                             this the log arrives in bursts, minutes late.
        bufsize=1, text=True Line buffering on the reading side.
        poll + final reload  The page refreshes the log every 2 seconds
                             and reloads once when the run ends, so the
                             result panel appears without user action.

  RULE 2 — A METRIC WITHOUT A BASELINE IS NOT A MEASUREMENT

      In a 3-class problem where 70% of the samples are HOLD, a model
      that always answers HOLD scores 70% accuracy and has learned
      nothing. Reporting "70%" alone actively misleads. Every accuracy
      is therefore printed next to the majority-class baseline, and the
      verdict is stated in words:

          val_accuracy 100.0% vs majority-class baseline 47.4%
          -> the model is BETTER than always predicting the commonest class.

      When the baseline wins, it says NO BETTER than. It is not softened.

  RULE 3 — THE RANGE MODEL'S ERROR IS REPORTED IN MONEY

      val_mae is a fraction of price, which is unreadable. It is also
      printed as USD at a reference price, because "2.00 USD per bound"
      is a quantity a trader can judge and "0.001" is not.

  RULE 4 — ONE LIVE LOG PER COMMAND, OVERWRITTEN

      The question being answered is "what is happening right now".
      An archive of previous attempts makes that harder, not easier;
      finished runs are already summarised in the command history.

--------------------------------------------------------------------------------
3. WHAT WAS BUILT
--------------------------------------------------------------------------------

  NEW
      tests/integration/test_training_visibility.py
          23 regression tests, one class per cause

  CHANGED
      presentation/commands/handlers.py
          _run_script rewritten around Popen with live streaming;
          RUN_LOG_DIR, run_log_path(), read_run_log();
          --storage-root passed to all four script-backed buttons
      presentation/web/server.py
          GET /api/log
      presentation/web/renderer.py
          live log panel, polling JS, .runlog style
      infrastructure/ai/wavenet/wavenet_trainer.py
          fold_metrics: final-epoch value of every metric, per fold
      application/services/dual_model_service.py
          surfaces fold_metrics in the training outcome
      scripts/run_dual_models.py
          ConsoleProgressReporter wired in, --quiet, print_quality()
      .gitignore
          run_logs/

--------------------------------------------------------------------------------
4. VERIFICATION
--------------------------------------------------------------------------------

    black --check .                 clean
    ruff check .                    All checks passed
    mypy src --python-version 3.12  288 source files, no issues
    pytest                          1228 passed, 12 skipped
    RUN_TF=1 (three chunks)         278 + 370 + 592

  LIVE TEST AGAINST A RUNNING DASHBOARD

    POST /run command=train_dual_models, then polling /api/log:

        [8s]  busy=True   lines=32
        [16s] busy=True   lines=33
        [24s] busy=True   lines=63
        [32s] busy=True   lines=77
        [40s] busy=False  (finished)

    The log grew WHILE the process was running — the thing that was
    impossible before this phase.

--------------------------------------------------------------------------------
5. AN HONEST NOTE ABOUT THE NUMBERS IN THAT TEST
--------------------------------------------------------------------------------

  The verification run reported val_accuracy 100% on FOUR validation
  samples, against synthetic sine-wave candles (real MT5 data is only
  reachable on the user's Windows machine). Four samples means each one
  carries 25% of the score. That number says nothing about model
  quality; it only proves the reporting path works.

  On real data with more folds and a larger validation window, expect a
  far lower figure. If 100% appears there, it indicates data leakage,
  not success.

--------------------------------------------------------------------------------
6. WHAT THIS PHASE DELIBERATELY DID NOT DO
--------------------------------------------------------------------------------

  * No progress WITHIN an epoch. On real data an epoch may take minutes,
    which would need a batch-level callback. Granularity is per-epoch.
  * fold_metrics is not persisted to the database, so comparing the
    quality of two training runs is still a manual act.
  * No authentication on /api/log. It exposes the same information the
    dashboard already shows, and the dashboard still has no auth — the
    log endpoint does not make that worse, but it does not fix it.

================================================================================
