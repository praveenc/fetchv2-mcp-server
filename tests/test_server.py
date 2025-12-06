"""Tests for the FetchV2 MCP server."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from fetchv2_mcp_server.server import (
    check_robots_txt,
    discover_links,
    fetch,
    fetch_and_extract,
    fetch_batch,
    fetch_llms_txt,
    get_robots_txt_url,
    is_markdown_url,
    parse_llms_txt,
)


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_robots_txt_url(self):
        """Test robots.txt URL generation."""
        assert (
            get_robots_txt_url("https://example.com/page")
            == "https://example.com/robots.txt"
        )
        assert (
            get_robots_txt_url("https://example.com:8080/path")
            == "https://example.com:8080/robots.txt"
        )
        assert (
            get_robots_txt_url("http://sub.example.com/a/b/c")
            == "http://sub.example.com/robots.txt"
        )

    def test_is_markdown_url(self):
        """Test markdown URL detection."""
        assert is_markdown_url("https://example.com/README.md") is True
        assert is_markdown_url("https://example.com/doc.markdown") is True
        assert is_markdown_url("https://example.com/page.mdx") is True
        assert is_markdown_url("https://example.com/page.html") is False
        assert is_markdown_url("https://example.com/page") is False
        # Case insensitive
        assert is_markdown_url("https://example.com/README.MD") is True


class TestRobotsTxt:
    """Tests for robots.txt handling."""

    @pytest.mark.asyncio
    async def test_robots_txt_timeout_allows_fetch(self):
        """When robots.txt times out, fetching should be allowed."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException("timeout")

        # Should not raise - timeout means allow
        await check_robots_txt("https://example.com/page", "TestBot", mock_client)

    @pytest.mark.asyncio
    async def test_robots_txt_connection_error_allows_fetch(self):
        """When robots.txt connection fails, fetching should be allowed."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.ConnectError("connection failed")

        # Should not raise
        await check_robots_txt("https://example.com/page", "TestBot", mock_client)

    @pytest.mark.asyncio
    async def test_robots_txt_404_allows_fetch(self):
        """When robots.txt returns 404, fetching should be allowed."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        # Should not raise - 404 means no robots.txt
        await check_robots_txt("https://example.com/page", "TestBot", mock_client)


class TestFetchAndExtract:
    """Tests for content fetching and extraction."""

    @pytest.mark.asyncio
    async def test_fetch_markdown_url_returns_raw(self):
        """Markdown URLs should return raw content without extraction."""
        mock_response = AsyncMock()
        mock_response.text = "# Hello World\n\nThis is markdown."
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            content, content_type = await fetch_and_extract(
                "https://example.com/README.md",
                "TestBot",
            )

            assert content == "# Hello World\n\nThis is markdown."
            assert content_type == "markdown (raw)"

    @pytest.mark.asyncio
    async def test_fetch_html_extracts_content(self):
        """HTML content should be extracted via Trafilatura."""
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>Navigation here</nav>
            <article>
                <h1>Main Content</h1>
                <p>This is the main article content that should be extracted.</p>
            </article>
            <footer>Footer content</footer>
        </body>
        </html>
        """
        mock_response = AsyncMock()
        mock_response.text = html_content
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            content, content_type = await fetch_and_extract(
                "https://example.com/page",
                "TestBot",
            )

            assert content_type == "markdown (extracted)"
            # Trafilatura should extract the main content
            assert "Main Content" in content or "article content" in content

    @pytest.mark.asyncio
    async def test_fetch_raw_mode_skips_extraction(self):
        """Raw mode should return content without extraction."""
        html_content = "<html><body><p>Raw HTML</p></body></html>"
        mock_response = AsyncMock()
        mock_response.text = html_content
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            content, content_type = await fetch_and_extract(
                "https://example.com/page",
                "TestBot",
                raw=True,
            )

            assert content == html_content
            assert "raw" in content_type


class TestFetchTool:
    """Tests for the fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_returns_content_with_header(self):
        """Fetch tool should return content with URL header."""
        with (
            patch("fetchv2_mcp_server.server.check_robots_txt", new_callable=AsyncMock),
            patch(
                "fetchv2_mcp_server.server.fetch_and_extract", new_callable=AsyncMock
            ) as mock_extract,
        ):
            mock_extract.return_value = (
                "Test content here",
                "markdown (extracted)",
            )

            result = await fetch(url="https://example.com/page")

            assert "# Content from https://example.com/page" in result
            assert "Test content here" in result
            assert "markdown (extracted)" in result

    @pytest.mark.asyncio
    async def test_fetch_pagination(self):
        """Fetch tool should support pagination via start_index."""
        long_content = "A" * 10000

        with (
            patch("fetchv2_mcp_server.server.check_robots_txt", new_callable=AsyncMock),
            patch(
                "fetchv2_mcp_server.server.fetch_and_extract", new_callable=AsyncMock
            ) as mock_extract,
        ):
            mock_extract.return_value = (long_content, "markdown (extracted)")

            result = await fetch(
                url="https://example.com/page",
                max_length=1000,
                start_index=0,
            )

            assert "Truncated" in result
            assert "start_index=1000" in result


