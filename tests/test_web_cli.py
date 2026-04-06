"""Tests for the ``serve`` CLI command registration.

Covers: Click command registration, help text, and option defaults.
Does NOT start the uvicorn server (uvicorn.run is mocked).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from mutual_dissent.cli import main


class TestServeCommandRegistration:
    """serve command is registered and has correct options."""

    def test_serve_appears_in_help(self) -> None:
        """serve command is listed in main --help output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "serve" in result.output

    def test_serve_help_shows_description(self) -> None:
        """serve --help shows the command description."""
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start the web UI server" in result.output

    def test_serve_help_shows_port_option(self) -> None:
        """serve --help lists --port option."""
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_serve_help_shows_host_option(self) -> None:
        """serve --help lists --host option."""
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output

    def test_serve_help_shows_no_open_option(self) -> None:
        """serve --help lists --no-open option."""
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--no-open" in result.output


class TestServeCommandExecution:
    """serve command calls uvicorn.run with correct arguments."""

    def test_serve_default_args(self) -> None:
        """serve with no options starts uvicorn with defaults."""
        runner = CliRunner()
        mock_run = MagicMock()
        with (
            patch("uvicorn.run", mock_run),
            patch("webbrowser.open"),
            patch("threading.Timer", return_value=MagicMock()),
        ):
            result = runner.invoke(main, ["serve"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8080

    def test_serve_no_open(self) -> None:
        """serve --no-open does not open browser."""
        runner = CliRunner()
        mock_run = MagicMock()
        mock_timer_cls = MagicMock()
        with (
            patch("uvicorn.run", mock_run),
            patch("threading.Timer", mock_timer_cls),
        ):
            result = runner.invoke(main, ["serve", "--no-open"])
        assert result.exit_code == 0
        mock_timer_cls.assert_not_called()

    def test_serve_custom_port(self) -> None:
        """serve --port passes custom port."""
        runner = CliRunner()
        mock_run = MagicMock()
        with (
            patch("uvicorn.run", mock_run),
            patch("webbrowser.open"),
            patch("threading.Timer", return_value=MagicMock()),
        ):
            result = runner.invoke(main, ["serve", "--port", "9000"])
        assert result.exit_code == 0
        _, kwargs = mock_run.call_args
        assert kwargs["port"] == 9000
