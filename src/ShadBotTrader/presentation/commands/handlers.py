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
from dataclasses import replace
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
MODEL_ROLE_CHOICES: tuple[str, ...] = (
    "all",
    "range",
    "signal",
    "trend",
    "trend_signal",
    "trend_score",
)
TREND_SCORE_LOSS_CHOICES: tuple[str, ...] = ("composite", "mae")
CLASS_WEIGHT_CHOICES: tuple[str, ...] = ("auto", "off")
BOOSTER_CHOICES: tuple[str, ...] = ("auto", "lightgbm", "xgboost", "catboost")
BOOSTER_OUTPUT_CHOICES: tuple[str, ...] = ("multiclass", "buy", "sell")
WINDOW_SUMMARY_CHOICES: tuple[str, ...] = ("last", "basic", "multi_scale")
SCORE_METRIC_CHOICES: tuple[str, ...] = (
    "total_pnl",
    "profit_factor",
    "precision_then_pnl",
    "winrate_then_pnl",
)
MONITOR_METRIC_CHOICES: tuple[str, ...] = (
    "auto",
    "val_loss",
    "val_mae",
    "val_macro_f1",
    "val_buy_sell_f1",
    "val_action_min_f1",
    "val_action_min_f1_supported",
)


def trend_signal_class_weight_args(command: Command, role: str) -> List[str]:
    """CLI args for balanced trend_signal class weights."""
    if role != "trend_signal":
        return []
    mode = command.text("class_weight", "auto").strip().lower() or "auto"
    if mode not in CLASS_WEIGHT_CHOICES:
        mode = "auto"
    return ["--class-weight", mode]


def trend_score_loss_args(command: Command, role: str) -> List[str]:
    """CLI args for the optional trend_score MAE objective.

    The knob is intentionally role-gated: range models keep their proven
    composite RangeLoss unless the operator is explicitly training the
    trend_score model.
    """
    if role != "trend_score":
        return []
    loss = command.text("trend_score_loss", "composite").strip().lower() or "composite"
    if loss not in TREND_SCORE_LOSS_CHOICES:
        loss = "composite"
    return ["--trend-score-loss", loss]


def monitor_metric_args(command: Command, role: str) -> List[str]:
    """CLI args for choosing the checkpoint/early-stop metric.

    The dashboard exposes this as an advanced knob. It is intentionally
    role-gated so an operator cannot accidentally ask a range model to
    monitor a classification-only metric that will never be emitted.
    """
    metric = command.text("monitor_metric", "auto").strip().lower() or "auto"
    if metric not in MONITOR_METRIC_CHOICES or metric == "auto":
        return []
    allowed_by_role = {
        "trend_signal": {
            "val_loss",
            "val_macro_f1",
            "val_buy_sell_f1",
            "val_action_min_f1",
            "val_action_min_f1_supported",
        },
        "trend_score": {"val_loss", "val_mae"},
        "trend": {"val_loss"},
        "signal": {"val_loss"},
        "range": {"val_loss"},
        "all": {"val_loss"},
    }
    if metric not in allowed_by_role.get(role, {"val_loss"}):
        return []
    return ["--monitor-metric", metric]


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


