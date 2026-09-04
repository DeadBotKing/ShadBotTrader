"""Command handlers (Phase 19, section 13).

    Controller -> Command Bus -> Command Handler -> Application Service

Each handler is thin on purpose: it validates input, calls an existing
application service, and turns the outcome into a ``CommandResult``.
None of them contains trading, AI, risk or persistence logic — that all
lives where it already lived. If a handler ever starts calculating
something, it has crossed the line §4 draws.
"""

from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ShadBotTrader.presentation.commands.commands import (
    Command,
    CommandDescriptor,
    CommandField,
    CommandKind,
    CommandResult,
    CommandStatus,
)

Handler = Callable[[Command], CommandResult]

#: The two timeframes the platform trains on: 5M feeds the signal model,
#: 1H feeds the range model (Phase 29 §2). They are fetched together
#: because building the dataset with only one of them is not a smaller
#: dataset — it is a missing model.
TRAINING_TIMEFRAMES: tuple[str, ...] = ("5M", "1H", "1D")


#: Where a running script's output is streamed so the dashboard and the
#: operator can watch it while it is still running (Phase 36).
RUN_LOG_DIR = Path("run_logs")


def run_log_path(action: str, root: "str | Path" = RUN_LOG_DIR) -> Path:
    """The live log file for one command.

    One file per command kind, overwritten each run: the point is to
    answer "what is happening right now", and an ever-growing archive of
    old attempts makes that question harder, not easier. Finished runs
    are already summarised in the command history.
    """
    safe = "".join(character for character in action if character.isalnum() or character in "-_")
    return Path(root) / f"{safe or 'command'}.log"


#: Lines that carry a result rather than progress chatter. When the log
#: is longer than the window the dashboard shows, these are kept and the
#: batch ticks are thinned — a batch counter scrolling past is useless if
#: it hides the epoch's loss (Phase 42).
_IMPORTANT_MARKERS = (
    "epoch ",
    "fold ",
    "val_loss",
    "val_mae",
    "val_accuracy",
    "SAVED",
    "QUALITY",
    "PREDICTION",
    "[X]",
    "[!]",
    "[i]",
    "TRAINING",
    "FEATURES",
    "Traceback",
    "Error",
    "error",
    "$ ",
)


def _is_progress_tick(line: str) -> bool:
    """True for a batch progress line — safe to drop when space is short."""
    stripped = line.strip()
    return stripped.startswith("[") and "batch " in stripped and "%" in stripped


