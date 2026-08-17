"""Resolve what a broker actually calls an instrument (Phase 11, §14-15).

Every broker names the same instrument differently. Gold alone appears as
``XAUUSD``, ``XAUUSD.i``, ``XAUUSDm``, ``XAUUSD_i``, ``XAUUSD.raw``,
``GOLD``, ``GOLDmicro`` — and a symbol that exists is still unusable
until it is visible in Market Watch.

This module turns "the symbol you asked for was not found" into "here is
what your broker calls it". It performs no I/O of its own: the caller
supplies the symbol list, which keeps it testable without a terminal and
keeps the MT5 dependency in one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

#: Instrument aliases seen across retail brokers, mapped to the stem the
#: platform uses internally. Order matters only for readability.
_ALIASES: Dict[str, Sequence[str]] = {
    "XAUUSD": ("XAUUSD", "GOLD", "XAUUSDO", "GOLDSPOT"),
    "XAGUSD": ("XAGUSD", "SILVER", "SILVERSPOT"),
    "EURUSD": ("EURUSD", "EUR/USD"),
    "GBPUSD": ("GBPUSD", "GBP/USD"),
    "USDJPY": ("USDJPY", "USD/JPY"),
    "BTCUSD": ("BTCUSD", "BITCOIN", "BTCUSDT"),
    "USOIL": ("USOIL", "WTI", "CRUDE", "XTIUSD"),
}

#: Every name the alias table knows, used to decide whether peeling a
#: suffix produced something real.
_KNOWN_CORES = frozenset(
    {stem for stem in _ALIASES}
    | {alias.upper().replace("/", "") for aliases in _ALIASES.values() for alias in aliases}
)

#: Account-type decoration brokers append. Longest first so that
#: ``MICRO`` is consumed before ``M`` and ``XAUUSDMICRO`` does not
#: collapse to ``XAUUSDICRO``.
_SUFFIXES = (
    "MICRO",
    "CENT",
    "CASH",
    "SPOT",
    "ECN",
    "PRO",
    "RAW",
    "STP",
    "SB",
    "I",
    "M",
    "C",
    "E",
    "Z",
)

#: Prefixes some brokers put in front of the instrument.
_PREFIXES = ("FX", "CFD")

#: Names that are already the instrument. Stripping a trailing letter from
#: these would corrupt them (``GOLD`` -> ``GOL``), so they are protected.
_PROTECTED = frozenset({"GOLD", "SILVER", "WTI", "CRUDE", "BITCOIN"})


def _strip_separated(text: str) -> str:
    """Drop dot/underscore/dash separated decoration: ``XAUUSD.pro.ecn``."""
    head, *rest = re.split(r"[._\-]", text)
    for part in rest:
        if part and part not in _SUFFIXES:
            # Not decoration we recognise — keep the name intact rather
            # than guessing, so an unknown instrument is never mangled.
            return text
    return head


def normalise(symbol: str) -> str:
    """Strip broker decoration down to a comparable core.

    ``XAUUSD.i``, ``XAUUSDm`` and ``xauusd_pro`` all reduce to ``XAUUSD``.
    Names the platform recognises as instruments in their own right
    (``GOLD``) are never truncated.
    """
    cleaned = symbol.strip().upper().replace("/", "")
    if not cleaned:
        return ""

    for prefix in _PREFIXES:
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix) + 2:
            cleaned = cleaned[len(prefix) :].lstrip("._-")
            break

    cleaned = _strip_separated(cleaned)
    if cleaned in _PROTECTED:
        return cleaned

    # Now peel a directly-attached suffix, e.g. XAUUSDm / GOLDmicro.
    for suffix in _SUFFIXES:
        if not cleaned.endswith(suffix):
            continue
        stem = cleaned[: -len(suffix)]
        # A currency pair is six characters; never cut below a plausible
        # instrument name, or "USTEC" would become "UST".
        if len(stem) >= 4 and (stem in _PROTECTED or len(stem) >= 6 or stem in _KNOWN_CORES):
            return stem
    return cleaned


def canonical_stem(symbol: str) -> str:
    """Map a symbol onto the platform's internal name, if it is known."""
    core = normalise(symbol)
    for stem, aliases in _ALIASES.items():
        if core == stem or core in {alias.upper().replace("/", "") for alias in aliases}:
            return stem
    return core


@dataclass(frozen=True)
class SymbolMatch:
    """One candidate broker symbol, with why it was chosen."""

    name: str
    score: int
    reason: str

    @property
    def is_exact(self) -> bool:
        return self.score >= 100


@dataclass
class ResolutionReport:
    """Everything found for one requested instrument."""

    requested: str
    matches: List[SymbolMatch] = field(default_factory=list)
    searched: int = 0

    @property
    def found(self) -> bool:
        return bool(self.matches)

    @property
    def best(self) -> SymbolMatch | None:
        return self.matches[0] if self.matches else None

    def advice(self) -> List[str]:
        """Actionable next steps, written for a human staring at a terminal."""
        if not self.searched:
            return [
                "The terminal reported no symbols at all.",
                "Open MetaTrader 5, then in Market Watch right-click -> Show All.",
            ]
        if not self.found:
            return [
                f"No symbol resembling '{self.requested}' among {self.searched} instruments.",
                "In MT5: Market Watch -> right-click -> Show All, then list again:",
                "    shadbot-data mt5-symbols --pattern " + normalise(self.requested)[:3],
                "Brokers rename instruments freely (XAUUSD.i, XAUUSDm, GOLD).",
            ]
        best = self.best
        assert best is not None
        if best.is_exact:
            return [f"Use --symbol {best.name}"]
        return [
            f"'{self.requested}' does not exist, but '{best.name}' looks like it.",
            f"    shadbot-data mt5-ingest --symbol {best.name} --timeframe 5M --bars 5000",
        ]


def resolve(requested: str, available: Sequence[str]) -> ResolutionReport:
    """Rank ``available`` broker symbols by how well they match ``requested``.

    Scoring is deliberately transparent rather than clever — a wrong
    instrument is an expensive mistake, so every candidate carries the
    reason it was suggested and the caller stays in control.
    """
    report = ResolutionReport(requested=requested, searched=len(available))
    if not available:
        return report

    wanted_raw = requested.strip().upper()
    wanted_core = normalise(requested)
    wanted_stem = canonical_stem(requested)

    scored: List[SymbolMatch] = []
    for name in available:
        upper = name.strip().upper()
        core = normalise(name)
        stem = canonical_stem(name)

        if upper == wanted_raw:
            scored.append(SymbolMatch(name, 100, "exact match"))
        elif core == wanted_core:
            scored.append(SymbolMatch(name, 90, "same instrument, broker suffix"))
        elif stem == wanted_stem:
            scored.append(SymbolMatch(name, 80, f"known alias of {wanted_stem}"))
        elif wanted_core and wanted_core in upper:
            scored.append(SymbolMatch(name, 60, "contains the requested name"))
        elif wanted_stem and wanted_stem in upper:
            scored.append(SymbolMatch(name, 50, f"contains {wanted_stem}"))

    # highest score first; ties broken by the shortest (least decorated) name
    scored.sort(key=lambda match: (-match.score, len(match.name), match.name))
    report.matches = scored
    return report
