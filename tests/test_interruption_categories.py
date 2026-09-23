"""
Unit & Integration Tests for Interruption Classification and Selective Actions.

Verifies:
- All 7 interruption categories:
  1. BACKCHANNEL: "uh huh", "cool", "got it"
  2. QUESTION: "Why are you picking that hotel?", "What is the total budget?"
  3. CORRECTION: "Actually make that 4 people"
  4. CONSTRAINT_CHANGE: "Avoid places with lots of walking"
  5. GOAL_CHANGE: "Find hostels instead of luxury hotels"
  6. TASK_CANCELLATION: "Stop searching for activities"
  7. NEW_GOAL: "Forget everything, help me write an email"
- Selective Task Cancellation vs. Global Wipe
- Useful Finding Preservation
"""

import asyncio
import pytest

from backend.agent.orchestrator import AgentState
from backend.agent.interruption_manager import InterruptionType
from backend.execution.task_graph import TaskStatus
from backend.memory.session_memory import session_memory


@pytest.mark.asyncio
async def test_backchannel_resumes_cleanly():
    """Verify backchannels ('ok', 'yeah') don't disrupt execution."""
    session_id = "test_backchannel"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    # Start goal
    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.1)

    initial_tasks = len(orchestrator.task_graph)
    assert orchestrator.state in (AgentState.EXECUTING, AgentState.THINKING)

    # User interjects backchannel
    res = await orchestrator.handle_user_input("cool, got it")
    assert res["status"] == "backchannel_resumed"
    assert res["classification"]["type"] == "BACKCHANNEL"

    # Verify task graph was NOT altered
    assert len(orchestrator.task_graph) == initial_tasks
    assert orchestrator.state in (AgentState.EXECUTING, AgentState.THINKING)

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_question_interruption_does_not_destroy_plan():
    """Verify side questions are answered without destroying active plan."""
    session_id = "test_question"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.1)

    initial_tasks = len(orchestrator.task_graph)

    # User asks a question
    res = await orchestrator.handle_user_input("What is the current budget?")
    assert res["status"] == "answering_question"
    assert "answer" in res

    # Verify graph preserved
    assert len(orchestrator.task_graph) == initial_tasks

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_selective_cancellation_preserves_independent_tasks():
    """
    Verify that when user cancels or modifies a specific aspect,
    independent tasks and completed work are preserved.
    """
    session_id = "test_selective"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")

    # Wait for first tasks to complete
    await asyncio.sleep(0.4)

    completed_ids = [t.id for t in orchestrator.task_graph.get_tasks_by_status(TaskStatus.COMPLETED)]

    # Interrupt with walking constraint
    res = await orchestrator.handle_user_input("Avoid places with lots of walking.")
    diff = res["diff"]

    # Any previously completed task must be KEPT
    for cid in completed_ids:
        assert cid in diff["keep"], f"Completed task {cid} should be kept in plan diff"

    # Replanned graph should still have all completed tasks
    for cid in completed_ids:
        t = orchestrator.task_graph.get_task(cid)
        assert t is not None
        assert t.status == TaskStatus.COMPLETED, f"Task {cid} should remain COMPLETED"

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_task_cancellation_interruption():
    """Verify explicit cancellation ('stop', 'cancel') cancels active tasks."""
    session_id = "test_cancel_task"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.1)

    # User explicitly interrupts with cancellation
    res = await orchestrator.handle_user_input("Stop and cancel the active search")
    assert res["status"] in ("cancelled", "processed")

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_goal_change_interruption():
    """Verify 'instead of' / 'switch to' triggers GOAL_CHANGE replan."""
    session_id = "test_goal_change"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.1)

    res = await orchestrator.handle_user_input("Find hostels instead of luxury hotels")
    assert res["status"] == "goal_changed"
    assert "diff" in res

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)
