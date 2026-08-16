"""Simulation session and configuration (Phase 16, sections 5-7, 12-13)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Mapping, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.simulation_types import SessionStatus, SimulationMode


class SimulationConfiguration:
    """Everything that defines a reproducible run (section 12).

    Two runs sharing a configuration, a dataset and a seed must produce
    identical results (section 10).
    """

    def __init__(
        self,
        initial_capital: Decimal = Decimal("100000"),
        base_currency: str = "USD",
        spread: Decimal = Decimal("2"),
        slippage_rate: Decimal = Decimal("0"),
        commission_rate: Decimal = Decimal("0"),
        seed: int = 42,
        mode: SimulationMode = SimulationMode.BACKTEST,
        warmup_bars: int = 0,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if initial_capital <= 0:
            raise ValidationError("initial_capital must be positive")
        if spread < 0:
            raise ValidationError("spread must not be negative")
        if slippage_rate < 0:
            raise ValidationError("slippage_rate must not be negative")
        if commission_rate < 0:
            raise ValidationError("commission_rate must not be negative")
        if warmup_bars < 0:
            raise ValidationError("warmup_bars must not be negative")

        self._initial_capital = initial_capital
        self._base_currency = base_currency.strip().upper()
        self._spread = spread
        self._slippage_rate = slippage_rate
        self._commission_rate = commission_rate
        self._seed = seed
        self._mode = mode
        self._warmup_bars = warmup_bars
        self._metadata: Dict[str, Any] = dict(metadata or {})

    @property
    def initial_capital(self) -> Decimal:
        return self._initial_capital

    @property
    def base_currency(self) -> str:
        return self._base_currency

    @property
    def spread(self) -> Decimal:
        return self._spread

    @property
    def slippage_rate(self) -> Decimal:
        return self._slippage_rate

    @property
    def commission_rate(self) -> Decimal:
        return self._commission_rate

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def mode(self) -> SimulationMode:
        return self._mode

    @property
    def warmup_bars(self) -> int:
        """Bars consumed before trading starts (indicator warmup)."""
        return self._warmup_bars

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_capital": str(self._initial_capital),
            "base_currency": self._base_currency,
            "spread": str(self._spread),
            "slippage_rate": str(self._slippage_rate),
            "commission_rate": str(self._commission_rate),
            "seed": self._seed,
            "mode": self._mode.value,
            "warmup_bars": self._warmup_bars,
        }


class SimulationSession:
    """One independent run of the simulation platform (section 6)."""

    def __init__(
        self,
        session_id: str,
        configuration: SimulationConfiguration,
        start_time: Timestamp,
        end_time: Optional[Timestamp] = None,
        strategy_id: str = "",
    ) -> None:
        if not session_id.strip():
            raise ValidationError("session_id must not be empty")
        self._session_id = session_id.strip()
        self._configuration = configuration
        self._start_time = start_time
        self._end_time = end_time
        self._strategy_id = strategy_id
        self._status = SessionStatus.CREATED
        self._events_processed = 0
        self._failure_reason = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def configuration(self) -> SimulationConfiguration:
        return self._configuration

    @property
    def start_time(self) -> Timestamp:
        return self._start_time

    @property
    def end_time(self) -> Optional[Timestamp]:
        return self._end_time

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def status(self) -> SessionStatus:
        return self._status

    @property
    def events_processed(self) -> int:
        return self._events_processed

    @property
    def failure_reason(self) -> str:
        return self._failure_reason

    # -- lifecycle ---------------------------------------------------------
    def initializing(self) -> None:
        self._require(SessionStatus.CREATED)
        self._status = SessionStatus.INITIALIZING

    def start(self) -> None:
        self._require(SessionStatus.CREATED, SessionStatus.INITIALIZING)
        self._status = SessionStatus.RUNNING

    def pause(self) -> None:
        """Pause without losing state (section 24)."""
        self._require(SessionStatus.RUNNING)
        self._status = SessionStatus.PAUSED

    def resume(self) -> None:
        self._require(SessionStatus.PAUSED)
        self._status = SessionStatus.RUNNING

    def complete(self) -> None:
        self._require(SessionStatus.RUNNING, SessionStatus.PAUSED)
        self._status = SessionStatus.COMPLETED

    def fail(self, reason: str) -> None:
        self._status = SessionStatus.FAILED
        self._failure_reason = reason

    def cancel(self) -> None:
        self._require(SessionStatus.RUNNING, SessionStatus.PAUSED, SessionStatus.CREATED)
        self._status = SessionStatus.CANCELLED

    def count_event(self) -> None:
        self._events_processed += 1

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        )

    def _require(self, *allowed: SessionStatus) -> None:
        if self._status not in allowed:
            names = ", ".join(status.value for status in allowed)
            raise ValidationError(
                f"Invalid session transition from {self._status.value} (expected {names})"
            )
