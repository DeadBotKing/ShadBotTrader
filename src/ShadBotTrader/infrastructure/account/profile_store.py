"""Persistence and use of broker account profiles (Phase 32).

Profiles are stored as one JSON file. Passwords are never in it — the
file records only which environment variable holds each password, so the
store can be backed up, diffed or emailed without leaking credentials.

The store also builds a connected MT5 provider from a profile and can
verify a profile end to end: connect, read the account, and confirm the
symbols the profile maps actually exist at that broker. Discovering a
bad alias during a live run is far more expensive than discovering it
here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.account.profile import AccountBook, AccountProfile, SymbolMap
from ShadBotTrader.domain.common.errors import ValidationError

DEFAULT_STORE = "configs/accounts.json"


class AccountProfileStore:
    """Reads and writes the profile book."""

    def __init__(self, path: str | Path = DEFAULT_STORE) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> AccountBook:
        """Read the book, returning an empty one when nothing is stored."""
        if not self._path.exists():
            return AccountBook()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise ValidationError(
                f"Cannot read the account store at {self._path}: {error}"
            ) from error
        return AccountBook.from_dict(payload)

    def save(self, book: AccountBook) -> Path:
        """Write the book. Never contains a password."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(book.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return self._path

    # ----------------------------------------------------------- mutation --
    def add(
        self,
        name: str,
        login: int,
        server: str,
        terminal_path: str = "",
        is_demo: bool = True,
        note: str = "",
        symbol_map: Optional[Dict[str, str]] = None,
        make_active: bool = False,
    ) -> AccountProfile:
        book = self.load()
        profile = AccountProfile(
            name=name,
            login=login,
            server=server,
            terminal_path=terminal_path,
            symbol_map=SymbolMap.from_dict(symbol_map),
            is_demo=is_demo,
            note=note,
        )
        book.add(profile, make_active=make_active)
        self.save(book)
        return profile

    def remove(self, name: str) -> None:
        book = self.load()
        book.remove(name)
        self.save(book)

    def activate(self, name: str) -> AccountProfile:
        book = self.load()
        profile = book.activate(name)
        self.save(book)
        return profile

    def set_symbol(self, name: str, canonical: str, broker_symbol: str) -> AccountProfile:
        book = self.load()
        profile = book.get(name)
        profile.symbol_map.set(canonical, broker_symbol)
        book.update(profile)
        self.save(book)
        return profile

    def clear_symbol(self, name: str, canonical: str) -> bool:
        book = self.load()
        profile = book.get(name)
        removed = profile.symbol_map.remove(canonical)
        book.update(profile)
        self.save(book)
        return removed

    def active(self) -> Optional[AccountProfile]:
        return self.load().active_profile


@dataclass
class ProfileCheck:
    """The result of verifying one profile against its broker."""

    profile: str
    connected: bool
    account: Dict[str, Any]
    symbols_checked: int = 0
    missing_symbols: List[str] = None  # type: ignore[assignment]
    suggestions: Dict[str, str] = None  # type: ignore[assignment]
    error: str = ""

    def __post_init__(self) -> None:
        if self.missing_symbols is None:
            self.missing_symbols = []
        if self.suggestions is None:
            self.suggestions = {}

    @property
    def is_usable(self) -> bool:
        return self.connected and not self.missing_symbols

    def summary_lines(self) -> List[str]:
        if not self.connected:
            return [f"[X] {self.profile}: {self.error}"]

        lines = [
            f"[ok] {self.profile}: connected as {self.account.get('login')} "
            f"@ {self.account.get('server')}",
            f"     balance {self.account.get('balance')} " f"{self.account.get('currency')}",
        ]
        if self.missing_symbols:
            lines.append(f"     [!] not found at this broker: {', '.join(self.missing_symbols)}")
            for canonical, suggestion in self.suggestions.items():
                lines.append(f"         {canonical} -> try '{suggestion}'")
        elif self.symbols_checked:
            lines.append(f"     all {self.symbols_checked} mapped symbol(s) exist")
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "connected": self.connected,
            "account": self.account,
            "symbols_checked": self.symbols_checked,
            "missing_symbols": list(self.missing_symbols),
            "suggestions": dict(self.suggestions),
            "usable": self.is_usable,
            "error": self.error,
        }


class AccountConnector:
    """Turns a profile into a live MT5 provider, and verifies it."""

    def __init__(self, store: Optional[AccountProfileStore] = None) -> None:
        self._store = store or AccountProfileStore()

    @property
    def store(self) -> AccountProfileStore:
        return self._store

    def provider_for(
        self,
        profile: AccountProfile,
        password: Optional[str] = None,
        mt5_module: Any = None,
    ) -> Any:
        """Build an MT5 provider bound to ``profile``."""
        from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
            Mt5MarketDataProvider,
        )

        return Mt5MarketDataProvider(
            login=profile.login,
            password=profile.resolve_password(password),
            server=profile.server,
            terminal_path=profile.terminal_path or None,
            mt5_module=mt5_module,
        )

    def check(
        self,
        profile: AccountProfile,
        password: Optional[str] = None,
        mt5_module: Any = None,
    ) -> ProfileCheck:
        """Connect and confirm every mapped symbol exists (never raises)."""
        from ShadBotTrader.infrastructure.data.mt5_symbol_resolver import resolve

        provider = self.provider_for(profile, password, mt5_module)
        try:
            account = provider.account_summary()
        except Exception as error:
            return ProfileCheck(
                profile=profile.name,
                connected=False,
                account={},
                error=f"{type(error).__name__}: {error}",
            )

        missing: List[str] = []
        suggestions: Dict[str, str] = {}
        checked = 0

        try:
            available = provider.available_symbols()
            known = {name.strip().upper() for name in available}
            for canonical, broker_symbol in profile.symbol_map.aliases.items():
                checked += 1
                if broker_symbol.strip().upper() in known:
                    continue
                missing.append(broker_symbol)
                report = resolve(broker_symbol, available)
                if report.best is not None:
                    suggestions[canonical] = report.best.name
        except Exception as error:  # symbol listing is best-effort
            suggestions["_error"] = str(error)
        finally:
            provider.shutdown()

        return ProfileCheck(
            profile=profile.name,
            connected=True,
            account=account,
            symbols_checked=checked,
            missing_symbols=missing,
            suggestions=suggestions,
        )

    def check_named(self, name: str, **kwargs: Any) -> ProfileCheck:
        return self.check(self._store.load().get(name), **kwargs)

    def auto_map(
        self,
        profile: AccountProfile,
        canonical_symbols: List[str],
        mt5_module: Any = None,
        password: Optional[str] = None,
    ) -> Dict[str, str]:
        """Work out this broker's spelling for each canonical symbol.

        Suggestions are returned rather than written: silently binding a
        dataset to a guessed instrument is exactly the mistake this whole
        mechanism exists to prevent.
        """
        from ShadBotTrader.infrastructure.data.mt5_symbol_resolver import resolve

        provider = self.provider_for(profile, password, mt5_module)
        try:
            available = provider.available_symbols()
        finally:
            provider.shutdown()

        found: Dict[str, str] = {}
        for canonical in canonical_symbols:
            report = resolve(canonical, available)
            if report.best is not None:
                found[canonical.strip().upper()] = report.best.name
        return found
