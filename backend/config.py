"""NEXUS Backend Configuration — loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Also try the backend directory itself
    load_dotenv()


class Settings:
    """Application settings sourced from environment variables."""

    # LLM Provider
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Speech
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Server
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    # Session
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
    MAX_SESSIONS: int = int(os.getenv("MAX_SESSIONS", "100"))

    # Redis (optional)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    @property
    def use_redis(self) -> bool:
        return bool(self.REDIS_URL)


settings = Settings()
