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


# ---------------------------------------------- the read-only boundary -----
class TestReadOnlyOverHttp:
    def _send(self, url: str, method: str):
        request = urllib.request.Request(url, method=method, data=b"{}")
        return urllib.request.urlopen(request, timeout=10)

    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
    def test_mutating_methods_are_refused(self, server, method):
        """Phase 19 §4: the GUI cannot execute, train or modify."""
        with pytest.raises(urllib.error.HTTPError) as error:
            self._send(f"{server}/", method)
        assert error.value.code == 405

    def test_refusal_explains_why(self, server):
        try:
            self._send(f"{server}/", "POST")
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            assert "read-only" in payload["error"].lower()
            assert "Phase 19" in payload["detail"]

    def test_no_endpoint_accepts_a_trade(self, server):
        """There is simply no route that could place an order."""
        for path in ("/trade", "/order", "/execute", "/api/trade"):
            with pytest.raises(urllib.error.HTTPError) as error:
                get(f"{server}{path}")
            assert error.value.code == 404


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
