"""Command definitions and results (Phase 19, sections 11-13).

A Command is the user's *intent*, expressed as data:

    User clicks "Fetch data"  ->  FetchMarketDataCommand

The GUI builds the command and hands it to the bus. It never performs
the work itself — that stays in the application services, exactly as
§4 requires.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CommandStatus(str, Enum):
    """Lifecycle of a dispatched command."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class CommandKind(str, Enum):
    """Every operation the dashboard may request.

    Deliberately a closed set: the GUI cannot invent an operation, and a
    reviewer can see the entire surface in one place.
    """

    # -- accounts (Phase 32) --------------------------------------------
    ADD_ACCOUNT = "add_account"
    ACTIVATE_ACCOUNT = "activate_account"
    REMOVE_ACCOUNT = "remove_account"
    CHECK_ACCOUNT = "check_account"
    MAP_SYMBOL = "map_symbol"
    AUTO_MAP_SYMBOLS = "auto_map_symbols"

    # -- data and features ----------------------------------------------
    FETCH_MARKET_DATA = "fetch_market_data"
    COMPUTE_FEATURES = "compute_features"
    BUILD_DATASET = "build_dataset"
    WEEKLY_UPDATE = "weekly_update"
    BUILD_TIMEFRAME = "build_timeframe"
    EVALUATE_MODEL = "evaluate_model"
    INSPECT_DATASET = "inspect_dataset"

    # -- AI ---------------------------------------------------------------
    TRAIN_MODEL = "train_model"
    TRAIN_DUAL_MODELS = "train_dual_models"
    OPTIMISE_LEARNING_RATE = "optimise_learning_rate"

    # -- simulation and trading ------------------------------------------
    RUN_BACKTEST = "run_backtest"
    RECORD_REPLAY = "record_replay"
    RUN_OPTIMISATION = "run_optimisation"
    RUN_TRADING_CYCLE = "run_trading_cycle"
    RUN_EXECUTION_DEMO = "run_execution_demo"
    RUN_LIVE_TICK = "run_live_tick"

    # -- operations --------------------------------------------------------
    BACKUP_DATABASE = "backup_database"
    HEALTH_CHECK = "health_check"
    REFRESH_PROJECT_STATE = "refresh_project_state"


@dataclass(frozen=True)
class Command:
    """A request to run one operation, with its parameters."""

    kind: CommandKind
    parameters: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get(self, name: str, default: Any = None) -> Any:
        return self.parameters.get(name, default)

    def text(self, name: str, default: str = "") -> str:
        value = self.parameters.get(name, default)
        return str(value) if value is not None else default

    def integer(self, name: str, default: int = 0) -> int:
        raw = self.parameters.get(name, default)
        try:
            return int(str(raw))
        except (TypeError, ValueError):
            return default

    def number(self, name: str, default: float = 0.0) -> float:
        raw = self.parameters.get(name, default)
        try:
            return float(str(raw))
        except (TypeError, ValueError):
            return default

    def flag(self, name: str) -> bool:
        raw = self.parameters.get(name)
        return str(raw).lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class CommandResult:
    """What happened when a command ran."""

    kind: CommandKind
    status: CommandStatus
    message: str = ""
    detail: str = ""
    lines: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    finished_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def success(
        cls,
        kind: CommandKind,
        message: str,
        lines: Optional[List[str]] = None,
        duration: float = 0.0,
    ) -> "CommandResult":
        return cls(
            kind=kind,
            status=CommandStatus.SUCCEEDED,
            message=message,
            lines=lines or [],
            duration_seconds=duration,
        )

    @classmethod
    def failure(
        cls,
        kind: CommandKind,
        message: str,
        detail: str = "",
        duration: float = 0.0,
    ) -> "CommandResult":
        return cls(
            kind=kind,
            status=CommandStatus.FAILED,
            message=message,
            detail=detail,
            duration_seconds=duration,
        )

    @classmethod
    def rejected(cls, kind: CommandKind, message: str) -> "CommandResult":
        """Refused before running — a precondition was not met."""
        return cls(kind=kind, status=CommandStatus.REJECTED, message=message)

    @property
    def succeeded(self) -> bool:
        return self.status is CommandStatus.SUCCEEDED

    @property
    def tone(self) -> str:
        """Semantic class for the UI."""
        if self.status is CommandStatus.SUCCEEDED:
            return "positive"
        if self.status is CommandStatus.RUNNING:
            return "warning"
        return "negative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "status": self.status.value,
            "message": self.message,
            "detail": self.detail,
            "lines": self.lines,
            "duration_seconds": round(self.duration_seconds, 2),
            "finished_at": self.finished_at.isoformat(),
        }


@dataclass(frozen=True)
class CommandDescriptor:
    """UI metadata for one command: label, help text, form fields."""

    kind: CommandKind
    label: str
    description: str
    fields: List["CommandField"] = field(default_factory=list)
    danger: bool = False
    slow: bool = False
    #: UI section this command belongs to. With thirty buttons on one
    #: page, grouping is the difference between a control panel and a wall.
    group: str = "General"

    @property
    def action(self) -> str:
        return self.kind.value


@dataclass(frozen=True)
class CommandField:
    """One input on a command's form."""

    name: str
    label: str
    default: str = ""
    kind: str = "text"  # text | number | checkbox | select
    hint: str = ""
    #: Allowed values when ``kind`` is ``select``. The view renders these
    #: as a dropdown so the operator picks from what actually exists
    #: instead of typing a name and discovering the typo three minutes
    #: into a training run (Phase 40).
    options: tuple[str, ...] = ()

    @property
    def is_select(self) -> bool:
        return self.kind == "select" and bool(self.options)
