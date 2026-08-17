"""Every run must be reachable from the GUI (Phase 32).

The user's requirement is explicit: from now on everything is launched
from the dashboard. These tests are the guard that keeps it true — if
someone adds a new script or command without a button, one of them fails
rather than the omission being discovered months later.
"""

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from ShadBotTrader.infrastructure.account import AccountProfileStore
from ShadBotTrader.infrastructure.persistence import Database
from ShadBotTrader.presentation.commands.commands import CommandKind
from ShadBotTrader.presentation.commands.handlers import (
    AccountCommandHandlers,
    CommandHandlers,
    descriptors,
)
from ShadBotTrader.presentation.web.server import create_server

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Scripts that are developer utilities rather than platform operations.
#: Each exclusion is deliberate and explained, so the list cannot quietly
#: become a place to hide missing buttons.
NOT_GUI_OPERATIONS = {
    "run_dashboard.py": "starts the GUI itself",
    "run_service.py": "the supervisor that would host the GUI",
    "parquet_view.py": "a file inspector, not a platform run",
    "run_pip.py": "same as the Refresh project state button",
    "run_persistence.py": "a storage demo, superseded by real runs",
    "run_real_data.py": "guided setup wizard, replaced by Accounts + Fetch",
}


@pytest.fixture
def server(tmp_path):
    database = tmp_path / "gui.db"
    Database(database).close()

    store = AccountProfileStore(tmp_path / "accounts.json")
    store.add("demo", 12345, "Test-MT5", make_active=True)
    store.set_symbol("demo", "XAUUSD", "XAUUSD_i")

    httpd = create_server(
        database,
        host="127.0.0.1",
        port=0,
        storage_root=tmp_path / "datasets",
        replay_path=tmp_path / "replay.html",
        account_store=tmp_path / "accounts.json",
    )
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


# ------------------------------------------------------------- coverage ---
class TestEveryRunHasAButton:
    def test_every_command_kind_has_a_handler(self):
        registry = CommandHandlers("x.db").registry()

        missing = set(CommandKind) - set(registry)

        assert not missing, f"no handler for: {[k.value for k in missing]}"

    def test_every_command_kind_has_a_descriptor(self):
        described = {descriptor.kind for descriptor in descriptors()}

        missing = set(CommandKind) - described

        assert not missing, f"no button for: {[k.value for k in missing]}"

    def test_every_script_is_reachable_from_the_gui(self):
        """A new script without a button fails here, not in production."""
        scripts = {path.name for path in (REPO_ROOT / "scripts").glob("run_*.py")} | {
            "parquet_view.py"
        }
        covered = {
            "run_data.py",
            "run_features.py",
            "run_ai.py",
            "run_dual_models.py",
            "run_backtest.py",
            "run_replay.py",
            "run_optimisation.py",
            "run_trading.py",
            "run_execution.py",
            "run_live_loop.py",
            "run_training_dataset.py",
            "run_weekly_update.py",
        }

        unaccounted = scripts - covered - set(NOT_GUI_OPERATIONS)

        assert not unaccounted, (
            f"These scripts have no dashboard button and no documented "
            f"exclusion: {sorted(unaccounted)}"
        )

    def test_the_operational_groups_all_exist(self):
        groups = {descriptor.group for descriptor in descriptors()}

        assert {"Accounts", "Data", "AI", "Simulation", "Trading", "Operations"} <= groups

    def test_each_group_holds_at_least_one_command(self):
        counts: dict[str, int] = {}
        for descriptor in descriptors():
            counts[descriptor.group] = counts.get(descriptor.group, 0) + 1

        assert all(count > 0 for count in counts.values())

    def test_every_descriptor_explains_itself(self):
        for descriptor in descriptors():
            assert descriptor.label, descriptor.kind
            assert len(descriptor.description) > 20, descriptor.kind


