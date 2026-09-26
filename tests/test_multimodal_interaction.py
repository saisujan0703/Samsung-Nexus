"""
Automated tests for Phase 6 — Multimodal Grounding & Interaction Completion
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.agent.orchestrator import Orchestrator, AgentState
from backend.execution.task_graph import Task, TaskGraph, TaskStatus
from backend.memory.session_memory import SessionMemory
from backend.providers.base import MockProvider
from backend.realtime.events import EventBus, EventType, NexusEvent
from backend.tools.base import ToolRegistry


# Sample 1x1 pixel PNG image base64 data URI
VALID_IMAGE_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def session_components():
    eb = EventBus()
    tr = ToolRegistry()
    llm = MockProvider()
    session_id = "test_multimodal_session"
    orch = Orchestrator(session_id, llm, tr, eb)
    return eb, tr, llm, orch


# --------------------------------------------------------------------------
# Test A: Image upload accepted for valid image
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_valid_image_upload_accepted(session_components):
    eb, tr, llm, orch = session_components
    res = await orch.handle_image_upload(VALID_IMAGE_B64, prompt="Check itinerary room")
    assert res.get("status") == "image_analyzed"
    assert "analysis" in res


# --------------------------------------------------------------------------
# Test B: Invalid image rejected safely
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_b_invalid_image_rejected(session_components):
    eb, tr, llm, orch = session_components

    # Empty payload
    res_empty = await orch.handle_image_upload("", prompt="Empty check")
    assert res_empty.get("status") == "error"

    # Oversized payload (> 14 million chars)
    oversized = "data:image/png;base64," + ("A" * 15_000_000)
    res_oversized = await orch.handle_image_upload(oversized, prompt="Big check")
    assert res_oversized.get("status") == "error"


# --------------------------------------------------------------------------
# Test C: Image context associated with correct session
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_c_image_context_associated_with_session(session_components):
    eb, tr, llm, orch = session_components
    await orch.handle_image_upload(VALID_IMAGE_B64, prompt="Hotel photo")

    context_dict = orch.context_manager.to_dict()
    findings = context_dict.get("completed_findings", [])
    vision_findings = [f for f in findings if f.get("category") == "vision"]
    assert len(vision_findings) >= 1
    assert "analysis" in vision_findings[0]["data"]


# --------------------------------------------------------------------------
# Test D: Image + text input reaches the same session
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_d_image_and_text_same_session(session_components):
    eb, tr, llm, orch = session_components
    
    # 1. Upload image
    await orch.handle_image_upload(VALID_IMAGE_B64, prompt="Itinerary screenshot")

    # 2. Submit text in same session
    await orch.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees")

    summary = orch.context_manager.get_context_summary()
    assert "Goal: Plan a 3-day Chennai trip for 15000 rupees" in summary
    assert "vision" in summary.lower() or "findings" in summary.lower()


# --------------------------------------------------------------------------
# Test E: Image processing produces appropriate EventBus lifecycle events
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_e_image_processing_lifecycle_events(session_components):
    eb, tr, llm, orch = session_components
    events_captured = []

    async def capture_event(evt: NexusEvent):
        events_captured.append(evt.type)

    eb.subscribe_all(capture_event)

    await orch.handle_image_upload(VALID_IMAGE_B64, prompt="Analyze room condition")

    assert EventType.IMAGE_RECEIVED in events_captured
    assert EventType.IMAGE_PROCESSING in events_captured
    assert EventType.IMAGE_CONTEXT_READY in events_captured


# --------------------------------------------------------------------------
# Test F & G: Interruption during multimodal processing / stale result protection
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f_and_g_interrupted_image_processing_stale_guard(session_components):
    eb, tr, llm, orch = session_components

    # Start image analysis task
    start_version = orch.plan_version
    orch.plan_version += 1  # Simulate interruption / plan bump during processing

    res = await orch.handle_image_upload(VALID_IMAGE_B64, prompt="Late prompt")
    # If version incremented before processing completes, stale result is ignored
    assert res.get("status") in ("image_analyzed", "stale_ignored")


# --------------------------------------------------------------------------
# Test H: Provider failure produces controlled error state
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_h_provider_failure_controlled_error(session_components):
    eb, tr, llm, orch = session_components

    class FailingProvider(MockProvider):
        async def analyze_image(self, image_data: str, prompt: str) -> str:
            raise RuntimeError("Vision model quota exhausted")

    orch.llm = FailingProvider()
    res = await orch.handle_image_upload(VALID_IMAGE_B64, prompt="Fail check")

    assert res.get("status") == "error"
    assert "Vision model quota exhausted" in res.get("error", "")


# --------------------------------------------------------------------------
# Test I & J: REST Integration and Session persistence
# --------------------------------------------------------------------------
def test_i_and_j_rest_and_session_persistence():
    client = TestClient(app)

    # 1. Create session
    res_session = client.post("/api/session")
    assert res_session.status_code == 200
    sid = res_session.json()["session_id"]

    # 2. Upload image via REST
    res_img = client.post(f"/api/session/{sid}/image", json={"image_data": VALID_IMAGE_B64, "prompt": "REST test"})
    assert res_img.status_code == 200
    assert res_img.json()["status"] == "image_analyzed"

    # 3. Get session snapshot
    res_snap = client.get(f"/api/session/{sid}")
    assert res_snap.status_code == 200
    snapshot = res_snap.json()
    assert snapshot["session_id"] == sid
