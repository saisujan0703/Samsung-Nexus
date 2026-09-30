"""
NEXUS Response Manager — Generates streaming natural language responses.

Formats task execution outputs, replan summaries, and agent status
into clear, concise text suitable for both UI display and TTS voice synthesis.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from backend.providers.base import LLMProvider, Message
from backend.realtime.events import EventBus, EventType


class ResponseManager:
    """
    Manages response generation, streaming, and formatting for voice and text.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        event_bus: EventBus,
        session_id: str = "",
    ) -> None:
        self.llm = llm_provider
        self.event_bus = event_bus
        self.session_id = session_id
        self._current_generation: asyncio.Task | None = None
        self._cancelled = asyncio.Event()

    async def acknowledge_interruption(self, interruption_type: str, details: dict[str, Any], text: str) -> str:
        """
        Generate an instant, snappy spoken acknowledgment of an interruption.
        
        Designed to respond within <50ms so user knows they were heard immediately.
        """
        if interruption_type == "BACKCHANNEL":
            return ""  # Do not speak on backchannel
        elif interruption_type == "CONSTRAINT_CHANGE":
            if "reason" in details and "parents" in details.get("reason", ""):
                return "Got it! Your parents are coming. Adjusting the group size and accommodations now."
            if "max_walking" in details:
                return "Understood, filtering for low-walking spots and accessible transport."
            if "budget" in details:
                b_val = details["budget"]
                try:
                    b_int = int(str(b_val).replace(",", "").replace("₹", "").strip())
                    return f"Understood, adjusting your budget limit to ₹{b_int:,}."
                except (ValueError, TypeError):
                    return f"Understood, adjusting your budget limit to ₹{b_val}."
            return "Got it, updating the plan with those new details."
        elif interruption_type == "CORRECTION":
            return "Got it, correcting that now."
        elif interruption_type == "QUESTION":
            return "Let me check that for you."
        elif interruption_type == "TASK_CANCELLATION":
            return "Stopping that task right away."
        elif interruption_type == "NEW_GOAL":
            return "Understood. Shelving the current plan and starting fresh with your new goal."
        elif interruption_type == "GOAL_CHANGE":
            return "Got it, shifting the goal and updating our itinerary."
        return "I'm on it."

    async def generate_task_response(
        self,
        task_results: list[dict[str, Any]],
        goal: str,
        context: str = "",
    ) -> str:
        """
        Generate full response for completed tasks.
        """
        self._cancelled.clear()
        await self.event_bus.emit(
            EventType.RESPONSE_STARTED,
            session_id=self.session_id,
            goal=goal,
        )

        full_text = await self.llm.generate_response(task_results, goal, context)

        await self.event_bus.emit(
            EventType.RESPONSE_COMPLETED,
            session_id=self.session_id,
            text=full_text,
        )
        return full_text

    async def stream_task_response(
        self,
        task_results: list[dict[str, Any]],
        goal: str,
        context: str = "",
    ) -> AsyncIterator[str]:
        """
        Stream response tokens or words, emitting WebSocket events per chunk.
        """
        self._cancelled.clear()
        await self.event_bus.emit(
            EventType.RESPONSE_STARTED,
            session_id=self.session_id,
            goal=goal,
        )

        full_text = await self.llm.generate_response(task_results, goal, context)
        words = full_text.split()
        accumulated = ""

        for word in words:
            if self._cancelled.is_set():
                break
            chunk = word + " "
            accumulated += chunk
            await self.event_bus.emit(
                EventType.RESPONSE_CHUNK,
                session_id=self.session_id,
                chunk=chunk,
                text=accumulated,
            )
            yield chunk
            await asyncio.sleep(0.03)  # natural speech cadence pacing

        if not self._cancelled.is_set():
            await self.event_bus.emit(
                EventType.RESPONSE_COMPLETED,
                session_id=self.session_id,
                text=accumulated.strip(),
            )

    def cancel_response(self) -> None:
        """Cancel current streaming generation (e.g. if user interrupts while speaking)."""
        self._cancelled.set()
        if self._current_generation and not self._current_generation.done():
            self._current_generation.cancel()
