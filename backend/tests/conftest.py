"""Configuration for tests."""

import pytest


@pytest.fixture
def anyio_backend():
    """Returns the asyncio backend for anyio."""
    return "asyncio"
