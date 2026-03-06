"""Tests for the ``config test`` CLI command and display rendering.

Covers: Click command registration (config group exists, test subcommand
exists), render_config_test with success results, render_config_test with
error results, and the _run_config_test async helper.
"""

from __future__ import annotations

from click.testing import CliRunner

from mutual_dissent.cli import main
from mutual_dissent.display import render_config_test
from mutual_dissent.models import ModelResponse
from mutual_dissent.types import RoutingDecision, Vendor

# ---------------------------------------------------------------------------
# Click command registration
# ---------------------------------------------------------------------------


class TestCommandRegistration:
    """config group and test subcommand are registered correctly."""

    def test_config_group_exists(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "config" in result.output

    def test_config_shows_test_subcommand(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "test" in result.output

    def test_config_test_shows_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "test", "--help"])
        assert result.exit_code == 0
        assert "Test provider configuration" in result.output


# ---------------------------------------------------------------------------
# render_config_test output
# ---------------------------------------------------------------------------


def _make_result(
    alias: str,
    vendor: Vendor,
    via_openrouter: bool,
    model_id: str,
    *,
    latency_ms: int | None = 1200,
    error: str | None = None,
) -> dict[str, RoutingDecision | ModelResponse | str]:
    """Build a result dict matching _run_config_test output format."""
    decision = RoutingDecision(vendor=vendor, mode="auto", via_openrouter=via_openrouter)
    response = ModelResponse(
        model_id=model_id,
        model_alias=alias,
        round_number=0,
        content="OK" if not error else "",
        latency_ms=latency_ms,
        error=error,
    )
    return {"alias": alias, "decision": decision, "response": response}


class TestRenderConfigTestSuccess:
    """render_config_test renders success results correctly."""

    def test_renders_without_error(self, capsys: object) -> None:
        """Smoke test — render_config_test doesn't raise."""
        results = [
            _make_result("claude", Vendor.ANTHROPIC, False, "claude-sonnet-4-6"),
            _make_result("gpt", Vendor.OPENAI, True, "openai/gpt-5.2"),
        ]
        # Should not raise.
        render_config_test(results)

    def test_success_all_aliases_shown(self) -> None:
        """All tested aliases appear in the output."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result("claude", Vendor.ANTHROPIC, False, "claude-sonnet-4-6"),
            _make_result("gpt", Vendor.OPENAI, True, "openai/gpt-5.2"),
            _make_result("gemini", Vendor.GOOGLE, True, "google/gemini-2.5-pro"),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True)

        # Temporarily replace module console.
        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "claude" in output
        assert "gpt" in output
        assert "gemini" in output

    def test_latency_formatted_as_seconds(self) -> None:
        """Latency renders as seconds (e.g. 1.2s)."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result(
                "claude",
                Vendor.ANTHROPIC,
                False,
                "claude-sonnet-4-6",
                latency_ms=1200,
            ),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True)

        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "1.2s" in output

    def test_direct_route_shown(self) -> None:
        """Direct-routed models show 'direct' in route column."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result("claude", Vendor.ANTHROPIC, False, "claude-sonnet-4-6"),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True)

        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "direct" in output

    def test_openrouter_route_shown(self) -> None:
        """OpenRouter-routed models show 'openrouter' in route column."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result("gpt", Vendor.OPENAI, True, "openai/gpt-5.2"),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True)

        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "openrouter" in output


class TestRenderConfigTestError:
    """render_config_test renders error results correctly."""

    def test_error_shows_message(self) -> None:
        """Error responses show the error message in the status column."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result(
                "grok",
                Vendor.XAI,
                True,
                "x-ai/grok-4",
                latency_ms=None,
                error="401 Unauthorized",
            ),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True)

        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "401 Unauthorized" in output

    def test_error_shows_dash_for_latency(self) -> None:
        """Error responses show a dash instead of latency."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result(
                "grok",
                Vendor.XAI,
                True,
                "x-ai/grok-4",
                latency_ms=None,
                error="timeout",
            ),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True)

        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "\u2014" in output

    def test_mixed_success_and_error(self) -> None:
        """Table renders correctly with both success and error rows."""
        from io import StringIO

        from rich.console import Console

        results = [
            _make_result("claude", Vendor.ANTHROPIC, False, "claude-sonnet-4-6"),
            _make_result(
                "grok",
                Vendor.XAI,
                True,
                "x-ai/grok-4",
                latency_ms=None,
                error="connection error",
            ),
        ]

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True, width=120)

        import mutual_dissent.display as display_mod

        original_console = display_mod.console
        display_mod.console = test_console
        try:
            render_config_test(results)
        finally:
            display_mod.console = original_console

        output = buf.getvalue()
        assert "claude" in output
        assert "grok" in output
        assert "connection error" in output
        assert "1.2s" in output


