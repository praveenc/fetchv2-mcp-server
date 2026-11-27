"""Tests for capability-gated confirmation prompts (form elicitation). No real network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

import httpx
import pytest
from mcp.client import Client
from mcp.types import (
    ClientCapabilities,
    ElicitationCapability,
    ElicitRequestParams,
    ElicitResult,
    FormElicitationCapability,
    TextContent,
    UrlElicitationCapability,
)

from fetchv2_mcp_server.server import form_elicitation_supported, mcp

PAGE_URL = "https://example.com/page"
LLMS_URL = "https://example.com/llms.txt"
LEGACY = "legacy"
MODERN = "2026-07-28"


def llms_txt(count: int) -> str:
    links = "\n".join(f"- [Page {i}](https://example.com/p{i}.md)" for i in range(count))
    return f"# Docs\n\n## Pages\n\n{links}\n"


def site(llms_links: int = 0):
    """robots.txt disallows everything; pages and llms.txt are served."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        if request.url.path == "/llms.txt":
            return httpx.Response(200, text=llms_txt(llms_links))
        return httpx.Response(200, text=f"content of {request.url.path}")

    return handler


def answering(action: Literal["accept", "decline", "cancel"], asked: list[str]):
    async def callback(context, params: ElicitRequestParams) -> ElicitResult:
        asked.append(params.message)
        return ElicitResult(action=action, content={} if action == "accept" else None)

    return callback


async def call(
    tool: str,
    args: dict,
    *,
    mode: str,
    action: Literal["accept", "decline", "cancel"] | None,
    asked: list[str],
):
    callback = answering(action, asked) if action else None
    async with Client(mcp, mode=mode, elicitation_callback=callback) as client:
        result = await client.call_tool(tool, args)
    assert isinstance(result.content[0], TextContent)
    return result, result.content[0].text


def page_requests(seen: list[httpx.Request]) -> list[str]:
    return [r.url.path for r in seen if r.url.path not in ("/robots.txt", "/llms.txt")]


class TestRobotsConfirmation:
    @pytest.mark.parametrize("mode", [LEGACY, MODERN])
    async def test_accept_fetches_page(self, mock_http, mode):
        seen = mock_http(site())
        asked: list[str] = []

        result, text = await call(
            "fetch", {"url": PAGE_URL}, mode=mode, action="accept", asked=asked
        )

        assert result.is_error is False
        assert len(asked) == 1
        assert "robots.txt disallows fetching this URL. Fetch anyway?" in asked[0]
        assert PAGE_URL in asked[0]
        assert "content of /page" in text
        assert page_requests(seen) == ["/page"]

    @pytest.mark.parametrize("mode", [LEGACY, MODERN])
    @pytest.mark.parametrize("action", ["decline", "cancel"])
    async def test_decline_or_cancel_does_not_fetch(self, mock_http, mode, action):
        seen = mock_http(site())
        asked: list[str] = []

        result, text = await call("fetch", {"url": PAGE_URL}, mode=mode, action=action, asked=asked)

        assert result.is_error is False
        assert len(asked) == 1
        assert f"Not fetched: {PAGE_URL}" in text
        assert "robots.txt disallows" in text
        assert page_requests(seen) == []

    @pytest.mark.parametrize("mode", [LEGACY, MODERN])
    async def test_unsupported_keeps_tool_error(self, mock_http, mode):
        seen = mock_http(site())

        result, text = await call("fetch", {"url": PAGE_URL}, mode=mode, action=None, asked=[])

        assert result.is_error is True
        assert "disallows fetching this URL" in text
        assert "fetch_manual prompt" in text
        assert page_requests(seen) == []

    async def test_ssrf_guard_is_never_prompted(self, mock_http):
        seen = mock_http(site())
        asked: list[str] = []

        result, text = await call(
            "fetch", {"url": "http://10.0.0.1/page"}, mode=MODERN, action="accept", asked=asked
        )

        assert result.is_error is True
        assert "Refusing to fetch" in text
        assert asked == []
        assert seen == []


class TestLlmsTxtConfirmation:
    @pytest.mark.parametrize("mode", [LEGACY, MODERN])
    async def test_accept_fetches_all_pages(self, mock_http, mode):
        seen = mock_http(site(llms_links=11))
        asked: list[str] = []

        _, text = await call(
            "fetch_llms_txt",
            {"url": LLMS_URL, "include_content": True},
            mode=mode,
            action="accept",
            asked=asked,
        )

        assert asked == ["This llms.txt lists 11 links. Fetch all 11 pages?"]
        assert "# Fetched Content" in text
        assert len(page_requests(seen)) == 11

    @pytest.mark.parametrize("mode", [LEGACY, MODERN])
    @pytest.mark.parametrize("action", ["decline", "cancel"])
    async def test_decline_returns_index_only(self, mock_http, mode, action):
        seen = mock_http(site(llms_links=11))

        result, text = await call(
            "fetch_llms_txt",
            {"url": LLMS_URL, "include_content": True},
            mode=mode,
            action=action,
            asked=[],
        )

        assert result.is_error is False
        assert "Found 11 documentation links." in text
        assert "fetch_batch" in text
        assert "# Fetched Content" not in text
        assert page_requests(seen) == []

    async def test_unsupported_fetches_all(self, mock_http):
        seen = mock_http(site(llms_links=11))

        _, text = await call(
            "fetch_llms_txt",
            {"url": LLMS_URL, "include_content": True},
            mode=MODERN,
            action=None,
            asked=[],
        )

        assert "# Fetched Content" in text
        assert len(page_requests(seen)) == 11

    async def test_ten_links_does_not_prompt(self, mock_http):
        seen = mock_http(site(llms_links=10))
        asked: list[str] = []

        _, text = await call(
            "fetch_llms_txt",
            {"url": LLMS_URL, "include_content": True},
            mode=MODERN,
            action="decline",
            asked=asked,
        )

        assert asked == []
        assert "# Fetched Content" in text
        assert len(page_requests(seen)) == 10


class TestCapabilityCheck:
    @pytest.mark.parametrize(
        ("elicitation", "expected"),
        [
            (None, False),
            (ElicitationCapability(), True),
            (ElicitationCapability(form=FormElicitationCapability()), True),
            (ElicitationCapability(url=UrlElicitationCapability()), False),
        ],
    )
    def test_form_capability(self, elicitation, expected):
        ctx = SimpleNamespace(
            protocol_version=MODERN,
            client_capabilities=ClientCapabilities(elicitation=elicitation),
        )

        assert form_elicitation_supported(ctx) is expected  # type: ignore[arg-type]

    def test_no_request_context(self):
        assert form_elicitation_supported(None) is False
        assert form_elicitation_supported(SimpleNamespace(protocol_version=None)) is False  # type: ignore[arg-type]
