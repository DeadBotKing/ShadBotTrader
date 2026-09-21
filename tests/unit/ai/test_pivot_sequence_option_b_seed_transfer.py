"""Phase151A Option B seed transfer audit helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "run_pivot_sequence_option_b_seed_transfer_validation.py"


def load_script():
    spec = importlib.util.spec_from_file_location("run_pivot_sequence_option_b_seed_transfer_validation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_seeds_deduplicates_and_requires_values():
    module = load_script()

    assert module.parse_seeds("1,2,1") == [1, 2]


def test_model_id_for_seed_is_stable():
    module = load_script()

    assert module.model_id_for_seed("my model", 42) == "my_model_seed_42"


def test_validation_score_drawdown_adjusted():
    module = load_script()

    score = module.validation_score({"total_cash_pnl": 10.0, "max_drawdown_cash": 4.0}, "drawdown_adjusted")

    assert score == 9.0


def test_train_command_includes_random_seed_and_unique_model_id():
    module = load_script()
    args = module.parse_args([
        "--tensor-path", "seq.npy",
        "--meta-path", "seq_meta.npz",
        "--flat-path", "flat.parquet",
        "--seeds", "123",
        "--epochs", "1",
    ])

    command = module.train_command(args, "model_seed_123", 123, Path("out"))

    assert "--random-seed" in command
    assert command[command.index("--random-seed") + 1] == "123"
    assert command[command.index("--model-id") + 1] == "model_seed_123"



def test_existing_model_record_picks_latest(tmp_path):
    module = load_script()
    model_dir = tmp_path / "models" / "m"
    model_dir.mkdir(parents=True)
    (model_dir / "v1_training.json").write_text("{}", encoding="utf-8")
    (model_dir / "v3_training.json").write_text("{}", encoding="utf-8")

    result = module.existing_model_record(str(tmp_path), "m")

    assert result == model_dir / "v3_training.json"
