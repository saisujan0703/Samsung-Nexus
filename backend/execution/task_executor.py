"""
NEXUS Async Task Executor — Runs tasks concurrently respecting dependencies.

Supports:
- Concurrent execution of independent tasks
- Cooperative cancellation via asyncio.Event
- Progress reporting via event bus
- Safe cleanup of orphan tasks
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable, TYPE_CHECKING

from backend.execution.task_graph import Task, TaskGraph, TaskStatus
from backend.realtime.events import EventBus, EventType

if TYPE_CHECKING:
    from backend.tools.base import ToolRegistry


class TaskExecutor:
    """
    Executes tasks from a TaskGraph concurrently.

    The executor polls the graph for ready tasks (dependencies met),
    launches them as asyncio tasks, and updates their status on
    completion, failure, or cancellation.
    """

    def __init__(
        self,
        task_graph: TaskGraph,
        tool_registry: "ToolRegistry",
        event_bus: EventBus,
        session_id: str = "",
    ) -> None:
        self.graph = task_graph
        self.tools = tool_registry
        self.event_bus = event_bus
        self.session_id = session_id
        self.plan_version: int = 1

        # Maps task_id -> (asyncio.Task, cancel_event, execution_id, plan_version)
        self._running: dict[str, tuple[asyncio.Task, asyncio.Event, str, int]] = {}
        self._execution_task: asyncio.Task | None = None
        self._stopped = asyncio.Event()
        self._stopped.set()  # not running initially

    # -- Lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """Start the execution loop."""
        if self._execution_task and not self._execution_task.done():
            return  # already running
        self._stopped.clear()
        self._execution_task = asyncio.create_task(self._execution_loop())

    async def stop(self) -> None:
        """Stop the execution loop and cancel all running tasks."""
        self._stopped.set()
        if self._execution_task and not self._execution_task.done():
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass
        await self._cancel_all_running("executor_stopped")

    async def wait_for_completion(self, timeout: float | None = None) -> bool:
        """Wait until all tasks are complete or timeout."""
        start_time = asyncio.get_running_loop().time()
        try:
            while not self.graph.is_complete and not self._stopped.is_set():
                await asyncio.sleep(0.05)
                if timeout is not None and (asyncio.get_running_loop().time() - start_time) >= timeout:
                    return False
            return self.graph.is_complete
        except asyncio.CancelledError:
            return False

    # -- Execution Loop ----------------------------------------------------

    async def _execution_loop(self) -> None:
        """Main loop: continuously schedule ready tasks."""
        try:
            while not self._stopped.is_set():
                # Schedule any tasks that are ready
                ready_tasks = self.graph.get_ready_tasks()
                for task in ready_tasks:
                    if task.id not in self._running:
                        await self._launch_task(task)

                # Clean up finished asyncio tasks
                self._cleanup_finished()

                # Check if everything is done
                if self.graph.is_complete:
                    break

                await asyncio.sleep(0.05)  # 50ms poll interval
        except asyncio.CancelledError:
            pass

    async def _launch_task(self, task: Task) -> None:
        """Launch a single task as an asyncio coroutine."""
        if task.id in self._running:
            return  # Prevent duplicate launching of same task ID

        import uuid
        execution_id = f"{task.id}_p{self.plan_version}_{uuid.uuid4().hex[:6]}"
        cancel_event = asyncio.Event()

        # Transition to RUNNING
        try:
            self.graph.update_task_status(task.id, TaskStatus.RUNNING)
        except Exception:
            return

        await self.event_bus.emit(
            EventType.TASK_STARTED,
            session_id=self.session_id,
            task_id=task.id,
            task_name=task.name,
            tool=task.tool,
        )

        # Create the asyncio task
        atask = asyncio.create_task(
            self._run_task(task, cancel_event, execution_id, self.plan_version)
        )
        self._running[task.id] = (atask, cancel_event, execution_id, self.plan_version)

    async def _run_task(
        self,
        task: Task,
        cancel_event: asyncio.Event,
        execution_id: str,
        current_plan_version: int,
    ) -> None:
        """Execute a single task using its designated tool."""
        try:
            tool = self.tools.get_tool(task.tool)
            if tool is None:
                raise ValueError(f"Unknown tool: {task.tool}")

            await self.event_bus.emit(
                EventType.TOOL_CALLED,
                session_id=self.session_id,
                task_id=task.id,
                tool_name=task.tool,
                input=task.input,
            )

            await self.event_bus.emit(
                EventType.TOOL_PROGRESS,
                session_id=self.session_id,
                task_id=task.id,
                tool_name=task.tool,
                status="executing",
            )

            # Resolve dependency outputs to enrich input for downstream tools
            tool_input = dict(task.input)
            dep_outputs = {}
            for dep_id in task.dependencies:
                dep_task = self.graph.get_task(dep_id)
                if dep_task and dep_task.output:
                    dep_outputs[dep_id] = dep_task.output
            if dep_outputs:
                tool_input["_dependency_outputs"] = dep_outputs

            # Execute the tool
            result = await tool.execute(tool_input, cancel_event)

            # Check for cancellation or stale execution
            running_info = self._running.get(task.id)
            is_current_execution = running_info and running_info[2] == execution_id

            if cancel_event.is_set() or task.status == TaskStatus.CANCELLED or not is_current_execution:
                return

            if self.plan_version != current_plan_version:
                return

            # Store result and mark complete
            self.graph.set_task_output(task.id, result.data)
            if task.status == TaskStatus.RUNNING:
                self.graph.update_task_status(task.id, TaskStatus.COMPLETED)

            await self.event_bus.emit(
                EventType.TASK_COMPLETED,
                session_id=self.session_id,
                task_id=task.id,
                task_name=task.name,
                output_summary=result.summary,
            )

            await self.event_bus.emit(
                EventType.TOOL_COMPLETED,
                session_id=self.session_id,
                task_id=task.id,
                tool_name=task.tool,
                success=True,
            )

        except asyncio.CancelledError:
            if task.status == TaskStatus.RUNNING:
                try:
                    self.graph.update_task_status(task.id, TaskStatus.CANCELLED, "cancelled")
                except Exception:
                    pass
        except Exception as e:
            if task.status == TaskStatus.RUNNING:
                try:
                    self.graph.update_task_status(task.id, TaskStatus.FAILED, str(e))
                except Exception:
                    pass

            await self.event_bus.emit(
                EventType.TASK_FAILED,
                session_id=self.session_id,
                task_id=task.id,
                task_name=task.name,
                error=str(e),
            )

            await self.event_bus.emit(
                EventType.TOOL_FAILED,
                session_id=self.session_id,
                task_id=task.id,
                tool_name=task.tool,
                error=str(e),
            )

    # -- Cancellation ------------------------------------------------------

    async def cancel_task(self, task_id: str, reason: str = "plan_change") -> list[str]:
        """Cancel a specific task and its downstream dependents."""
        cancelled_tasks = self.graph.cancel_task(task_id, reason)
        cancelled_ids = [t.id for t in cancelled_tasks]

        for tid in cancelled_ids:
            if tid in self._running:
                atask, cancel_event, _, _ = self._running.pop(tid)
                cancel_event.set()
                atask.cancel()
                try:
                    await atask
                except (asyncio.CancelledError, Exception):
                    pass

            await self.event_bus.emit(
                EventType.TASK_CANCELLED,
                session_id=self.session_id,
                task_id=tid,
                reason=reason,
            )

        return cancelled_ids

    async def cancel_tasks(self, task_ids: list[str], reason: str = "plan_change") -> list[str]:
        """Cancel multiple tasks."""
        all_cancelled: list[str] = []
        for tid in task_ids:
            cancelled = await self.cancel_task(tid, reason)
            all_cancelled.extend(cancelled)
        return list(set(all_cancelled))

    async def _cancel_all_running(self, reason: str = "shutdown") -> None:
        """Cancel all currently running asyncio tasks."""
        for tid, (atask, cancel_event, _, _) in list(self._running.items()):
            cancel_event.set()
            atask.cancel()
            try:
                await atask
            except (asyncio.CancelledError, Exception):
                pass
        self._running.clear()

    # -- Utilities ---------------------------------------------------------

    def _cleanup_finished(self) -> None:
        """Remove completed asyncio tasks from the running dict."""
        finished = [tid for tid, (at, _, _, _) in self._running.items() if at.done()]
        for tid in finished:
            del self._running[tid]

    @property
    def running_count(self) -> int:
        return len(self._running)

    def get_running_task_ids(self) -> list[str]:
        return list(self._running.keys())
