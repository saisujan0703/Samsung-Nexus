"""
Unit tests for GeminiProvider and Provider Factory.
"""

import importlib

import pytest

import backend.config as config_module
import backend.providers.base as provider_base_module
from backend.providers.base import create_provider, Message
from backend.providers.google_gemini import GeminiProvider


def reload_provider_modules():
    """Reload config and provider modules to respect env-based configuration in tests."""
    importlib.reload(config_module)
    importlib.reload(provider_base_module)
    return config_module, provider_base_module


def test_valid_provider_configuration(monkeypatch):
    """Valid runtime config should produce a configured Gemini provider."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    config_module, provider_base_module = reload_provider_modules()

    provider = provider_base_module.create_provider(config_module.settings.LLM_PROVIDER)
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"
    assert provider.model == "gemini-3.8-flash"


def test_missing_provider_configuration_raises(monkeypatch):
    """Missing API keys should be rejected before provider instantiation."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    config_module, provider_base_module = reload_provider_modules()
    monkeypatch.setattr(config_module.Settings, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "GOOGLE_API_KEY", "")

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        provider_base_module.create_provider(config_module.settings.LLM_PROVIDER)


def test_invalid_provider_configuration_raises(monkeypatch):
    """Unsupported provider names should fail fast without silent fallback."""
    monkeypatch.setenv("LLM_PROVIDER", "unsupported_provider")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    config_module, provider_base_module = reload_provider_modules()

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        provider_base_module.create_provider(config_module.settings.LLM_PROVIDER)


def test_provider_model_configuration_uses_env(monkeypatch):
    """The configured Gemini model should come from environment settings."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    config_module, provider_base_module = reload_provider_modules()

    provider = provider_base_module.create_provider(config_module.settings.LLM_PROVIDER)
    assert provider.model == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_gemini_fallback_when_unconfigured():
    """Verify GeminiProvider falls back to mock provider gracefully when no key is set."""
    provider = GeminiProvider(api_key="", fallback_to_mock=True)
    assert not provider.is_configured

    # Test classification fallback
    res = await provider.classify(
        text="Wait, my parents are coming",
        categories=["BACKCHANNEL", "CONSTRAINT_CHANGE", "QUESTION"],
    )
    assert res.category == "CONSTRAINT_CHANGE"
    assert "parents" in res.details.get("reason", "") or res.confidence > 0.5

    # Test planning fallback
    plan = await provider.create_plan(
        goal="Plan a 3-day Chennai trip for 15000",
        constraints={"city": "chennai", "budget": 15000},
    )
    assert len(plan.tasks) > 0

    # Test generation fallback
    text = await provider.generate([Message(role="user", content="hello")])
    assert len(text) > 0


@pytest.mark.asyncio
async def test_gemini_raises_when_fallback_disabled():
    """Verify GeminiProvider raises ValueError if key is missing and fallback is disabled."""
    provider = GeminiProvider(api_key="", fallback_to_mock=False)
    assert not provider.is_configured

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        await provider.generate([Message(role="user", content="hello")])


async def mock_sleep(seconds):
    pass


@pytest.mark.asyncio
async def test_gemini_retry_503_success(monkeypatch):
    """Verify GeminiProvider retries 503 and succeeds on subsequent attempt."""
    monkeypatch.setattr("asyncio.sleep", mock_sleep)
    call_count = 0

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.text = str(json_data)

        def json(self):
            return self._json

    async def mock_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockResponse(503, {"error": {"message": "High demand"}})
        return MockResponse(200, {"candidates": [{"content": {"parts": [{"text": "Success after 503"}]}}]})

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    result = await provider.generate([Message(role="user", content="Test")])
    assert call_count == 2
    assert result == "Success after 503"


@pytest.mark.asyncio
async def test_gemini_retry_429_success(monkeypatch):
    """Verify GeminiProvider retries 429 rate limit error and succeeds on retry."""
    monkeypatch.setattr("asyncio.sleep", mock_sleep)
    call_count = 0

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.text = str(json_data)

        def json(self):
            return self._json

    async def mock_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockResponse(429, {"error": {"message": "Rate limited"}})
        return MockResponse(200, {"candidates": [{"content": {"parts": [{"text": "Success after 429"}]}}]})

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    result = await provider.generate([Message(role="user", content="Test")])
    assert call_count == 2
    assert result == "Success after 429"


@pytest.mark.asyncio
async def test_gemini_all_attempts_503_fallback(monkeypatch):
    """Verify GeminiProvider retries up to 3 times on 503 before raising or falling back."""
    monkeypatch.setattr("asyncio.sleep", mock_sleep)
    call_count = 0

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.text = str(json_data)

        def json(self):
            return self._json

    async def mock_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        return MockResponse(503, {"error": {"message": "High demand"}})

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash", fallback_to_mock=False)
    with pytest.raises(RuntimeError, match="status 503"):
        await provider.generate([Message(role="user", content="Test")])
    assert call_count == 3


@pytest.mark.asyncio
async def test_gemini_400_no_retry(monkeypatch):
    """Verify permanent 400 Bad Request does not retry and fails immediately on attempt 1."""
    monkeypatch.setattr("asyncio.sleep", mock_sleep)
    call_count = 0

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.text = str(json_data)

        def json(self):
            return self._json

    async def mock_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        return MockResponse(400, {"error": {"message": "Bad Request"}})

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash", fallback_to_mock=False)
    with pytest.raises(RuntimeError, match="status 400"):
        await provider.generate([Message(role="user", content="Test")])
    assert call_count == 1


@pytest.mark.asyncio
async def test_fallback_message_does_not_falsely_claim_missing_key(monkeypatch):
    """Verify MockProvider fallback message does not claim API key is missing when configured."""
    monkeypatch.setenv("GOOGLE_API_KEY", "real-test-key")
    config_module, provider_base_module = reload_provider_modules()

    mock_provider = provider_base_module.MockProvider()
    response = await mock_provider.generate_response([], goal="Explain array vs arraylist")

    assert "set GOOGLE_API_KEY in .env" not in response
    assert "high demand or unavailability" in response or "offline fallback mode" in response

