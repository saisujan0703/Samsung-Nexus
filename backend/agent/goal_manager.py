"""
NEXUS Goal Manager — Tracks current goal, constraints, and goal history.

Detects whether user input represents a constraint change, goal modification,
or completely new goal.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.realtime.events import EventBus, EventType


class Goal(BaseModel):
    """Represents a user's current goal."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    summary: str = ""
    raw_input: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    parent_goal_id: str | None = None


class GoalManager:
    """
    Manages the user's current goal and constraint history.

    Responsibilities:
    - Set and update goals
    - Track constraint changes with versioning
    - Detect what changed between old and new goals
    - Maintain goal history for context preservation
    """

    def __init__(self, event_bus: EventBus, session_id: str = "") -> None:
        self.event_bus = event_bus
        self.session_id = session_id
        self.current_goal: Goal | None = None
        self.goal_history: list[Goal] = []

    async def set_goal(self, summary: str, constraints: dict[str, Any], raw_input: str = "") -> Goal:
        """Set a brand new goal."""
        if self.current_goal:
            self.goal_history.append(self.current_goal)

        goal = Goal(
            summary=summary,
            raw_input=raw_input,
            constraints=constraints,
        )
        self.current_goal = goal

        await self.event_bus.emit(
            EventType.GOAL_SET,
            session_id=self.session_id,
            goal_id=goal.id,
            summary=goal.summary,
            constraints=goal.constraints,
        )

        return goal

    async def update_constraints(self, changes: dict[str, Any], reason: str = "") -> dict[str, Any]:
        """
        Update constraints on the current goal.

        Returns a dict of what actually changed (old_value → new_value).
        """
        if not self.current_goal:
            return {}

        actual_changes: dict[str, Any] = {}
        old_constraints = dict(self.current_goal.constraints)

        for key, new_value in changes.items():
            old_value = self.current_goal.constraints.get(key)

            if key == "num_people_delta":
                # Special handling: delta change
                current_people = self.current_goal.constraints.get("num_people", 1)
                new_people = current_people + new_value
                self.current_goal.constraints["num_people"] = new_people
                actual_changes["num_people"] = {"old": current_people, "new": new_people, "reason": changes.get("reason", reason)}
            elif old_value != new_value:
                self.current_goal.constraints[key] = new_value
                actual_changes[key] = {"old": old_value, "new": new_value}

        if actual_changes:
            self.current_goal.version += 1

            # Update goal summary
            c = self.current_goal.constraints
            city = c.get("city", "").title()
            days = c.get("duration_days", "?")
            people = c.get("num_people", "?")
            budget = c.get("budget", "?")
            walking = c.get("max_walking", None)
            summary_parts = [f"Plan a {days}-day {city} trip for {people} people under ₹{budget:,}" if isinstance(budget, int) else f"Plan a {days}-day {city} trip for {people} people"]
            if walking:
                summary_parts.append(f"(max walking: {walking})")
            self.current_goal.summary = " ".join(summary_parts)

            await self.event_bus.emit(
                EventType.GOAL_CHANGED,
                session_id=self.session_id,
                goal_id=self.current_goal.id,
                changes=actual_changes,
                new_constraints=self.current_goal.constraints,
                new_summary=self.current_goal.summary,
                version=self.current_goal.version,
            )

        return actual_changes

    def get_constraints(self) -> dict[str, Any]:
        return self.current_goal.constraints if self.current_goal else {}

    def get_goal_summary(self) -> str:
        return self.current_goal.summary if self.current_goal else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_goal": self.current_goal.model_dump() if self.current_goal else None,
            "history_count": len(self.goal_history),
        }
