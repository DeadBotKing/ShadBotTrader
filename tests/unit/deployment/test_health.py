"""Tests for health, readiness and liveness (Phase 24, §38-42).

The distinction between the three is the point. A system that has just
started is alive but not ready; one missing an optional dependency is
degraded but must keep serving. Collapsing these into one boolean is how
a deployment ends up trading on a half-initialised platform.
"""

from ShadBotTrader.domain.deployment.health import (
    DependencyKind,
    HealthMonitor,
    HealthStatus,
)
from ShadBotTrader.infrastructure.deployment.health_checks import default_monitor


class TestHealthStatus:
    def test_degraded_still_serves_but_unhealthy_does_not(self):
        assert HealthStatus.HEALTHY.is_serving
        assert HealthStatus.DEGRADED.is_serving
        assert not HealthStatus.UNHEALTHY.is_serving


class TestMonitor:
    def test_all_passing_is_healthy_and_ready(self):
        monitor = HealthMonitor(version="1.0.0", environment="test")
        monitor.register("a", lambda: True)
        monitor.register("b", lambda: True, DependencyKind.OPTIONAL)

        report = monitor.run()

        assert report.status is HealthStatus.HEALTHY
        assert report.is_ready
        assert report.is_live

    def test_a_failed_optional_dependency_only_degrades(self):
        """TensorFlow being absent must not stop the dashboard."""
        monitor = HealthMonitor()
        monitor.register("critical_one", lambda: True, DependencyKind.CRITICAL)
        monitor.register("optional_one", lambda: False, DependencyKind.OPTIONAL)

        report = monitor.run()

        assert report.status is HealthStatus.DEGRADED
        assert report.is_ready  # still able to accept work
        assert report.is_live

    def test_a_failed_critical_dependency_makes_it_unhealthy(self):
        monitor = HealthMonitor()
        monitor.register("database", lambda: False, DependencyKind.CRITICAL)

        report = monitor.run()

        assert report.status is HealthStatus.UNHEALTHY
        assert not report.is_ready
        # liveness is separate: the process still answered
        assert report.is_live

    def test_a_check_that_raises_is_recorded_not_propagated(self):
        """A health endpoint that itself crashes tells an operator nothing."""

        def explode():
            raise RuntimeError("connection refused")

        monitor = HealthMonitor()
        monitor.register("broker", explode, DependencyKind.CRITICAL)

        report = monitor.run()

        assert report.status is HealthStatus.UNHEALTHY
        assert "connection refused" in report.failures[0].detail

    def test_a_check_may_return_a_detail_string(self):
        monitor = HealthMonitor()
        monitor.register("database", lambda: (True, "128 KB"))

        report = monitor.run()

        assert report.checks[0].detail == "128 KB"

    def test_registration_chains(self):
        monitor = HealthMonitor().register("a", lambda: True).register("b", lambda: True)

        assert monitor.registered == ["a", "b"]

    def test_only_critical_failures_block_service(self):
        monitor = HealthMonitor()
        monitor.register("opt", lambda: False, DependencyKind.OPTIONAL)
        monitor.register("crit", lambda: False, DependencyKind.CRITICAL)

        report = monitor.run()
        blocking = [check.name for check in report.checks if check.blocks_service]

        assert blocking == ["crit"]

    def test_the_report_serialises(self):
        import json

        monitor = HealthMonitor(version="1.0.0", environment="production")
        monitor.register("a", lambda: True)

        payload = json.loads(json.dumps(monitor.run().to_dict()))

        assert payload["status"] == "healthy"
        assert payload["version"] == "1.0.0"
        assert payload["ready"] is True

    def test_each_check_is_timed(self):
        monitor = HealthMonitor()
        monitor.register("a", lambda: True)

        assert monitor.run().checks[0].duration_ms >= 0.0


class TestDefaultMonitor:
    def test_the_python_runtime_is_always_checked(self):
        report = default_monitor(version="1.0.0", environment="test").run()

        names = [check.name for check in report.checks]
        assert "python_runtime" in names

    def test_optional_dependencies_are_classified_as_optional(self):
        """Their absence must never make the platform unhealthy."""
        report = default_monitor().run()

        by_name = {check.name: check for check in report.checks}
        assert by_name["tensorflow"].kind is DependencyKind.OPTIONAL
        assert by_name["metatrader5"].kind is DependencyKind.OPTIONAL
        # whatever their state, the platform can still accept work
        assert report.is_ready

    def test_a_missing_database_is_a_critical_failure(self, tmp_path):
        report = default_monitor(database_path=str(tmp_path / "nope.db")).run()

        assert report.status is HealthStatus.UNHEALTHY
        assert not report.is_ready

    def test_a_real_database_passes(self, tmp_path):
        from ShadBotTrader.infrastructure.persistence import Database

        path = tmp_path / "live.db"
        Database(path).close()

        report = default_monitor(database_path=str(path)).run()
        database_check = next(c for c in report.checks if c.name == "database")

        assert database_check.passed

    def test_an_unwritable_storage_root_fails(self, tmp_path):
        report = default_monitor(storage_root=str(tmp_path / "missing")).run()
        storage = next(c for c in report.checks if c.name == "storage")

        assert not storage.passed
        assert "missing" in storage.detail

    def test_a_writable_storage_root_passes(self, tmp_path):
        report = default_monitor(storage_root=str(tmp_path)).run()
        storage = next(c for c in report.checks if c.name == "storage")

        assert storage.passed
        # the probe file must not be left behind
        assert not (tmp_path / ".write_probe").exists()
