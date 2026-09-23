"""
NEXUS Realtime Session Manager — Connects WebSocket clients to Orchestrator and EventBus.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect

from backend.agent.orchestrator import Orchestrator
from backend.memory.session_memory import session_memory
from backend.realtime.events import EventBus, NexusEvent


class RealtimeSessionManager:
    """
    Manages active WebSocket connections per session and forwards EventBus events.
    """

    def __init__(self) -> None:
        # Maps session_id -> set of active WebSocket instances
        self._connections: dict[str, set[WebSocket]] = {}
        # Tracks which session has an active event bus listener registered
        self._listener_registered: set[str] = set()
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> tuple[Orchestrator, EventBus]:
        """Accept WebSocket connection and register forwarder to EventBus."""
        await websocket.accept()
        orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()
            self._connections[session_id].add(websocket)

            # Register event bus forwarder once per session
            if session_id not in self._listener_registered:
                self._register_event_forwarder(session_id, event_bus)
                self._listener_registered.add(session_id)

        # Send initial full state snapshot to the client
        snapshot = orchestrator.get_snapshot()
        await websocket.send_json({
            "type": "initial_state",
            "payload": snapshot,
            "session_id": session_id,
        })

        return orchestrator, event_bus

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Unregister a client connection."""
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(websocket)
                if not self._connections[session_id]:
                    del self._connections[session_id]

    def _register_event_forwarder(self, session_id: str, event_bus: EventBus) -> None:
        """Forward all events emitted by this session's EventBus to connected WebSockets."""
        async def _forward(event: NexusEvent) -> None:
            message = {
                "type": event.type.value.lower(),
                "event_type": event.type.value,
                "data": event.data,
                "timestamp": event.timestamp,
                "session_id": session_id,
            }
            sockets = list(self._connections.get(session_id, []))
            for ws in sockets:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

        event_bus.subscribe_all(_forward)

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        """Broadcast arbitrary JSON payload to all clients of a session."""
        sockets = list(self._connections.get(session_id, []))
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                pass


# Global singleton realtime manager
realtime_manager = RealtimeSessionManager()
