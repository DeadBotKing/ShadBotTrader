"""Dashboard HTTP server (Phase 19).

Built on the standard library so the GUI adds no dependency.

Routes
    GET  /             the dashboard page
    GET  /replay       the last recorded backtest replay, bar by bar
    GET  /data         candlestick chart and dataset inspection
    GET  /api/state    the same data as JSON
    GET  /api/status   what the command bus is doing right now
    GET  /health       liveness probe
    POST /run          dispatch a command (only when actions are enabled)

The command surface is a **closed set**: ``/run`` accepts only the
``CommandKind`` values the bus knows, and each one is handled by an
application service. The GUI still performs no trading, AI or risk logic
itself (§4) — it dispatches intent (§3, §12-13).

Actions can be switched off entirely with ``allow_commands=False``, which
restores the strictly read-only behaviour.
"""

from __future__ import annotations

import json
from html import escape as html_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from ShadBotTrader.presentation.commands.bus import CommandBus
from ShadBotTrader.presentation.commands.commands import Command, CommandKind
from ShadBotTrader.presentation.commands.handlers import descriptors
from ShadBotTrader.presentation.gateway.dashboard_gateway import DashboardGateway
from ShadBotTrader.presentation.web.renderer import render_dashboard


class DashboardHandler(BaseHTTPRequestHandler):
    """Serves the dashboard and dispatches commands."""

    database_path: str = "shadbot.db"
    storage_root: str = "datasets"
    replay_path: str = "replay.html"
    account_store: str = "configs/accounts.json"
    allow_commands: bool = True
    bus: Optional[CommandBus] = None
    server_version = "ShadBotTrader/1.1"

    # -- routing --------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        route = urlparse(self.path)
        query = parse_qs(route.query)
        session = query.get("session", [None])[0]

        try:
            if route.path in ("/", "/index.html"):
                self._send_html(self._page(session))
            elif route.path == "/replay":
                self._send_html(self._replay())
            elif route.path == "/data":
                self._send_html(self._data_page(query))
            elif route.path == "/api/data":
                self._send_json(self._data_payload(query))
            elif route.path == "/api/range-forecast":
                self._send_json(self._range_forecast_payload(query))
            elif route.path == "/api/state":
                self._send_json(self._state(session))
            elif route.path == "/api/status":
                self._send_json(self._status())
            elif route.path == "/api/log":
                self._send_json(self._run_log(query))
            elif route.path == "/health":
                self._send_json({"status": "ok", "database": self.database_path})
            elif route.path == "/favicon.ico":
                self._send(204, "text/plain", b"")
            else:
                self._send_json({"error": "not found", "path": route.path}, status=404)
        except Exception as error:  # pragma: no cover - defensive
            self._send_json({"error": str(error)}, status=500)

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path)
        if route.path != "/run":
            self._send_json({"error": "not found", "path": route.path}, status=404)
            return

        if not self.allow_commands or self.bus is None:
            self._send_json(
                {
                    "error": "This dashboard is read-only.",
                    "detail": "It was started with actions disabled.",
                },
                status=405,
            )
            return

        parameters = self._read_form()
        raw_kind = parameters.pop("command", "")
        try:
            kind = CommandKind(raw_kind)
        except ValueError:
            self._send_json(
                {
                    "error": f"Unknown command: {raw_kind!r}",
                    "known": [item.value for item in CommandKind],
                },
                status=400,
            )
            return

        # Long jobs must not block the HTTP response.
        result = self.bus.dispatch_async(Command(kind=kind, parameters=parameters))

        if self._wants_json():
            self._send_json(result.to_dict(), status=202)
        else:
            self._redirect("/?started=" + kind.value)

    def do_PUT(self) -> None:  # noqa: N802
        self._refuse()

    def do_DELETE(self) -> None:  # noqa: N802
        self._refuse()

    def do_PATCH(self) -> None:  # noqa: N802
        self._refuse()

    def _refuse(self) -> None:
        """Only POST /run is accepted; nothing else may change state."""
        self._send_json(
            {
                "error": "Unsupported method.",
                "detail": "The dashboard exposes exactly one action endpoint: POST /run",
            },
            status=405,
        )

    # -- content --------------------------------------------------------
    def _page(self, session: Optional[str]) -> str:
        gateway = DashboardGateway.open(self.database_path)
        view = gateway.dashboard(session)
        points = (
            gateway.equity_points(view.portfolio.session_id) if view.portfolio is not None else []
        )
        gateway.database.close()

        bus = self.bus
        return render_dashboard(
            view,
            points,
            commands=descriptors(self.storage_root) if (self.allow_commands and bus) else (),
            result=bus.last_result() if bus else None,
            history=bus.history()[:8] if bus else (),
            busy=bus.running if bus else None,
            busy_seconds=bus.running_for_seconds if bus else 0.0,
            accounts=self._accounts(),
        )

    def _accounts(self) -> dict[str, Any]:
        """The account book, or an empty one when nothing is configured."""
        from ShadBotTrader.infrastructure.account import AccountProfileStore

        try:
            return AccountProfileStore(self.account_store).load().to_dict()
        except Exception:
            # A damaged account file must not take the dashboard down.
            return {}

    def _replay(self) -> str:
        """Serve the recorded replay, or explain how to record one."""
        path = Path(self.replay_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>No replay yet</title>"
            "<style>body{background:#0e1117;color:#e6edf3;font-family:ui-monospace,"
            "monospace;padding:32px}a{color:#58a6ff}code{background:#161b22;"
            "padding:2px 6px;border-radius:4px}</style></head><body>"
            "<h1>No replay recorded yet</h1>"
            "<p>Press <b>Record a replay</b> on the dashboard, or run:</p>"
            "<p><code>python -m ShadBotTrader.backtest_cli replay --out "
            f"{html_escape(str(path))}</code></p>"
            "<p><a href='/'>&#8592; back to the dashboard</a></p>"
            "</body></html>"
        )

    def _selected_series(self, query: dict[str, list[str]]) -> tuple[str, str]:
        """Which symbol/timeframe the page is showing.

        Falls back to the first stored series so the page is useful on the
        very first visit, before anything has been chosen.
        """
        from ShadBotTrader.presentation.gateway.data_inspector import DataInspector

        raw = query.get("series", [""])[0]
        if "|" in raw:
            symbol, timeframe = raw.split("|", 1)
            if symbol.strip() and timeframe.strip():
                return symbol.strip(), timeframe.strip()

        available = DataInspector(self.storage_root).available_series()
        if available:
            return available[0]["symbol"], available[0]["timeframe"]
        return "XAUUSD", "5M"

    def _data_page(self, query: dict[str, list[str]]) -> str:
        from ShadBotTrader.presentation.gateway.data_inspector import DataInspector
        from ShadBotTrader.presentation.gateway.range_forecast_inspector import (
            RangeForecastInspector,
        )
        from ShadBotTrader.presentation.web.data_renderer import render_data_page

        inspector = DataInspector(self.storage_root)
        symbol, timeframe = self._selected_series(query)

        try:
            # فاز ۸۶-ب: همهٔ مدل‌های رنج موجود — نه فقط هم‌تایم‌فریم
            inspector_rf = RangeForecastInspector(self.storage_root)
            models_all = inspector_rf.available_models("1D")
            models_all += [
                m
                for m in inspector_rf.available_models("1H")
                if m["model_id"] not in {x["model_id"] for x in models_all}
            ]
            models = models_all
        except Exception:
            models = []

        return render_data_page(
            candles=inspector.candles(symbol, timeframe).to_dict(),
            matrix=inspector.training_matrix(symbol, timeframe).to_dict(),
            features=inspector.features(),
            series=inspector.available_series(),
            selected={"symbol": symbol, "timeframe": timeframe},
            range_models=models,
        )

    def _range_forecast_payload(self, query: dict[str, list[str]]) -> dict[str, Any]:
        """فاز ۸۵ — مسیر پیش‌بینی رنج برای یک کندل انتخابی روی /data."""
        from ShadBotTrader.presentation.gateway.range_forecast_inspector import (
            RangeForecastInspector,
        )

        def _q(name: str, default: str = "") -> str:
            return query.get(name, [default])[0]

        symbol = _q("symbol", "XAUUSD")
        timeframe = _q("timeframe", "1H")
        model_id = _q("model", "gold_range_1h")
        try:
            bar_index = int(_q("bar", "0"))
        except ValueError:
            self._send_json({"error": "bar must be an integer"})
            return
        try:
            inspector = RangeForecastInspector(self.storage_root)
            forecast = inspector.forecast_at(
                symbol=symbol,
                timeframe=timeframe,
                model_id=model_id,
                bar_index=bar_index,
            )
            self._send_json(forecast.to_dict())
        except Exception as error:
            self._send_json({"error": f"{type(error).__name__}: {error}"})

    def _data_payload(self, query: dict[str, list[str]]) -> dict[str, Any]:
        """The same information as JSON, for scripting or checking."""
        from ShadBotTrader.presentation.gateway.data_inspector import DataInspector

        inspector = DataInspector(self.storage_root)
        symbol, timeframe = self._selected_series(query)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": inspector.candles(symbol, timeframe).to_dict(),
            "matrix": inspector.training_matrix(symbol, timeframe).to_dict(),
            "features": inspector.features(),
            "series": inspector.available_series(),
        }

    def _state(self, session: Optional[str]) -> dict[str, Any]:
        gateway = DashboardGateway.open(self.database_path)
        view = gateway.dashboard(session)
        payload = view.to_dict()
        if view.portfolio is not None:
            payload["equity"] = [
                {"timestamp": point.timestamp, "value": point.value}
                for point in gateway.equity_points(view.portfolio.session_id)
            ]
        gateway.database.close()
        payload["commands"] = self._status()
        payload["accounts"] = self._accounts()
        return payload

    def _status(self) -> dict[str, Any]:
        bus = self.bus
        if bus is None or not self.allow_commands:
            return {"enabled": False, "busy": False, "history": []}
        running = bus.running
        return {
            "enabled": True,
            "busy": bus.is_busy,
            "running": running.value if running else None,
            "running_for_seconds": round(bus.running_for_seconds, 1),
            "available": [item.action for item in descriptors(self.storage_root)],
            "history": [item.to_dict() for item in bus.history()],
        }

    def _run_log(self, query: dict[str, list[str]]) -> dict[str, Any]:
        """The live output of a running (or just-finished) command.

        Polled by the dashboard every two seconds while a command runs,
        so a long training job shows its epochs as they happen instead of
        looking frozen until it exits (Phase 36).
        """
        from ShadBotTrader.presentation.commands.handlers import read_run_log

        bus = self.bus
        running = bus.running.value if (bus is not None and bus.running) else None
        action = (query.get("command", [None])[0] or running or "").strip()

        if not action:
            return {"command": None, "busy": False, "lines": []}

        return {
            "command": action,
            "busy": bool(bus is not None and bus.is_busy),
            "running": running,
            "running_for_seconds": round(bus.running_for_seconds, 1) if bus else 0.0,
            "lines": read_run_log(action, lines=int(query.get("lines", ["200"])[0] or 200)),
        }

    # -- request helpers -------------------------------------------------
    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")

        if "application/json" in content_type:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return {}
            return {str(key): str(value) for key, value in payload.items()}

        return {key: values[0] for key, values in parse_qs(body).items()}

    def _wants_json(self) -> bool:
        accept = self.headers.get("Accept", "")
        content_type = self.headers.get("Content-Type", "")
        return "application/json" in accept or "application/json" in content_type

    # -- responses ------------------------------------------------------
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_html(self, markup: str) -> None:
        self._send(200, "text/html; charset=utf-8", markup.encode("utf-8"))

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def _redirect(self, location: str) -> None:
        """Post/Redirect/Get: a refresh must not resubmit the command."""
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print(f"  {self.command} {self.path}")


