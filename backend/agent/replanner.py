"""
NEXUS Replanner / Plan Diff Engine — The core technical innovation.

When a user changes constraints or goals, the replanner:
1. Generates a new plan for the updated goal
2. Compares old tasks vs new tasks
3. Classifies each task as KEEP / CANCEL / MODIFY / ADD
4. Applies the diff to the task graph with minimal disruption
"""

from __future__ import annotations

from typing import Any

from backend.execution.task_graph import Task, TaskGraph, TaskStatus, PlanDiffAction
from backend.providers.base import LLMProvider, PlanSpec
from backend.realtime.events import EventBus, EventType


class PlanDiff:
    """Result of comparing an old plan to a new plan."""

    def __init__(self) -> None:
        self.keep: list[str] = []       # task IDs to keep
        self.cancel: list[str] = []     # task IDs to cancel
        self.modify: list[dict] = []    # {task_id, changes}
        self.add: list[dict] = []       # new task specs to add

    def to_dict(self) -> dict:
        return {
            "keep": self.keep,
            "cancel": self.cancel,
            "modify": self.modify,
            "add": self.add,
            "summary": (
                f"KEEP: {len(self.keep)}, CANCEL: {len(self.cancel)}, "
                f"MODIFY: {len(self.modify)}, ADD: {len(self.add)}"
            ),
        }


