"""NEXUS Backend Configuration — loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_path = _PROJECT_ROOT / ".env"
def reload_env() -> None:
    """Reload environment variables from .env without overriding explicitly set env vars."""
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
    else:
        load_dotenv(override=False)


class Settings:
    """Application settings sourced dynamically from environment variables."""

    SUPPORTED_LLM_PROVIDERS = {"mock", "gemini", "google_gemini"}

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
    MAX_SESSIONS: int = int(os.getenv("MAX_SESSIONS", "100"))
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    @classmethod
    def reload(cls) -> None:
        """Force reload .env and refresh environment."""
        reload_env()
        cls.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
        cls.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        cls.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        cls.DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
        cls.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
        cls.BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
        cls.BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
        cls.FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        cls.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        cls.SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
        cls.MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "100"))
        cls.REDIS_URL = os.getenv("REDIS_URL", "")

    @property
    def llm_provider(self) -> str:
        return self.LLM_PROVIDER

    @property
    def google_api_key(self) -> str:
        return self.GOOGLE_API_KEY

    @property
    def gemini_model(self) -> str:
        return self.GEMINI_MODEL

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
        provider = cls.normalize_provider_name(provider_name or cls.LLM_PROVIDER)
        if provider not in cls.SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"Unsupported LLM provider: {provider!r}. Supported values: {', '.join(sorted(cls.SUPPORTED_LLM_PROVIDERS))}."
            )

        if provider in {"gemini", "google_gemini"}:
            resolved_key = (api_key if api_key is not None else cls.GOOGLE_API_KEY or "").strip()
            if not resolved_key:
                raise ValueError("Missing required configuration: GOOGLE_API_KEY must be set when LLM_PROVIDER is 'gemini'.")
            resolved_model = (model_name if model_name is not None else cls.GEMINI_MODEL or "").strip()
            if not resolved_model:
                raise ValueError("Missing required configuration: GEMINI_MODEL must be set to a non-empty model name.")

        return {
            "provider": provider,
            "api_key_present": bool((api_key if api_key is not None else cls.GOOGLE_API_KEY or "").strip()),
            "model": (model_name if model_name is not None else cls.GEMINI_MODEL or "gemini-3.8-flash").strip() or "gemini-3.8-flash",
        }

    @property
    def use_redis(self) -> bool:
        return bool(self.REDIS_URL)


reload_env()
Settings.reload()
settings = Settings()