class TestFetchBatchTool:
    """Tests for the fetch_batch tool."""

    @pytest.mark.asyncio
    async def test_fetch_batch_returns_combined_results(self):
        """Fetch batch should combine results from all URLs."""
        with patch(
            "fetchv2_mcp_server.server.fetch_and_extract", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.side_effect = [
                ("Content from page 1", "markdown (extracted)"),
                ("Content from page 2", "markdown (extracted)"),
            ]

            result = await fetch_batch(
                urls=["https://example.com/page1", "https://example.com/page2"],
            )

            assert "## https://example.com/page1" in result
            assert "## https://example.com/page2" in result
            assert "Content from page 1" in result
            assert "Content from page 2" in result

    @pytest.mark.asyncio
    async def test_fetch_batch_handles_errors_gracefully(self):
        """Fetch batch should handle individual URL errors gracefully."""
        from mcp.shared.exceptions import McpError
        from mcp.types import INTERNAL_ERROR, ErrorData

        with patch(
            "fetchv2_mcp_server.server.fetch_and_extract", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.side_effect = [
                ("Content from page 1", "markdown (extracted)"),
                McpError(ErrorData(code=INTERNAL_ERROR, message="Failed to fetch")),
            ]

            result = await fetch_batch(
                urls=["https://example.com/page1", "https://example.com/page2"],
            )

            assert "Content from page 1" in result
            assert "<error>" in result
            assert "Failed to fetch" in result


class TestDiscoverLinksTool:
    """Tests for the discover_links tool."""

    @pytest.mark.asyncio
    async def test_discover_links_finds_links(self):
        """Discover links should find all href links in HTML."""
        html_content = """
        <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="https://external.com/page">External</a>
        </body>
        </html>
        """
        mock_response = AsyncMock()
        mock_response.text = html_content
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await discover_links(url="https://example.com")

            assert "Found 3 links" in result
            assert "https://example.com/page1" in result
            assert "https://example.com/page2" in result
            assert "https://external.com/page" in result

    @pytest.mark.asyncio
    async def test_discover_links_with_filter(self):
        """Discover links should filter by regex pattern."""
        html_content = """
        <html>
        <body>
            <a href="/docs/intro">Docs Intro</a>
            <a href="/docs/guide">Docs Guide</a>
            <a href="/blog/post">Blog Post</a>
        </body>
        </html>
        """
        mock_response = AsyncMock()
        mock_response.text = html_content
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await discover_links(
                url="https://example.com", filter_pattern="/docs/"
            )

            assert "Found 2 links" in result
            assert "/docs/intro" in result
            assert "/docs/guide" in result
            assert "/blog/" not in result


class TestParseLLMSTxt:
    """Tests for parse_llms_txt helper function."""

    def test_parse_llms_txt_basic(self):
        """Parse basic llms.txt format with sections and links."""
        content = (
            "# My Project\n\n"
            "## Docs\n\n"
            "- [Getting Started](https://example.com/start.md): How to begin\n"
            "- [API Reference](https://example.com/api.md): API docs\n\n"
            "## Examples\n\n"
            "- [Demo](https://example.com/demo.md): A demo\n"
        )
        result = parse_llms_txt(content)

        assert result["title"] == "My Project"
        assert "Docs" in result["sections"]
        assert len(result["sections"]["Docs"]) == 2
        assert result["sections"]["Docs"][0]["title"] == "Getting Started"
        assert result["sections"]["Docs"][0]["url"] == "https://example.com/start.md"
        assert result["sections"]["Docs"][0]["desc"] == "How to begin"
        assert "Examples" in result["sections"]
        assert len(result["sections"]["Examples"]) == 1

    def test_parse_llms_txt_no_summary(self):
        """Parse llms.txt without summary."""
        content = (
            "# Project Name\n\n" "## Docs\n\n" "- [Page](https://example.com/page.md)\n"
        )
        result = parse_llms_txt(content)

        assert result["title"] == "Project Name"
        assert result["summary"] == ""
        assert "Docs" in result["sections"]


class TestFetchLLMSTxtTool:
    """Tests for the fetch_llms_txt tool."""

    @pytest.mark.asyncio
    async def test_fetch_llms_txt_parses_structure(self):
        """Fetch llms.txt should parse and return structure."""
        llms_content = (
            "# Test Project\n\n"
            "> Project description\n\n"
            "## Documentation\n\n"
            "- [Guide](https://example.com/guide.md): The guide\n"
            "- [API](https://example.com/api.md): API reference\n"
        )
        mock_response = AsyncMock()
        mock_response.text = llms_content
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_llms_txt(url="https://example.com/llms.txt")

            assert "# Test Project" in result
            assert "Project description" in result
            assert "## Documentation" in result
            assert "[Guide](https://example.com/guide.md)" in result
            assert "Found 2 documentation links" in result

    @pytest.mark.asyncio
    async def test_fetch_llms_txt_resolves_relative_urls(self):
        """Fetch llms.txt should resolve relative URLs to absolute URLs."""
        # Simulating Raycast-style llms.txt with relative paths
        llms_content = (
            "# Raycast API\n\n"
            "## Docs\n\n"
            "- [Introduction](/readme.md): Start building\n"
            "- [Getting Started](/basics/getting-started.md): Prerequisites\n"
        )
        mock_response = AsyncMock()
        mock_response.text = llms_content
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_llms_txt(url="https://developers.raycast.com/llms.txt")

            # Relative URLs should be resolved to absolute
            assert "https://developers.raycast.com/readme.md" in result
            assert "https://developers.raycast.com/basics/getting-started.md" in result
            # Original relative paths should NOT appear
            assert "](/readme.md)" not in result
