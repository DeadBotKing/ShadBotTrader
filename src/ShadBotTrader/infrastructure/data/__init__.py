"""Concrete Data Platform infrastructure.

* ``csv_market_data_provider`` — reads raw candle CSV files (L0/L1).
* ``candle_validator``       — validates raw records (L2).
* ``candle_normalizer``      — canonicalises symbol/timeframe/UTC (L3).
* ``quality_analyzer``       — gaps, duplicates, outliers.
* ``parquet_candle_store``   — Parquet storage (PyArrow).
* ``in_memory_dataset_catalog`` — in-memory dataset registry.
"""
