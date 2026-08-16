"""Tests for the SQLite database core: migrations, transactions, integrity."""

import sqlite3
import threading

import pytest

from ShadBotTrader.infrastructure.persistence.database import (
    MIGRATIONS,
    SCHEMA_VERSION,
    Database,
)


@pytest.fixture
def database() -> Database:
    return Database(":memory:")


class TestMigrations:
    def test_schema_is_created_on_construction(self, database):
        assert database.schema_version == SCHEMA_VERSION
        assert len(database.table_names()) >= 13

    def test_every_logical_area_has_a_table(self, database):
        tables = set(database.table_names())
        expected = {
            "market_dataset",
            "feature_definition",
            "ai_model",
            "ai_training_run",
            "trading_decision",
            "execution_attempt",
            "portfolio_fill",
            "portfolio_transaction",
            "portfolio_position",
            "learning_candidate",
            "learning_experiment",
            "system_state",
            "schema_migrations",
        }
        assert expected <= tables

    def test_migrating_twice_is_a_no_op(self, database):
        """Running migrations on every start-up must be safe (Phase 20 §73)."""
        before = database.applied_migrations()
        assert database.migrate() == SCHEMA_VERSION
        assert len(database.applied_migrations()) == len(before)

    def test_migrations_are_recorded_with_a_timestamp(self, database):
        rows = database.applied_migrations()
        assert len(rows) == len(MIGRATIONS)
        assert rows[0]["name"] == "initial_schema"
        assert rows[0]["applied_at"]

    def test_migration_versions_are_unique_and_ordered(self):
        versions = [version for version, _, _ in MIGRATIONS]
        assert versions == sorted(versions)
        assert len(versions) == len(set(versions))

    def test_system_state_records_the_version(self, database):
        state = database.system_state()
        assert state is not None
        assert state["migration_version"] == SCHEMA_VERSION
        assert state["environment"] == "local"

    def test_environment_is_configurable(self):
        database = Database(":memory:", environment="test")
        state = database.system_state()
        assert state is not None
        assert state["environment"] == "test"


class TestTransactions:
    def test_a_failed_transaction_rolls_back(self, database):
        """A half-written unit of work must leave nothing behind."""
        with pytest.raises(RuntimeError):
            with database.transaction() as connection:
                connection.execute(
                    "INSERT INTO learning_experiment "
                    "(experiment_id, objective, status, hypothesis, payload, recorded_at) "
                    "VALUES ('e1', 'o', 's', '', '{}', 'now')"
                )
                raise RuntimeError("boom")

        assert database.row_count("learning_experiment") == 0

    def test_a_successful_transaction_commits(self, database):
        with database.transaction() as connection:
            connection.execute(
                "INSERT INTO learning_experiment "
                "(experiment_id, objective, status, hypothesis, payload, recorded_at) "
                "VALUES ('e1', 'o', 's', '', '{}', 'now')"
            )
        assert database.row_count("learning_experiment") == 1

    def test_execute_many_is_atomic(self, database):
        rows = [(f"e{index}", "obj", "created", "", "{}", "now") for index in range(5)]
        database.execute_many(
            "INSERT INTO learning_experiment "
            "(experiment_id, objective, status, hypothesis, payload, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        assert database.row_count("learning_experiment") == 5


class TestIntegrity:
    def test_foreign_keys_are_enabled(self, database):
        """SQLite leaves this OFF by default — a classic silent bug."""
        row = database.query_one("PRAGMA foreign_keys")
        assert row is not None and row[0] == 1

    def test_primary_key_prevents_duplicates(self, database):
        database.execute(
            "INSERT INTO ai_model (model_id, version, name, model_type, family, "
            "payload, created_at) VALUES ('m', 1, 'n', 't', 'f', '{}', 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            database.execute(
                "INSERT INTO ai_model (model_id, version, name, model_type, family, "
                "payload, created_at) VALUES ('m', 1, 'n', 't', 'f', '{}', 'now')"
            )

    def test_system_state_is_a_singleton_row(self, database):
        with pytest.raises(sqlite3.IntegrityError):
            database.execute(
                "INSERT INTO system_state (id, migration_version, environment, "
                "initialized_at, updated_at) VALUES (2, 1, 'x', 'now', 'now')"
            )


class TestFileDatabase:
    def test_data_survives_reopening(self, tmp_path):
        """The whole point of persistence."""
        path = tmp_path / "test.db"

        first = Database(path)
        first.execute(
            "INSERT INTO learning_experiment "
            "(experiment_id, objective, status, hypothesis, payload, recorded_at) "
            "VALUES ('kept', 'obj', 'completed', '', '{}', 'now')"
        )
        first.close()

        second = Database(path)
        assert second.row_count("learning_experiment") == 1
        row = second.query_one("SELECT * FROM learning_experiment")
        assert row is not None and row["experiment_id"] == "kept"

    def test_parent_directories_are_created(self, tmp_path):
        database = Database(tmp_path / "nested" / "deep" / "test.db")
        assert database.path.exists()

    def test_reopening_does_not_re_run_migrations(self, tmp_path):
        path = tmp_path / "test.db"
        Database(path).close()
        second = Database(path)
        assert len(second.applied_migrations()) == len(MIGRATIONS)


class TestQueries:
    def test_row_count_rejects_unknown_tables(self, database):
        """Guards the f-string in row_count against injection."""
        with pytest.raises(ValueError, match="Unknown table"):
            database.row_count("users; DROP TABLE ai_model")

    def test_statistics_covers_every_table(self, database):
        stats = database.statistics()
        assert set(stats) == set(database.table_names())
        assert stats["ai_model"] == 0

    def test_query_one_returns_none_when_empty(self, database):
        assert database.query_one("SELECT * FROM ai_model") is None

    def test_parameters_are_bound_not_interpolated(self, database):
        """Injection attempt must be stored as data, not executed."""
        nasty = "'; DROP TABLE ai_model; --"
        database.execute(
            "INSERT INTO ai_model (model_id, version, name, model_type, family, "
            "payload, created_at) VALUES (?, 1, 'n', 't', 'f', '{}', 'now')",
            (nasty,),
        )
        assert "ai_model" in database.table_names()
        row = database.query_one("SELECT model_id FROM ai_model")
        assert row is not None and row["model_id"] == nasty


def test_connections_are_per_thread(tmp_path):
    """Sharing one SQLite connection across threads corrupts data."""
    database = Database(tmp_path / "threads.db")
    seen: list[int] = []

    def worker() -> None:
        seen.append(id(database.connection))

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(set(seen)) == 3  # a distinct connection per thread