# ----------------------------------------------------------------- page ---
class TestDashboardPage:
    def test_every_button_is_rendered(self, server):
        page = get(f"{server}/")

        for descriptor in descriptors():
            assert f'value="{descriptor.action}"' in page, descriptor.action

    def test_the_groups_are_shown(self, server):
        page = get(f"{server}/")

        for group in ("Accounts", "Data", "AI", "Simulation", "Trading", "Operations"):
            assert group in page

    def test_the_account_panel_lists_the_profile(self, server):
        page = get(f"{server}/")

        assert "demo" in page
        assert "Test-MT5" in page

    def test_the_symbol_alias_is_visible(self, server):
        """The operator must see which instrument will actually be traded."""
        page = get(f"{server}/")

        assert "XAUUSD_i" in page

    def test_the_password_variable_is_shown_not_the_password(self, server):
        page = get(f"{server}/")

        assert "SHADBOT_MT5_PASSWORD_DEMO" in page

    def test_the_api_exposes_the_accounts(self, server):
        payload = json.loads(get(f"{server}/api/state"))

        assert payload["accounts"]["active"] == "demo"
        assert "demo" in payload["accounts"]["profiles"]

    def test_a_dangerous_command_is_marked(self, server):
        page = get(f"{server}/")

        assert "destructive" in page

    def test_the_status_endpoint_lists_every_command(self, server):
        payload = json.loads(get(f"{server}/api/status"))

        assert len(payload["available"]) == len(list(CommandKind))


# ------------------------------------------------------- symbol handling ---
class TestSymbolTranslation:
    def handlers(self, tmp_path, aliases=None):
        store = AccountProfileStore(tmp_path / "accounts.json")
        store.add("demo", 12345, "Test-MT5", make_active=True)
        for canonical, broker in (aliases or {}).items():
            store.set_symbol("demo", canonical, broker)
        return CommandHandlers(
            tmp_path / "x.db",
            tmp_path / "datasets",
            tmp_path / "replay.html",
            tmp_path / "accounts.json",
        )

    def test_an_unmapped_symbol_is_used_as_is(self, tmp_path):
        handlers = self.handlers(tmp_path)

        symbol, note = handlers.broker_symbol("XAUUSD")

        assert symbol == "XAUUSD"
        assert "demo" in note

    def test_a_mapped_symbol_is_translated_for_the_broker(self, tmp_path):
        handlers = self.handlers(tmp_path, {"XAUUSD": "XAUUSD_i"})

        symbol, note = handlers.broker_symbol("XAUUSD")

        assert symbol == "XAUUSD_i"
        assert "XAUUSD -> XAUUSD_i" in note

    def test_no_profile_means_no_translation(self, tmp_path):
        handlers = CommandHandlers(
            tmp_path / "x.db",
            tmp_path / "datasets",
            tmp_path / "replay.html",
            tmp_path / "empty.json",
        )

        symbol, note = handlers.broker_symbol("XAUUSD")

        assert symbol == "XAUUSD"
        assert note == ""


