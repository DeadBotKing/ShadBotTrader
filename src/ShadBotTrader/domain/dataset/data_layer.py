"""The L0..L9 data layers of the Data Platform."""

from __future__ import annotations

from enum import Enum


class DataLayer(str, Enum):
    """The canonical data layers defined by Phase 11."""

    EXTERNAL = "L0_external"
    RAW = "L1_raw"
    VALIDATED = "L2_validated"
    NORMALIZED = "L3_normalized"
    PROCESSED = "L4_processed"
    FEATURE = "L5_feature"
    TRAINING = "L6_training"
    MODEL_OUTPUT = "L7_model_output"
    OPERATIONAL = "L8_operational"
    ARCHIVE = "L9_archive"
