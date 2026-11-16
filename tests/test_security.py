"""Tests for the SSRF guard and the response size cap. No real network."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from fetchv2_mcp_server import server
from fetchv2_mcp_server.server import discover_links, fetch, fetch_batch


def ok(request: httpx.Request) -> httpx.Response:
    """Return a small HTML page for any request."""
    return httpx.Response(200, text="<html><body><p>hello</p></body></html>")


class TestSSRFGuard:
    """The guard refuses non-public hosts on every request and redirect hop."""

    @pytest.mark.asyncio
    async def test_loopback_ip_is_refused(self, mock_http):
        seen = mock_http(ok)

        with pytest.raises(ToolError, match="non-public address 127.0.0.1"):
            await fetch(url="http://127.0.0.1/")

        assert seen == []

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost/",
            "http://LOCALHOST./admin",
            "http://api.localhost/",
            "http://[::1]/",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/",
            "http://172.16.0.1/",
            "http://192.168.1.1/",
            "http://0.0.0.0/",
            "http://100.64.0.1/",
            "http://224.0.0.1/",
            "http://[::ffff:127.0.0.1]/",
            "http://[::ffff:a9fe:a9fe]/",
            "http://[fd00::1]/",
            "http://[fe80::1]/",
            "http://[::]/",
        ],
    )
    @pytest.mark.asyncio
    async def test_non_public_urls_are_refused(self, mock_http, url):
        seen = mock_http(ok)

        with pytest.raises(ToolError, match="Refusing to fetch"):
            await fetch(url=url, bypass_robots_txt=True)

        assert seen == []

    @pytest.mark.asyncio
    async def test_hostname_resolving_to_private_ip_is_refused(self, mock_http, fake_resolver):
        fake_resolver["intranet.example.com"] = ["10.1.2.3"]
        seen = mock_http(ok)

        with pytest.raises(ToolError, match="non-public address 10.1.2.3"):
            await fetch(url="https://intranet.example.com/", bypass_robots_txt=True)

        assert seen == []

    @pytest.mark.asyncio
    async def test_any_private_address_in_resolution_is_refused(self, mock_http, fake_resolver):
        fake_resolver["mixed.example.com"] = ["93.184.215.14", "127.0.0.1"]
        mock_http(ok)

        with pytest.raises(ToolError, match="non-public address 127.0.0.1"):
            await fetch(url="https://mixed.example.com/", bypass_robots_txt=True)

    @pytest.mark.asyncio
    async def test_redirect_to_loopback_is_refused(self, mock_http):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "public.example.com":
                return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
            return httpx.Response(200, text="internal secret")

        seen = mock_http(handler)

        with pytest.raises(ToolError, match="non-public address 127.0.0.1"):
            await fetch(url="https://public.example.com/", bypass_robots_txt=True)

        assert [r.url.host for r in seen] == ["public.example.com"]

    @pytest.mark.asyncio
    async def test_robots_txt_check_is_guarded(self, mock_http):
        seen = mock_http(ok)

        with pytest.raises(ToolError, match="Refusing to fetch http://10.0.0.1/robots.txt"):
            await fetch(url="http://10.0.0.1/page")

        assert seen == []

    @pytest.mark.asyncio
    async def test_fetch_batch_reports_blocked_url_inline(self, mock_http):
        mock_http(ok)

        result = await fetch_batch(urls=["https://example.com/", "http://127.0.0.1/"])

        assert "hello" in result
        assert "<error>Refusing to fetch http://127.0.0.1/" in result

    @pytest.mark.asyncio
    async def test_discover_links_is_guarded(self, mock_http):
        mock_http(ok)

        with pytest.raises(ToolError, match="Refusing to fetch"):
            await discover_links(url="http://192.168.0.1/")

    @pytest.mark.asyncio
    async def test_public_url_passes(self, mock_http):
        seen = mock_http(ok)

        result = await fetch(url="https://example.com/page", bypass_robots_txt=True)

        assert "hello" in result
        assert [str(r.url) for r in seen] == ["https://example.com/page"]

    @pytest.mark.asyncio
    async def test_unresolvable_host_is_refused(self, mock_http, monkeypatch):
        async def fail(host: str, port: int) -> list[str]:
            raise OSError("name not known")

        monkeypatch.setattr(server, "resolve_host", fail)
        mock_http(ok)

        with pytest.raises(ToolError, match="cannot resolve"):
            await fetch(url="https://nowhere.invalid/", bypass_robots_txt=True)

    @pytest.mark.parametrize("value", ["1", "true", "YES"])
    @pytest.mark.asyncio
    async def test_opt_in_env_var_allows_loopback(self, mock_http, monkeypatch, value):
        monkeypatch.setenv(server.ALLOW_PRIVATE_NETWORKS_ENV, value)
        mock_http(ok)

        result = await fetch(url="http://127.0.0.1:8000/", bypass_robots_txt=True)

        assert "hello" in result

    @pytest.mark.asyncio
    async def test_other_env_values_keep_guard_on(self, mock_http, monkeypatch):
        monkeypatch.setenv(server.ALLOW_PRIVATE_NETWORKS_ENV, "0")
        mock_http(ok)

        with pytest.raises(ToolError, match="Refusing to fetch"):
            await fetch(url="http://127.0.0.1/", bypass_robots_txt=True)


class TestResponseSizeCap:
    """Bodies over MAX_RESPONSE_BYTES are cut while streaming or refused up front."""

    @pytest.mark.asyncio
    async def test_body_over_cap_is_truncated_and_flagged(self, mock_http, monkeypatch):
        monkeypatch.setattr(server, "MAX_RESPONSE_BYTES", 1000)

        async def body() -> AsyncIterator[bytes]:
            for _ in range(10):
                yield b"a" * 600

        # An async stream has no Content-Length, so only the byte count can stop it
        mock_http(
            lambda request: httpx.Response(
                200, content=body(), headers={"content-type": "text/plain"}
            )
        )

        content, _ = await server.fetch_and_extract("https://example.com/big.txt", "TestBot")

        assert content.startswith("a" * 1000)
        assert "a" * 1001 not in content
        assert "Truncated: response body exceeded 1000 bytes" in content

    @pytest.mark.asyncio
    async def test_body_under_cap_is_not_flagged(self, mock_http):
        mock_http(lambda request: httpx.Response(200, text="small"))

        content, _ = await server.fetch_and_extract("https://example.com/a.txt", "TestBot")

        assert content == "small"

    @pytest.mark.asyncio
    async def test_content_length_over_cap_is_refused(self, mock_http):
        too_big = str(server.MAX_RESPONSE_BYTES + 1)
        mock_http(
            lambda request: httpx.Response(200, headers={"content-length": too_big}, content=b"")
        )

        with pytest.raises(ToolError, match="over the .* byte limit"):
            await fetch(url="https://example.com/huge", bypass_robots_txt=True)
