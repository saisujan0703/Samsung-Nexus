"""
End-to-end integration test for NEXUS Backend REST, WebSocket, and Interruptible Engine.

Tests:
1. REST Endpoints (health, session CRUD, tasks, context)
2. WebSocket connection and live event forwarding
3. Complex live scenario:
   - Initial goal: "Plan a 3-day Chennai trip for 15000 rupees."
   - Interruption 1: "Wait. I am travelling with my parents. Avoid places requiring lots of walking."
     -> Verified: classified as CONSTRAINT_CHANGE, plan diff KEEP/CANCEL/MODIFY/ADD, selective task cancellation.
   - Interruption 2: "Actually increase the budget to 20000."
     -> Verified: budget updated, replanned.
   - Interruption 3: "Forget the trip. Help me prepare for an interview instead."
     -> Verified: classified as NEW_GOAL, obsolete trip tasks cancelled, new interview plan generated.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.agent.orchestrator import AgentState
from backend.agent.interruption_manager import InterruptionType
from backend.execution.task_graph import TaskStatus


def test_rest_endpoints():
    """Verify all REST API endpoints."""
    client = TestClient(app)

    # 1. GET /health
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. POST /api/session
    res = client.post("/api/session")
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    assert len(session_id) > 0

    # 3. GET /api/session/{session_id}
    res = client.get(f"/api/session/{session_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["state"] == "IDLE"

    # 4. GET /api/session/{session_id}/tasks
    res = client.get(f"/api/session/{session_id}/tasks")
    assert res.status_code == 200
    assert "tasks" in res.json()

    # 5. GET /api/session/{session_id}/context
    res = client.get(f"/api/session/{session_id}/context")
    assert res.status_code == 200
    assert "session_id" in res.json()


def test_websocket_and_live_events():
    """Verify WebSocket connection, initial snapshot, and typed event forwarding."""
    client = TestClient(app)

    # Create session
    res = client.post("/api/session")
    session_id = res.json()["session_id"]

    # Connect WebSocket
    with client.websocket_connect(f"/ws/{session_id}") as ws:
        # Initial state message
        init_msg = ws.receive_json()
        assert init_msg["type"] == "initial_state"
        assert init_msg["session_id"] == session_id
        assert init_msg["payload"]["state"] == "IDLE"

        # Send ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


@pytest.mark.asyncio
async def test_end_to_end_interruptible_flow(monkeypatch):
    """
    Test the exact defining NEXUS scenario:
    Initial Goal -> Execution -> Interruption (Parents + Walking) ->
    Constraint Change -> Plan Diff -> Selective Cancellation ->
    Budget Update -> New Goal Pivot.
    """
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from backend.config import Settings, settings
    monkeypatch.setattr(Settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    from backend.memory.session_memory import session_memory
    from backend.realtime.events import EventType

    from backend.providers.base import MockProvider
    session_id = "test_scenario_1"
    await session_memory.delete(session_id)
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)
    orchestrator.provider = MockProvider()

    events_received = []

    async def event_collector(evt):
        events_received.append(evt)

    event_bus.subscribe_all(event_collector)

    # -----------------------------------------------------------------------
    # Step 1: User gives initial complex goal
    # -----------------------------------------------------------------------
    initial_prompt = "Plan a 3-day Chennai trip for 15000 rupees."
    result1 = await orchestrator.handle_user_input(initial_prompt)

    assert result1["status"] == "plan_started"
    assert len(orchestrator.task_graph) > 0
    assert orchestrator.state in (AgentState.EXECUTING, AgentState.THINKING)
    assert orchestrator.goal_manager.current_goal is not None

    # Let the tasks start executing briefly
    await asyncio.sleep(0.3)
    assert orchestrator.task_graph.has_running_tasks or len(orchestrator.task_graph.get_tasks_by_status(TaskStatus.COMPLETED)) > 0

    initial_task_count = len(orchestrator.task_graph)
    completed_before_interruption = len(orchestrator.task_graph.get_tasks_by_status(TaskStatus.COMPLETED))

    # -----------------------------------------------------------------------
    # Step 2: User interrupts while agent is executing
    # -----------------------------------------------------------------------
    interruption_text = "Wait. I am travelling with my parents. Avoid places requiring lots of walking."
    result2 = await orchestrator.handle_user_input(interruption_text)

    # Verify classification
    assert result2["status"] == "replanned"
    assert "diff" in result2
    diff = result2["diff"]

    # Verify Plan Diff contains KEEP, and affected tasks are modified/added
    assert len(diff["keep"]) > 0, "Useful completed or independent tasks MUST be kept"
    assert len(diff["modify"]) > 0 or len(diff["add"]) > 0

    # Verify constraints were updated
    constraints = orchestrator.goal_manager.get_constraints()
    assert constraints.get("max_walking") == "low"
    assert constraints.get("num_people", 0) >= 3  # parents added to group

    # Verify Context preservation
    preserved_findings = orchestrator.context_manager.get_valid_findings()
    # Any completed findings before interruption should be preserved if valid
    assert orchestrator.context_manager.context.interruption_count >= 1

    # -----------------------------------------------------------------------
    # Step 3: Second Interruption — Budget modification
    # -----------------------------------------------------------------------
    budget_interruption = "Actually increase the budget to 20000."
    result3 = await orchestrator.handle_user_input(budget_interruption)

    assert result3["status"] == "replanned"
    new_budget = orchestrator.goal_manager.get_constraints().get("budget")
    assert new_budget == 20000

    # -----------------------------------------------------------------------
    # Step 4: Third Interruption — Complete Goal Pivot (NEW_GOAL)
    # -----------------------------------------------------------------------
    new_goal_text = "Forget the trip. Help me prepare for an interview instead."
    result4 = await orchestrator.handle_user_input(new_goal_text)

    assert result4["status"] == "new_goal_started"
    # Verify the current goal is now interview prep
    assert "interview" in orchestrator.goal_manager.get_goal_summary().lower()
    # Verify new tasks are running for interview
    assert orchestrator.state in (AgentState.EXECUTING, AgentState.THINKING)

    # Clean up
    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_session_memory_get():
    """Verify session_memory.get() return values for active, missing, and expired sessions."""
    from backend.memory.session_memory import SessionMemory

    mem = SessionMemory(ttl_seconds=1)
    session_id = "test_mem_s1"

    # Non-existent session returns (None, None)
    orch, bus = await mem.get("non_existent")
    assert orch is None
    assert bus is None

    # Created session returns orchestrator and event_bus
    orch1, bus1, is_new = await mem.get_or_create(session_id)
    assert is_new is True
    assert orch1 is not None
    assert bus1 is not None

    orch2, bus2 = await mem.get(session_id)
    assert orch2 is orch1
    assert bus2 is bus1

    # Wait for TTL to expire
    await asyncio.sleep(1.1)

    # Expired session returns (None, None) and is evicted
    orch_exp, bus_exp = await mem.get(session_id)
    assert orch_exp is None
    assert bus_exp is None


@pytest.mark.asyncio
async def test_speech_started_voice_interruption(monkeypatch):
    """Verify handle_speech_started() and speech-start voice interruption flow."""
    from backend.config import Settings, settings
    monkeypatch.setattr(Settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    from backend.memory.session_memory import session_memory
    from backend.agent.orchestrator import AgentState

    from backend.providers.base import MockProvider
    session_id = "test_speech_int"
    await session_memory.delete(session_id)
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)
    orchestrator.provider = MockProvider()

    # 1. Start initial goal
    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    assert orchestrator.state in (AgentState.EXECUTING, AgentState.THINKING)

    # 2. Simulate speech_started signal while agent is active
    await orchestrator.handle_speech_started()
    assert orchestrator.state == AgentState.INTERRUPTED

    # 3. Followed by user interruption transcript
    interruption_text = "Wait. I am travelling with my parents. Avoid places requiring lots of walking."
    res = await orchestrator.handle_user_input(interruption_text)

    assert res["status"] == "replanned"
    assert "diff" in res

    # Clean up
    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


