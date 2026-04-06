"""Tests for the Starlette web application factory and routes.

Covers: app creation, HTML page responses, template rendering.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from mutual_dissent.web.app import create_app


class TestAppCreation:
    """create_app returns a working Starlette application."""

    def test_app_has_state(self) -> None:
        """App state includes templates and ws_manager."""
        app = create_app()
        assert hasattr(app.state, "templates")
        assert hasattr(app.state, "ws_manager")


class TestPageRoutes:
    """HTML page routes return 200 with expected content."""

    def test_debate_page(self) -> None:
        """GET / returns the debate page."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "mutual-dissent" in resp.text
        assert "debate-input" in resp.text

    def test_dashboard_page(self) -> None:
        """GET /dashboard returns the dashboard page."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "Transcript Browser" in resp.text

    def test_settings_page(self) -> None:
        """GET /settings returns the settings page."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert "Provider API Keys" in resp.text

    def test_static_css(self) -> None:
        """Static CSS file is served."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/static/app.css")
        assert resp.status_code == 200
        assert "debate-bubble" in resp.text
