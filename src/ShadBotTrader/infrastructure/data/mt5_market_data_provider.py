"""MetaTrader 5 market-data provider — real broker price history.

Implements the existing ``MarketDataProvider`` port, so the Data
Platform, Feature Platform, backtester and optimiser all consume real
prices without a single change anywhere else. That is the payoff of the
port/adapter boundary set up in Phase 11.

PLATFORM NOTE
    The ``MetaTrader5`` package is **Windows-only** — it talks to a
    running MT5 terminal through a local IPC channel. On Linux/macOS the
    import fails, which is why it is an optional dependency and imported
    lazily. Everything else in the platform keeps working without it.

USAGE
    pip install MetaTrader5

    # the MT5 terminal must be installed, running and logged in
    provider = Mt5MarketDataProvider()
    records = provider.fetch_candles("XAUUSD", "5M", source="5000")

``source`` carries the number of bars to fetch (a string, to satisfy the
port contract). Use ``fetch_range`` for an explicit date window.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.ports import MarketDataProvider
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord

# ShadBotTrader timeframe -> MetaTrader5 constant name.
# Resolved lazily so this module imports without the package present.
_TIMEFRAME_NAMES: Dict[str, str] = {
    "1M": "TIMEFRAME_M1",
    "2M": "TIMEFRAME_M2",
    "3M": "TIMEFRAME_M3",
    "4M": "TIMEFRAME_M4",
    "5M": "TIMEFRAME_M5",
    "6M": "TIMEFRAME_M6",
    "10M": "TIMEFRAME_M10",
    "12M": "TIMEFRAME_M12",
    "15M": "TIMEFRAME_M15",
    "20M": "TIMEFRAME_M20",
    "30M": "TIMEFRAME_M30",
    "1H": "TIMEFRAME_H1",
    "2H": "TIMEFRAME_H2",
    "3H": "TIMEFRAME_H3",
    "4H": "TIMEFRAME_H4",
    "6H": "TIMEFRAME_H6",
    "8H": "TIMEFRAME_H8",
    "12H": "TIMEFRAME_H12",
    "1D": "TIMEFRAME_D1",
    "D1": "TIMEFRAME_D1",
    "1W": "TIMEFRAME_W1",
    "W1": "TIMEFRAME_W1",
    "1MN": "TIMEFRAME_MN1",
    "MN1": "TIMEFRAME_MN1",
}

_INSTALL_HINT = (
    "The MetaTrader5 package is required for live broker data.\n"
    "  pip install MetaTrader5\n"
    "It is Windows-only and needs the MT5 terminal installed, running "
    "and logged in. On Linux/macOS use the CSV provider instead "
    "(shadbot-data ingest --source path/to/file.csv)."
)


def load_mt5() -> Any:
    """Import the MetaTrader5 module or fail with actionable guidance."""
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - platform dependent
        raise ImportError(_INSTALL_HINT) from exc
    return mt5


def is_available() -> bool:
    """True when the MetaTrader5 package can be imported."""
    try:
        load_mt5()
    except ImportError:
        return False
    return True


def supported_timeframes() -> List[str]:
    """Timeframes this provider can translate for MT5."""
    return sorted(_TIMEFRAME_NAMES)


class Mt5MarketDataProvider(MarketDataProvider):
    """Fetches real candle history from a MetaTrader 5 terminal.

    The provider performs NO validation or transformation: per the port
    contract it moves rows from the broker into raw records, and the
    Data Platform decides whether they are acceptable. Every MT5 field
    the platform does not model (spread, real_volume) is preserved in
    ``extra`` so nothing the broker sent is lost.
    """

    def __init__(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        terminal_path: Optional[str] = None,
        mt5_module: Any = None,
    ) -> None:
        """Create the provider.

        Credentials are optional: when omitted, the already-authenticated
        session of the running terminal is used, which avoids putting a
        password anywhere near the codebase.

        ``mt5_module`` exists so the adapter can be tested without a
        broker; production code leaves it as None.
        """
        self._login = login
        self._password = password
        self._server = server
        self._terminal_path = terminal_path
        self._mt5 = mt5_module
        self._initialized = False

    # -- port contract ------------------------------------------------------
    @property
    def provider_name(self) -> str:
        return "mt5"

    def fetch_candles(self, symbol: str, timeframe: str, source: str) -> List[RawCandleRecord]:
        """Fetch the most recent ``source`` bars for ``symbol``.

        ``source`` is the bar count as a string, e.g. ``"5000"``.
        """
        try:
            count = int(str(source).strip() or "1000")
        except ValueError as exc:
            raise ValidationError(f"MT5 source must be a bar count, got {source!r}") from exc
        if count < 1:
            raise ValidationError("Bar count must be >= 1")

        mt5 = self._ensure_initialized()
        rates = mt5.copy_rates_from_pos(symbol, self._resolve_timeframe(timeframe), 0, count)
        return self._to_records(rates, symbol, timeframe, mt5)

    # -- extended API ---------------------------------------------------------
    def fetch_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[RawCandleRecord]:
        """Fetch every bar between ``start`` and ``end`` (UTC)."""
        if end <= start:
            raise ValidationError("end must be after start")

        mt5 = self._ensure_initialized()
        rates = mt5.copy_rates_range(
            symbol,
            self._resolve_timeframe(timeframe),
            self._as_utc(start),
            self._as_utc(end),
        )
        return self._to_records(rates, symbol, timeframe, mt5)

    def available_symbols(self, pattern: str = "") -> List[str]:
        """List the symbols the terminal exposes."""
        mt5 = self._ensure_initialized()
        symbols = mt5.symbols_get(pattern) if pattern else mt5.symbols_get()
        return sorted(item.name for item in (symbols or ()))

    def live_quote(self, symbol: str) -> Dict[str, Any]:
        """The current bid/ask and the spread BETWEEN them (Phase 45).

        The spread is read from the live tick rather than assumed. Gold
        spreads float: they widen at the session roll and around news,
        and a fixed guess is wrong in whichever direction hurts — too
        low and the backtest flatters itself, too high and the strategy
        refuses trades it should take.

        ``spread_points`` from ``symbol_info`` is an integer in points
        and is only a snapshot; ``ask - bid`` from the tick is the price
        actually available right now, so that is what is authoritative
        here. The integer is returned alongside for diagnostics.
        """
        mt5 = self._ensure_initialized()

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ConnectionError(
                f"MT5 has no tick for {symbol!r}: {self._last_error(mt5)}. "
                f"Is the symbol visible in Market Watch?"
            )

        bid = float(getattr(tick, "bid", 0.0) or 0.0)
        ask = float(getattr(tick, "ask", 0.0) or 0.0)
        if bid <= 0 or ask <= 0:
            raise ConnectionError(
                f"MT5 returned an unusable tick for {symbol!r} "
                f"(bid={bid}, ask={ask}). The market may be closed."
            )

        info = mt5.symbol_info(symbol)
        point = float(getattr(info, "point", 0.0) or 0.0) if info is not None else 0.0
        digits = int(getattr(info, "digits", 0) or 0) if info is not None else 0
        spread_points = getattr(info, "spread", None) if info is not None else None

        spread = ask - bid
        mid = (ask + bid) / 2.0

        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread": spread,
            "spread_pct": (spread / mid) if mid else 0.0,
            "spread_points": spread_points,
            "point": point,
            "digits": digits,
            "time": getattr(tick, "time", None),
        }

    def account_summary(self) -> Dict[str, Any]:
        """Basic account facts, useful for verifying the connection."""
        mt5 = self._ensure_initialized()
        info = mt5.account_info()
        if info is None:
            raise ConnectionError(f"MT5 account_info failed: {self._last_error(mt5)}")
        return {
            "login": getattr(info, "login", None),
            "server": getattr(info, "server", None),
            "currency": getattr(info, "currency", None),
            "balance": getattr(info, "balance", None),
            "equity": getattr(info, "equity", None),
            "leverage": getattr(info, "leverage", None),
            "trade_mode": getattr(info, "trade_mode", None),
        }

    def shutdown(self) -> None:
        """Close the terminal connection."""
        if self._initialized and self._mt5 is not None:
            self._mt5.shutdown()
            self._initialized = False

    def __enter__(self) -> "Mt5MarketDataProvider":
        self._ensure_initialized()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.shutdown()

    # -- internals ------------------------------------------------------------
    def _ensure_initialized(self) -> Any:
        """Connect to the terminal once, then reuse the session."""
        if self._mt5 is None:
            self._mt5 = load_mt5()
        if self._initialized:
            return self._mt5

        kwargs: Dict[str, Any] = {}
        if self._terminal_path:
            kwargs["path"] = self._terminal_path
        if self._login is not None:
            kwargs["login"] = self._login
        if self._password:
            kwargs["password"] = self._password
        if self._server:
            kwargs["server"] = self._server

        if not self._mt5.initialize(**kwargs):
            raise ConnectionError(
                f"Could not connect to the MetaTrader 5 terminal: "
                f"{self._last_error(self._mt5)}. Make sure the terminal is "
                f"installed, running and logged in."
            )
        self._initialized = True
        return self._mt5

    def _resolve_timeframe(self, timeframe: str) -> Any:
        """Translate a platform timeframe into an MT5 constant."""
        key = timeframe.strip().upper()
        name = _TIMEFRAME_NAMES.get(key)
        if name is None:
            raise ValidationError(
                f"Unsupported timeframe '{timeframe}'. "
                f"Supported: {', '.join(supported_timeframes())}"
            )
        mt5 = self._mt5 if self._mt5 is not None else load_mt5()
        constant = getattr(mt5, name, None)
        if constant is None:  # pragma: no cover - defensive
            raise ValidationError(f"MetaTrader5 has no constant '{name}'")
        return constant

    def _to_records(
        self,
        rates: Optional[Sequence[Any]],
        symbol: str,
        timeframe: str,
        mt5: Any,
    ) -> List[RawCandleRecord]:
        """Convert MT5 rate rows into raw records.

        An empty result is an error, not an empty dataset: silently
        ingesting nothing would look like a successful run.
        """
        if rates is None:
            raise ConnectionError(
                f"MT5 returned no data for {symbol} {timeframe}: " f"{self._last_error(mt5)}"
            )
        if len(rates) == 0:
            raise ValidationError(
                f"MT5 returned zero bars for {symbol} {timeframe}. Check that "
                f"the symbol exists and is visible in Market Watch."
            )

        records: List[RawCandleRecord] = []
        for rate in rates:
            row = self._row_to_mapping(rate)
            moment = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
            records.append(
                RawCandleRecord(
                    symbol=symbol,
                    timeframe=timeframe.upper(),
                    timestamp=moment.isoformat(),
                    open=str(row["open"]),
                    high=str(row["high"]),
                    low=str(row["low"]),
                    close=str(row["close"]),
                    # tick_volume is what retail FX actually reports;
                    # real_volume is usually 0 outside exchange feeds.
                    volume=str(row.get("tick_volume", 0)),
                    extra={
                        "provider": self.provider_name,
                        "spread": row.get("spread"),
                        "real_volume": row.get("real_volume"),
                    },
                )
            )
        return records

    @staticmethod
    def _row_to_mapping(rate: Any) -> Dict[str, Any]:
        """Read a numpy structured row (or any mapping) uniformly."""
        fields = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
        if hasattr(rate, "dtype") and getattr(rate.dtype, "names", None):
            return {name: rate[name] for name in rate.dtype.names}
        if isinstance(rate, dict):
            return dict(rate)
        return {name: getattr(rate, name, None) for name in fields}

    @staticmethod
    def _as_utc(moment: datetime) -> datetime:
        """MT5 expects naive UTC datetimes."""
        if moment.tzinfo is None:
            return moment
        return moment.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _last_error(mt5: Any) -> str:
        try:
            return str(mt5.last_error())
        except Exception:  # pragma: no cover - defensive
            return "unknown error"
