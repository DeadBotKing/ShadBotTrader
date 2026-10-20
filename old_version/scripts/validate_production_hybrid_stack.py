"""Phase134A: validate/freeze the selected hybrid production stack.

This script does not trade. It checks that the selected model stack, telemetry
schema and safety settings are coherent enough for paper/shadow runs. Live mode
is deliberately blocked unless every safety gate passes.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd

from ShadBotTrader.application.services.hybrid_production_service import (
    HybridProductionStackConfig,
    read_stack_config,
    validate_stack_config,
    write_stack_config,
)
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_CONFIG = REPO_ROOT / "configs" / "hybrid_production_stack.json"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_production_validation")


@dataclass(frozen=True)
class ModelCheck:
    model_id: str
    requested_version: int
    resolved_version: int
    exists: bool
    required: bool
    detail: str


@dataclass(frozen=True)
class ProductionValidationReport:
    passed: bool
    live_allowed: bool
    config_path: str
    schema_hash: str
    telemetry_rows: int
    telemetry_channels: int
    model_checks: list[ModelCheck]
    safety_gates: list[dict[str, Any]]
    output_config_path: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate/freeze the Phase134 hybrid production stack.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG))
    parser.add_argument("--mode", choices=("paper_shadow", "live"), default="paper_shadow")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--base-model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--base-model-version", type=int, default=0)
    parser.add_argument("--meta-model-id", default="")
    parser.add_argument("--meta-model-version", type=int, default=0)
    parser.add_argument("--meta-model-type", choices=("none", "flat", "tensor"), default="none")
    parser.add_argument("--decision-mode", choices=("meta", "score", "both"), default="meta")
    parser.add_argument("--meta-threshold", type=float, default=0.55)
    parser.add_argument("--score-threshold", type=float, default=0.0)
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-1d-version", type=int, default=0)
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--range-4h-version", type=int, default=0)
    parser.add_argument("--telemetry-flat-path", default="")
    parser.add_argument("--telemetry-tensor-path", default="")
    parser.add_argument("--telemetry-schema-hash", default="")
    parser.add_argument("--max-daily-loss-percent", type=float, default=5.0)
    parser.add_argument("--max-open-positions", type=int, default=1)
    parser.add_argument("--position-size-units", type=float, default=0.1)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--paper-shadow-passed", choices=("0", "1"), default="0")
    parser.add_argument("--account-profile-confirmed", choices=("0", "1"), default="0")
    parser.add_argument("--symbol-mapping-confirmed", choices=("0", "1"), default="0")
    parser.add_argument("--kill-switch-enabled", choices=("0", "1"), default="1")
    parser.add_argument("--explicit-live-confirm", default="")
    parser.add_argument("--write-config", choices=("0", "1"), default="1")
    parser.add_argument("--require-models", choices=("0", "1"), default="0")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> str:
    return str(
        storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"
    )


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> str:
    return str(
        storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_tensor_latest.npz"
    )


def config_from_args(args: argparse.Namespace) -> HybridProductionStackConfig:
    storage_root = Path(args.storage_root)
    config = read_stack_config(args.config_path)
    return HybridProductionStackConfig.from_mapping(
        {
            **config.to_dict(),
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "mode": args.mode,
            "base_model_id": args.base_model_id,
            "base_model_version": args.base_model_version,
            "meta_model_id": args.meta_model_id,
            "meta_model_version": args.meta_model_version,
            "meta_model_type": args.meta_model_type,
            "decision_mode": args.decision_mode,
            "meta_threshold": args.meta_threshold,
            "score_threshold": args.score_threshold,
            "range_1d_model_id": args.range_1d_model_id,
            "range_1d_version": args.range_1d_version,
            "range_4h_model_id": args.range_4h_model_id,
            "range_4h_version": args.range_4h_version,
            "telemetry_flat_path": args.telemetry_flat_path
            or default_flat_path(storage_root, args.symbol, args.timeframe),
            "telemetry_tensor_path": args.telemetry_tensor_path
            or default_tensor_path(storage_root, args.symbol, args.timeframe),
            "telemetry_schema_hash": args.telemetry_schema_hash,
            "max_daily_loss_percent": args.max_daily_loss_percent,
            "max_open_positions": args.max_open_positions,
            "position_size_units": args.position_size_units,
            "initial_capital": args.initial_capital,
            "paper_shadow_passed": args.paper_shadow_passed == "1",
            "account_profile_confirmed": args.account_profile_confirmed == "1",
            "symbol_mapping_confirmed": args.symbol_mapping_confirmed == "1",
            "kill_switch_enabled": args.kill_switch_enabled == "1",
            "explicit_live_confirm": args.explicit_live_confirm,
        }
    )


def telemetry_schema(flat_path: str, tensor_path: str) -> tuple[str, int, int]:
    tensor = Path(tensor_path)
    if tensor.exists():
        with np.load(tensor, allow_pickle=True) as data:
            names = [
                str(value) for value in np.asarray(data["channel_names"], dtype=object).tolist()
            ]
            rows = int(data["X"].shape[0])
            channels = len(names)
            return hash_names(names), rows, channels
    flat = Path(flat_path)
    if flat.exists():
        frame = pd.read_parquet(flat)
        blocked = {
            "timestamp",
            "source_index",
            "label",
            "close",
            "target_trade_win",
            "target_trade_score_r",
            "target_trade_pnl",
            "target_side",
            "target_exit_index",
            "target_outcome_code",
            "candidate_mask",
        }
        names = [name for name in frame.columns if name not in blocked]
        return hash_names(names), len(frame), len(names)
    return "", 0, 0


def hash_names(names: Sequence[str]) -> str:
    text = "\n".join(str(name) for name in names)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_check(
    catalogue: ModelCatalogue, model_id: str, requested: int, required: bool
) -> ModelCheck:
    if not model_id.strip():
        return ModelCheck(model_id, requested, 0, not required, required, "empty optional model")
    resolved = requested if requested > 0 else catalogue.latest_version(model_id)
    exists = resolved > 0 and catalogue.read(model_id, resolved) is not None
    detail = "ok" if exists else f"missing {model_id} v{resolved or requested}"
    return ModelCheck(model_id, requested, resolved, exists, required, detail)


def model_checks(config: HybridProductionStackConfig, storage_root: Path) -> list[ModelCheck]:
    catalogue = ModelCatalogue(storage_root)
    checks = [
        model_check(catalogue, config.base_model_id, config.base_model_version, True),
        model_check(catalogue, config.range_1d_model_id, config.range_1d_version, True),
        model_check(catalogue, config.range_4h_model_id, config.range_4h_version, True),
    ]
    checks.append(
        model_check(
            catalogue,
            config.meta_model_id,
            config.meta_model_version,
            config.meta_model_type != "none",
        )
    )
    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    config = config_from_args(args)
    schema_hash, telemetry_rows, telemetry_channels = telemetry_schema(
        config.telemetry_flat_path, config.telemetry_tensor_path
    )
    validation = validate_stack_config(config, schema_hash)
    checks = model_checks(config, storage_root)
    models_ok = all(check.exists or not check.required for check in checks)
    passed = validation.passed and (models_ok or args.require_models == "0")

    output_config = ""
    if args.write_config == "1":
        frozen = HybridProductionStackConfig.from_mapping(
            {**config.to_dict(), "telemetry_schema_hash": schema_hash}
        )
        output_config = str(write_stack_config(args.config_path, frozen))

    report = ProductionValidationReport(
        passed=passed,
        live_allowed=validation.live_allowed and models_ok,
        config_path=str(args.config_path),
        schema_hash=schema_hash,
        telemetry_rows=telemetry_rows,
        telemetry_channels=telemetry_channels,
        model_checks=checks,
        safety_gates=validation.to_dict()["gates"],
        output_config_path=output_config,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest.json"
    out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 74)
    print("  PHASE134 PRODUCTION STACK VALIDATION")
    print("=" * 74)
    print(f"  mode        : {config.mode}")
    print(f"  passed      : {report.passed}")
    print(f"  live allowed: {report.live_allowed}")
    print(f"  schema hash : {schema_hash or 'missing'}")
    print(f"  telemetry   : rows={telemetry_rows:,}, channels={telemetry_channels:,}")
    for check in checks:
        prefix = "OK" if check.exists or not check.required else "MISS"
        print(
            f"  [{prefix}] model {check.model_id or '(none)'} v{check.resolved_version}: {check.detail}"
        )
    print(f"  config      : {output_config or args.config_path}")
    print(f"  report      : {out_path}")
    return 0 if passed or args.require_models == "0" else 2


if __name__ == "__main__":
    raise SystemExit(main())
