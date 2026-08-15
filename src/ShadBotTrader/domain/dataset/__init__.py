"""Dataset domain: identity, versioning, schemas, descriptors and ports.

This bounded context is framework-independent. It owns the contracts the
Data Platform relies on (repositories and providers) and the value
objects that describe datasets; the concrete Parquet/CSV/SQL
implementations live in ``ShadBotTrader.infrastructure.data``.
"""
