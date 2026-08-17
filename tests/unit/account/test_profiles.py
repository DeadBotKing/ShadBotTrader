"""Tests for broker account profiles and symbol mapping (Phase 32).

Two properties carry real risk:

* a password must never reach disk — a credential in a JSON file beside
  the code is one screenshot away from being public;
* symbol translation must be exact — trading the wrong instrument is
  indistinguishable from a strategy failure until the statement arrives.
"""

import json

import pytest

from ShadBotTrader.domain.account import (
    AccountBook,
    AccountProfile,
    SymbolMap,
    password_env_var,
)
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.account import AccountProfileStore


def profile(name: str = "demo", **overrides) -> AccountProfile:
    defaults = dict(name=name, login=53102853, server="Alpari-MT5-Demo")
    defaults.update(overrides)
    return AccountProfile(**defaults)


# ------------------------------------------------------------- symbol map ---
class TestSymbolMap:
    def test_an_unmapped_symbol_passes_through(self):
        """A broker using the standard spelling needs no entry."""
        assert SymbolMap().resolve("XAUUSD") == "XAUUSD"

    def test_a_mapped_symbol_is_translated(self):
        mapping = SymbolMap({"XAUUSD": "XAUUSD_i"})

        assert mapping.resolve("XAUUSD") == "XAUUSD_i"

    def test_lookup_is_case_insensitive(self):
        mapping = SymbolMap({"XAUUSD": "XAUUSD_i"})

        assert mapping.resolve("xauusd") == "XAUUSD_i"

    def test_the_reverse_lookup_recovers_the_canonical_name(self):
        mapping = SymbolMap({"XAUUSD": "XAUUSD_i"})

        assert mapping.canonical_for("XAUUSD_i") == "XAUUSD"

    def test_an_unknown_broker_symbol_reverses_to_itself(self):
        assert SymbolMap().canonical_for("WEIRD") == "WEIRD"

    def test_an_empty_symbol_is_refused(self):
        with pytest.raises(ValidationError):
            SymbolMap().resolve("   ")

    def test_entries_can_be_added_and_removed(self):
        mapping = SymbolMap()
        mapping.set("EURUSD", "EURUSD.i")

        assert mapping.resolve("EURUSD") == "EURUSD.i"
        assert mapping.remove("EURUSD")
        assert mapping.resolve("EURUSD") == "EURUSD"

    def test_removing_something_absent_reports_false(self):
        assert not SymbolMap().remove("NOPE")


# ---------------------------------------------------------------- profile ---
class TestAccountProfile:
    def test_a_valid_profile_is_accepted(self):
        item = profile()

        assert item.login == 53102853
        assert item.server == "Alpari-MT5-Demo"
        assert item.created_at

    @pytest.mark.parametrize("name", ["", "has space", "-starts-with-dash", "a" * 60])
    def test_a_bad_profile_name_is_refused(self, name):
        """The name becomes a filename and an env-var fragment."""
        with pytest.raises(ValidationError):
            profile(name=name)

    def test_a_non_positive_login_is_refused(self):
        with pytest.raises(ValidationError):
            profile(login=0)

    def test_an_empty_server_is_refused(self):
        with pytest.raises(ValidationError):
            profile(server="  ")

    def test_the_password_variable_is_derived_from_the_name(self):
        assert profile("alpari-demo").password_variable == ("SHADBOT_MT5_PASSWORD_ALPARI_DEMO")
        assert password_env_var("broker.b") == "SHADBOT_MT5_PASSWORD_BROKER_B"

    def test_the_password_comes_from_the_environment(self, monkeypatch):
        item = profile("demo")
        monkeypatch.setenv(item.password_variable, "from-env")

        assert item.resolve_password() == "from-env"
        assert item.has_password

    def test_an_explicit_password_wins(self, monkeypatch):
        item = profile("demo")
        monkeypatch.setenv(item.password_variable, "from-env")

        assert item.resolve_password("typed-now") == "typed-now"

    def test_a_shared_fallback_variable_is_honoured(self, monkeypatch):
        monkeypatch.delenv(profile("demo").password_variable, raising=False)
        monkeypatch.setenv("SHADBOT_MT5_PASSWORD", "shared")

        assert profile("demo").resolve_password() == "shared"

    def test_no_password_means_use_the_terminal_session(self, monkeypatch):
        monkeypatch.delenv(profile("demo").password_variable, raising=False)
        monkeypatch.delenv("SHADBOT_MT5_PASSWORD", raising=False)

        assert profile("demo").resolve_password() is None

    def test_the_serialised_form_never_contains_a_password(self, monkeypatch):
        item = profile("demo")
        monkeypatch.setenv(item.password_variable, "top-secret")

        payload = json.dumps(item.to_dict(reveal_secrets=True))

        assert "top-secret" not in payload
        assert "password_variable" in payload

    def test_symbols_translate_through_the_profile(self):
        item = profile(symbol_map=SymbolMap({"XAUUSD": "XAUUSD_i"}))

        assert item.broker_symbol("XAUUSD") == "XAUUSD_i"
        assert item.canonical_symbol("XAUUSD_i") == "XAUUSD"

    def test_a_live_account_is_flagged(self):
        warnings = profile(is_demo=False).warnings()

        assert any("LIVE" in warning for warning in warnings)

    def test_an_empty_alias_map_is_mentioned(self):
        warnings = profile().warnings()

        assert any("alias" in warning for warning in warnings)

    def test_a_profile_round_trips(self):
        original = profile(symbol_map=SymbolMap({"XAUUSD": "XAUUSD_i"}), note="test")

        restored = AccountProfile.from_dict(original.to_dict())

        assert restored.login == original.login
        assert restored.broker_symbol("XAUUSD") == "XAUUSD_i"


