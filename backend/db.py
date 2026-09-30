"""
SURU AI Persistent Database — User Accounts & Chat Storage (SQLite).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "suru_chat.db")


def get_db_connection() -> sqlite3.Connection:
    """Create and return a SQLite connection with row factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables for users and chat sessions."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    sports_fixtures TEXT,
                    goal_summary TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id 
                ON user_sessions(user_id, updated_at DESC)
                """
            )
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """Generate SHA-256 hash for password."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


def create_user(email: str, password: str, display_name: str) -> dict[str, Any]:
    """
    Create a new user account.
    Raises ValueError if email is already registered.
    """
    clean_email = email.strip().lower()
    clean_name = display_name.strip() or clean_email.split("@")[0]
    pwd_hash = hash_password(password)
    now = time.time()

    conn = get_db_connection()
    try:
        with conn:
            # Check existing
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (clean_email,)
            ).fetchone()
            if existing:
                raise ValueError("Account already registered. Please log in instead.")

            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, display_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (clean_email, pwd_hash, clean_name, now),
            )
            user_id = cursor.lastrowid
            return {
                "id": user_id,
                "email": clean_email,
                "display_name": clean_name,
                "created_at": now,
            }
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Optional[dict[str, Any]]:
    """Authenticate user with email and password."""
    clean_email = email.strip().lower()
    pwd_hash = hash_password(password)

    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT id, email, password_hash, display_name, created_at
            FROM users
            WHERE email = ?
            """,
            (clean_email,),
        ).fetchone()

        if not row:
            return None

        if row["password_hash"] != pwd_hash:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    """Retrieve user by ID."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def save_user_chat(
    user_id: int,
    session_id: str,
    title: str,
    messages: list[dict[str, Any]],
    sports_fixtures: Optional[dict[str, Any]] = None,
    goal_summary: str = "",
) -> dict[str, Any]:
    """Insert or update a user chat session in the database."""
    now = time.time()
    messages_json = json.dumps(messages)
    sports_json = json.dumps(sports_fixtures) if sports_fixtures else None

    conn = get_db_connection()
    try:
        with conn:
            existing = conn.execute(
                "SELECT created_at FROM user_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()

            created_at = existing["created_at"] if existing else now

            conn.execute(
                """
                INSERT OR REPLACE INTO user_sessions (
                    id, user_id, title, messages, sports_fixtures, goal_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    title,
                    messages_json,
                    sports_json,
                    goal_summary,
                    created_at,
                    now,
                ),
            )
            return {
                "id": session_id,
                "user_id": user_id,
                "title": title,
                "updated_at": now,
            }
    finally:
        conn.close()


def get_user_chats(user_id: int) -> list[dict[str, Any]]:
    """Retrieve all chats for a given user, newest first."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, title, messages, sports_fixtures, goal_summary, created_at, updated_at
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()

        results = []
        for r in rows:
            try:
                msgs = json.loads(r["messages"])
            except Exception:
                msgs = []

            try:
                sports = json.loads(r["sports_fixtures"]) if r["sports_fixtures"] else None
            except Exception:
                sports = None

            results.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "messages": msgs,
                    "sportsFixtures": sports,
                    "goalSummary": r["goal_summary"] or "",
                    "createdAt": r["created_at"] * 1000,
                    "updatedAt": r["updated_at"] * 1000,
                }
            )
        return results
    finally:
        conn.close()


def delete_user_chat(user_id: int, session_id: str) -> bool:
    """Delete a user chat session."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM user_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


# Automatically initialize tables on import
init_db()
