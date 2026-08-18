"""Phase 29 demo — train the two predictive models.

    RANGE MODEL   1H candles  ->  highest high + lowest low, next N bars
    SIGNAL MODEL  5M candles  ->  buy / sell / hold with probabilities

    python scripts/run_dual_models.py                    # both, quick
    python scripts/run_dual_models.py --model range
    python scripts/run_dual_models.py --model signal --epochs 3
    python scripts/run_dual_models.py --symbol XAUUSD --with-features

Both models train roll-forward: each fold trains on a window and
validates on the window that immediately follows, so no future bar ever
influences a past prediction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STORAGE_ROOT = REPO_ROOT / "datasets"


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the range and signal models (Phase 29).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument(
        "--model",
        choices=("all", "both", "range", "signal", "range_1h", "range_1d"),
        default="all",
        help=(
            "which model to train. 'range_1h' / 'range_1d' pick one "
            "range model; 'all' trains the signal model plus every "
            "range timeframe in --range-timeframes."
        ),
    )
    parser.add_argument(
        "--range-timeframes",
        default="1H,1D",
        help="comma separated timeframes to train a range model for",
    )
    parser.add_argument("--range-timeframe", default="", help="alias of --range-timeframes")
    parser.add_argument("--signal-timeframe", default="5M", help="signal model candles")
    parser.add_argument("--horizon", type=int, default=5, help="candles to look ahead")
    parser.add_argument("--window", type=int, default=24, help="input window size")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--folds", type=int, default=2, help="roll-forward folds to keep")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0008,
        help="neutral band of the signal model, as a price fraction",
    )
    parser.add_argument(
        "--with-features",
        action="store_true",
        help="use the full 109-feature catalogue (slower)",
    )
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the per-epoch training log",
    )
    return parser.parse_args(argv)


class NoRealData(RuntimeError):
    """Raised when a timeframe has no stored broker candles."""


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    """Load stored REAL candles for one timeframe.

    Phase 35: no sample fallback. Training a model on generated candles
    produces weights that look trained and mean nothing, and once they
    are on disk nobody can tell which run they came from.
    """
    from ShadBotTrader.data_cli import build_service
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.account import AccountProfileStore
    from ShadBotTrader.infrastructure.data.symbol_scope import (
        resolve_stored_symbol,
        stored_symbols,
    )

    _, store, _ = build_service(storage_root)
    try:
        profile = AccountProfileStore().active()
    except Exception:
        profile = None

    resolved = resolve_stored_symbol(store, symbol, timeframe, profile)
    if not resolved.found:
        raise NoRealData(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}. "
            f"Run Data -> Fetch market data with Timeframes = 5M,1H first."
        )
    if resolved.is_alias:
        print(f"  [i] {resolved.note}")
    return store.query(Symbol(resolved.resolved), Timeframe(timeframe))


def build_service(args: argparse.Namespace):
    from ShadBotTrader.application.services.dual_model_service import DualModelService

    if not args.with_features:
        return DualModelService(include_features=False)

    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set,
    )

    return DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )


def train_one(service, args, role, timeframe: str) -> int:
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe

    rule(f"{role.name.upper()} MODEL  ({timeframe} candles, {role.horizon} ahead)")
    print(f"  model id : {role.model_id}")
    print(f"  dataset  : {args.symbol} {timeframe}")
    if role.name == "signal":
        # State the labelling rule outright: it decides what BUY means.
        print(
            f"  label rule: a move of more than {args.threshold:.4%} over "
            f"{role.horizon} candles is BUY/SELL, otherwise HOLD"
        )
    print(f"  {role.description}")

    try:
        candles = load_candles(Path(args.storage_root), args.symbol, timeframe)
    except NoRealData as error:
        print(f"\n  [X] {error}")
        return 1
    print(f"\n  candles loaded : {len(candles)}")

    try:
        dataset = service.prepare(candles, Symbol(args.symbol), Timeframe(timeframe), role)
    except Exception as error:
        print(f"\n  [X] Cannot prepare data: {error}")
        return 1

    summary = dataset.summary()
    print(f"  usable rows    : {summary['rows']}")
    print(f"  feature columns: {summary['feature_columns']}")
    print(f"  dropped warmup : {summary['dropped_warmup']}")
    if summary["skipped_features"]:
        print(f"  skipped feats  : {summary['skipped_features']}")
    if dataset.label_distribution:
        print(f"  label balance  : {dataset.label_distribution}")
        if dataset.degenerate:
            print(
                "  [!] One class barely appears. A model trained here will "
                "learn to always answer the majority class."
            )

    try:
        import tensorflow  # noqa: F401
    except ImportError:
        print("\n  [i] TensorFlow is not installed, so training is skipped.")
        print("      Data preparation above is real and complete.")
        print("      Install with: pip install -r requirements-ai.txt")
        return 0

    # Phase 36: the reporter has existed since Phase 13 and nothing ever
    # passed it, so a run that takes twenty minutes printed one line at
    # the end. Silence during training is indistinguishable from a hang.
    from ShadBotTrader.infrastructure.ai.training_progress import (
        ConsoleProgressReporter,
        NullProgressReporter,
    )

    reporter = NullProgressReporter() if args.quiet else ConsoleProgressReporter()

    # Phase 41: say what this will cost BEFORE starting. A 500-row window
    # over 50,000 candles is 12 GB if materialised; the operator saw the
    # machine fill up with no explanation and no output.
    rows = len(dataset.series)
    windows = max(rows - role.window_size - role.horizon + 1, 0)
    naive_gb = windows * role.window_size * dataset.feature_count * 4 / 1e9

    # Phase 48: state the matrix shape outright at the start of every
    # run. "What am I actually feeding this thing" used to require
    # reading three files to answer.
    from ShadBotTrader.infrastructure.ai.model_diagram import describe_input_matrix

    rule("INPUT MATRIX")
    for line in describe_input_matrix(
        rows=rows,
        columns=dataset.feature_count,
        window_size=role.window_size,
        horizon=role.horizon,
    ):
        print(f"  {line}")
    print(f"  if materialised: {naive_gb:.1f} GB  (streamed instead when large)")
    if windows < 1:
        print(
            f"\n  [X] Not enough data: {rows:,} rows cannot make a single "
            f"{role.window_size}-row window."
        )
        print("      Use a smaller --window, or fetch more candles.")
        return 1

    print(f"\n  training roll-forward ({args.epochs} epoch(s), {args.folds} fold(s)) ...")
    # Phase 46: checkpoint after every epoch. The operator lost 18
    # completed epochs to a 2-hour timeout because nothing was written
    # until train() returned.
    checkpoint = make_epoch_checkpoint(args, role, timeframe, dataset)

    outcome = service.train(
        candles,
        Symbol(args.symbol),
        Timeframe(timeframe),
        role,
        run_id=f"{role.name}-demo",
        epochs=args.epochs,
        max_folds=args.folds,
        progress=reporter,
        on_epoch_model=checkpoint,
    )
    losses = outcome["fold_losses"]
    print(f"  fold losses    : {[round(value, 6) for value in losses]}")
    print_quality(outcome, role)
    save_model(outcome, args, role, timeframe, dataset, checkpoint)

    # ---- one live prediction so the output is concrete -----------------
    window = [row[: dataset.feature_count] for row in dataset.series[-role.window_size :]]
    last_close = float(candles[-1].close.amount)

    if role.name == "range":
        from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor

        forecast = RangePredictor(horizon=role.horizon, timeframe=timeframe).forecast(
            outcome["artifact"], window, reference_close=last_close
        )
        print(f"\n  PREDICTION for the next {role.horizon} {timeframe} candles:")
        print(f"    current close  : {forecast.reference_close:.2f}")
        print(
            f"    highest high   : {forecast.predicted_high:.2f} " f"({forecast.high_offset:+.3%})"
        )
        print(f"    lowest low     : {forecast.predicted_low:.2f} " f"({forecast.low_offset:+.3%})")
        ratio = forecast.reward_risk()
        print(f"    reward / risk  : {'n/a' if ratio is None else f'{ratio:.2f}'}")
        if not forecast.is_coherent:
            print(
                "    [!] The model put its high BELOW its low. With this little "
                "training that is expected; it is reported, not hidden."
            )
    else:
        from ShadBotTrader.infrastructure.ai.dual_predictor import SignalPredictor

        forecast = SignalPredictor(horizon=role.horizon, timeframe=timeframe).forecast(
            outcome["artifact"], window
        )
        print(f"\n  PREDICTION for the next {role.horizon} {timeframe} candles:")
        print(f"    sell : {forecast.sell_probability:6.1%}")
        print(f"    hold : {forecast.hold_probability:6.1%}")
        print(f"    buy  : {forecast.buy_probability:6.1%}")
        print(f"    -> {forecast.describe()}")
        print(f"    actionable (>=60%): {forecast.is_actionable()}")

    return 0


def make_epoch_checkpoint(args, role, timeframe: str, dataset):
    """A callback that writes the model after every epoch.

    Hours of training used to live only in RAM until the very last line
    of train(). Any interruption threw all of it away. Now each epoch
    overwrites a single ``checkpoint`` version, so the worst case is
    losing one epoch instead of twenty.

    The checkpoint reuses one version number on purpose: the point is a
    rescue copy, not a history. The final save still writes a proper new
    version through save_model().
    """
    from pathlib import Path

    from ShadBotTrader.infrastructure.ai.model_catalogue import (
        ModelCatalogue,
        ModelRecord,
    )

    root = Path(args.storage_root)
    catalogue = ModelCatalogue(root)
    state = {
        "version": catalogue.next_version(role.model_id),
        "best_score": float("inf"),
        "best_epoch": 0,
        "best_metric": "val_loss",
        "worse_streak": 0,
        "diagram_done": False,
    }

    def checkpoint(model, epoch: int, logs: dict, total_epochs: int) -> None:
        # Phase 48: the architecture picture, saved once per run on the
        # first epoch — the earliest moment a built model exists.
        if not state.get("diagram_done"):
            state["diagram_done"] = True
            try:
                from ShadBotTrader.infrastructure.ai.model_diagram import (
                    save_model_diagram,
                )

                target = (
                    Path(args.storage_root)
                    / "models"
                    / role.model_id
                    / f"v{state['version']}_architecture.png"
                )
                outcome = save_model_diagram(
                    model,
                    target,
                    title=f"{role.model_id} — {role.window_size} x {dataset.feature_count} input",
                )
                print(f"      {outcome.describe()}")
                if outcome.reason:
                    print(f"        ({outcome.reason})")
            except Exception as error:
                print(f"      [!] could not save the architecture diagram: {error}")

        from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
        from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
        from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
            FilesystemArtifactStore,
        )
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
            _serialize_model,
        )

        # Phase 47: keep the BEST epoch, not the newest one.
        #
        # Training loss falls almost monotonically; validation loss does
        # not. It falls, bottoms out, then climbs as the network starts
        # memorising. Saving whatever happened to run last therefore
        # saves the most overfitted model of the run — the operator asked
        # exactly the right question about this.
        #
        # val_loss is the judge rather than val_accuracy: accuracy moves
        # in coarse steps on a 3-class problem and ties constantly, while
        # loss registers every improvement in confidence.
        # Both roles are judged the same way, on their own metric: the
        # signal model reports val_loss, the range model val_mae. Naming
        # the metric in the log matters — a range model that printed
        # "val_loss" would send the operator hunting for a number that
        # is not there.
        metric_name = "val_loss"
        score = logs.get("val_loss")
        if score is None:
            if "val_mae" in logs:
                metric_name, score = "val_mae", logs["val_mae"]
            else:
                metric_name, score = "loss", logs.get("loss")
        score = float(score) if score is not None else float("inf")

        improved = score < state["best_score"]
        if not improved:
            state["worse_streak"] += 1
            print(
                f"      [epoch {epoch + 1}/{total_epochs}] {metric_name} "
                f"{score:.6f} — no better than {state['best_score']:.6f} "
                f"(best is epoch {state['best_epoch']}); keeping it"
            )
            return

        state["best_score"] = score
        state["best_epoch"] = epoch + 1
        state["best_metric"] = metric_name
        state["worse_streak"] = 0

        version = state["version"]
        payload = _serialize_model(model)
        artifact = ModelArtifact.create(
            model_id=ModelId(role.model_id),
            version=ModelVersion(version),
            framework="tensorflow",
            framework_version="",
            format="keras",
            payload=payload,
            training_run_id=f"{role.name}-epoch{epoch + 1}",
        )

        store = FilesystemArtifactStore(root)
        directory = root / "models" / role.model_id
        for name in (f"v{version}.bin", f"v{version}.json"):
            path = directory / name
            if path.exists():
                path.unlink()  # artifacts are immutable; replace
        store.save(artifact)

        catalogue.write(
            ModelRecord(
                model_id=role.model_id,
                role=role.name,
                symbol=args.symbol,
                timeframe=timeframe,
                version=version,
                rows=len(dataset.series),
                windows=max(len(dataset.series) - role.window_size - role.horizon + 1, 0),
                window_size=role.window_size,
                feature_columns=dataset.feature_count,
                epochs=epoch + 1,
                folds=args.folds,
                # Phase 49: the label rule travels with the model. Without
                # it, testing a 0.15%-trained model rebuilds 0.08% labels
                # and reports an accuracy that belongs to no model at all.
                threshold=(float(role.target.threshold) if role.name == "signal" else 0.0),
                horizon=int(role.horizon),
                metrics={k: float(v) for k, v in logs.items()},
                note=(f"best epoch {epoch + 1}/{total_epochs} " f"({metric_name} {score:.6f})"),
            )
        )
        print(
            f"      [BEST so far] epoch {epoch + 1}/{total_epochs} "
            f"{metric_name} {score:.6f} — saved as v{version}"
        )

    checkpoint.state = state  # type: ignore[attr-defined]
    return checkpoint


def save_model(outcome: dict, args, role, timeframe: str, dataset, checkpoint=None) -> None:
    """Persist the trained artifact and record what produced it.

    Phase 40: training used to fit a network, print a prediction and
    exit. Nothing reached datasets/models/, so "Retrain the model" had
    nothing to retrain and two runs could never be compared. Every run
    since Phase 29 was thrown away at process exit.

    The sidecar record is what lets the dashboard list models by role
    and dataset instead of asking the operator to decode a filename.
    """
    from pathlib import Path

    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
        FilesystemArtifactStore,
    )
    from ShadBotTrader.infrastructure.ai.model_catalogue import (
        ModelCatalogue,
        ModelRecord,
    )

    root = Path(args.storage_root)
    catalogue = ModelCatalogue(root)

    artifact = outcome["artifact"]
    metrics = (outcome.get("fold_metrics") or [{}])[-1]

    # Phase 47: `artifact` holds the weights of the LAST epoch. The
    # per-epoch checkpoint already saved the BEST one. Writing the last
    # epoch as a second version would leave two models on disk and put
    # the worse one at the top of the dropdown, which is precisely the
    # trap the operator asked about.
    state = getattr(checkpoint, "state", None)
    if state and state.get("best_epoch"):
        final = float(metrics.get("val_loss", metrics.get("val_mae", float("inf"))))
        best = float(state["best_score"])
        version = int(state["version"])
        label = state.get("best_metric", "val_loss")
        if final > best:
            print(
                f"\n  KEPT   {role.model_id} v{version} from epoch "
                f"{state['best_epoch']} ({label} {best:.6f})"
            )
            print(
                f"    the final epoch scored {final:.6f} — worse, so it was "
                f"NOT written over the best one"
            )
            print(f"    record  : {catalogue.record_path(role.model_id, version)}")
            return
        # The last epoch WAS the best; the checkpoint already stored it.
        print(
            f"\n  KEPT   {role.model_id} v{version} from the final epoch "
            f"({label} {final:.6f}, the best of the run)"
        )
        print(f"    record  : {catalogue.record_path(role.model_id, version)}")
        return

    version = catalogue.next_version(role.model_id)

    try:
        stored = artifact.with_version(version) if hasattr(artifact, "with_version") else artifact
        FilesystemArtifactStore(root).save(stored)
    except FileExistsError:
        # Artifact immutability is deliberate; fall through to the record
        # so the run is still described rather than silently unrecorded.
        print(f"  [!] artifact v{version} already exists; keeping the existing file")
    except Exception as error:
        print(f"  [!] could not save the artifact: {type(error).__name__}: {error}")
        return

    record = ModelRecord(
        model_id=role.model_id,
        role=role.name,
        symbol=args.symbol,
        timeframe=timeframe,
        version=version,
        rows=len(dataset.series),
        windows=max(len(dataset.series) - role.window_size - role.horizon + 1, 0),
        window_size=role.window_size,
        feature_columns=dataset.feature_count,
        epochs=args.epochs,
        folds=args.folds,
        threshold=(float(role.target.threshold) if role.name == "signal" else 0.0),
        horizon=int(role.horizon),
        metrics={key: float(value) for key, value in metrics.items()},
    )
    path = catalogue.write(record)
    print(f"\n  SAVED  {role.model_id} v{version}")
    print(f"    role    : {record.role} trained on {record.symbol} {record.timeframe}")
    print(f"    quality : {record.headline_metric}")
    print(f"    record  : {path}")


def print_quality(outcome: dict, role) -> None:
    """Report how good the model actually is, not just that it ran.

    Phase 36: the run printed fold losses and nothing else. A loss is
    unitless — 0.31 means nothing on its own — so this prints the metric
    that answers the question the operator is really asking.

    For the signal model that is accuracy against the majority-class
    baseline: a 3-class problem where one class dominates can reach 70%
    accuracy by never doing anything, and a model that has not beaten
    its baseline has learned nothing worth trading.
    """
    metrics = outcome.get("fold_metrics") or []
    if not metrics:
        return

    final = metrics[-1]
    print("\n  QUALITY (final fold)")
    for name in sorted(final):
        print(f"    {name:<16}: {final[name]:.6f}")

    if role.name == "signal":
        accuracy = final.get("val_accuracy", final.get("accuracy"))
        distribution = outcome.get("dataset", {}).get("label_distribution") or {}
        total = sum(distribution.values()) if distribution else 0
        if accuracy is not None and total:
            baseline = max(distribution.values()) / total
            verdict = "BETTER than" if accuracy > baseline else "NO BETTER than"
            print(
                f"\n    val_accuracy {accuracy:.1%} vs majority-class baseline " f"{baseline:.1%}"
            )
            print(f"    -> the model is {verdict} always predicting the commonest class.")
            if accuracy <= baseline:
                print(
                    "    With one epoch and a few folds this is expected; it is "
                    "reported rather than hidden."
                )
    else:
        mae = final.get("val_mae", final.get("mae"))
        if mae is not None:
            print(
                f"\n    val_mae {mae:.6f} — average error of the predicted "
                f"high/low offsets, as a fraction of price."
            )
            print(f"    On gold at 2,000 that is about {mae * 2000:.2f} USD per bound.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader.infrastructure.ai.model_roles import (
        range_model_role,
        signal_model_role,
    )

    print("=== ShadBotTrader — Phase 29 dual predictive models ===")
    print(f"symbol {args.symbol} | horizon {args.horizon} | window {args.window}")
    print(f"features: {'109-feature catalogue' if args.with_features else 'OHLCV only'}")

    service = build_service(args)
    status = 0

    # Which range timeframes to train (Phase 39). The operator can pick
    # one model and one dataset explicitly — training the 1H range model
    # on 1H candles is a different job from the 1D one, and mixing them
    # up silently would be worse than refusing.
    if args.model in ("range_1h", "range_1d"):
        range_timeframes = [args.model.split("_")[1].upper()]
    else:
        raw = args.range_timeframe or args.range_timeframes
        range_timeframes = [item.strip().upper() for item in raw.split(",") if item.strip()]

    wants_range = args.model in ("all", "both", "range", "range_1h", "range_1d")
    wants_signal = args.model in ("all", "both", "signal")

    planned = [f"range({tf})" for tf in range_timeframes] if wants_range else []
    if wants_signal:
        planned.append(f"signal({args.signal_timeframe})")
    print(f"training: {', '.join(planned) or 'nothing'}")

    if wants_range:
        for timeframe in range_timeframes:
            role = range_model_role(
                timeframe=timeframe,
                horizon=args.horizon,
                window_size=args.window,
            )
            status |= train_one(service, args, role, timeframe)

    if wants_signal:
        role = signal_model_role(
            timeframe=args.signal_timeframe,
            horizon=args.horizon,
            threshold=args.threshold,
            window_size=args.window,
        )
        status |= train_one(service, args, role, args.signal_timeframe)

    rule("DONE")
    print("  Both models train roll-forward: no future bar influences a past")
    print("  prediction. Labels for the final N candles are dropped, never guessed.")
    return status


if __name__ == "__main__":
    sys.exit(main())
