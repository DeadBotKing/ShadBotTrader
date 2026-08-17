"""Broker account profiles and per-account symbol mapping (Phase 32).

One installation must serve several accounts — a demo and a live one, or
two brokers side by side — and each broker names instruments its own way.
Alpari calls gold ``XAUUSD``; another broker calls the same instrument
``XAUUSD_i`` or ``GOLD``.

Two ideas keep that manageable:

**The profile owns the connection.** Login, server and terminal path
travel together, because a login without its server is meaningless and
mixing them across brokers is how an order lands on the wrong account.

**The alias map is per profile.** The platform speaks one canonical name
internally (``XAUUSD``) and each profile translates to whatever its
broker uses. Datasets, models and backtests therefore stay comparable
across accounts instead of fragmenting into ``XAUUSD``, ``XAUUSD_i`` and
``GOLD`` versions of the same thing.

**Passwords are never written to the profile store.** They live in the
OS environment (or are typed per session) and the profile only records
*which* variable holds them. A password in a JSON file beside the code
is one screenshot away from being public.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.common.errors import ValidationError

#: Environment variable holding a profile's password, by profile name.
PASSWORD_ENV_TEMPLATE = "SHADBOT_MT5_PASSWORD_{profile}"

#: Characters allowed in a profile name — it becomes a filename and an
#: environment-variable fragment, so it stays boring on purpose.
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$")


def password_env_var(profile_name: str) -> str:
    """The environment variable that holds this profile's password."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "_", profile_name).upper()
    return PASSWORD_ENV_TEMPLATE.format(profile=cleaned)


@dataclass
class SymbolMap:
    """Canonical name -> the name this broker actually uses.

    Lookups are case-insensitive and fall back to the canonical name:
    a broker that happens to use the standard spelling needs no entry at
    all, so the map stays short and only records genuine differences.
    """

    aliases: Dict[str, str] = field(default_factory=dict)

    def resolve(self, canonical: str) -> str:
        """The broker's name for ``canonical``."""
        if not canonical or not canonical.strip():
            raise ValidationError("symbol must not be empty")
        key = canonical.strip().upper()
        return self.aliases.get(key, canonical.strip())

    def canonical_for(self, broker_symbol: str) -> str:
        """Reverse lookup: the platform name for a broker symbol."""
        target = (broker_symbol or "").strip().upper()
        for canonical, broker in self.aliases.items():
            if broker.strip().upper() == target:
                return canonical
        return broker_symbol.strip()

    def set(self, canonical: str, broker_symbol: str) -> None:
        if not canonical.strip() or not broker_symbol.strip():
            raise ValidationError("both canonical and broker symbol are required")
        self.aliases[canonical.strip().upper()] = broker_symbol.strip()

    def remove(self, canonical: str) -> bool:
        return self.aliases.pop(canonical.strip().upper(), None) is not None

    @property
    def is_empty(self) -> bool:
        return not self.aliases

    def to_dict(self) -> Dict[str, str]:
        return dict(self.aliases)

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, Any]]) -> "SymbolMap":
        return cls(
            aliases={
                str(key).strip().upper(): str(value).strip()
                for key, value in (payload or {}).items()
                if str(key).strip() and str(value).strip()
            }
        )