def read_run_log(action: str, root: "str | Path" = RUN_LOG_DIR, lines: int = 200) -> List[str]:
    """The tail of a command's live log, or an empty list.

    A naive tail is wrong here. A long training run emits far more batch
    ticks than result lines, so the plain last-N window filled up with
    progress bars and pushed every epoch result out of sight — the
    operator watched a counter scroll and never saw a single loss value.

    So when the log does not fit, the ticks are thinned first and the
    result lines are kept. The most recent lines always survive,
    whatever kind they are.
    """
    path = run_log_path(action, root)
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    all_lines = text.splitlines()
    if len(all_lines) <= lines:
        return all_lines

    # Always keep the most recent lines verbatim: whatever is happening
    # right now matters more than what happened ten minutes ago.
    recent_size = max(lines // 4, 10)
    recent = all_lines[-recent_size:]
    earlier = all_lines[:-recent_size]

    budget = lines - len(recent)

    # Walk backwards so that, when the budget runs out, it is the OLDEST
    # material that is dropped rather than the newest.
    important: List[str] = []
    ticks: List[tuple[int, str]] = []
    for index in range(len(earlier) - 1, -1, -1):
        line = earlier[index]
        if _is_progress_tick(line):
            ticks.append((index, line))
        elif any(marker in line for marker in _IMPORTANT_MARKERS):
            important.append(line)

    # Result lines come first in the budget; they are the answer the
    # operator is waiting for. Ticks only fill whatever is left.
    selected_important = list(reversed(important[:budget]))
    remaining = budget - len(selected_important)

    selected_ticks: List[str] = []
    if remaining > 0 and ticks:
        # Spread the surviving ticks across the run instead of taking a
        # contiguous block, so the shape of the whole epoch stays visible.
        ordered = list(reversed(ticks))
        stride = max(1, len(ordered) // remaining)
        selected_ticks = [
            line for position, (_, line) in enumerate(ordered) if position % stride == 0
        ]
        selected_ticks = selected_ticks[-remaining:]

    # Re-interleave in file order.
    wanted_important = list(selected_important)
    wanted_ticks = list(selected_ticks)
    merged: List[str] = []
    for line in earlier:
        if wanted_important and line == wanted_important[0]:
            merged.append(wanted_important.pop(0))
        elif wanted_ticks and line == wanted_ticks[0]:
            merged.append(wanted_ticks.pop(0))

    return merged[-budget:] + recent


DEFAULT_LEARNING_RATE = 1.5e-4


def _parse_spread(command: Any) -> "tuple[Decimal, Optional[Decimal]]":
    """spread_mode و spread_value رو بخون و (spread_fixed, spread_pct) برگردون.

    pct mode:   spread_fixed=0, spread_pct=0.0006
    fixed mode: spread_fixed=1.80, spread_pct=None
    """
    mode = command.text("spread_mode", "pct").strip().lower()
    value = Decimal(str(command.number("spread_value", 0.06)))

    if mode == "pct":
        # آلپاری: spread به صورت درصد
        # مثلاً 0.06 → 0.06% → 0.0006 fraction
        pct = value / Decimal("100")  # 0.06 → 0.0006
        return Decimal("0"), pct
    else:
        # spread ثابت دلاری
        return value, None


def saved_learning_rate(storage_root: str | Path, model_id: str) -> float:
    """Return the last selected LR for a model, or the platform default."""
    try:
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        catalogue = ModelCatalogue(storage_root)
        version = catalogue.latest_version(model_id)
        record = catalogue.read(model_id, version) if version else None
        value = float(record.learning_rate) if record is not None else 0.0
        return value if value > 0 else DEFAULT_LEARNING_RATE
    except Exception:
        return DEFAULT_LEARNING_RATE


def _split_model_spec(text: str, default_id: str) -> tuple[str, int | None]:
    """فاز ۹۶: «id» یا «id:vN» → (model_id, version|None).

    خالی → (default_id, None) یعنی جدیدترین نسخه.
    """
    raw = (text or "").strip()
    if not raw:
        return default_id, None
    if ":" in raw:
        model_id, _, version = raw.partition(":")
        version = version.strip().lstrip("vV")  # «v1» یا «1» هر دو قبول
        return (model_id.strip() or default_id), (int(version) if version.isdigit() else None)
    return raw, None


def percent_to_fraction(raw: str, default: float) -> float:
    """Turn a percent typed by a human into the fraction the code uses.

    ``0.08`` means 0.08%, which is 0.0008 as a return. Accepts a stray
    ``%`` and falls back rather than raising: a malformed number in a
    form field should not abort a training run that is otherwise valid.
    """
    text = str(raw).strip().rstrip("%").strip()
    if not text:
        return default
    try:
        value = float(text)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value / 100.0


def parse_timeframes(raw: str) -> List[str]:
    """Split a ``5M,1H`` field into an ordered, de-duplicated list."""
    seen: List[str] = []
    for token in (raw or "").replace(";", ",").replace(" ", ",").split(","):
        cleaned = token.strip().upper()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


# ---------------------------------------------------------------- registry --
#: Roles the operator can train, in the words they think in.
MODEL_ROLE_CHOICES: tuple[str, ...] = ("all", "range", "signal", "trend")


def stored_dataset_choices(storage_root: "str | Path" = "datasets") -> List[str]:
    """Timeframes that actually have stored candles, for a dropdown.

    Phase 40: the operator asked to pick a dataset from a list rather
    than type one. Offering a timeframe with no data would be offering a
    guaranteed failure, so the list is built from what is on disk and
    falls back to the training timeframes only when nothing is stored
    yet (the very first run, where the list would otherwise be empty).
    """
    from ShadBotTrader.infrastructure.data.symbol_scope import stored_symbols

    root = Path(storage_root)
    processed = root / "processed"
    found: List[str] = []
    if processed.is_dir():
        for symbol in stored_symbols(root):
            directory = processed / symbol
            if not directory.is_dir():
                continue
            for entry in sorted(directory.iterdir()):
                if entry.is_dir() and entry.name not in found:
                    found.append(entry.name)

    if not found:
        return list(TRAINING_TIMEFRAMES)

    order = {name: index for index, name in enumerate(TRAINING_TIMEFRAMES)}
    return sorted(found, key=lambda name: (order.get(name, 99), name))


def trained_model_choices(storage_root: "str | Path" = "datasets") -> List[str]:
    """Model ids that exist on disk, newest first.

    Empty when nothing has been trained yet — the handler then explains
    that rather than presenting an empty dropdown as if it were a choice.
    """
    from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

    return ModelCatalogue(storage_root).choices()


def descriptors(storage_root: "str | Path" = "datasets") -> List[CommandDescriptor]:
    """Every command the dashboard offers, with its form.

    ``storage_root`` is read (never written) so the dropdowns can show
    the datasets and models that genuinely exist.
    """
    datasets = stored_dataset_choices(storage_root)
    trained = trained_model_choices(storage_root)
    return [
        CommandDescriptor(
            kind=CommandKind.FETCH_MARKET_DATA,
            label="Fetch market data",
            description=(
                "Download real candles from MetaTrader 5 for EVERY listed "
                "timeframe and append them to the stored history. Requires "
                "Windows with the MT5 terminal running — generated sample "
                "data is never substituted for real prices."
            ),
            fields=[
                CommandField(
                    "symbol",
                    "Symbol",
                    "XAUUSD",
                    hint="platform name; the broker's alias is applied automatically",
                ),
                CommandField(
                    "timeframe",
                    "Timeframes",
                    "5M,1H,1D",
                    hint="comma separated — 5M feeds the signal model, 1H the range model",
                ),
                CommandField("bars", "Bars", "5000", kind="number"),
                CommandField(
                    "max_candles",
                    "Keep at most",
                    "100000",
                    kind="number",
                    hint="rolling limit — oldest candles are dropped",
                ),
                CommandField(
                    "allow_gap",
                    "Allow gap",
                    "0",
                    hint="1 = accept a discontinuity the broker could not fill",
                ),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.COMPUTE_FEATURES,
            label="Update features",
            description=(
                "Compute the standard feature set for EVERY listed timeframe, "
                "each stored separately. Stored features are REUSED until the "
                "candles change; updating the dataset forces a full recompute."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "timeframe",
                    "Timeframes",
                    "5M,1H,1D",
                    hint="comma separated — each one is computed and stored separately",
                ),
                CommandField(
                    "force",
                    "Force recompute",
                    "0",
                    hint="1 = recompute even when the candles have not changed",
                ),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.AUDIT_CAUSAL_FEATURES,
            label="Audit causal features",
            description=(
                "Report which standard features are allowed into model/live "
                "input and which are blocked for future leakage."
            ),
            fields=[],
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.AUDIT_CAUSAL_INVARIANCE,
            label="Run causality invariance test",
            description=(
                "Change only the future part of a stored candle series and "
                "prove that every causal feature and the causal model matrix "
                "keep the earlier prefix identical. Full-series PCA, Fourier, "
                "wavelet and centered-extrema features remain research-only."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "timeframe", "Timeframe", "5M", kind="select", options=("5M", "1H", "1D")
                ),
                CommandField(
                    "split_pct",
                    "Unchanged prefix %",
                    "70",
                    kind="number",
                    hint="future candles after this point are deliberately mutated",
                ),
                CommandField(
                    "max_bars",
                    "Audit at most",
                    "2000",
                    kind="number",
                    hint="limits runtime; use the full dataset only when needed",
                ),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_MODEL,
            label="Retrain a saved model",
            description=(
                "Continue training a model that already exists. Pick it from "
                "the list of saved models and choose which stored dataset to "
                "train it on. Retraining writes a NEW version — the previous "
                "one is kept so the two can be compared."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "saved_model",
                    "Saved model",
                    trained[0] if trained else "",
                    kind="select",
                    options=tuple(trained) if trained else ("(none trained yet)",),
                    hint="models found in datasets/models",
                ),
                CommandField(
                    "dataset",
                    "Dataset",
                    datasets[0] if datasets else "1H",
                    kind="select",
                    options=tuple(datasets),
                    hint="which stored candles to train on",
                ),
                CommandField(
                    "range_horizon",
                    "Range horizon (candles)",
                    "1",
                    kind="number",
                    hint=(
                        "چند کندل جلوتر — باید با مدل ذخیره‌شده یکی باشد. "
                        "1H: 12 یا 24 برای براکت معنادار"
                    ),
                ),
                CommandField(
                    "threshold_pct",
                    "Signal movement threshold %",
                    "",
                    kind="number",
                    hint="blank keeps the saved model threshold; binary labels have no HOLD class",
                ),
                CommandField(
                    "resume",
                    "Continue from checkpoint",
                    "1",
                    kind="select",
                    options=("1", "0"),
                    hint="1 = ادامه از آخرین checkpoint (پیشنهاد) | 0 = از صفر شروع",
                ),
                CommandField(
                    "epochs",
                    "Target epochs (total)",
                    "100",
                    kind="number",
                    hint="کل epoch هدف — مثلاً اگه 50 داری و میخوای 100 بشه، اینجا 100 بنویس",
                ),
                CommandField("folds", "Folds", "3", kind="number"),
                CommandField(
                    "es_patience",
                    "EarlyStopping patience",
                    "0",
                    kind="number",
                    hint="0 = auto (epochs/5) · بزرگ‌تر = ReduceLR فرصت کاهش LR",
                ),
                CommandField(
                    "rlr_patience",
                    "ReduceLR patience",
                    "0",
                    kind="number",
                    hint="0 = auto (epochs/10)",
                ),
                CommandField(
                    "window",
                    "Window rows",
                    "150",
                    kind="number",
                    hint="باید با مدل ذخیره‌شده یکی باشه (معمولاً 150)",
                ),
                CommandField(
                    "n_layers",
                    "WaveNet layers × block",
                    "0",
                    kind="number",
                    hint="0 = پیش‌فرض (signal 5, range 4) — RF باید < window",
                ),
                CommandField(
                    "n_blocks",
                    "WaveNet blocks",
                    "0",
                    kind="number",
                    hint="0 = پیش‌فرض (2) — مثال: 150+4×2 → RF=121 (81%)",
                ),
                CommandField(
                    "val_size",
                    "Validation samples per fold",
                    "0",
                    kind="number",
                    hint="0 = auto: ۱۰٪ استخر لیبل (فاز ۵۹)",
                ),
                CommandField(
                    "learning_rate",
                    "Learning rate (0 = auto)",
                    "0",
                    kind="number",
                    hint="0 = آخرین LR ذخیره‌شده | مقدار دستی مثلاً 0.0001",
                ),
                CommandField(
                    "train_ratio",
                    "Training prefix %",
                    "80",
                    kind="number",
                    hint="همون نسبتی که موقع آموزش اول استفاده شد (معمولاً 80)",
                ),
                CommandField(
                    "timeout_minutes",
                    "Give up after (minutes)",
                    "480",
                    kind="number",
                    hint="real training takes hours; each epoch is checkpointed",
                ),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_BACKTEST,
            label="Run a backtest",
            description=(
                "Replay the stored candles through the production trading "
                "chain and record the result."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Signal timeframe", "5M"),
                CommandField(
                    "mode",
                    "Engine",
                    "auto",
                    kind="select",
                    options=("auto", "dual", "legacy"),
                    hint="auto uses signal -> range -> TP/SL when both models and timeframes exist",
                ),
                CommandField(
                    "range_timeframe",
                    "Range timeframe",
                    "1D",
                    hint="1D = پیش‌بینی high/low فردا (horizon=1) — دقیق‌ترین",
                ),
                CommandField(
                    "signal_model",
                    "Signal model (id or id:vN)",
                    "",
                    hint="خالی = gold_signal_5m جدیدترین نسخه؛ نسخهٔ خاص: gold_signal_5m:v1",
                ),
                CommandField(
                    "range_model",
                    "Range model (id or id:vN)",
                    "",
                    hint=(
                        "خالی = gold_range_{tf} جدیدترین نسخه. فاز ۹۵: مدل ATR را "
                        "صریح انتخاب کن (مثلا gold_range_1d:v1) — نسخه‌های قدیمی "
                        "(pct) آفست ثابتِ درصدی می‌دهند"
                    ),
                ),
                CommandField("threshold_pct", "Signal probability %", "60", kind="number"),
                CommandField("signal_window", "Signal window (0 = model)", "0", kind="number"),
                CommandField("range_window", "Range window (0 = model)", "0", kind="number"),
                CommandField(
                    "reward_risk_multiplier",
                    "Reward/Risk multiplier",
                    "1.5",
                    kind="number",
                    hint=(
                        "TP must be at least this times SL distance "
                        "(e.g. 1.5 means TP >= 1.5x SL)"
                    ),
                ),
                CommandField(
                    "commission",
                    "Commission rate",
                    "0",
                    kind="number",
                    hint="0 = بدون کمیسیون | مثلاً 0.0001 = 0.01%",
                ),
                CommandField(
                    "filter_zero_bar",
                    "Filter 0-bar trades",
                    "0",
                    kind="select",
                    options=("0", "1"),
                    hint="1 = skip trades that open and close on the same bar",
                ),
                CommandField(
                    "test_ratio",
                    "Test holdout % (0 = all)",
                    "0",
                    kind="number",
                    hint="trade only the final percentage; train the model on the earlier prefix",
                ),
                CommandField("capital", "Capital", "100", kind="number"),
                CommandField("quantity", "Quantity", "0.01", kind="number"),
                CommandField(
                    "spread_mode",
                    "Spread type",
                    "pct",
                    kind="select",
                    options=("pct", "fixed"),
                    hint="pct = درصد از قیمت (مثل آلپاری) | fixed = دلار ثابت",
                ),
                CommandField(
                    "spread_value",
                    "Spread value",
                    "0.06",
                    kind="number",
                    hint="pct mode: 0.06 = 0.06% | fixed mode: 1.80 = $1.80",
                ),
                CommandField("slippage", "Slippage rate", "0", kind="number"),
                CommandField(
                    "same_bar_policy",
                    "If TP and SL share a candle",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "target_first", "skip_ambiguous"),
                ),
                CommandField(
                    "last_n_candles",
                    "Last N candles (0 = all)",
                    "0",
                    kind="number",
                    hint="0 = کل تاریخچه | مثلاً 10000 = فقط ۱۰۰۰۰ کندل آخر (تست سریع)",
                ),
                CommandField(
                    "session_filter",
                    "Session filter (hours UTC)",
                    "0",
                    kind="select",
                    options=("0", "1"),
                    hint="1 = فقط ساعت‌های خوب: 2,5,6,10,14,15,16,18 UTC (WR=45.7% بجای 33.5%)",
                ),
                CommandField(
                    "strategy",
                    "Strategy",
                    "triple",
                    kind="select",
                    options=("triple", "classic"),
                    hint=(
                        "triple = 5M سیگنال · 4H براکت TP/SL · 1D ترند (نیاز به "
                        "دیتاست 1D و 4H و مدل‌هاشون) | classic = تک مدل رنج"
                    ),
                ),
                CommandField(
                    "slope_mode",
                    "Slope mode (triple)",
                    "both",
                    kind="select",
                    options=("both", "either", "high", "low"),
                    hint="مجوز ۲: both = هر دو شیب | either = یکی کافی | high/low = فقط همان",
                ),
                CommandField(
                    "max_entry_distance_atr",
                    "Max entry distance (×daily ATR)",
                    "0.25",
                    kind="number",
                    hint=(
                        "مجوز ۴ (triple): ورود باید نزدیک سطح روزانه باشد — خرید "
                        "نزدیک Low پیش‌بینی D1، فروش نزدیک High. 0 = خاموش. "
                        "پیشنهاد از داده: 0.25 (~$10 در ATR=$40)"
                    ),
                ),
                CommandField(
                    "min_sl_distance",
                    "Min SL distance ($)",
                    "0",
                    kind="number",
                    hint="حداقل فاصله SL از entry (دلار). 0=غیرفعال. پیشنهاد: 3",
                ),
            ],
            group="Simulation",
        ),
        CommandDescriptor(
            kind=CommandKind.RECORD_REPLAY,
            label="Record a replay",
            description=(
                "Run the same backtest with recording on, then write a "
                "player you can watch bar by bar: where it entered, where "
                "it exited and what each trade produced. Opens at /replay."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Signal timeframe", "5M"),
                CommandField(
                    "mode",
                    "Engine",
                    "auto",
                    kind="select",
                    options=("auto", "dual", "legacy"),
                ),
                CommandField(
                    "use_last_settings",
                    "Use last backtest settings",
                    "1",
                    kind="select",
                    options=("1", "0"),
                    hint=(
                        "1 keeps Run a backtest and Record a replay identical; "
                        "0 uses this form's values"
                    ),
                ),
                CommandField(
                    "range_timeframe",
                    "Range timeframe",
                    "1D",
                    hint="1D = پیش‌بینی high/low فردا (horizon=1) — دقیق‌ترین",
                ),
                CommandField(
                    "signal_model",
                    "Signal model (id or id:vN)",
                    "",
                    hint="خالی = gold_signal_5m جدیدترین نسخه؛ نسخهٔ خاص: gold_signal_5m:v1",
                ),
                CommandField(
                    "range_model",
                    "Range model (id or id:vN)",
                    "",
                    hint=(
                        "خالی = gold_range_{tf} جدیدترین نسخه. فاز ۹۵: مدل ATR را "
                        "صریح انتخاب کن (مثلا gold_range_1d:v1) — نسخه‌های قدیمی "
                        "(pct) آفست ثابتِ درصدی می‌دهند"
                    ),
                ),
                CommandField("threshold_pct", "Signal probability %", "60", kind="number"),
                CommandField("signal_window", "Signal window (0 = model)", "0", kind="number"),
                CommandField("range_window", "Range window (0 = model)", "0", kind="number"),
                CommandField(
                    "reward_risk_multiplier",
                    "Reward/Risk multiplier",
                    "1.5",
                    kind="number",
                    hint=(
                        "TP must be at least this times SL distance "
                        "(e.g. 1.5 means TP >= 1.5x SL)"
                    ),
                ),
                CommandField(
                    "commission",
                    "Commission rate",
                    "0",
                    kind="number",
                    hint="0 = بدون کمیسیون | مثلاً 0.0001 = 0.01%",
                ),
                CommandField(
                    "filter_zero_bar",
                    "Filter 0-bar trades",
                    "0",
                    kind="select",
                    options=("0", "1"),
                    hint="1 = skip trades that open and close on the same bar",
                ),
                CommandField(
                    "test_ratio",
                    "Test holdout % (0 = all)",
                    "0",
                    kind="number",
                    hint="trade only the final percentage; train the model on the earlier prefix",
                ),
                CommandField("capital", "Capital", "100", kind="number"),
                CommandField("quantity", "Quantity", "0.01", kind="number"),
                CommandField(
                    "spread_mode",
                    "Spread type",
                    "pct",
                    kind="select",
                    options=("pct", "fixed"),
                    hint="pct = درصد از قیمت (مثل آلپاری) | fixed = دلار ثابت",
                ),
                CommandField(
                    "spread_value",
                    "Spread value",
                    "0.06",
                    kind="number",
                    hint="pct mode: 0.06 = 0.06% | fixed mode: 1.80 = $1.80",
                ),
                CommandField("slippage", "Slippage rate", "0", kind="number"),
                CommandField(
                    "same_bar_policy",
                    "If TP and SL share a candle",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "target_first", "skip_ambiguous"),
                ),
                CommandField(
                    "last_n_candles",
                    "Last N candles (0 = all)",
                    "0",
                    kind="number",
                    hint="0 = کل تاریخچه | مثلاً 10000 = فقط ۱۰۰۰۰ کندل آخر (تست سریع)",
                ),
                CommandField(
                    "session_filter",
                    "Session filter (hours UTC)",
                    "0",
                    kind="select",
                    options=("0", "1"),
                    hint="1 = فقط ساعت‌های خوب: 2,5,6,10,14,15,16,18 UTC",
                ),
                CommandField(
                    "trend_filter",
                    "Daily trend filter",
                    "none",
                    kind="select",
                    options=("none", "ema50"),
                    hint=(
                        "ema50 = SHORT ممنوع وقتی قیمت بالای EMA50 روزانه و LONG "
                        "ممنوع وقتی زیر آن (ضد ترند-شکنی)"
                    ),
                ),
                CommandField(
                    "strategy",
                    "Strategy",
                    "triple",
                    kind="select",
                    options=("triple", "classic"),
                    hint=(
                        "triple = 5M سیگنال · 4H براکت TP/SL · 1D ترند (نیاز به "
                        "دیتاست 1D و 4H و مدل‌هاشون) | classic = تک مدل رنج"
                    ),
                ),
                CommandField(
                    "slope_mode",
                    "Slope mode (triple)",
                    "both",
                    kind="select",
                    options=("both", "either", "high", "low"),
                    hint="مجوز ۲: both = هر دو شیب | either = یکی کافی | high/low = فقط همان",
                ),
                CommandField(
                    "max_entry_distance_atr",
                    "Max entry distance (×daily ATR)",
                    "0.25",
                    kind="number",
                    hint=(
                        "مجوز ۴ (triple): ورود باید نزدیک سطح روزانه باشد — خرید "
                        "نزدیک Low پیش‌بینی D1، فروش نزدیک High. 0 = خاموش. "
                        "پیشنهاد از داده: 0.25 (~$10 در ATR=$40)"
                    ),
                ),
                CommandField(
                    "min_sl_distance",
                    "Min SL distance ($)",
                    "0",
                    kind="number",
                    hint="حداقل فاصله SL از entry. 0=غیرفعال. پیشنهاد: 3",
                ),
            ],
            group="Simulation",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_OPTIMISATION,
            label="Run optimisation",
            description=(
                "Search strategy parameters in-sample, validate the leaders "
                "on unseen folds, and remember the outcome."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("folds", "Validation folds", "3", kind="number"),
            ],
            slow=True,
            group="Simulation",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_TRADING_CYCLE,
            label="Run a trading cycle",
            description=(
                "Evaluate the strategy once against the latest stored candle "
                "and persist the decision, execution and position."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("timeframe", "Timeframe", "5M"),
                CommandField("session", "Session", "dashboard"),
            ],
            group="Trading",
        ),
        CommandDescriptor(
            kind=CommandKind.REFRESH_PROJECT_STATE,
            label="Refresh project state",
            description="Rescan the repository and regenerate the project snapshot.",
            group="Operations",
        ),
        # -- accounts (Phase 32) -----------------------------------------
        CommandDescriptor(
            kind=CommandKind.ADD_ACCOUNT,
            label="Add account",
            description=(
                "Register a MetaTrader 5 account. The password is NOT stored: "
                "set it in the environment variable shown after saving."
            ),
            fields=[
                CommandField("name", "Profile name", "alpari-demo"),
                CommandField("login", "Login", "", kind="number"),
                CommandField("server", "Server", "Alpari-MT5-Demo"),
                CommandField("terminal_path", "Terminal path", "", hint="optional"),
                CommandField("is_demo", "Demo account", "1", hint="1 = demo, 0 = live"),
            ],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.ACTIVATE_ACCOUNT,
            label="Switch account",
            description="Make a profile the active one; every run then uses it.",
            fields=[CommandField("name", "Profile name", "")],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.CHECK_ACCOUNT,
            label="Check account",
            description=(
                "Connect to the broker and confirm every mapped symbol exists. "
                "Leave the name empty to check the active profile."
            ),
            fields=[CommandField("name", "Profile name", "")],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.MAP_SYMBOL,
            label="Map a symbol",
            description=(
                "Tell this profile what its broker calls an instrument, "
                "e.g. XAUUSD -> XAUUSD_i. Datasets keep the canonical name."
            ),
            fields=[
                CommandField("name", "Profile name", ""),
                CommandField("canonical", "Platform symbol", "XAUUSD"),
                CommandField("broker", "Broker symbol", "XAUUSD_i"),
            ],
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.AUTO_MAP_SYMBOLS,
            label="Detect symbol names",
            description=(
                "Ask the broker what it calls each instrument and suggest a "
                "mapping. Suggestions are applied only when you confirm."
            ),
            fields=[
                CommandField("name", "Profile name", ""),
                CommandField("symbols", "Symbols", "XAUUSD,EURUSD,GBPUSD"),
                CommandField("apply", "Apply suggestions", "0", hint="1 = save them"),
            ],
            slow=True,
            group="Accounts",
        ),
        CommandDescriptor(
            kind=CommandKind.REMOVE_ACCOUNT,
            label="Remove account",
            description="Delete a profile. The broker account itself is untouched.",
            fields=[CommandField("name", "Profile name", "")],
            danger=True,
            group="Accounts",
        ),
        # -- data ----------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.BUILD_DATASET,
            label="Build training dataset",
            description=(
                "Build TWO separate datasets from the stored real candles: "
                "5M for the signal model and 1H for the range model. Each "
                "gets its own matrix of 123 columns. Real data only — "
                "'Fetch market data' must have run for both timeframes."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("candles", "Candles per timeframe", "100000", kind="number"),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.EVALUATE_MODEL,
            label="Test a model on a dataset",
            description=(
                "Score a saved model against a stored dataset without "
                "training it. Every result is appended to "
                "run_logs/evaluations.jsonl so runs can be compared."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "saved_model",
                    "Model",
                    trained[0] if trained else "",
                    kind="select",
                    options=tuple(trained) if trained else ("(none trained yet)",),
                ),
                CommandField(
                    "dataset",
                    "Dataset",
                    datasets[0] if datasets else "1H",
                    kind="select",
                    options=tuple(datasets),
                    hint="which stored candles to score against",
                ),
                CommandField(
                    "max_windows",
                    "Sample at most",
                    "5000",
                    kind="number",
                    hint="0 = every window (slow on 49,000)",
                ),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.INSPECT_DATASET,
            label="Inspect a dataset",
            description=(
                "Show what a stored dataset actually is: how many candles, "
                "the matrix shape, the column breakdown and the model input "
                "tensor it produces."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    datasets[0] if datasets else "1H",
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("window", "Window rows", "500", kind="number"),
            ],
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.BUILD_TIMEFRAME,
            label="Build a higher timeframe",
            description=(
                "Aggregate stored candles into a larger timeframe, e.g. 1H "
                "into 1D. Use this when the broker gave you hours of history "
                "but you want to train a daily model. Incomplete buckets are "
                "dropped, never half-filled."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("source", "From", "1H"),
                CommandField("target", "To", "1D"),
            ],
            slow=True,
            group="Data",
        ),
        CommandDescriptor(
            kind=CommandKind.WEEKLY_UPDATE,
            label="Weekly update",
            description=(
                "Back up, refresh the dataset (full feature recompute) and "
                "prepare the models for continued training."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField("candles", "Candles", "100000", kind="number"),
                CommandField("force", "Ignore the 7-day gate", "0"),
            ],
            slow=True,
            group="Data",
        ),
        # -- AI --------------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.TRAIN_DUAL_MODELS,
            label="Train a model",
            description=(
                "Train one model on one dataset. Pick the kind of model — "
                "'range' predicts the future high and low, 'signal' predicts "
                "binary buy/sell — and the stored dataset it learns from. The "
                "saved model records both, so it can be found again."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "model",
                    "Model type",
                    "range",
                    kind="select",
                    options=tuple(MODEL_ROLE_CHOICES),
                    hint="range = future high/low · signal = binary buy/sell",
                ),
                CommandField(
                    "dataset",
                    "Dataset",
                    datasets[0] if datasets else "1H",
                    kind="select",
                    options=tuple(datasets),
                    hint="which stored candles to train on",
                ),
                CommandField(
                    "range_horizon",
                    "Range horizon (candles)",
                    "1",
                    kind="number",
                    hint=(
                        "چند کندل جلوتر — فقط برای range. "
                        "1H: 12 (نیم‌روز) یا 24 (یک روز) برای براکت معنادار"
                    ),
                ),
                CommandField(
                    "threshold_pct",
                    "Signal movement threshold %",
                    "0.08",
                    kind="number",
                    hint="first future +/- threshold hit creates BUY/SELL; no HOLD class",
                ),
                CommandField(
                    "epochs",
                    "Epochs",
                    "50",
                    kind="number",
                    hint="range 1D: 50 مناسبه | signal 5M: 30",
                ),
                CommandField("folds", "Folds", "3", kind="number"),
                CommandField(
                    "es_patience",
                    "EarlyStopping patience",
                    "0",
                    kind="number",
                    hint="0 = auto (epochs/5) · بزرگ‌تر = ReduceLR فرصت کاهش LR قبل قطع",
                ),
                CommandField(
                    "rlr_patience",
                    "ReduceLR patience",
                    "0",
                    kind="number",
                    hint="0 = auto (epochs/10) · مثلاً 8-12 برای کاهش چندپله LR",
                ),
                CommandField(
                    "window",
                    "Window rows",
                    "150",
                    kind="number",
                    hint="150 = 7 ماه برای 1D | 150 = 12.5 ساعت برای 5M",
                ),
                CommandField(
                    "n_layers",
                    "WaveNet layers × block",
                    "0",
                    kind="number",
                    hint="0 = پیش‌فرض (signal 5, range 4) · RF باید < window — 150 با 4 هماهنگه",
                ),
                CommandField(
                    "n_blocks",
                    "WaveNet blocks",
                    "0",
                    kind="number",
                    hint="0 = پیش‌فرض (2) — مثال: 150+4×2 → RF=121 (81%)",
                ),
                CommandField(
                    "val_size",
                    "Validation samples per fold",
                    "0",
                    kind="number",
                    hint="0 = auto: ۱۰٪ استخر لیبل (فاز ۵۹) — قبلاً ۲٪ بود و کم می‌شد",
                ),
                CommandField(
                    "learning_rate",
                    "Learning rate (0 = auto)",
                    "0",
                    kind="number",
                    hint="0 = آخرین LR ذخیره‌شده | range: 1e-4 | signal: 1e-4",
                ),
                CommandField(
                    "train_ratio",
                    "Training prefix %",
                    "80",
                    kind="number",
                    hint="80 = 80% train, 20% validation — پیشنهاد",
                ),
                CommandField(
                    "timeout_minutes",
                    "Give up after (minutes)",
                    "480",
                    kind="number",
                    hint="real training takes hours; each epoch is checkpointed",
                ),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.OPTIMISE_LEARNING_RATE,
            label="Find best learning rate",
            description=(
                "Run a short walk-forward sweep for several learning rates "
                "separately on the Signal or Range model, select the lowest "
                "validation score, then train and save the final model with it."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "model",
                    "Model type",
                    "signal",
                    kind="select",
                    options=("signal", "range", "trend"),
                    hint="trend = رنگ کندل بعدی (سبز/قرمز) — دیتاست: هر TF (پیشنهاد: 1D یا 4H)",
                ),
                CommandField(
                    "dataset",
                    "Dataset",
                    datasets[0] if datasets else "5M",
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField(
                    "learning_rates",
                    "Candidates",
                    "1e-5,3e-5,1e-4,3e-4,1e-3",
                    hint="comma-separated values; lower val_loss/val_mae wins",
                ),
                CommandField("threshold_pct", "Signal movement threshold %", "0.08", kind="number"),
                CommandField("window", "Window rows", "100", kind="number"),
                CommandField(
                    "n_layers",
                    "WaveNet layers \u00d7 block",
                    "0",
                    kind="number",
                    hint="0 = \u067e\u06cc\u0634\u200c\u0641\u0631\u0636 (signal 5, range 4)",
                ),
                CommandField(
                    "n_blocks",
                    "WaveNet blocks",
                    "0",
                    kind="number",
                    hint="0 = \u067e\u06cc\u0634\u200c\u0641\u0631\u0636 (2)",
                ),
                CommandField("train_ratio", "Training prefix %", "100", kind="number"),
                CommandField("pilot_epochs", "Pilot epochs", "1", kind="number"),
                CommandField("pilot_folds", "Pilot folds", "1", kind="number"),
                CommandField("final_epochs", "Final epochs", "3", kind="number"),
                CommandField("final_folds", "Final folds", "2", kind="number"),
                CommandField(
                    "timeout_minutes",
                    "Give up after (minutes)",
                    "480",
                    kind="number",
                ),
            ],
            slow=True,
            group="AI",
        ),
        # -- trading ---------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.RUN_EXECUTION_DEMO,
            label="Run execution demo",
            description="Drive one intent through resolver, venue and ledger.",
            fields=[CommandField("symbol", "Symbol", "XAUUSD")],
            group="Trading",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_LIVE_TICK,
            label="Run one live tick",
            description=(
                "One five-minute cycle: buffers, both models, strategy, risk " "gate and execution."
            ),
            fields=[CommandField("symbol", "Symbol", "XAUUSD")],
            slow=True,
            group="Trading",
        ),
        # -- operations --------------------------------------------------------
        CommandDescriptor(
            kind=CommandKind.BACKUP_DATABASE,
            label="Back up the database",
            description="Take a backup and verify it can be read back.",
            fields=[CommandField("note", "Note", "manual backup")],
            group="Operations",
        ),
        CommandDescriptor(
            kind=CommandKind.HEALTH_CHECK,
            label="Health check",
            description="Liveness, readiness and every dependency.",
            group="Operations",
        ),
    ]


