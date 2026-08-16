"""Concrete AI Platform infrastructure.

* ``in_memory_model_registry`` — model definition catalog.
* ``filesystem_artifact_store`` — artifact persistence with checksums.
* ``training_run_recorder`` — reproducible training-run ledger.
* ``metrics`` — regression/classification/trading metric calculators.
* ``roll_forward`` — walk-forward train/validation splitting.
* ``wavenet`` — the Wavenet model + trainer (TensorFlow adapter).
* ``baseline`` — deterministic reference predictors (no ML framework).
"""
