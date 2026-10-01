"""
Pytest configuration for SURU AI test suite.
Ensures unit and integration tests run deterministically with MockProvider
unless a test explicitly configures or patches live/mocked Gemini.
"""

import os
import pytest
from backend.config import settings, Settings

@pytest.fixture(autouse=True)
def default_test_environment(monkeypatch):
    """Default all automated tests to mock provider unless overridden."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    Settings.reload()
    yield
    Settings.reload()
