"""Anthropic provider implementation.

Async HTTP provider that sends Messages API requests directly to the
Anthropic API endpoint.  Uses ``httpx`` for consistency with
``OpenRouterProvider`` — no SDK dependency required.

Key differences from OpenRouter:

- Auth via ``x-api-key`` header (not ``Authorization: Bearer``).
- ``max_tokens`` is required in every request payload.
- System messages must be hoisted to a top-level ``system`` field.
- Response content is an array of typed blocks, not a plain string.

Typical usage::

    import asyncio
    from mutual_dissent.providers.anthropic import AnthropicProvider

    async def main():
        async with AnthropicProvider(api_key="sk-ant-...") as provider:
            response = await provider.complete(
                "claude-sonnet-4-6", prompt="Hello",
            )

    asyncio.run(main())
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from mutual_dissent.models import ModelResponse
from mutual_dissent.providers.base import Provider

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 120.0  # seconds — generous for slow responses


class AnthropicProvider(Provider):
    """Async provider for the Anthropic Messages API.

    Uses ``httpx.AsyncClient`` for connection pooling and async I/O.
    Designed to be used as an async context manager.

    Args:
        api_key: Anthropic API key.
        max_tokens: Maximum tokens per response.  Defaults to 4096.
        timeout: Request timeout in seconds.  Defaults to 120s.

    Example::

        async with AnthropicProvider(api_key="sk-ant-...") as provider:
            resp = await provider.complete(
                "claude-sonnet-4-6", prompt="What is 2+2?",
            )
            print(resp.content)
    """

    def __init__(
        self,
        api_key: str,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY env var.")
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> AnthropicProvider:
        """Open the underlying HTTP connection pool."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """Close the underlying HTTP connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def complete(
        self,
        model_id: str,
        *,
        messages: list[dict[str, Any]] | None = None,
        prompt: str | None = None,
        model_alias: str = "",
        round_number: int = 0,
    ) -> ModelResponse:
        """Send a Messages API request to a single model.

        Accepts either ``messages`` (list of chat messages) or ``prompt``
        (single user message string).  Exactly one must be provided.

        System-role messages in the ``messages`` list are automatically
        extracted and hoisted to the top-level ``system`` field, as
        required by the Anthropic API.

        Args:
            model_id: Anthropic model identifier (e.g. "claude-sonnet-4-6").
            messages: Chat messages in OpenAI-compatible format.
            prompt: Single user message string (convenience shorthand).
            model_alias: Human-readable name for logging.  Defaults to
                the model_id if not provided.
            round_number: Which debate round this belongs to.

        Returns:
            ModelResponse with the model's reply, timing, and token stats.

        Raises:
            ValueError: If both or neither of ``messages``/``prompt`` are given.
            RuntimeError: If the client is used outside a context manager.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        resolved = self._resolve_messages(messages, prompt)
        alias = model_alias or model_id
        start = time.monotonic()

        system_text, chat_messages = _extract_system(resolved)

        payload: dict[str, Any] = {
            "model": model_id,
            "max_tokens": self._max_tokens,
            "messages": chat_messages,
        }
        if system_text is not None:
            payload["system"] = system_text

        try:
            resp = await self._client.post(ANTHROPIC_API_URL, json=payload)
        except httpx.TimeoutException:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ModelResponse(
                model_id=model_id,
                model_alias=alias,
                round_number=round_number,
                content="",
                latency_ms=elapsed_ms,
                error=f"Request timed out after {self._timeout}s",
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code != 200:
            error_detail = _extract_error(resp)
            return ModelResponse(
                model_id=model_id,
                model_alias=alias,
                round_number=round_number,
                content="",
                latency_ms=elapsed_ms,
                error=f"HTTP {resp.status_code}: {error_detail}",
            )

        data = resp.json()
        content = _extract_content(data)
        token_count = _extract_token_count(data)
        input_tokens, output_tokens = _extract_token_split(data)

        return ModelResponse(
            model_id=model_id,
            model_alias=alias,
            round_number=round_number,
            content=content,
            latency_ms=elapsed_ms,
            token_count=token_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def _extract_system(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Separate system messages from chat messages.

    The Anthropic Messages API requires system prompts in a top-level
    ``system`` field rather than inline ``{"role": "system"}`` messages.

    Args:
        messages: Mixed list of chat messages, possibly including system messages.

    Returns:
        Tuple of (system_text, remaining_messages).  System messages are
        concatenated with double newlines if multiple exist.  Returns
        ``None`` for system_text if no system messages are present.
    """
    system_parts: list[str] = []
    chat_messages: list[dict[str, Any]] = []

    for msg in messages:
        if msg.get("role") == "system":
            system_parts.append(msg["content"])
        else:
            chat_messages.append(msg)

    system_text = "\n\n".join(system_parts) if system_parts else None
    return system_text, chat_messages


def _extract_content(data: dict[str, Any]) -> str:
    """Extract text from Anthropic's content block array.

    Concatenates all text-type blocks, ignoring non-text blocks
    (``tool_use``, ``thinking``, etc.).

    Args:
        data: Parsed JSON response body.

    Returns:
        The joined text content, or a descriptive fallback if no text
        blocks are found.
    """
    try:
        content_blocks: list[dict[str, Any]] = data["content"]
        texts = [block["text"] for block in content_blocks if block.get("type") == "text"]
        if texts:
            return "".join(texts)
        return "[No text content in response]"
    except (KeyError, TypeError):
        return f"[Failed to parse response: {data}]"


def _extract_token_count(data: dict[str, Any]) -> int | None:
    """Sum input_tokens + output_tokens from usage.

    Args:
        data: Parsed JSON response body.

    Returns:
        Total token count if both fields are present, None otherwise.
    """
    usage = data.get("usage")
    if usage and "input_tokens" in usage and "output_tokens" in usage:
        return int(usage["input_tokens"]) + int(usage["output_tokens"])
    return None


def _extract_token_split(data: dict[str, Any]) -> tuple[int | None, int | None]:
    """Extract input/output token split from an API response.

    Args:
        data: Parsed JSON response body.

    Returns:
        Tuple of (input_tokens, output_tokens). Either or both may be
        None if the API did not report them.
    """
    usage = data.get("usage")
    if not usage:
        return None, None
    inp = int(usage["input_tokens"]) if "input_tokens" in usage else None
    out = int(usage["output_tokens"]) if "output_tokens" in usage else None
    return inp, out


def _extract_error(resp: httpx.Response) -> str:
    """Extract error message from an Anthropic error response.

    Handles the Anthropic format::

        {"type": "error", "error": {"type": "...", "message": "..."}}

    Args:
        resp: The httpx response object.

    Returns:
        Human-readable error description.
    """
    try:
        body = resp.json()
        error = body.get("error", {})
        if isinstance(error, dict):
            return str(error.get("message", str(body)))
        return str(error)
    except Exception:
        return str(resp.text[:500])
