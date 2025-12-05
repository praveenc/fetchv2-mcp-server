"""Pytest configuration for fetchv2-mcp-server tests."""

import pytest


@pytest.fixture(autouse=True)
def _reset_logging():
    """Reset logging configuration between tests."""
    import logging

    logging.getLogger("fetchv2-mcp-server").handlers.clear()