class Replanner:
    """
    Computes plan diffs and applies them to the task graph.

    This is the heart of the interruptible agent — it determines
    exactly which tasks to keep, cancel, modify, or add when the
    user changes their mind.
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

    async def compute_diff(
        self,
        task_graph: TaskGraph,
        new_constraints: dict[str, Any],
        changed_fields: dict[str, Any],
    ) -> PlanDiff:
        """
        Compare the current task graph against what a new plan would look like.

        Uses the changed fields to determine which tasks are affected.
        """
        diff = PlanDiff()
        old_tasks = task_graph.get_all_tasks()

        # Generate new plan for comparison
        goal = self._build_goal_string(new_constraints)
        new_plan = await self.llm.create_plan(goal, new_constraints)

        # Build lookup of new task names/tools
        new_task_map = {t["name"].lower(): t for t in new_plan.tasks}
        old_task_map = {t.name.lower(): t for t in old_tasks}

        # Determine which old tasks to keep/cancel/modify
        for old_task in old_tasks:
            name_lower = old_task.name.lower()

            if old_task.status == TaskStatus.COMPLETED:
                # Completed tasks are kept if still relevant
                if self._is_task_affected(old_task, changed_fields):
                    # Results may be partially invalid but we keep the task as completed
                    diff.keep.append(old_task.id)
                    old_task.diff_action = PlanDiffAction.KEEP
                else:
                    diff.keep.append(old_task.id)
                    old_task.diff_action = PlanDiffAction.KEEP

            elif old_task.status == TaskStatus.CANCELLED:
                # Already cancelled, skip
                continue

            elif name_lower in new_task_map:
                new_spec = new_task_map[name_lower]
                if self._is_task_affected(old_task, changed_fields):
                    # Task exists in new plan but parameters changed
                    diff.modify.append({
                        "task_id": old_task.id,
                        "new_input": new_spec.get("input", {}),
                        "reason": f"Parameters updated due to: {list(changed_fields.keys())}",
                    })
                    old_task.diff_action = PlanDiffAction.MODIFY
                else:
                    diff.keep.append(old_task.id)
                    old_task.diff_action = PlanDiffAction.KEEP
            else:
                # Task doesn't exist in new plan — cancel it
                diff.cancel.append(old_task.id)
                old_task.diff_action = PlanDiffAction.CANCEL

        # Determine which new tasks to add
        for new_name, new_spec in new_task_map.items():
            if new_name not in old_task_map:
                diff.add.append(new_spec)

        await self.event_bus.emit(
            EventType.PLAN_DIFF_COMPUTED,
            session_id=self.session_id,
            diff=diff.to_dict(),
        )

        return diff

    async def apply_diff(
        self,
        task_graph: TaskGraph,
        diff: PlanDiff,
        executor_cancel_callback=None,
    ) -> dict[str, Any]:
        """
        Apply a plan diff to the task graph.

        Returns a summary of what changed.
        """
        cancelled_ids: list[str] = []
        modified_ids: list[str] = []
        added_ids: list[str] = []

        # 1. Cancel obsolete tasks
        for task_id in diff.cancel:
            task = task_graph.get_task(task_id)
            if task and task.is_active:
                cancelled = task_graph.cancel_task(task_id, "plan_diff_cancel")
                cancelled_ids.extend([t.id for t in cancelled])
                if executor_cancel_callback:
                    await executor_cancel_callback(task_id, "plan_diff_cancel")

        # 2. Modify tasks (update input parameters)
        for mod in diff.modify:
            task_id = mod["task_id"]
            task = task_graph.get_task(task_id)
            if task:
                if task.status == TaskStatus.RUNNING:
                    # Cancel the running task so it can be restarted with new params
                    cancelled = task_graph.cancel_task(task_id, "modified_by_replan")
                    cancelled_ids.extend([t.id for t in cancelled])
                    if executor_cancel_callback:
                        await executor_cancel_callback(task_id, "modified_by_replan")

                    # Re-add with new parameters
                    new_task = Task(
                        id=task_id + "_v2",
                        name=task.name,
                        description=task.description,
                        tool=task.tool,
                        input=mod.get("new_input", task.input),
                        dependencies=task.dependencies,
                        priority=task.priority,
                        affected_by="replan",
                        diff_action=PlanDiffAction.MODIFY,
                    )
                    # Update dependencies to point to existing completed tasks
                    valid_deps = []
                    for dep in new_task.dependencies:
                        dep_task = task_graph.get_task(dep)
                        if dep_task and dep_task.status == TaskStatus.COMPLETED:
                            valid_deps.append(dep)
                    new_task.dependencies = valid_deps
                    task_graph.add_task(new_task)
                    modified_ids.append(new_task.id)

                elif task.status == TaskStatus.PENDING:
                    # Just update the input
                    task.input = mod.get("new_input", task.input)
                    task.affected_by = "replan"
                    task.diff_action = PlanDiffAction.MODIFY
                    modified_ids.append(task.id)

        # 3. Add new tasks
        for task_spec in diff.add:
            # Resolve dependencies — map to existing completed tasks or other new tasks
            deps = task_spec.get("dependencies", [])
            valid_deps = []
            for dep in deps:
                dep_task = task_graph.get_task(dep)
                if dep_task and dep_task.status == TaskStatus.COMPLETED:
                    valid_deps.append(dep)
                # If dependency doesn't exist or isn't completed, skip it
                # (the task will become ready once the dep completes or if it has no deps)

            new_task = Task(
                id=task_spec.get("id", ""),
                name=task_spec.get("name", ""),
                description=task_spec.get("description", ""),
                tool=task_spec.get("tool", ""),
                input=task_spec.get("input", {}),
                dependencies=valid_deps,
                priority=task_spec.get("priority", 0),
                affected_by="replan",
                diff_action=PlanDiffAction.ADD,
            )
            try:
                task_graph.add_task(new_task)
                added_ids.append(new_task.id)
            except ValueError:
                # Dependency not in graph, add without deps
                new_task.dependencies = []
                task_graph.add_task(new_task)
                added_ids.append(new_task.id)

        result = {
            "cancelled": cancelled_ids,
            "modified": modified_ids,
            "added": added_ids,
            "kept": diff.keep,
        }

        await self.event_bus.emit(
            EventType.PLAN_UPDATED,
            session_id=self.session_id,
            cancelled=cancelled_ids,
            modified=modified_ids,
            added=added_ids,
            kept=diff.keep,
        )

        return result

    def _is_task_affected(self, task: Task, changed_fields: dict[str, Any]) -> bool:
        """Determine if a task is affected by the changed constraints."""
        input_str = str(task.input).lower()
        name_lower = task.name.lower()

        for field, change in changed_fields.items():
            field_lower = field.lower()

            # Budget changes affect price-related tasks
            if field_lower == "budget":
                if any(w in name_lower or w in input_str for w in ["price", "budget", "cost", "hotel", "calculate"]):
                    return True

            # People changes affect capacity/cost tasks
            if field_lower in ("num_people", "num_people_delta"):
                if any(w in name_lower or w in input_str for w in ["people", "person", "room", "budget", "cost", "calculate"]):
                    return True

            # Walking changes affect destination/activity selection
            if field_lower == "max_walking":
                if any(w in name_lower or w in input_str for w in ["destination", "activity", "itinerary", "walking"]):
                    return True

            # City changes affect everything
            if field_lower == "city":
                return True

            # Duration changes
            if field_lower == "duration_days":
                if any(w in name_lower or w in input_str for w in ["itinerary", "hotel", "night", "day", "calculate"]):
                    return True

        return False

    def _build_goal_string(self, constraints: dict[str, Any]) -> str:
        city = constraints.get("city", "").title()
        days = constraints.get("duration_days", "?")
        people = constraints.get("num_people", "?")
        budget = constraints.get("budget", "?")
        parts = [f"Plan a {days}-day {city} trip for {people} people"]
        if isinstance(budget, int):
            parts[0] += f" under ₹{budget:,}"
        if constraints.get("max_walking"):
            parts.append(f"with max walking level: {constraints['max_walking']}")
        return " ".join(parts)
