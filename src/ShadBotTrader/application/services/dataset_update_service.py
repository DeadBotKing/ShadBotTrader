"""Incremental dataset updates that stay continuous (Phase 33).

``Fetch market data`` used to write a new version and read only the
latest, so a second fetch **replaced** the history instead of extending
it. Two hundred stored candles plus fifty new ones left fifty.

This service does what the operator expects:

    load what is stored
      -> fetch only what is new
      -> check the join for a real gap (closed days excluded)
      -> backfill the gap from the broker when there is one
      -> merge, de-duplicate, keep the newest N
      -> verify the result is continuous before writing

The order matters. Verification happens *before* the write, so a failed
update leaves the previous dataset untouched rather than half-replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.dataset.continuity import (
    ContinuityReport,
    Gap,
    MarketCalendar,
    analyse_continuity,
    check_join,
    merge_candles,
    timeframe_delta,
)
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe

#: Candles retained per symbol/timeframe (the user's requirement).
DEFAULT_MAX_CANDLES = 100_000

#: Missing candles tolerated at a join before it counts as a gap.
#: Brokers occasionally drop a single bar; treating that as corruption
#: would block every update for no real benefit.
DEFAULT_TOLERANCE = 2


@dataclass
class UpdateResult:
    """What one dataset update did."""

    symbol: str
    timeframe: str
    existing_count: int = 0
    fetched_count: int = 0
    backfilled_count: int = 0
    added_count: int = 0
    replaced_count: int = 0
    dropped_count: int = 0
    final_count: int = 0
    version: int = 0
    gap: Optional[Gap] = None
    gap_resolved: bool = False
    continuity: Optional[ContinuityReport] = None
    refused: bool = False
    reason: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.refused

    def summary_lines(self) -> List[str]:
        if self.refused:
            lines = [f"REFUSED: {self.reason}"]
            if self.gap is not None:
                lines.append(f"  {self.gap.describe()}")
            lines.append("  The stored dataset was NOT modified.")
            return lines

        lines = [
            f"stored before : {self.existing_count:,}",
            f"fetched       : {self.fetched_count:,}",
        ]
        if self.backfilled_count:
            lines.append(f"backfilled    : {self.backfilled_count:,} (gap repaired)")
        lines.extend(
            [
                f"new candles   : {self.added_count:,}",
                f"updated bars  : {self.replaced_count:,}",
            ]
        )
        if self.dropped_count:
            lines.append(
                f"dropped       : {self.dropped_count:,} oldest "
                f"(rolling {self.final_count:,} limit)"
            )
        lines.append(f"stored now    : {self.final_count:,}")

        if self.continuity is not None:
            if self.continuity.is_continuous:
                lines.append("continuity    : OK — no gaps")
            else:
                lines.append(
                    f"continuity    : {len(self.continuity.gaps)} gap(s), "
                    f"{self.continuity.missing_candles:,} candles missing"
                )
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "existing": self.existing_count,
            "fetched": self.fetched_count,
            "backfilled": self.backfilled_count,
            "added": self.added_count,
            "replaced": self.replaced_count,
            "dropped": self.dropped_count,
            "final": self.final_count,
            "version": self.version,
            "gap": self.gap.to_dict() if self.gap else None,
            "gap_resolved": self.gap_resolved,
            "refused": self.refused,
            "reason": self.reason,
            "continuity": self.continuity.to_dict() if self.continuity else None,
        }


class DatasetUpdateService:
    """Appends new candles to a stored history without breaking it."""

    def __init__(
        self,
        candle_store: Any,
        provider: Any = None,
        max_candles: int = DEFAULT_MAX_CANDLES,
        tolerance: int = DEFAULT_TOLERANCE,
    ) -> None:
        self._store = candle_store
        self._provider = provider
        self._max_candles = max_candles
        self._tolerance = tolerance
        #: Why the last backfill attempt returned nothing, if it failed.
        self.last_backfill_error = ""
        #: The broker's spelling to ask for when backfilling, when it
        #: differs from the canonical name the candles are stored under.
        self._broker_symbol: Dict[str, str] = {}

    # ----------------------------------------------------------- reading --
    def stored(self, symbol: str, timeframe: str) -> List[Candle]:
        return list(self._store.query(Symbol(symbol), Timeframe(timeframe)))

    def inspect(self, symbol: str, timeframe: str) -> ContinuityReport:
        """Continuity of what is already stored."""
        candles = self.stored(symbol, timeframe)
        return analyse_continuity(candles, Timeframe(timeframe), tolerance=self._tolerance)

    # ----------------------------------------------------------- updating --
    def update(
        self,
        symbol: str,
        timeframe: str,
        incoming: Sequence[Candle],
        allow_gap: bool = False,
        backfill: bool = True,
    ) -> UpdateResult:
        """Merge ``incoming`` into the stored history.

        Args:
            allow_gap: accept a discontinuity that could not be repaired.
                Off by default: a model trained across an unexplained hole
                learns a price move that never happened.
            backfill: try to fetch the missing range from the provider
                before giving up.
        """
        frame = Timeframe(timeframe)
        existing = self.stored(symbol, timeframe)

        result = UpdateResult(
            symbol=symbol,
            timeframe=timeframe,
            existing_count=len(existing),
            fetched_count=len(incoming),
        )

        if not incoming:
            result.refused = True
            result.reason = "the provider returned no candles"
            return result

        calendar = MarketCalendar.learn(existing) if existing else None
        self.last_backfill_error = ""
        gap = check_join(existing, incoming, frame, calendar, self._tolerance)
        result.gap = gap

        repaired: List[Candle] = []
        if gap is not None:
            if backfill and self._provider is not None:
                repaired = self._backfill(symbol, timeframe, gap)
                result.backfilled_count = len(repaired)
                if repaired:
                    # Re-check with the repair in place: the broker may
                    # have had only part of the missing range.
                    still = check_join(
                        existing,
                        [*repaired, *incoming],
                        frame,
                        calendar,
                        self._tolerance,
                    )
                    result.gap = still
                    result.gap_resolved = still is None
                    gap = still

            if gap is not None and not allow_gap:
                result.refused = True
                result.reason = (
                    f"{gap.missing} candle(s) are missing between the stored "
                    f"history and the new data. Joining them would teach the "
                    f"model a price move that never happened."
                )
                if self.last_backfill_error:
                    result.reason += f" Backfill failed: {self.last_backfill_error}"
                return result

        merged = merge_candles(existing, [*repaired, *incoming], self._max_candles)

        existing_times = {candle.open_time.value for candle in existing}
        incoming_times = {candle.open_time.value for candle in [*repaired, *incoming]}
        result.added_count = len(incoming_times - existing_times)
        result.replaced_count = len(incoming_times & existing_times)
        result.dropped_count = max(len(existing) + result.added_count - len(merged), 0)
        result.final_count = len(merged)

        # Verify BEFORE writing: a failed update must leave the stored
        # dataset exactly as it was.
        result.continuity = analyse_continuity(merged, frame, calendar, tolerance=self._tolerance)
        if not result.continuity.is_continuous and not allow_gap:
            result.refused = True
            result.reason = f"the merged series still has " f"{len(result.continuity.gaps)} gap(s)"
            return result

        result.version = self._write(symbol, timeframe, merged)
        return result

    def fetch_and_update(
        self,
        symbol: str,
        timeframe: str,
        bars: int = 5000,
        allow_gap: bool = False,
        store_as: Optional[str] = None,
    ) -> UpdateResult:
        """Fetch from the provider, then merge — the GUI's path.

        ``symbol`` is the broker's spelling (``XAUUSD_i``); ``store_as``
        is the canonical platform name the candles are filed under
        (``XAUUSD``). Keeping the two apart is what stops one instrument
        turning into two disconnected datasets when a second broker
        spells it differently (Phase 35).
        """
        if self._provider is None:
            return UpdateResult(
                symbol=symbol,
                timeframe=timeframe,
                refused=True,
                reason="no market data provider is configured",
            )

        canonical = (store_as or symbol).strip().upper()
        # The gap repair inside update() must ask the broker using the
        # broker's own spelling, not the canonical one.
        self._broker_symbol[canonical] = symbol
        records = self._provider.fetch_candles(symbol, timeframe, str(bars))
        candles = self._relabel(self._to_candles(records, symbol, timeframe), canonical)
        return self.update(canonical, timeframe, candles, allow_gap=allow_gap)

    def _relabel(self, candles: Sequence[Candle], symbol: str) -> List[Candle]:
        """Re-file broker-named candles under the canonical symbol."""
        target = Symbol(symbol)
        return [
            (
                candle
                if str(candle.symbol) == str(target)
                else Candle(
                    symbol=target,
                    timeframe=candle.timeframe,
                    open_time=candle.open_time,
                    open_price=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )
            )
            for candle in candles
        ]

    # --------------------------------------------------------- internals --
    def _backfill(self, symbol: str, timeframe: str, gap: Gap) -> List[Candle]:
        """Ask the broker for exactly the missing range."""
        fetch_range = getattr(self._provider, "fetch_range", None)
        if not callable(fetch_range):
            return []

        broker_symbol = self._broker_symbol.get(symbol, symbol)

        step = timeframe_delta(Timeframe(timeframe))
        try:
            records = fetch_range(
                broker_symbol,
                timeframe,
                gap.after + step / 2,
                gap.before,
            )
        except Exception as error:
            # A broker that cannot serve the range is a normal outcome —
            # but the reason is recorded rather than swallowed, because a
            # silent empty backfill looks identical to "the history does
            # not exist" and sends the operator hunting in the wrong place.
            self.last_backfill_error = f"{type(error).__name__}: {error}"
            return []

        candles = self._relabel(self._to_candles(records, broker_symbol, timeframe), symbol)
        return [candle for candle in candles if gap.after < candle.open_time.value < gap.before]

    def _to_candles(self, records: Sequence[Any], symbol: str, timeframe: str) -> List[Candle]:
        """Validate and normalise raw provider records into candles."""
        from ShadBotTrader.infrastructure.data.candle_normalizer import CandleNormalizer
        from ShadBotTrader.infrastructure.data.candle_validator import CandleValidator

        validation = CandleValidator().validate(list(records))
        return list(CandleNormalizer().normalize(validation.records).candles)

    def _write(self, symbol: str, timeframe: str, candles: Sequence[Candle]) -> int:
        from ShadBotTrader.domain.dataset.data_layer import DataLayer
        from ShadBotTrader.domain.dataset.dataset_identity import DataKind, DatasetId

        provider_name = getattr(self._provider, "provider_name", "csv")
        dataset_id = DatasetId(
            provider=provider_name,
            kind=DataKind.MARKET_CANDLE,
            symbol=symbol,
            timeframe=timeframe,
            layer=DataLayer.NORMALIZED.value,
        )

        # ``next_version`` counts the RAW directory, but this service only
        # writes normalized candles. Using it here returns a version that
        # already exists on the normalized side and the write is refused,
        # so the next free normalized version is computed directly.
        version = self._next_normalized_version(symbol, timeframe)
        self._store.save_normalized(dataset_id, version, list(candles))
        return version

    def _next_normalized_version(self, symbol: str, timeframe: str) -> int:
        """One past the highest normalized version already on disk."""
        root = getattr(self._store, "_root", None)
        if root is None:  # a store that does not expose its layout
            return 1

        from ShadBotTrader.infrastructure.data.parquet_candle_store import (
            _canonical_symbol,
        )

        directory = Path(root) / "processed" / _canonical_symbol(symbol) / timeframe
        if not directory.is_dir():
            return 1

        versions: List[int] = []
        for path in directory.iterdir():
            if path.suffix != ".parquet" or not path.stem.startswith("v"):
                continue
            try:
                versions.append(int(path.stem[1:]))
            except ValueError:
                continue
        return max(versions, default=0) + 1


def describe_freshness(last_candle: Optional[datetime], timeframe: str) -> Dict[str, Any]:
    """How stale the stored history is, in candles and in time."""
    if last_candle is None:
        return {"known": False}

    now = datetime.now(timezone.utc)
    if last_candle.tzinfo is None:
        last_candle = last_candle.replace(tzinfo=timezone.utc)

    behind = now - last_candle
    step = timeframe_delta(Timeframe(timeframe))
    candles_behind = int(behind / step) if step > timedelta(0) else 0

    return {
        "known": True,
        "last_candle": last_candle.isoformat(),
        "hours_behind": round(behind.total_seconds() / 3600, 1),
        "candles_behind": candles_behind,
        "stale": candles_behind > 2,
    }