@dataclass
class AccountProfile:
    """Everything needed to connect to one broker account.

    ``password`` is deliberately absent. :meth:`resolve_password` reads it
    from the environment at connect time so it never reaches disk.
    """

    name: str
    login: int
    server: str
    terminal_path: str = ""
    symbol_map: SymbolMap = field(default_factory=SymbolMap)
    is_demo: bool = True
    note: str = ""
    created_at: str = ""
    last_used_at: str = ""

    def __post_init__(self) -> None:
        if not _NAME_PATTERN.match(self.name or ""):
            raise ValidationError(
                f"Profile name '{self.name}' is invalid. Use letters, digits, "
                f"'-' or '_' (max 48 characters) — the name becomes a filename."
            )
        if self.login <= 0:
            raise ValidationError("login must be a positive account number")
        if not (self.server or "").strip():
            raise ValidationError("server must not be empty (e.g. Alpari-MT5-Demo)")
        self.server = self.server.strip()
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------ secrets --
    @property
    def password_variable(self) -> str:
        return password_env_var(self.name)

    def resolve_password(self, explicit: Optional[str] = None) -> Optional[str]:
        """The password for this profile, or None when it is not set.

        Order: an explicitly supplied value (typed this session), then the
        profile-specific environment variable, then a shared fallback.
        ``None`` means "use the terminal's existing session", which is the
        safest default: MetaTrader is usually already logged in.
        """
        if explicit:
            return explicit
        return os.environ.get(self.password_variable) or os.environ.get("SHADBOT_MT5_PASSWORD")

    @property
    def has_password(self) -> bool:
        return self.resolve_password() is not None

    # ------------------------------------------------------------ symbols --
    def broker_symbol(self, canonical: str) -> str:
        """Translate a platform symbol into this broker's spelling."""
        return self.symbol_map.resolve(canonical)

    def canonical_symbol(self, broker_symbol: str) -> str:
        return self.symbol_map.canonical_for(broker_symbol)

    # ----------------------------------------------------------- lifecycle --
    def touch(self) -> None:
        """Record that this profile was just used."""
        self.last_used_at = datetime.now(timezone.utc).isoformat()

    def warnings(self) -> List[str]:
        """Things worth telling the operator before connecting."""
        messages: List[str] = []
        if not self.is_demo:
            messages.append(
                f"'{self.name}' is marked LIVE (account {self.login}). "
                f"Orders placed here move real money."
            )
        if self.symbol_map.is_empty:
            messages.append(
                "No symbol aliases are set. If this broker renames instruments "
                "(XAUUSD_i, GOLD, ...), add a mapping so datasets stay comparable."
            )
        return messages

    def to_dict(self, reveal_secrets: bool = False) -> Dict[str, Any]:
        """Serialisable form. Never contains a password."""
        payload: Dict[str, Any] = {
            "name": self.name,
            "login": self.login,
            "server": self.server,
            "terminal_path": self.terminal_path,
            "symbol_map": self.symbol_map.to_dict(),
            "is_demo": self.is_demo,
            "note": self.note,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "password_variable": self.password_variable,
            "password_set": self.has_password,
        }
        if reveal_secrets:
            # Even here the password is not included: nothing in this
            # object holds it, by design.
            payload["password"] = "(read from the environment at connect time)"
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AccountProfile":
        return cls(
            name=str(payload.get("name", "")),
            login=int(payload.get("login", 0)),
            server=str(payload.get("server", "")),
            terminal_path=str(payload.get("terminal_path", "")),
            symbol_map=SymbolMap.from_dict(payload.get("symbol_map")),
            is_demo=bool(payload.get("is_demo", True)),
            note=str(payload.get("note", "")),
            created_at=str(payload.get("created_at", "")),
            last_used_at=str(payload.get("last_used_at", "")),
        )


@dataclass
class AccountBook:
    """The set of known profiles, with one marked active."""

    profiles: Dict[str, AccountProfile] = field(default_factory=dict)
    active: str = ""

    def add(self, profile: AccountProfile, make_active: bool = False) -> None:
        if profile.name in self.profiles:
            raise ValidationError(
                f"A profile named '{profile.name}' already exists. "
                f"Remove it first, or choose another name."
            )
        self.profiles[profile.name] = profile
        if make_active or not self.active:
            self.active = profile.name

    def update(self, profile: AccountProfile) -> None:
        if profile.name not in self.profiles:
            raise ValidationError(f"No profile named '{profile.name}'")
        self.profiles[profile.name] = profile

    def remove(self, name: str) -> None:
        if name not in self.profiles:
            raise ValidationError(f"No profile named '{name}'")
        del self.profiles[name]
        if self.active == name:
            # Never leave a dangling active pointer: the next lookup
            # would fail somewhere far from this call.
            self.active = next(iter(self.profiles), "")

    def get(self, name: str) -> AccountProfile:
        profile = self.profiles.get(name)
        if profile is None:
            known = ", ".join(sorted(self.profiles)) or "none"
            raise ValidationError(f"No profile named '{name}'. Known: {known}")
        return profile

    def activate(self, name: str) -> AccountProfile:
        profile = self.get(name)
        self.active = name
        profile.touch()
        return profile

    @property
    def active_profile(self) -> Optional[AccountProfile]:
        return self.profiles.get(self.active) if self.active else None

    @property
    def names(self) -> List[str]:
        return sorted(self.profiles)

    def __len__(self) -> int:
        return len(self.profiles)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active": self.active,
            "profiles": {
                name: profile.to_dict() for name, profile in sorted(self.profiles.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AccountBook":
        book = cls()
        for name, entry in (payload.get("profiles") or {}).items():
            entry.setdefault("name", name)
            book.profiles[name] = AccountProfile.from_dict(entry)
        active = str(payload.get("active", ""))
        book.active = active if active in book.profiles else next(iter(book.profiles), "")
        return book
