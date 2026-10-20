"""Tests for versions, environments and safe shutdown (Phase 24)."""

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.deployment.release import (
    DeploymentManifest,
    Environment,
    ReleaseVersion,
    ShutdownPhase,
    ShutdownPlan,
)


class TestEnvironment:
    def test_only_production_may_touch_real_money(self):
        """Encoded once so a call site cannot forget it."""
        assert Environment.PRODUCTION.allows_real_money
        for other in (Environment.DEVELOPMENT, Environment.TEST, Environment.STAGING):
            assert not other.allows_real_money

    def test_production_and_staging_need_confirmation(self):
        assert Environment.PRODUCTION.requires_confirmation
        assert Environment.STAGING.requires_confirmation
        assert not Environment.DEVELOPMENT.requires_confirmation

    def test_parsing_is_forgiving_about_case_and_spaces(self):
        assert Environment.parse("  PRODUCTION ") is Environment.PRODUCTION

    def test_an_unknown_environment_lists_the_valid_ones(self):
        with pytest.raises(ValidationError) as error:
            Environment.parse("prod")
        assert "production" in str(error.value)


class TestReleaseVersion:
    def test_a_plain_version_parses(self):
        version = ReleaseVersion.parse("1.2.3")
        assert (version.major, version.minor, version.patch) == (1, 2, 3)
        assert str(version) == "1.2.3"

    def test_a_build_suffix_is_preserved(self):
        version = ReleaseVersion.parse("1.2.3+abc123")
        assert version.build == "abc123"
        assert str(version) == "1.2.3+abc123"
        assert version.core == "1.2.3"

    def test_bumping_resets_the_lower_components(self):
        version = ReleaseVersion.parse("1.2.3")
        assert str(version.bump_patch()) == "1.2.4"
        assert str(version.bump_minor()) == "1.3.0"
        assert str(version.bump_major()) == "2.0.0"

    def test_versions_order_numerically_not_lexically(self):
        """'1.10.0' must be newer than '1.9.0'."""
        assert ReleaseVersion.parse("1.9.0") < ReleaseVersion.parse("1.10.0")

    @pytest.mark.parametrize("text", ["", "1.2", "1.2.3.4", "a.b.c"])
    def test_malformed_versions_are_refused(self, text):
        with pytest.raises(ValidationError):
            ReleaseVersion.parse(text)


class TestDeploymentManifest:
    def manifest(self, **overrides):
        defaults = dict(
            version=ReleaseVersion.parse("1.0.0"),
            environment=Environment.PRODUCTION,
            schema_version=1,
            git_commit="abcdef1234567890",
            model_versions={"gold_signal": 3},
        )
        defaults.update(overrides)
        return DeploymentManifest.create(**defaults)

    def test_the_identity_pins_down_what_is_running(self):
        identity = self.manifest().identity

        assert "v1.0.0" in identity
        assert "production" in identity
        assert "abcdef12" in identity

    def test_production_without_a_commit_is_flagged(self):
        warnings = self.manifest(git_commit="").warnings()

        assert any("git commit" in warning for warning in warnings)

    def test_a_prerelease_version_in_production_is_flagged(self):
        warnings = self.manifest(version=ReleaseVersion.parse("0.1.0")).warnings()

        assert any("pre-1.0" in warning for warning in warnings)

    def test_missing_model_versions_are_flagged(self):
        """A rollback that cannot restore the models is not a rollback."""
        warnings = self.manifest(model_versions={}).warnings()

        assert any("model versions" in warning for warning in warnings)

    def test_a_clean_production_manifest_has_no_warnings(self):
        assert self.manifest().warnings() == []

    def test_the_manifest_serialises(self):
        import json

        payload = json.loads(json.dumps(self.manifest().to_dict()))

        assert payload["environment"] == "production"
        assert payload["model_versions"] == {"gold_signal": 3}


class TestShutdownPlan:
    def test_the_happy_path_runs_in_order(self):
        plan = ShutdownPlan()
        assert plan.accepting_work

        plan.begin_drain("SIGTERM")
        assert not plan.accepting_work

        plan.complete_work()
        plan.persist()
        plan.finish()

        assert plan.is_stopped
        assert plan.steps == [
            "stopped accepting new work",
            "in-flight work completed",
            "state persisted",
            "stopped",
        ]

    def test_state_cannot_be_persisted_before_draining(self):
        """Persisting first would save state that is already stale."""
        plan = ShutdownPlan()

        with pytest.raises(ValidationError) as error:
            plan.persist()
        assert "after draining" in str(error.value)

    def test_in_flight_work_blocks_persistence(self):
        plan = ShutdownPlan()
        plan.begin_drain()
        plan.in_flight = 2

        with pytest.raises(ValidationError) as error:
            plan.persist()
        assert "in flight" in str(error.value)

    def test_draining_twice_is_refused(self):
        plan = ShutdownPlan()
        plan.begin_drain()

        with pytest.raises(ValidationError):
            plan.begin_drain()

    def test_the_reason_is_carried_through(self):
        plan = ShutdownPlan()
        plan.begin_drain("consecutive failures")

        assert plan.reason == "consecutive failures"
        assert plan.to_dict()["phase"] == ShutdownPhase.DRAINING.value
