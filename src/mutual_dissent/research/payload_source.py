"""Payload Source Protocol — abstracts where debate inputs come from.

Default implementation returns user-provided query with no per-model context.
External tools (CounterSignal, CounterAgent) implement this to feed payloads
programmatically into debates.

Typical usage::

    from mutual_dissent.research import DefaultPayloadSource

    source = DefaultPayloadSource("What is MCP?")
    query = source.get_query()
    context = source.get_context("claude")  # Returns None
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PayloadSource(ABC):
    """Abstracts where debate inputs come from.

    Default implementation returns user-provided query with no per-model context.
    External tools (CounterSignal, CounterAgent) implement this to feed payloads
    programmatically into debates.
    """

    @abstractmethod
    def get_query(self) -> str:
        """Return the debate query string.

        Returns:
            The query to use for the debate.
        """

    @abstractmethod
    def get_context(self, model_alias: str) -> str | None:
        """Return per-model context for a specific panelist, or None.

        Args:
            model_alias: The model alias from the panel config.

        Returns:
            Context string to prepend to this model's prompt, or None.
        """


class DefaultPayloadSource(PayloadSource):
    """User-provided query with no per-model context.

    Args:
        query: The debate query string.
    """

    def __init__(self, query: str) -> None:
        self._query = query

    def get_query(self) -> str:
        """Return the stored query string.

        Returns:
            The query provided at construction time.
        """
        return self._query

    def get_context(self, model_alias: str) -> str | None:
        """Return None — default source has no per-model context.

        Args:
            model_alias: The model alias (unused).

        Returns:
            Always None.
        """
        return None