def descriptor_for(kind: CommandKind) -> CommandDescriptor:
    for descriptor in descriptors():
        if descriptor.kind is kind:
            return descriptor
    raise KeyError(kind)


# ---------------------------------------------------------------- handlers --
#: فاز ۶۷ — برچسب build برای گزارش بکتست؛ اپراتور با یک نگاه می‌بیند
#: با کدِ چندم اجرا می‌کند (کد قدیمی = گزارش قدیمی = گمراهی).
ENGINE_BUILD = "phase-67 (bug49+50 fixed: range prefill + signal points)"


class CommandHandlers:
    """Binds commands to the application services that do the work."""

    def __init__(
        self,
        database_path: str | Path,
        storage_root: str | Path = "datasets",
        replay_path: str | Path = "replay.html",
        account_store: str | Path = "configs/accounts.json",
    ):
        self._database_path = Path(database_path)
        self._storage_root = Path(storage_root)
        self._account_store = Path(account_store)
        # Where "Record a replay" writes its player. The server serves this
        # file at /replay, so the two must agree on one location.
        self._replay_path = Path(replay_path)
        self._run_log_dir = RUN_LOG_DIR
        # The replay button re-runs the most recent backtest settings by
        # default, so its numbers cannot differ merely because the user
        # opened a second form with fresh defaults.
        self._last_backtest_parameters: Optional[Dict[str, Any]] = None
        self._last_backtest_replay_ready = False
        self._last_backtest_summary: Dict[str, Any] = {}

    @property
    def replay_path(self) -> Path:
        return self._replay_path

    def run_log_path(self, action: str) -> Path:
        """Where this handler streams a script's output while it runs."""
        return run_log_path(action, self._run_log_dir)

    def _run_script(
        self,
        command: Command,
        arguments: List[str],
        success_message: str,
        started: float,
        timeout: int = 900,
    ) -> CommandResult:
        """Run a project script, streaming its output to a live log.

        Scripts run in a subprocess so a crash inside one cannot take the
        dashboard down with it, and so a long run can be time-limited.

        Phase 36: the output is read line by line and appended to
        ``run_logs/{command}.log`` **as it arrives**, instead of being
        collected by ``subprocess.run`` and revealed only at the end. A
        twenty-minute training run that prints nothing until it finishes
        is indistinguishable from one that has hung, and the operator has
        no way to tell whether the loss is falling.

        Two details make the stream actually live:

        * ``PYTHONUNBUFFERED=1`` — otherwise Python buffers 8 KB of stdout
          when the far end is a pipe rather than a terminal, so the log
          would arrive in bursts long after the epoch produced it.
        * ``bufsize=1`` with ``text=True`` — line buffering on our side.
        """
        import os
        import subprocess
        import sys

        log_path = self.run_log_path(command.kind.value)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        environment = dict(os.environ)
        environment["PYTHONUNBUFFERED"] = "1"

        tail: List[str] = []
        deadline = time.monotonic() + timeout

        try:
            with log_path.open("w", encoding="utf-8", errors="replace") as log:
                log.write(f"$ {' '.join(arguments)}\n")
                log.flush()

                process = subprocess.Popen(
                    [sys.executable, *arguments],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(Path.cwd()),
                    env=environment,
                )

                assert process.stdout is not None
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    stripped = line.rstrip("\n")
                    if stripped.strip():
                        tail.append(stripped)
                        if len(tail) > 400:
                            del tail[:200]
                    if time.monotonic() > deadline:
                        process.kill()
                        log.write("\n[killed: timeout]\n")
                        return CommandResult.failure(
                            command.kind,
                            f"Timed out after {timeout // 60} minutes "
                            f"(any completed epoch was checkpointed)",
                            "\n".join(tail[-25:]) + "\n\nReduce the size of the run, or start it "
                            "from a terminal.",
                            time.monotonic() - started,
                        )

                returncode = process.wait()
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not start the script",
                str(error),
                time.monotonic() - started,
            )

        if returncode != 0:
            return CommandResult.failure(
                command.kind,
                "The script reported a failure",
                ("\n".join(tail[-25:]))[-1500:],
                time.monotonic() - started,
            )

        interesting = [line for line in tail if not line.startswith("=")]
        return CommandResult.success(
            command.kind, success_message, interesting[-25:], time.monotonic() - started
        )

    def registry(self) -> Dict[CommandKind, Handler]:
        registry: Dict[CommandKind, Handler] = {
            CommandKind.FETCH_MARKET_DATA: self.fetch_market_data,
            CommandKind.COMPUTE_FEATURES: self.compute_features,
            CommandKind.AUDIT_CAUSAL_FEATURES: self.audit_causal_features,
            CommandKind.AUDIT_CAUSAL_INVARIANCE: self.audit_causal_invariance,
            CommandKind.TRAIN_MODEL: self.train_model,
            CommandKind.RUN_BACKTEST: self.run_backtest,
            CommandKind.RECORD_REPLAY: self.record_replay,
            CommandKind.RUN_OPTIMISATION: self.run_optimisation,
            CommandKind.RUN_TRADING_CYCLE: self.run_trading_cycle,
            CommandKind.REFRESH_PROJECT_STATE: self.refresh_project_state,
        }
        # Phase 32 handlers live in their own class; merged here so the
        # bus still sees a single flat registry.
        accounts = AccountCommandHandlers(
            self._database_path, self._storage_root, self._account_store
        )
        registry.update(
            {
                CommandKind.ADD_ACCOUNT: accounts.add_account,
                CommandKind.ACTIVATE_ACCOUNT: accounts.activate_account,
                CommandKind.REMOVE_ACCOUNT: accounts.remove_account,
                CommandKind.CHECK_ACCOUNT: accounts.check_account,
                CommandKind.MAP_SYMBOL: accounts.map_symbol,
                CommandKind.AUTO_MAP_SYMBOLS: accounts.auto_map_symbols,
                CommandKind.BUILD_DATASET: accounts.build_dataset,
                CommandKind.WEEKLY_UPDATE: accounts.weekly_update,
                CommandKind.BUILD_TIMEFRAME: accounts.build_timeframe,
                CommandKind.EVALUATE_MODEL: accounts.evaluate_model,
                CommandKind.INSPECT_DATASET: accounts.inspect_dataset,
                CommandKind.TRAIN_DUAL_MODELS: accounts.train_dual_models,
                CommandKind.OPTIMISE_LEARNING_RATE: accounts.optimise_learning_rate,
                CommandKind.RUN_EXECUTION_DEMO: accounts.run_execution_demo,
                CommandKind.RUN_LIVE_TICK: accounts.run_live_tick,
                CommandKind.BACKUP_DATABASE: accounts.backup_database,
                CommandKind.HEALTH_CHECK: accounts.health_check,
            }
        )
        return registry

    # -- data ---------------------------------------------------------------
    def active_profile(self):
        """The active broker profile, or None when none is configured.

        Returned rather than raised: every run must still work on sample
        data before a broker is set up.
        """
        from ShadBotTrader.infrastructure.account import AccountProfileStore

        try:
            return AccountProfileStore(self._account_store).active()
        except Exception:
            return None

    def broker_symbol(self, canonical: str) -> tuple[str, str]:
        """Translate a platform symbol for the active broker.

        Returns ``(broker_symbol, note)``. The dataset keeps the canonical
        name so that switching brokers does not fragment history into
        XAUUSD / XAUUSD_i / GOLD copies of the same instrument.
        """
        profile = self.active_profile()
        if profile is None:
            return canonical, ""
        translated = profile.broker_symbol(canonical)
        if translated == canonical:
            return translated, f"account: {profile.name}"
        return translated, f"account: {profile.name} ({canonical} -> {translated})"

    def fetch_market_data(self, command: Command) -> CommandResult:
        """Download real candles for every requested timeframe.

        Phase 35 changed two things the operator kept tripping over:

        * ``timeframe`` accepts a list (``5M,1H``) and each one is
          fetched in the same run, because the training dataset needs
          both and fetching one silently left the other empty.
        * candles are stored under the **canonical** symbol even though
          they are fetched under the broker's spelling, so ``XAUUSD`` and
          ``XAUUSD_i`` stop being two disconnected datasets.
        """
        from ShadBotTrader.application.services.dataset_update_service import (
            DatasetUpdateService,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        timeframes = parse_timeframes(command.text("timeframe", "5M,1H,1D"))
        bars = max(command.integer("bars", 5000), 1)
        allow_gap = command.text("allow_gap", "0").strip() == "1"
        max_candles = max(command.integer("max_candles", 100_000), 1000)

        if not timeframes:
            return CommandResult.rejected(
                command.kind, "No timeframe given. Use for example: 5M,1H"
            )

        if not mt5mod.is_available():
            # Phase 35: no synthetic fallback. Silently ingesting a sine
            # wave under a real symbol is how a model ends up trained on
            # fiction that nobody can tell apart from market data.
            return CommandResult.rejected(
                command.kind,
                "MetaTrader 5 is not available, and this platform no longer "
                "substitutes generated candles for real ones. Run the "
                "dashboard on Windows with the MT5 terminal open and an "
                "account configured under 'Accounts'.",
            )

        broker_symbol, account_note = self.broker_symbol(symbol)
        profile = self.active_profile()
        if profile is not None:
            provider = mt5mod.Mt5MarketDataProvider(
                login=profile.login,
                password=profile.resolve_password(),
                server=profile.server,
                terminal_path=profile.terminal_path or None,
            )
        else:
            provider = mt5mod.Mt5MarketDataProvider()

        lines: List[str] = [
            "source: MetaTrader 5 (real broker data)",
            account_note or "account: terminal session",
            f"fetched as    : {broker_symbol}",
            f"stored as     : {symbol} (canonical)",
        ]
        headline: List[str] = []
        refused: List[str] = []

        try:
            _, store, _ = build_service(self._storage_root, provider=provider)
            updater = DatasetUpdateService(store, provider=provider, max_candles=max_candles)
            for timeframe in timeframes:
                lines.append("")
                lines.append(f"--- {timeframe} ---")
                try:
                    update = updater.fetch_and_update(
                        broker_symbol,
                        timeframe,
                        bars=bars,
                        allow_gap=allow_gap,
                        store_as=symbol,
                    )
                except Exception as error:
                    refused.append(timeframe)
                    lines.append(f"FAILED: {type(error).__name__}: {error}")
                    continue

                lines.extend(update.summary_lines())
                if update.refused:
                    refused.append(timeframe)
                else:
                    headline.append(
                        f"{timeframe} +{update.added_count:,} " f"({update.final_count:,} stored)"
                    )
        finally:
            provider.shutdown()

        lines.append("")
        lines.append("See the candles: open /data")

        if refused:
            lines.append("")
            lines.append(
                "A refused timeframe left its stored dataset untouched. "
                "Re-run when the broker can supply the missing range, or "
                "tick 'Allow gap' to accept the discontinuity deliberately."
            )
            return CommandResult.failure(
                command.kind,
                f"{symbol}: {len(refused)} of {len(timeframes)} timeframe(s) "
                f"refused ({', '.join(refused)})",
                "\n".join(lines),
                time.monotonic() - started,
            )

        return CommandResult.success(
            command.kind,
            f"{symbol}: " + " | ".join(headline),
            lines,
            time.monotonic() - started,
        )

    # -- features ------------------------------------------------------------
    def audit_causal_features(self, command: Command) -> CommandResult:
        """Run the fail-closed Stage 1 feature causality audit."""
        from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
        from ShadBotTrader.infrastructure.feature.causality_audit import audit_feature_set
        from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

        started = time.monotonic()
        report = audit_feature_set(standard_feature_set(), CalculatorRegistry())
        lines = [
            f"catalog features : {len(report.rows)}",
            f"allowed model    : {len(report.allowed)}",
            f"excluded         : {len(report.excluded)}",
            "",
            "EXCLUDED FEATURES:",
            *[f"  {feature}: {reason}" for feature, reason in report.excluded.items()],
        ]
        return CommandResult.success(
            command.kind,
            f"Causality audit complete: {len(report.excluded)} feature(s) blocked",
            lines,
            time.monotonic() - started,
        )

    def audit_causal_invariance(self, command: Command) -> CommandResult:
        """Run the runtime unchanged-prefix causality proof on stored data."""
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
        from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol
        from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
        from ShadBotTrader.infrastructure.feature.invariance_audit import (
            audit_feature_set_invariance,
            audit_matrix_invariance,
        )
        from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1

        started = time.monotonic()
        symbol_text = command.text("symbol", "XAUUSD").strip().upper()
        timeframe_text = command.text("timeframe", "5M").strip().upper()
        split_pct = command.number("split_pct", 70.0)
        max_bars = max(120, min(command.integer("max_bars", 2000), 5000))
        if not 1.0 < split_pct < 100.0:
            return CommandResult.rejected(command.kind, "split_pct must be between 1 and 100")

        _, store, _ = build_service(self._storage_root)
        resolved = resolve_stored_symbol(store, symbol_text, timeframe_text)
        if not resolved.found:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol_text} {timeframe_text}. Fetch market data first.",
            )
        all_candles = store.query(Symbol(resolved.resolved), Timeframe(timeframe_text))
        candles = list(all_candles[-max_bars:])
        if len(candles) < 120:
            return CommandResult.rejected(
                command.kind,
                f"Need at least 120 candles for the audit; found {len(candles)}.",
            )
        split_index = max(1, min(len(candles) - 1, int(len(candles) * split_pct / 100.0)))
        feature_set = standard_feature_set_v1()
        resolver = CalculatorRegistry()
        symbol = Symbol(symbol_text)
        timeframe = Timeframe(timeframe_text)

        feature_report = audit_feature_set_invariance(
            feature_set,
            resolver,
            candles,
            symbol,
            timeframe,
            split_index=split_index,
        )

        def build(values):
            return build_feature_matrix(
                values,
                symbol,
                timeframe,
                feature_set=feature_set,
                resolver=resolver,
                include_features=True,
                causal_only=True,
            )

        matrix_report = audit_matrix_invariance(build, candles, split_index=split_index)
        result_label = "PASS" if feature_report.is_clean and matrix_report.passed else "FAIL"
        lines = [
            f"candles checked   : {len(candles):,} ({symbol_text} {timeframe_text})",
            f"unchanged prefix  : {split_index:,} rows ({split_pct:.1f}%)",
            f"catalog            : {len(feature_set.definitions)} definitions",
            f"runtime definitions: {len(feature_report.rows) - len(feature_report.errors)} checked",
            f"declared causal   : {sum(row.declared_causal for row in feature_report.rows)}",
            f"causal failures   : {len(feature_report.causal_failures)}",
            f"matrix prefix     : {matrix_report.compared_rows:,} rows",
            f"matrix invariant  : {'PASS' if matrix_report.passed else 'FAIL'}",
            "",
            f"RESULT             : {result_label}",
        ]
        if feature_report.causal_failures:
            lines.extend(
                [
                    "",
                    "CAUSAL FAILURES:",
                    *[
                        f"  {row.feature_id}: {row.error or f'changed at {row.first_difference}'}"
                        for row in feature_report.causal_failures
                    ],
                ]
            )
        if not matrix_report.passed:
            lines.append(f"  matrix: {matrix_report.error or matrix_report.first_difference}")

        clean = feature_report.is_clean and matrix_report.passed
        if clean:
            return CommandResult.success(
                command.kind,
                "Causality invariance PASS: causal features and model matrix are prefix-stable",
                lines,
                time.monotonic() - started,
            )
        return CommandResult.failure(
            command.kind,
            "Causality invariance FAILED: future mutation changed production input",
            "\\n".join(lines),
            time.monotonic() - started,
        )

    def compute_features(self, command: Command) -> CommandResult:
        """Compute the feature catalogue for every requested timeframe.

        Phase 37 changed three things:

        * ``timeframe`` accepts a list and defaults to ``5M,1H``, because
          the two models train on two different timeframes and computing
          only one silently left the other stale.
        * each timeframe is stored under its own directory, so 5M and 1H
          copies of ``atr_14`` no longer land in the same folder as two
          indistinguishable versions.
        * progress is streamed to the run log while it happens: 109
          features over 100k candles takes minutes and used to print
          nothing at all.
        """
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.feature_cli import _build_service as build_feature_service
        from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol
        from ShadBotTrader.infrastructure.feature.feature_progress import (
            ConsoleFeatureProgress,
        )
        from ShadBotTrader.infrastructure.feature.standard_catalog import (
            standard_feature_set_v1,
        )
        from ShadBotTrader.infrastructure.persistence import (
            Database,
            SqliteFeatureRegistry,
        )

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        timeframes = parse_timeframes(command.text("timeframe", "5M,1H,1D"))
        force = command.text("force", "0").strip() == "1"
        if not timeframes:
            return CommandResult.rejected(
                command.kind, "No timeframe given. Use for example: 5M,1H"
            )

        _, store, _ = build_service(self._storage_root)
        feature_set = standard_feature_set_v1()

        log_path = self.run_log_path(command.kind.value)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = [f"feature set : {feature_set.name}"]
        failed: List[str] = []

        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            reporter = ConsoleFeatureProgress(stream=log)

            for timeframe in timeframes:
                resolved = resolve_stored_symbol(store, symbol, timeframe)
                if not resolved.found:
                    message = (
                        f"{timeframe}: no stored candles for {symbol}. "
                        f"Run 'Fetch market data' first."
                    )
                    log.write(f"\n[X] {message}\n")
                    log.flush()
                    lines.append(f"{timeframe}: SKIPPED — no candles")
                    failed.append(timeframe)
                    continue

                candles = store.query(Symbol(resolved.resolved), Timeframe(timeframe))
                try:
                    service, _, _ = build_feature_service(self._storage_root)
                    service._progress = reporter
                    outcome = service.compute_set(
                        feature_set=feature_set,
                        symbol=Symbol(symbol),
                        timeframe=Timeframe(timeframe),
                        candles=candles,
                        source_dataset_id=(f"csv.market_candle.{symbol}.{timeframe}.L3_normalized"),
                        dataset_version=1,
                        force=force,
                    )
                except Exception as error:
                    log.write(f"\n[X] {timeframe}: {type(error).__name__}: {error}\n")
                    log.flush()
                    lines.append(f"{timeframe}: FAILED — {error}")
                    failed.append(timeframe)
                    continue

                quarantined = sum(1 for item in outcome.outcomes if item.quarantined)
                research = sum(1 for item in outcome.outcomes if not item.live_compatible)
                if outcome.from_cache:
                    # Phase 38: unchanged candles mean the stored values
                    # are still correct, so nothing was recomputed.
                    lines.append(
                        f"{timeframe}: {outcome.reused_count} feature(s) REUSED "
                        f"from the store — the dataset has not changed"
                    )
                else:
                    lines.append(
                        f"{timeframe}: {len(outcome.outcomes) - quarantined}/"
                        f"{len(outcome.outcomes)} recomputed over "
                        f"{len(candles):,} candles "
                        f"({quarantined} quarantined, {research} research-only)"
                    )

        # Record the catalogue in the database so the dashboard can show it.
        database = Database(self._database_path)
        registry = SqliteFeatureRegistry(database)
        for definition in feature_set.definitions:
            registry.register(definition)
        database.close()

        lines.append("")
        lines.append(f"{len(feature_set.definitions)} definitions registered in the database")
        lines.append("Each timeframe is stored separately: features/{symbol}/{timeframe}/")
        lines.append("Inspect them: open /data")

        if failed:
            return CommandResult.failure(
                command.kind,
                f"{symbol}: {len(failed)} of {len(timeframes)} timeframe(s) failed "
                f"({', '.join(failed)})",
                "\n".join(lines),
                time.monotonic() - started,
            )

        return CommandResult.success(
            command.kind,
            f"{symbol}: features computed for {', '.join(timeframes)}",
            lines,
            time.monotonic() - started,
        )

    # -- AI --------------------------------------------------------------------
    def train_model(self, command: Command) -> CommandResult:
        """Retrain a model that already exists (Phase 40).

        This button used to run ``run_ai.py --quick``, an unrelated demo
        that trained a throwaway classifier and saved nothing. It now
        retrains a model the operator picks from the list of saved ones,
        on the dataset they pick, and writes a NEW version so the old
        weights survive for comparison.
        """
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        started = time.monotonic()
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            return CommandResult.rejected(
                command.kind,
                "TensorFlow is not installed — run: pip install -r requirements-ai.txt",
            )

        catalogue = ModelCatalogue(self._storage_root)
        saved = command.text("saved_model", "").strip()
        known = catalogue.choices()

        if not known:
            return CommandResult.rejected(
                command.kind,
                "No trained models yet. Use 'Train a model' first — retraining "
                "needs something to retrain.",
            )
        if saved in ("", "(none trained yet)"):
            saved = known[0]
        if saved not in known:
            return CommandResult.rejected(
                command.kind,
                f"Unknown model {saved!r}. Available: {', '.join(known)}",
            )

        record = catalogue.read(saved, catalogue.latest_version(saved))
        if record is not None and record.model_id.startswith("gold_trend_"):
            # فاز ۹۸: مدل ترند — نقش بازسازی‌شدهٔ مخصوص خودش
            role = "trend"
        else:
            role = (record.role if record else "").strip() or (
                "signal" if "signal" in saved else "range"
            )
        dataset = command.text("dataset", "").strip().upper()
        if not dataset:
            dataset = (record.timeframe if record else "") or "1H"

        # Signal training uses a first-passage price threshold.  The
        # empty field inherits the saved model's threshold; a range model
        # does not use this value.
        inherited = (
            float(getattr(record, "threshold", 0.0) or 0.0008)
            if role in ("signal", "trend_signal")
            else 0.0
        )
        if role == "signal":
            threshold = percent_to_fraction(command.text("threshold_pct", ""), inherited)
        elif role == "trend_signal":
            # فاز ۹۹: X برحسب ATR14 — خالی = threshold ذخیره‌شدهٔ مدل
            _raw = command.text("threshold_pct", "").strip()
            threshold = percent_to_fraction(_raw, inherited) if _raw else inherited
        else:
            threshold = 0.0  # trend رنگ — برچسب به آستانه نیاز ندارد

        note = []
        if record is not None and dataset != record.timeframe:
            # Allowed, but the operator should know: the same model is
            # being pointed at a different market rhythm.
            note.append(
                f"NOTE: {saved} was trained on {record.timeframe}; "
                f"retraining it on {dataset} changes what it models."
            )

        # LR: اگه کاربر عدد داده از همون استفاده کن، وگرنه از saved
        _lr_manual = command.number("learning_rate", 0.0)
        learning_rate = (
            float(_lr_manual)
            if _lr_manual and _lr_manual > 0
            else saved_learning_rate(self._storage_root, saved)
        )
        # resume flag: ادامه از checkpoint یا از صفر
        _resume = command.text("resume", "1").strip() == "1"
        _resume_args = ["--resume"] if _resume else []
        _mode_label = "resume" if _resume else "from scratch"

        # فاز ۶۲: پیچ‌های معماری + ولیدیشن — 0 = پیش‌فرض/auto (فاز ۵۹/۶۱)
        _n_layers = max(command.integer("n_layers", 0), 0)
        _n_blocks = max(command.integer("n_blocks", 0), 0)
        _val_size = max(command.integer("val_size", 0), 0)
        _arch_args = []
        if _n_layers:
            _arch_args += ["--n-layers", str(_n_layers)]
        if _n_blocks:
            _arch_args += ["--n-blocks", str(_n_blocks)]
        if _val_size:
            _arch_args += ["--val-size", str(_val_size)]
        _es_p = max(command.integer("es_patience", 0), 0)
        _rlr_p = max(command.integer("rlr_patience", 0), 0)
        if _es_p:
            _arch_args += ["--es-patience", str(_es_p)]
        if _rlr_p:
            _arch_args += ["--rlr-patience", str(_rlr_p)]
        # فاز ۸۰: horizon رنج — باید با مدل ذخیره‌شده یکی باشد
        if role == "range":
            _rng_h = max(command.integer("range_horizon", 1), 1)
            if _rng_h != 1:
                _arch_args += ["--horizon", str(_rng_h)]

        return self._run_script(
            command,
            [
                "scripts/run_dual_models.py",
                "--with-features",
                "--symbol",
                command.text("symbol", "XAUUSD"),
                "--model",
                role,
                "--range-timeframes" if role == "range" else "--signal-timeframe",
                dataset,
                "--epochs",
                str(max(command.integer("epochs", 2), 1)),
                "--folds",
                str(max(command.integer("folds", 2), 1)),
                "--window",
                str(max(command.integer("window", 150), 2)),
                "--train-ratio",
                str(command.number("train_ratio", 80.0)),
                "--threshold",
                str(threshold),
                "--learning-rate",
                str(learning_rate),
                "--storage-root",
                str(self._storage_root),
                *_arch_args,
                *_resume_args,
            ],
            f"Retrained {saved} on {dataset} "
            f"({_mode_label}, LR {learning_rate:.2e}"
            f"{' — manual' if (_lr_manual and _lr_manual > 0) else ' — auto/saved'})"
            + (f" — {note[0]}" if note else ""),
            started,
            timeout=7200,
        )

    # -- simulation --------------------------------------------------------------
    def _run_simulation(self, command: Command, record_replay: bool = False):
        """Run the model-driven simulation when its prerequisites exist.

        ``mode=auto`` is deliberately explicit about the compatibility
        fallback: old demo data may contain only one timeframe or no saved
        models. In that case the legacy momentum baseline is used and the
        result carries a warning. With both model/data sets present, the
        signal-first dual workflow is always selected.
        """
        from ShadBotTrader.application.services.backtest_service import BacktestService
        from ShadBotTrader.application.services.dual_model_backtest_service import (
            DualModelBacktestService,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from ShadBotTrader.domain.simulation.simulation_types import EntryTiming, SameBarPolicy
        from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource

        symbol_text = command.text("symbol", "XAUUSD")
        signal_timeframe = command.text("timeframe", "5M")
        symbol = Symbol(symbol_text)
        signal_tf = Timeframe(signal_timeframe)
        mode = command.text("mode", "auto").strip().lower()
        if mode not in {"auto", "dual", "legacy"}:
            raise ValueError("mode must be auto, dual or legacy")

        _, store, _ = build_service(self._storage_root)
        signal_candles = store.query(symbol, signal_tf)
        if not signal_candles:
            raise LookupError(
                f"No stored candles for {symbol_text} {signal_timeframe}. Fetch data first."
            )

        # ── last_n_candles: فقط N کندل آخر برای تست سریع ─────────────────
        last_n = max(0, command.integer("last_n_candles", 0))
        if last_n > 0 and len(signal_candles) > last_n:
            signal_candles = list(signal_candles)[-last_n:]

        dual_note = ""
        range_timeframe = command.text("range_timeframe", "1D")
        range_candles = store.query(symbol, Timeframe(range_timeframe))
        # فاز ۹۷: استراتژی سه‌تایم‌فریمی — مدل رنج 1D هم لازم است.
        # وقتی کلید غایب است (فراخوانی قدیمی/تست‌ها) → classic؛ فرم GUI
        # همیشه فیلد را می‌فرستد (پیش‌فرض فرم = triple).
        _strategy = command.text("strategy", "classic").strip().lower() or "classic"
        _slope_mode = command.text("slope_mode", "both").strip().lower() or "both"
        daily_candles: list = []
        if mode in ("dual", "auto") and _strategy == "triple":
            if range_timeframe.upper() != "4H":
                raise ValueError(
                    "Triple strategy needs Range timeframe = 4H (TP/SL from the "
                    "4H model). Set Range timeframe to 4H or use strategy=classic."
                )
            daily_candles = list(store.query(symbol, Timeframe("1D")))
            if not daily_candles:
                raise LookupError(
                    "Triple strategy needs stored XAUUSD 1D candles — "
                    "fetch XAUUSD 1D first (daily trend license)."
                )

        # باگ ۴۹: range candles هرگز با last_n بریده نمی‌شود.
        # ۹٬۰۰۰ کندل 5M یعنی ~۳۱ روز؛ برش زمانیِ range با همان cutoff
        # فقط ~۳۰ کندل 1D باقی می‌گذاشت در حالی که مدل رنج برای هر تصمیم
        # window=150 کندل روزانه می‌خواهد → abstain همیشگی → trades=0.
        # علیت را خودِ DualModelPredictionSource enforce می‌کند (فقط
        # کندل‌های 1D بسته‌شده قبل از زمان تصمیم دیده می‌شوند)؛ بریدن
        # تاریخچهٔ range نه لازم است نه بی‌خطر.
        if last_n > 0 and not range_candles and mode in ("dual", "auto"):
            dual_note = (
                f"No stored {range_timeframe} candles — the dual engine "
                "cannot produce range forecasts."
            )
        # configuration رو از قبل تعریف کن تا scoping خطا نده
        _spread_fixed, _spread_pct = _parse_spread(command)
        configuration = SimulationConfiguration(
            initial_capital=Decimal(str(command.number("capital", 100.0))),
            spread=_spread_fixed,
            spread_pct=_spread_pct,
            slippage_rate=Decimal(str(command.number("slippage", 0.0))),
            commission_rate=Decimal(str(command.number("commission", 0.0))),
            warmup_bars=0,
            entry_timing=EntryTiming.NEXT_OPEN,
            same_bar_policy=SameBarPolicy(
                command.text("same_bar_policy", SameBarPolicy.STOP_FIRST.value)
            ),
        )
        if mode != "legacy" and range_candles:
            try:
                _spread_fixed, _spread_pct = _parse_spread(command)
                configuration = SimulationConfiguration(
                    initial_capital=Decimal(str(command.number("capital", 100.0))),
                    spread=_spread_fixed,
                    spread_pct=_spread_pct,
                    slippage_rate=Decimal(str(command.number("slippage", 0.0))),
                    commission_rate=Decimal(str(command.number("commission", 0.0))),
                    warmup_bars=0,
                    entry_timing=EntryTiming.NEXT_OPEN,
                    same_bar_policy=SameBarPolicy(
                        command.text("same_bar_policy", SameBarPolicy.STOP_FIRST.value)
                    ),
                )
                # فاز ۵۲: session filter و min_sl_distance
                _session_filter = command.text("session_filter", "0").strip() == "1"
                _allowed_hours = list({2, 5, 6, 10, 14, 15, 16, 18}) if _session_filter else None
                _min_sl = max(0.0, command.number("min_sl_distance", 0.0))

                # range_model_id از range_timeframe ساخته میشه
                # gold_range_1h یا gold_range_1d بسته به انتخاب کاربر
                # فاز ۹۶: «id:vN» نسخهٔ صریح را انتخاب می‌کند — بدون آن
                # latest_version (بزرگ‌ترین شماره) لود می‌شود که ممکن است
                # مدل قدیمیِ قبل از فاز ۹۵ باشد.
                _default_range_id = f"gold_range_{range_timeframe.lower()}"
                _signal_id, _signal_ver = _split_model_spec(
                    command.text("signal_model", ""), "gold_signal_5m"
                )
                _range_id, _range_ver = _split_model_spec(
                    command.text("range_model", ""), _default_range_id
                )
                dual = DualModelBacktestService.from_storage(
                    storage_root=self._storage_root,
                    symbol=symbol_text,
                    signal_model_id=_signal_id,
                    range_model_id=_range_id,
                    signal_version=_signal_ver,
                    range_version=_range_ver,
                    min_signal_confidence=command.number("threshold_pct", 60.0) / 100.0,
                    signal_window_size=command.integer("signal_window", 0) or None,
                    range_window_size=command.integer("range_window", 0) or None,
                    configuration=configuration,
                    base_quantity=Decimal(str(command.number("quantity", 0.01))),
                    reward_risk_multiplier=command.number("reward_risk_multiplier", 1.5),
                    filter_zero_bar=command.text("filter_zero_bar", "0").strip() == "1",
                    allowed_hours_utc=_allowed_hours,
                    min_sl_distance=_min_sl,
                    trend_filter=command.text("trend_filter", "none").strip() or "none",
                    strategy=_strategy,
                    slope_mode=_slope_mode,
                    max_entry_distance_atr=command.number("max_entry_distance_atr", 0.25),
                )
                result = dual.run(
                    session_id=("replay-" if record_replay else "dashboard-") + symbol_text,
                    signal_candles=signal_candles,
                    range_candles=range_candles,
                    record_replay=record_replay,
                    test_ratio=command.number("test_ratio", 0.0) / 100.0,
                    daily_candles=daily_candles,
                )
                # باگ ۴۹-completion: مسیر dual هم باید خوراک رنج را گزارش کند
                self._last_range_feed = (
                    (len(range_candles), range_timeframe)
                    if mode == "dual" and range_candles
                    else None
                )
                self._last_run_context = {
                    "symbol_line": f"{symbol_text} {signal_timeframe} + {range_timeframe} (range)",
                    "models_line": f"{_signal_id}:{_signal_ver or 'latest'}"
                    f" + {_range_id}:{_range_ver or 'latest'}",
                }
                return result, "dual", ""
            except Exception as _dual_err:
                if mode == "dual":
                    raise

                _err_detail = str(_dual_err)[:300]
                dual_note = f"Dual-model failed: {_err_detail} — legacy baseline was used."
        elif mode == "dual":
            raise LookupError(
                f"Dual mode needs stored {symbol_text} {range_timeframe} candles "
                "as well as the saved signal and range models."
            )
        elif mode == "auto":
            dual_note = (
                f"Dual mode unavailable: store {symbol_text} {range_timeframe} candles "
                "and both saved models to enable signal -> range -> TP/SL."
            )

        legacy = BacktestService(
            configuration=SimulationConfiguration(
                initial_capital=Decimal(str(command.number("capital", 100.0))),
                spread=Decimal(str(command.number("spread", 4.0))),
                slippage_rate=Decimal(str(command.number("slippage", 0.0))),
                commission_rate=Decimal("0.0001"),
                warmup_bars=20,
            ),
            base_quantity=Decimal(str(command.number("quantity", 0.01))),
        )
        result = legacy.run(
            f"legacy-{'replay' if record_replay else 'dashboard'}-{symbol_text}",
            symbol,
            signal_tf,
            signal_candles,
            prediction_source=MomentumPredictionSource(lookback=6),
            record_replay=record_replay,
        )
        # باگ ۴۹: برای گزارش — چند کندل 1D واقعاً به موتور رسید
        self._last_range_feed = (
            (len(range_candles), range_timeframe) if mode == "dual" and range_candles else None
        )
        self._last_run_context = {
            "symbol_line": f"{symbol_text} {signal_timeframe}",
            "models_line": "legacy momentum baseline",
        }
        return result, "legacy", dual_note

    def run_backtest(self, command: Command) -> CommandResult:
        started = time.monotonic()
        self._last_backtest_replay_ready = False
        try:
            # Record the exact tape here as well. Record a replay can then
            # serve this completed run verbatim instead of rerunning it.
            result, mode, note = self._run_simulation(command, record_replay=True)
        except LookupError as error:
            return CommandResult.rejected(command.kind, str(error))
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Backtest failed", str(error), time.monotonic() - started
            )

        # Record the exact effective inputs used by this completed run.
        # Record a replay uses them by default for a like-for-like rerun.
        self._last_backtest_parameters = dict(command.parameters)
        metrics = result.metrics
        self._last_backtest_summary = {
            "run_id": result.session.session_id,
            "engine": mode,
            "trades": metrics.trade_count,
            "initial_equity": metrics.starting_equity,
            "final_equity": metrics.final_equity,
            "return": metrics.total_return,
            "return_percent": metrics.total_return_percent,
            "gross_profit": metrics.gross_profit,
            "gross_loss": metrics.gross_loss,
            "net_profit": metrics.net_profit,
            "net_loss": metrics.net_loss,
            "profit_factor": metrics.profit_factor,
            "net_profit_factor": metrics.net_profit_factor,
            "expectancy": metrics.expectancy,
            "fees": metrics.total_fees,
            "spread_cost": metrics.spread_cost,
            "slippage_cost": metrics.slippage_cost,
            "quantity": command.number("quantity", 0.01),
            "spread": command.number("spread", 0.35 if mode == "dual" else 4.0),
            "commission_rate": 0.0001,
            "slippage_rate": command.number("slippage", 0.0),
            "entry_timing": "next_open" if mode == "dual" else "signal_close",
            "test_ratio": command.number("test_ratio", 0.0) / 100.0,
            "reward_risk_multiplier": command.number("reward_risk_multiplier", 1.5),
            "filter_zero_bar": command.text("filter_zero_bar", "0").strip() == "1",
            "take_profits": result.bracket_exit_counts.get("take_profit", 0),
            "stop_losses": result.bracket_exit_counts.get("stop_loss", 0),
        }
        self._last_backtest_replay_ready = False
        replay_diagnostics: List[str] = []
        trade_log_path: Optional[Path] = None
        if result.tape is not None:
            tape = result.tape
            tape_final = tape.final_equity
            tape_closed = len(tape.round_trips())
            replay_diagnostics = [
                f"replay bars : {len(tape.bars)}",
                f"replay fills: {len(tape.markers)}",
                f"replay closed: {tape_closed}",
                f"replay final : {tape_final}",
            ]
            if tape_final != metrics.final_equity or tape_closed != metrics.trade_count:
                return CommandResult.failure(
                    command.kind,
                    "Backtest/replay consistency check failed",
                    "\\n".join(
                        [
                            f"engine final equity : {metrics.final_equity}",
                            f"replay final equity : {tape_final}",
                            f"engine trades       : {metrics.trade_count}",
                            f"replay closed       : {tape_closed}",
                            "The replay was not published because it does not describe "
                            "the same run.",
                        ]
                    ),
                    time.monotonic() - started,
                )
            from ShadBotTrader.infrastructure.simulation.trade_log import write_trade_log
            from ShadBotTrader.presentation.web.replay_renderer import render_replay

            self._replay_path.parent.mkdir(parents=True, exist_ok=True)
            self._replay_path.write_text(render_replay(tape, result.metrics), encoding="utf-8")
            try:
                trade_log_path = write_trade_log(
                    tape,
                    self._run_log_dir / "backtest_trades.csv",
                    run_metadata=self._last_backtest_summary,
                )
            except Exception as error:  # the numeric backtest must remain usable
                replay_diagnostics.append(f"trade log : FAILED ({type(error).__name__}: {error})")
            self._last_backtest_replay_ready = True
        hit = metrics.hit_rate
        profit_factor = metrics.profit_factor if metrics.profit_factor is not None else "n/a"
        net_profit_factor = (
            metrics.net_profit_factor if metrics.net_profit_factor is not None else "n/a"
        )
        expectancy = metrics.expectancy if metrics.expectancy is not None else "n/a"
        # ── لاگ مدل‌های لودشده ────────────────────────────────────────────
        _model_log_lines: list = []
        if mode == "dual":
            try:
                from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

                _catalogue = ModelCatalogue(self._storage_root)
                for _mid in [
                    command.text("signal_model", "gold_signal_5m"),
                    f"gold_range_{command.text('range_timeframe', '1D').lower()}",
                ]:
                    _ver = _catalogue.latest_version(_mid)
                    _rec = _catalogue.read(_mid, _ver) if _ver else None
                    if _rec:
                        _model_log_lines.append(
                            f"  {_rec.model_id} v{_rec.version}"
                            f" | {_rec.role}/{_rec.timeframe}"
                            f" | {_rec.headline_metric}"
                            f" | epochs={_rec.epochs}"
                            f" | trained={_rec.trained_at[:10]}"
                        )
                    else:
                        _model_log_lines.append(f"  {_mid} — NOT FOUND!")
            except Exception as _e:
                _model_log_lines.append(f"  model info error: {_e}")

        # فاز ۷۱: بخش «شرایط شروع» — هر فیلدی که در فرم تنظیم می‌شود
        # باید در گزارش باشد تا هر اجرا قابل بازتولید و مقایسه باشد.
        _feed = getattr(self, "_last_range_feed", None)
        _ctx = getattr(self, "_last_run_context", None) or {}
        lines = [
            f"engine      : {mode}",
            f"build       : {ENGINE_BUILD}",
            f"run id      : {result.session.session_id}",
            (f"symbol      : {_ctx.get('symbol_line', '')}" if _ctx else "symbol      : n/a"),
            (f"models      : {_ctx.get('models_line', '')}" if _ctx else "models      : n/a"),
            f"confidence  : {command.number('threshold_pct', 60.0):g}% (signal gate)",
            (
                f"windows     : signal={command.integer('signal_window', 0) or 'model'}"
                f" · range={command.integer('range_window', 0) or 'model'}"
            ),
            f"R/R mult.   : {command.number('reward_risk_multiplier', 1.5):g}",
            f"same-bar    : {command.text('same_bar_policy', 'stop_first')}",
            (
                f"test ratio  : {command.number('test_ratio', 0.0):g}%"
                + ("" if command.number("test_ratio", 0.0) > 0 else " (all bars)")
            ),
            (
                "session filt: "
                + (
                    "yes — hours 2,5,6,10,14,15,16,18 UTC"
                    if command.text("session_filter", "0").strip() == "1"
                    else "no"
                )
            ),
            (
                "trend filt : "
                + (
                    "ema50 — anti-trend entries blocked"
                    if (command.text("trend_filter", "none").strip() or "none") == "ema50"
                    else "off"
                )
            ),
            (
                "strategy   : "
                + (
                    f"triple — 5M signal · "
                    f"{command.text('range_timeframe', '1D')} bracket · 1D trend "
                    f"(slope {command.text('slope_mode', 'both')}, "
                    f"proximity {command.number('max_entry_distance_atr', 0.25)}×ATR)"
                    if (command.text("strategy", "triple").strip() or "triple") == "triple"
                    else "classic — single range model"
                )
            ),
            (
                f"min SL dist : {command.number('min_sl_distance', 0.0):g}$"
                if command.number("min_sl_distance", 0.0) > 0
                else "min SL dist : off"
            ),
            (
                "filter 0-bar: "
                + ("yes" if command.text("filter_zero_bar", "0").strip() == "1" else "no")
            ),
            (
                f"capital     : {command.number('capital', 100.0):g}"
                f" · quantity: {command.number('quantity', 0.01):g}"
            ),
            (
                f"spread      : {command.number('spread_value', 0.06):g}"
                + ("%" if command.text("spread_mode", "pct") == "pct" else "$")
                + f" · commission: {command.number('commission', 0.0):g}"
            ),
            f"slip rate   : {command.number('slippage', 0.0):g}",
            f"entry       : {'next_open' if mode == 'dual' else 'signal_close'}",
            # باگ ۴۹: شفافیت — چند کندل 1D واقعاً به موتور رنج رسید؟
            (
                f"range candles: {self._last_range_feed[0]} ({self._last_range_feed[1]})"
                if getattr(self, "_last_range_feed", None)
                else "range candles: n/a"
            ),
            (
                f"last N bars : {command.integer('last_n_candles', 0):,} کندل آخر"
                if command.integer("last_n_candles", 0) > 0
                else "last N bars : all (کل تاریخچه)"
            ),
            f"trades      : {metrics.trade_count}",
            f"initial eq  : {metrics.starting_equity:.4f}",
            f"final eq    : {metrics.final_equity:.4f}",
            f"return      : {metrics.total_return:.4f} " f"({metrics.total_return_percent:.2f}%)",
            f"gross profit: {metrics.gross_profit:.4f}",
            f"gross loss  : {metrics.gross_loss:.4f}",
            f"net profit  : {metrics.net_profit:.4f}",
            f"net loss    : {metrics.net_loss:.4f}",
            f"profit fact.: {profit_factor}",
            f"net PF      : {net_profit_factor}",
            f"expectancy  : {expectancy}",
            f"max drawdown: {metrics.max_drawdown_percent:.2f}%",
            f"hit rate    : {f'{hit:.3f}' if hit is not None else 'n/a'}",
            f"fees        : {metrics.total_fees:.4f}",
            f"spread cost : {metrics.spread_cost:.4f}",
            f"slippage    : {metrics.slippage_cost:.4f}",
        ]
        if mode == "dual":
            lines.extend(
                [
                    f"take profits: {result.bracket_exit_counts['take_profit']}",
                    f"stop losses : {result.bracket_exit_counts['stop_loss']}",
                ]
            )
            # فاز ۶۸: شمارش نقاط سیگنال و خطاهای رنج/سیگنال — تا رد شدن
            # یا خطای خاموش دیگر نامرئی نماند (باگ ۵۰ همین‌جا پنهان بود).
            _pst = getattr(result, "source_stats", {}) or {}
            if _pst:
                lines.append(
                    f"signals seen: {_pst.get('signal_predictions', 0)}"
                    f" · range ran: {_pst.get('range_predictions', 0)}"
                    f" · abstains: {_pst.get('abstentions', 0)}"
                )
                # فاز ۹۷: گیت‌های استراتژی سه‌تایم‌فریمی
                if _pst.get("daily_blocked") or _pst.get("daily_predictions"):
                    lines.append(
                        f"daily gate : {_pst.get('daily_blocked', 0)} blocked · "
                        f"{_pst.get('daily_predictions', 0)} passed "
                        f"(slope {_pst.get('slope_mode', 'both')})"
                    )
                if _pst.get("proximity_blocked"):
                    lines.append(
                        f"proximity  : {_pst['proximity_blocked']} entries refused — "
                        f"too far from the daily level "
                        f"(max {_pst.get('max_entry_distance_atr', 0)}×ATR)"
                    )
                if _pst.get("sl_fallback_d0") or _pst.get("sl_fallback_today"):
                    lines.append(
                        f"sl fallback: D0 x{_pst.get('sl_fallback_d0', 0)} · "
                        f"today-5M x{_pst.get('sl_fallback_today', 0)} · "
                        f"no-SL refused {_pst.get('no_sl_found', 0)} · "
                        f"final-SL refused {_pst.get('final_sl_refused', 0)}"
                    )
                if _pst.get("license3_refused") or _pst.get("rr_refused"):
                    lines.append(
                        f"lic-3/rr   : TP-side refused {_pst.get('license3_refused', 0)} · "
                        f"R/R refused {_pst.get('rr_refused', 0)}"
                    )
                # فاز ۹۶-ب: بلوک‌های فیلتر ترند
                if _pst.get("trend_blocked"):
                    lines.append(
                        f"trend blocks: {_pst['trend_blocked']} anti-trend entries "
                        f"refused by ema50 filter"
                    )
                # فاز ۹۵/۹۶: واحد تارگت مدل رنج — مدل قدیمی (pct) هشدار بلند
                if _pst.get("range_target_units"):
                    if _pst["range_target_units"] == "pct":
                        lines.append(
                            "range units : pct ‼️ PRE-Phase95 model — offsets are a "
                            "CONSTANT % of price. Select the ATR model "
                            "(range_model = id:vN, e.g. gold_range_1d:v1) or archive "
                            "the old version; results are not comparable."
                        )
                    else:
                        lines.append(f"range units : {_pst['range_target_units']}")
                for _err, _n in (_pst.get("errors") or {}).items():
                    lines.append(f"  [err x{_n}] {_err}")
        if replay_diagnostics:
            lines.extend(replay_diagnostics)
        if trade_log_path is not None:
            lines.append(f"trade log   : {trade_log_path} ({len(result.tape.round_trips())} rows)")
        if self._last_backtest_replay_ready:
            lines.append(f"replay      : exact tape written to {self._replay_path}")
        if note:
            lines.append(f"note        : {note}")
        # مدل‌های لودشده رو به ابتدای lines اضافه کن
        if _model_log_lines:
            model_header = ["--- models loaded ---"] + _model_log_lines + ["---"]
            lines = model_header + lines

        # لاگ کامل رو روی disk هم ذخیره کن
        try:
            import datetime as _dt

            _log_dir = self._run_log_dir
            _log_dir.mkdir(parents=True, exist_ok=True)
            _log_path = _log_dir / "backtest_run.log"
            _ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _sep = "=" * 60
            with open(_log_path, "a", encoding="utf-8") as _lf:
                _lf.write("\n" + _sep + "\n")
                _lf.write("BACKTEST RUN @ " + _ts + "\n")
                _lf.write(_sep + "\n")
                for _line in lines:
                    _lf.write(_line + "\n")
        except Exception:
            pass  # لاگ fail نباید بکتست رو خراب کنه

        return CommandResult.success(
            command.kind,
            f"Backtested {result.bars_processed} bars ({mode})",
            lines,
            time.monotonic() - started,
        )

    def record_replay(self, command: Command) -> CommandResult:
        """Run a recorded backtest and write the player to disk."""
        from ShadBotTrader.presentation.web.replay_renderer import render_replay

        started = time.monotonic()
        effective_command = command
        used_last_settings = False
        requested = str(command.get("use_last_settings", "1")).lower()
        if self._last_backtest_parameters and requested not in {"0", "false", "no", "off"}:
            effective_command = Command(
                kind=command.kind,
                parameters=dict(self._last_backtest_parameters),
            )
            used_last_settings = True

        # The normal Run a backtest now records the tape once. Reuse that
        # exact tape instead of running the models a second time; this is
        # the strongest guarantee that the numeric report and /replay are
        # describing the same run.
        if used_last_settings and self._last_backtest_replay_ready and self._replay_path.exists():
            summary = self._last_backtest_summary
            lines = [
                f"engine        : {summary.get('engine', 'unknown')}",
                f"run id        : {summary.get('run_id', 'unknown')}",
                f"trades        : {summary.get('trades', 0)}",
                f"initial eq    : {summary.get('initial_equity', 0)}",
                f"final eq      : {summary.get('final_equity', 0)}",
                f"return        : {summary.get('return', 0)} "
                f"({summary.get('return_percent', 0):.2f}%)",
                f"R/R mult.     : {summary.get('reward_risk_multiplier', 1.5):g}",
                f"filter 0-bar  : {'yes' if summary.get('filter_zero_bar', False) else 'no'}",
                f"fees          : {summary.get('fees', 0)}",
                f"spread cost   : {summary.get('spread_cost', 0)}",
                f"slippage      : {summary.get('slippage_cost', 0)}",
                f"take profits  : {summary.get('take_profits', 0)}",
                f"stop losses   : {summary.get('stop_losses', 0)}",
                "settings      : exact tape from the last completed Run a backtest",
                f"written to    : {self._replay_path}",
            ]
            return CommandResult.success(
                command.kind,
                "Replay is the exact last completed backtest",
                lines,
                time.monotonic() - started,
            )

        try:
            result, mode, note = self._run_simulation(effective_command, record_replay=True)
        except LookupError as error:
            return CommandResult.rejected(command.kind, str(error))
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Replay run failed", str(error), time.monotonic() - started
            )

        tape = result.tape
        if tape is None:  # pragma: no cover - recording was requested
            return CommandResult.failure(
                command.kind, "The run produced no replay", "", time.monotonic() - started
            )

        markup = render_replay(tape, result.metrics)
        self._replay_path.parent.mkdir(parents=True, exist_ok=True)
        self._replay_path.write_text(markup, encoding="utf-8")
        trade_log_path: Optional[Path] = None
        try:
            from ShadBotTrader.infrastructure.simulation.trade_log import write_trade_log

            trade_log_path = write_trade_log(
                tape,
                self._run_log_dir / "backtest_trades.csv",
                run_metadata={
                    "engine": mode,
                    "quantity": command.number("quantity", 0.01),
                    "spread": command.number("spread", 0.35 if mode == "dual" else 4.0),
                    "commission_rate": 0.0001,
                    "slippage_rate": command.number("slippage", 0.0),
                    "test_ratio": command.number("test_ratio", 0.0) / 100.0,
                    "reward_risk_multiplier": command.number("reward_risk_multiplier", 1.5),
                    "filter_zero_bar": command.text("filter_zero_bar", "0").strip() == "1",
                },
            )
        except Exception:
            # Replay rendering remains useful even if a filesystem log
            # cannot be written.
            pass

        trips = tape.round_trips()
        wins = sum(1 for trip in trips if trip["result"] == "win")
        lines = [
            f"engine        : {mode}",
            f"run id        : {tape.session_id}",
            f"fills         : {len(tape.markers)}",
            f"closed trades : {len(trips)} ({wins} win / {len(trips) - wins} loss)",
            f"return        : {result.metrics.total_return:.4f} "
            f"({result.metrics.total_return_percent:.2f}%)",
            f"written to    : {self._replay_path}",
        ]
        if trade_log_path is not None:
            lines.append(f"trade log     : {trade_log_path} ({len(trips)} rows)")
        if mode == "dual":
            lines.extend(
                [
                    f"take profits  : {result.bracket_exit_counts['take_profit']}",
                    f"stop losses   : {result.bracket_exit_counts['stop_loss']}",
                ]
            )
        if used_last_settings:
            lines.append("settings      : same as the last completed Run a backtest")
        if note:
            lines.append(f"note          : {note}")
        return CommandResult.success(
            command.kind,
            f"Recorded {len(tape.bars)} bars — open /replay to watch it",
            lines,
            time.monotonic() - started,
        )

    def run_optimisation(self, command: Command) -> CommandResult:
        from ShadBotTrader.application.services.optimisation_service import (
            OptimisationService,
            default_baseline,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from ShadBotTrader.infrastructure.persistence import (
            Database,
            SqliteLearningMemory,
        )

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD")
        timeframe = command.text("timeframe", "5M")
        folds = max(command.integer("folds", 3), 2)

        _, store, _ = build_service(self._storage_root)
        candles = store.query(Symbol(symbol), Timeframe(timeframe))
        if not candles:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {timeframe}. Fetch data first.",
            )

        database = Database(self._database_path)
        try:
            service = OptimisationService(
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                simulation_config=SimulationConfiguration(
                    initial_capital=Decimal("100"),
                    spread=Decimal("4"),
                    commission_rate=Decimal(str(command.number("commission", 0.0))),
                    warmup_bars=10,
                ),
            )
            # results land in the database so the dashboard shows them
            service.memory = SqliteLearningMemory(database)
            result = service.run(
                f"dashboard-{symbol}",
                {"lookback": [3, 6, 12], "strategy_min_confidence": [0.55, 0.65]},
                candles,
                baseline=default_baseline(),
                fold_count=folds,
            )
        except Exception as error:
            database.close()
            return CommandResult.failure(
                command.kind,
                "Optimisation failed",
                str(error),
                time.monotonic() - started,
            )
        database.close()

        verdict = result.verdict
        if verdict is None:
            outcome = "no candidate reached the gate"
        elif verdict.approved:
            outcome = f"APPROVED — {verdict.reason}"
        else:
            reason = verdict.rejection_reason
            outcome = f"REJECTED ({reason.value if reason else 'unknown'})"

        return CommandResult.success(
            command.kind,
            f"Evaluated {len(result.evaluated)} candidate(s)",
            [
                f"validated : {len(result.validated)}",
                f"promoted  : {result.promoted}",
                f"gate      : {outcome}",
                "A rejection is a valid outcome: the gate refuses anything",
                "that cannot prove itself out of sample.",
            ],
            time.monotonic() - started,
        )

    # -- trading -------------------------------------------------------------
    def run_trading_cycle(self, command: Command) -> CommandResult:
        from ShadBotTrader.application.services.execution_service import ExecutionService
        from ShadBotTrader.application.services.trading_decision_service import (
            TradingDecisionService,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.execution.market_view import (
            ExecutionContext,
        )
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
        from ShadBotTrader.domain.strategy.strategy_context import (
            PortfolioView,
            PredictionView,
            StrategyContext,
        )
        from ShadBotTrader.infrastructure.execution import (
            DefaultIntentResolver,
            SimulatedExecutionVenue,
        )
        from ShadBotTrader.infrastructure.persistence import (
            Database,
            SqliteDecisionJournal,
            SqliteExecutionJournal,
            SqlitePortfolioLedger,
        )
        from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource
        from ShadBotTrader.infrastructure.simulation.candle_data_provider import (
            CandleMarketDataProvider,
        )
        from ShadBotTrader.infrastructure.trading import (
            AiDirectionalStrategy,
            DefaultIntentFactory,
            DefaultSignalValidator,
            PolicyRiskGate,
            PositionAwareDecisionEngine,
        )

        started = time.monotonic()
        symbol_text = command.text("symbol", "XAUUSD")
        timeframe_text = command.text("timeframe", "5M")
        session = command.text("session", "dashboard")
        symbol = Symbol(symbol_text)
        timeframe = Timeframe(timeframe_text)

        _, store, _ = build_service(self._storage_root)
        candles = store.query(symbol, timeframe)
        if len(candles) < 20:
            return CommandResult.rejected(
                command.kind,
                f"Need at least 20 candles for {symbol_text}; found {len(candles)}.",
            )

        # A prediction for the latest bar, produced by the same source the
        # backtester uses — the GUI does not compute anything itself.
        provider = CandleMarketDataProvider(symbol, candles, spread=Decimal("4"))
        source = MomentumPredictionSource(lookback=6)
        events = provider.events()
        for event in events:
            source.observe(event)
        latest = events[-1]
        value = source.predict(latest)
        if value is None:
            return CommandResult.rejected(command.kind, "Not enough history for a prediction.")

        database = Database(self._database_path)
        ledger = SqlitePortfolioLedger(database, session_id=session, starting_cash=Decimal("100"))
        trading = TradingDecisionService(
            strategies=[AiDirectionalStrategy(min_confidence=0.55)],
            decision_engine=PositionAwareDecisionEngine(),
            risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=2)),
            intent_factory=DefaultIntentFactory(base_quantity=Decimal("0.01")),
            validator=DefaultSignalValidator(max_signal_age_seconds=10**9),
            journal=SqliteDecisionJournal(database, session_id=session),
        )
        execution = ExecutionService(
            resolver=DefaultIntentResolver(),
            venue=SimulatedExecutionVenue(commission_rate=Decimal("0.0001")),
            ledger=ledger,
            journal=SqliteExecutionJournal(database, session_id=session),
        )

        position = ledger.position(symbol)
        context = StrategyContext(
            timestamp=latest.event_time,
            symbol=symbol,
            timeframe=timeframe,
            predictions=[
                PredictionView(
                    model_id="gold_direction",
                    model_version=1,
                    value=value,
                    confidence=source.confidence(latest),
                    generated_at=latest.event_time,
                )
            ],
            portfolio=PortfolioView(
                equity=ledger.cash.amount,
                open_position_quantity=position.signed_quantity,
                open_position_count=0 if position.is_flat else 1,
            ),
        )

        outcome = trading.evaluate(context)
        lines = [
            f"prediction : {value:.4f}",
            f"signal     : {outcome.signal.signal_type.value if outcome.signal else '-'}",
            f"decision   : " f"{outcome.decision.decision_type.value if outcome.decision else '-'}",
        ]

        if outcome.intent is None:
            lines.append(f"no intent  : {outcome.rejected_reason or 'nothing to do'}")
            database.close()
            return CommandResult.success(
                command.kind,
                "Cycle complete — no trade",
                lines,
                time.monotonic() - started,
            )

        quote = provider.quote_for(latest.candle) if latest.candle else None
        if quote is None:
            database.close()
            return CommandResult.failure(command.kind, "No quote for the latest bar")

        executed = execution.execute(
            outcome.intent,
            ExecutionContext(
                timestamp=latest.event_time,
                quote=quote,
                position=position,
                equity=ledger.cash.amount,
            ),
        )
        if executed.executed and executed.result is not None:
            lines.append(
                f"filled     : {executed.result.filled_quantity} @ "
                f"{executed.result.average_fill_price}"
            )
        else:
            lines.append(f"not filled : {executed.rejected_reason}")
        lines.append(f"position   : {ledger.position(symbol)}")
        database.close()

        return CommandResult.success(
            command.kind,
            f"Cycle complete for session '{session}'",
            lines,
            time.monotonic() - started,
        )

    # -- project ----------------------------------------------------------------
    def refresh_project_state(self, command: Command) -> CommandResult:
        from ShadBotTrader.intelligence import main as intelligence_main

        started = time.monotonic()
        try:
            code = intelligence_main(["--project-root", str(Path.cwd())])
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Project scan failed",
                str(error),
                time.monotonic() - started,
            )
        if code != 0:
            return CommandResult.failure(command.kind, f"Scanner exited with {code}")
        return CommandResult.success(
            command.kind,
            "Project state regenerated",
            ["written to project_state/generated/"],
            time.monotonic() - started,
        )