# ---------------------------------------------------------------------------
# config path subcommand
# ---------------------------------------------------------------------------


class TestConfigPath:
    """config path subcommand."""

    def test_config_path_shows_in_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "path" in result.output

    def test_config_path_prints_path(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "path"])
        assert result.exit_code == 0
        assert ".mutual-dissent" in result.output
        assert "config.toml" in result.output


# ---------------------------------------------------------------------------
# config show subcommand
# ---------------------------------------------------------------------------


class TestConfigShow:
    """config show subcommand."""

    def test_config_show_in_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output

    def test_config_show_runs(self, monkeypatch) -> None:
        """config show runs without error and shows key sections."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "config.toml" in result.output

    def test_config_show_never_exposes_full_key(self, monkeypatch) -> None:
        """Full API key must never appear in config show output."""
        full_key = "sk-or-v1-abcdefghijklmnopqrstuvwxyz1234567890"
        monkeypatch.setenv("OPENROUTER_API_KEY", full_key)
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert full_key not in result.output

    def test_config_show_check_models_flag_exists(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show", "--help"])
        assert result.exit_code == 0
        assert "check-models" in result.output


# ---------------------------------------------------------------------------
# render_config_show output
# ---------------------------------------------------------------------------


class TestRenderConfigShow:
    """render_config_show() display function."""

    def _capture(self, config, context_lengths=None):
        """Helper to capture render_config_show output."""
        from io import StringIO

        from rich.console import Console

        import mutual_dissent.display as display_mod

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=True, width=120)
        original_console = display_mod.console
        display_mod.console = test_console
        try:
            from mutual_dissent.display import render_config_show

            render_config_show(config, context_lengths=context_lengths)
        finally:
            display_mod.console = original_console
        return buf.getvalue()

    def test_shows_config_path(self) -> None:
        from mutual_dissent.config import Config

        config = Config()
        output = self._capture(config)
        assert "config.toml" in output

    def test_shows_panel(self) -> None:
        from mutual_dissent.config import Config

        config = Config()
        output = self._capture(config)
        assert "claude" in output
        assert "gpt" in output

    def test_shows_synthesizer(self) -> None:
        from mutual_dissent.config import Config

        config = Config()
        output = self._capture(config)
        assert "claude" in output

    def test_shows_rounds(self) -> None:
        from mutual_dissent.config import Config

        config = Config()
        output = self._capture(config)
        # Default rounds is 1
        assert "1" in output

    def test_masks_api_key(self) -> None:
        """API keys must be masked -- never shown in full."""
        from mutual_dissent.config import Config

        config = Config()
        full_key = "sk-or-v1-abcdefghijklmnopqrstuvwxyz1234567890"
        config.providers["openrouter"] = full_key
        output = self._capture(config)
        # Full key must NOT appear.
        assert full_key not in output
        # Masked form should appear.
        assert "sk-or-" in output
        assert "7890" in output

    def test_shows_not_configured(self) -> None:
        """Providers without keys show 'not configured'."""
        from mutual_dissent.config import Config

        config = Config()
        config.providers = {}
        output = self._capture(config)
        assert "not configured" in output.lower()

    def test_shows_provider_source_env(self, monkeypatch) -> None:
        """Provider key from env var shows 'env' source."""
        from mutual_dissent.config import load_config

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey12345678")
        config = load_config()
        output = self._capture(config)
        assert "env" in output.lower()

    def test_shows_model_aliases(self) -> None:
        """Model aliases section shows alias to model ID mappings."""
        from mutual_dissent.config import Config

        config = Config()
        output = self._capture(config)
        assert "anthropic/claude-sonnet-4-6" in output

    def test_shows_routing_mode(self) -> None:
        from mutual_dissent.config import Config

        config = Config()
        output = self._capture(config)
        assert "auto" in output

    def test_shows_context_length(self) -> None:
        """Context lengths shown when provided."""
        from mutual_dissent.config import Config

        config = Config()
        context_lengths = {"claude": 200000}
        output = self._capture(config, context_lengths=context_lengths)
        assert "200,000" in output or "200000" in output
