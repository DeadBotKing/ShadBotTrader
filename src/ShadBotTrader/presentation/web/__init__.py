"""Web view and server (Phase 19 §8)."""

from ShadBotTrader.presentation.web.renderer import render_dashboard
from ShadBotTrader.presentation.web.server import create_server, serve

__all__ = ["create_server", "render_dashboard", "serve"]