# ------------------------------------------------------------------- book ---
class TestAccountBook:
    def test_the_first_profile_becomes_active(self):
        book = AccountBook()
        book.add(profile("first"))

        assert book.active == "first"

    def test_duplicate_names_are_refused(self):
        book = AccountBook()
        book.add(profile("demo"))

        with pytest.raises(ValidationError, match="already exists"):
            book.add(profile("demo"))

    def test_switching_the_active_profile(self):
        book = AccountBook()
        book.add(profile("a"))
        book.add(profile("b"))

        activated = book.activate("b")

        assert book.active == "b"
        assert activated.last_used_at

    def test_removing_the_active_profile_picks_another(self):
        """A dangling active pointer would fail far from this call."""
        book = AccountBook()
        book.add(profile("a"))
        book.add(profile("b"))
        book.activate("a")

        book.remove("a")

        assert book.active == "b"

    def test_removing_the_last_profile_clears_the_pointer(self):
        book = AccountBook()
        book.add(profile("only"))

        book.remove("only")

        assert book.active == ""
        assert book.active_profile is None

    def test_an_unknown_profile_lists_the_known_ones(self):
        book = AccountBook()
        book.add(profile("known"))

        with pytest.raises(ValidationError, match="known"):
            book.get("missing")

    def test_the_book_round_trips(self):
        book = AccountBook()
        book.add(profile("a", symbol_map=SymbolMap({"XAUUSD": "XAUUSD_i"})))
        book.add(profile("b"))
        book.activate("b")

        restored = AccountBook.from_dict(book.to_dict())

        assert restored.names == ["a", "b"]
        assert restored.active == "b"
        assert restored.get("a").broker_symbol("XAUUSD") == "XAUUSD_i"


# ------------------------------------------------------------------ store ---
class TestProfileStore:
    def test_an_absent_store_loads_as_empty(self, tmp_path):
        book = AccountProfileStore(tmp_path / "none.json").load()

        assert len(book) == 0

    def test_a_profile_survives_a_save_and_load(self, tmp_path):
        store = AccountProfileStore(tmp_path / "accounts.json")
        store.add("demo", 12345, "Test-MT5", make_active=True)

        book = store.load()

        assert book.names == ["demo"]
        assert book.active == "demo"

    def test_the_file_never_contains_a_password(self, tmp_path, monkeypatch):
        path = tmp_path / "accounts.json"
        store = AccountProfileStore(path)
        created = store.add("demo", 12345, "Test-MT5")
        monkeypatch.setenv(created.password_variable, "hunter2")

        store.save(store.load())  # rewrite with the password set

        assert "hunter2" not in path.read_text(encoding="utf-8")

    def test_symbols_can_be_mapped_and_cleared(self, tmp_path):
        store = AccountProfileStore(tmp_path / "accounts.json")
        store.add("demo", 12345, "Test-MT5")

        store.set_symbol("demo", "XAUUSD", "XAUUSD_i")
        assert store.load().get("demo").broker_symbol("XAUUSD") == "XAUUSD_i"

        assert store.clear_symbol("demo", "XAUUSD")
        assert store.load().get("demo").broker_symbol("XAUUSD") == "XAUUSD"

    def test_two_profiles_keep_independent_mappings(self):
        """The whole reason the map is per profile."""
        book = AccountBook()
        book.add(profile("alpari", symbol_map=SymbolMap({"XAUUSD": "XAUUSD"})))
        book.add(profile("other", symbol_map=SymbolMap({"XAUUSD": "XAUUSD_i"})))

        assert book.get("alpari").broker_symbol("XAUUSD") == "XAUUSD"
        assert book.get("other").broker_symbol("XAUUSD") == "XAUUSD_i"

    def test_a_damaged_store_fails_with_the_path(self, tmp_path):
        path = tmp_path / "accounts.json"
        path.write_text("{ not json", encoding="utf-8")

        with pytest.raises(ValidationError, match="accounts.json"):
            AccountProfileStore(path).load()

    def test_activating_through_the_store_persists(self, tmp_path):
        store = AccountProfileStore(tmp_path / "accounts.json")
        store.add("a", 1, "S1", make_active=True)
        store.add("b", 2, "S2")

        store.activate("b")

        assert AccountProfileStore(tmp_path / "accounts.json").load().active == "b"
