"""Phase134 production stack safety gate tests."""

from __future__ import annotations

from ShadBotTrader.application.services.hybrid_production_service import (
    LIVE_CONFIRMATION_PHRASE,
    HybridProductionStackConfig,
    validate_stack_config,
)


def test_paper_shadow_config_passes_without_live_confirm():
    config = HybridProductionStackConfig(mode="paper_shadow")

    validation = validate_stack_config(config, "abc123")

    assert validation.passed
    assert not validation.live_allowed


def test_live_config_requires_all_safety_gates():
    config = HybridProductionStackConfig(mode="live", explicit_live_confirm="wrong")

    validation = validate_stack_config(config, "abc123")

    assert not validation.passed
    assert not validation.live_allowed
    failed = {gate.name for gate in validation.gates if not gate.passed}
    assert "paper_shadow_passed" in failed
    assert "explicit_live_confirmation" in failed


def test_live_config_can_pass_only_with_explicit_confirmation_and_flags():
    config = HybridProductionStackConfig(
        mode="live",
        paper_shadow_passed=True,
        account_profile_confirmed=True,
        symbol_mapping_confirmed=True,
        explicit_live_confirm=LIVE_CONFIRMATION_PHRASE,
    )

    validation = validate_stack_config(config, "abc123")

    assert validation.passed
    assert validation.live_allowed


def test_schema_hash_mismatch_blocks_validation():
    config = HybridProductionStackConfig(telemetry_schema_hash="old")

    validation = validate_stack_config(config, "new")

    assert not validation.passed
    failed = {gate.name for gate in validation.gates if not gate.passed}
    assert "schema_hash_matches_config" in failed
