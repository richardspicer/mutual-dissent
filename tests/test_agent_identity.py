"""Tests for single-model multi-agent support (agent identity).

Covers: assign_agent_ids(), duplicate panel debates, mixed panels,
reflection filtering with duplicate aliases, per-agent stats,
transcript round-trip with agent IDs, and display label rendering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mutual_dissent.config import Config
from mutual_dissent.display import _base_alias, _get_color, format_markdown
from mutual_dissent.models import DebateRound, DebateTranscript, ModelResponse
from mutual_dissent.orchestrator import assign_agent_ids, run_debate
from mutual_dissent.transcript import _parse_transcript_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_router() -> MagicMock:
    """Create a mock ProviderRouter that preserves agent_id on responses.

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
                content=f"response from {req.get('agent_id', req['model_alias'])}",
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
        agent_id: str = "",
    ) -> ModelResponse:
        return ModelResponse(
            model_id=f"vendor/{model_alias or alias_or_id}-model",
            model_alias=model_alias or alias_or_id,
            round_number=round_number,
            content=f"synthesis by {model_alias or alias_or_id}",
            token_count=75,
            agent_id=agent_id,
        )

    router.complete_parallel = _complete_parallel
    router.complete = _complete

    return router


def _test_config() -> Config:
    """Build a minimal Config for tests.

    Returns:
        Config with test key set.
    """
    return Config(
        api_key="test-key",
        providers={"openrouter": "test-key"},
    )


# ---------------------------------------------------------------------------
# assign_agent_ids()
# ---------------------------------------------------------------------------


class TestAssignAgentIds:
    """assign_agent_ids() produces unique identities for panel aliases."""

    def test_unique_aliases_unchanged(self) -> None:
        """Unique aliases get no suffix."""
        result = assign_agent_ids(["claude", "gpt", "gemini"])
        assert result == ["claude", "gpt", "gemini"]

    def test_all_duplicates_get_suffix(self) -> None:
        """All instances of a duplicate alias get numbered suffixes."""
        result = assign_agent_ids(["claude", "claude", "claude"])
        assert result == ["claude-1", "claude-2", "claude-3"]

    def test_mixed_panel(self) -> None:
        """Only duplicate aliases get suffixes; unique ones stay as-is."""
        result = assign_agent_ids(["claude", "claude", "gpt"])
        assert result == ["claude-1", "claude-2", "gpt"]

    def test_multiple_duplicate_groups(self) -> None:
        """Multiple groups of duplicates each get independent numbering."""
        result = assign_agent_ids(["claude", "gpt", "claude", "gpt"])
        assert result == ["claude-1", "gpt-1", "claude-2", "gpt-2"]

    def test_single_alias(self) -> None:
        """Single-element panel stays unchanged."""
        result = assign_agent_ids(["claude"])
        assert result == ["claude"]

    def test_empty_panel(self) -> None:
        """Empty panel returns empty list."""
        result = assign_agent_ids([])
        assert result == []

    def test_four_duplicates(self) -> None:
        """Four identical aliases get suffixes 1-4."""
        result = assign_agent_ids(["claude", "claude", "claude", "claude"])
        assert result == ["claude-1", "claude-2", "claude-3", "claude-4"]


# ---------------------------------------------------------------------------
# Duplicate panel debate via run_debate
# ---------------------------------------------------------------------------


class TestDuplicatePanelDebate:
    """run_debate() with duplicate aliases produces distinct agent responses."""

    @pytest.mark.asyncio
    async def test_three_claude_agents(self) -> None:
        """Panel of 3 claudes produces 3 distinct responses per round."""
        mock_router = _make_mock_router()

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            transcript = await run_debate(
                "test query",
                _test_config(),
                panel=["claude", "claude", "claude"],
                rounds=1,
            )

        # Initial round should have 3 responses.
        initial = transcript.rounds[0]
        assert len(initial.responses) == 3

        # Each response should have a unique agent_id.
        agent_ids = [r.agent_id for r in initial.responses]
        assert agent_ids == ["claude-1", "claude-2", "claude-3"]

        # All should share the same model_alias.
        aliases = [r.model_alias for r in initial.responses]
        assert aliases == ["claude", "claude", "claude"]

    @pytest.mark.asyncio
    async def test_reflection_sees_others(self) -> None:
        """Each agent sees the other agents' responses during reflection."""
        captured_requests: list[list[dict[str, object]]] = []
        mock_router = _make_mock_router()

        original_cp = mock_router.complete_parallel

        async def _capture_cp(
            requests: list[dict[str, object]],
        ) -> list[ModelResponse]:
            captured_requests.append(requests)
            return await original_cp(requests)

        mock_router.complete_parallel = _capture_cp

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            await run_debate(
                "test query",
                _test_config(),
                panel=["claude", "claude", "claude"],
                rounds=1,
            )

        # Second call to complete_parallel is the reflection round.
        assert len(captured_requests) >= 2
        reflection_requests = captured_requests[1]

        # Each reflection prompt should contain the other 2 agents' labels.
        for req in reflection_requests:
            prompt = str(req["prompt"])
            agent = str(req["agent_id"])
            # The prompt should mention the other agents' display labels.
            other_agents = [aid for aid in ["claude-1", "claude-2", "claude-3"] if aid != agent]
            for other in other_agents:
                assert other in prompt, f"Agent {agent}'s reflection prompt should mention {other}"

    @pytest.mark.asyncio
    async def test_mixed_panel_identities(self) -> None:
        """Mixed panel: duplicates get suffixed, unique stays as-is."""
        mock_router = _make_mock_router()

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            transcript = await run_debate(
                "test query",
                _test_config(),
                panel=["claude", "claude", "gpt"],
                rounds=1,
            )

        initial = transcript.rounds[0]
        agent_ids = [r.agent_id for r in initial.responses]
        assert agent_ids == ["claude-1", "claude-2", "gpt"]

    @pytest.mark.asyncio
    async def test_unique_panel_no_suffix(self) -> None:
        """Unique aliases produce no suffix (backward compat)."""
        mock_router = _make_mock_router()

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            transcript = await run_debate(
                "test query",
                _test_config(),
                panel=["claude", "gpt"],
                rounds=1,
            )

        initial = transcript.rounds[0]
        agent_ids = [r.agent_id for r in initial.responses]
        assert agent_ids == ["claude", "gpt"]


