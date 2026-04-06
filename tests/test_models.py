"""Tests for data models.

Covers: ModelResponse new fields (role, routing, analysis), defaults,
and to_dict() serialization of all fields.
"""

from __future__ import annotations

from mutual_dissent.models import ModelResponse


class TestModelResponseDefaults:
    """New fields have correct default values."""

    def test_role_defaults_to_empty_string(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
        )
        assert r.role == ""

    def test_routing_defaults_to_none(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
        )
        assert r.routing is None

    def test_analysis_defaults_to_empty_dict(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
        )
        assert r.analysis == {}

    def test_analysis_default_is_independent(self) -> None:
        """Each instance gets its own dict (not shared mutable default)."""
        r1 = ModelResponse(model_id="test/model", model_alias="test", round_number=0, content="a")
        r2 = ModelResponse(model_id="test/model", model_alias="test", round_number=0, content="b")
        r1.analysis["score"] = 0.9
        assert "score" not in r2.analysis

    def test_agent_id_defaults_to_empty_string(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
        )
        assert r.agent_id == ""

    def test_display_label_returns_agent_id_when_set(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="claude",
            round_number=0,
            content="hello",
            agent_id="claude-2",
        )
        assert r.display_label == "claude-2"

    def test_display_label_falls_back_to_model_alias(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="claude",
            round_number=0,
            content="hello",
        )
        assert r.display_label == "claude"


class TestModelResponseToDict:
    """to_dict() includes all fields including new ones."""

    def test_to_dict_includes_role(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
            role="initial",
        )
        d = r.to_dict()
        assert d["role"] == "initial"

    def test_to_dict_includes_routing(self) -> None:
        routing = {"vendor": "anthropic", "mode": "auto", "via_openrouter": True}
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
            routing=routing,
        )
        d = r.to_dict()
        assert d["routing"] == routing

    def test_to_dict_includes_analysis(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
            analysis={"score": 0.5},
        )
        d = r.to_dict()
        assert d["analysis"] == {"score": 0.5}

    def test_to_dict_includes_agent_id(self) -> None:
        r = ModelResponse(
            model_id="test/model",
            model_alias="claude",
            round_number=0,
            content="hello",
            agent_id="claude-1",
        )
        d = r.to_dict()
        assert d["agent_id"] == "claude-1"

    def test_to_dict_defaults(self) -> None:
        """Default values appear correctly in to_dict() output."""
        r = ModelResponse(
            model_id="test/model",
            model_alias="test",
            round_number=0,
            content="hello",
        )
        d = r.to_dict()
        assert d["role"] == ""
        assert d["routing"] is None
        assert d["analysis"] == {}
        assert d["agent_id"] == ""
