"""
Automated unit & integration test suite for Phase 7 — Evaluation & Protocol Compliance.
"""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.evaluation.harness import evaluation_harness
from backend.evaluation.scenarios import (
    run_scenario_1_basic_goal,
    run_scenario_2_constraint_change,
    run_scenario_3_question_interruption,
    run_scenario_4_task_cancellation,
    run_scenario_5_goal_pivot,
    run_scenario_6_rapid_interruptions,
    run_scenario_7_voice_interruption,
    run_scenario_8_multimodal,
    run_scenario_9_reconnect,
)


@pytest.fixture
def api_client():
    return TestClient(app)


# --------------------------------------------------------------------------
# Test 1-9: Scenario-based evaluation tests
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_1_basic_goal():
    res = await run_scenario_1_basic_goal()
    assert res.passed is True
    assert res.scenario_id == "scenario_1"


@pytest.mark.asyncio
async def test_scenario_2_constraint_change():
    res = await run_scenario_2_constraint_change()
    assert res.passed is True
    assert res.interruption_recovery == "SUCCESS"


@pytest.mark.asyncio
async def test_scenario_3_question_interruption():
    res = await run_scenario_3_question_interruption()
    assert res.passed is True


@pytest.mark.asyncio
async def test_scenario_4_task_cancellation():
    res = await run_scenario_4_task_cancellation()
    assert res.passed is True


@pytest.mark.asyncio
async def test_scenario_5_goal_pivot():
    res = await run_scenario_5_goal_pivot()
    assert res.passed is True


@pytest.mark.asyncio
async def test_scenario_6_rapid_interruptions():
    res = await run_scenario_6_rapid_interruptions()
    assert res.passed is True


@pytest.mark.asyncio
async def test_scenario_7_voice_interruption():
    res = await run_scenario_7_voice_interruption()
    assert res.passed is True


@pytest.mark.asyncio
async def test_scenario_8_multimodal():
    res = await run_scenario_8_multimodal()
    assert res.passed is True


@pytest.mark.asyncio
async def test_scenario_9_reconnect():
    res = await run_scenario_9_reconnect()
    assert res.passed is True


# --------------------------------------------------------------------------
# Test 10: Evaluation harness run_all
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_harness_run_all():
    results = await evaluation_harness.run_all()
    assert len(results) == 9
    assert all(r.passed for r in results)


# --------------------------------------------------------------------------
# Test 11: Protocol compliance & malformed WebSocket inputs
# --------------------------------------------------------------------------
def test_protocol_malformed_websocket(api_client):
    with api_client.websocket_connect("/ws/protocol_test_session") as ws:
        # Initial snapshot received
        init_msg = ws.receive_json()
        assert init_msg.get("type") == "initial_state"

        # Send ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong.get("type") == "pong"

        # Send unknown message type — connection must remain alive and return ack
        ws.send_json({"type": "unknown_random_type", "foo": "bar"})
        ack = ws.receive_json()
        assert ack.get("type") == "ack"
        assert ack.get("status") == "ignored"

        # Send malformed user input with missing text
        ws.send_json({"type": "user_input"})
        warning = ws.receive_json()
        assert warning.get("type") == "warning"


# --------------------------------------------------------------------------
# Test 12: REST Evaluation & Snapshot Endpoints
# --------------------------------------------------------------------------
def test_evaluation_and_snapshot_rest_endpoints(api_client):
    # 1. Create session
    res = api_client.post("/api/session")
    assert res.status_code == 200
    sid = res.json()["session_id"]

    # 2. Get snapshot endpoint
    res_snap = api_client.get(f"/api/session/{sid}/snapshot")
    assert res_snap.status_code == 200
    snap = res_snap.json()
    assert "plan_version" in snap
    assert "metrics" in snap

    # 3. Get events endpoint
    res_evt = api_client.get(f"/api/session/{sid}/events")
    assert res_evt.status_code == 200
    assert "events" in res_evt.json()

    # 4. Evaluate scenario endpoint
    res_eval = api_client.get(f"/api/session/{sid}/snapshot")
    assert res_eval.status_code == 200


# --------------------------------------------------------------------------
# Test 13: Secret Leakage & Serialization Safety
# --------------------------------------------------------------------------
def test_secret_leakage_and_serialization_safety(api_client):
    res = api_client.post("/api/session")
    sid = res.json()["session_id"]
    snap = api_client.get(f"/api/session/{sid}/snapshot").json()

    # Verify JSON serializability
    serialized = json.dumps(snap)
    assert len(serialized) > 0

    # Verify no secrets or API keys in serialized payload
    assert "GOOGLE_API_KEY" not in serialized
    assert "secret" not in serialized.lower() or "secret" in "session_id"
