"""Phase187A: train a multistep range WaveNet without touching production ids.

The current gold_range_4h / gold_range_1d artifacts stay untouched.
This command writes only ids that contain ``multistep``, default:

    gold_range_multistep_4h
    gold_range_multistep_1d

Architecture is the existing range WaveNet seq2seq head, not Option B.
horizon=5 emits [high_1, low_1, ..., high_5, low_5].

No paper trading. No live trading. No overwrite of production range ids.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for path in (SCRIPT_DIR, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

PROTECTED_RANGE_IDS = frozenset(
    {
        "gold_range",
        "gold_range_5m",
        "gold_range_1h",
        "gold_range_4h",
        "gold_range_1d",
    }
)
DEFAULT_PREFIX = "gold_range_multistep"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a new multistep range WaveNet without overwriting gold_range_* production ids.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframes", default="4H,1D")
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--window", type=int, default=150)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--n-layers", type=int, default=4)
    parser.add_argument("--n-blocks", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1.5e-4)
    parser.add_argument("--es-patience", type=int, default=0)
    parser.add_argument("--rlr-patience", type=int, default=0)
    parser.add_argument("--model-id-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--storage-root", default="datasets")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def canonical_timeframe(text: str) -> str:
    value = str(text or "").strip().upper()
    if value in {"4", "H4", "4H"}:
        return "4H"
    if value in {"1", "D", "D1", "1D"}:
        return "1D"
    if value in {"60", "H1", "1H"}:
        return "1H"
    return value


def parse_timeframes(text: str) -> list[str]:
    values = [canonical_timeframe(item) for item in str(text or "").replace(";", ",").split(",") if item.strip()]
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    if not output:
        raise RuntimeError("At least one timeframe is required")
    return output


def resolved_model_id(timeframe: str, prefix: str = DEFAULT_PREFIX) -> str:
    """Return a save id that cannot collide with a production range model."""
    from ShadBotTrader.infrastructure.ai.model_roles import range_model_id

    tf = canonical_timeframe(timeframe)
    cleaned = str(prefix or "").strip().lower().strip("_")
    if not cleaned:
        raise RuntimeError("model id prefix is empty")
    model_id = f"{cleaned}_{tf.lower()}"
    production_id = range_model_id(tf).lower()
    if model_id in PROTECTED_RANGE_IDS or model_id == production_id:
        raise RuntimeError(
            f"Refusing to train into protected range id {model_id}. "
            "Use a prefix that contains 'multistep'."
        )
    if "multistep" not in model_id:
        raise RuntimeError(
            f"Refusing model id {model_id}: it does not contain 'multistep', "
            "so it could be confused with a production range artifact."
        )
    if model_id.startswith("gold_range_") and "multistep" not in model_id.split("gold_range_", 1)[1]:
        raise RuntimeError(f"Refusing model id {model_id}")
    return model_id


def build_multistep_role(timeframe: str, args: argparse.Namespace):
    from ShadBotTrader.infrastructure.ai.model_roles import range_model_role

    tf = canonical_timeframe(timeframe)
    model_id = resolved_model_id(tf, args.model_id_prefix)
    role = range_model_role(
        timeframe=tf,
        horizon=max(int(args.horizon), 2),
        window_size=max(int(args.window), 2),
        n_layers_per_block=max(int(args.n_layers), 1),
        n_blocks=max(int(args.n_blocks), 1),
    )
    if not role.seq2seq:
        raise RuntimeError("Range multistep training requires the existing seq2seq WaveNet head")
    return replace(
        role,
        model_id=model_id,
        description=(
            f"Multistep range WaveNet for {tf}: high/low of each of the next "
            f"{role.horizon} candles. Does not replace {PROTECTED_RANGE_IDS}."
        ),
    )


def output_width(horizon: int) -> int:
    return max(int(horizon), 1) * 2


def training_plan(args: argparse.Namespace) -> list[dict[str, object]]:
    plan = []
    for timeframe in parse_timeframes(args.timeframes):
        role = build_multistep_role(timeframe, args)
        plan.append(
            {
                "timeframe": timeframe,
                "model_id": role.model_id,
                "horizon": role.horizon,
                "output_width": output_width(role.horizon),
                "output_layout": "high_1,low_1,...,high_H,low_H",
                "window_size": role.window_size,
                "n_layers_per_block": role.n_layers_per_block,
                "n_blocks": role.n_blocks,
                "seq2seq": role.seq2seq,
                "architecture": "range_wavenet_seq2seq",
                "option_b_used": 0,
                "storage_dir": str(Path(args.storage_root) / "models" / role.model_id),
                "protected_ids_untouched": ",".join(sorted(PROTECTED_RANGE_IDS)),
            }
        )
    return plan


def print_plan(plan: list[dict[str, object]]) -> None:
    print("[i] Phase187A range multistep training plan", flush=True)
    print("[i] architecture: existing range WaveNet seq2seq. Option B is not used.", flush=True)
    print("[i] production ids are not write targets.", flush=True)
    print(
        "[i] new compiles use Huber delta=1.0 for ATR targets. "
        "Saved gold_range_* artifacts are not rewritten. Do not rerun unless the owner asks.",
        flush=True,
    )
    for row in plan:
        print(
            f"[i] {row['timeframe']}: model_id={row['model_id']} horizon={row['horizon']} "
            f"output_width={row['output_width']} window={row['window_size']} "
            f"layers={row['n_layers_per_block']} blocks={row['n_blocks']}",
            flush=True,
        )
        print(f"    save dir: {row['storage_dir']}", flush=True)


def trainer_argv(args: argparse.Namespace, timeframe: str) -> list[str]:
    return [
        "--model",
        "range",
        "--symbol",
        str(args.symbol),
        "--range-timeframes",
        canonical_timeframe(timeframe),
        "--horizon",
        str(max(int(args.horizon), 2)),
        "--window",
        str(max(int(args.window), 2)),
        "--epochs",
        str(max(int(args.epochs), 1)),
        "--folds",
        str(max(int(args.folds), 1)),
        "--n-layers",
        str(max(int(args.n_layers), 1)),
        "--n-blocks",
        str(max(int(args.n_blocks), 1)),
        "--learning-rate",
        str(float(args.learning_rate)),
        "--es-patience",
        str(max(int(args.es_patience), 0)),
        "--rlr-patience",
        str(max(int(args.rlr_patience), 0)),
        "--with-features",
        "--storage-root",
        str(args.storage_root),
    ]


def run(argv: list[str] | None = None) -> list[dict[str, object]]:
    args = parse_args(argv)
    if int(args.horizon) < 2:
        raise RuntimeError("--horizon must be >= 2 for a multistep range model")
    if float(args.learning_rate) <= 0:
        raise RuntimeError("--learning-rate must be positive")
    plan = training_plan(args)
    print_plan(plan)
    if args.dry_run:
        print("[i] dry-run: no model was trained and no artifact was written", flush=True)
        return plan

    try:
        import tensorflow  # noqa: F401
    except ImportError as error:
        raise RuntimeError(
            "TensorFlow is not installed. This sandbox cannot train the model. "
            "Run the same command on the machine that has the XAUUSD datasets and "
            "requirements-ai.txt installed."
        ) from error

    import run_dual_models

    for row in plan:
        timeframe = str(row["timeframe"])
        role = build_multistep_role(timeframe, args)
        trainer_args = run_dual_models.parse_args(trainer_argv(args, timeframe))
        service = run_dual_models.build_service(trainer_args)
        print(f"[i] training {role.model_id}; this does not open gold_range_{timeframe.lower()}", flush=True)
        status = run_dual_models.train_one(service, trainer_args, role, timeframe, learning_rate=float(args.learning_rate))
        if status:
            raise RuntimeError(f"Training failed for {role.model_id} with status {status}")
    print("[DONE] Phase187A multistep range models trained under new ids only", flush=True)
    print("[i] Next audit, after training:", flush=True)
    print("    AI → Audit range multistep accuracy", flush=True)
    print("    4H range model = gold_range_multistep_4h", flush=True)
    print("    1D range model = gold_range_multistep_1d", flush=True)
    print("[i] No paper. No live.", flush=True)
    return plan


def main() -> None:
    run()


if __name__ == "__main__":
    main()
