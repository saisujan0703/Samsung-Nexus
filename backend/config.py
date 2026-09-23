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

    SUPPORTED_LLM_PROVIDERS = {"mock", "gemini", "google_gemini"}

    # LLM Provider
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

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

    @classmethod
    def normalize_provider_name(cls, provider_name: str | None) -> str:
        """Normalize provider names coming from config or user input."""
        if provider_name is None:
            return "mock"
        normalized = provider_name.strip().lower().replace("-", "_")
        if normalized in {"google", "google_gemini"}:
            return "google_gemini"
        return normalized

    @classmethod
    def validate_provider_config(
        cls,
        provider_name: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, str | bool]:
        """Validate provider configuration and return sanitized runtime settings."""
        provider = cls.normalize_provider_name(provider_name or os.getenv("LLM_PROVIDER", "mock"))
        if provider not in cls.SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"Unsupported LLM provider: {provider!r}. Supported values: {', '.join(sorted(cls.SUPPORTED_LLM_PROVIDERS))}."
            )

        if provider in {"gemini", "google_gemini"}:
            if not (api_key or "").strip():
                raise ValueError("Missing required configuration: GOOGLE_API_KEY must be set when LLM_PROVIDER is 'gemini'.")
            if not (model_name or "").strip():
                raise ValueError("Missing required configuration: GEMINI_MODEL must be set to a non-empty model name.")

        return {
            "provider": provider,
            "api_key_present": bool((api_key or "").strip()),
            "model": (model_name or "gemini-1.5-flash").strip() or "gemini-1.5-flash",
        }

    @property
    def use_redis(self) -> bool:
        return bool(self.REDIS_URL)


settings = Settings()
