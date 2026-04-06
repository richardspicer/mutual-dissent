"""Tests for the web API endpoints.

Covers: transcript list, transcript detail, transcript export,
settings save.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from starlette.testclient import TestClient

from mutual_dissent.web.app import create_app


class TestTranscriptAPI:
    """API endpoints for transcript access."""

    def test_get_transcripts_returns_json(self) -> None:
        """GET /api/transcripts returns JSON array."""
        app = create_app()
        client = TestClient(app)
        with patch("mutual_dissent.web.routes.list_transcripts", return_value=[]):
            resp = client.get("/api/transcripts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_transcripts_with_limit(self) -> None:
        """GET /api/transcripts?limit=5 passes limit to list_transcripts."""
        app = create_app()
        client = TestClient(app)
        with patch("mutual_dissent.web.routes.list_transcripts", return_value=[]) as mock_list:
            client.get("/api/transcripts?limit=5")
        mock_list.assert_called_once_with(limit=5)

    def test_get_transcript_detail_not_found(self) -> None:
        """GET /api/transcripts/{id} returns 404 when not found."""
        app = create_app()
        client = TestClient(app)
        with patch("mutual_dissent.web.routes.load_transcript", return_value=None):
            resp = client.get("/api/transcripts/nonexistent")
        assert resp.status_code == 404

    def test_transcript_export_not_found(self) -> None:
        """GET /api/transcripts/{id}/export returns 404 when not found."""
        app = create_app()
        client = TestClient(app)
        with patch("mutual_dissent.web.routes.load_transcript", return_value=None):
            resp = client.get("/api/transcripts/nonexistent/export")
        assert resp.status_code == 404


class TestSettingsAPI:
    """POST /settings saves configuration."""

    def test_save_defaults(self) -> None:
        """POST /settings with defaults updates config."""
        app = create_app()
        client = TestClient(app)
        with (
            patch("mutual_dissent.web.routes.load_config") as mock_load,
            patch("mutual_dissent.web.routes.write_config") as mock_write,
        ):
            from mutual_dissent.config import Config

            mock_load.return_value = Config()
            resp = client.post(
                "/settings",
                content=json.dumps({"defaults": {"rounds": 2}}),
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_write.assert_called_once()

    def test_save_providers(self) -> None:
        """POST /settings with providers updates provider keys."""
        app = create_app()
        client = TestClient(app)
        with (
            patch("mutual_dissent.web.routes.load_config") as mock_load,
            patch("mutual_dissent.web.routes.write_config"),
        ):
            from mutual_dissent.config import Config

            mock_load.return_value = Config()
            resp = client.post(
                "/settings",
                content=json.dumps({"providers": {"openrouter": "sk-test"}}),
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
