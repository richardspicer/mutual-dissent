"""Starlette web application for Mutual Dissent.

Defines the ASGI app factory with Jinja2 templates, static file
serving, and WebSocket support. Started via ``mutual-dissent serve``.
"""

from __future__ import annotations

from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from mutual_dissent.web.routes import (
    dashboard_page,
    debate_page,
    get_transcript_detail,
    get_transcripts,
    save_settings,
    settings_page,
    transcript_export,
)
from mutual_dissent.web.websocket import ConnectionManager, debate_ws

_WEB_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app() -> Starlette:
    """Build and return the Starlette ASGI application.

    Configures Jinja2 templates, static files, route handlers, and a
    WebSocket connection manager stored on ``app.state``.

    Returns:
        Configured Starlette application instance.
    """
    routes = [
        Route("/", debate_page),
        Route("/dashboard", dashboard_page),
        Route("/settings", settings_page),
        Route("/settings", save_settings, methods=["POST"]),
        Route("/api/transcripts", get_transcripts),
        Route("/api/transcripts/{transcript_id:str}", get_transcript_detail),
        Route("/api/transcripts/{transcript_id:str}/export", transcript_export),
        WebSocketRoute("/ws/debate", debate_ws),
        Mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static"),
    ]

    app = Starlette(routes=routes)

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app.state.templates = templates
    app.state.ws_manager = ConnectionManager()

    return app
