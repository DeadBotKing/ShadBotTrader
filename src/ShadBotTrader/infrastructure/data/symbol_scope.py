"""Find the name a symbol's candles are actually stored under (Phase 35).

The platform speaks one canonical name (``XAUUSD``); a broker may call
the same instrument ``XAUUSD_i`` or ``GOLD``. Phase 32 introduced the
per-profile alias map for exactly that, but ``Fetch market data`` still
wrote the candles under the *broker's* spelling while every other run
read the canonical one. The result was two disconnected datasets for one
instrument, and a "Build training dataset" that found nothing.

From Phase 35 the rule is one line long:

    fetch under the broker's name, store under the canonical one.

This module is the safety net for what was already written the old way.
It looks for stored candles under the canonical name first, then under
every alias the profile knows, and reports which one it used — so an
operator with a pre-Phase-35 ``XAUUSD_i`` directory keeps working while
being told, in plain words, what is going on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe


@dataclass(frozen=True)
class StoredSymbol:
    """Which stored symbol answers for a requested one."""

    requested: str
    resolved: str
    stored_count: int = 0
    note: str = ""
    candidates: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return self.stored_count > 0

    @property
    def is_alias(self) -> bool:
        return self.found and self.resolved != self.requested


def alias_candidates(symbol: str, profile: Any = None) -> List[str]:
    """Every name this instrument might be stored under, best first.

    Order matters: the canonical name wins, because that is where new
    data goes. Aliases are only a fallback for history written before
    Phase 35.
    """
    canonical = symbol.strip().upper()
    names: List[str] = [canonical]

    if profile is not None:
        try:
            broker = profile.broker_symbol(canonical)
        except Exception:
            broker = ""
        if broker and broker.upper() not in {name.upper() for name in names}:
            names.append(broker)

        try:
            reverse = profile.canonical_symbol(canonical)
        except Exception:
            reverse = ""
        if reverse and reverse.upper() not in {name.upper() for name in names}:
            names.append(reverse)

    return names


def resolve_stored_symbol(
    store: Any,
    symbol: str,
    timeframe: str,
    profile: Any = None,
) -> StoredSymbol:
    """The stored symbol that actually holds candles for ``symbol``."""
    candidates = alias_candidates(symbol, profile)
    frame = Timeframe(timeframe)

    for name in candidates:
        try:
            count = len(store.query(Symbol(name), frame))
        except Exception:
            count = 0
        if count:
            note = (
                ""
                if name == candidates[0]
                else (
                    f"no candles under '{candidates[0]}'; using the broker-named "
                    f"history stored as '{name}' (written before Phase 35)"
                )
            )
            return StoredSymbol(
                requested=candidates[0],
                resolved=name,
                stored_count=count,
                note=note,
                candidates=tuple(candidates),
            )

    return StoredSymbol(
        requested=candidates[0],
        resolved=candidates[0],
        stored_count=0,
        note=f"no stored candles for {timeframe} under any of: {', '.join(candidates)}",
        candidates=tuple(candidates),
    )


def stored_symbols(storage_root: str | Path) -> List[str]:
    """Every symbol that has normalized candles on disk."""
    processed = Path(storage_root) / "processed"
    if not processed.is_dir():
        return []
    return sorted(entry.name for entry in processed.iterdir() if entry.is_dir())
