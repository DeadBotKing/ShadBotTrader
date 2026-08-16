"""Read-only dashboard HTTP server (Phase 19).

Built on the standard library so the GUI adds no dependency. The server
only ever answers GET; there is no endpoint that can trade, train or
mutate anything, which is how Phase 19 §4 is enforced rather than merely
documented.

Routes
    /            the dashboard page
    /api/state   the same data as JSON
    /health      a liveness probe
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from ShadBotTrader.presentation.gateway.dashboard_gateway import DashboardGateway
from ShadBotTrader.presentation.web.renderer import render_dashboard


class DashboardHandler(BaseHTTPRequestHandler):
    """Serves the dashboard. GET only, by design."""

    database_path: str = "shadbot.db"
    server_version = "ShadBotTrader/1.0"

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
            elif route.path == "/health":
                self._send_json({"status": "ok", "database": self.database_path})
            elif route.path == "/favicon.ico":
                self._send(204, "text/plain", b"")
            else:
                self._send_json({"error": "not found", "path": route.path}, status=404)
        except Exception as error:  # pragma: no cover - defensive
            self._send_json({"error": str(error)}, status=500)

    def do_POST(self) -> None:  # noqa: N802
        """Refused on purpose: the GUI is a viewer, not a controller."""
        self._send_json(
            {
                "error": "This dashboard is read-only.",
                "detail": (
                    "Phase 19 forbids the GUI from executing orders, training "
                    "models or modifying state. Use the CLIs for actions."
                ),
            },
            status=405,
        )

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST

    # -- content --------------------------------------------------------
    def _page(self, session: Optional[str]) -> str:
        gateway = DashboardGateway.open(self.database_path)
        view = gateway.dashboard(session)
        points = (
            gateway.equity_points(view.portfolio.session_id) if view.portfolio is not None else []
        )
        gateway.database.close()
        return render_dashboard(view, points)

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
        return payload

    # -- responses ------------------------------------------------------
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # No caching: the dashboard reflects live stored state.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_html(self, markup: str) -> None:
        self._send(200, "text/html; charset=utf-8", markup.encode("utf-8"))

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def log_message(self, format: str, *args: Any) -> None:
        """Concise access log."""
        print(f"  {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


def create_server(
    database_path: str | Path = "shadbot.db",
    host: str = "0.0.0.0",
    port: int = 8080,
) -> ThreadingHTTPServer:
    """Build the dashboard server.

    Binds to 0.0.0.0 by default so the page is reachable from outside the
    container it runs in.
    """
    handler = type(
        "BoundDashboardHandler",
        (DashboardHandler,),
        {"database_path": str(database_path)},
    )
    return ThreadingHTTPServer((host, port), handler)


def serve(
    database_path: str | Path = "shadbot.db",
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    """Run the dashboard until interrupted."""
    server = create_server(database_path, host, port)
    shown = "localhost" if host in ("0.0.0.0", "") else host

    print("=== ShadBotTrader dashboard ===")
    print(f"  database : {database_path}")
    print(f"  url      : http://{shown}:{port}")
    print(f"  api      : http://{shown}:{port}/api/state")
    print("  read-only: no endpoint can trade, train or modify state")
    print("\n  Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopping ...")
    finally:
        server.shutdown()
        server.server_close()
