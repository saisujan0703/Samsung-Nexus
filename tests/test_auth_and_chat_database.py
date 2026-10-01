"""
Tests for SURU AI Authentication and SQLite Persistent Chat Database.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
import backend.db as db


@pytest.fixture(autouse=True)
def clean_test_db(tmp_path, monkeypatch):
    """Use an isolated SQLite database for testing."""
    test_db_path = str(tmp_path / "test_suru.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    yield


def test_user_registration_and_duplicate_handling():
    client = TestClient(app)

    # 1. Register a new user
    res1 = client.post(
        "/api/auth/register",
        json={
            "email": "user@gmail.com",
            "password": "secretpassword",
            "display_name": "Saksham",
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ok"
    assert data1["user"]["email"] == "user@gmail.com"
    assert data1["user"]["display_name"] == "Saksham"
    user_id = data1["user"]["id"]

    # 2. Attempt registering with same email (case-insensitive check)
    res2 = client.post(
        "/api/auth/register",
        json={
            "email": "USER@gmail.com",
            "password": "anotherpassword",
            "display_name": "Saksham 2",
        },
    )
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]


def test_user_login_validation():
    client = TestClient(app)

    # Register user
    client.post(
        "/api/auth/register",
        json={
            "email": "loginuser@yahoo.com",
            "password": "correctpassword",
            "display_name": "Tester",
        },
    )

    # Wrong password
    res_wrong = client.post(
        "/api/auth/login",
        json={"email": "loginuser@yahoo.com", "password": "wrongpassword"},
    )
    assert res_wrong.status_code == 401
    assert "Invalid email or password" in res_wrong.json()["detail"]

    # Correct credentials
    res_correct = client.post(
        "/api/auth/login",
        json={"email": "loginuser@yahoo.com", "password": "correctpassword"},
    )
    assert res_correct.status_code == 200
    assert res_correct.json()["user"]["display_name"] == "Tester"


def test_chat_persistence_across_sessions():
    client = TestClient(app)

    # Register user
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "chatuser@custom.com",
            "password": "pwd",
            "display_name": "Alex",
        },
    ).json()
    user_id = reg["user"]["id"]

    # Initially user has no chats
    list1 = client.get(f"/api/user/{user_id}/chats").json()
    assert list1["chats"] == []

    # Save a chat session
    save_res = client.post(
        f"/api/user/{user_id}/chats",
        json={
            "session_id": "session-101",
            "title": "Quantum Physics Exploration",
            "messages": [
                {"id": "m1", "role": "user", "content": "Explain qubits"},
                {"id": "m2", "role": "assistant", "content": "Qubits exist in superposition."},
            ],
            "sports_fixtures": None,
            "goal_summary": "Explain qubits",
        },
    )
    assert save_res.status_code == 200

    # Retrieve saved chats
    list2 = client.get(f"/api/user/{user_id}/chats").json()
    assert len(list2["chats"]) == 1
    saved_chat = list2["chats"][0]
    assert saved_chat["id"] == "session-101"
    assert saved_chat["title"] == "Quantum Physics Exploration"
    assert len(saved_chat["messages"]) == 2
    assert saved_chat["messages"][0]["content"] == "Explain qubits"

    # Delete the chat
    del_res = client.delete(f"/api/user/{user_id}/chats/session-101")
    assert del_res.status_code == 200

    # Verify deleted
    list3 = client.get(f"/api/user/{user_id}/chats").json()
    assert list3["chats"] == []