#: Phase 119: keep the dashboard operator-friendly without deleting knobs.
#: These field names are still rendered and submitted; they are simply folded
#: under ``Advanced options`` so the default workflow shows only the controls
#: an operator normally changes.
_ADVANCED_COMMAND_FIELDS: Dict[CommandKind, set[str]] = {
    CommandKind.FETCH_MARKET_DATA: {"max_candles", "allow_gap"},
    CommandKind.AUDIT_CAUSAL_INVARIANCE: {"split_pct", "max_bars"},
    CommandKind.TRAIN_MODEL: {
        "range_horizon",
        "threshold_pct",
        "trend_score_loss",
        "monitor_metric",
        "es_patience",
        "rlr_patience",
        "n_layers",
        "n_blocks",
        "val_size",
        "timeout_minutes",
    },
    CommandKind.RUN_BACKTEST: {
        "mode",
        "signal_model",
        "range_model",
        "threshold_pct",
        "signal_window",
        "range_window",
        "reward_risk_multiplier",
        "commission",
        "filter_zero_bar",
        "test_ratio",
        "capital",
        "quantity",
        "spread_mode",
        "spread_value",
        "slippage",
        "same_bar_policy",
        "last_n_candles",
        "session_filter",
        "slope_mode",
        "max_entry_distance_atr",
        "min_sl_distance",
    },
    CommandKind.RECORD_REPLAY: {
        "use_last_settings",
        "mode",
        "signal_model",
        "range_model",
        "threshold_pct",
        "signal_window",
        "range_window",
        "reward_risk_multiplier",
        "commission",
        "filter_zero_bar",
        "test_ratio",
        "capital",
        "quantity",
        "spread_mode",
        "spread_value",
        "slippage",
        "same_bar_policy",
        "last_n_candles",
        "session_filter",
        "trend_filter",
        "slope_mode",
        "max_entry_distance_atr",
        "min_sl_distance",
    },
    CommandKind.AUDIT_TREND_SIGNAL: {"val_size", "model_id", "max_windows", "timeout_minutes"},
    CommandKind.CALIBRATE_TREND_SIGNAL: {
        "model_id",
        "scope",
        "threshold_min",
        "threshold_max",
        "threshold_step",
        "min_margin",
        "min_trades",
        "precision_floor",
        "max_windows",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.TRAIN_DUAL_MODELS: {
        "range_horizon",
        "threshold_pct",
        "trend_score_loss",
        "monitor_metric",
        "es_patience",
        "rlr_patience",
        "n_layers",
        "n_blocks",
        "val_size",
        "timeout_minutes",
    },
    CommandKind.TRAIN_TREND_SIGNAL_BOOSTER: {
        "summary_mode",
        "folds",
        "val_size",
        "class_weight",
        "n_estimators",
        "booster_lr",
        "max_depth",
        "num_leaves",
        "max_samples",
        "timeout_minutes",
    },
    CommandKind.CALIBRATE_TREND_SIGNAL_BOOSTERS: {
        "buy_model_id",
        "sell_model_id",
        "buy_model_version",
        "sell_model_version",
        "scope",
        "threshold_min",
        "threshold_max",
        "threshold_step",
        "min_margin",
        "min_trades",
        "min_side_trades",
        "precision_floor",
        "max_windows",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.BUILD_HYBRID_XGBOOST_MATRIX: {
        "scope",
        "folds",
        "val_size",
        "max_windows",
        "include_tabular_summary",
        "include_multiclass_booster",
        "include_specialists",
        "include_wavenet",
        "require_wavenet",
        "include_range",
        "require_range",
        "buy_model_id",
        "sell_model_id",
        "multiclass_model_id",
        "wavenet_model_id",
        "range_1d_model_id",
        "range_4h_model_id",
        "buy_model_version",
        "sell_model_version",
        "multiclass_model_version",
        "wavenet_model_version",
        "range_1d_version",
        "range_4h_version",
        "output_name",
        "timeout_minutes",
    },
    CommandKind.BACKTEST_HYBRID_XGBOOST_HEAD: {
        "matrix_path",
        "model_id",
        "model_version",
        "eval_frac",
        "threshold_min",
        "threshold_max",
        "threshold_step",
        "min_margin",
        "min_trades",
        "precision_floor",
        "min_profit_factor",
        "score_metric",
        "max_hold_bars",
        "min_4h_room",
        "min_1d_room",
        "min_tp_distance",
        "min_sl_distance",
        "spread_mode",
        "spread_value",
        "slippage",
        "same_bar_policy",
        "max_windows",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.CHECK_HYBRID_SIGNIFICANCE: {
        "matrix_path",
        "model_version",
        "eval_frac",
        "buy_threshold",
        "sell_threshold",
        "min_margin",
        "max_hold_bars",
        "min_4h_room",
        "min_1d_room",
        "min_tp_distance",
        "min_sl_distance",
        "spread_mode",
        "spread_value",
        "slippage",
        "same_bar_policy",
        "max_windows",
        "white_check",
        "candidate_rows_path",
        "white_max_candidates",
        "timeout_minutes",
    },
    CommandKind.AUDIT_HYBRID_RANGE_AWARE_DECISIONS: {
        "matrix_path",
        "model_version",
        "eval_frac",
        "max_windows",
        "buy_threshold",
        "sell_threshold",
        "min_margin",
        "min_4h_room",
        "min_1d_room",
        "min_tp_distance",
        "min_sl_distance",
        "spread_mode",
        "spread_value",
        "slippage",
        "capital",
        "base_quantity",
        "timeout_minutes",
    },
    CommandKind.REPORT_HYBRID_FULL_BACKTEST: {
        "source_mode",
        "matrix_path",
        "model_version",
        "eval_frac",
        "max_windows",
        "stream_scope",
        "stream_chunk_size",
        "stream_wavenet",
        "buy_threshold",
        "sell_threshold",
        "min_margin",
        "max_hold_bars",
        "min_4h_room",
        "min_1d_room",
        "min_tp_distance",
        "min_sl_distance",
        "spread_mode",
        "spread_value",
        "slippage",
        "initial_capital",
        "units",
        "same_bar_policy",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.REPLAY_HYBRID_CHRONOLOGICAL_BACKTEST: {
        "source_mode",
        "matrix_path",
        "model_version",
        "eval_frac",
        "max_windows",
        "stream_scope",
        "stream_chunk_size",
        "stream_wavenet",
        "buy_threshold",
        "sell_threshold",
        "min_margin",
        "max_hold_bars",
        "min_4h_room",
        "min_1d_room",
        "min_tp_distance",
        "min_sl_distance",
        "spread_mode",
        "spread_value",
        "slippage",
        "initial_capital",
        "units",
        "same_bar_policy",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.BUILD_HYBRID_TELEMETRY_TENSOR: {
        "source_mode",
        "matrix_path",
        "model_version",
        "eval_frac",
        "max_windows",
        "stream_scope",
        "stream_chunk_size",
        "stream_wavenet",
        "window",
        "label_horizon",
        "atr_mult",
        "train_ratio",
        "tensor_window",
        "safe_lag_bars",
        "telemetry_lag_mode",
        "sample_stride",
        "max_samples",
        "candidate_samples_only",
        "dtype",
        "max_tensor_mb",
        "include_htf_context",
        "buy_threshold",
        "sell_threshold",
        "min_margin",
        "max_hold_bars",
        "min_4h_room",
        "min_1d_room",
        "min_tp_distance",
        "min_sl_distance",
        "spread_mode",
        "spread_value",
        "slippage",
        "same_bar_policy",
        "output_name",
        "timeout_minutes",
    },
    CommandKind.TRAIN_HYBRID_META_LABELER: {
        "flat_path",
        "model_id",
        "task",
        "target",
        "booster",
        "candidate_only",
        "train_frac",
        "val_frac",
        "min_samples",
        "class_weight",
        "n_estimators",
        "booster_lr",
        "max_depth",
        "num_leaves",
        "meta_threshold",
        "score_threshold",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.BACKTEST_HYBRID_META_LABELER: {
        "flat_path",
        "meta_model_version",
        "meta_threshold",
        "score_threshold",
        "eval_frac",
        "max_windows",
        "initial_capital",
        "units",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET: {
        "tensor_path",
        "model_id",
        "task",
        "candidate_only",
        "train_frac",
        "val_frac",
        "purge_gap",
        "max_samples",
        "batch_size",
        "epochs",
        "learning_rate",
        "filters",
        "kernel_size",
        "n_layers",
        "n_blocks",
        "dense_units",
        "dropout",
        "score_loss_weight",
        "class_weight",
        "meta_threshold",
        "score_threshold",
        "monitor_metric",
        "early_stopping_patience",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET: {
        "tensor_path",
        "flat_path",
        "model_version",
        "decision_mode",
        "meta_threshold",
        "score_threshold",
        "eval_frac",
        "max_windows",
        "initial_capital",
        "units",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.TRAIN_HYBRID_TELEMETRY_TSMIXER: {
        "tensor_path",
        "model_id",
        "task",
        "candidate_only",
        "train_frac",
        "val_frac",
        "purge_gap",
        "max_samples",
        "batch_size",
        "epochs",
        "learning_rate",
        "mixer_layers",
        "time_hidden_units",
        "feature_hidden_units",
        "dense_units",
        "dropout",
        "score_loss_weight",
        "class_weight",
        "meta_threshold",
        "score_threshold",
        "monitor_metric",
        "early_stopping_patience",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.BACKTEST_HYBRID_TELEMETRY_TSMIXER: {
        "tensor_path",
        "flat_path",
        "model_version",
        "decision_mode",
        "meta_threshold",
        "score_threshold",
        "eval_frac",
        "max_windows",
        "initial_capital",
        "units",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.TRAIN_HYBRID_TELEMETRY_PATCHTST: {
        "tensor_path",
        "model_id",
        "task",
        "candidate_only",
        "train_frac",
        "val_frac",
        "purge_gap",
        "max_samples",
        "batch_size",
        "epochs",
        "learning_rate",
        "patch_len",
        "stride",
        "d_model",
        "layers",
        "heads",
        "ff_units",
        "dense_units",
        "dropout",
        "score_loss_weight",
        "class_weight",
        "meta_threshold",
        "score_threshold",
        "monitor_metric",
        "early_stopping_patience",
        "save_record",
        "timeout_minutes",
    },
    CommandKind.BACKTEST_HYBRID_TELEMETRY_PATCHTST: {
        "tensor_path",
        "flat_path",
        "model_version",
        "decision_mode",
        "meta_threshold",
        "score_threshold",
        "eval_frac",
        "max_windows",
        "initial_capital",
        "units",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.BACKTEST_META_FILTERED_HYBRID: {
        "flat_path",
        "tensor_path",
        "candidates",
        "candidate_versions",
        "decision_modes",
        "meta_thresholds",
        "score_thresholds",
        "eval_frac",
        "max_windows",
        "min_trades",
        "score_metric",
        "initial_capital",
        "units",
        "skip_missing",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION: {
        "flat_path",
        "model_id",
        "task",
        "target",
        "booster",
        "candidate_only",
        "start_month",
        "end_month",
        "train_months_min",
        "validation_months",
        "purge_gap_bars",
        "meta_thresholds",
        "score_thresholds",
        "min_trades",
        "score_metric",
        "class_weight",
        "n_estimators",
        "booster_lr",
        "max_depth",
        "num_leaves",
        "initial_capital",
        "units",
        "timeout_minutes",
    },
    CommandKind.VALIDATE_PRODUCTION_HYBRID_STACK: {
        "config_path",
        "mode",
        "base_model_version",
        "meta_model_id",
        "meta_model_version",
        "meta_model_type",
        "decision_mode",
        "meta_threshold",
        "score_threshold",
        "range_1d_model_id",
        "range_1d_version",
        "range_4h_model_id",
        "range_4h_version",
        "telemetry_flat_path",
        "telemetry_tensor_path",
        "telemetry_schema_hash",
        "max_daily_loss_percent",
        "max_open_positions",
        "position_size_units",
        "initial_capital",
        "paper_shadow_passed",
        "account_profile_confirmed",
        "symbol_mapping_confirmed",
        "kill_switch_enabled",
        "explicit_live_confirm",
        "write_config",
        "require_models",
        "timeout_minutes",
    },
    CommandKind.RUN_HYBRID_PAPER_SHADOW: {
        "config_path",
        "flat_path",
        "eval_frac",
        "max_windows",
        "allow_validation_fail",
        "report_title",
        "timeout_minutes",
    },
    CommandKind.OPTIMISE_LEARNING_RATE: {
        "threshold_pct",
        "atr_mult",
        "class_weight",
        "label_horizon",
        "trend_score_loss",
        "monitor_metric",
        "n_layers",
        "n_blocks",
        "timeout_minutes",
    },
}


def _with_advanced_fields(items: List[CommandDescriptor]) -> List[CommandDescriptor]:
    """Return descriptors with rarely changed fields marked as advanced."""

    marked: List[CommandDescriptor] = []
    for descriptor in items:
        advanced_names = _ADVANCED_COMMAND_FIELDS.get(descriptor.kind, set())
        if not advanced_names:
            marked.append(descriptor)
            continue
        fields = [
            replace(field, advanced=field.name in advanced_names) for field in descriptor.fields
        ]
        marked.append(replace(descriptor, fields=fields))
    return marked


def descriptors(storage_root: "str | Path" = "datasets") -> List[CommandDescriptor]:
    """Every command the dashboard offers, with its form.

    ``storage_root`` is read (never written) so the dropdowns can show
    the datasets and models that genuinely exist.
    """
    datasets = stored_dataset_choices(storage_root)
    trained = trained_model_choices(storage_root)
    items = [
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
                    "atr_mult",
                    "Trend-signal barrier (×ATR14)",
                    "0.5",
                    kind="number",
                    hint="فقط trend_signal: فاصلهٔ مانع BUY/SELL برحسب ATR14 (پیش‌فرض 0.5)",
                ),
                CommandField(
                    "class_weight",
                    "Trend-signal class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                    hint="فقط trend_signal: auto = وزن متعادل جداگانه برای هر fold train",
                ),
                CommandField(
                    "label_horizon",
                    "Trend-signal/score horizon (candles)",
                    "",
                    kind="number",
                    hint=(
                        "خالی = خودکار | trend_signal: 288 کندل 5M = یک روز | "
                        "trend_score روی 1D: خودکار = 1 یعنی score از کندل واقعی فردا"
                    ),
                ),
                CommandField(
                    "trend_score_loss",
                    "Trend-score loss",
                    "composite",
                    kind="select",
                    options=TREND_SCORE_LOSS_CHOICES,
                    hint=(
                        "فقط trend_score: composite = 3*Huber+6*MAE+1*MSE | "
                        "mae = آموزش با MAE خالص؛ checkpoint/ES روی val_mae"
                    ),
                ),
                CommandField(
                    "monitor_metric",
                    "Monitor metric",
                    "auto",
                    kind="select",
                    options=MONITOR_METRIC_CHOICES,
                    hint=(
                        "پیشرفته: برای trend_signal بهتر است val_buy_sell_f1؛ "
                        "auto یعنی پیش‌فرض اسکریپت"
                    ),
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
            kind=CommandKind.AUDIT_TREND_SIGNAL,
            label="Audit trend-signal labels",
            description=(
                "Inspect the BUY/HOLD/SELL trend-signal target before retraining: "
                "label balance, ambiguous samples, fold geometry, baselines and, "
                "when a model exists, per-class F1/precision/recall."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                    hint="trend_signal normally uses 5M candles",
                ),
                CommandField("window", "Window rows", "288", kind="number"),
                CommandField(
                    "label_horizon",
                    "Label horizon (candles)",
                    "288",
                    kind="number",
                    hint="288×5M ≈ one trading day for the current trend_signal target",
                ),
                CommandField(
                    "atr_mult",
                    "Barrier (×daily-range proxy)",
                    "0.5",
                    kind="number",
                    hint="same distance used by trend_signal labels; e.g. 0.5",
                ),
                CommandField("folds", "Folds to audit", "3", kind="number"),
                CommandField(
                    "val_size",
                    "Validation samples per fold",
                    "0",
                    kind="number",
                    hint="0 = auto, same 10% geometry as training",
                ),
                CommandField(
                    "model_id",
                    "Model id (optional)",
                    "",
                    hint="empty = gold_trend_signal_{dataset}; scoring is skipped if missing",
                ),
                CommandField(
                    "max_windows",
                    "Score at most",
                    "5000",
                    kind="number",
                    hint="0 = all labelled windows when a trained model exists",
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "60", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.CALIBRATE_TREND_SIGNAL,
            label="Calibrate trend-signal thresholds",
            description=(
                "After training a trend_signal model, scan BUY/SELL probability "
                "thresholds and write CSV/HTML/JSON heatmaps. The selected "
                "thresholds can be saved into the model record."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField(
                    "model_id",
                    "Model id",
                    "",
                    hint="empty = gold_trend_signal_{dataset}; latest version is used",
                ),
                CommandField("window", "Window rows", "288", kind="number"),
                CommandField("label_horizon", "Label horizon", "288", kind="number"),
                CommandField("atr_mult", "Barrier", "0.5", kind="number"),
                CommandField("train_ratio", "Training prefix %", "80", kind="number"),
                CommandField(
                    "scope",
                    "Calibration scope",
                    "auto",
                    kind="select",
                    options=("auto", "holdout", "last-fold", "all"),
                    hint="auto = holdout when train_ratio < 100, otherwise last-fold",
                ),
                CommandField("threshold_min", "Threshold min", "0.35", kind="number"),
                CommandField("threshold_max", "Threshold max", "0.95", kind="number"),
                CommandField("threshold_step", "Threshold step", "0.05", kind="number"),
                CommandField("min_margin", "Min probability margin", "0", kind="number"),
                CommandField("min_trades", "Min trades", "50", kind="number"),
                CommandField("precision_floor", "Precision floor", "0", kind="number"),
                CommandField("max_windows", "Score at most", "8000", kind="number"),
                CommandField(
                    "save_record",
                    "Save thresholds to model record",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "120", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_TREND_SIGNAL_BOOSTER,
            label="Train trend-signal booster",
            description=(
                "Train a separate LightGBM/XGBoost/CatBoost branch on causal "
                "window summaries for trend_signal. This does not overwrite the "
                "WaveNet model; it creates a separate booster artifact."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField(
                    "booster",
                    "Booster",
                    "auto",
                    kind="select",
                    options=BOOSTER_CHOICES,
                    hint="auto tries LightGBM, then XGBoost, then CatBoost",
                ),
                CommandField(
                    "output_mode",
                    "Output",
                    "multiclass",
                    kind="select",
                    options=BOOSTER_OUTPUT_CHOICES,
                    hint="multiclass=SELL/HOLD/BUY; buy/sell=train specialist binary branch",
                ),
                CommandField("window", "Window rows", "288", kind="number"),
                CommandField("label_horizon", "Label horizon", "288", kind="number"),
                CommandField("atr_mult", "Barrier", "0.5", kind="number"),
                CommandField("train_ratio", "Training prefix %", "80", kind="number"),
                CommandField(
                    "summary_mode",
                    "Summary mode",
                    "basic",
                    kind="select",
                    options=WINDOW_SUMMARY_CHOICES,
                    hint="basic is the recommended first booster benchmark",
                ),
                CommandField("folds", "Folds", "3", kind="number"),
                CommandField("val_size", "Validation samples/fold", "2000", kind="number"),
                CommandField(
                    "class_weight",
                    "Class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                ),
                CommandField("n_estimators", "Trees/iterations", "400", kind="number"),
                CommandField("booster_lr", "Booster LR", "0.03", kind="number"),
                CommandField("max_depth", "Max depth", "4", kind="number"),
                CommandField("num_leaves", "LightGBM leaves", "31", kind="number"),
                CommandField("max_samples", "Max samples", "0", kind="number"),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.CALIBRATE_TREND_SIGNAL_BOOSTERS,
            label="Calibrate booster specialists",
            description=(
                "Load the BUY and SELL trend-signal booster specialists, scan "
                "probability thresholds, and save the paired decision gate."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("booster", "Booster", "lightgbm"),
                CommandField(
                    "summary_mode",
                    "Summary mode",
                    "basic",
                    kind="select",
                    options=WINDOW_SUMMARY_CHOICES,
                ),
                CommandField("window", "Window rows", "288", kind="number"),
                CommandField("label_horizon", "Label horizon", "288", kind="number"),
                CommandField("atr_mult", "Barrier", "0.5", kind="number"),
                CommandField("train_ratio", "Training prefix %", "80", kind="number"),
                CommandField(
                    "buy_model_id",
                    "BUY model id",
                    "",
                    hint="empty = gold_buy_{booster}_{summary}_{dataset}",
                ),
                CommandField(
                    "sell_model_id",
                    "SELL model id",
                    "",
                    hint="empty = gold_sell_{booster}_{summary}_{dataset}",
                ),
                CommandField("buy_model_version", "BUY version", "0", kind="number"),
                CommandField("sell_model_version", "SELL version", "0", kind="number"),
                CommandField(
                    "scope",
                    "Scope",
                    "auto",
                    kind="select",
                    options=("auto", "holdout", "last-fold", "all"),
                ),
                CommandField("threshold_min", "Threshold min", "0.35", kind="number"),
                CommandField("threshold_max", "Threshold max", "0.95", kind="number"),
                CommandField("threshold_step", "Threshold step", "0.05", kind="number"),
                CommandField("min_margin", "Min margin", "0", kind="number"),
                CommandField("min_trades", "Min trades", "50", kind="number"),
                CommandField("min_side_trades", "Min side trades", "10", kind="number"),
                CommandField("precision_floor", "Precision floor", "0", kind="number"),
                CommandField("max_windows", "Score at most", "8000", kind="number"),
                CommandField(
                    "save_record",
                    "Save to model records",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "120", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BUILD_HYBRID_XGBOOST_MATRIX,
            label="Build hybrid XGBoost matrix",
            description=(
                "Build the final XGBoost-ready matrix from booster probabilities, "
                "optional WaveNet probabilities, and 1D/4H range-model room features."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("window", "Window rows", "288", kind="number"),
                CommandField("label_horizon", "Label horizon", "288", kind="number"),
                CommandField("atr_mult", "Barrier", "0.5", kind="number"),
                CommandField("train_ratio", "Training prefix %", "80", kind="number"),
                CommandField("booster", "Booster", "lightgbm"),
                CommandField(
                    "summary_mode",
                    "Summary mode",
                    "basic",
                    kind="select",
                    options=WINDOW_SUMMARY_CHOICES,
                ),
                CommandField(
                    "scope",
                    "Scope",
                    "holdout",
                    kind="select",
                    options=("auto", "holdout", "last-fold", "all"),
                ),
                CommandField("max_windows", "Max windows", "8000", kind="number"),
                CommandField(
                    "include_specialists",
                    "Use specialists",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField(
                    "include_multiclass_booster",
                    "Use multiclass booster",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField(
                    "include_wavenet",
                    "Use WaveNet output",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField(
                    "require_wavenet",
                    "Require WaveNet",
                    "0",
                    kind="select",
                    options=("0", "1"),
                ),
                CommandField(
                    "include_range",
                    "Use range models",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField(
                    "require_range",
                    "Require range",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("buy_model_id", "BUY booster id", ""),
                CommandField("sell_model_id", "SELL booster id", ""),
                CommandField("multiclass_model_id", "Multiclass id", ""),
                CommandField("wavenet_model_id", "WaveNet id", "gold_trend_signal_5m"),
                CommandField("range_1d_model_id", "1D range id", "gold_range_1d"),
                CommandField("range_4h_model_id", "4H range id", "gold_range_4h"),
                CommandField("buy_model_version", "BUY version", "0", kind="number"),
                CommandField("sell_model_version", "SELL version", "0", kind="number"),
                CommandField("multiclass_model_version", "Multiclass version", "0", kind="number"),
                CommandField("wavenet_model_version", "WaveNet version", "0", kind="number"),
                CommandField("range_1d_version", "1D version", "0", kind="number"),
                CommandField("range_4h_version", "4H version", "0", kind="number"),
                CommandField("include_tabular_summary", "Include raw summary", "0"),
                CommandField("output_name", "Output name", "hybrid_xgboost_matrix_v1"),
                CommandField("timeout_minutes", "Give up after (minutes)", "240", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BACKTEST_HYBRID_XGBOOST_HEAD,
            label="Backtest hybrid XGBoost head",
            description=(
                "Calibrate BUY/SELL probability thresholds for the final hybrid "
                "head, then simulate TP/SL using the 4H range bracket and 1D range filter."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("model_id", "Hybrid head id", "gold_hybrid_lightgbm_head_5m"),
                CommandField("eval_frac", "Eval fraction", "0.30", kind="number"),
                CommandField("threshold_min", "Threshold min", "0.35", kind="number"),
                CommandField("threshold_max", "Threshold max", "0.95", kind="number"),
                CommandField("threshold_step", "Threshold step", "0.05", kind="number"),
                CommandField(
                    "score_metric",
                    "Score metric",
                    "total_pnl",
                    kind="select",
                    options=SCORE_METRIC_CHOICES,
                ),
                CommandField("matrix_path", "Matrix path", ""),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField("min_margin", "Min margin", "0", kind="number"),
                CommandField("min_trades", "Min trades", "30", kind="number"),
                CommandField("precision_floor", "Precision floor", "0", kind="number"),
                CommandField("min_profit_factor", "Min profit factor", "0", kind="number"),
                CommandField("max_hold_bars", "Max hold bars", "48", kind="number"),
                CommandField("min_4h_room", "Min 4H room ($)", "0", kind="number"),
                CommandField("min_1d_room", "Min 1D room ($)", "0", kind="number"),
                CommandField("min_tp_distance", "Min TP distance ($)", "1", kind="number"),
                CommandField("min_sl_distance", "Min SL distance ($)", "1", kind="number"),
                CommandField(
                    "spread_mode", "Spread type", "pct", kind="select", options=("pct", "fixed")
                ),
                CommandField("spread_value", "Spread value", "0.06", kind="number"),
                CommandField("slippage", "Slippage ($)", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField(
                    "units",
                    "PnL units",
                    "1",
                    kind="number",
                    hint="1 = one XAUUSD price-dollar move changes balance by $1",
                ),
                CommandField(
                    "same_bar_policy",
                    "Same-bar policy",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "tp_first"),
                ),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField(
                    "save_record", "Save thresholds", "1", kind="select", options=("1", "0")
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "120", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.CHECK_HYBRID_SIGNIFICANCE,
            label="Check hybrid significance",
            description=(
                "Run the Phase 113 Monte Carlo random baseline for the saved hybrid-head "
                "thresholds using the same range TP/SL, spread, slippage and eval slice."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("model_id", "Hybrid head id", "gold_hybrid_lightgbm_head_5m"),
                CommandField("trials", "Random trials", "1000", kind="number"),
                CommandField("seed", "Random seed", "42", kind="number"),
                CommandField("matrix_path", "Matrix path", ""),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "0.30", kind="number"),
                CommandField("buy_threshold", "BUY threshold", "-1", kind="number"),
                CommandField("sell_threshold", "SELL threshold", "-1", kind="number"),
                CommandField("min_margin", "Min margin", "-1", kind="number"),
                CommandField("max_hold_bars", "Max hold bars", "48", kind="number"),
                CommandField("min_4h_room", "Min 4H room ($)", "2", kind="number"),
                CommandField("min_1d_room", "Min 1D room ($)", "5", kind="number"),
                CommandField("min_tp_distance", "Min TP distance ($)", "2", kind="number"),
                CommandField("min_sl_distance", "Min SL distance ($)", "2", kind="number"),
                CommandField(
                    "spread_mode", "Spread type", "pct", kind="select", options=("pct", "fixed")
                ),
                CommandField("spread_value", "Spread value", "0.06", kind="number"),
                CommandField("slippage", "Slippage ($)", "0", kind="number"),
                CommandField(
                    "same_bar_policy",
                    "Same-bar policy",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "tp_first"),
                ),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField(
                    "white_check", "White-style max check", "1", kind="select", options=("1", "0")
                ),
                CommandField(
                    "candidate_rows_path",
                    "Phase125 rows JSON",
                    "run_logs/hybrid_head_backtest/latest.json",
                ),
                CommandField("white_max_candidates", "Max white candidates", "0", kind="number"),
                CommandField("timeout_minutes", "Give up after (minutes)", "120", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.AUDIT_HYBRID_RANGE_AWARE_DECISIONS,
            label="Audit hybrid range-aware decisions",
            description=(
                "Route the saved hybrid head thresholds through the Phase 116 strategy, "
                "decision engine, risk gate and intent factory, then write TRADE/NO_TRADE reasons."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("model_id", "Hybrid head id", "gold_hybrid_lightgbm_head_5m"),
                CommandField("matrix_path", "Matrix path", ""),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "0.30", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField("buy_threshold", "BUY threshold", "-1", kind="number"),
                CommandField("sell_threshold", "SELL threshold", "-1", kind="number"),
                CommandField("min_margin", "Min margin", "-1", kind="number"),
                CommandField("min_4h_room", "Min 4H room ($)", "2", kind="number"),
                CommandField("min_1d_room", "Min 1D room ($)", "5", kind="number"),
                CommandField("min_tp_distance", "Min TP distance ($)", "2", kind="number"),
                CommandField("min_sl_distance", "Min SL distance ($)", "2", kind="number"),
                CommandField(
                    "spread_mode", "Spread type", "pct", kind="select", options=("pct", "fixed")
                ),
                CommandField("spread_value", "Spread value", "0.06", kind="number"),
                CommandField("slippage", "Slippage ($)", "0", kind="number"),
                CommandField("capital", "Audit capital", "10000", kind="number"),
                CommandField("base_quantity", "Intent quantity", "1", kind="number"),
                CommandField("timeout_minutes", "Give up after (minutes)", "120", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.REPORT_HYBRID_FULL_BACKTEST,
            label="Full hybrid 5M backtest report",
            description=(
                "Run the saved hybrid range-aware threshold over all selected 5M matrix rows "
                "and generate an HTML report with PnL, equity curve and trades."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("model_id", "Hybrid head id", "gold_hybrid_lightgbm_head_5m"),
                CommandField(
                    "source_mode",
                    "Source mode",
                    "matrix",
                    kind="select",
                    options=("matrix", "stream"),
                    hint="stream = memory-safe full 5M evaluation without building one huge matrix",
                ),
                CommandField("matrix_path", "Matrix path", ""),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField(
                    "stream_scope",
                    "Stream scope",
                    "all",
                    kind="select",
                    options=("all", "holdout", "last-fold", "auto"),
                ),
                CommandField("stream_chunk_size", "Stream chunk rows", "2000", kind="number"),
                CommandField(
                    "stream_wavenet",
                    "Stream WaveNet",
                    "neutral",
                    kind="select",
                    options=("neutral", "batch"),
                    hint="neutral avoids the RAM spike from building one huge WaveNet tensor",
                ),
                CommandField("buy_threshold", "BUY threshold", "-1", kind="number"),
                CommandField("sell_threshold", "SELL threshold", "-1", kind="number"),
                CommandField("min_margin", "Min margin", "-1", kind="number"),
                CommandField("max_hold_bars", "Max hold bars", "48", kind="number"),
                CommandField("min_4h_room", "Min 4H room ($)", "2", kind="number"),
                CommandField("min_1d_room", "Min 1D room ($)", "5", kind="number"),
                CommandField("min_tp_distance", "Min TP distance ($)", "2", kind="number"),
                CommandField("min_sl_distance", "Min SL distance ($)", "2", kind="number"),
                CommandField(
                    "spread_mode", "Spread type", "pct", kind="select", options=("pct", "fixed")
                ),
                CommandField("spread_value", "Spread value", "0.06", kind="number"),
                CommandField("slippage", "Slippage ($)", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField(
                    "units",
                    "PnL units",
                    "1",
                    kind="number",
                    hint="1 = one XAUUSD price-dollar move changes balance by $1",
                ),
                CommandField(
                    "same_bar_policy",
                    "Same-bar policy",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "tp_first"),
                ),
                CommandField("report_title", "Report title", "Hybrid range-aware full 5M backtest"),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.REPLAY_HYBRID_CHRONOLOGICAL_BACKTEST,
            label="Chronological hybrid replay",
            description=(
                "Run the hybrid range-aware model candle-by-candle with only one open "
                "position at a time, then generate an HTML replay with entry/TP/SL/exit."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("model_id", "Hybrid head id", "gold_hybrid_lightgbm_head_5m"),
                CommandField(
                    "source_mode",
                    "Source mode",
                    "stream",
                    kind="select",
                    options=("stream", "matrix"),
                    hint="stream is the memory-safe full-history default",
                ),
                CommandField("matrix_path", "Matrix path", ""),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField(
                    "stream_scope",
                    "Stream scope",
                    "all",
                    kind="select",
                    options=("all", "holdout", "last-fold", "auto"),
                ),
                CommandField("stream_chunk_size", "Stream chunk rows", "500", kind="number"),
                CommandField(
                    "stream_wavenet",
                    "Stream WaveNet",
                    "neutral",
                    kind="select",
                    options=("neutral", "batch"),
                    hint="neutral avoids the RAM spike from building one huge WaveNet tensor",
                ),
                CommandField("buy_threshold", "BUY threshold", "-1", kind="number"),
                CommandField("sell_threshold", "SELL threshold", "-1", kind="number"),
                CommandField("min_margin", "Min margin", "-1", kind="number"),
                CommandField("max_hold_bars", "Max hold bars", "48", kind="number"),
                CommandField("min_4h_room", "Min 4H room ($)", "2", kind="number"),
                CommandField("min_1d_room", "Min 1D room ($)", "5", kind="number"),
                CommandField("min_tp_distance", "Min TP distance ($)", "2", kind="number"),
                CommandField("min_sl_distance", "Min SL distance ($)", "2", kind="number"),
                CommandField(
                    "spread_mode", "Spread type", "pct", kind="select", options=("pct", "fixed")
                ),
                CommandField("spread_value", "Spread value", "0.06", kind="number"),
                CommandField("slippage", "Slippage ($)", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField(
                    "units",
                    "PnL units",
                    "0.1",
                    kind="number",
                    hint="0.1 = one XAUUSD price-dollar move changes balance by $0.10",
                ),
                CommandField(
                    "same_bar_policy",
                    "Same-bar policy",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "tp_first"),
                ),
                CommandField(
                    "report_title",
                    "Report title",
                    "Chronological hybrid single-position replay",
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BUILD_HYBRID_TELEMETRY_TENSOR,
            label="Build hybrid telemetry tensor",
            description=(
                "Build the Phase127 causal 3D telemetry tensor with Target C, safe_lag=48, "
                "lagged backtest telemetry and aligned 4H/1D context."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("model_id", "Hybrid head id", "gold_hybrid_lightgbm_head_5m"),
                CommandField(
                    "source_mode",
                    "Source mode",
                    "matrix",
                    kind="select",
                    options=("matrix", "stream"),
                    hint="matrix is safest for first run; stream can build rows in chunks",
                ),
                CommandField("matrix_path", "Matrix path", ""),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max source rows", "0", kind="number"),
                CommandField(
                    "stream_scope",
                    "Stream scope",
                    "all",
                    kind="select",
                    options=("all", "holdout", "last-fold", "auto"),
                ),
                CommandField("stream_chunk_size", "Stream chunk rows", "500", kind="number"),
                CommandField(
                    "stream_wavenet",
                    "Stream WaveNet",
                    "neutral",
                    kind="select",
                    options=("neutral", "batch"),
                ),
                CommandField("tensor_window", "Tensor window", "150", kind="number"),
                CommandField("safe_lag_bars", "Safe lag bars", "48", kind="number"),
                CommandField(
                    "telemetry_lag_mode",
                    "Telemetry lag mode",
                    "fixed",
                    kind="select",
                    options=("fixed", "exit_closed"),
                ),
                CommandField("sample_stride", "Sample stride", "1", kind="number"),
                CommandField("max_samples", "Max tensor samples", "0", kind="number"),
                CommandField(
                    "candidate_samples_only",
                    "Candidate samples only",
                    "0",
                    kind="select",
                    options=("0", "1"),
                ),
                CommandField(
                    "dtype",
                    "Tensor dtype",
                    "float16",
                    kind="select",
                    options=("float16", "float32"),
                ),
                CommandField("max_tensor_mb", "Max tensor MB", "512", kind="number"),
                CommandField(
                    "include_htf_context",
                    "Include 4H/1D context",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("window", "Base model window", "288", kind="number"),
                CommandField("label_horizon", "Label horizon", "288", kind="number"),
                CommandField("atr_mult", "Barrier", "0.5", kind="number"),
                CommandField("train_ratio", "Training prefix %", "80", kind="number"),
                CommandField("buy_threshold", "BUY threshold", "-1", kind="number"),
                CommandField("sell_threshold", "SELL threshold", "-1", kind="number"),
                CommandField("min_margin", "Min margin", "-1", kind="number"),
                CommandField("max_hold_bars", "Max hold bars", "48", kind="number"),
                CommandField("min_4h_room", "Min 4H room ($)", "2", kind="number"),
                CommandField("min_1d_room", "Min 1D room ($)", "5", kind="number"),
                CommandField("min_tp_distance", "Min TP distance ($)", "2", kind="number"),
                CommandField("min_sl_distance", "Min SL distance ($)", "2", kind="number"),
                CommandField(
                    "spread_mode", "Spread type", "pct", kind="select", options=("pct", "fixed")
                ),
                CommandField("spread_value", "Spread value", "0.06", kind="number"),
                CommandField("slippage", "Slippage ($)", "0", kind="number"),
                CommandField(
                    "same_bar_policy",
                    "Same-bar policy",
                    "stop_first",
                    kind="select",
                    options=("stop_first", "tp_first"),
                ),
                CommandField("output_name", "Output name", "hybrid_telemetry_tensor_v1"),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_HYBRID_META_LABELER,
            label="Train hybrid meta-labeler",
            description=(
                "Train the Phase128 LightGBM/CatBoost/XGBoost meta-labeler on the "
                "causal telemetry flat matrix to filter hybrid trade candidates."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("model_id", "Meta model id", ""),
                CommandField(
                    "task",
                    "Task",
                    "classifier",
                    kind="select",
                    options=("classifier", "regressor"),
                ),
                CommandField("target", "Target column", ""),
                CommandField(
                    "booster", "Booster", "lightgbm", kind="select", options=BOOSTER_CHOICES
                ),
                CommandField(
                    "candidate_only",
                    "Candidate rows only",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("train_frac", "Train fraction", "0.70", kind="number"),
                CommandField("val_frac", "Validation fraction", "0.15", kind="number"),
                CommandField("min_samples", "Min samples", "200", kind="number"),
                CommandField(
                    "class_weight",
                    "Class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                ),
                CommandField("n_estimators", "Trees/iterations", "500", kind="number"),
                CommandField("booster_lr", "Booster LR", "0.03", kind="number"),
                CommandField("max_depth", "Max depth", "3", kind="number"),
                CommandField("num_leaves", "LightGBM leaves", "31", kind="number"),
                CommandField("meta_threshold", "Meta threshold", "0.55", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField("save_record", "Save model", "1", kind="select", options=("1", "0")),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BACKTEST_HYBRID_META_LABELER,
            label="Backtest hybrid meta-labeler",
            description=(
                "Apply the trained Phase128 meta-filter to telemetry candidates and "
                "produce chronological HTML/JSON/CSV trading reports."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("meta_model_id", "Meta model id", "gold_hybrid_meta_lightgbm_5m"),
                CommandField("meta_model_version", "Meta version", "0", kind="number"),
                CommandField("meta_threshold", "Meta threshold", "-1", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField("units", "PnL units", "0.1", kind="number"),
                CommandField(
                    "report_title", "Report title", "Meta-filtered hybrid chronological backtest"
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET,
            label="Train telemetry WaveNet/TCN",
            description=(
                "Train the Phase129 causal WaveNet/TCN on the 3D telemetry tensor "
                "to predict candidate win probability and expected R-score."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_telemetry_wavenet_5m"),
                CommandField(
                    "task",
                    "Task",
                    "multihead",
                    kind="select",
                    options=("multihead", "classifier", "regressor"),
                ),
                CommandField(
                    "candidate_only",
                    "Candidate samples only",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("train_frac", "Train fraction", "0.70", kind="number"),
                CommandField("val_frac", "Validation fraction", "0.15", kind="number"),
                CommandField("purge_gap", "Purge gap", "336", kind="number"),
                CommandField("max_samples", "Max samples", "0", kind="number"),
                CommandField("batch_size", "Batch size", "64", kind="number"),
                CommandField("epochs", "Epochs", "30", kind="number"),
                CommandField("learning_rate", "Learning rate", "0.001", kind="number"),
                CommandField("filters", "Conv filters", "48", kind="number"),
                CommandField("kernel_size", "Kernel size", "3", kind="number"),
                CommandField("n_layers", "Dilation layers", "5", kind="number"),
                CommandField("n_blocks", "Residual blocks", "2", kind="number"),
                CommandField("dense_units", "Dense units", "64", kind="number"),
                CommandField("dropout", "Dropout", "0.20", kind="number"),
                CommandField("score_loss_weight", "Score loss weight", "0.50", kind="number"),
                CommandField(
                    "class_weight",
                    "Class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                ),
                CommandField("meta_threshold", "Meta threshold", "0.55", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField(
                    "monitor_metric",
                    "Monitor metric",
                    "auto",
                    kind="select",
                    options=(
                        "auto",
                        "val_loss",
                        "val_meta_win_ap",
                        "val_meta_win_precision",
                        "val_score_r_mae",
                    ),
                ),
                CommandField("early_stopping_patience", "Early stop patience", "8", kind="number"),
                CommandField("save_record", "Save model", "1", kind="select", options=("1", "0")),
                CommandField("timeout_minutes", "Give up after (minutes)", "240", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET,
            label="Backtest telemetry WaveNet/TCN",
            description=(
                "Apply the trained Phase129 WaveNet/TCN as a meta-filter and write "
                "chronological HTML/JSON/CSV trading reports."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_telemetry_wavenet_5m"),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField(
                    "decision_mode",
                    "Decision mode",
                    "meta",
                    kind="select",
                    options=("meta", "score", "both"),
                ),
                CommandField("meta_threshold", "Meta threshold", "-1", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField("units", "PnL units", "0.1", kind="number"),
                CommandField(
                    "report_title", "Report title", "Telemetry WaveNet filtered hybrid replay"
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_HYBRID_TELEMETRY_TSMIXER,
            label="Train telemetry TSMixer",
            description=(
                "Train the Phase130 TSMixer benchmark on the 3D telemetry tensor with "
                "time-mixing and feature-mixing MLP blocks."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_telemetry_tsmixer_5m"),
                CommandField(
                    "task",
                    "Task",
                    "multihead",
                    kind="select",
                    options=("multihead", "classifier", "regressor"),
                ),
                CommandField(
                    "candidate_only",
                    "Candidate samples only",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("train_frac", "Train fraction", "0.70", kind="number"),
                CommandField("val_frac", "Validation fraction", "0.15", kind="number"),
                CommandField("purge_gap", "Purge gap", "336", kind="number"),
                CommandField("max_samples", "Max samples", "0", kind="number"),
                CommandField("batch_size", "Batch size", "64", kind="number"),
                CommandField("epochs", "Epochs", "30", kind="number"),
                CommandField("learning_rate", "Learning rate", "0.001", kind="number"),
                CommandField("mixer_layers", "Mixer layers", "4", kind="number"),
                CommandField("time_hidden_units", "Time hidden units", "64", kind="number"),
                CommandField("feature_hidden_units", "Feature hidden units", "128", kind="number"),
                CommandField("dense_units", "Dense units", "64", kind="number"),
                CommandField("dropout", "Dropout", "0.20", kind="number"),
                CommandField("score_loss_weight", "Score loss weight", "0.50", kind="number"),
                CommandField(
                    "class_weight",
                    "Class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                ),
                CommandField("meta_threshold", "Meta threshold", "0.55", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField(
                    "monitor_metric",
                    "Monitor metric",
                    "auto",
                    kind="select",
                    options=(
                        "auto",
                        "val_loss",
                        "val_meta_win_ap",
                        "val_meta_win_precision",
                        "val_score_r_mae",
                    ),
                ),
                CommandField("early_stopping_patience", "Early stop patience", "8", kind="number"),
                CommandField("save_record", "Save model", "1", kind="select", options=("1", "0")),
                CommandField("timeout_minutes", "Give up after (minutes)", "240", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BACKTEST_HYBRID_TELEMETRY_TSMIXER,
            label="Backtest telemetry TSMixer",
            description=(
                "Apply the trained Phase130 TSMixer as a meta-filter and write "
                "chronological HTML/JSON/CSV trading reports."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_telemetry_tsmixer_5m"),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField(
                    "decision_mode",
                    "Decision mode",
                    "meta",
                    kind="select",
                    options=("meta", "score", "both"),
                ),
                CommandField("meta_threshold", "Meta threshold", "-1", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField("units", "PnL units", "0.1", kind="number"),
                CommandField(
                    "report_title", "Report title", "Telemetry TSMixer filtered hybrid replay"
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.TRAIN_HYBRID_TELEMETRY_PATCHTST,
            label="Train telemetry PatchTST",
            description=(
                "Train the Phase131 PatchTST benchmark on the 3D telemetry tensor with "
                "temporal patches and Transformer encoder blocks."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_telemetry_patchtst_5m"),
                CommandField(
                    "task",
                    "Task",
                    "multihead",
                    kind="select",
                    options=("multihead", "classifier", "regressor"),
                ),
                CommandField(
                    "candidate_only",
                    "Candidate samples only",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("train_frac", "Train fraction", "0.70", kind="number"),
                CommandField("val_frac", "Validation fraction", "0.15", kind="number"),
                CommandField("purge_gap", "Purge gap", "336", kind="number"),
                CommandField("max_samples", "Max samples", "0", kind="number"),
                CommandField("batch_size", "Batch size", "64", kind="number"),
                CommandField("epochs", "Epochs", "30", kind="number"),
                CommandField("learning_rate", "Learning rate", "0.001", kind="number"),
                CommandField("patch_len", "Patch length", "16", kind="number"),
                CommandField("stride", "Patch stride", "8", kind="number"),
                CommandField("d_model", "Model width", "64", kind="number"),
                CommandField("layers", "Transformer layers", "3", kind="number"),
                CommandField("heads", "Attention heads", "4", kind="number"),
                CommandField("ff_units", "Feed-forward units", "128", kind="number"),
                CommandField("dense_units", "Dense units", "64", kind="number"),
                CommandField("dropout", "Dropout", "0.20", kind="number"),
                CommandField("score_loss_weight", "Score loss weight", "0.50", kind="number"),
                CommandField(
                    "class_weight",
                    "Class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                ),
                CommandField("meta_threshold", "Meta threshold", "0.55", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField(
                    "monitor_metric",
                    "Monitor metric",
                    "auto",
                    kind="select",
                    options=(
                        "auto",
                        "val_loss",
                        "val_meta_win_ap",
                        "val_meta_win_precision",
                        "val_score_r_mae",
                    ),
                ),
                CommandField("early_stopping_patience", "Early stop patience", "8", kind="number"),
                CommandField("save_record", "Save model", "1", kind="select", options=("1", "0")),
                CommandField("timeout_minutes", "Give up after (minutes)", "240", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BACKTEST_HYBRID_TELEMETRY_PATCHTST,
            label="Backtest telemetry PatchTST",
            description=(
                "Apply the trained Phase131 PatchTST as a meta-filter and write "
                "chronological HTML/JSON/CSV trading reports."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_telemetry_patchtst_5m"),
                CommandField("model_version", "Model version", "0", kind="number"),
                CommandField(
                    "decision_mode",
                    "Decision mode",
                    "meta",
                    kind="select",
                    options=("meta", "score", "both"),
                ),
                CommandField("meta_threshold", "Meta threshold", "-1", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField("units", "PnL units", "0.1", kind="number"),
                CommandField(
                    "report_title", "Report title", "Telemetry PatchTST filtered hybrid replay"
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.BACKTEST_META_FILTERED_HYBRID,
            label="Backtest meta-filtered hybrid",
            description=(
                "Compare base hybrid candidates against every trained telemetry meta-filter "
                "on the same chronological single-position replay."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("tensor_path", "Telemetry tensor path", ""),
                CommandField(
                    "candidates",
                    "Candidates",
                    "base,gold_hybrid_meta_lightgbm_5m,gold_hybrid_telemetry_wavenet_5m,gold_hybrid_telemetry_tsmixer_5m,gold_hybrid_telemetry_patchtst_5m",
                ),
                CommandField("candidate_versions", "Candidate versions", "0"),
                CommandField("decision_modes", "Decision modes", "meta"),
                CommandField("meta_thresholds", "Meta thresholds", "record"),
                CommandField("score_thresholds", "Score thresholds", "0"),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField("min_trades", "Min trades", "10", kind="number"),
                CommandField(
                    "score_metric",
                    "Score metric",
                    "total_pnl",
                    kind="select",
                    options=("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted"),
                ),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField("units", "PnL units", "0.1", kind="number"),
                CommandField(
                    "skip_missing", "Skip missing models", "1", kind="select", options=("1", "0")
                ),
                CommandField("report_title", "Report title", "Hybrid meta-filter comparison"),
                CommandField("timeout_minutes", "Give up after (minutes)", "180", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION,
            label="Run hybrid walk-forward validation",
            description=(
                "Train a flat telemetry meta-labeler only on past months, calibrate on "
                "past validation months, and test the next unseen month without leakage."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("model_id", "Model id", "gold_hybrid_meta_walkforward_5m"),
                CommandField(
                    "task",
                    "Task",
                    "classifier",
                    kind="select",
                    options=("classifier", "regressor"),
                ),
                CommandField("target", "Target column", ""),
                CommandField(
                    "booster", "Booster", "lightgbm", kind="select", options=BOOSTER_CHOICES
                ),
                CommandField(
                    "candidate_only",
                    "Candidate rows only",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("start_month", "Start month", ""),
                CommandField("end_month", "End month", ""),
                CommandField("train_months_min", "Min train months", "3", kind="number"),
                CommandField("validation_months", "Validation months", "1", kind="number"),
                CommandField("purge_gap_bars", "Purge gap bars", "336", kind="number"),
                CommandField(
                    "meta_thresholds", "Meta threshold grid", "0.45,0.50,0.55,0.60,0.65,0.70"
                ),
                CommandField("score_thresholds", "Score threshold grid", "0,0.05,0.10,0.20"),
                CommandField("min_trades", "Min trades/fold", "10", kind="number"),
                CommandField(
                    "score_metric",
                    "Score metric",
                    "total_pnl",
                    kind="select",
                    options=("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted"),
                ),
                CommandField(
                    "class_weight",
                    "Class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                ),
                CommandField("n_estimators", "Trees/iterations", "400", kind="number"),
                CommandField("booster_lr", "Booster LR", "0.03", kind="number"),
                CommandField("max_depth", "Max depth", "3", kind="number"),
                CommandField("num_leaves", "LightGBM leaves", "31", kind="number"),
                CommandField("initial_capital", "Initial capital ($)", "100", kind="number"),
                CommandField("units", "PnL units", "0.1", kind="number"),
                CommandField("timeout_minutes", "Give up after (minutes)", "240", kind="number"),
            ],
            slow=True,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.VALIDATE_PRODUCTION_HYBRID_STACK,
            label="Validate production hybrid stack",
            description=(
                "Freeze and validate the Phase134 selected hybrid stack, telemetry schema, "
                "risk settings and live-safety gates before paper/live use."
            ),
            fields=[
                CommandField("symbol", "Symbol", "XAUUSD"),
                CommandField(
                    "dataset",
                    "Dataset",
                    "5M" if "5M" in datasets else (datasets[0] if datasets else "5M"),
                    kind="select",
                    options=tuple(datasets),
                ),
                CommandField("config_path", "Config path", "configs/hybrid_production_stack.json"),
                CommandField(
                    "mode", "Mode", "paper_shadow", kind="select", options=("paper_shadow", "live")
                ),
                CommandField("base_model_id", "Base model id", "gold_hybrid_lightgbm_head_5m"),
                CommandField("base_model_version", "Base version", "0", kind="number"),
                CommandField("meta_model_id", "Meta model id", ""),
                CommandField("meta_model_version", "Meta version", "0", kind="number"),
                CommandField(
                    "meta_model_type",
                    "Meta model type",
                    "none",
                    kind="select",
                    options=("none", "flat", "tensor"),
                ),
                CommandField(
                    "decision_mode",
                    "Decision mode",
                    "meta",
                    kind="select",
                    options=("meta", "score", "both"),
                ),
                CommandField("meta_threshold", "Meta threshold", "0.55", kind="number"),
                CommandField("score_threshold", "Score threshold", "0", kind="number"),
                CommandField("range_1d_model_id", "1D range model", "gold_range_1d"),
                CommandField("range_1d_version", "1D range version", "0", kind="number"),
                CommandField("range_4h_model_id", "4H range model", "gold_range_4h"),
                CommandField("range_4h_version", "4H range version", "0", kind="number"),
                CommandField("telemetry_flat_path", "Telemetry flat path", ""),
                CommandField("telemetry_tensor_path", "Telemetry tensor path", ""),
                CommandField("telemetry_schema_hash", "Expected schema hash", ""),
                CommandField("max_daily_loss_percent", "Max daily loss %", "5", kind="number"),
                CommandField("max_open_positions", "Max open positions", "1", kind="number"),
                CommandField("position_size_units", "Position size units", "0.1", kind="number"),
                CommandField("initial_capital", "Initial capital", "100", kind="number"),
                CommandField(
                    "paper_shadow_passed",
                    "Paper shadow passed",
                    "0",
                    kind="select",
                    options=("0", "1"),
                ),
                CommandField(
                    "account_profile_confirmed",
                    "Account confirmed",
                    "0",
                    kind="select",
                    options=("0", "1"),
                ),
                CommandField(
                    "symbol_mapping_confirmed",
                    "Symbol mapping confirmed",
                    "0",
                    kind="select",
                    options=("0", "1"),
                ),
                CommandField(
                    "kill_switch_enabled",
                    "Kill switch enabled",
                    "1",
                    kind="select",
                    options=("1", "0"),
                ),
                CommandField("explicit_live_confirm", "Live confirm phrase", ""),
                CommandField(
                    "write_config", "Write config", "1", kind="select", options=("1", "0")
                ),
                CommandField(
                    "require_models", "Require models exist", "0", kind="select", options=("0", "1")
                ),
                CommandField("timeout_minutes", "Give up after (minutes)", "60", kind="number"),
            ],
            slow=False,
            group="AI",
        ),
        CommandDescriptor(
            kind=CommandKind.RUN_HYBRID_PAPER_SHADOW,
            label="Run hybrid paper shadow",
            description=(
                "Run the frozen Phase134 hybrid stack over stored telemetry as paper/shadow "
                "decisions only; no real broker orders are sent."
            ),
            fields=[
                CommandField("config_path", "Config path", "configs/hybrid_production_stack.json"),
                CommandField("flat_path", "Telemetry flat path", ""),
                CommandField("eval_frac", "Eval fraction", "1.00", kind="number"),
                CommandField("max_windows", "Max windows", "0", kind="number"),
                CommandField(
                    "allow_validation_fail",
                    "Allow validation fail",
                    "0",
                    kind="select",
                    options=("0", "1"),
                ),
                CommandField("report_title", "Report title", "Hybrid production paper shadow"),
                CommandField("timeout_minutes", "Give up after (minutes)", "120", kind="number"),
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
                    hint=(
                        "range = future high/low · signal = binary buy/sell · "
                        "trend = candle color · trend_signal = BUY/HOLD/SELL · "
                        "trend_score = next-candle strength"
                    ),
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
                    "atr_mult",
                    "Trend-signal barrier (×ATR14)",
                    "0.5",
                    kind="number",
                    hint="فقط trend_signal: فاصلهٔ مانع BUY/SELL برحسب ATR14 (پیش‌فرض 0.5)",
                ),
                CommandField(
                    "class_weight",
                    "Trend-signal class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                    hint="فقط trend_signal: auto = وزن متعادل جداگانه برای هر fold train",
                ),
                CommandField(
                    "label_horizon",
                    "Trend-signal/score horizon (candles)",
                    "",
                    kind="number",
                    hint=(
                        "خالی = خودکار | trend_signal: 288 کندل 5M = یک روز | "
                        "trend_score روی 1D: خودکار = 1 یعنی score از کندل واقعی فردا"
                    ),
                ),
                CommandField(
                    "trend_score_loss",
                    "Trend-score loss",
                    "composite",
                    kind="select",
                    options=TREND_SCORE_LOSS_CHOICES,
                    hint=(
                        "فقط trend_score: composite = 3*Huber+6*MAE+1*MSE | "
                        "mae = آموزش با MAE خالص؛ checkpoint/ES روی val_mae"
                    ),
                ),
                CommandField(
                    "monitor_metric",
                    "Monitor metric",
                    "auto",
                    kind="select",
                    options=MONITOR_METRIC_CHOICES,
                    hint=(
                        "پیشرفته: برای trend_signal بهتر است val_buy_sell_f1؛ "
                        "auto یعنی پیش‌فرض اسکریپت"
                    ),
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
                    options=("signal", "range", "trend", "trend_signal", "trend_score"),
                    hint=(
                        "trend = رنگ کندل بعدی (سبز/قرمز) — پیشنهاد: 1D | "
                        "trend_signal = BUY/HOLD/SELL روی پنجرهٔ rolling "
                        "(دیتاست 5M، Window=288، Barrier=0.5×ATR14) | "
                        "trend_score = score روند (−1..+1) — روی 1D: کندل واقعی فردا"
                    ),
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
                CommandField(
                    "atr_mult",
                    "Trend-signal barrier (×ATR14)",
                    "0.5",
                    kind="number",
                    hint="فقط trend_signal: فاصلهٔ مانع BUY/SELL برحسب ATR14",
                ),
                CommandField(
                    "class_weight",
                    "Trend-signal class weights",
                    "auto",
                    kind="select",
                    options=CLASS_WEIGHT_CHOICES,
                    hint="فقط trend_signal: auto = وزن متعادل جداگانه برای هر fold train",
                ),
                CommandField(
                    "label_horizon",
                    "Trend-signal/score horizon (candles)",
                    "",
                    kind="number",
                    hint=(
                        "خالی = خودکار | trend_signal: 288 کندل 5M = یک روز | "
                        "trend_score روی 1D: خودکار = 1 یعنی score از کندل واقعی فردا"
                    ),
                ),
                CommandField(
                    "trend_score_loss",
                    "Trend-score loss",
                    "composite",
                    kind="select",
                    options=TREND_SCORE_LOSS_CHOICES,
                    hint=(
                        "فقط trend_score: composite = loss فعلی | mae = pilot/final با MAE خالص؛ "
                        "LR sweep بر اساس val_mae انتخاب می‌شود"
                    ),
                ),
                CommandField(
                    "monitor_metric",
                    "Monitor metric",
                    "auto",
                    kind="select",
                    options=MONITOR_METRIC_CHOICES,
                    hint=(
                        "پیشرفته: metric انتخاب LR/final checkpoint؛ "
                        "trend_signal = val_buy_sell_f1"
                    ),
                ),
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
    return _with_advanced_fields(items)


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

        Three details make the stream actually live on Windows too:

        * ``PYTHONUNBUFFERED=1`` and ``python -u`` — otherwise Python
          buffers stdout when the far end is a pipe rather than a terminal.
        * ``PYTHONUTF8=1`` / ``PYTHONIOENCODING=utf-8`` plus an explicit
          UTF-8 pipe decoder — the training script prints Persian text and
          symbols such as ``—``/``−``.  On Windows the dashboard process may
          otherwise decode the child pipe with a legacy code page and abort
          the log reader before the first epoch line reaches the browser.
        * The log file is opened only for each short append.  Holding a
          write handle for the whole training run can make live reads flaky
          on Windows; short appends leave ``/api/log`` free to read the file
          between writes.
        """
        import os
        import subprocess
        import sys

        log_path = self.run_log_path(command.kind.value)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        def replace_log(line: str) -> None:
            with log_path.open("w", encoding="utf-8", errors="replace") as log:
                log.write(line)
                log.flush()

        def append_log(line: str) -> None:
            with log_path.open("a", encoding="utf-8", errors="replace") as log:
                log.write(line)
                log.flush()

        environment = dict(os.environ)
        environment["PYTHONUNBUFFERED"] = "1"
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"

        tail: List[str] = []
        deadline = time.monotonic() + timeout
        process: Any = None
        returncode = 1

        try:
            replace_log(f"$ {' '.join(arguments)}\n")

            process = subprocess.Popen(
                [sys.executable, "-u", *arguments],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(Path.cwd()),
                env=environment,
            )

            assert process.stdout is not None
            for line in process.stdout:
                append_log(line)
                stripped = line.rstrip("\n")
                if stripped.strip():
                    tail.append(stripped)
                    if len(tail) > 400:
                        del tail[:200]
                if time.monotonic() > deadline:
                    process.kill()
                    append_log("\n[killed: timeout]\n")
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
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            try:
                append_log(f"\n[log reader failed: {type(error).__name__}: {error}]\n")
            except OSError:
                pass
            return CommandResult.failure(
                command.kind,
                "Could not stream the script output",
                f"{type(error).__name__}: {error}",
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
                CommandKind.AUDIT_TREND_SIGNAL: accounts.audit_trend_signal,
                CommandKind.CALIBRATE_TREND_SIGNAL: accounts.calibrate_trend_signal,
                CommandKind.TRAIN_TREND_SIGNAL_BOOSTER: accounts.train_trend_signal_booster,
                CommandKind.CALIBRATE_TREND_SIGNAL_BOOSTERS: (
                    accounts.calibrate_trend_signal_boosters
                ),
                CommandKind.BUILD_HYBRID_XGBOOST_MATRIX: accounts.build_hybrid_xgboost_matrix,
                CommandKind.BACKTEST_HYBRID_XGBOOST_HEAD: accounts.backtest_hybrid_xgboost_head,
                CommandKind.CHECK_HYBRID_SIGNIFICANCE: accounts.check_hybrid_significance,
                CommandKind.AUDIT_HYBRID_RANGE_AWARE_DECISIONS: (
                    accounts.audit_hybrid_range_aware_decisions
                ),
                CommandKind.REPORT_HYBRID_FULL_BACKTEST: accounts.report_hybrid_full_backtest,
                CommandKind.REPLAY_HYBRID_CHRONOLOGICAL_BACKTEST: (
                    accounts.replay_hybrid_chronological_backtest
                ),
                CommandKind.BUILD_HYBRID_TELEMETRY_TENSOR: (accounts.build_hybrid_telemetry_tensor),
                CommandKind.TRAIN_HYBRID_META_LABELER: accounts.train_hybrid_meta_labeler,
                CommandKind.BACKTEST_HYBRID_META_LABELER: accounts.backtest_hybrid_meta_labeler,
                CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET: (
                    accounts.train_hybrid_telemetry_wavenet
                ),
                CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET: (
                    accounts.backtest_hybrid_telemetry_wavenet
                ),
                CommandKind.TRAIN_HYBRID_TELEMETRY_TSMIXER: (
                    accounts.train_hybrid_telemetry_tsmixer
                ),
                CommandKind.BACKTEST_HYBRID_TELEMETRY_TSMIXER: (
                    accounts.backtest_hybrid_telemetry_tsmixer
                ),
                CommandKind.TRAIN_HYBRID_TELEMETRY_PATCHTST: (
                    accounts.train_hybrid_telemetry_patchtst
                ),
                CommandKind.BACKTEST_HYBRID_TELEMETRY_PATCHTST: (
                    accounts.backtest_hybrid_telemetry_patchtst
                ),
                CommandKind.BACKTEST_META_FILTERED_HYBRID: (accounts.backtest_meta_filtered_hybrid),
                CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION: (
                    accounts.run_hybrid_walk_forward_validation
                ),
                CommandKind.VALIDATE_PRODUCTION_HYBRID_STACK: (
                    accounts.validate_production_hybrid_stack
                ),
                CommandKind.RUN_HYBRID_PAPER_SHADOW: accounts.run_hybrid_paper_shadow,
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
        if record is not None and record.model_id.startswith("gold_trend_score_"):
            # فاز ۹۸-ب: مدل score روند
            role = "trend_score"
        elif record is not None and record.model_id.startswith("gold_trend_signal_"):
            # فاز ۹۹: مدل سیگنال ترند
            role = "trend_signal"
        elif record is not None and record.model_id.startswith("gold_trend_"):
            # فاز ۹۸: مدل ترند (رنگ) — نقش بازسازی‌شدهٔ مخصوص خودش
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
        _lh = command.integer("label_horizon", 0)
        _lh_args = (
            ["--label-horizon", str(max(_lh, 1))]
            if role in ("trend_signal", "trend_score") and _lh
            else []
        )
        _score_loss_args = trend_score_loss_args(command, role)
        _class_weight_args = trend_signal_class_weight_args(command, role)
        _monitor_metric_args = monitor_metric_args(command, role)

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
                *_lh_args,
                *_score_loss_args,
                *_class_weight_args,
                *_monitor_metric_args,
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

    def audit_trend_signal(self, command: Command) -> CommandResult:
        """Audit the trend_signal BUY/HOLD/SELL labels before expensive training."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        model_id = command.text("model_id", "").strip()
        model_args = ["--model-id", model_id] if model_id else []
        val_size = max(command.integer("val_size", 0), 0)
        val_args = ["--val-size", str(val_size)] if val_size else []

        return self._run_script(
            command,
            [
                "scripts/evaluate_trend_signal_5m.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--window",
                str(max(command.integer("window", 288), 2)),
                "--label-horizon",
                str(max(command.integer("label_horizon", 288), 1)),
                "--atr-mult",
                str(max(0.05, command.number("atr_mult", 0.5))),
                "--folds",
                str(max(command.integer("folds", 3), 1)),
                "--max-windows",
                str(max(command.integer("max_windows", 5000), 0)),
                "--storage-root",
                str(self._storage_root),
                *val_args,
                *model_args,
            ],
            f"Audited trend_signal labels on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 60), 5) * 60,
        )

    def calibrate_trend_signal(self, command: Command) -> CommandResult:
        """Calibrate BUY/SELL probability thresholds for a trend_signal model."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        model_id = command.text("model_id", "").strip()
        model_args = ["--model-id", model_id] if model_id else []
        return self._run_script(
            command,
            [
                "scripts/calibrate_trend_signal_thresholds.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--window",
                str(max(command.integer("window", 288), 2)),
                "--label-horizon",
                str(max(command.integer("label_horizon", 288), 1)),
                "--atr-mult",
                str(max(0.05, command.number("atr_mult", 0.5))),
                "--train-ratio",
                str(command.number("train_ratio", 80.0)),
                "--scope",
                command.text("scope", "auto").strip() or "auto",
                "--folds",
                str(max(command.integer("folds", 3), 1)),
                "--threshold-min",
                str(command.number("threshold_min", 0.35)),
                "--threshold-max",
                str(command.number("threshold_max", 0.95)),
                "--threshold-step",
                str(command.number("threshold_step", 0.05)),
                "--min-margin",
                str(max(command.number("min_margin", 0.0), 0.0)),
                "--min-trades",
                str(max(command.integer("min_trades", 50), 0)),
                "--precision-floor",
                str(max(command.number("precision_floor", 0.0), 0.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 8000), 0)),
                "--storage-root",
                str(self._storage_root),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                *model_args,
            ],
            f"Calibrated trend_signal thresholds on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 120), 5) * 60,
        )

    def train_trend_signal_booster(self, command: Command) -> CommandResult:
        """Train a separate tabular booster branch for trend_signal."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        booster = command.text("booster", "auto").strip().lower() or "auto"
        if booster not in BOOSTER_CHOICES:
            booster = "auto"
        output_mode = command.text("output_mode", "multiclass").strip().lower() or "multiclass"
        if output_mode not in BOOSTER_OUTPUT_CHOICES:
            output_mode = "multiclass"
        summary_mode = command.text("summary_mode", "basic").strip().lower() or "basic"
        if summary_mode not in WINDOW_SUMMARY_CHOICES:
            summary_mode = "basic"

        return self._run_script(
            command,
            [
                "scripts/train_trend_signal_boosters.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--booster",
                booster,
                "--output-mode",
                output_mode,
                "--summary-mode",
                summary_mode,
                "--window",
                str(max(command.integer("window", 288), 2)),
                "--label-horizon",
                str(max(command.integer("label_horizon", 288), 1)),
                "--atr-mult",
                str(max(0.05, command.number("atr_mult", 0.5))),
                "--train-ratio",
                str(command.number("train_ratio", 80.0)),
                "--folds",
                str(max(command.integer("folds", 3), 1)),
                "--val-size",
                str(max(command.integer("val_size", 2000), 4)),
                "--class-weight",
                command.text("class_weight", "auto").strip().lower() or "auto",
                "--n-estimators",
                str(max(command.integer("n_estimators", 400), 1)),
                "--learning-rate",
                str(max(command.number("booster_lr", 0.03), 1e-6)),
                "--max-depth",
                str(max(command.integer("max_depth", 4), 1)),
                "--num-leaves",
                str(max(command.integer("num_leaves", 31), 2)),
                "--max-samples",
                str(max(command.integer("max_samples", 0), 0)),
                "--storage-root",
                str(self._storage_root),
            ],
            f"Trained {booster} trend_signal booster branch on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def calibrate_trend_signal_boosters(self, command: Command) -> CommandResult:
        """Calibrate paired BUY/SELL booster specialist thresholds."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )
        buy_model = command.text("buy_model_id", "").strip()
        sell_model = command.text("sell_model_id", "").strip()
        buy_args = ["--buy-model-id", buy_model] if buy_model else []
        sell_args = ["--sell-model-id", sell_model] if sell_model else []

        return self._run_script(
            command,
            [
                "scripts/calibrate_trend_signal_boosters.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--booster",
                command.text("booster", "lightgbm").strip().lower() or "lightgbm",
                "--summary-mode",
                command.text("summary_mode", "basic").strip().lower() or "basic",
                "--window",
                str(max(command.integer("window", 288), 2)),
                "--label-horizon",
                str(max(command.integer("label_horizon", 288), 1)),
                "--atr-mult",
                str(max(0.05, command.number("atr_mult", 0.5))),
                "--train-ratio",
                str(command.number("train_ratio", 80.0)),
                "--scope",
                command.text("scope", "auto").strip() or "auto",
                "--threshold-min",
                str(command.number("threshold_min", 0.35)),
                "--threshold-max",
                str(command.number("threshold_max", 0.95)),
                "--threshold-step",
                str(command.number("threshold_step", 0.05)),
                "--min-margin",
                str(max(command.number("min_margin", 0.0), 0.0)),
                "--min-trades",
                str(max(command.integer("min_trades", 50), 0)),
                "--min-side-trades",
                str(max(command.integer("min_side_trades", 10), 0)),
                "--precision-floor",
                str(max(command.number("precision_floor", 0.0), 0.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 8000), 0)),
                "--buy-model-version",
                str(max(command.integer("buy_model_version", 0), 0)),
                "--sell-model-version",
                str(max(command.integer("sell_model_version", 0), 0)),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                "--storage-root",
                str(self._storage_root),
                *buy_args,
                *sell_args,
            ],
            f"Calibrated trend_signal booster specialists on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 120), 5) * 60,
        )

    def build_hybrid_xgboost_matrix(self, command: Command) -> CommandResult:
        """Build model-output meta-features for the final XGBoost head."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        optional_text_fields = [
            ("--buy-model-id", "buy_model_id"),
            ("--sell-model-id", "sell_model_id"),
            ("--multiclass-model-id", "multiclass_model_id"),
        ]
        optional_args: List[str] = []
        for flag, field in optional_text_fields:
            value = command.text(field, "").strip()
            if value:
                optional_args += [flag, value]

        return self._run_script(
            command,
            [
                "scripts/build_hybrid_xgboost_matrix.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--window",
                str(max(command.integer("window", 288), 2)),
                "--label-horizon",
                str(max(command.integer("label_horizon", 288), 1)),
                "--atr-mult",
                str(max(0.05, command.number("atr_mult", 0.5))),
                "--train-ratio",
                str(command.number("train_ratio", 80.0)),
                "--scope",
                command.text("scope", "holdout").strip() or "holdout",
                "--folds",
                str(max(command.integer("folds", 3), 1)),
                "--val-size",
                str(max(command.integer("val_size", 2000), 4)),
                "--max-windows",
                str(max(command.integer("max_windows", 8000), 0)),
                "--summary-mode",
                command.text("summary_mode", "basic").strip().lower() or "basic",
                "--booster",
                command.text("booster", "lightgbm").strip().lower() or "lightgbm",
                "--include-tabular-summary",
                "1" if command.text("include_tabular_summary", "0").strip() == "1" else "0",
                "--include-specialists",
                "1" if command.text("include_specialists", "1").strip() != "0" else "0",
                "--include-multiclass-booster",
                "1" if command.text("include_multiclass_booster", "1").strip() != "0" else "0",
                "--include-wavenet",
                "1" if command.text("include_wavenet", "1").strip() != "0" else "0",
                "--require-wavenet",
                "1" if command.text("require_wavenet", "0").strip() == "1" else "0",
                "--include-range",
                "1" if command.text("include_range", "1").strip() != "0" else "0",
                "--require-range",
                "1" if command.text("require_range", "1").strip() != "0" else "0",
                "--wavenet-model-id",
                command.text("wavenet_model_id", "gold_trend_signal_5m").strip()
                or "gold_trend_signal_5m",
                "--range-1d-model-id",
                command.text("range_1d_model_id", "gold_range_1d").strip() or "gold_range_1d",
                "--range-4h-model-id",
                command.text("range_4h_model_id", "gold_range_4h").strip() or "gold_range_4h",
                "--buy-model-version",
                str(max(command.integer("buy_model_version", 0), 0)),
                "--sell-model-version",
                str(max(command.integer("sell_model_version", 0), 0)),
                "--multiclass-model-version",
                str(max(command.integer("multiclass_model_version", 0), 0)),
                "--wavenet-model-version",
                str(max(command.integer("wavenet_model_version", 0), 0)),
                "--range-1d-version",
                str(max(command.integer("range_1d_version", 0), 0)),
                "--range-4h-version",
                str(max(command.integer("range_4h_version", 0), 0)),
                "--output-name",
                command.text("output_name", "hybrid_xgboost_matrix_v1").strip()
                or "hybrid_xgboost_matrix_v1",
                "--storage-root",
                str(self._storage_root),
                *optional_args,
            ],
            f"Built hybrid XGBoost matrix on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 240), 5) * 60,
        )

    def backtest_hybrid_xgboost_head(self, command: Command) -> CommandResult:
        """Calibrate and backtest the hybrid head with range TP/SL."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )
        matrix_path = command.text("matrix_path", "").strip()
        matrix_args = ["--matrix-path", matrix_path] if matrix_path else []
        score_metric = command.text("score_metric", "total_pnl").strip() or "total_pnl"
        if score_metric not in SCORE_METRIC_CHOICES:
            score_metric = "total_pnl"

        return self._run_script(
            command,
            [
                "scripts/backtest_hybrid_xgboost_head.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--eval-frac",
                str(command.number("eval_frac", 0.30)),
                "--threshold-min",
                str(command.number("threshold_min", 0.35)),
                "--threshold-max",
                str(command.number("threshold_max", 0.95)),
                "--threshold-step",
                str(command.number("threshold_step", 0.05)),
                "--min-margin",
                str(max(command.number("min_margin", 0.0), 0.0)),
                "--min-trades",
                str(max(command.integer("min_trades", 30), 0)),
                "--precision-floor",
                str(max(command.number("precision_floor", 0.0), 0.0)),
                "--min-profit-factor",
                str(max(command.number("min_profit_factor", 0.0), 0.0)),
                "--score-metric",
                score_metric,
                "--max-hold-bars",
                str(max(command.integer("max_hold_bars", 48), 1)),
                "--min-4h-room",
                str(max(command.number("min_4h_room", 0.0), 0.0)),
                "--min-1d-room",
                str(max(command.number("min_1d_room", 0.0), 0.0)),
                "--min-tp-distance",
                str(max(command.number("min_tp_distance", 1.0), 0.0)),
                "--min-sl-distance",
                str(max(command.number("min_sl_distance", 1.0), 0.0)),
                "--spread-mode",
                command.text("spread_mode", "pct").strip().lower() or "pct",
                "--spread-value",
                str(max(command.number("spread_value", 0.06), 0.0)),
                "--slippage",
                str(max(command.number("slippage", 0.0), 0.0)),
                "--same-bar-policy",
                command.text("same_bar_policy", "stop_first").strip() or "stop_first",
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                "--storage-root",
                str(self._storage_root),
                *matrix_args,
            ],
            f"Backtested hybrid XGBoost head on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 120), 5) * 60,
        )

    def check_hybrid_significance(self, command: Command) -> CommandResult:
        """Run the Phase 113 random baseline for the saved hybrid head."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        matrix_path = command.text("matrix_path", "").strip()
        matrix_args = ["--matrix-path", matrix_path] if matrix_path else []
        return self._run_script(
            command,
            [
                "scripts/backtest_significance_check.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--eval-frac",
                str(command.number("eval_frac", 0.30)),
                "--buy-threshold",
                str(command.number("buy_threshold", -1.0)),
                "--sell-threshold",
                str(command.number("sell_threshold", -1.0)),
                "--min-margin",
                str(command.number("min_margin", -1.0)),
                "--max-hold-bars",
                str(max(command.integer("max_hold_bars", 48), 1)),
                "--min-4h-room",
                str(max(command.number("min_4h_room", 2.0), 0.0)),
                "--min-1d-room",
                str(max(command.number("min_1d_room", 5.0), 0.0)),
                "--min-tp-distance",
                str(max(command.number("min_tp_distance", 2.0), 0.0)),
                "--min-sl-distance",
                str(max(command.number("min_sl_distance", 2.0), 0.0)),
                "--spread-mode",
                command.text("spread_mode", "pct").strip().lower() or "pct",
                "--spread-value",
                str(max(command.number("spread_value", 0.06), 0.0)),
                "--slippage",
                str(max(command.number("slippage", 0.0), 0.0)),
                "--same-bar-policy",
                command.text("same_bar_policy", "stop_first").strip() or "stop_first",
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--trials",
                str(max(command.integer("trials", 1000), 1)),
                "--seed",
                str(command.integer("seed", 42)),
                "--white-check",
                "1" if command.text("white_check", "1").strip() != "0" else "0",
                "--candidate-rows-path",
                command.text(
                    "candidate_rows_path", "run_logs/hybrid_head_backtest/latest.json"
                ).strip()
                or "run_logs/hybrid_head_backtest/latest.json",
                "--white-max-candidates",
                str(max(command.integer("white_max_candidates", 0), 0)),
                "--storage-root",
                str(self._storage_root),
                *matrix_args,
            ],
            f"Checked hybrid-head significance on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 120), 5) * 60,
        )

    def audit_hybrid_range_aware_decisions(self, command: Command) -> CommandResult:
        """Run the Phase 116 runtime decision audit for the saved hybrid head."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        matrix_path = command.text("matrix_path", "").strip()
        matrix_args = ["--matrix-path", matrix_path] if matrix_path else []
        return self._run_script(
            command,
            [
                "scripts/audit_hybrid_range_aware_decisions.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--eval-frac",
                str(command.number("eval_frac", 0.30)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--buy-threshold",
                str(command.number("buy_threshold", -1.0)),
                "--sell-threshold",
                str(command.number("sell_threshold", -1.0)),
                "--min-margin",
                str(command.number("min_margin", -1.0)),
                "--min-4h-room",
                str(max(command.number("min_4h_room", 2.0), 0.0)),
                "--min-1d-room",
                str(max(command.number("min_1d_room", 5.0), 0.0)),
                "--min-tp-distance",
                str(max(command.number("min_tp_distance", 2.0), 0.0)),
                "--min-sl-distance",
                str(max(command.number("min_sl_distance", 2.0), 0.0)),
                "--spread-mode",
                command.text("spread_mode", "pct").strip().lower() or "pct",
                "--spread-value",
                str(max(command.number("spread_value", 0.06), 0.0)),
                "--slippage",
                str(max(command.number("slippage", 0.0), 0.0)),
                "--capital",
                str(max(command.number("capital", 10000.0), 0.0)),
                "--base-quantity",
                str(max(command.number("base_quantity", 1.0), 0.000001)),
                "--storage-root",
                str(self._storage_root),
                *matrix_args,
            ],
            f"Audited Phase116 hybrid range-aware decisions on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 120), 5) * 60,
        )

    def report_hybrid_full_backtest(self, command: Command) -> CommandResult:
        """Generate an HTML full-history hybrid 5M backtest report."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        matrix_path = command.text("matrix_path", "").strip()
        matrix_args = ["--matrix-path", matrix_path] if matrix_path else []
        return self._run_script(
            command,
            [
                "scripts/report_hybrid_full_backtest.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--source-mode",
                command.text("source_mode", "matrix").strip().lower() or "matrix",
                "--stream-scope",
                command.text("stream_scope", "all").strip().lower() or "all",
                "--stream-chunk-size",
                str(max(command.integer("stream_chunk_size", 2000), 50)),
                "--stream-wavenet",
                command.text("stream_wavenet", "neutral").strip().lower() or "neutral",
                "--model-id",
                command.text("model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--buy-threshold",
                str(command.number("buy_threshold", -1.0)),
                "--sell-threshold",
                str(command.number("sell_threshold", -1.0)),
                "--min-margin",
                str(command.number("min_margin", -1.0)),
                "--max-hold-bars",
                str(max(command.integer("max_hold_bars", 48), 1)),
                "--min-4h-room",
                str(max(command.number("min_4h_room", 2.0), 0.0)),
                "--min-1d-room",
                str(max(command.number("min_1d_room", 5.0), 0.0)),
                "--min-tp-distance",
                str(max(command.number("min_tp_distance", 2.0), 0.0)),
                "--min-sl-distance",
                str(max(command.number("min_sl_distance", 2.0), 0.0)),
                "--spread-mode",
                command.text("spread_mode", "pct").strip().lower() or "pct",
                "--spread-value",
                str(max(command.number("spread_value", 0.06), 0.0)),
                "--slippage",
                str(max(command.number("slippage", 0.0), 0.0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 1.0), 0.0)),
                "--same-bar-policy",
                command.text("same_bar_policy", "stop_first").strip() or "stop_first",
                "--report-title",
                command.text("report_title", "Hybrid range-aware full 5M backtest").strip()
                or "Hybrid range-aware full 5M backtest",
                "--storage-root",
                str(self._storage_root),
                *matrix_args,
            ],
            f"Generated full hybrid 5M backtest report on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def replay_hybrid_chronological_backtest(self, command: Command) -> CommandResult:
        """Run the Phase126A single-position chronological hybrid replay."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        matrix_path = command.text("matrix_path", "").strip()
        matrix_args = ["--matrix-path", matrix_path] if matrix_path else []
        return self._run_script(
            command,
            [
                "scripts/replay_hybrid_chronological_backtest.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--source-mode",
                command.text("source_mode", "stream").strip().lower() or "stream",
                "--stream-scope",
                command.text("stream_scope", "all").strip().lower() or "all",
                "--stream-chunk-size",
                str(max(command.integer("stream_chunk_size", 500), 50)),
                "--stream-wavenet",
                command.text("stream_wavenet", "neutral").strip().lower() or "neutral",
                "--model-id",
                command.text("model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--buy-threshold",
                str(command.number("buy_threshold", -1.0)),
                "--sell-threshold",
                str(command.number("sell_threshold", -1.0)),
                "--min-margin",
                str(command.number("min_margin", -1.0)),
                "--max-hold-bars",
                str(max(command.integer("max_hold_bars", 48), 1)),
                "--min-4h-room",
                str(max(command.number("min_4h_room", 2.0), 0.0)),
                "--min-1d-room",
                str(max(command.number("min_1d_room", 5.0), 0.0)),
                "--min-tp-distance",
                str(max(command.number("min_tp_distance", 2.0), 0.0)),
                "--min-sl-distance",
                str(max(command.number("min_sl_distance", 2.0), 0.0)),
                "--spread-mode",
                command.text("spread_mode", "pct").strip().lower() or "pct",
                "--spread-value",
                str(max(command.number("spread_value", 0.06), 0.0)),
                "--slippage",
                str(max(command.number("slippage", 0.0), 0.0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--same-bar-policy",
                command.text("same_bar_policy", "stop_first").strip() or "stop_first",
                "--report-title",
                command.text("report_title", "Chronological hybrid single-position replay").strip()
                or "Chronological hybrid single-position replay",
                "--storage-root",
                str(self._storage_root),
                *matrix_args,
            ],
            f"Generated chronological hybrid replay on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def build_hybrid_telemetry_tensor(self, command: Command) -> CommandResult:
        """Build the Phase127 causal telemetry tensor from GUI/Dashboard."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        matrix_path = command.text("matrix_path", "").strip()
        matrix_args = ["--matrix-path", matrix_path] if matrix_path else []
        return self._run_script(
            command,
            [
                "scripts/build_hybrid_telemetry_tensor.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--source-mode",
                command.text("source_mode", "matrix").strip().lower() or "matrix",
                "--stream-scope",
                command.text("stream_scope", "all").strip().lower() or "all",
                "--stream-chunk-size",
                str(max(command.integer("stream_chunk_size", 500), 50)),
                "--stream-wavenet",
                command.text("stream_wavenet", "neutral").strip().lower() or "neutral",
                "--model-id",
                command.text("model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--window",
                str(max(command.integer("window", 288), 2)),
                "--label-horizon",
                str(max(command.integer("label_horizon", 288), 1)),
                "--atr-mult",
                str(max(command.number("atr_mult", 0.5), 0.05)),
                "--train-ratio",
                str(command.number("train_ratio", 80.0)),
                "--tensor-window",
                str(max(command.integer("tensor_window", 150), 2)),
                "--safe-lag-bars",
                str(max(command.integer("safe_lag_bars", 48), 1)),
                "--telemetry-lag-mode",
                command.text("telemetry_lag_mode", "fixed").strip().lower() or "fixed",
                "--sample-stride",
                str(max(command.integer("sample_stride", 1), 1)),
                "--max-samples",
                str(max(command.integer("max_samples", 0), 0)),
                "--candidate-samples-only",
                "1" if command.text("candidate_samples_only", "0").strip() == "1" else "0",
                "--dtype",
                command.text("dtype", "float16").strip().lower() or "float16",
                "--max-tensor-mb",
                str(max(command.number("max_tensor_mb", 512.0), 1.0)),
                "--include-htf-context",
                "1" if command.text("include_htf_context", "1").strip() != "0" else "0",
                "--buy-threshold",
                str(command.number("buy_threshold", -1.0)),
                "--sell-threshold",
                str(command.number("sell_threshold", -1.0)),
                "--min-margin",
                str(command.number("min_margin", -1.0)),
                "--max-hold-bars",
                str(max(command.integer("max_hold_bars", 48), 1)),
                "--min-4h-room",
                str(max(command.number("min_4h_room", 2.0), 0.0)),
                "--min-1d-room",
                str(max(command.number("min_1d_room", 5.0), 0.0)),
                "--min-tp-distance",
                str(max(command.number("min_tp_distance", 2.0), 0.0)),
                "--min-sl-distance",
                str(max(command.number("min_sl_distance", 2.0), 0.0)),
                "--spread-mode",
                command.text("spread_mode", "pct").strip().lower() or "pct",
                "--spread-value",
                str(max(command.number("spread_value", 0.06), 0.0)),
                "--slippage",
                str(max(command.number("slippage", 0.0), 0.0)),
                "--same-bar-policy",
                command.text("same_bar_policy", "stop_first").strip().lower() or "stop_first",
                "--output-name",
                command.text("output_name", "hybrid_telemetry_tensor_v1").strip()
                or "hybrid_telemetry_tensor_v1",
                "--storage-root",
                str(self._storage_root),
                *matrix_args,
            ],
            f"Built Phase127 hybrid telemetry tensor on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def train_hybrid_meta_labeler(self, command: Command) -> CommandResult:
        """Train the Phase128 flat telemetry meta-labeler."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        flat_path = command.text("flat_path", "").strip()
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/train_hybrid_meta_labeler.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "").strip(),
                "--task",
                command.text("task", "classifier").strip().lower() or "classifier",
                "--target",
                command.text("target", "").strip(),
                "--booster",
                command.text("booster", "lightgbm").strip().lower() or "lightgbm",
                "--candidate-only",
                "1" if command.text("candidate_only", "1").strip() != "0" else "0",
                "--train-frac",
                str(command.number("train_frac", 0.70)),
                "--val-frac",
                str(command.number("val_frac", 0.15)),
                "--min-samples",
                str(max(command.integer("min_samples", 200), 1)),
                "--class-weight",
                command.text("class_weight", "auto").strip().lower() or "auto",
                "--n-estimators",
                str(max(command.integer("n_estimators", 500), 1)),
                "--learning-rate",
                str(max(command.number("booster_lr", 0.03), 1e-6)),
                "--max-depth",
                str(max(command.integer("max_depth", 3), 1)),
                "--num-leaves",
                str(max(command.integer("num_leaves", 31), 2)),
                "--meta-threshold",
                str(max(command.number("meta_threshold", 0.55), 0.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                "--storage-root",
                str(self._storage_root),
                *flat_args,
            ],
            f"Trained Phase128 hybrid meta-labeler on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def backtest_hybrid_meta_labeler(self, command: Command) -> CommandResult:
        """Backtest the Phase128 meta-filtered hybrid candidates."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        flat_path = command.text("flat_path", "").strip()
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/backtest_hybrid_meta_labeler.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--meta-model-id",
                command.text("meta_model_id", "gold_hybrid_meta_lightgbm_5m").strip()
                or "gold_hybrid_meta_lightgbm_5m",
                "--meta-model-version",
                str(max(command.integer("meta_model_version", 0), 0)),
                "--meta-threshold",
                str(command.number("meta_threshold", -1.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--report-title",
                command.text("report_title", "Meta-filtered hybrid chronological backtest").strip()
                or "Meta-filtered hybrid chronological backtest",
                "--storage-root",
                str(self._storage_root),
                *flat_args,
            ],
            f"Backtested Phase128 hybrid meta-labeler on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def train_hybrid_telemetry_wavenet(self, command: Command) -> CommandResult:
        """Train the Phase129 WaveNet/TCN on the telemetry tensor."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        tensor_path = command.text("tensor_path", "").strip()
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        return self._run_script(
            command,
            [
                "scripts/train_hybrid_telemetry_wavenet.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_telemetry_wavenet_5m").strip()
                or "gold_hybrid_telemetry_wavenet_5m",
                "--task",
                command.text("task", "multihead").strip().lower() or "multihead",
                "--candidate-only",
                "1" if command.text("candidate_only", "1").strip() != "0" else "0",
                "--train-frac",
                str(command.number("train_frac", 0.70)),
                "--val-frac",
                str(command.number("val_frac", 0.15)),
                "--purge-gap",
                str(max(command.integer("purge_gap", 336), 0)),
                "--max-samples",
                str(max(command.integer("max_samples", 0), 0)),
                "--batch-size",
                str(max(command.integer("batch_size", 64), 1)),
                "--epochs",
                str(max(command.integer("epochs", 30), 1)),
                "--learning-rate",
                str(max(command.number("learning_rate", 0.001), 1e-8)),
                "--filters",
                str(max(command.integer("filters", 48), 1)),
                "--kernel-size",
                str(max(command.integer("kernel_size", 3), 1)),
                "--n-layers",
                str(max(command.integer("n_layers", 5), 1)),
                "--n-blocks",
                str(max(command.integer("n_blocks", 2), 1)),
                "--dense-units",
                str(max(command.integer("dense_units", 64), 1)),
                "--dropout",
                str(max(command.number("dropout", 0.20), 0.0)),
                "--score-loss-weight",
                str(max(command.number("score_loss_weight", 0.50), 0.0)),
                "--class-weight",
                command.text("class_weight", "auto").strip().lower() or "auto",
                "--meta-threshold",
                str(max(command.number("meta_threshold", 0.55), 0.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--monitor-metric",
                command.text("monitor_metric", "auto").strip() or "auto",
                "--early-stopping-patience",
                str(max(command.integer("early_stopping_patience", 8), 0)),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                "--storage-root",
                str(self._storage_root),
                *tensor_args,
            ],
            f"Trained Phase129 telemetry WaveNet/TCN on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 240), 5) * 60,
        )

    def backtest_hybrid_telemetry_wavenet(self, command: Command) -> CommandResult:
        """Backtest the Phase129 WaveNet/TCN meta-filter."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        tensor_path = command.text("tensor_path", "").strip()
        flat_path = command.text("flat_path", "").strip()
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/backtest_hybrid_telemetry_wavenet.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_telemetry_wavenet_5m").strip()
                or "gold_hybrid_telemetry_wavenet_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--decision-mode",
                command.text("decision_mode", "meta").strip().lower() or "meta",
                "--meta-threshold",
                str(command.number("meta_threshold", -1.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--report-title",
                command.text("report_title", "Telemetry WaveNet filtered hybrid replay").strip()
                or "Telemetry WaveNet filtered hybrid replay",
                "--storage-root",
                str(self._storage_root),
                *tensor_args,
                *flat_args,
            ],
            f"Backtested Phase129 telemetry WaveNet/TCN on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def train_hybrid_telemetry_tsmixer(self, command: Command) -> CommandResult:
        """Train the Phase130 TSMixer on the telemetry tensor."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        tensor_path = command.text("tensor_path", "").strip()
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        return self._run_script(
            command,
            [
                "scripts/train_hybrid_telemetry_tsmixer.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_telemetry_tsmixer_5m").strip()
                or "gold_hybrid_telemetry_tsmixer_5m",
                "--task",
                command.text("task", "multihead").strip().lower() or "multihead",
                "--candidate-only",
                "1" if command.text("candidate_only", "1").strip() != "0" else "0",
                "--train-frac",
                str(command.number("train_frac", 0.70)),
                "--val-frac",
                str(command.number("val_frac", 0.15)),
                "--purge-gap",
                str(max(command.integer("purge_gap", 336), 0)),
                "--max-samples",
                str(max(command.integer("max_samples", 0), 0)),
                "--batch-size",
                str(max(command.integer("batch_size", 64), 1)),
                "--epochs",
                str(max(command.integer("epochs", 30), 1)),
                "--learning-rate",
                str(max(command.number("learning_rate", 0.001), 1e-8)),
                "--mixer-layers",
                str(max(command.integer("mixer_layers", 4), 1)),
                "--time-hidden-units",
                str(max(command.integer("time_hidden_units", 64), 1)),
                "--feature-hidden-units",
                str(max(command.integer("feature_hidden_units", 128), 1)),
                "--dense-units",
                str(max(command.integer("dense_units", 64), 1)),
                "--dropout",
                str(max(command.number("dropout", 0.20), 0.0)),
                "--score-loss-weight",
                str(max(command.number("score_loss_weight", 0.50), 0.0)),
                "--class-weight",
                command.text("class_weight", "auto").strip().lower() or "auto",
                "--meta-threshold",
                str(max(command.number("meta_threshold", 0.55), 0.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--monitor-metric",
                command.text("monitor_metric", "auto").strip() or "auto",
                "--early-stopping-patience",
                str(max(command.integer("early_stopping_patience", 8), 0)),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                "--storage-root",
                str(self._storage_root),
                *tensor_args,
            ],
            f"Trained Phase130 telemetry TSMixer on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 240), 5) * 60,
        )

    def backtest_hybrid_telemetry_tsmixer(self, command: Command) -> CommandResult:
        """Backtest the Phase130 TSMixer meta-filter."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        tensor_path = command.text("tensor_path", "").strip()
        flat_path = command.text("flat_path", "").strip()
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/backtest_hybrid_telemetry_tsmixer.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_telemetry_tsmixer_5m").strip()
                or "gold_hybrid_telemetry_tsmixer_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--decision-mode",
                command.text("decision_mode", "meta").strip().lower() or "meta",
                "--meta-threshold",
                str(command.number("meta_threshold", -1.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--report-title",
                command.text("report_title", "Telemetry TSMixer filtered hybrid replay").strip()
                or "Telemetry TSMixer filtered hybrid replay",
                "--storage-root",
                str(self._storage_root),
                *tensor_args,
                *flat_args,
            ],
            f"Backtested Phase130 telemetry TSMixer on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def train_hybrid_telemetry_patchtst(self, command: Command) -> CommandResult:
        """Train the Phase131 PatchTST on the telemetry tensor."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        tensor_path = command.text("tensor_path", "").strip()
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        return self._run_script(
            command,
            [
                "scripts/train_hybrid_telemetry_patchtst.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_telemetry_patchtst_5m").strip()
                or "gold_hybrid_telemetry_patchtst_5m",
                "--task",
                command.text("task", "multihead").strip().lower() or "multihead",
                "--candidate-only",
                "1" if command.text("candidate_only", "1").strip() != "0" else "0",
                "--train-frac",
                str(command.number("train_frac", 0.70)),
                "--val-frac",
                str(command.number("val_frac", 0.15)),
                "--purge-gap",
                str(max(command.integer("purge_gap", 336), 0)),
                "--max-samples",
                str(max(command.integer("max_samples", 0), 0)),
                "--batch-size",
                str(max(command.integer("batch_size", 64), 1)),
                "--epochs",
                str(max(command.integer("epochs", 30), 1)),
                "--learning-rate",
                str(max(command.number("learning_rate", 0.001), 1e-8)),
                "--patch-len",
                str(max(command.integer("patch_len", 16), 1)),
                "--stride",
                str(max(command.integer("stride", 8), 1)),
                "--d-model",
                str(max(command.integer("d_model", 64), 1)),
                "--layers",
                str(max(command.integer("layers", 3), 1)),
                "--heads",
                str(max(command.integer("heads", 4), 1)),
                "--ff-units",
                str(max(command.integer("ff_units", 128), 1)),
                "--dense-units",
                str(max(command.integer("dense_units", 64), 1)),
                "--dropout",
                str(max(command.number("dropout", 0.20), 0.0)),
                "--score-loss-weight",
                str(max(command.number("score_loss_weight", 0.50), 0.0)),
                "--class-weight",
                command.text("class_weight", "auto").strip().lower() or "auto",
                "--meta-threshold",
                str(max(command.number("meta_threshold", 0.55), 0.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--monitor-metric",
                command.text("monitor_metric", "auto").strip() or "auto",
                "--early-stopping-patience",
                str(max(command.integer("early_stopping_patience", 8), 0)),
                "--save-record",
                "1" if command.text("save_record", "1").strip() != "0" else "0",
                "--storage-root",
                str(self._storage_root),
                *tensor_args,
            ],
            f"Trained Phase131 telemetry PatchTST on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 240), 5) * 60,
        )

    def backtest_hybrid_telemetry_patchtst(self, command: Command) -> CommandResult:
        """Backtest the Phase131 PatchTST meta-filter."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        tensor_path = command.text("tensor_path", "").strip()
        flat_path = command.text("flat_path", "").strip()
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/backtest_hybrid_telemetry_patchtst.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_telemetry_patchtst_5m").strip()
                or "gold_hybrid_telemetry_patchtst_5m",
                "--model-version",
                str(max(command.integer("model_version", 0), 0)),
                "--decision-mode",
                command.text("decision_mode", "meta").strip().lower() or "meta",
                "--meta-threshold",
                str(command.number("meta_threshold", -1.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--report-title",
                command.text("report_title", "Telemetry PatchTST filtered hybrid replay").strip()
                or "Telemetry PatchTST filtered hybrid replay",
                "--storage-root",
                str(self._storage_root),
                *tensor_args,
                *flat_args,
            ],
            f"Backtested Phase131 telemetry PatchTST on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def backtest_meta_filtered_hybrid(self, command: Command) -> CommandResult:
        """Run the Phase132 candidate comparison backtest."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        flat_path = command.text("flat_path", "").strip()
        tensor_path = command.text("tensor_path", "").strip()
        flat_args = ["--flat-path", flat_path] if flat_path else []
        tensor_args = ["--tensor-path", tensor_path] if tensor_path else []
        return self._run_script(
            command,
            [
                "scripts/backtest_meta_filtered_hybrid.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--candidates",
                command.text(
                    "candidates",
                    "base,gold_hybrid_meta_lightgbm_5m,gold_hybrid_telemetry_wavenet_5m,gold_hybrid_telemetry_tsmixer_5m,gold_hybrid_telemetry_patchtst_5m",
                ).strip(),
                "--candidate-versions",
                command.text("candidate_versions", "0").strip() or "0",
                "--decision-modes",
                command.text("decision_modes", "meta").strip() or "meta",
                "--meta-thresholds",
                command.text("meta_thresholds", "record").strip() or "record",
                "--score-thresholds",
                command.text("score_thresholds", "0").strip() or "0",
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--min-trades",
                str(max(command.integer("min_trades", 10), 0)),
                "--score-metric",
                command.text("score_metric", "total_pnl").strip() or "total_pnl",
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--skip-missing",
                "1" if command.text("skip_missing", "1").strip() != "0" else "0",
                "--report-title",
                command.text("report_title", "Hybrid meta-filter comparison").strip()
                or "Hybrid meta-filter comparison",
                "--storage-root",
                str(self._storage_root),
                *flat_args,
                *tensor_args,
            ],
            f"Compared meta-filtered hybrid candidates on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 180), 5) * 60,
        )

    def run_hybrid_walk_forward_validation(self, command: Command) -> CommandResult:
        """Run the Phase133 walk-forward validation from GUI/Dashboard."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        flat_path = command.text("flat_path", "").strip()
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/run_hybrid_walk_forward_validation.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--model-id",
                command.text("model_id", "gold_hybrid_meta_walkforward_5m").strip()
                or "gold_hybrid_meta_walkforward_5m",
                "--task",
                command.text("task", "classifier").strip().lower() or "classifier",
                "--target",
                command.text("target", "").strip(),
                "--booster",
                command.text("booster", "lightgbm").strip().lower() or "lightgbm",
                "--candidate-only",
                "1" if command.text("candidate_only", "1").strip() != "0" else "0",
                "--start-month",
                command.text("start_month", "").strip(),
                "--end-month",
                command.text("end_month", "").strip(),
                "--train-months-min",
                str(max(command.integer("train_months_min", 3), 1)),
                "--validation-months",
                str(max(command.integer("validation_months", 1), 1)),
                "--purge-gap-bars",
                str(max(command.integer("purge_gap_bars", 336), 0)),
                "--meta-thresholds",
                command.text("meta_thresholds", "0.45,0.50,0.55,0.60,0.65,0.70").strip()
                or "0.45,0.50,0.55,0.60,0.65,0.70",
                "--score-thresholds",
                command.text("score_thresholds", "0,0.05,0.10,0.20").strip() or "0,0.05,0.10,0.20",
                "--min-trades",
                str(max(command.integer("min_trades", 10), 0)),
                "--score-metric",
                command.text("score_metric", "total_pnl").strip() or "total_pnl",
                "--class-weight",
                command.text("class_weight", "auto").strip().lower() or "auto",
                "--n-estimators",
                str(max(command.integer("n_estimators", 400), 1)),
                "--learning-rate",
                str(max(command.number("booster_lr", 0.03), 1e-8)),
                "--max-depth",
                str(max(command.integer("max_depth", 3), 1)),
                "--num-leaves",
                str(max(command.integer("num_leaves", 31), 2)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--units",
                str(max(command.number("units", 0.1), 0.0)),
                "--storage-root",
                str(self._storage_root),
                *flat_args,
            ],
            f"Ran Phase133 walk-forward validation on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 240), 5) * 60,
        )

    def validate_production_hybrid_stack(self, command: Command) -> CommandResult:
        """Validate/freeze the Phase134 production hybrid stack."""
        started = time.monotonic()
        symbol = command.text("symbol", "XAUUSD").strip().upper()
        dataset = command.text("dataset", "").strip().upper()
        available = stored_dataset_choices(self._storage_root)
        if not dataset:
            dataset = "5M" if "5M" in available else (available[0] if available else "5M")
        if dataset not in available:
            return CommandResult.rejected(
                command.kind,
                f"No stored {dataset} dataset. Available: {', '.join(available) or 'none'}",
            )

        return self._run_script(
            command,
            [
                "scripts/validate_production_hybrid_stack.py",
                "--symbol",
                symbol,
                "--timeframe",
                dataset,
                "--config-path",
                command.text("config_path", "configs/hybrid_production_stack.json").strip()
                or "configs/hybrid_production_stack.json",
                "--mode",
                command.text("mode", "paper_shadow").strip().lower() or "paper_shadow",
                "--base-model-id",
                command.text("base_model_id", "gold_hybrid_lightgbm_head_5m").strip()
                or "gold_hybrid_lightgbm_head_5m",
                "--base-model-version",
                str(max(command.integer("base_model_version", 0), 0)),
                "--meta-model-id",
                command.text("meta_model_id", "").strip(),
                "--meta-model-version",
                str(max(command.integer("meta_model_version", 0), 0)),
                "--meta-model-type",
                command.text("meta_model_type", "none").strip().lower() or "none",
                "--decision-mode",
                command.text("decision_mode", "meta").strip().lower() or "meta",
                "--meta-threshold",
                str(max(command.number("meta_threshold", 0.55), 0.0)),
                "--score-threshold",
                str(command.number("score_threshold", 0.0)),
                "--range-1d-model-id",
                command.text("range_1d_model_id", "gold_range_1d").strip() or "gold_range_1d",
                "--range-1d-version",
                str(max(command.integer("range_1d_version", 0), 0)),
                "--range-4h-model-id",
                command.text("range_4h_model_id", "gold_range_4h").strip() or "gold_range_4h",
                "--range-4h-version",
                str(max(command.integer("range_4h_version", 0), 0)),
                "--telemetry-flat-path",
                command.text("telemetry_flat_path", "").strip(),
                "--telemetry-tensor-path",
                command.text("telemetry_tensor_path", "").strip(),
                "--telemetry-schema-hash",
                command.text("telemetry_schema_hash", "").strip(),
                "--max-daily-loss-percent",
                str(max(command.number("max_daily_loss_percent", 5.0), 0.0)),
                "--max-open-positions",
                str(max(command.integer("max_open_positions", 1), 0)),
                "--position-size-units",
                str(max(command.number("position_size_units", 0.1), 0.0)),
                "--initial-capital",
                str(max(command.number("initial_capital", 100.0), 0.0)),
                "--paper-shadow-passed",
                "1" if command.text("paper_shadow_passed", "0").strip() == "1" else "0",
                "--account-profile-confirmed",
                "1" if command.text("account_profile_confirmed", "0").strip() == "1" else "0",
                "--symbol-mapping-confirmed",
                "1" if command.text("symbol_mapping_confirmed", "0").strip() == "1" else "0",
                "--kill-switch-enabled",
                "1" if command.text("kill_switch_enabled", "1").strip() != "0" else "0",
                "--explicit-live-confirm",
                command.text("explicit_live_confirm", "").strip(),
                "--write-config",
                "1" if command.text("write_config", "1").strip() != "0" else "0",
                "--require-models",
                "1" if command.text("require_models", "0").strip() == "1" else "0",
                "--storage-root",
                str(self._storage_root),
            ],
            f"Validated Phase134 production hybrid stack on {symbol} {dataset}",
            started,
            timeout=max(command.integer("timeout_minutes", 60), 5) * 60,
        )

    def run_hybrid_paper_shadow(self, command: Command) -> CommandResult:
        """Run Phase134 paper/shadow decisions with real orders disabled."""
        started = time.monotonic()
        flat_path = command.text("flat_path", "").strip()
        flat_args = ["--flat-path", flat_path] if flat_path else []
        return self._run_script(
            command,
            [
                "scripts/run_hybrid_paper_shadow.py",
                "--config-path",
                command.text("config_path", "configs/hybrid_production_stack.json").strip()
                or "configs/hybrid_production_stack.json",
                "--eval-frac",
                str(command.number("eval_frac", 1.0)),
                "--max-windows",
                str(max(command.integer("max_windows", 0), 0)),
                "--allow-validation-fail",
                "1" if command.text("allow_validation_fail", "0").strip() == "1" else "0",
                "--report-title",
                command.text("report_title", "Hybrid production paper shadow").strip()
                or "Hybrid production paper shadow",
                "--storage-root",
                str(self._storage_root),
                *flat_args,
            ],
            "Ran Phase134 hybrid paper shadow (real orders disabled)",
            started,
            timeout=max(command.integer("timeout_minutes", 120), 5) * 60,
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
        # فاز ۱۰۰: label_horizon خالی/0 = خودکار — اسکریپت برای
        # trend_score روی 1D افق 1 (کندل واقعی فردا) و برای بقیه
        # 288 برمی‌دارد. عدد غیرصفر کاربر عیناً پاس می‌شود.
        _lh = command.integer("label_horizon", 0)
        _lh_args = (
            ["--label-horizon", str(max(_lh, 1))]
            if role in ("trend_signal", "trend_score") and _lh
            else []
        )
        _score_loss_args = trend_score_loss_args(command, role)
        _class_weight_args = trend_signal_class_weight_args(command, role)
        _monitor_metric_args = monitor_metric_args(command, role)
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
                dataset if role in ("signal", "trend", "trend_signal", "trend_score") else "5M",
                "--epochs",
                str(max(command.integer("epochs", 1), 1)),
                "--folds",
                str(max(command.integer("folds", 2), 1)),
                "--window",
                str(max(command.integer("window", 500), 2)),
                *_lh_args,
                *_score_loss_args,
                *_class_weight_args,
                *_monitor_metric_args,
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
        if role not in {"signal", "range", "trend", "trend_signal", "trend_score"}:
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
                "trend_score": "1D",
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
            threshold = 0.0  # trend رنگ / trend_score رگرسیون
        # فاز ۶۲: پیچ‌های معماری — 0 = پیش‌فرض نقش (فاز ۶۱)
        _opt_layers = max(command.integer("n_layers", 0), 0)
        _opt_blocks = max(command.integer("n_blocks", 0), 0)
        _opt_arch = []
        if _opt_layers:
            _opt_arch += ["--n-layers", str(_opt_layers)]
        if _opt_blocks:
            _opt_arch += ["--n-blocks", str(_opt_blocks)]
        _lh = command.integer("label_horizon", 0)
        _lh_args = (
            ["--label-horizon", str(max(_lh, 1))]
            if role in ("trend_signal", "trend_score") and _lh
            else []
        )
        _score_loss_args = trend_score_loss_args(command, role)
        _class_weight_args = trend_signal_class_weight_args(command, role)
        _monitor_metric_args = monitor_metric_args(command, role)
        arguments = [
            "scripts/run_dual_models.py",
            "--with-features",
            "--symbol",
            command.text("symbol", "XAUUSD"),
            "--model",
            role,
            "--range-timeframes",
            dataset if role in ("range", "trend") else "1H",
            "--signal-timeframe",
            dataset if role in ("signal", "trend", "trend_signal", "trend_score") else "5M",
            "--threshold",
            str(threshold),
            "--window",
            str(max(command.integer("window", 100), 2)),
            *_opt_arch,
            *_lh_args,
            *_score_loss_args,
            *_class_weight_args,
            *_monitor_metric_args,
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