def create_server(
    database_path: str | Path = "shadbot.db",
    host: str = "0.0.0.0",
    port: int = 8080,
    allow_commands: bool = True,
    storage_root: str | Path = "datasets",
    replay_path: str | Path = "replay.html",
    account_store: str | Path = "configs/accounts.json",
) -> ThreadingHTTPServer:
    """Build the dashboard server.

    Binds to 0.0.0.0 by default so the page is reachable from outside the
    container it runs in. Pass ``allow_commands=False`` for a strictly
    read-only viewer.
    """
    bus = (
        CommandBus.with_defaults(
            str(database_path), str(storage_root), str(replay_path), str(account_store)
        )
        if allow_commands
        else None
    )
    handler = type(
        "BoundDashboardHandler",
        (DashboardHandler,),
        {
            "database_path": str(database_path),
            "storage_root": str(storage_root),
            "replay_path": str(replay_path),
            "account_store": str(account_store),
            "allow_commands": allow_commands,
            "bus": bus,
        },
    )
    return ThreadingHTTPServer((host, port), handler)


def serve(
    database_path: str | Path = "shadbot.db",
    host: str = "0.0.0.0",
    port: int = 8080,
    allow_commands: bool = True,
    storage_root: str | Path = "datasets",
    replay_path: str | Path = "replay.html",
    account_store: str | Path = "configs/accounts.json",
) -> None:
    """Run the dashboard until interrupted."""
    server = create_server(
        database_path,
        host,
        port,
        allow_commands,
        storage_root,
        replay_path,
        account_store,
    )
    shown = "localhost" if host in ("0.0.0.0", "") else host

    print("=== ShadBotTrader dashboard ===")
    print(f"  database : {database_path}")
    print(f"  url      : http://{shown}:{port}")
    print(f"  api      : http://{shown}:{port}/api/state")
    print(f"  replay   : http://{shown}:{port}/replay")
    print(f"  data     : http://{shown}:{port}/data")
    if allow_commands:
        print(f"  actions  : {len(descriptors())} buttons enabled (POST /run)")
        print("             the GUI dispatches intent; services do the work")
    else:
        print("  actions  : disabled (read-only)")
    print("\n  Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopping ...")
    finally:
        server.shutdown()
        server.server_close()
