"""Tests for the WebSocket connection manager and status text.

Covers: ConnectionManager lifecycle, _status_text formatting.
"""

from __future__ import annotations

from mutual_dissent.web.websocket import ConnectionManager, _status_text


class TestConnectionManager:
    """ConnectionManager tracks connections correctly."""

    def test_initial_count_is_zero(self) -> None:
        """New manager has zero active connections."""
        mgr = ConnectionManager()
        assert mgr.active_connections == 0


class TestStatusText:
    """_status_text returns correct text for each debate phase."""

    def test_initial_round(self) -> None:
        """Shows initial round message."""
        result = _status_text("initial", 0, 2)
        assert result == "Running initial round..."

    def test_reflection_round(self) -> None:
        """Shows reflection N of M."""
        result = _status_text("reflection", 1, 2)
        assert result == "Reflection 1 of 2..."

    def test_synthesis_round(self) -> None:
        """Shows synthesizing message."""
        result = _status_text("synthesis", -1, 2)
        assert result == "Synthesizing..."

    def test_unknown_type(self) -> None:
        """Unknown round types show generic text."""
        result = _status_text("unknown", 5, 2)
        assert "Round 5" in result
