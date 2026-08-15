"""Concrete Feature Platform infrastructure.

* ``calculators`` — deterministic, causal indicator calculators (the
  indicator knowledge ported from the legacy FeatureEngineering code).
* ``feature_quality_engine`` — NaN/Inf/range/alignment checks.
* ``leakage_checker`` — availability-time <= decision-time enforcement.
* ``parquet_feature_store`` — Parquet persistence of feature results.
* ``in_memory_feature_registry`` — feature definition catalog.
* ``standard_catalog`` — the standard FX feature set (v1).
"""