# ---------------------------------------------------------------------------
# Stats aggregation
# ---------------------------------------------------------------------------


class TestStatsWithDuplicates:
    """_compute_stats with duplicate aliases produces per-agent and per-model data."""

    @pytest.mark.asyncio
    async def test_per_agent_and_per_model_stats(self) -> None:
        """Stats contain both per_agent detail and per_model rollup."""
        mock_router = _make_mock_router()

        with patch("mutual_dissent.orchestrator.ProviderRouter", return_value=mock_router):
            transcript = await run_debate(
                "test query",
                _test_config(),
                panel=["claude", "claude"],
                rounds=1,
            )

        stats = transcript.metadata["stats"]

        # per_model: both agents roll up under "claude".
        assert "claude" in stats["per_model"]
        claude_model = stats["per_model"]["claude"]
        # 2 agents * 2 rounds (initial + reflection) = 4 calls, plus synthesis = 5
        assert claude_model["calls"] >= 4

        # per_agent: each agent tracked separately.
        assert "claude-1" in stats["per_agent"]
        assert "claude-2" in stats["per_agent"]
        assert stats["per_agent"]["claude-1"]["model_alias"] == "claude"
        assert stats["per_agent"]["claude-2"]["model_alias"] == "claude"


# ---------------------------------------------------------------------------
# Transcript round-trip
# ---------------------------------------------------------------------------


class TestAgentIdTranscriptRoundTrip:
    """Agent IDs survive JSON serialization round-trip."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Serialize a transcript with agent_ids, parse back, verify preserved."""
        original = DebateTranscript(
            transcript_id="agentid1-5678-9abc-def0-123456789abc",
            query="Agent identity test",
            panel=["claude", "claude", "gpt"],
            synthesizer_id="gpt",
            max_rounds=1,
            metadata={"version": "test"},
        )
        original.rounds.append(
            DebateRound(
                round_number=0,
                round_type="initial",
                responses=[
                    ModelResponse(
                        model_id="anthropic/claude-sonnet-4-6",
                        model_alias="claude",
                        round_number=0,
                        content="Response 1",
                        agent_id="claude-1",
                        role="initial",
                    ),
                    ModelResponse(
                        model_id="anthropic/claude-sonnet-4-6",
                        model_alias="claude",
                        round_number=0,
                        content="Response 2",
                        agent_id="claude-2",
                        role="initial",
                    ),
                    ModelResponse(
                        model_id="openai/gpt-4o",
                        model_alias="gpt",
                        round_number=0,
                        content="Response 3",
                        agent_id="gpt",
                        role="initial",
                    ),
                ],
            )
        )
        original.synthesis = ModelResponse(
            model_id="openai/gpt-4o",
            model_alias="gpt",
            round_number=-1,
            content="Synthesized",
            agent_id="gpt",
            role="synthesis",
        )

        # Serialize
        filepath = tmp_path / "2026-04-06_agentid1.json"
        filepath.write_text(json.dumps(original.to_dict(), indent=2), encoding="utf-8")

        # Parse back
        restored = _parse_transcript_file(filepath)

        assert restored.rounds[0].responses[0].agent_id == "claude-1"
        assert restored.rounds[0].responses[1].agent_id == "claude-2"
        assert restored.rounds[0].responses[2].agent_id == "gpt"
        assert restored.synthesis is not None
        assert restored.synthesis.agent_id == "gpt"

    def test_old_transcript_without_agent_id(self, tmp_path: Path) -> None:
        """Old transcripts without agent_id field parse with empty default."""
        data: dict[str, Any] = {
            "transcript_id": "old00001-5678-9abc-def0-123456789abc",
            "query": "Old transcript test",
            "panel": ["claude", "gpt"],
            "synthesizer_id": "claude",
            "max_rounds": 1,
            "rounds": [
                {
                    "round_number": 0,
                    "round_type": "initial",
                    "responses": [
                        {
                            "model_id": "anthropic/claude-sonnet-4-6",
                            "model_alias": "claude",
                            "round_number": 0,
                            "content": "Old response",
                            "timestamp": "2026-01-01T00:00:00+00:00",
                            "token_count": 100,
                            "latency_ms": 500,
                            "error": None,
                            # No agent_id, role, routing, analysis fields.
                        },
                    ],
                }
            ],
            "synthesis": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {},
        }
        filepath = tmp_path / "2026-01-01_old00001.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")

        restored = _parse_transcript_file(filepath)
        resp = restored.rounds[0].responses[0]
        assert resp.agent_id == ""
        assert resp.display_label == "claude"


