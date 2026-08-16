"""Presentation layer — Phase 19.

    View  ->  ViewModel  ->  Gateway  ->  Application / Infrastructure

The GUI holds no trading, AI, risk, portfolio or database logic. It
displays state and nothing else; the gateway it depends on exposes only
read operations, so the boundary is structural rather than a convention.
"""

from ShadBotTrader.presentation.gateway.dashboard_gateway import DashboardGateway
from ShadBotTrader.presentation.viewmodels.models import DashboardView
from ShadBotTrader.presentation.web.renderer import render_dashboard
from ShadBotTrader.presentation.web.server import create_server, serve

__all__ = [
    "DashboardGateway",
    "DashboardView",
    "create_server",
    "render_dashboard",
    "serve",
]
