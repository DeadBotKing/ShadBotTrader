"""Phase134 production-stack configuration and safety gates.

The research phases may keep many scripts and candidate models. The online bot
must not. This module defines the narrow, serialisable configuration and the
hard safety checks that any paper/live entry point must pass before it can be
considered production-ready.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

LIVE_CONFIRMATION_PHRASE = "ENABLE_REAL_HYBRID_TRADING"


@dataclass(frozen=True)
class HybridProductionStackConfig:
    """One selected hybrid stack, plus paper/live safety settings."""

    symbol: str = "XAUUSD"
    timeframe: str = "5M"
    mode: str = "paper_shadow"  # paper_shadow | live
    base_model_id: str = "gold_hybrid_lightgbm_head_5m"
    base_model_version: int = 0
    meta_model_id: str = ""
    meta_model_version: int = 0
    meta_model_type: str = "none"  # none | flat | tensor
    decision_mode: str = "meta"  # meta | score | both
    meta_threshold: float = 0.55
    score_threshold: float = 0.0
    range_1d_model_id: str = "gold_range_1d"
    range_1d_version: int = 0
    range_4h_model_id: str = "gold_range_4h"
    range_4h_version: int = 0
    telemetry_flat_path: str = "datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet"
    telemetry_tensor_path: str = "datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz"
    telemetry_schema_hash: str = ""
    max_daily_loss_percent: float = 5.0
    max_open_positions: int = 1
    position_size_units: float = 0.1
    initial_capital: float = 100.0
    paper_shadow_passed: bool = False
    account_profile_confirmed: bool = False
    symbol_mapping_confirmed: bool = False
    kill_switch_enabled: bool = True
    explicit_live_confirm: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HybridProductionStackConfig":
        defaults = cls().to_dict()
        merged = {**defaults, **dict(payload)}
        return cls(
            symbol=str(merged["symbol"]),
            timeframe=str(merged["timeframe"]),
            mode=str(merged["mode"]),
            base_model_id=str(merged["base_model_id"]),
            base_model_version=int(merged["base_model_version"] or 0),
            meta_model_id=str(merged["meta_model_id"] or ""),
            meta_model_version=int(merged["meta_model_version"] or 0),
            meta_model_type=str(merged["meta_model_type"] or "none"),
            decision_mode=str(merged["decision_mode"] or "meta"),
            meta_threshold=float(merged["meta_threshold"] or 0.0),
            score_threshold=float(merged["score_threshold"] or 0.0),
            range_1d_model_id=str(merged["range_1d_model_id"]),
            range_1d_version=int(merged["range_1d_version"] or 0),
            range_4h_model_id=str(merged["range_4h_model_id"]),
            range_4h_version=int(merged["range_4h_version"] or 0),
            telemetry_flat_path=str(merged["telemetry_flat_path"]),
            telemetry_tensor_path=str(merged["telemetry_tensor_path"]),
            telemetry_schema_hash=str(merged["telemetry_schema_hash"] or ""),
            max_daily_loss_percent=float(merged["max_daily_loss_percent"] or 0.0),
            max_open_positions=int(merged["max_open_positions"] or 0),
            position_size_units=float(merged["position_size_units"] or 0.0),
            initial_capital=float(merged["initial_capital"] or 0.0),
            paper_shadow_passed=bool(merged["paper_shadow_passed"]),
            account_profile_confirmed=bool(merged["account_profile_confirmed"]),
            symbol_mapping_confirmed=bool(merged["symbol_mapping_confirmed"]),
            kill_switch_enabled=bool(merged["kill_switch_enabled"]),
            explicit_live_confirm=str(merged["explicit_live_confirm"] or ""),
            notes=str(merged["notes"] or ""),
        )


@dataclass(frozen=True)
class SafetyGateResult:
    """One production-readiness check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class HybridProductionValidation:
    """The complete validation verdict."""

    config: HybridProductionStackConfig
    schema_hash: str
    gates: list[SafetyGateResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in self.gates)

    @property
    def live_allowed(self) -> bool:
        if self.config.mode != "live":
            return False
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "live_allowed": self.live_allowed,
            "schema_hash": self.schema_hash,
            "config": self.config.to_dict(),
            "gates": [asdict(gate) for gate in self.gates],
        }


def read_stack_config(path: str | Path) -> HybridProductionStackConfig:
    file_path = Path(path)
    if not file_path.exists():
        return HybridProductionStackConfig()
    return HybridProductionStackConfig.from_mapping(
        json.loads(file_path.read_text(encoding="utf-8"))
    )


def write_stack_config(path: str | Path, config: HybridProductionStackConfig) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return file_path


def safety_gates(config: HybridProductionStackConfig, schema_hash: str) -> list[SafetyGateResult]:
    """Validate the non-negotiable paper/live safety settings."""

    gates = [
        SafetyGateResult(
            "mode_supported",
            config.mode in ("paper_shadow", "live"),
            f"mode={config.mode}",
        ),
        SafetyGateResult(
            "base_model_selected",
            bool(config.base_model_id.strip()),
            config.base_model_id,
        ),
        SafetyGateResult(
            "range_models_selected",
            bool(config.range_1d_model_id.strip() and config.range_4h_model_id.strip()),
            f"{config.range_1d_model_id}, {config.range_4h_model_id}",
        ),
        SafetyGateResult(
            "position_size_positive",
            config.position_size_units > 0,
            f"units={config.position_size_units}",
        ),
        SafetyGateResult(
            "initial_capital_positive",
            config.initial_capital > 0,
            f"initial={config.initial_capital}",
        ),
        SafetyGateResult(
            "risk_limits_present",
            config.max_daily_loss_percent > 0 and config.max_open_positions > 0,
            (
                f"daily_loss={config.max_daily_loss_percent}, "
                f"max_positions={config.max_open_positions}"
            ),
        ),
        SafetyGateResult(
            "kill_switch_enabled",
            config.kill_switch_enabled,
            "kill switch must be available before any live run",
        ),
        SafetyGateResult(
            "schema_hash_known",
            bool(schema_hash),
            schema_hash or "missing",
        ),
    ]
    if config.telemetry_schema_hash:
        gates.append(
            SafetyGateResult(
                "schema_hash_matches_config",
                config.telemetry_schema_hash == schema_hash,
                f"config={config.telemetry_schema_hash}, current={schema_hash}",
            )
        )
    if config.mode == "live":
        gates.extend(
            [
                SafetyGateResult("paper_shadow_passed", config.paper_shadow_passed),
                SafetyGateResult("account_profile_confirmed", config.account_profile_confirmed),
                SafetyGateResult("symbol_mapping_confirmed", config.symbol_mapping_confirmed),
                SafetyGateResult(
                    "explicit_live_confirmation",
                    config.explicit_live_confirm == LIVE_CONFIRMATION_PHRASE,
                    "real execution requires the exact confirmation phrase",
                ),
            ]
        )
    return gates


def validate_stack_config(
    config: HybridProductionStackConfig, schema_hash: str
) -> HybridProductionValidation:
    return HybridProductionValidation(
        config=config,
        schema_hash=schema_hash,
        gates=safety_gates(config, schema_hash),
    )
