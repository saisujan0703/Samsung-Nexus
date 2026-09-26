"""
NEXUS Orchestrator — Central coordinator for the interruptible real-time agent.

Manages agent state machine, routes user inputs and interruptions, coordinates
planning, execution, replanning, and streaming responses.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any

from backend.agent.context_manager import ContextManager
from backend.agent.goal_manager import GoalManager
from backend.agent.interruption_manager import Interruption, InterruptionManager, InterruptionType
from backend.agent.planner import Planner
from backend.agent.replanner import Replanner
from backend.agent.response_manager import ResponseManager
from backend.execution.task_executor import TaskExecutor
from backend.execution.task_graph import TaskGraph, TaskStatus
from backend.providers.base import LLMProvider
from backend.realtime.events import EventBus, EventType
from backend.tools.base import ToolRegistry


class AgentState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    REPLANNING = "REPLANNING"


class Orchestrator:
    """
    Coordinates all NEXUS agent subsystems into an interruptible execution loop.
    """

    def __init__(
        self,
        session_id: str,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
    ) -> None:
        self.session_id = session_id
        self.llm = llm_provider
        self.tools = tool_registry
        self.event_bus = event_bus

        self.state: AgentState = AgentState.IDLE
        self.previous_state: AgentState = AgentState.IDLE
        self.plan_version: int = 1

        # Subsystems
        self.task_graph = TaskGraph()
        self.goal_manager = GoalManager(event_bus, session_id)
        self.context_manager = ContextManager(event_bus, session_id)
        self.interruption_manager = InterruptionManager(llm_provider, event_bus, session_id)
        self.planner = Planner(llm_provider, event_bus, session_id)
        self.replanner = Replanner(llm_provider, event_bus, session_id)
        self.response_manager = ResponseManager(llm_provider, event_bus, session_id)
        self.executor = TaskExecutor(self.task_graph, self.tools, event_bus, session_id)

        # Wire task completion to findings
        self._execution_monitor_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # Evaluation & Latency Metrics
        self.metrics: dict[str, Any] = {
            "input_count": 0,
            "interruption_count": 0,
            "last_input_ts": None,
            "last_interruption_ts": None,
            "last_planning_duration_ms": 0.0,
            "last_response_generation_ms": 0.0,
        }

    # -- State Management --------------------------------------------------

    async def set_state(self, new_state: AgentState, reason: str = "") -> None:
        """Transitions agent state and emits event."""
        if self.state == new_state:
            return
        self.previous_state = self.state
        self.state = new_state
        await self.event_bus.emit(
            EventType.AGENT_STATE_CHANGED,
            session_id=self.session_id,
            state=new_state.value,
            previous_state=self.previous_state.value,
            reason=reason,
        )

    # -- Input Handling ----------------------------------------------------

    async def handle_user_input(self, text: str) -> dict[str, Any]:
        """
        Handle incoming text or speech transcript from user.
        Determines if it's an initial command or a live interruption.
        """
        async with self._lock:
            text = text.strip()
            if not text:
                return {"status": "empty"}

            await self.context_manager.add_conversation_turn("user", text)
            await self.event_bus.emit(
                EventType.USER_TEXT_INPUT,
                session_id=self.session_id,
                text=text,
            )

            is_active = self.state in (
                AgentState.EXECUTING,
                AgentState.SPEAKING,
                AgentState.THINKING,
                AgentState.REPLANNING,
                AgentState.INTERRUPTED,
            )

            if is_active:
                return await self._handle_interruption(text)
            else:
                return await self._handle_new_goal(text)

    async def handle_speech_started(self) -> None:
        """Process an immediate user speech onset signal from WebSocket."""
        async with self._lock:
            await self.event_bus.emit(
                EventType.USER_SPEECH_STARTED,
                session_id=self.session_id,
            )
            if self.state in (
                AgentState.SPEAKING,
                AgentState.EXECUTING,
                AgentState.THINKING,
                AgentState.REPLANNING,
            ):
                if self.state == AgentState.SPEAKING:
                    self.response_manager.cancel_response()
                await self.set_state(AgentState.INTERRUPTED, reason="user_speech_started")

    async def _handle_interruption(self, text: str) -> dict[str, Any]:
        """Process a live user interruption while agent is active."""
        agent_was_speaking = self.state == AgentState.SPEAKING
        agent_was_executing = self.state == AgentState.EXECUTING

        # Instantly silence speech if speaking
        if agent_was_speaking:
            self.response_manager.cancel_response()

        await self.set_state(AgentState.INTERRUPTED, reason="user_interruption")
        await self.context_manager.record_interruption()

        # Classify the interruption
        current_goal = self.goal_manager.get_goal_summary()
        interruption: Interruption = await self.interruption_manager.classify_interruption(
            text=text,
            agent_was_speaking=agent_was_speaking,
            agent_was_executing=agent_was_executing,
            current_goal=current_goal,
        )

        # Quick spoken acknowledgment
        ack_speech = await self.response_manager.acknowledge_interruption(
            interruption.type.value,
            interruption.details,
            text,
        )

        # Route by interruption category
        if interruption.type == InterruptionType.BACKCHANNEL:
            # User said "ok", "yeah", etc. Resume previous activity without altering plan.
            await self.set_state(
                self.previous_state if self.previous_state != AgentState.INTERRUPTED else AgentState.EXECUTING,
                reason="backchannel_resumed",
            )
            return {"status": "backchannel_resumed", "classification": interruption.model_dump()}

        elif interruption.type == InterruptionType.CONSTRAINT_CHANGE:
            return await self._handle_constraint_change_interruption(interruption, ack_speech)

        elif interruption.type == InterruptionType.GOAL_CHANGE:
            return await self._handle_goal_change_interruption(interruption, ack_speech)

        elif interruption.type == InterruptionType.NEW_GOAL:
            return await self._handle_new_goal_interruption(interruption, ack_speech)

        elif interruption.type == InterruptionType.TASK_CANCELLATION:
            return await self._handle_cancellation_interruption(interruption, ack_speech)

        elif interruption.type == InterruptionType.CORRECTION:
            # Treat correction as constraint change
            return await self._handle_constraint_change_interruption(interruption, ack_speech)

        elif interruption.type == InterruptionType.QUESTION:
            return await self._handle_question_interruption(interruption, ack_speech)

        # Fallback
        await self.set_state(AgentState.EXECUTING, reason="fallback_resume")
        return {"status": "processed", "classification": interruption.model_dump()}

    async def _handle_constraint_change_interruption(
        self,
        interruption: Interruption,
        ack_speech: str = "",
    ) -> dict[str, Any]:
        """Apply constraint change via Replanner without full restart."""
        self.plan_version += 1
        self.executor.plan_version = self.plan_version
        await self.set_state(AgentState.REPLANNING, reason="constraint_change")

        # 1. Update Goal constraints
        changes = interruption.details
        if not changes:
            # Fallback extraction
            changes = {"raw_constraint_update": interruption.raw_text}

        actual_changes = await self.goal_manager.update_constraints(
            changes, reason=interruption.reasoning or "user_interrupted"
        )

        # 2. Preserve valid findings and context
        await self.context_manager.preserve_context(f"Constraints modified: {list(actual_changes.keys())}")

        # 3. Compute Plan Diff
        diff = await self.replanner.compute_diff(
            task_graph=self.task_graph,
            new_constraints=self.goal_manager.get_constraints(),
            changed_fields=actual_changes if actual_changes else changes,
        )

        # 4. Apply Diff to Task Graph (selectively cancel, modify, add)
        apply_summary = await self.replanner.apply_diff(
            task_graph=self.task_graph,
            diff=diff,
            executor_cancel_callback=self.executor.cancel_task,
        )

        # 5. Resume execution with updated graph
        await self.set_state(AgentState.EXECUTING, reason="replan_applied")
        self._ensure_execution_running()

        return {
            "status": "replanned",
            "diff": diff.to_dict(),
            "apply_summary": apply_summary,
            "ack": ack_speech,
        }

    async def _handle_goal_change_interruption(
        self,
        interruption: Interruption,
        ack_speech: str = "",
    ) -> dict[str, Any]:
        """Goal modified — replan affected elements."""
        self.plan_version += 1
        self.executor.plan_version = self.plan_version
        await self.set_state(AgentState.REPLANNING, reason="goal_change")
        new_summary = f"{self.goal_manager.get_goal_summary()} (Modified: {interruption.raw_text})"
        constraints = self.goal_manager.get_constraints()

        # Update goal
        await self.goal_manager.set_goal(
            summary=new_summary,
            constraints=constraints,
            raw_input=interruption.raw_text,
        )

        diff = await self.replanner.compute_diff(
            task_graph=self.task_graph,
            new_constraints=constraints,
            changed_fields={"goal": new_summary},
        )
        apply_summary = await self.replanner.apply_diff(
            task_graph=self.task_graph,
            diff=diff,
            executor_cancel_callback=self.executor.cancel_task,
        )

        await self.set_state(AgentState.EXECUTING, reason="goal_replan_applied")
        self._ensure_execution_running()

        return {"status": "goal_changed", "diff": diff.to_dict(), "apply_summary": apply_summary, "ack": ack_speech}

    async def _handle_new_goal_interruption(
        self,
        interruption: Interruption,
        ack_speech: str = "",
    ) -> dict[str, Any]:
        """Complete pivot to a brand new goal."""
        self.plan_version += 1
        self.executor.plan_version = self.plan_version
        await self.executor.stop()
        await self.set_state(AgentState.THINKING, reason="new_goal_pivot")

        # Plan from scratch for new goal
        tasks = await self.planner.create_plan(
            goal=interruption.raw_text,
            constraints={},
            task_graph=self.task_graph,
            context=self.context_manager.get_context_summary(),
        )

        await self.goal_manager.set_goal(
            summary=interruption.raw_text,
            constraints=self.planner.llm._extract_constraint_changes(interruption.raw_text) if hasattr(self.planner.llm, "_extract_constraint_changes") else {},
            raw_input=interruption.raw_text,
        )

        await self.set_state(AgentState.EXECUTING, reason="new_plan_starting")
        self._ensure_execution_running()

        return {"status": "new_goal_started", "tasks_count": len(tasks), "ack": ack_speech}

    async def _handle_cancellation_interruption(
        self,
        interruption: Interruption,
        ack_speech: str = "",
    ) -> dict[str, Any]:
        """Cancel specific or active tasks."""
        self.plan_version += 1
        self.executor.plan_version = self.plan_version
        cancelled = await self.executor.cancel_tasks(
            self.executor.get_running_task_ids(),
            reason="user_requested_cancellation",
        )
        if not self.task_graph.has_active_tasks:
            await self.set_state(AgentState.IDLE, reason="all_cancelled")
        else:
            await self.set_state(AgentState.EXECUTING, reason="resumed_remaining")
        return {"status": "cancelled", "cancelled_tasks": cancelled, "ack": ack_speech}

    async def _handle_question_interruption(
        self,
        interruption: Interruption,
        ack_speech: str = "",
    ) -> dict[str, Any]:
        """Answer a side question without halting background work."""
        # Speak answer
        ans = f"Regarding your question '{interruption.raw_text}': based on current findings, {self.context_manager.get_context_summary()[:150]}."
        await self.set_state(AgentState.SPEAKING, reason="answering_question")
        
        # Async task to speak and resume
        async def speak_and_resume():
            await self.response_manager.generate_task_response(
                task_results=[{"name": "Question Answer", "status": "COMPLETED", "output": {"answer": ans}}],
                goal=interruption.raw_text,
                context=self.context_manager.get_context_summary(),
            )
            if self.task_graph.has_active_tasks:
                await self.set_state(AgentState.EXECUTING, reason="resume_after_question")
            else:
                await self.set_state(AgentState.IDLE, reason="question_completed")

        asyncio.create_task(speak_and_resume())
        return {"status": "answering_question", "answer": ans, "ack": ack_speech}

    # -- New Goal Flow -----------------------------------------------------

    async def _handle_new_goal(self, text: str) -> dict[str, Any]:
        """Initial goal creation and execution trigger."""
        self.plan_version += 1
        self.executor.plan_version = self.plan_version
        await self.set_state(AgentState.THINKING, reason="initial_planning")

        # 1. Initial Plan Creation
        tasks = await self.planner.create_plan(
            goal=text,
            constraints={},
            task_graph=self.task_graph,
            context=self.context_manager.get_context_summary(),
        )

        # 2. Extract initial constraints for GoalManager
        initial_constraints = {}
        if hasattr(self.llm, "_extract_constraint_changes"):
            initial_constraints = self.llm._extract_constraint_changes(text)

        await self.goal_manager.set_goal(
            summary=text,
            constraints=initial_constraints,
            raw_input=text,
        )
        await self.context_manager.update_goal(text, initial_constraints)

        # 3. Start Execution
        await self.set_state(AgentState.EXECUTING, reason="starting_plan_execution")
        self._ensure_execution_running()

        return {
            "status": "plan_started",
            "goal": text,
            "tasks": [t.to_dict() for t in tasks],
        }

    # -- Execution Monitoring ----------------------------------------------

    def _ensure_execution_running(self) -> None:
        """Start or restart the task executor loop and monitoring."""
        asyncio.create_task(self.executor.start())
        if self._execution_monitor_task and not self._execution_monitor_task.done():
            self._execution_monitor_task.cancel()
        self._execution_monitor_task = asyncio.create_task(self._monitor_execution_loop())

    async def _monitor_execution_loop(self) -> None:
        """Monitors task execution progress and completes response when all tasks finish."""
        start_version = self.plan_version
        try:
            while not self.task_graph.is_complete:
                await asyncio.sleep(0.1)
                if self.plan_version != start_version:
                    return

            # When complete and not interrupted:
            if self.state == AgentState.EXECUTING and self.plan_version == start_version:
                await self.set_state(AgentState.SPEAKING, reason="tasks_completed")

                completed_tasks = [
                    t.to_dict() for t in self.task_graph.get_tasks_by_status(TaskStatus.COMPLETED)
                ]

                # Record findings to ContextManager
                for t in completed_tasks:
                    if t.get("output"):
                        await self.context_manager.add_finding(
                            task_id=t["id"],
                            category=t.get("tool", "general"),
                            data=t["output"],
                        )

                if self.plan_version != start_version:
                    return

                # Generate speech / text response
                summary = await self.response_manager.generate_task_response(
                    task_results=completed_tasks,
                    goal=self.goal_manager.get_goal_summary(),
                    context=self.context_manager.get_context_summary(),
                )
                if self.plan_version == start_version and self.state == AgentState.SPEAKING:
                    await self.context_manager.add_conversation_turn("assistant", summary)
                    await self.set_state(AgentState.IDLE, reason="response_finished")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Orchestrator] Execution monitor error: {e}")
            if self.plan_version == start_version:
                await self.set_state(AgentState.IDLE, reason=f"error_{e}")

    # -- Image Handling ----------------------------------------------------

    async def handle_image_upload(self, image_data: str, prompt: str = "") -> dict[str, Any]:
        """Handle user multimodal image input."""
        async with self._lock:
            # 1. Image payload validation
            if not image_data or not isinstance(image_data, str):
                await self.event_bus.emit(
                    EventType.ERROR,
                    session_id=self.session_id,
                    error="Invalid image upload payload",
                )
                return {"status": "error", "error": "Invalid image payload"}

            # Max 10MB base64 payload size check (~14 million chars)
            if len(image_data) > 14_000_000:
                await self.event_bus.emit(
                    EventType.ERROR,
                    session_id=self.session_id,
                    error="Image payload exceeds 10MB size limit",
                )
                return {"status": "error", "error": "Image payload exceeds 10MB size limit"}

            # Format check if data URI format
            if "," in image_data:
                header = image_data.split(",", 1)[0].lower()
                if not any(fmt in header for fmt in ["png", "jpeg", "jpg", "webp", "gif"]):
                    await self.event_bus.emit(
                        EventType.ERROR,
                        session_id=self.session_id,
                        error="Unsupported image format",
                    )
                    return {"status": "error", "error": "Unsupported image format"}

            start_version = self.plan_version

            await self.event_bus.emit(
                EventType.USER_IMAGE_UPLOAD,
                session_id=self.session_id,
                prompt=prompt,
            )
            await self.event_bus.emit(
                EventType.IMAGE_RECEIVED,
                session_id=self.session_id,
                prompt=prompt,
            )
            await self.event_bus.emit(
                EventType.IMAGE_PROCESSING,
                session_id=self.session_id,
                prompt=prompt,
            )

            try:
                # 2. Analyze image using provider / tool
                analysis = await self.llm.analyze_image(image_data, prompt)

                # 3. Check for interruption / plan version change
                if self.plan_version != start_version:
                    return {"status": "stale_ignored", "reason": "plan_version_changed"}

                # 4. Integrate into Session Context
                await self.context_manager.add_finding(
                    task_id="image_upload",
                    category="vision",
                    data={"analysis": analysis, "prompt": prompt or "Image uploaded"},
                )
                await self.context_manager.add_conversation_turn("user", f"[Uploaded Image] {prompt if prompt else 'Image attached'}")
                await self.context_manager.add_conversation_turn("assistant", f"[Visual Analysis] {analysis}")

                await self.event_bus.emit(
                    EventType.IMAGE_CONTEXT_READY,
                    session_id=self.session_id,
                    analysis=analysis,
                    prompt=prompt,
                )

                # 5. If prompt contains text or agent is active, trigger contextual replan
                if prompt.strip() and self.state in (AgentState.EXECUTING, AgentState.SPEAKING, AgentState.THINKING):
                    await self.set_state(AgentState.REPLANNING, reason="multimodal_replan")
                    diff = await self.replanner.compute_diff(
                        task_graph=self.task_graph,
                        new_constraints=self.goal_manager.get_constraints(),
                        changed_fields={"image_context": analysis, "prompt": prompt},
                    )
                    apply_summary = await self.replanner.apply_diff(
                        task_graph=self.task_graph,
                        diff=diff,
                        executor_cancel_callback=self.executor.cancel_task,
                    )
                    await self.set_state(AgentState.EXECUTING, reason="multimodal_replan_applied")
                    self._ensure_execution_running()

                return {"status": "image_analyzed", "analysis": analysis}

            except Exception as e:
                await self.event_bus.emit(
                    EventType.ERROR,
                    session_id=self.session_id,
                    error=f"Image processing failed: {e}",
                )
                return {"status": "error", "error": str(e)}

    # -- Snapshot & Status -------------------------------------------------

    def get_snapshot(self) -> dict[str, Any]:
        """Returns complete serializable snapshot of agent state."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "previous_state": self.previous_state.value,
            "plan_version": self.plan_version,
            "goal": self.goal_manager.to_dict(),
            "context": self.context_manager.to_dict(),
            "task_graph": self.task_graph.to_dict(),
            "running_tasks": self.executor.get_running_task_ids(),
            "completed_tasks": [t.id for t in self.task_graph.get_tasks_by_status(TaskStatus.COMPLETED)],
            "cancelled_tasks": [t.id for t in self.task_graph.get_tasks_by_status(TaskStatus.CANCELLED)],
            "interruption_count": self.interruption_manager.get_interruption_count(),
            "metrics": dict(self.metrics),
        }
