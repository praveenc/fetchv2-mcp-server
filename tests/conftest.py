"""Pytest configuration for fetchv2-mcp-server tests."""

from collections.abc import Callable

import httpx
import pytest

from fetchv2_mcp_server import server

PUBLIC_IP = "93.184.215.14"


@pytest.fixture(autouse=True)
def _reset_logging():
    """Reset logging configuration between tests."""
    import logging

    logging.getLogger("fetchv2-mcp-server").handlers.clear()


@pytest.fixture(autouse=True)
def fake_resolver(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Resolve every hostname to a public IP, with per-host overrides. No real DNS."""
    overrides: dict[str, list[str]] = {}

    async def _resolve(host: str, port: int) -> list[str]:
        return overrides.get(host, [PUBLIC_IP])

    monkeypatch.setattr(server, "resolve_host", _resolve)
    monkeypatch.delenv(server.ALLOW_PRIVATE_NETWORKS_ENV, raising=False)
    return overrides


@pytest.fixture
def mock_http(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Callable[[httpx.Request], httpx.Response]], list[httpx.Request]]:
    """
    Route the server's HTTP clients through an httpx.MockTransport.

    The real SSRF guard hook stays active. Returns the list of requests that
    reached the transport.
    """
    real_new_client = server.new_client

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def _record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        transport = httpx.MockTransport(_record)
        monkeypatch.setattr(
            server, "new_client", lambda **kw: real_new_client(transport=transport, **kw)
        )
        return seen

    return install
