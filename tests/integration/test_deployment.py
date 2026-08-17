"""Integration tests for deployment (Phase 24).

Two things dominate here, because they are the ones that cost real money
when wrong:

* **A backup that has never been restored is not a backup** (§80). Every
  backup is verified, and a corrupt file must be refused *before* the
  live database is touched.
* **Shutdown order** (§34). Drain, persist, stop — and never cut into a
  cycle that is mid-flight.
"""

import json
import threading
import time
from pathlib import Path

import pytest

from ShadBotTrader.application.services.runner_service import (
    RunnerConfig,
    RunnerService,
)
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.deployment.health import DependencyKind, HealthMonitor
from ShadBotTrader.infrastructure.deployment.backup import BackupService
from ShadBotTrader.infrastructure.persistence import Database


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "live.db"
    Database(path).close()
    return path


@pytest.fixture
def service(tmp_path, database):
    return BackupService(database, tmp_path / "backups")


class Result:
    """Stand-in for a TickResult."""

    def __init__(self, status="no_trade", acted=False):
        self.status = status
        self.acted = acted
        self.reason = ""


# --------------------------------------------------------------- backup ---
class TestBackup:
    def test_a_backup_is_verified_on_creation(self, service):
        record = service.create(note="test")

        assert record.verified
        assert Path(record.path).exists()
        assert record.schema_version == 1
        assert record.table_counts

    def test_the_metadata_sidecar_is_written(self, service):
        record = service.create()
        sidecar = Path(record.path).with_suffix(".json")

        assert sidecar.exists()
        assert json.loads(sidecar.read_text())["verified"] is True

    def test_backing_up_a_missing_database_fails_clearly(self, tmp_path):
        with pytest.raises(ValidationError) as error:
            BackupService(tmp_path / "nope.db").create()
        assert "does not exist" in str(error.value)

    def test_backups_are_listed_newest_first(self, service):
        for index in range(3):
            service.create(note=f"n{index}")
            time.sleep(0.01)

        records = service.list_backups()

        assert len(records) == 3
        assert records == sorted(records, key=lambda r: r.created_at, reverse=True)

    def test_two_backups_in_the_same_second_do_not_collide(self, service):
        first = service.create()
        second = service.create()

        assert first.path != second.path
        assert Path(first.path).exists() and Path(second.path).exists()

    def test_a_corrupt_file_is_refused(self, service, tmp_path):
        broken = tmp_path / "broken.db"
        broken.write_bytes(b"definitely not a database")

        with pytest.raises(ValidationError) as error:
            service.verify(broken)
        assert "not a readable SQLite database" in str(error.value)

    def test_restoring_a_corrupt_file_leaves_the_original_intact(self, service, database, tmp_path):
        """Verification happens before anything is overwritten."""
        broken = tmp_path / "broken.db"
        broken.write_bytes(b"garbage")
        before = database.read_bytes()

        with pytest.raises(ValidationError):
            service.restore(broken)

        assert database.read_bytes() == before

    def test_restore_keeps_a_safety_copy(self, service, database):
        record = service.create()

        outcome = service.restore(record.path)

        assert outcome["previous_saved_to"]
        assert Path(outcome["previous_saved_to"]).exists()

    def test_restore_can_skip_the_safety_copy(self, service):
        record = service.create()

        outcome = service.restore(record.path, safety_copy=False)

        assert outcome["previous_saved_to"] is None

    def test_a_restored_database_is_readable(self, service, database):
        record = service.create()
        service.restore(record.path)

        restored = Database(database)
        try:
            assert restored.schema_version == 1
        finally:
            restored.close()

    def test_pruning_keeps_the_newest(self, service):
        for _ in range(5):
            service.create()
            time.sleep(0.01)
        newest = service.latest()

        removed = service.prune(keep=2)

        assert len(removed) == 3
        assert len(service.list_backups()) == 2
        assert service.latest().path == newest.path

    def test_pruning_everything_is_refused(self, service):
        with pytest.raises(ValidationError):
            service.prune(keep=0)

    def test_pruning_removes_the_sidecar_too(self, service):
        for _ in range(3):
            service.create()
            time.sleep(0.01)

        removed = service.prune(keep=1)

        for path in removed:
            assert not Path(path).with_suffix(".json").exists()


