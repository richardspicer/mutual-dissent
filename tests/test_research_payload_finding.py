"""Tests for Payload Source Protocol and Finding Output Adapter.

Covers: PayloadSource ABC, DefaultPayloadSource, orchestrator payload_source
integration, ResearchFinding dataclass, FindingSeverity enum, and
CounterAgent-compatible JSON export.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mutual_dissent.models import ModelResponse
from mutual_dissent.orchestrator import _merge_payload_context, run_debate
from mutual_dissent.research import (
    DefaultPayloadSource,
    FindingSeverity,
    PayloadSource,
    ResearchFinding,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_TIME = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)


class CustomPayloadSource(PayloadSource):
    """Test implementation that provides query and per-model context."""

    def __init__(self, query: str, contexts: dict[str, str]) -> None:
        self._query = query
        self._contexts = contexts

    def get_query(self) -> str:
        """Return the stored query string.

        Returns:
            The test query.
        """
        return self._query

    def get_context(self, model_alias: str) -> str | None:
        """Return per-model context from the stored mapping.

        Args:
            model_alias: The model alias to look up.

        Returns:
            Context string or None.
        """
        return self._contexts.get(model_alias)


def _make_mock_router() -> MagicMock:
    """Create a mock ProviderRouter for orchestrator tests.

    Returns:
        MagicMock configured as an async context manager.
    """
    router = MagicMock()

    async def _enter(*_args: object) -> MagicMock:
        return router

    async def _exit(*_args: object) -> None:
        pass

    router.__aenter__ = _enter
    router.__aexit__ = _exit

    async def _complete_parallel(
        requests: list[dict[str, object]],
    ) -> list[ModelResponse]:
        return [
            ModelResponse(
                model_id=f"vendor/{req['model_alias']}-model",
                model_alias=str(req["model_alias"]),
                round_number=int(req.get("round_number", 0)),
                content=str(req.get("prompt", "")),
                token_count=50,
                agent_id=str(req.get("agent_id", "")),
            )
            for req in requests
        ]

    async def _complete(
        alias_or_id: str,
        *,
        messages: list[dict[str, object]] | None = None,
        prompt: str | None = None,
        model_alias: str = "",
        round_number: int = 0,
    ) -> ModelResponse:
        return ModelResponse(
            model_id=f"vendor/{model_alias or alias_or_id}-model",
            model_alias=model_alias or alias_or_id,
            round_number=round_number,
            content=f"synthesis by {model_alias or alias_or_id}",
            token_count=75,
        )

    router.complete_parallel = _complete_parallel
    router.complete = _complete

    return router


def _test_config() -> Any:
    """Build a minimal Config for tests.

    Returns:
        Config with test key set.
    """
    from mutual_dissent.config import Config

    return Config(
        api_key="test-key",
        providers={"openrouter": "test-key"},
    )


# ---------------------------------------------------------------------------
# DefaultPayloadSource
# ---------------------------------------------------------------------------


class TestDefaultPayloadSource:
    """DefaultPayloadSource returns query and None context."""

    def test_get_query(self) -> None:
        """get_query() returns the provided query string."""
        source = DefaultPayloadSource("What is MCP?")
        assert source.get_query() == "What is MCP?"

    def test_get_context_returns_none(self) -> None:
        """get_context() always returns None."""
        source = DefaultPayloadSource("query")
        assert source.get_context("claude") is None
        assert source.get_context("gpt") is None
        assert source.get_context("nonexistent") is None

    def test_empty_query(self) -> None:
        """Empty string is a valid query."""
        source = DefaultPayloadSource("")
        assert source.get_query() == ""


# ---------------------------------------------------------------------------
# Custom PayloadSource
# ---------------------------------------------------------------------------


class TestCustomPayloadSource:
    """Custom PayloadSource implementation returns per-model context."""

    def test_get_query(self) -> None:
        """Custom source returns its query."""
        source = CustomPayloadSource("injected query", {"claude": "ctx"})
        assert source.get_query() == "injected query"

    def test_get_context_for_known_alias(self) -> None:
        """Returns context for aliases in the mapping."""
        source = CustomPayloadSource("q", {"claude": "Claude context", "gpt": "GPT context"})
        assert source.get_context("claude") == "Claude context"
        assert source.get_context("gpt") == "GPT context"

    def test_get_context_for_unknown_alias(self) -> None:
        """Returns None for aliases not in the mapping."""
        source = CustomPayloadSource("q", {"claude": "ctx"})
        assert source.get_context("gpt") is None


# ---------------------------------------------------------------------------
# _merge_payload_context
# ---------------------------------------------------------------------------


class TestMergePayloadContext:
    """_merge_payload_context merges PayloadSource and explicit context."""

    def test_payload_only(self) -> None:
        """Payload context is used when no explicit context exists."""
        source = CustomPayloadSource("q", {"claude": "payload ctx"})
        result = _merge_payload_context(source, ["claude", "gpt"], None)
        assert result == {"claude": "payload ctx"}

    def test_explicit_only(self) -> None:
        """Explicit context passes through when payload has no context."""
        source = DefaultPayloadSource("q")
        result = _merge_payload_context(source, ["claude"], {"claude": "explicit ctx"})
        assert result == {"claude": "explicit ctx"}

    def test_merge_both(self) -> None:
        """Both contexts are concatenated for same alias."""
        source = CustomPayloadSource("q", {"claude": "payload ctx"})
        result = _merge_payload_context(source, ["claude"], {"claude": "explicit ctx"})
        assert result is not None
        assert result["claude"] == "payload ctx\n\nexplicit ctx"

    def test_no_context_returns_none(self) -> None:
        """Returns None when neither source provides context."""
        source = DefaultPayloadSource("q")
        result = _merge_payload_context(source, ["claude"], None)
        assert result is None

    def test_preserves_non_panel_explicit_context(self) -> None:
        """Explicit context for aliases not in panel is preserved."""
        source = DefaultPayloadSource("q")
        result = _merge_payload_context(source, ["claude"], {"gpt": "extra ctx"})
        assert result == {"gpt": "extra ctx"}


# ---------------------------------------------------------------------------
# Orchestrator integration — payload_source
# ---------------------------------------------------------------------------


class TestOrchestratorPayloadSource:
    """run_debate() uses payload_source for query and context."""

    @pytest.mark.asyncio
    async def test_payload_source_overrides_query(self) -> None:
        """payload_source.get_query() replaces the query parameter."""
        mock_router = _make_mock_router()
        source = CustomPayloadSource("injected query", {})

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            transcript = await run_debate(
                "original query",
                _test_config(),
                panel=["claude"],
                rounds=1,
                payload_source=source,
            )

        assert transcript.query == "injected query"

    @pytest.mark.asyncio
    async def test_payload_source_context_in_prompt(self) -> None:
        """payload_source.get_context() appears in panelist prompts."""
        captured_requests: list[list[dict[str, object]]] = []
        mock_router = _make_mock_router()

        original_cp = mock_router.complete_parallel

        async def _capture_cp(
            requests: list[dict[str, object]],
        ) -> list[ModelResponse]:
            captured_requests.append(requests)
            return await original_cp(requests)

        mock_router.complete_parallel = _capture_cp

        source = CustomPayloadSource(
            "test query",
            {"claude": "Injected context for Claude"},
        )

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            await run_debate(
                "ignored",
                _test_config(),
                panel=["claude", "gpt"],
                rounds=1,
                payload_source=source,
            )

        # Initial round: claude should have context, gpt should not.
        initial_requests = captured_requests[0]
        claude_prompt = str(
            next(r["prompt"] for r in initial_requests if r["model_alias"] == "claude")
        )
        gpt_prompt = str(next(r["prompt"] for r in initial_requests if r["model_alias"] == "gpt"))
        assert "Injected context for Claude" in claude_prompt
        assert "Injected context for Claude" not in gpt_prompt

    @pytest.mark.asyncio
    async def test_payload_source_merges_with_panelist_context(self) -> None:
        """payload_source context merges with explicit panelist_context."""
        captured_requests: list[list[dict[str, object]]] = []
        mock_router = _make_mock_router()

        original_cp = mock_router.complete_parallel

        async def _capture_cp(
            requests: list[dict[str, object]],
        ) -> list[ModelResponse]:
            captured_requests.append(requests)
            return await original_cp(requests)

        mock_router.complete_parallel = _capture_cp

        source = CustomPayloadSource("q", {"claude": "payload ctx"})

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            await run_debate(
                "ignored",
                _test_config(),
                panel=["claude"],
                rounds=1,
                payload_source=source,
                panelist_context={"claude": "explicit ctx"},
            )

        # Both contexts should appear in the prompt.
        initial_requests = captured_requests[0]
        claude_prompt = str(
            next(r["prompt"] for r in initial_requests if r["model_alias"] == "claude")
        )
        assert "payload ctx" in claude_prompt
        assert "explicit ctx" in claude_prompt

    @pytest.mark.asyncio
    async def test_none_payload_source_unchanged_behavior(self) -> None:
        """When payload_source is None, existing behavior is unchanged."""
        mock_router = _make_mock_router()

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            transcript = await run_debate(
                "original query",
                _test_config(),
                panel=["claude"],
                rounds=1,
            )

        assert transcript.query == "original query"
        assert transcript.synthesis is not None


# ---------------------------------------------------------------------------
# ResearchFinding
# ---------------------------------------------------------------------------


class TestResearchFinding:
    """ResearchFinding dataclass construction and serialization."""

    def test_construction(self) -> None:
        """All fields can be set explicitly."""
        finding = ResearchFinding(
            finding_id="MD-001",
            title="Consensus manipulation",
            description="Model shifted consensus via injection",
            severity=FindingSeverity.HIGH,
            evidence="Transcript excerpt...",
            category="ATLAS-T0001",
            experiment_id="exp-042",
            source_tool="mutual-dissent",
            metadata={"rounds": 3, "panel_size": 4},
            timestamp=FIXED_TIME,
        )
        assert finding.finding_id == "MD-001"
        assert finding.severity == FindingSeverity.HIGH
        assert finding.experiment_id == "exp-042"

    def test_defaults(self) -> None:
        """Optional fields have correct defaults."""
        finding = ResearchFinding(
            finding_id="MD-002",
            title="Test",
            description="Test finding",
            severity=FindingSeverity.INFO,
        )
        assert finding.evidence == ""
        assert finding.category == ""
        assert finding.experiment_id is None
        assert finding.source_tool == "mutual-dissent"
        assert finding.metadata == {}

    def test_to_dict_keys(self) -> None:
        """to_dict() produces CounterAgent-compatible keys."""
        finding = ResearchFinding(
            finding_id="MD-001",
            title="Test finding",
            description="Description here",
            severity=FindingSeverity.MEDIUM,
            evidence="evidence text",
            category="OWASP-A01",
            experiment_id="exp-001",
            timestamp=FIXED_TIME,
        )
        d = finding.to_dict()

        # CounterAgent key mappings.
        assert d["rule_id"] == "MD-001"
        assert d["owasp_id"] == "OWASP-A01"
        assert d["title"] == "Test finding"
        assert d["description"] == "Description here"
        assert d["severity"] == "medium"
        assert d["evidence"] == "evidence text"
        assert d["remediation"] == ""
        assert d["tool_name"] is None
        assert d["metadata"]["source_tool"] == "mutual-dissent"
        assert d["metadata"]["experiment_id"] == "exp-001"
        assert d["timestamp"] == FIXED_TIME.isoformat()

    def test_to_dict_json_serializable(self) -> None:
        """to_dict() output is fully JSON-serializable."""
        finding = ResearchFinding(
            finding_id="MD-001",
            title="Test",
            description="Desc",
            severity=FindingSeverity.LOW,
            metadata={"nested": {"key": "value"}},
            timestamp=FIXED_TIME,
        )
        result = json.dumps(finding.to_dict())
        parsed = json.loads(result)
        assert parsed["rule_id"] == "MD-001"
        assert parsed["severity"] == "low"

    def test_to_dict_roundtrip_json(self) -> None:
        """Round-trip JSON serialization preserves all fields."""
        finding = ResearchFinding(
            finding_id="MD-003",
            title="Reflection manipulation",
            description="Detailed description of finding",
            severity=FindingSeverity.CRITICAL,
            evidence="Round 2 transcript shows...",
            category="ATLAS-T0042",
            experiment_id="exp-099",
            metadata={"models": ["claude", "gpt"], "rounds": 2},
            timestamp=FIXED_TIME,
        )
        serialized = json.dumps(finding.to_dict())
        restored = json.loads(serialized)

        assert restored["rule_id"] == "MD-003"
        assert restored["owasp_id"] == "ATLAS-T0042"
        assert restored["severity"] == "critical"
        assert restored["metadata"]["source_tool"] == "mutual-dissent"
        assert restored["metadata"]["experiment_id"] == "exp-099"
        assert restored["metadata"]["models"] == ["claude", "gpt"]
        assert restored["timestamp"] == FIXED_TIME.isoformat()

    def test_metadata_merge_in_to_dict(self) -> None:
        """to_dict() merges instance metadata with source_tool and experiment_id."""
        finding = ResearchFinding(
            finding_id="MD-004",
            title="T",
            description="D",
            severity=FindingSeverity.INFO,
            metadata={"custom_key": "custom_value"},
            experiment_id="exp-005",
        )
        d = finding.to_dict()
        assert d["metadata"]["custom_key"] == "custom_value"
        assert d["metadata"]["source_tool"] == "mutual-dissent"
        assert d["metadata"]["experiment_id"] == "exp-005"


# ---------------------------------------------------------------------------
# FindingSeverity
# ---------------------------------------------------------------------------


class TestFindingSeverity:
    """FindingSeverity enum values match CounterAgent conventions."""

    def test_all_values(self) -> None:
        """All five severity levels exist with correct string values."""
        assert FindingSeverity.CRITICAL == "critical"
        assert FindingSeverity.HIGH == "high"
        assert FindingSeverity.MEDIUM == "medium"
        assert FindingSeverity.LOW == "low"
        assert FindingSeverity.INFO == "info"

    def test_is_str_enum(self) -> None:
        """FindingSeverity values are strings (StrEnum)."""
        assert isinstance(FindingSeverity.HIGH, str)
        assert FindingSeverity.HIGH.value == "high"
