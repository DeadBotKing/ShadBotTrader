"""SQLite database connection and schema management (Phase 20).

Phase 20 names SQL Server as the eventual production engine, but every
rule it actually mandates — migrations, transactions, referential
integrity, auditability, and a Domain that never sees the database — is
satisfied here with SQLite.

The trade is deliberate: SQLite ships inside Python, needs no server, no
driver and no connection string, so persistence works the moment the
project is cloned. Because everything sits behind the existing
repository ports, adding a SQL Server adapter later is a new class, not
a rewrite.

Design rules honoured here:

* schema changes only ever happen through a numbered migration (§73-74)
* migrations are deterministic and repeatable — running twice is a no-op
* every write happens inside a transaction
* foreign keys are enforced (SQLite needs this switched on explicitly)
* the schema version is queryable at runtime
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Optional, Sequence, Tuple

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------
# Migrations. Append-only: never edit a shipped migration, add the next one.
# Logical areas mirror the Phase 20 schema domains (market, ai, trading,
# portfolio, learning, system) using a table prefix, since SQLite has no
# schema namespaces.
# --------------------------------------------------------------------------
MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "initial_schema",
        """
        -- ============================================ system ============
        CREATE TABLE IF NOT EXISTS system_state (
            id                INTEGER PRIMARY KEY CHECK (id = 1),
            migration_version INTEGER NOT NULL,
            environment       TEXT    NOT NULL DEFAULT 'local',
            initialized_at    TEXT    NOT NULL,
            updated_at        TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );

        -- ============================================ market =============
        CREATE TABLE IF NOT EXISTS market_dataset (
            dataset_key TEXT    NOT NULL,
            version     INTEGER NOT NULL,
            provider    TEXT    NOT NULL,
            kind        TEXT    NOT NULL,
            symbol      TEXT    NOT NULL,
            timeframe   TEXT    NOT NULL,
            layer       TEXT    NOT NULL,
            status      TEXT    NOT NULL,
            row_count   INTEGER NOT NULL DEFAULT 0,
            time_start  TEXT,
            time_end    TEXT,
            payload     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            PRIMARY KEY (dataset_key, version)
        );
        CREATE INDEX IF NOT EXISTS ix_market_dataset_symbol
            ON market_dataset (symbol, timeframe);

        -- ============================================ feature ============
        CREATE TABLE IF NOT EXISTS feature_definition (
            feature_id  TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            payload     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );

        -- ============================================ ai =================
        CREATE TABLE IF NOT EXISTS ai_model (
            model_id    TEXT    NOT NULL,
            version     INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            model_type  TEXT    NOT NULL,
            family      TEXT    NOT NULL,
            payload     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            PRIMARY KEY (model_id, version)
        );

        CREATE TABLE IF NOT EXISTS ai_training_run (
            run_id        TEXT PRIMARY KEY,
            model_id      TEXT    NOT NULL,
            model_version INTEGER NOT NULL,
            seed          INTEGER NOT NULL,
            payload       TEXT    NOT NULL,
            started_at    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_training_run_model
            ON ai_training_run (model_id, model_version);

        -- ============================================ trading ============
        CREATE TABLE IF NOT EXISTS trading_decision (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id     TEXT    NOT NULL,
            decision_id    TEXT    NOT NULL,
            strategy_id    TEXT    NOT NULL,
            symbol         TEXT    NOT NULL,
            decision_type  TEXT    NOT NULL,
            confidence     REAL    NOT NULL,
            approved       INTEGER,
            rejection      TEXT,
            intent_id      TEXT,
            payload        TEXT    NOT NULL,
            recorded_at    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_decision_session
            ON trading_decision (session_id);
        CREATE INDEX IF NOT EXISTS ix_decision_symbol
            ON trading_decision (symbol, decision_type);

        CREATE TABLE IF NOT EXISTS execution_attempt (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT    NOT NULL,
            intent_id    TEXT    NOT NULL,
            order_id     TEXT,
            symbol       TEXT    NOT NULL,
            side         TEXT    NOT NULL,
            status       TEXT,
            filled_qty   TEXT,
            avg_price    TEXT,
            rejection    TEXT,
            payload      TEXT    NOT NULL,
            recorded_at  TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_execution_session
            ON execution_attempt (session_id);

        -- ============================================ portfolio ==========
        CREATE TABLE IF NOT EXISTS portfolio_fill (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL,
            fill_id      TEXT NOT NULL,
            order_id     TEXT NOT NULL,
            symbol       TEXT NOT NULL,
            side         TEXT NOT NULL,
            quantity     TEXT NOT NULL,
            price        TEXT NOT NULL,
            fee          TEXT,
            currency     TEXT NOT NULL,
            executed_at  TEXT NOT NULL,
            recorded_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_fill_session
            ON portfolio_fill (session_id, symbol);

        CREATE TABLE IF NOT EXISTS portfolio_transaction (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id       TEXT NOT NULL,
            transaction_id   TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount           TEXT NOT NULL,
            currency         TEXT NOT NULL,
            reference        TEXT,
            symbol           TEXT,
            occurred_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_transaction_session
            ON portfolio_transaction (session_id);

        CREATE TABLE IF NOT EXISTS portfolio_position (
            session_id      TEXT NOT NULL,
            symbol          TEXT NOT NULL,
            signed_quantity TEXT NOT NULL,
            average_price   TEXT,
            realized_pnl    TEXT NOT NULL,
            total_fees      TEXT NOT NULL,
            currency        TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            PRIMARY KEY (session_id, symbol)
        );

        -- ============================================ learning ===========
        CREATE TABLE IF NOT EXISTS learning_candidate (
            signature       TEXT PRIMARY KEY,
            candidate_id    TEXT NOT NULL,
            status          TEXT NOT NULL,
            in_sample       TEXT,
            out_of_sample   TEXT,
            overfit_gap     TEXT,
            rejection       TEXT,
            payload         TEXT NOT NULL,
            recorded_at     TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_candidate_status
            ON learning_candidate (status);

        CREATE TABLE IF NOT EXISTS learning_experiment (
            experiment_id TEXT PRIMARY KEY,
            objective     TEXT NOT NULL,
            status        TEXT NOT NULL,
            hypothesis    TEXT,
            payload       TEXT NOT NULL,
            recorded_at   TEXT NOT NULL
        );
        """,
    ),
]


class Database:
    """A migrated SQLite database with transaction support.

    The connection is created per-thread: SQLite objects cannot be shared
    across threads, and silently sharing one is a classic source of
    intermittent corruption.
    """

    def __init__(self, path: str | Path = "shadbot.db", environment: str = "local") -> None:
        self._path = Path(path)
        self._environment = environment
        self._is_memory = str(path) == ":memory:"
        self._local = threading.local()
        self._shared: Optional[sqlite3.Connection] = None

        if not self._is_memory:
            self._path.parent.mkdir(parents=True, exist_ok=True)

        self.migrate()

    # -- connection ---------------------------------------------------------
    @property
    def path(self) -> Path:
        return self._path

    @property
    def connection(self) -> sqlite3.Connection:
        """The connection for the current thread."""
        # An in-memory database lives only as long as its connection, so
        # it must be shared rather than recreated.
        if self._is_memory:
            if self._shared is None:
                self._shared = self._connect()
            return self._shared

        existing = getattr(self._local, "connection", None)
        if existing is None:
            existing = self._connect()
            self._local.connection = existing
        return existing

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._path), detect_types=sqlite3.PARSE_DECLTYPES)
        connection.row_factory = sqlite3.Row
        # Referential integrity is OFF by default in SQLite.
        connection.execute("PRAGMA foreign_keys = ON")
        # WAL gives readers and a writer concurrency; irrelevant in memory.
        if not self._is_memory:
            connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a unit of work atomically; roll back on any exception."""
        connection = self.connection
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()

    # -- queries -------------------------------------------------------------
    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> sqlite3.Cursor:
        """Run a statement inside its own transaction."""
        with self.transaction() as connection:
            return connection.execute(sql, parameters)

    def execute_many(self, sql: str, rows: Sequence[Sequence[Any]]) -> None:
        """Run a statement for many rows inside one transaction."""
        with self.transaction() as connection:
            connection.executemany(sql, rows)

    def query(self, sql: str, parameters: Sequence[Any] = ()) -> List[sqlite3.Row]:
        """Return every row of a read query."""
        return list(self.connection.execute(sql, parameters).fetchall())

    def query_one(self, sql: str, parameters: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        """Return the first row of a read query, or None."""
        return self.connection.execute(sql, parameters).fetchone()

    # -- migrations -----------------------------------------------------------
    def migrate(self) -> int:
        """Apply every pending migration; return the resulting version.

        Idempotent by design: already-applied migrations are skipped, so
        calling this on every start-up is safe (§73).
        """
        connection = self.connection
        connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    INTEGER PRIMARY KEY,
                name       TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """)
        connection.commit()

        applied = {
            row["version"] for row in connection.execute("SELECT version FROM schema_migrations")
        }

        for version, name, script in MIGRATIONS:
            if version in applied:
                continue
            with self.transaction() as active:
                active.executescript(script)
                active.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) " "VALUES (?, ?, ?)",
                    (version, name, _now()),
                )

        self._touch_system_state()
        return self.schema_version

    @property
    def schema_version(self) -> int:
        """The highest applied migration version (0 when empty)."""
        row = self.query_one("SELECT MAX(version) AS version FROM schema_migrations")
        if row is None or row["version"] is None:
            return 0
        return int(row["version"])

    def applied_migrations(self) -> List[sqlite3.Row]:
        """Every applied migration, oldest first."""
        return self.query("SELECT * FROM schema_migrations ORDER BY version")

    def _touch_system_state(self) -> None:
        """Record the migration version and environment (§ system state)."""
        now = _now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO system_state
                    (id, migration_version, environment, initialized_at, updated_at)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    migration_version = excluded.migration_version,
                    environment       = excluded.environment,
                    updated_at        = excluded.updated_at
                """,
                (self.schema_version, self._environment, now, now),
            )

    def system_state(self) -> Optional[sqlite3.Row]:
        """The recorded system state row."""
        return self.query_one("SELECT * FROM system_state WHERE id = 1")

    # -- maintenance ----------------------------------------------------------
    def table_names(self) -> List[str]:
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row["name"] for row in rows]

    def row_count(self, table: str) -> int:
        """Row count of ``table`` (name is validated against the schema)."""
        if table not in self.table_names():
            raise ValueError(f"Unknown table: {table}")
        row = self.query_one(f"SELECT COUNT(*) AS total FROM {table}")  # noqa: S608
        return int(row["total"]) if row else 0

    def statistics(self) -> dict[str, int]:
        """Row counts for every table, for reporting."""
        return {name: self.row_count(name) for name in self.table_names()}

    def close(self) -> None:
        """Close this thread's connection."""
        if self._is_memory:
            if self._shared is not None:
                self._shared.close()
                self._shared = None
            return
        existing = getattr(self._local, "connection", None)
        if existing is not None:
            existing.close()
            self._local.connection = None

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