# -------------------------------------------------------------- handlers ---
class TestAccountHandlers:
    def handlers(self, tmp_path):
        return AccountCommandHandlers(
            tmp_path / "x.db", tmp_path / "datasets", tmp_path / "accounts.json"
        )

    def command(self, kind, **parameters):
        from ShadBotTrader.presentation.commands.commands import Command

        return Command(kind=kind, parameters=parameters)

    def test_adding_an_account_reports_the_password_variable(self, tmp_path):
        result = self.handlers(tmp_path).add_account(
            self.command(CommandKind.ADD_ACCOUNT, name="demo", login="12345", server="Test-MT5")
        )

        assert result.succeeded
        assert any("SHADBOT_MT5_PASSWORD_DEMO" in line for line in result.lines)

    def test_an_incomplete_account_is_rejected(self, tmp_path):
        result = self.handlers(tmp_path).add_account(
            self.command(CommandKind.ADD_ACCOUNT, name="demo")
        )

        assert not result.succeeded
        assert "required" in result.message

    def test_mapping_a_symbol_persists(self, tmp_path):
        handlers = self.handlers(tmp_path)
        handlers.add_account(
            self.command(CommandKind.ADD_ACCOUNT, name="demo", login="1", server="S")
        )

        result = handlers.map_symbol(
            self.command(CommandKind.MAP_SYMBOL, canonical="XAUUSD", broker="XAUUSD_i")
        )

        assert result.succeeded
        store = AccountProfileStore(tmp_path / "accounts.json")
        assert store.load().get("demo").broker_symbol("XAUUSD") == "XAUUSD_i"

    def test_mapping_without_an_account_is_rejected(self, tmp_path):
        result = self.handlers(tmp_path).map_symbol(
            self.command(CommandKind.MAP_SYMBOL, canonical="XAUUSD", broker="XAUUSD_i")
        )

        assert not result.succeeded

    def test_switching_to_an_unknown_account_fails_clearly(self, tmp_path):
        result = self.handlers(tmp_path).activate_account(
            self.command(CommandKind.ACTIVATE_ACCOUNT, name="ghost")
        )

        assert not result.succeeded

    def test_the_health_check_runs(self, tmp_path):
        result = self.handlers(tmp_path).health_check(self.command(CommandKind.HEALTH_CHECK))

        assert result.lines
        assert "status" in result.lines[0]

    def test_backing_up_without_a_database_is_rejected(self, tmp_path):
        result = self.handlers(tmp_path).backup_database(self.command(CommandKind.BACKUP_DATABASE))

        assert not result.succeeded
        assert "No database" in result.message


# ------------------------------------------------------- first-run path ---
class TestFirstRun:
    """The dashboard must be reachable with nothing set up yet.

    Regression: `serve` used to refuse to start without a database and
    print "run scripts/run_persistence.py first" — a terminal command,
    to reach the GUI whose whole purpose is to replace terminal commands.
    """

    def test_serving_creates_a_missing_database(self, tmp_path, monkeypatch, capsys):
        from ShadBotTrader import dashboard_cli

        database = tmp_path / "brand-new.db"
        started: dict[str, object] = {}

        def fake_serve(path, **kwargs):
            started["path"] = str(path)

        monkeypatch.setattr(dashboard_cli, "serve", fake_serve)

        exit_code = dashboard_cli.main(["--db", str(database), "serve", "--port", "0"])

        assert exit_code == 0
        assert database.exists(), "the dashboard must create its own database"
        assert started["path"] == str(database)
        assert "creating it" in capsys.readouterr().out

    def test_the_created_database_has_the_current_schema(self, tmp_path, monkeypatch):
        from ShadBotTrader import dashboard_cli

        database = tmp_path / "new.db"
        monkeypatch.setattr(dashboard_cli, "serve", lambda path, **kwargs: None)
        dashboard_cli.main(["--db", str(database), "serve"])

        opened = Database(database)
        try:
            assert opened.schema_version >= 1
        finally:
            opened.close()

    def test_an_existing_database_is_left_alone(self, tmp_path, monkeypatch, capsys):
        from ShadBotTrader import dashboard_cli

        database = tmp_path / "existing.db"
        Database(database).close()
        before = database.stat().st_mtime

        monkeypatch.setattr(dashboard_cli, "serve", lambda path, **kwargs: None)
        dashboard_cli.main(["--db", str(database), "serve"])

        assert database.stat().st_mtime == before
        assert "creating it" not in capsys.readouterr().out

    def test_the_empty_page_points_at_buttons_not_scripts(self, tmp_path):
        """Sending the operator back to a shell defeats the dashboard."""
        database = tmp_path / "empty.db"
        Database(database).close()

        httpd = create_server(
            database,
            host="127.0.0.1",
            port=0,
            storage_root=tmp_path / "datasets",
            account_store=tmp_path / "accounts.json",
        )
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            page = get(f"http://127.0.0.1:{port}/")
        finally:
            httpd.shutdown()
            httpd.server_close()

        assert "start here" in page
        assert "Add account" in page
        assert "run_persistence" not in page, "the empty state must not send users to a script"
