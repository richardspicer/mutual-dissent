"""Tests for CLI version check utilities."""

from __future__ import annotations

from mutual_dissent.cli import _parse_version


class TestParseVersion:
    """Tests for _parse_version."""

    def test_three_segment(self) -> None:
        assert _parse_version("0.1.1") == (0, 1, 1)

    def test_two_segment(self) -> None:
        assert _parse_version("1.0") == (1, 0)

    def test_single_segment(self) -> None:
        assert _parse_version("3") == (3,)

    def test_comparison_newer(self) -> None:
        assert _parse_version("0.2.0") > _parse_version("0.1.1")

    def test_comparison_equal(self) -> None:
        assert _parse_version("1.0.0") == _parse_version("1.0.0")

    def test_comparison_older(self) -> None:
        assert _parse_version("0.1.0") < _parse_version("0.1.1")

    def test_invalid_returns_zero(self) -> None:
        assert _parse_version("not.a.version") == (0,)

    def test_empty_returns_zero(self) -> None:
        assert _parse_version("") == (0,)