class AccountCommandHandlers(CommandHandlers):
    """Handlers for the Phase 32 account and operations commands.

    Separated from :class:`CommandHandlers` so the original class stays
    focused; both are merged into one registry by
    :meth:`CommandHandlers.registry`.

    Phase 40: it now *inherits* rather than duplicates. ``_run_script``
    used to live only here while ``train_model`` — which calls it — lived
    on the parent, so retraining would have raised ``AttributeError`` the
    moment anyone pressed the button. Sharing the helper through
    inheritance makes that impossible instead of merely fixed.
    """

    def __init__(
        self,
        database_path: "str | Path",
        storage_root: "str | Path" = "datasets",
        account_store: "str | Path" = "configs/accounts.json",
    ) -> None:
        self._database_path = Path(database_path)
        self._storage_root = Path(storage_root)
        self._account_store = Path(account_store)
        self._run_log_dir = RUN_LOG_DIR

    def run_log_path(self, action: str) -> Path:
        """Where this handler streams a script's output while it runs."""
        return run_log_path(action, self._run_log_dir)

    # -- helpers ------------------------------------------------------------
    def _store(self):
        from ShadBotTrader.infrastructure.account import AccountProfileStore

        return AccountProfileStore(self._account_store)

    def active_profile(self):
        """The active broker profile, or None when none is configured.

        Used to translate symbols; a missing profile is not an error
        because the canonical name is the default anyway.
        """
        try:
            return self._store().active()
        except Exception:
            return None

    def _profile(self, command: Command):
        """The named profile, or the active one when no name is given."""
        store = self._store()
        name = command.text("name", "").strip()
        book = store.load()
        if name:
            return store, book.get(name)
        active = book.active_profile
        if active is None:
            raise LookupError("No account profile exists yet. Use 'Add account' first.")
        return store, active

    # -- accounts -----------------------------------------------------------
    def add_account(self, command: Command) -> CommandResult:
        started = time.monotonic()
        name = command.text("name", "").strip()
        login = command.integer("login", 0)
        server = command.text("server", "").strip()

        if not name or login <= 0 or not server:
            return CommandResult.rejected(command.kind, "name, login and server are all required")

        try:
            profile = self._store().add(
                name=name,
                login=login,
                server=server,
                terminal_path=command.text("terminal_path", "").strip(),
                is_demo=command.text("is_demo", "1").strip() != "0",
                make_active=True,
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not add the account",
                str(error),
                time.monotonic() - started,
            )

        lines = [
            f"login    : {profile.login} @ {profile.server}",
            f"type     : {'demo' if profile.is_demo else 'LIVE'}",
            "",
            "The password is NOT stored. Set it in your shell:",
            f"    $env:{profile.password_variable} = 'your-password'",
            "",
            "Or leave it unset to use the terminal's existing session.",
        ]
        return CommandResult.success(
            command.kind,
            f"Added '{name}' and made it active",
            lines,
            time.monotonic() - started,
        )

    def activate_account(self, command: Command) -> CommandResult:
        started = time.monotonic()
        name = command.text("name", "").strip()
        if not name:
            return CommandResult.rejected(command.kind, "a profile name is required")
        try:
            profile = self._store().activate(name)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not switch account",
                str(error),
                time.monotonic() - started,
            )
        return CommandResult.success(
            command.kind,
            f"'{name}' is now the active account",
            [
                f"login  : {profile.login} @ {profile.server}",
                f"type   : {'demo' if profile.is_demo else 'LIVE'}",
                f"symbols: {profile.symbol_map.to_dict() or 'no aliases'}",
            ],
            time.monotonic() - started,
        )

    def remove_account(self, command: Command) -> CommandResult:
        started = time.monotonic()
        name = command.text("name", "").strip()
        if not name:
            return CommandResult.rejected(command.kind, "a profile name is required")
        try:
            self._store().remove(name)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not remove the account",
                str(error),
                time.monotonic() - started,
            )
        remaining = self._store().load()
        return CommandResult.success(
            command.kind,
            f"Removed '{name}'",
            [
                f"remaining: {', '.join(remaining.names) or 'none'}",
                f"active   : {remaining.active or 'none'}",
            ],
            time.monotonic() - started,
        )

    def check_account(self, command: Command) -> CommandResult:
        from ShadBotTrader.infrastructure.account import AccountConnector

        started = time.monotonic()
        try:
            store, profile = self._profile(command)
        except Exception as error:
            return CommandResult.rejected(command.kind, str(error))

        report = AccountConnector(store).check(profile)
        if not report.connected:
            return CommandResult.failure(
                command.kind,
                f"Cannot reach the broker for '{profile.name}'",
                report.error + "\n\nIs MetaTrader 5 running and logged in?",
                time.monotonic() - started,
            )

        return CommandResult.success(
            command.kind,
            f"'{profile.name}' is reachable"
            + ("" if report.is_usable else " — but some symbols are missing"),
            report.summary_lines(),
            time.monotonic() - started,
        )

    def map_symbol(self, command: Command) -> CommandResult:
        started = time.monotonic()
        canonical = command.text("canonical", "").strip()
        broker = command.text("broker", "").strip()
        if not canonical or not broker:
            return CommandResult.rejected(
                command.kind, "both the platform and broker symbol are required"
            )
        try:
            store, profile = self._profile(command)
            updated = store.set_symbol(profile.name, canonical, broker)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not map the symbol",
                str(error),
                time.monotonic() - started,
            )
        return CommandResult.success(
            command.kind,
            f"{canonical} -> {broker} on '{updated.name}'",
            [f"{key} -> {value}" for key, value in sorted(updated.symbol_map.aliases.items())],
            time.monotonic() - started,
        )

    def auto_map_symbols(self, command: Command) -> CommandResult:
        from ShadBotTrader.infrastructure.account import AccountConnector

        started = time.monotonic()
        try:
            store, profile = self._profile(command)
        except Exception as error:
            return CommandResult.rejected(command.kind, str(error))

        wanted = [
            item.strip() for item in command.text("symbols", "XAUUSD").split(",") if item.strip()
        ]
        try:
            found = AccountConnector(store).auto_map(profile, wanted)
        except Exception as error:
            return CommandResult.failure(
                command.kind,
                "Could not read the broker's symbol list",
                str(error),
                time.monotonic() - started,
            )

        apply = command.text("apply", "0").strip() == "1"
        lines: List[str] = []
        for canonical in wanted:
            suggestion = found.get(canonical.strip().upper())
            if suggestion is None:
                lines.append(f"{canonical:<10} -> NOT FOUND at this broker")
                continue
            lines.append(f"{canonical:<10} -> {suggestion}")
            if apply:
                store.set_symbol(profile.name, canonical, suggestion)

        lines.append("")
        lines.append(
            "Applied and saved."
            if apply
            else "Suggestions only — re-run with 'Apply suggestions' = 1 to save."
        )
        return CommandResult.success(
            command.kind,
            f"Matched {len(found)} of {len(wanted)} symbol(s)",
            lines,
            time.monotonic() - started,
        )

    # -- data ---------------------------------------------------------------
    def missing_timeframes(self, symbol: str) -> List[str]:
        """Training timeframes that have no stored candles yet.

        Checked before the build rather than during it, so the operator
        is told which button to press instead of reading a stack trace
        three minutes into a feature computation.
        """
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.infrastructure.data.symbol_scope import (
            resolve_stored_symbol,
        )

        try:
            _, store, _ = build_service(self._storage_root)
        except Exception:
            return []

        profile = self.active_profile()
        missing: List[str] = []
        for timeframe in TRAINING_TIMEFRAMES:
            try:
                found = resolve_stored_symbol(store, symbol, timeframe, profile).found
            except Exception:
                found = False
            if not found:
                missing.append(timeframe)
        return missing

    def build_dataset(self, command: Command) -> CommandResult:
        """Build the 5M and the 1H dataset — two matrices, one run."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        candles = max(command.integer("candles", 100_000), 1000)

        missing = self.missing_timeframes(symbol)
        if missing:
            return CommandResult.rejected(
                command.kind,
                f"No stored candles for {symbol} {', '.join(missing)}. "
                f"The platform builds one dataset per timeframe — 5M for the "
                f"signal model and 1H for the range model — and it will not "
                f"substitute generated data for either. Run 'Fetch market "
                f"data' with Timeframes = 5M,1H first.",
            )

        return self._run_script(
            command,
            [
                "scripts/run_training_dataset.py",
                "--build",
                "--symbol",
                symbol,
                "--candles",
                str(candles),
                "--storage-root",
                str(self._storage_root),
            ],
            f"Built the 5M and 1H datasets for {symbol}",
            started,
            timeout=3600,
        )

    def evaluate_model(self, command: Command) -> CommandResult:
        """Score a saved model on a chosen dataset and log the result."""
        from ShadBotTrader.application.services.model_evaluation_service import (
            ModelEvaluationService,
        )
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        started = time.monotonic()
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            return CommandResult.rejected(
                command.kind,
                "TensorFlow is not installed — run: pip install -r requirements-ai.txt",
            )

        catalogue = ModelCatalogue(self._storage_root)
        known = catalogue.choices()
        if not known:
            return CommandResult.rejected(
                command.kind,
                "No trained models yet. Use 'Train a model' first — there is " "nothing to test.",
            )

        model_id = command.text("saved_model", "").strip()
        if model_id in ("", "(none trained yet)"):
            model_id = known[0]
        if model_id not in known:
            return CommandResult.rejected(
                command.kind, f"Unknown model {model_id!r}. Available: {', '.join(known)}"
            )

        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = available[0] if available else "1H"

        service = ModelEvaluationService(self._storage_root, self._run_log_dir)
        result = service.evaluate(
            model_id=model_id,
            symbol=symbol,
            timeframe=dataset,
            max_windows=max(command.integer("max_windows", 5000), 0),
        )
        log_path = service.append_to_log(result)

        lines = [*result.summary_lines(), "", f"appended to {log_path}"]
        if result.failed:
            return CommandResult.failure(
                command.kind,
                f"Could not test {model_id} on {dataset}",
                "\n".join(lines),
                time.monotonic() - started,
            )
        return CommandResult.success(
            command.kind,
            f"{model_id} on {symbol} {dataset}: {result.headline}",
            lines,
            time.monotonic() - started,
        )

    def inspect_dataset(self, command: Command) -> CommandResult:
        """Describe a stored dataset: shape, columns, model input."""
        from ShadBotTrader.infrastructure.ai.model_diagram import describe_input_matrix
        from ShadBotTrader.presentation.gateway.data_inspector import DataInspector

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = available[0] if available else "1H"
        window = max(command.integer("window", 500), 2)

        inspector = DataInspector(self._storage_root)
        candles = inspector.candles(symbol, dataset)
        matrix = inspector.training_matrix(symbol, dataset)

        candle_count = getattr(candles, "count", 0) or 0
        lines: List[str] = [
            f"symbol / dataset : {symbol} {dataset}",
            f"candles stored   : {candle_count:,}",
        ]
        first = getattr(candles, "first_time", "")
        last = getattr(candles, "last_time", "")
        if first or last:
            lines.append(f"range            : {first} .. {last}")
        low = getattr(candles, "price_low", None)
        high = getattr(candles, "price_high", None)
        if low is not None and high is not None:
            lines.append(f"price range      : {low} .. {high}")

        if not matrix.exists:
            lines.extend(
                [
                    "",
                    "No training matrix yet for this dataset.",
                    "Run 'Build training dataset' to create it.",
                ]
            )
            return CommandResult.success(
                command.kind,
                f"{symbol} {dataset}: {candle_count:,} candles, no matrix yet",
                lines,
                time.monotonic() - started,
            )

        # ColumnInfo objects, not dicts — ask them directly rather than
        # guessing at a mapping shape.
        kinds: Dict[str, int] = {}
        constant: List[str] = []
        incomplete: List[str] = []
        for column in matrix.columns:
            kind = str(getattr(column, "kind", "?"))
            kinds[kind] = kinds.get(kind, 0) + 1
            if getattr(column, "is_constant", False):
                constant.append(str(getattr(column, "name", "?")))
            if not getattr(column, "is_complete", True):
                incomplete.append(str(getattr(column, "name", "?")))

        width = len(matrix.columns)
        lines.append("")
        lines.extend(describe_input_matrix(matrix.rows, width, window, horizon=5))
        lines.append("")
        lines.append("columns by kind:")
        for kind in sorted(kinds):
            lines.append(f"    {kind:<14}: {kinds[kind]}")

        if matrix.digest:
            lines.append("")
            lines.append(f"digest   : {matrix.digest}")
        if matrix.built_at:
            lines.append(f"built at : {matrix.built_at}")
        if constant:
            lines.append("")
            lines.append(
                f"constant columns ({len(constant)}): {', '.join(constant[:6])}"
                + (" ..." if len(constant) > 6 else "")
            )
        if incomplete:
            lines.append(f"incomplete columns: {', '.join(incomplete[:6])}")
        for warning in matrix.warnings[:5]:
            lines.append(f"[!] {warning}")

        lines.append("")
        lines.append("See the candles as a chart: open /data")

        return CommandResult.success(
            command.kind,
            f"{symbol} {dataset}: matrix {matrix.rows:,} x {width}",
            lines,
            time.monotonic() - started,
        )

    def build_timeframe(self, command: Command) -> CommandResult:
        """Aggregate a stored series into a larger timeframe (Phase 39).

        The daily model needs daily candles. A broker usually serves them
        directly, but an operator who already downloaded years of 1H
        history should not have to download it all again to train a 1D
        model — the daily bar is fully determined by the hours inside it.
        """
        from ShadBotTrader.application.services.dataset_update_service import (
            DatasetUpdateService,
        )
        from ShadBotTrader.data_cli import build_service
        from ShadBotTrader.domain.market.resample import resample_candles
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol

        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        source = command.text("source", "1H").strip().upper()
        target = command.text("target", "1D").strip().upper()

        _, store, _ = build_service(self._storage_root)
        resolved = resolve_stored_symbol(store, symbol, source)
        if not resolved.found:
            return CommandResult.rejected(
                command.kind,
                f"No stored {source} candles for {symbol}. Fetch them first.",
            )

        candles = store.query(Symbol(resolved.resolved), Timeframe(source))
        try:
            outcome = resample_candles(candles, target, source=source)
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Could not aggregate", str(error), time.monotonic() - started
            )

        if not outcome.candles:
            return CommandResult.failure(
                command.kind,
                "Nothing to store",
                f"Every {target} bucket was incomplete.",
                time.monotonic() - started,
            )

        updater = DatasetUpdateService(store, max_candles=200_000)
        update = updater.update(symbol, target, outcome.candles, allow_gap=True, backfill=False)

        lines = [
            f"source : {symbol} {source}",
            f"target : {symbol} {target}",
            *outcome.summary_lines(),
            "",
            *update.summary_lines(),
            "",
            f"Now run 'Update features' and 'Build training dataset' for {target}.",
        ]
        if update.refused:
            return CommandResult.failure(
                command.kind,
                "Storing the aggregate was refused",
                "\n".join(lines),
                time.monotonic() - started,
            )
        return CommandResult.success(
            command.kind,
            f"{symbol}: {outcome.count:,} {target} candles from {outcome.source_count:,} {source}",
            lines,
            time.monotonic() - started,
        )

    def weekly_update(self, command: Command) -> CommandResult:
        started = time.monotonic()
        arguments = [
            "scripts/run_weekly_update.py",
            "--symbol",
            command.text("symbol", "XAUUSD"),
            "--candles",
            str(max(command.integer("candles", 100_000), 1000)),
            "--db",
            str(self._database_path),
            "--storage-root",
            str(self._storage_root),
        ]
        if command.text("force", "0").strip() == "1":
            arguments.append("--force")
        return self._run_script(command, arguments, "Weekly update finished", started, timeout=7200)

    # -- AI -------------------------------------------------------------------
    def train_dual_models(self, command: Command) -> CommandResult:
        """Train one kind of model on one stored dataset (Phase 40)."""
        started = time.monotonic()
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            return CommandResult.rejected(
                command.kind,
                "TensorFlow is not installed — run: pip install -r requirements-ai.txt",
            )

        role = command.text("model", "range").strip().lower() or "range"
        if role not in MODEL_ROLE_CHOICES:
            return CommandResult.rejected(
                command.kind,
                f"Unknown model type {role!r}. Choose one of: " f"{', '.join(MODEL_ROLE_CHOICES)}",
            )

        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = available[0] if available else "1H"
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available)}",
            )
        model_id = f"gold_{role}_{dataset.lower()}"
        # LR: اگه کاربر عدد داده از همون استفاده کن، وگرنه از saved
        _lr_manual = command.number("learning_rate", 0.0)
        learning_rate = (
            float(_lr_manual)
            if _lr_manual and _lr_manual > 0
            else saved_learning_rate(self._storage_root, model_id)
        )
        # فاز ۶۲: پیچ‌های معماری + اندازهٔ ولیدیشن — 0 یعنی «پیش‌فرض/auto»
        # و فلگ به اسکریپت پاس نمی‌شود تا رفتار پیش‌فرض فاز ۵۹/۶۱ برقرار بماند.
        _n_layers = max(command.integer("n_layers", 0), 0)
        _n_blocks = max(command.integer("n_blocks", 0), 0)
        _val_size = max(command.integer("val_size", 0), 0)
        _arch_args = []
        if _n_layers:
            _arch_args += ["--n-layers", str(_n_layers)]
        if _n_blocks:
            _arch_args += ["--n-blocks", str(_n_blocks)]
        if _val_size:
            _arch_args += ["--val-size", str(_val_size)]
        # فاز ۷۴: patienceها (0 = auto) و فاز ۸۰: horizon رنج
        _es_p = max(command.integer("es_patience", 0), 0)
        _rlr_p = max(command.integer("rlr_patience", 0), 0)
        if _es_p:
            _arch_args += ["--es-patience", str(_es_p)]
        if _rlr_p:
            _arch_args += ["--rlr-patience", str(_rlr_p)]
        _rng_h = max(command.integer("range_horizon", 1), 1)
        if role in ("range", "all") and _rng_h != 1:
            _arch_args += ["--horizon", str(_rng_h)]
        return self._run_script(
            command,
            [
                "scripts/run_dual_models.py",
                "--with-features",
                "--symbol",
                command.text("symbol", "XAUUSD"),
                "--model",
                role,
                # One dataset choice drives whichever model was picked.
                # 'all' trains both, so the chosen dataset feeds the range
                # model and the signal model keeps its own 5M default —
                # a signal model on daily candles is a different product,
                # not a variation.
                # فاز ۹۸: trend هم تایم‌فریمش از «Dataset» می‌آید —
                # اسکریپت برای trend اول range_timeframes را می‌خواند.
                "--range-timeframes",
                dataset,
                "--signal-timeframe",
                dataset if role in ("signal", "trend", "trend_signal") else "5M",
                "--epochs",
                str(max(command.integer("epochs", 1), 1)),
                "--folds",
                str(max(command.integer("folds", 2), 1)),
                "--window",
                str(max(command.integer("window", 500), 2)),
                *(
                    ["--label-horizon", str(max(command.integer("label_horizon", 288), 1))]
                    if role == "trend_signal"
                    else []
                ),
                "--train-ratio",
                str(command.number("train_ratio", 100.0)),
                "--threshold",
                str(
                    percent_to_fraction(command.text("threshold_pct", "0.08"), 0.0008)
                    if role == "signal"
                    else (
                        max(0.05, command.number("atr_mult", 0.5))
                        if role == "trend_signal"
                        else 0.0
                    )
                ),
                "--learning-rate",
                str(learning_rate),
                "--storage-root",
                str(self._storage_root),
                *_arch_args,
            ],
            f"Trained {role} on {dataset} "
            f"(LR {learning_rate:.2e}"
            f"{' — manual' if (_lr_manual and _lr_manual > 0) else ' — auto/saved'})",
            started,
            timeout=max(command.integer("timeout_minutes", 480), 5) * 60,
        )

    # -- AI -------------------------------------------------------------------
    def optimise_learning_rate(self, command: Command) -> CommandResult:
        """Sweep candidate learning rates, then train/save the winner."""
        started = time.monotonic()
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            return CommandResult.rejected(
                command.kind,
                "TensorFlow is not installed — run: pip install -r requirements-ai.txt",
            )

        role = command.text("model", "signal").strip().lower()
        if role not in {"signal", "range", "trend", "trend_signal"}:
            return CommandResult.rejected(
                command.kind, "Model type must be signal, range, trend or trend_signal"
            )

        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            preferred = {
                "signal": "5M",
                "range": "1H",
                "trend": "1D",
                "trend_signal": "5M",  # فاز ۹۹: پنجرهٔ 288 کندل 5M
            }.get(role, "1H")
            dataset = preferred if preferred in available else (available[0] if available else "")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        if role == "signal":
            threshold = percent_to_fraction(command.text("threshold_pct", "0.08"), 0.0008)
        elif role == "trend_signal":
            # فاز ۹۹: X برحسب ATR14 (نه درصد)
            threshold = max(0.05, command.number("atr_mult", 0.5))
        else:
            threshold = 0.0  # trend رنگ
        # فاز ۶۲: پیچ‌های معماری — 0 = پیش‌فرض نقش (فاز ۶۱)
        _opt_layers = max(command.integer("n_layers", 0), 0)
        _opt_blocks = max(command.integer("n_blocks", 0), 0)
        _opt_arch = []
        if _opt_layers:
            _opt_arch += ["--n-layers", str(_opt_layers)]
        if _opt_blocks:
            _opt_arch += ["--n-blocks", str(_opt_blocks)]
        arguments = [
            "scripts/run_dual_models.py",
            "--with-features",
            "--symbol",
            command.text("symbol", "XAUUSD"),
            "--model",
            role,
            "--range-timeframes",
            dataset if role == "range" else "1H",
            "--signal-timeframe",
            dataset if role in ("signal", "trend") else "5M",
            "--threshold",
            str(threshold),
            "--window",
            str(max(command.integer("window", 100), 2)),
            *_opt_arch,
            "--train-ratio",
            str(command.number("train_ratio", 100.0)),
            "--learning-rates",
            command.text("learning_rates", "1e-5,3e-5,1e-4,3e-4,1e-3"),
            "--tune-learning-rate",
            "--lr-search-epochs",
            str(max(command.integer("pilot_epochs", 1), 1)),
            "--lr-search-folds",
            str(max(command.integer("pilot_folds", 1), 1)),
            "--epochs",
            str(max(command.integer("final_epochs", 3), 1)),
            "--folds",
            str(max(command.integer("final_folds", 2), 1)),
            "--storage-root",
            str(self._storage_root),
        ]
        return self._run_script(
            command,
            arguments,
            f"Selected and trained the best learning rate for {role} on {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 480), 5) * 60,
        )

    # -- trading ---------------------------------------------------------------
    def run_execution_demo(self, command: Command) -> CommandResult:
        started = time.monotonic()
        return self._run_script(
            command, ["scripts/run_execution.py"], "Execution demo finished", started
        )

    def run_live_tick(self, command: Command) -> CommandResult:
        started = time.monotonic()
        return self._run_script(
            command,
            [
                "scripts/run_live_loop.py",
                "--demo",
                "--ticks",
                "1",
                "--symbol",
                command.text("symbol", "XAUUSD"),
                "--storage-root",
                str(self._storage_root),
            ],
            "Live tick complete",
            started,
            timeout=1800,
        )

    # -- operations --------------------------------------------------------------
    def backup_database(self, command: Command) -> CommandResult:
        from ShadBotTrader.infrastructure.deployment.backup import BackupService

        started = time.monotonic()
        if not self._database_path.exists():
            return CommandResult.rejected(
                command.kind, f"No database at {self._database_path} to back up."
            )
        try:
            record = BackupService(self._database_path).create(
                note=command.text("note", "manual backup")
            )
        except Exception as error:
            return CommandResult.failure(
                command.kind, "Backup failed", str(error), time.monotonic() - started
            )
        return CommandResult.success(
            command.kind,
            f"Backed up {record.total_rows:,} rows",
            [
                f"file    : {Path(record.path).name}",
                f"size    : {record.size_kb:.1f} KB",
                f"schema  : v{record.schema_version}",
                f"verified: {record.verified}",
            ],
            time.monotonic() - started,
        )

    def health_check(self, command: Command) -> CommandResult:
        from ShadBotTrader import __version__
        from ShadBotTrader.infrastructure.deployment.health_checks import default_monitor

        started = time.monotonic()
        report = default_monitor(
            version=__version__,
            environment="development",
            database_path=(str(self._database_path) if self._database_path.exists() else None),
            storage_root=str(self._storage_root),
        ).run()

        message = f"{report.status.value} — ready={report.is_ready}"
        if report.is_ready:
            return CommandResult.success(
                command.kind, message, report.summary_lines(), time.monotonic() - started
            )
        # An unhealthy result must still show WHICH check failed. Putting
        # the detail only in `detail` left the GUI showing an empty box —
        # exactly when the operator most needs to see something.
        return CommandResult(
            kind=command.kind,
            status=CommandStatus.FAILED,
            message=message,
            detail="Fix the failing critical dependency before running anything.",
            lines=report.summary_lines(),
            duration_seconds=time.monotonic() - started,
        )

    # -- shared ------------------------------------------------------------------
