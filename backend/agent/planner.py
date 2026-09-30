"""
NEXUS Planner — Generates execution plans (task graphs) from goals.
"""

from __future__ import annotations

from typing import Any

from backend.execution.task_graph import Task, TaskGraph
from backend.providers.base import LLMProvider, PlanSpec
from backend.realtime.events import EventBus, EventType


class Planner:
    """
    Generates a TaskGraph from a user goal and constraints.

    Uses the LLM provider to create a structured plan, then
    converts it into Task objects in the graph.
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
        self.last_plan_spec: PlanSpec | None = None

    async def create_plan(
        self,
        goal: str,
        constraints: dict[str, Any],
        task_graph: TaskGraph,
        context: str = "",
    ) -> list[Task]:
        """
        Create a new execution plan and populate the task graph.

        Returns the list of created tasks.
        """
        # Generate plan via LLM
        plan_spec = await self.llm.create_plan(goal, constraints, context)
        self.last_plan_spec = plan_spec

        # Clear existing graph
        task_graph.clear()

        # Convert plan spec to Task objects
        tasks: list[Task] = []
        for task_spec in plan_spec.tasks:
            task = Task(
                id=task_spec.get("id", ""),
                name=task_spec.get("name", ""),
                description=task_spec.get("description", ""),
                tool=task_spec.get("tool", ""),
                input=task_spec.get("input", {}),
                dependencies=task_spec.get("dependencies", []),
                priority=task_spec.get("priority", 0),
            )
            tasks.append(task)

        # Add tasks to graph (order matters for dependency resolution)
        task_graph.add_tasks(tasks)

        await self.event_bus.emit(
            EventType.PLAN_CREATED,
            session_id=self.session_id,
            goal=goal,
            task_count=len(tasks),
            tasks=[{"id": t.id, "name": t.name, "tool": t.tool, "dependencies": t.dependencies} for t in tasks],
        )

        return tasks
