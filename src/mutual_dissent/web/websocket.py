"""WebSocket connection manager and debate streaming handler.

Manages real-time WebSocket connections for the debate interface.
The debate handler listens for ``debate_start`` messages and streams
round-by-round progress events back to the client.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from mutual_dissent.config import load_config
from mutual_dissent.models import DebateRound
from mutual_dissent.orchestrator import run_debate
from mutual_dissent.transcript import save_transcript

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track active WebSocket connections for event broadcasting.

    Attributes:
        _connections: Set of active WebSocket instances.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection.

        Args:
            websocket: The incoming WebSocket to accept.
        """
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active set.

        Args:
            websocket: The WebSocket to remove.
        """
        self._connections.discard(websocket)

    async def send_to(self, websocket: WebSocket, event: dict[str, Any]) -> None:
        """Send a JSON event to a specific WebSocket.

        Args:
            websocket: Target WebSocket connection.
            event: Dictionary to serialize as JSON.
        """
        try:
            await websocket.send_json(event)
        except Exception:
            logger.debug("Failed to send to websocket", exc_info=True)
            self._connections.discard(websocket)

    @property
    def active_connections(self) -> int:
        """Number of currently tracked connections."""
        return len(self._connections)


async def debate_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint for running debates with streaming events.

    Accepts a WebSocket, then listens for ``debate_start`` messages.
    On receipt, runs the debate via the orchestrator and pushes
    status/response/synthesis/done events back to the client.

    Args:
        websocket: The incoming WebSocket connection.
    """
    manager: ConnectionManager = websocket.app.state.ws_manager
    await manager.connect(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_to(
                    websocket, {"type": "debate_error", "message": "Invalid JSON"}
                )
                continue

            msg_type = data.get("type", "")
            if msg_type == "debate_start":
                await _handle_debate(websocket, manager, data)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


async def _handle_debate(
    websocket: WebSocket,
    manager: ConnectionManager,
    data: dict[str, Any],
) -> None:
    """Run a debate and stream events to the WebSocket.

    Args:
        websocket: Client WebSocket to send events to.
        manager: Connection manager for sending events.
        data: Parsed ``debate_start`` message with query, panel, etc.
    """
    query = data.get("query", "").strip()
    if not query:
        await manager.send_to(websocket, {"type": "debate_error", "message": "Query is required"})
        return

    panel = data.get("panel")
    synthesizer = data.get("synthesizer")
    rounds = data.get("rounds")

    config = load_config()

    if panel is None:
        panel = config.default_panel
    if synthesizer is None:
        synthesizer = config.default_synthesizer
    if rounds is None:
        rounds = config.default_rounds

    round_count = 0
    total_rounds = int(rounds)

    async def on_round_complete(debate_round: DebateRound) -> None:
        nonlocal round_count

        if debate_round.round_type == "synthesis":
            resp = debate_round.responses[0]
            await manager.send_to(
                websocket,
                {
                    "type": "debate_synthesis",
                    "content": resp.content,
                    "synthesizer": resp.display_label,
                    "error": resp.error,
                },
            )
        else:
            await manager.send_to(
                websocket,
                {
                    "type": "debate_status",
                    "message": _status_text(debate_round.round_type, round_count, total_rounds),
                    "round": debate_round.round_number,
                    "round_type": debate_round.round_type,
                },
            )
            for resp in debate_round.responses:
                await manager.send_to(
                    websocket,
                    {
                        "type": "debate_response",
                        "agent": resp.display_label,
                        "model_alias": resp.model_alias,
                        "content": resp.content,
                        "round": debate_round.round_number,
                        "round_type": debate_round.round_type,
                        "error": resp.error,
                    },
                )
            round_count += 1

    await manager.send_to(
        websocket,
        {
            "type": "debate_status",
            "message": "Starting debate...",
            "round": 0,
            "round_type": "initial",
        },
    )

    try:
        transcript = await run_debate(
            query,
            config,
            panel=panel,
            synthesizer=synthesizer,
            rounds=rounds,
            ground_truth=None,
            panelist_context=None,
            on_round_complete=on_round_complete,
        )

        saved_path = await asyncio.to_thread(save_transcript, transcript)
        logger.info("Transcript saved: %s", saved_path)

        await manager.send_to(
            websocket,
            {
                "type": "debate_done",
                "transcript_id": transcript.short_id,
            },
        )
    except Exception:
        logger.exception("Debate failed")
        await manager.send_to(
            websocket,
            {
                "type": "debate_error",
                "message": "Debate failed. Check server logs for details.",
            },
        )


def _status_text(round_type: str, round_number: int, total_rounds: int) -> str:
    """Format a human-readable status message for a debate phase.

    Args:
        round_type: One of "initial", "reflection", "synthesis".
        round_number: Current round index (0-based).
        total_rounds: Configured number of reflection rounds.

    Returns:
        Status message string.
    """
    if round_type == "initial":
        return "Running initial round..."
    if round_type == "reflection":
        return f"Reflection {round_number} of {total_rounds}..."
    if round_type == "synthesis":
        return "Synthesizing..."
    return f"Round {round_number}..."
