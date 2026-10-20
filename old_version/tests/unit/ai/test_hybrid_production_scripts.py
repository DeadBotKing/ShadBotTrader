"""Phase134 script helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

VALIDATE_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "validate_production_hybrid_stack.py"
)
PAPER_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "run_hybrid_paper_shadow.py"


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_schema_hash_is_stable_for_channel_names():
    module = load_script(VALIDATE_SCRIPT, "validate_production_hybrid_stack")

    assert module.hash_names(["a", "b"]) == module.hash_names(["a", "b"])
    assert module.hash_names(["a", "b"]) != module.hash_names(["b", "a"])


def test_telemetry_schema_reads_flat_when_tensor_missing(tmp_path):
    module = load_script(VALIDATE_SCRIPT, "validate_production_hybrid_stack")
    flat = tmp_path / "flat.parquet"
    pd.DataFrame(
        {
            "timestamp": ["t"],
            "source_index": [1],
            "target_trade_win": [1],
            "candidate_mask": [1],
            "feature_a": [0.1],
            "feature_b": [0.2],
        }
    ).to_parquet(flat, index=False)

    schema_hash, rows, channels = module.telemetry_schema(str(flat), str(tmp_path / "missing.npz"))

    assert schema_hash
    assert rows == 1
    assert channels == 2


def test_paper_eval_indices_uses_tail_and_cap():
    module = load_script(PAPER_SCRIPT, "run_hybrid_paper_shadow")

    indices = module.eval_indices(10, eval_frac=0.5, max_windows=3)

    assert indices.tolist() == [5, 6, 7]


def test_decision_rows_converts_trade_equity_to_balance():
    module = load_script(PAPER_SCRIPT, "run_hybrid_paper_shadow")

    trade = type(
        "Trade",
        (),
        {
            "number": 1,
            "timestamp": "t",
            "source_index": 10,
            "side": "BUY",
            "entry": 2000.0,
            "tp": 2010.0,
            "sl": 1990.0,
            "exit_index": 20,
            "pnl": 5.0,
            "equity": 5.0,
        },
    )()

    rows = module.decision_rows([trade], initial_capital=100.0, units=0.1)

    assert rows[0].status == "would_trade"
    assert rows[0].balance_after == pytest.approx(100.5)
