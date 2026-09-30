"""
SURU AI Backend — FastAPI REST and WebSocket API Server.

Connects client applications to the real-time interruptible agent orchestrator.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.memory.session_memory import session_memory
from backend.realtime.session import realtime_manager
import backend.db as db


app = FastAPI(
    title="SURU AI: Interruptible Real-Time Agent API",
    description="Backend engine for interruptible multimodal AI agents",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)
    display_name: str = Field(default="")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class SaveChatRequest(BaseModel):
    session_id: str
    title: str = "New Conversation"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    sports_fixtures: Optional[dict[str, Any]] = None
    goal_summary: Optional[str] = ""


RegisterRequest.model_rebuild()
LoginRequest.model_rebuild()
SaveChatRequest.model_rebuild()


class CreateSessionResponse(BaseModel):
    session_id: str
    message: str



class UserInputRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ImageUploadRequest(BaseModel):
    image_data: str
    prompt: str = "Analyze this image and integrate relevant information into the current plan."


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "nexus-backend", "version": "1.0.0"}


@app.post("/api/auth/register")
async def register_user(req: RegisterRequest) -> dict[str, Any]:
    """Register a new user account."""
    try:
        user = db.create_user(req.email, req.password, req.display_name)
        return {"status": "ok", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to register user")


@app.post("/api/auth/login")
async def login_user(req: LoginRequest) -> dict[str, Any]:
    """Authenticate and log in an existing user."""
    user = db.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"status": "ok", "user": user}


@app.get("/api/user/{user_id}/chats")
async def list_user_chats(user_id: int) -> dict[str, Any]:
    """Get all saved chat sessions for the user from persistent database."""
    chats = db.get_user_chats(user_id)
    return {"status": "ok", "chats": chats}


@app.post("/api/user/{user_id}/chats")
async def save_user_chat_endpoint(user_id: int, req: SaveChatRequest) -> dict[str, Any]:
    """Persist or update chat session for user."""
    saved = db.save_user_chat(
        user_id=user_id,
        session_id=req.session_id,
        title=req.title,
        messages=req.messages,
        sports_fixtures=req.sports_fixtures,
        goal_summary=req.goal_summary or "",
    )
    return {"status": "ok", "chat": saved}


@app.delete("/api/user/{user_id}/chats/{session_id}")
async def delete_user_chat_endpoint(user_id: int, session_id: str) -> dict[str, Any]:
    """Delete a saved chat session for user."""
    deleted = db.delete_user_chat(user_id, session_id)
    return {"status": "ok", "deleted": deleted}


@app.post("/api/session", response_model=CreateSessionResponse)
async def create_session() -> CreateSessionResponse:
    """Create a new agent session."""
    session_id = str(uuid.uuid4())[:8]
    await session_memory.get_or_create(session_id)
    return CreateSessionResponse(session_id=session_id, message="Session initialized successfully")


@app.get("/api/session/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get complete snapshot of session state."""
    orchestrator, _ = await session_memory.get(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")
    return orchestrator.get_snapshot()


@app.get("/api/session/{session_id}/tasks")
async def get_tasks(session_id: str) -> dict[str, Any]:
    """Get current TaskGraph state."""
    orchestrator, _ = await session_memory.get(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")
    return orchestrator.task_graph.to_dict()


@app.get("/api/session/{session_id}/context")
async def get_context(session_id: str) -> dict[str, Any]:
    """Get active session context."""
    orchestrator, _ = await session_memory.get(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")
    return orchestrator.context_manager.to_dict()


@app.post("/api/session/{session_id}/input")
async def post_user_input(session_id: str, request: UserInputRequest) -> dict[str, Any]:
    """Submit user input to the agent (can be initial goal or live interruption)."""
    orchestrator, _, _ = await session_memory.get_or_create(session_id)
    result = await orchestrator.handle_user_input(request.text)
    return result


@app.post("/api/session/{session_id}/image")
async def post_image(session_id: str, request: ImageUploadRequest) -> dict[str, Any]:
    """Submit image to the agent."""
    orchestrator, _, _ = await session_memory.get_or_create(session_id)
    result = await orchestrator.handle_image_upload(request.image_data, request.prompt)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Image processing error"))
    return result


@app.get("/api/session/{session_id}/snapshot")
async def get_session_snapshot(session_id: str) -> dict[str, Any]:
    """Canonical serializable snapshot of agent state for evaluation."""
    orchestrator, _ = await session_memory.get(session_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Session not found")
    return orchestrator.get_snapshot()


@app.get("/api/session/{session_id}/events")
async def get_session_events(session_id: str, limit: int = 100) -> dict[str, Any]:
    """Retrieve recorded event bus log for evaluation."""
    orchestrator, event_bus = await session_memory.get(session_id)
    if not orchestrator or not event_bus:
        raise HTTPException(status_code=404, detail="Session not found")
    events = event_bus.get_events(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "count": len(events),
        "events": [e.model_dump() for e in events],
    }


@app.post("/api/evaluate/{scenario_id}")
async def run_evaluation_scenario(scenario_id: str) -> dict[str, Any]:
    """Run evaluation scenario harness and return structured metrics."""
    from backend.evaluation.harness import evaluation_harness
    if scenario_id.lower() == "all":
        results = await evaluation_harness.run_all()
        return {"scenarios": [r.model_dump() for r in results]}
    else:
        result = await evaluation_harness.run_scenario(scenario_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
        return result.model_dump()


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Real-time duplex connection.
    - Streams all agent events (tasks, replanning, streaming tokens) to client
    - Receives user inputs, interruptions, and audio/image events from client
    """
    orchestrator, _ = await realtime_manager.connect(session_id, websocket)

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except Exception:
                # Handle malformed / non-JSON websocket messages gracefully
                await websocket.send_json({"type": "error", "error": "Invalid JSON frame"})
                continue

            if not isinstance(data, dict):
                await websocket.send_json({"type": "error", "error": "JSON payload must be an object"})
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "user_input":
                text = data.get("text", "")
                if text and isinstance(text, str):
                    import asyncio
                    asyncio.create_task(orchestrator.handle_user_input(text))
                else:
                    await websocket.send_json({"type": "warning", "message": "Empty user_input ignored"})

            elif msg_type == "image_upload":
                image_data = data.get("image_data", "")
                prompt = data.get("prompt", "")
                if image_data:
                    import asyncio
                    asyncio.create_task(orchestrator.handle_image_upload(image_data, prompt))
                else:
                    await websocket.send_json({"type": "warning", "message": "Empty image_upload ignored"})

            elif msg_type == "speech_started":
                import asyncio
                asyncio.create_task(orchestrator.handle_speech_started())

            else:
                # Safely ignore unknown event types without dropping connection
                await websocket.send_json({"type": "ack", "received": msg_type, "status": "ignored"})

    except WebSocketDisconnect:
        await realtime_manager.disconnect(session_id, websocket)
    except Exception as e:
        await realtime_manager.disconnect(session_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