# --------------------------------------------------------------- runner ---
class TestRunner:
    def test_it_stops_after_the_configured_cycles(self):
        runner = RunnerService(
            tick=lambda: Result(), config=RunnerConfig(interval_seconds=0, max_cycles=4)
        )

        state = runner.run()

        assert state.cycles == 4
        assert runner.shutdown.is_stopped

    def test_shutdown_follows_the_required_order(self):
        runner = RunnerService(
            tick=lambda: Result(), config=RunnerConfig(interval_seconds=0, max_cycles=1)
        )
        runner.run()

        assert runner.shutdown.steps == [
            "stopped accepting new work",
            "in-flight work completed",
            "state persisted",
            "stopped",
        ]

    def test_trades_are_counted(self):
        runner = RunnerService(
            tick=lambda: Result("traded", acted=True),
            config=RunnerConfig(interval_seconds=0, max_cycles=3),
        )

        assert runner.run().trades == 3

    def test_a_failing_tick_is_counted_not_fatal(self):
        def explode():
            raise RuntimeError("broker unreachable")

        runner = RunnerService(
            tick=explode,
            config=RunnerConfig(interval_seconds=0, max_cycles=3, max_consecutive_failures=99),
        )
        state = runner.run()

        assert state.cycles == 3
        assert state.failures == 3
        assert "broker unreachable" in state.last_reason

    def test_repeated_failures_stop_the_runner(self):
        """Retrying forever hides an outage instead of surfacing it."""

        def explode():
            raise RuntimeError("down")

        runner = RunnerService(
            tick=explode,
            config=RunnerConfig(interval_seconds=0, max_cycles=100, max_consecutive_failures=3),
        )
        state = runner.run()

        assert state.cycles == 3
        assert "consecutive failures" in state.stop_reason

    def test_a_success_resets_the_failure_streak(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
            return Result()

        runner = RunnerService(
            tick=flaky,
            config=RunnerConfig(interval_seconds=0, max_cycles=4, max_consecutive_failures=2),
        )
        state = runner.run()

        assert state.cycles == 4
        assert state.consecutive_failures == 0

    def test_an_unhealthy_system_refuses_to_run_a_cycle(self):
        monitor = HealthMonitor()
        monitor.register("database", lambda: False, DependencyKind.CRITICAL)
        calls = {"n": 0}

        def tick():
            calls["n"] += 1
            return Result()

        runner = RunnerService(
            tick=tick,
            config=RunnerConfig(interval_seconds=0, max_cycles=2, max_consecutive_failures=99),
            monitor=monitor,
        )
        runner.run()

        assert calls["n"] == 0  # the tick never ran
        assert runner.state.last_status == "unhealthy"

    def test_a_degraded_system_still_runs(self):
        monitor = HealthMonitor()
        monitor.register("mt5", lambda: False, DependencyKind.OPTIONAL)

        runner = RunnerService(
            tick=lambda: Result(),
            config=RunnerConfig(interval_seconds=0, max_cycles=2),
            monitor=monitor,
        )

        assert runner.run().cycles == 2

    def test_state_survives_a_restart(self, tmp_path):
        path = tmp_path / "state.json"
        config = RunnerConfig(interval_seconds=0, max_cycles=3, state_path=str(path))

        RunnerService(tick=lambda: Result("traded", True), config=config).run()
        second = RunnerService(
            tick=lambda: Result("traded", True),
            config=RunnerConfig(interval_seconds=0, max_cycles=5, state_path=str(path)),
        )
        state = second.run()

        assert state.cycles == 5  # resumed from 3, ran 2 more
        assert state.trades == 5

    def test_a_damaged_state_file_does_not_stop_the_runner(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text("{ this is not json", encoding="utf-8")

        runner = RunnerService(
            tick=lambda: Result(),
            config=RunnerConfig(interval_seconds=0, max_cycles=2, state_path=str(path)),
        )

        assert runner.run().cycles == 2

    def test_stopping_waits_for_the_cycle_in_flight(self):
        """§33: a deployment must not interrupt active trading."""
        entered = threading.Event()
        release = threading.Event()
        finished = []

        def slow_tick():
            entered.set()
            release.wait(timeout=5)
            finished.append(True)
            return Result()

        runner = RunnerService(
            tick=slow_tick, config=RunnerConfig(interval_seconds=0, max_cycles=1)
        )
        thread = threading.Thread(target=runner.run, daemon=True)
        thread.start()

        entered.wait(timeout=5)
        runner.request_stop("test")  # arrives mid-tick
        release.set()
        thread.join(timeout=5)

        assert finished == [True]  # the tick completed
        assert runner.shutdown.is_stopped

    def test_backups_are_taken_on_schedule(self, tmp_path, database):
        backup = BackupService(database, tmp_path / "backups")
        runner = RunnerService(
            tick=lambda: Result(),
            config=RunnerConfig(interval_seconds=0, max_cycles=6, backup_every=2),
            backup=backup,
        )
        runner.run()

        assert len(backup.list_backups()) == 3

    def test_a_failed_backup_does_not_stop_trading(self, tmp_path):
        class BrokenBackup:
            def create(self, note=""):
                raise RuntimeError("disk full")

        events = []
        runner = RunnerService(
            tick=lambda: Result(),
            config=RunnerConfig(interval_seconds=0, max_cycles=2, backup_every=1),
            backup=BrokenBackup(),
            on_event=lambda name, payload: events.append(name),
        )
        state = runner.run()

        assert state.cycles == 2
        assert state.failures == 0
        assert "backup_failed" in events

    def test_an_observer_that_raises_cannot_break_the_runner(self):
        def bad_observer(name, payload):
            raise RuntimeError("logging is down")

        runner = RunnerService(
            tick=lambda: Result(),
            config=RunnerConfig(interval_seconds=0, max_cycles=2),
            on_event=bad_observer,
        )

        assert runner.run().cycles == 2
