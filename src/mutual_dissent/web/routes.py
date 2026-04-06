"""HTTP route handlers for the Mutual Dissent web UI.

Serves HTML pages (debate, dashboard, settings) and JSON API
endpoints for transcript access and configuration management.
"""

from __future__ import annotations

import json
import os
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.templating import Jinja2Templates

from mutual_dissent.config import (
    _ENV_VAR_MAP,
    MAX_ROUNDS,
    Config,
    load_config,
    write_config,
)
from mutual_dissent.transcript import list_transcripts, load_transcript


def _templates(request: Request) -> Jinja2Templates:
    """Retrieve the Jinja2Templates instance from app state.

    Args:
        request: Current HTTP request.

    Returns:
        Jinja2Templates instance.
    """
    templates: Jinja2Templates = request.app.state.templates
    return templates


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------


async def debate_page(request: Request) -> Response:
    """Render the debate chat interface.

    Args:
        request: HTTP request.

    Returns:
        Rendered debate.html template.
    """
    config = load_config()
    available_models = sorted(config.model_aliases.keys())
    return _templates(request).TemplateResponse(
        request,
        "debate.html",
        {
            "available_models": available_models,
            "default_panel": config.default_panel,
            "default_synthesizer": config.default_synthesizer,
            "default_rounds": config.default_rounds,
            "max_rounds": MAX_ROUNDS,
        },
    )


async def dashboard_page(request: Request) -> Response:
    """Render the dashboard with transcript list.

    Args:
        request: HTTP request.

    Returns:
        Rendered dashboard.html template.
    """
    transcripts = list_transcripts(limit=0)
    return _templates(request).TemplateResponse(
        request,
        "dashboard.html",
        {"transcripts": transcripts},
    )


async def settings_page(request: Request) -> Response:
    """Render the settings page with current configuration.

    Args:
        request: HTTP request.

    Returns:
        Rendered settings.html template.
    """
    config = load_config()
    providers_status = _build_providers_status(config)
    return _templates(request).TemplateResponse(
        request,
        "settings.html",
        {
            "config": config,
            "providers_status": providers_status,
            "max_rounds": MAX_ROUNDS,
        },
    )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


async def save_settings(request: Request) -> Response:
    """Save configuration changes from the settings form.

    Reads JSON body with optional keys: providers, routing, defaults,
    model_aliases. Merges into current config and writes to disk.

    Args:
        request: HTTP request with JSON body.

    Returns:
        JSON response with success status.
    """
    body = await request.json()
    config = load_config()

    env_providers = _detect_env_providers()

    if "providers" in body:
        for provider_name, key_value in body["providers"].items():
            if provider_name not in env_providers and key_value:
                config.providers[provider_name] = key_value

    if "routing" in body:
        config.routing.update(body["routing"])

    if "defaults" in body:
        defaults = body["defaults"]
        if "panel" in defaults:
            config.default_panel = defaults["panel"]
        if "synthesizer" in defaults:
            config.default_synthesizer = defaults["synthesizer"]
        if "rounds" in defaults:
            config.default_rounds = min(int(defaults["rounds"]), MAX_ROUNDS)

    if "model_aliases" in body:
        for alias, ids in body["model_aliases"].items():
            if isinstance(ids, dict):
                config._model_aliases_v2[alias] = ids
                config.model_aliases[alias] = ids.get("openrouter", "")
            elif isinstance(ids, str):
                config.model_aliases[alias] = ids
                config._model_aliases_v2[alias] = {"openrouter": ids}

    write_config(config, env_providers=env_providers)

    return JSONResponse({"status": "ok"})


async def get_transcripts(request: Request) -> Response:
    """Return transcript list as JSON.

    Args:
        request: HTTP request. Supports ``?limit=N`` query param.

    Returns:
        JSON array of transcript summaries.
    """
    limit_str = request.query_params.get("limit", "0")
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 0
    transcripts = list_transcripts(limit=limit)
    return JSONResponse(transcripts)


async def get_transcript_detail(request: Request) -> Response:
    """Return a full transcript as JSON.

    Args:
        request: HTTP request with transcript_id path param.

    Returns:
        JSON transcript or 404.
    """
    transcript_id = request.path_params["transcript_id"]
    transcript = load_transcript(transcript_id)
    if transcript is None:
        return JSONResponse({"error": "Transcript not found"}, status_code=404)
    return JSONResponse(transcript.to_dict())


async def transcript_export(request: Request) -> Response:
    """Export a transcript as JSON or markdown.

    Args:
        request: HTTP request with transcript_id path param and
            ``?format=json|markdown`` query param.

    Returns:
        JSON or markdown response with appropriate content type.
    """
    transcript_id = request.path_params["transcript_id"]
    fmt = request.query_params.get("format", "json")
    transcript = load_transcript(transcript_id)

    if transcript is None:
        return JSONResponse({"error": "Transcript not found"}, status_code=404)

    if fmt == "markdown":
        from mutual_dissent.display import format_markdown

        md = format_markdown(transcript, verbose=True)
        return Response(
            content=md,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{transcript.short_id}.md"'},
        )

    content = json.dumps(transcript.to_dict(), indent=2, ensure_ascii=False)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{transcript.short_id}.json"'},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_providers_status(config: Config) -> list[dict[str, Any]]:
    """Build provider status list for the settings page.

    For each known provider, reports the source of its API key
    (env, file, or none) and whether a key is present.

    Args:
        config: Current application config.

    Returns:
        List of dicts with name, label, source, and has_key fields.
    """
    providers = [
        ("openrouter", "OpenRouter"),
        ("anthropic", "Anthropic"),
        ("openai", "OpenAI"),
        ("google", "Google"),
        ("xai", "xAI"),
        ("groq", "Groq"),
    ]
    result: list[dict[str, Any]] = []
    env_provs = _detect_env_providers()

    for name, label in providers:
        has_key = bool(config.get_provider_key(name))
        source = "none"
        if name in env_provs:
            source = "env"
        elif config.providers.get(name, ""):
            source = "file"
        result.append(
            {
                "name": name,
                "label": label,
                "source": source,
                "has_key": has_key,
            }
        )
    return result


def _detect_env_providers() -> set[str]:
    """Detect which providers have keys set via environment variables.

    Returns:
        Set of provider names with env var keys.
    """
    env_provs: set[str] = set()
    for env_var, provider_name in _ENV_VAR_MAP.items():
        if os.environ.get(env_var, ""):
            env_provs.add(provider_name)
    return env_provs