# ---------------------------------------------------------------------------
# Display: _base_alias and color mapping
# ---------------------------------------------------------------------------


class TestBaseAlias:
    """_base_alias() extracts the base model alias from agent identity."""

    def test_plain_alias(self) -> None:
        assert _base_alias("claude") == "claude"

    def test_numbered_suffix(self) -> None:
        assert _base_alias("claude-1") == "claude"

    def test_multi_digit_suffix(self) -> None:
        assert _base_alias("claude-12") == "claude"

    def test_non_numeric_suffix_unchanged(self) -> None:
        """Aliases with non-numeric hyphen parts stay unchanged."""
        assert _base_alias("claude-opus") == "claude-opus"

    def test_color_for_agent_id(self) -> None:
        """Agent identity like 'claude-2' gets the 'claude' color."""
        assert _get_color("claude-2") == _get_color("claude")

    def test_color_for_unknown_agent(self) -> None:
        """Unknown base alias gets DEFAULT_COLOR."""
        from mutual_dissent.display import DEFAULT_COLOR

        assert _get_color("unknown-3") == DEFAULT_COLOR


# ---------------------------------------------------------------------------
# Display: markdown with agent identities
# ---------------------------------------------------------------------------


class TestMarkdownWithAgentIds:
    """format_markdown() uses agent_id for labels when set."""

    def test_verbose_shows_agent_ids(self) -> None:
        """Verbose markdown headings use agent_id when set."""
        transcript = DebateTranscript(
            transcript_id="mdagent1-5678-9abc-def0-123456789abc",
            query="Agent markdown test",
            panel=["claude", "claude"],
            synthesizer_id="claude",
            max_rounds=1,
            rounds=[
                DebateRound(
                    round_number=0,
                    round_type="initial",
                    responses=[
                        ModelResponse(
                            model_id="vendor/claude-model",
                            model_alias="claude",
                            round_number=0,
                            content="Response 1",
                            agent_id="claude-1",
                            role="initial",
                        ),
                        ModelResponse(
                            model_id="vendor/claude-model",
                            model_alias="claude",
                            round_number=0,
                            content="Response 2",
                            agent_id="claude-2",
                            role="initial",
                        ),
                    ],
                ),
            ],
            synthesis=ModelResponse(
                model_id="vendor/claude-model",
                model_alias="claude",
                round_number=-1,
                content="Synthesized",
                agent_id="claude-1",
                role="synthesis",
            ),
        )

        result = format_markdown(transcript, verbose=True)
        assert "### claude-1" in result
        assert "### claude-2" in result

    def test_metadata_panel_shows_agent_ids(self) -> None:
        """Metadata footer uses agent_id for panel listing."""
        transcript = DebateTranscript(
            transcript_id="mdpanel1-5678-9abc-def0-123456789abc",
            query="Panel metadata test",
            panel=["claude", "claude"],
            synthesizer_id="claude",
            max_rounds=1,
            rounds=[
                DebateRound(
                    round_number=0,
                    round_type="initial",
                    responses=[
                        ModelResponse(
                            model_id="vendor/claude-model",
                            model_alias="claude",
                            round_number=0,
                            content="R1",
                            agent_id="claude-1",
                            role="initial",
                        ),
                        ModelResponse(
                            model_id="vendor/claude-model",
                            model_alias="claude",
                            round_number=0,
                            content="R2",
                            agent_id="claude-2",
                            role="initial",
                        ),
                    ],
                ),
            ],
            synthesis=ModelResponse(
                model_id="vendor/claude-model",
                model_alias="claude",
                round_number=-1,
                content="Synth",
                agent_id="claude-1",
                role="synthesis",
            ),
        )

        result = format_markdown(transcript)
        assert "**Panel:** claude-1, claude-2" in result
