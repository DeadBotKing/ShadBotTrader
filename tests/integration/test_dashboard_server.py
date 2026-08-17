"""Integration tests for the dashboard HTTP server (Phase 19).

Starts the real server on an ephemeral port and drives it over HTTP, so
routing, content types and — most importantly — the read-only boundary
are verified end to end.
"""

import json
import threading
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

from ShadBotTrader.domain.execution.execution_types import ExecutionStatus
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.persistence import Database, SqlitePortfolioLedger
from ShadBotTrader.presentation.web.server import create_server
from tests.unit.strategy.conftest import BASE_TIME

XAU = Symbol("XAUUSD_i")


def d(value: str) -> Decimal:
    return Decimal(value)


@pytest.fixture
def server(tmp_path):
    """A running dashboard server with one stored position."""
    path = tmp_path / "server.db"
    database = Database(path)
    ledger = SqlitePortfolioLedger(database, session_id="http", starting_cash=d("100"))
    ledger.apply(
        ExecutionResult(
            intent_id="i1",
            order_id="o1",
            status=ExecutionStatus.FILLED,
            requested_quantity=d("2"),
            fills=[
                Fill(
                    fill_id="f1",
                    order_id="o1",
                    symbol=XAU,
                    side=OrderSide.BUY,
                    quantity=d("2"),
                    price=Price(d("2000")),
                    executed_at=Timestamp(BASE_TIME),
                    fee=Money(d("0.4"), "USD"),
                )
            ],
        )
    )
    database.close()

    httpd = create_server(path, host="127.0.0.1", port=0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    httpd.shutdown()
    httpd.server_close()


def get(url: str):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.headers, response.read().decode("utf-8")


# ------------------------------------------------------------- routes ------
def test_health_endpoint(server):
    status, _, body = get(f"{server}/health")
    assert status == 200
    assert json.loads(body)["status"] == "ok"


def test_dashboard_page_renders(server):
    status, headers, body = get(f"{server}/")
    assert status == 200
    assert "text/html" in headers["Content-Type"]
    assert body.startswith("<!DOCTYPE html>")
    assert "ShadBotTrader" in body


def test_dashboard_shows_stored_data(server):
    _, _, body = get(f"{server}/")
    assert "XAUUSD_i" in body
    assert "Portfolio" in body


def test_api_returns_json(server):
    status, headers, body = get(f"{server}/api/state")
    assert status == 200
    assert "application/json" in headers["Content-Type"]

    payload = json.loads(body)
    assert payload["system"]["schema_version"] == 1
    assert payload["portfolio"]["positions"][0]["symbol"] == "XAUUSD_i"


def test_unknown_route_returns_404(server):
    with pytest.raises(urllib.error.HTTPError) as error:
        get(f"{server}/does-not-exist")
    assert error.value.code == 404


def test_responses_are_not_cached(server):
    """The dashboard reflects live state; a cached page would mislead."""
    _, headers, _ = get(f"{server}/")
    assert headers["Cache-Control"] == "no-store"


def test_page_is_self_contained(server):
    """No network in the preview sandbox: nothing external may be needed."""
    _, _, body = get(f"{server}/")
    assert "<style>" in body
    assert "<script" not in body.lower()
    assert "cdn" not in body.lower()


def test_action_buttons_are_rendered(server):
    """The user asked for buttons; they must actually be on the page."""
    _, _, body = get(f"{server}/")
    assert "Fetch market data" in body
    assert "Update features" in body
    assert "Retrain the model" in body
    assert 'action="/run"' in body
    assert "<button" in body


# ------------------------------------------------ the command boundary -----
class TestCommandSurface:
    """Phase 19 §3 lists Command Dispatch as a GUI responsibility, and
    §12-13 define the path. The GUI may ask for work; it may not do the
    work, and the set of things it can ask for is closed."""

    def _send(self, url: str, method: str, body: bytes = b"{}"):
        request = urllib.request.Request(
            url,
            method=method,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        return urllib.request.urlopen(request, timeout=10)

    @pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
    def test_other_mutating_methods_are_refused(self, server, method):
        with pytest.raises(urllib.error.HTTPError) as error:
            self._send(f"{server}/", method)
        assert error.value.code == 405

    def test_post_is_only_accepted_on_run(self, server):
        with pytest.raises(urllib.error.HTTPError) as error:
            self._send(f"{server}/", "POST")
        assert error.value.code == 404

    def test_unknown_command_is_rejected(self, server):
        """The GUI cannot invent an operation."""
        with pytest.raises(urllib.error.HTTPError) as error:
            self._send(f"{server}/run", "POST", json.dumps({"command": "drop_tables"}).encode())
        assert error.value.code == 400
        payload = json.loads(error.value.read().decode("utf-8"))
        assert "Unknown command" in payload["error"]
        assert "known" in payload

    def test_no_endpoint_accepts_a_raw_trade(self, server):
        """There is no route that could place an order directly."""
        for path in ("/trade", "/order", "/execute", "/api/trade"):
            with pytest.raises(urllib.error.HTTPError) as error:
                get(f"{server}{path}")
            assert error.value.code == 404

    def test_status_lists_the_available_commands(self, server):
        _, _, body = get(f"{server}/api/status")
        payload = json.loads(body)
        assert payload["enabled"] is True
        assert "run_backtest" in payload["available"]
        assert "train_model" in payload["available"]

    def test_a_valid_command_is_accepted_and_runs_async(self, server):
        response = self._send(
            f"{server}/run",
            "POST",
            json.dumps({"command": "refresh_project_state"}).encode(),
        )
        assert response.status == 202
        payload = json.loads(response.read().decode("utf-8"))
        assert payload["status"] == "running"


class TestReadOnlyMode:
    """The dashboard can still be started as a strict viewer."""

    def test_actions_can_be_disabled(self, tmp_path):
        from ShadBotTrader.presentation.web.server import create_server

        path = tmp_path / "ro.db"
        Database(path).close()

        httpd = create_server(path, host="127.0.0.1", port=0, allow_commands=False)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            _, _, body = get(f"http://127.0.0.1:{port}/api/status")
            assert json.loads(body)["enabled"] is False

            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/run",
                method="POST",
                data=json.dumps({"command": "run_backtest"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=10)
            assert error.value.code == 405
            payload = json.loads(error.value.read().decode("utf-8"))
            assert "read-only" in payload["error"].lower()

            # and no buttons are rendered
            _, _, page = get(f"http://127.0.0.1:{port}/")
            assert "<button" not in page
        finally:
            httpd.shutdown()
            httpd.server_close()


# ----------------------------------------------------------- empty state ---
def test_empty_database_serves_guidance(tmp_path):
    path = tmp_path / "empty.db"
    Database(path).close()

    httpd = create_server(path, host="127.0.0.1", port=0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        _, _, body = get(f"http://127.0.0.1:{port}/")
        assert "Nothing recorded yet" in body
        assert "run_persistence" in body
    finally:
        httpd.shutdown()
        httpd.server_close()


# --------------------------------------------------------------- replay ---
class TestReplayRoute:
    """/replay serves the recorded player, or explains how to make one."""

    def _serve(self, tmp_path, replay_name="replay.html"):
        path = tmp_path / "replay.db"
        Database(path).close()
        httpd = create_server(
            path,
            host="127.0.0.1",
            port=0,
            replay_path=tmp_path / replay_name,
        )
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return httpd, f"http://127.0.0.1:{port}"

    def test_missing_replay_explains_how_to_record_one(self, tmp_path):
        httpd, base = self._serve(tmp_path)
        try:
            status, headers, body = get(f"{base}/replay")
            assert status == 200
            assert "text/html" in headers["Content-Type"]
            assert "No replay recorded yet" in body
            assert "backtest_cli replay" in body
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_a_recorded_replay_is_served_verbatim(self, tmp_path):
        (tmp_path / "replay.html").write_text(
            "<!DOCTYPE html><html><body>RECORDED PLAYER</body></html>",
            encoding="utf-8",
        )
        httpd, base = self._serve(tmp_path)
        try:
            status, _, body = get(f"{base}/replay")
            assert status == 200
            assert "RECORDED PLAYER" in body
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_the_dashboard_links_to_the_replay(self, tmp_path):
        httpd, base = self._serve(tmp_path)
        try:
            _, _, page = get(f"{base}/")
            assert 'href="/replay"' in page
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_record_replay_is_an_offered_command(self, tmp_path):
        httpd, base = self._serve(tmp_path)
        try:
            _, _, body = get(f"{base}/api/status")
            assert "record_replay" in json.loads(body)["available"]
        finally:
            httpd.shutdown()
            httpd.server_close()
