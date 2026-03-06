"""Provider routing layer for multi-vendor model dispatch.

Routes completion requests to the appropriate provider (OpenRouter or a
direct vendor API) based on model alias, routing configuration, and
available API keys.  Manages provider lifecycles as an async context
manager.

The ``ProviderRouter`` is the dispatch layer between the orchestrator and
individual providers.  Given a model alias like ``"claude"``, it
determines the vendor, checks routing config, selects the right provider,
resolves the correct model ID, and dispatches the request.  Returns
standard ``ModelResponse`` objects regardless of which provider handled
the call.

Typical usage::

    from mutual_dissent.config import load_config
    from mutual_dissent.providers.router import ProviderRouter

    config = load_config()
    async with ProviderRouter(config) as router:
        response = await router.complete("claude", prompt="Hello")
        responses = await router.complete_parallel([
            {"alias_or_id": "claude", "prompt": "Hello"},
            {"alias_or_id": "gpt", "prompt": "Hello"},
        ])
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mutual_dissent.config import Config
from mutual_dissent.models import ModelResponse
from mutual_dissent.providers.anthropic import AnthropicProvider
from mutual_dissent.providers.base import Provider
from mutual_dissent.providers.openrouter import OpenRouterProvider
from mutual_dissent.types import RoutingDecision, Vendor

# Registry of vendors with direct provider implementations.
# New vendors get added here as their providers are implemented.
_DIRECT_PROVIDERS: dict[str, type[Provider]] = {
    "anthropic": AnthropicProvider,
}


# OpenRouter model ID prefix → Vendor enum member.
_PREFIX_TO_VENDOR: dict[str, Vendor] = {
    "anthropic": Vendor.ANTHROPIC,
    "openai": Vendor.OPENAI,
    "google": Vendor.GOOGLE,
    "x-ai": Vendor.XAI,
    "groq": Vendor.GROQ,
}


def _resolve_vendor(alias_or_id: str, config: Config) -> Vendor:
    """Determine the vendor for a given alias or model ID.

    Resolution order:

    1. If alias exists in config's v2 aliases, extract vendor from the
       OpenRouter ID prefix.
    2. If ``alias_or_id`` contains ``/``, extract prefix as vendor.
    3. Fall back to ``Vendor.OPENROUTER`` (unknown vendor, route through
       OpenRouter).

    Args:
        alias_or_id: Model alias (e.g. ``"claude"``) or full model ID
            (e.g. ``"anthropic/claude-sonnet-4-6"``).
        config: Application configuration with alias mappings.

    Returns:
        The resolved ``Vendor`` enum member.
    """
    # 1. Check v2 aliases.
    if alias_or_id in config._model_aliases_v2:
        ids = config._model_aliases_v2[alias_or_id]
        openrouter_id = ids.get("openrouter", "")
        if "/" in openrouter_id:
            prefix = openrouter_id.split("/")[0]
            return _PREFIX_TO_VENDOR.get(prefix, Vendor.OPENROUTER)

    # 2. Full model ID with slash.
    if "/" in alias_or_id:
        prefix = alias_or_id.split("/")[0]
        return _PREFIX_TO_VENDOR.get(prefix, Vendor.OPENROUTER)

    # 3. Unknown — fall back to OpenRouter.
    return Vendor.OPENROUTER


class ProviderRouter:
    """Dispatch layer for multi-provider model access.

    Routes requests to the appropriate provider based on model alias,
    routing configuration, and available API keys.  Manages provider
    lifecycles as an async context manager.

    Args:
        config: Application configuration with provider keys and routing.

    Example::

        config = load_config()
        async with ProviderRouter(config) as router:
            response = await router.complete("claude", prompt="Hello")
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._providers: dict[str, Provider] = {}
        self._openrouter: OpenRouterProvider | None = None
        self._logger = logging.getLogger(__name__)

    async def __aenter__(self) -> ProviderRouter:
        """Open provider connections.

        Eagerly opens:

        - ``OpenRouterProvider`` if an OpenRouter key is configured.
        - Direct providers for each vendor that has both an API key
          and a registered provider class in ``_DIRECT_PROVIDERS``.

        Returns:
            This ``ProviderRouter`` instance.
        """
        or_key = self._config.get_provider_key("openrouter")
        if or_key:
            self._openrouter = OpenRouterProvider(api_key=or_key)
            await self._openrouter.__aenter__()

        for vendor, provider_cls in _DIRECT_PROVIDERS.items():
            key = self._config.get_provider_key(vendor)
            if key:
                provider = provider_cls(api_key=key)  # type: ignore[call-arg]
                await provider.__aenter__()
                self._providers[vendor] = provider

        return self

    async def __aexit__(self, *exc: Any) -> None:
        """Close all open provider connections.

        Uses ``asyncio.gather`` with ``return_exceptions=True`` to
        ensure all providers are closed even if one raises.
        """
        coros: list[Any] = []
        if self._openrouter is not None:
            coros.append(self._openrouter.__aexit__(None, None, None))
        for provider in self._providers.values():
            coros.append(provider.__aexit__(None, None, None))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)
        self._openrouter = None
        self._providers.clear()

    def route(self, alias_or_id: str) -> RoutingDecision:
        """Determine how a request should be routed.

        Pure decision function — no I/O.  Examines the routing config,
        available API keys, and registered provider classes to decide
        whether a request should go direct or through OpenRouter.

        Args:
            alias_or_id: Model alias (e.g. ``"claude"``) or full model ID
                (e.g. ``"anthropic/claude-sonnet-4-6"``).

        Returns:
            A ``RoutingDecision`` recording the vendor, mode, and
            whether OpenRouter is used.
        """
        vendor = _resolve_vendor(alias_or_id, self._config)
        mode = self._config.routing.get(
            alias_or_id,
            self._config.routing.get("default_mode", "auto"),
        )

        if mode == "openrouter":
            via_openrouter = True
        elif mode == "direct":
            has_key = self._config.get_provider_key(vendor.value) is not None
            if has_key:
                has_provider = vendor.value in _DIRECT_PROVIDERS
                if has_provider:
                    via_openrouter = False
                else:
                    via_openrouter = True
                    self._logger.warning(
                        "Direct mode requested for '%s' but no provider "
                        "implementation for vendor '%s'; falling back to OpenRouter",
                        alias_or_id,
                        vendor.value,
                    )
            else:
                via_openrouter = True
                self._logger.warning(
                    "Direct mode requested for '%s' but no API key for "
                    "vendor '%s'; falling back to OpenRouter",
                    alias_or_id,
                    vendor.value,
                )
        else:  # "auto"
            has_key = self._config.get_provider_key(vendor.value) is not None
            has_provider = vendor.value in _DIRECT_PROVIDERS
            via_openrouter = not (has_key and has_provider)

        return RoutingDecision(vendor=vendor, mode=mode, via_openrouter=via_openrouter)

    async def complete(
        self,
        alias_or_id: str,
        *,
        messages: list[dict[str, Any]] | None = None,
        prompt: str | None = None,
        model_alias: str = "",
        round_number: int = 0,
    ) -> ModelResponse:
        """Route and execute a single completion request.

        Determines the correct provider and model ID from the alias,
        then dispatches the request.  Returns a ``ModelResponse`` with
        an error field set (rather than raising) if no provider is
        available.

        Args:
            alias_or_id: Model alias (e.g. ``"claude"``) or full model ID.
            messages: Chat messages in OpenAI-compatible format.
            prompt: Single user message string (convenience shorthand).
            model_alias: Human-readable name for logging.  Defaults to
                ``alias_or_id`` if not provided.
            round_number: Debate round (0=initial, 1+=reflection,
                -1=synthesis).

        Returns:
            ``ModelResponse`` with the model's reply, or with ``error``
            set if routing/dispatch failed.
        """
        decision = self.route(alias_or_id)
        alias = model_alias or alias_or_id

        routing_dict = decision.to_dict()

        if decision.via_openrouter:
            if self._openrouter is None:
                response = ModelResponse(
                    model_id=alias_or_id,
                    model_alias=alias,
                    round_number=round_number,
                    content="",
                    error=(
                        f"No provider available for '{alias_or_id}': "
                        "no OpenRouter API key configured and no direct "
                        "provider available"
                    ),
                )
                response.routing = routing_dict
                return response
            model_id = self._config.resolve_model(alias_or_id)
            response = await self._openrouter.complete(
                model_id,
                messages=messages,
                prompt=prompt,
                model_alias=alias,
                round_number=round_number,
            )
            response.routing = routing_dict
            return response

        # Direct provider path.
        vendor_key = decision.vendor.value
        provider = self._providers.get(vendor_key)
        if provider is None:
            response = ModelResponse(
                model_id=alias_or_id,
                model_alias=alias,
                round_number=round_number,
                content="",
                error=f"No direct provider available for vendor '{vendor_key}'",
            )
            response.routing = routing_dict
            return response
        model_id = self._config.resolve_model(alias_or_id, direct=True)
        response = await provider.complete(
            model_id,
            messages=messages,
            prompt=prompt,
            model_alias=alias,
            round_number=round_number,
        )
        response.routing = routing_dict
        return response

    async def complete_parallel(
        self,
        requests: list[dict[str, Any]],
    ) -> list[ModelResponse]:
        """Fan out multiple requests across providers in parallel.

        Each request is independently routed, so different requests in
        the same batch can go to different providers.

        Args:
            requests: List of keyword argument dicts for ``complete()``.
                Each dict should contain at minimum ``alias_or_id`` and
                either ``prompt`` or ``messages``.

        Returns:
            List of ``ModelResponse`` objects in the same order as
            *requests*.
        """
        tasks = [self.complete(**req) for req in requests]
        return list(await asyncio.gather(*tasks))
