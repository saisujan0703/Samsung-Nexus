"""
Unit tests for GeminiProvider and Provider Factory.
"""

import pytest
from backend.providers.base import create_provider, Message
from backend.providers.google_gemini import GeminiProvider


def test_gemini_provider_factory():
    """Verify create_provider returns GeminiProvider when requested."""
    provider = create_provider("gemini")
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"


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
