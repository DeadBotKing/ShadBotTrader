"""Dashboard HTTP server (Phase 19).

Built on the standard library so the GUI adds no dependency.

Routes
    GET  /             the dashboard page
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
            elif route.path == "/api/state":
                self._send_json(self._state(session))
            elif route.path == "/api/status":
                self._send_json(self._status())
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
            commands=descriptors() if (self.allow_commands and bus) else (),
            result=bus.last_result() if bus else None,
            history=bus.history()[:8] if bus else (),
            busy=bus.running if bus else None,
            busy_seconds=bus.running_for_seconds if bus else 0.0,
        )

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
            "available": [item.action for item in descriptors()],
            "history": [item.to_dict() for item in bus.history()],
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
) -> ThreadingHTTPServer:
    """Build the dashboard server.

    Binds to 0.0.0.0 by default so the page is reachable from outside the
    container it runs in. Pass ``allow_commands=False`` for a strictly
    read-only viewer.
    """
    bus = (
        CommandBus.with_defaults(str(database_path), str(storage_root)) if allow_commands else None
    )
    handler = type(
        "BoundDashboardHandler",
        (DashboardHandler,),
        {
            "database_path": str(database_path),
            "storage_root": str(storage_root),
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
) -> None:
    """Run the dashboard until interrupted."""
    server = create_server(database_path, host, port, allow_commands, storage_root)
    shown = "localhost" if host in ("0.0.0.0", "") else host

    print("=== ShadBotTrader dashboard ===")
    print(f"  database : {database_path}")
    print(f"  url      : http://{shown}:{port}")
    print(f"  api      : http://{shown}:{port}/api/state")
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
