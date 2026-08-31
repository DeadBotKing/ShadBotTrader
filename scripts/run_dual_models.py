"""Phase 29 demo — train the two predictive models.

    RANGE MODEL   1H candles  ->  highest high + lowest low, next N bars
    SIGNAL MODEL  5M candles  ->  buy / sell with probabilities

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

# ── Windows console UTF-8 fix ──────────────────────────────────────────────
# Windows cmd/PowerShell default encoding is cp1252 which cannot print
# Unicode characters like +/- or arrows that appear in training logs.
# Reconfiguring stdout/stderr to UTF-8 prevents UnicodeEncodeError crashes.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except AttributeError:
        # Python < 3.7 — cannot reconfigure; best-effort replace
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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
        default="1D",
        help="comma separated timeframes to train a range model for (default: 1D)",
    )
    parser.add_argument("--range-timeframe", default="", help="alias of --range-timeframes")
    parser.add_argument("--signal-timeframe", default="5M", help="signal model candles")
    parser.add_argument(
        "--horizon",
        type=int,
        default=1,
        help=(
            "range candles to look ahead (default: 1 = next candle only). "
            "horizon=1 روی 1D: پیش‌بینی high/low فردا — دقیق‌ترین حالت. "
            "signal model searches until threshold hit (ignored for signal)."
        ),
    )
    parser.add_argument("--window", type=int, default=24, help="input window size")
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=100.0,
        help="percentage of chronological candles used for training (100 = all)",
    )
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--folds", type=int, default=2, help="roll-forward folds to keep")
    parser.add_argument(
        "--n-layers",
        type=int,
        default=0,
        help=(
            "WaveNet dilated layers per block (0 = role default: signal 5, "
            "range 4). Keep RF below the window — e.g. --window 150 with "
            "--n-layers 4 --n-blocks 2 gives RF=121 (81%%)."
        ),
    )
    parser.add_argument(
        "--n-blocks",
        type=int,
        default=0,
        help="WaveNet blocks (0 = role default: 2 for both roles).",
    )
    parser.add_argument(
        "--val-size",
        type=int,
        default=0,
        help=(
            "validation samples per fold. 0 = auto: 10%% of the labelled "
            "pool (was 2%% before Phase 59), clamped so the first fold "
            "still fits."
        ),
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.0,
        help=(
            "validation size as a fraction of the labelled pool, e.g. "
            "0.2 = 20%%. Ignored when --val-size > 0."
        ),
    )
    parser.add_argument("--learning-rate", type=float, default=1.5e-4)
    parser.add_argument(
        "--es-patience",
        type=int,
        default=0,
        help=(
            "EarlyStopping patience in epochs. 0 = auto (epochs/5, min 10). "
            "Raise it so ReduceLROnPlateau gets room to step LR down before "
            "the run is cut."
        ),
    )
    parser.add_argument(
        "--rlr-patience",
        type=int,
        default=0,
        help="ReduceLROnPlateau patience. 0 = auto (epochs/10, min 5).",
    )
    parser.add_argument(
        "--learning-rates",
        default="1e-5,3e-5,1e-4,3e-4,1e-3",
        help="comma-separated candidates for --tune-learning-rate",
    )
    parser.add_argument(
        "--tune-learning-rate",
        action="store_true",
        help="search candidates on pilot folds, then train/save with the winner",
    )
    parser.add_argument("--lr-search-epochs", type=int, default=1)
    parser.add_argument("--lr-search-folds", type=int, default=1)
    parser.add_argument(
        "--lr-search-only",
        action="store_true",
        help="search and report only; do not run the final training",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0008,
        help="signal price-move threshold used by the first-passage BUY/SELL labeler",
    )
    parser.add_argument(
        "--with-features",
        action="store_true",
        help="use the full standard feature catalogue (slower)",
    )
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the per-epoch training log",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Load the latest saved checkpoint and continue training from "
            "where it left off. Use when Colab disconnected mid-training. "
            "The saved epoch count is read from training.json and used as "
            "initial_epoch so Keras continues the learning-rate schedule."
        ),
    )
    return parser.parse_args(argv)


class NoRealData(RuntimeError):
    """Raised when a timeframe has no stored broker candles."""


def training_window_count(dataset, role) -> int:
    """Count ordinary or explicit first-passage training windows."""
    sample_ends = getattr(dataset, "sample_ends", None)
    if sample_ends is not None:
        return len(sample_ends)
    # PreparedDataset is already joined to complete labels. For a range
    # role, the horizon was consumed by attach_targets before this point;
    # subtracting it again under-counts the real generator by ``horizon``.
    return max(len(dataset.series) - role.window_size + 1, 0)


def effective_val_size(args: argparse.Namespace, pool_rows: int) -> int:
    """Resolve --val-size / --val-ratio against the labelled pool (فاز ۵۹).

    Returns 0 when neither option is set, meaning "trainer auto geometry"
    (10% of the pool, clamped — see ``DualModelService.build_trainer``).
    """
    if getattr(args, "val_size", 0) and args.val_size > 0:
        return int(args.val_size)
    if getattr(args, "val_ratio", 0.0) and args.val_ratio > 0:
        return max(4, int(pool_rows * float(args.val_ratio)))
    return 0


def signal_label_split_balance(
    dataset,
    role,
    max_folds: int,
    val_size_override: int = 0,
):
    """Train/validation BUY/SELL label balance for the signal model.

    For the binary signal model each labelled sample is a first-passage
    window whose label lives in the target column at ``dataset.sample_ends``.
    We rebuild the same expanding roll-forward plan the trainer will use
    (identical geometry from ``DualModelService.build_trainer``) and report
    the label counts of the LAST fold — the split that actually produces the
    saved artifact — as separate ``(train_balance, val_balance)`` dicts.

    Returns ``None`` for the range model (regression, no BUY/SELL labels).
    """
    sample_ends = getattr(dataset, "sample_ends", None)
    if sample_ends is None or not dataset.target_columns:
        return None

    from collections import Counter

    from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split

    rows = len(sample_ends)
    target_col = dataset.target_columns[0]
    labels = [int(round(dataset.series[idx][target_col])) for idx in sample_ends]

    # Mirror DualModelService.build_trainer geometry (Phase 39/44, فاز ۵۹)
    # so the split matches the folds actually trained on.
    val_size = val_size_override or max(4, min(2000, rows // 10))
    step = max(1, val_size)
    min_train_size = max(8, min(rows // 4, 20 * role.window_size))
    purge_gap = max(role.window_size - 1, 0)  # signal horizon is 0
    # Same guard as build_trainer (فاز ۵۹): first fold must fit.
    val_size = max(4, min(val_size, rows - min_train_size - purge_gap - 4))

    plan = expanding_split(
        total_length=rows,
        val_size=val_size,
        step=step,
        min_train_size=min_train_size,
        purge_gap=purge_gap,
        sample_end_indices=dataset.sample_ends,
        label_end_indices=dataset.sample_label_ends,
        window_size=role.window_size,
    )
    folds = list(plan.folds)
    if max_folds and max_folds > 0:
        folds = folds[-max_folds:]
    if not folds:
        return None
    last = folds[-1]

    def balance(slice_):
        counts = Counter(slice_)
        return {"sell": int(counts.get(0, 0)), "buy": int(counts.get(1, 0))}

    return (
        balance(labels[last.train_start : last.train_end]),
        balance(labels[last.val_start : last.val_end]),
    )


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


def parse_learning_rates(raw: str) -> list[float]:
    """Parse positive optimizer candidates from a dashboard/CLI field."""
    values: list[float] = []
    for token in (raw or "").replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        value = float(token)
        if value <= 0:
            raise ValueError(f"learning rate must be positive: {token}")
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError("at least one learning-rate candidate is required")
    return values


def search_learning_rate(service, args, role, timeframe: str, candles) -> float:
    """Select the lowest validation loss/MAE on a short walk-forward pilot."""
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.ai.training_progress import NullProgressReporter

    candles = training_prefix(candles, args, role)
    candidates = parse_learning_rates(args.learning_rates)
    metric_name = "val_loss" if role.name == "signal" else "val_mae"
    results: list[tuple[float, float]] = []
    rule(f"LEARNING RATE SEARCH — {role.name.upper()} / {timeframe}")
    print(f"  candidates : {', '.join(f'{rate:.2e}' for rate in candidates)}")
    print(f"  pilot      : {args.lr_search_epochs} epoch(s), {args.lr_search_folds} fold(s)")

    for rate in candidates:
        print(f"  testing    {rate:.2e} ...", flush=True)
        try:
            outcome = service.train(
                candles,
                Symbol(args.symbol),
                Timeframe(timeframe),
                role,
                run_id=f"lr-search-{role.name}-{rate:.2e}",
                epochs=max(args.lr_search_epochs, 1),
                max_folds=max(args.lr_search_folds, 1),
                progress=NullProgressReporter(),
                learning_rate=rate,
            )
            metrics = (outcome.get("fold_metrics") or [{}])[-1]
            score = metrics.get(metric_name)
            if score is None:
                score = metrics.get("val_loss")
            if score is None:
                raise ValueError(f"training did not report {metric_name}")
            score = float(score)
            results.append((rate, score))
            print(f"  {rate:.2e} -> {metric_name}={score:.6f}")
        except Exception as error:
            print(f"  {rate:.2e} -> FAILED: {type(error).__name__}: {error}")

    if not results:
        raise RuntimeError("every learning-rate candidate failed")
    winner, score = min(results, key=lambda item: item[1])
    print(f"  SELECTED   {winner:.2e} ({metric_name}={score:.6f})")
    return winner


def training_prefix(candles, args, role):
    """Keep only the chronological training prefix for OOS evaluation."""
    ratio = float(args.train_ratio)
    if not 0 < ratio <= 100:
        raise ValueError("train_ratio must be in (0, 100]")
    if ratio >= 100:
        return candles
    cutoff = max(role.window_size + 2, int(len(candles) * ratio / 100.0))
    if cutoff >= len(candles):
        return candles
    print(f"  train prefix    : {cutoff:,}/{len(candles):,} candles ({ratio:.1f}%)")
    return candles[:cutoff]


def _load_resume_weights(args, role) -> tuple:
    """Load saved checkpoint weights for resume training (Phase 50).

    Reads the latest training.json to find how many epochs were already
    completed, then loads the corresponding .bin artifact bytes so the
    trainer can warm-start the model weights instead of starting random.

    Returns:
        (weights_bytes, initial_epoch) — weights_bytes is None when no
        checkpoint exists and the caller should start from scratch.
    """
    from pathlib import Path

    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
        FilesystemArtifactStore,
    )
    from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

    root = Path(args.storage_root)
    catalogue = ModelCatalogue(root)
    version = catalogue.latest_version(role.model_id)
    if not version:
        print("  [i] RESUME: no saved checkpoint found — starting from scratch")
        return None, 0

    record = catalogue.read(role.model_id, version)
    if record is None:
        print("  [i] RESUME: cannot read training.json — starting from scratch")
        return None, 0

    initial_epoch = int(record.epochs or 0)
    if initial_epoch <= 0:
        print("  [i] RESUME: training.json has epochs=0 — starting from scratch")
        return None, 0

    store = FilesystemArtifactStore(root)
    artifact = store.load(ModelId(role.model_id), ModelVersion(version))
    if artifact is None:
        print(
            f"  [!] RESUME: training.json says epoch={initial_epoch} "
            f"but artifact v{version} not found — starting from scratch"
        )
        return None, 0

    print(
        f"  RESUME: loaded checkpoint v{version} "
        f"(epoch {initial_epoch}, {record.headline_metric})"
    )
    return artifact.payload, initial_epoch


def train_one(service, args, role, timeframe: str, learning_rate: float | None = None) -> int:
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe

    learning_rate = float(learning_rate or args.learning_rate)
    if learning_rate <= 0:
        raise ValueError("learning rate must be positive")
    horizon_text = "until threshold hit" if role.name == "signal" else f"{role.horizon} ahead"
    rule(f"{role.name.upper()} MODEL  ({timeframe} candles, {horizon_text})")
    print(f"  learning rate: {learning_rate:.2e}")
    print(f"  model id : {role.model_id}")
    print(f"  dataset  : {args.symbol} {timeframe}")
    # فاز ۶۱: معماری و پوشش RF را صریح چاپ کن — RF > window یعنی
    # لایه‌های اضافه فقط پارامتر هدررفته‌اند.
    from ShadBotTrader.infrastructure.ai.model_roles import receptive_field

    _rf = receptive_field(role.n_layers_per_block, role.n_blocks, role.kernel_size)
    _coverage = _rf / role.window_size if role.window_size else 0.0
    print(
        f"  architecture : window={role.window_size} · "
        f"{role.n_layers_per_block} layers × {role.n_blocks} blocks · "
        f"RF={_rf} ({_coverage:.0%} of window)"
    )
    # فاز ۷۴: patienceها — شفاف چه چیزی تنظیم است
    _es_p = max(getattr(args, "es_patience", 0), 0) or "auto (epochs/5)"
    _rlr_p = max(getattr(args, "rlr_patience", 0), 0) or "auto (epochs/10)"
    print(f"  callbacks    : EarlyStopping patience={_es_p} · ReduceLR patience={_rlr_p}")
    if _rf > role.window_size:
        print(
            f"  [!] RF {_rf} > window {role.window_size} — outer layers see "
            "only padding. Consider --n-layers/--n-blocks (e.g. 4x2 -> RF=121)."
        )
    if role.name == "signal":
        # State the binary labelling rule outright.
        print(
            f"  label rule: first future close reaching +/-{role.target.threshold:.4%} "
            "is BUY/SELL; search continues until a barrier is hit"
        )
    print(f"  {role.description}")

    try:
        candles = load_candles(Path(args.storage_root), args.symbol, timeframe)
    except NoRealData as error:
        print(f"\n  [X] {error}")
        return 1
    print(f"\n  candles loaded : {len(candles)}")
    candles = training_prefix(candles, args, role)

    try:
        dataset = service.prepare(candles, Symbol(args.symbol), Timeframe(timeframe), role)
    except Exception as error:
        print(f"\n  [X] Cannot prepare data: {error}")
        return 1

    summary = dataset.summary()
    print(f"  usable rows    : {summary['rows']}")
    print(f"  feature columns: {summary['feature_columns']}")
    print(f"  dropped warmup : {summary['dropped_warmup']}")
    if role.name == "range":
        # فاز ۹۵: واحد تارگت صریح — ATR یعنی مدل «چند ATR» یاد میگیرد
        units = summary.get("target_units", "pct")
        detail = (
            "(offset = (future − close) / ATR14 — price = close + mult × ATR14)"
            if units == "atr"
            else "(offset = (future − close) / close — legacy)"
        )
        print(f"  target units   : {units} {detail}")
    print(
        f"  causal input  : {summary.get('feature_columns', 0)} features; "
        f"excluded {summary.get('excluded_features', 0)} non-causal/unknown"
    )
    if summary["skipped_features"]:
        print(f"  skipped feats  : {summary['skipped_features']}")
    val_fold_baseline: float | None = None  # فاز ۶۰: baseline فولد آخرِ ولید
    if dataset.label_distribution:
        print(f"  label balance  : {dataset.label_distribution}")
        if dataset.degenerate:
            print(
                "  [!] One class barely appears. A model trained here will "
                "learn to always answer the majority class."
            )
        # train/validation split of the BUY/SELL labels (signal model)
        pool = training_window_count(dataset, role)
        split = signal_label_split_balance(
            dataset, role, int(args.folds), val_size_override=effective_val_size(args, pool)
        )
        if split is not None:
            train_balance, val_balance = split
            print(f"  train labels   : {train_balance}")
            print(f"  val labels     : {val_balance}")
            # فاز ۶۰: برای حکمِ QUALITY — baseline واقعی فولد آخرِ ولید.
            _val_total = sum(val_balance.values())
            val_fold_baseline = max(val_balance.values()) / _val_total if _val_total else None

    # فاز ۵۹: اندازهٔ ولیدیشن را صریح چاپ کن تا کمبودش پنهان نماند.
    # فاز ۶۳: همان تعریف rows که build_trainer استفاده می‌کند (سیگنال =
    # تعداد برچسب‌ها؛ رنج = طول series) تا عدد چاپ‌شده با fold واقعی یکی
    # باشد (اجرای range: سربرگ ۴۳۳ چاپ کرد ولی فولد واقعی ۴۴۸ بود).
    _se = getattr(dataset, "sample_ends", None)
    pool = len(_se) if _se is not None else len(dataset.series)
    resolved = effective_val_size(args, pool) or max(4, min(2000, pool // 10))
    share = (resolved / pool * 100.0) if pool else 0.0
    print(
        f"  val fold size  : {resolved} samples per fold "
        f"({share:.1f}% of {pool} labelled windows)"
    )

    # فاز ۹۵: baseline «پیش‌بینی ثابت» برای رنج — مدل رنج با تارگتِ
    # بدون مقیاس به میانگین ثابت فرو می‌ریخت. حالا معیار قضاوت مستقیم است:
    # MAE یک پیش‌بینی‌کنندهٔ ثابت (میانهٔ train) روی همان فولد ولید.
    # اگر val_mae مدل از این عدد کمتر نباشد، مدل چیزی یاد نگرفته.
    _units = getattr(dataset, "target_units", "pct") or "pct"
    if role.name == "range" and 0 < resolved < len(dataset.series):
        import statistics as _stats

        _tcols = dataset.target_columns
        _rows = dataset.series
        _train_rows = _rows[: len(_rows) - resolved]
        _val_rows = _rows[len(_rows) - resolved :]
        if _train_rows and _val_rows:
            _total = 0.0
            for _c in _tcols:
                _med = _stats.median(row[_c] for row in _train_rows)
                _total += sum(abs(row[_c] - _med) for row in _val_rows) / len(_val_rows)
            val_fold_baseline = _total / len(_tcols)
            unit_tag = "ATR14" if _units == "atr" else "frac"
            print(
                f"  constant base  : {val_fold_baseline:.4f} {unit_tag} "
                f"(MAE of always predicting the train median on the last "
                f"{resolved} rows — the model must beat this)"
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

    # فاز ۹۵: گزارشگر با واحد درست ساخته شود — val_mae برای مدل ATR
    # «ضریب ATR» است و دلارِ آن mult × ATR14 است، نه mult × قیمت.
    _atr_last = None
    if role.name == "range" and _units == "atr":
        from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

        _atr_value = atr_from_candles(candles, period=14)
        _atr_last = float(_atr_value) if _atr_value else None
    if not isinstance(reporter, NullProgressReporter):
        reporter = ConsoleProgressReporter(target_units=_units, atr_reference=_atr_last or 0.0)

    # Phase 41: say what this will cost BEFORE starting. A 500-row window
    # over 50,000 candles is 12 GB if materialised; the operator saw the
    # machine fill up with no explanation and no output.
    rows = len(dataset.series)
    windows = training_window_count(dataset, role)
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
        labels_already_aligned=True,
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

    # Phase 50: --resume — load existing checkpoint weights and continue.
    resume_weights: bytes | None = None
    initial_epoch: int = 0
    if getattr(args, "resume", False):
        resume_weights, initial_epoch = _load_resume_weights(args, role)

    remaining_epochs = args.epochs - initial_epoch
    if remaining_epochs <= 0:
        print(
            f"\n  [i] RESUME: already trained {initial_epoch} epochs "
            f"(target={args.epochs}). Nothing to do."
        )
        print("      Increase --epochs to train further.")
        return 0

    if initial_epoch > 0:
        print(
            f"\n  RESUME: continuing from epoch {initial_epoch} — "
            f"{remaining_epochs} epoch(s) remaining"
        )

    print(
        f"\n  training roll-forward ({remaining_epochs} epoch(s) remaining, "
        f"{args.folds} fold(s)) ..."
    )
    # Phase 46: checkpoint after every epoch. The operator lost 18
    # completed epochs to a 2-hour timeout because nothing was written
    # until train() returned.
    checkpoint = make_epoch_checkpoint(args, role, timeframe, dataset, learning_rate)

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
        learning_rate=learning_rate,
        initial_epoch=initial_epoch,
        resume_weights=resume_weights,
        val_size=effective_val_size(args, training_window_count(dataset, role)),
        early_stopping_patience=max(getattr(args, "es_patience", 0), 0),
        reduce_lr_patience=max(getattr(args, "rlr_patience", 0), 0),
    )
    losses = outcome["fold_losses"]
    print(f"  fold losses    : {[round(value, 6) for value in losses]}")
    print_quality(
        outcome,
        role,
        reference_price=float(candles[-1].close.amount),
        val_baseline=val_fold_baseline,
        target_units=_units,
        atr_reference=_atr_last,
    )
    save_model(outcome, args, role, timeframe, dataset, checkpoint, learning_rate)

    # ---- one live prediction so the output is concrete -----------------
    window = [row[: dataset.feature_count] for row in dataset.series[-role.window_size :]]
    last_close = float(candles[-1].close.amount)

    if role.name == "range":
        from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor
        from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

        target_units = getattr(dataset, "target_units", "pct") or "pct"
        atr_reference = None
        if target_units == "atr":
            # فاز ۹۵: مدل ATR به ATR(14) کندل مرجع نیاز دارد
            atr_value = atr_from_candles(candles, period=14)
            atr_reference = float(atr_value) if atr_value else None

        forecast = RangePredictor(
            horizon=role.horizon, timeframe=timeframe, target_units=target_units
        ).forecast(
            outcome["artifact"],
            window,
            reference_close=last_close,
            atr_reference=atr_reference,
        )
        print(f"\n  PREDICTION for the next {role.horizon} {timeframe} candles:")
        print(f"    current close  : {forecast.reference_close:.2f}")
        if target_units == "atr":
            print(f"    ATR(14) ref    : {forecast.atr_reference:.2f}")
            print(
                f"    highest high   : {forecast.predicted_high:.2f} "
                f"({forecast.high_atr_mult:+.2f}×ATR | {forecast.high_offset:+.3%})"
            )
            print(
                f"    lowest low     : {forecast.predicted_low:.2f} "
                f"({forecast.low_atr_mult:+.2f}×ATR | {forecast.low_offset:+.3%})"
            )
        else:
            print(
                f"    highest high   : {forecast.predicted_high:.2f} "
                f"({forecast.high_offset:+.3%})"
            )
            print(
                f"    lowest low     : {forecast.predicted_low:.2f} "
                f"({forecast.low_offset:+.3%})"
            )
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
        print(f"    buy  : {forecast.buy_probability:6.1%}")
        print(f"    -> {forecast.describe()}")
        print(f"    actionable (>=60%): {forecast.is_actionable()}")

    return 0


def make_epoch_checkpoint(args, role, timeframe: str, dataset, learning_rate: float = 1.5e-4):
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
        # in coarse steps on a binary problem and ties constantly, while
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
                windows=training_window_count(dataset, role),
                window_size=role.window_size,
                feature_columns=dataset.feature_count,
                epochs=epoch + 1,
                folds=args.folds,
                # Phase 49: the label rule travels with the model. Without
                # it, testing a 0.15%-trained model rebuilds 0.08% labels
                # and reports an accuracy that belongs to no model at all.
                threshold=(float(role.target.threshold) if role.name == "signal" else 0.0),
                # LR واقعی بعد از ReduceLROnPlateau رو ذخیره کن
                learning_rate=float(logs.get("learning_rate", learning_rate)),
                loss_function=role.loss,
                horizon=int(role.horizon),
                # فاز ۹۵: واحد تارگت — مدل رنج ATR پس پیش‌بینی در ضرایب ATR است
                target_units=(
                    (getattr(dataset, "target_units", "pct") or "pct")
                    if role.name == "range"
                    else "pct"
                ),
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


def save_model(
    outcome: dict,
    args,
    role,
    timeframe: str,
    dataset,
    checkpoint=None,
    learning_rate: float = 1.5e-4,
) -> None:
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
        windows=training_window_count(dataset, role),
        window_size=role.window_size,
        feature_columns=dataset.feature_count,
        epochs=args.epochs,
        folds=args.folds,
        threshold=(float(role.target.threshold) if role.name == "signal" else 0.0),
        learning_rate=float(learning_rate),
        loss_function=role.loss,
        horizon=int(role.horizon),
        # فاز ۹۵: واحد تارگت — مدل رنج ATR پس پیش‌بینی در ضرایب ATR است
        target_units=(
            (getattr(dataset, "target_units", "pct") or "pct") if role.name == "range" else "pct"
        ),
        metrics={key: float(value) for key, value in metrics.items()},
    )
    path = catalogue.write(record)
    print(f"\n  SAVED  {role.model_id} v{version}")
    print(f"    role    : {record.role} trained on {record.symbol} {record.timeframe}")
    print(f"    quality : {record.headline_metric}")
    print(f"    loss fn : {record.loss_function}")
    print(f"    record  : {path}")


def print_quality(
    outcome: dict,
    role,
    reference_price: float | None = None,
    val_baseline: float | None = None,
    target_units: str = "pct",
    atr_reference: float | None = None,
) -> None:
    """Report how good the model actually is, not just that it ran.

    Phase 36: the run printed fold losses and nothing else. A loss is
    unitless — 0.31 means nothing on its own — so this prints the metric
    that answers the question the operator is really asking.

    For the binary signal model that is accuracy against the
    majority-class baseline: a dataset with one direction dominating can
    reach high accuracy by always predicting it, and a model that has
    not beaten its baseline has learned nothing worth trading.
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
            # فاز ۶۰: baseline باید از توزیع لیبلِ **ولیدیشنِ فولد آخر** باشد،
            # نه کل استخر. در اجرای 2026-08-26 استخر 50/50 بود ولی فولد آخر
            # 65.2% sell — یعنی همیشه-sell روی همان ولید 65.2% می‌گرفت و
            # مقایسه با 50.3% حکمِ گمراه‌کننده می‌داد.
            pool_baseline = max(distribution.values()) / total
            if val_baseline is None:
                val_baseline = pool_baseline
            verdict = "BETTER than" if accuracy > val_baseline else "NO BETTER than"
            print(
                f"\n    val_accuracy {accuracy:.1%} vs val-fold majority baseline "
                f"{val_baseline:.1%}"
            )
            if abs(val_baseline - pool_baseline) > 0.02:
                print(
                    f"    (pool majority baseline is {pool_baseline:.1%}; the val "
                    "fold is regime-shifted — always-predict-majority scores "
                    f"{val_baseline:.1%} there)"
                )
            print(f"    -> the model is {verdict} always predicting the commonest class.")
            if accuracy <= val_baseline:
                print(
                    "    With one epoch and a few folds this is expected; it is "
                    "reported rather than hidden."
                )
    else:
        mae = final.get("val_mae", final.get("mae"))
        if mae is not None:
            # فاز ۹۵: واحد پیام با واحد تارگت یکی باشد
            if target_units == "atr":
                print(
                    f"\n    val_mae {mae:.4f} ATR14 — average miss of the "
                    f"predicted high/low, in ATR multiples."
                )
                if atr_reference is not None and atr_reference > 0:
                    print(
                        f"    With ATR14={atr_reference:.2f}, that is about "
                        f"{mae * atr_reference:.2f} USD per bound."
                    )
            else:
                print(
                    f"\n    val_mae {mae:.6f} — average error of the predicted "
                    f"high/low offsets, as a fraction of price."
                )
                if reference_price is not None and reference_price > 0:
                    tf_name = getattr(role, "timeframe", "the market")
                    print(
                        f"    At {reference_price:.2f} on {tf_name}, "
                        f"that is about {mae * reference_price:.2f} USD per bound."
                    )
                else:
                    print("    USD translation skipped: no reference close was supplied.")

            # فاز ۹۵-ج: حکم باید روی «آخرین timestep» باشد — همان خروجی که
            # inference مصرف می‌کند. val_mae کراس روی هر ۱۵۰ موقعیت پنجره
            # میانگین می‌گیرد و موقعیت‌های اولِ پنجره عمداً کمتر آموزش
            # می‌بینند (وزن loss: 40% کل، 60% آخرین) → val_mae تمام-سکانس
            # همیشه بدتر از توان واقعی مدل دیده می‌شود.
            high_mae = final.get("val_high_mae")
            low_mae = final.get("val_low_mae")
            if high_mae is not None and low_mae is not None:
                last_step_mae = (high_mae + low_mae) / 2.0
                print(
                    f"    final-step MAE (what inference uses): {last_step_mae:.4f} "
                    f"— full-sequence val_mae {mae:.4f} averages every window "
                    f"position and is NOT the trading number."
                )
            else:
                last_step_mae = mae

            # حکم مستقیم مقابل پیش‌بینی ثابت — ریشهٔ مشکل آفست ثابت همین‌جا
            # قابل سنجش است (baseline روی همان ردیف‌های فولد آخر است).
            if val_baseline is not None:
                if last_step_mae < val_baseline:
                    print(
                        f"    vs constant baseline {val_baseline:.4f}: the model "
                        f"BEATS always predicting the train median by "
                        f"{val_baseline - last_step_mae:.4f} "
                        f"({(val_baseline - last_step_mae) / val_baseline:.0%} better)."
                    )
                else:
                    print(
                        f"    vs constant baseline {val_baseline:.4f}: the final-step "
                        f"MAE {last_step_mae:.4f} is NO BETTER than a constant "
                        f"prediction — it has not learned anything usable yet."
                    )

            bound_labels = (
                ("val_high_mae", "high MAE"),
                ("val_low_mae", "low MAE"),
                ("val_high_rmse", "high RMSE"),
                ("val_low_rmse", "low RMSE"),
                ("val_high_bias", "high bias"),
                ("val_low_bias", "low bias"),
            )
            for key, label in bound_labels:
                if key in final:
                    print(f"    {label:<10}: {final[key]:+.6f}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader.infrastructure.ai.model_roles import (
        range_model_role,
        signal_model_role,
    )

    print("=== ShadBotTrader — Phase 29 dual predictive models ===")
    print(f"symbol {args.symbol} | horizon {args.horizon} | window {args.window}")
    # فاز ۹۵: عدد کاتالوگ هاردکد نباشد — تعداد واقعی در سربرگ خود مدل
    # چاپ می‌شود (feature columns). اینجا فقط حالت گفته می‌شود.
    print(f"features: {'full standard catalogue' if args.with_features else 'OHLCV only'}")

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

    def run_role(role, timeframe: str) -> None:
        nonlocal status
        rate = args.learning_rate
        if args.tune_learning_rate:
            try:
                candles = load_candles(Path(args.storage_root), args.symbol, timeframe)
                rate = search_learning_rate(service, args, role, timeframe, candles)
            except Exception as error:
                print(f"\n  [X] Learning-rate search failed: {type(error).__name__}: {error}")
                status |= 1
                return
            if args.lr_search_only:
                return
        try:
            status |= train_one(service, args, role, timeframe, learning_rate=rate)
        except Exception as error:
            print(f"\n  [X] Training failed: {type(error).__name__}: {error}")
            status |= 1

    if wants_range:
        for timeframe in range_timeframes:
            run_role(
                range_model_role(
                    timeframe=timeframe,
                    horizon=args.horizon,
                    window_size=args.window,
                    n_layers_per_block=args.n_layers or None,
                    n_blocks=args.n_blocks or None,
                ),
                timeframe,
            )

    if wants_signal:
        run_role(
            signal_model_role(
                timeframe=args.signal_timeframe,
                horizon=0,
                threshold=args.threshold,
                window_size=args.window,
                n_layers_per_block=args.n_layers or None,
                n_blocks=args.n_blocks or None,
            ),
            args.signal_timeframe,
        )

    rule("DONE")
    print("  Both models train roll-forward: no future bar influences a past")
    print("  prediction. Signal starts without a future threshold hit are dropped;")
    print("  no HOLD labels or guessed outcomes are added.")
    return status


if __name__ == "__main__":
    sys.exit(main())
