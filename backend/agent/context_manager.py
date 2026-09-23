"""
NEXUS Context Manager — Session context preservation across replans.

Maintains structured context so the agent doesn't lose important information
when the user interrupts and changes the plan.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.realtime.events import EventBus, EventType


class Finding(BaseModel):
    """A piece of information discovered during task execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_task_id: str = ""
    category: str = ""  # hotel, destination, activity, transport, cost
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    still_valid: bool = True


class SessionContext(BaseModel):
    """Complete structured context for a session."""
    session_id: str = ""
    current_goal_summary: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    completed_findings: list[Finding] = Field(default_factory=list)
    active_task_ids: list[str] = Field(default_factory=list)
    pending_task_ids: list[str] = Field(default_factory=list)
    cancelled_task_ids: list[str] = Field(default_factory=list)
    conversation_turns: list[dict[str, str]] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    interruption_count: int = 0


class ContextManager:
    """
    Manages structured session context.

    Key responsibilities:
    - Preserve completed findings across replans
    - Track conversation (summarized, not full history)
    - Maintain preferences and constraints
    - Invalidate findings when constraints change
    """

    def __init__(self, event_bus: EventBus, session_id: str = "") -> None:
        self.event_bus = event_bus
        self.session_id = session_id
        self.context = SessionContext(session_id=session_id)

    async def update_goal(self, summary: str, constraints: dict[str, Any]) -> None:
        self.context.current_goal_summary = summary
        self.context.constraints = constraints
        await self._emit_update("goal_updated")

    async def add_finding(self, task_id: str, category: str, data: dict[str, Any]) -> Finding:
        """Add a finding from a completed task."""
        finding = Finding(source_task_id=task_id, category=category, data=data)
        self.context.completed_findings.append(finding)
        return finding

    async def invalidate_findings(self, categories: list[str] | None = None, task_ids: list[str] | None = None) -> int:
        """Mark findings as invalid based on category or source task."""
        count = 0
        for finding in self.context.completed_findings:
            if categories and finding.category in categories:
                finding.still_valid = False
                count += 1
            if task_ids and finding.source_task_id in task_ids:
                finding.still_valid = False
                count += 1
        return count

    def get_valid_findings(self) -> list[Finding]:
        return [f for f in self.context.completed_findings if f.still_valid]

    async def add_conversation_turn(self, role: str, content: str) -> None:
        """Add a conversation turn, keeping only recent history."""
        self.context.conversation_turns.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only last 20 turns
        if len(self.context.conversation_turns) > 20:
            self.context.conversation_turns = self.context.conversation_turns[-20:]

    async def add_preference(self, key: str, value: Any) -> None:
        self.context.preferences[key] = value

    async def add_decision(self, decision: str) -> None:
        self.context.important_decisions.append(decision)

    async def update_task_lists(
        self,
        active: list[str] | None = None,
        pending: list[str] | None = None,
        cancelled: list[str] | None = None,
    ) -> None:
        if active is not None:
            self.context.active_task_ids = active
        if pending is not None:
            self.context.pending_task_ids = pending
        if cancelled is not None:
            self.context.cancelled_task_ids = cancelled

    async def record_interruption(self) -> None:
        self.context.interruption_count += 1

    async def preserve_context(self, changes_description: str = "") -> dict[str, Any]:
        """
        Preserve context across a replan. Called before modifying the task graph.
        Returns a summary of what was preserved.
        """
        valid_findings = self.get_valid_findings()
        preserved = {
            "findings_preserved": len(valid_findings),
            "constraints": dict(self.context.constraints),
            "preferences": dict(self.context.preferences),
            "decisions": list(self.context.important_decisions),
            "description": changes_description,
        }

        await self.event_bus.emit(
            EventType.CONTEXT_PRESERVED,
            session_id=self.session_id,
            preserved_findings=len(valid_findings),
            constraints=self.context.constraints,
        )

        return preserved

    def get_context_summary(self) -> str:
        """Generate a compressed context summary for LLM prompts."""
        parts = [f"Goal: {self.context.current_goal_summary}"]
        if self.context.constraints:
            parts.append(f"Constraints: {self.context.constraints}")
        if self.context.preferences:
            parts.append(f"Preferences: {self.context.preferences}")
        valid = self.get_valid_findings()
        if valid:
            parts.append(f"Findings: {len(valid)} valid results available")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return self.context.model_dump()

    async def _emit_update(self, reason: str = "") -> None:
        await self.event_bus.emit(
            EventType.CONTEXT_UPDATED,
            session_id=self.session_id,
            goal=self.context.current_goal_summary,
            constraints=self.context.constraints,
            preferences=self.context.preferences,
            findings_count=len(self.get_valid_findings()),
            interruption_count=self.context.interruption_count,
            reason=reason,
        )
