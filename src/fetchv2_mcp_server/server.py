"""
FetchV2 MCP Server - A robust web content fetcher using Trafilatura.

This server provides tools for fetching and extracting web content optimized for AI agents.
It combines the best practices from the MCP fetch server with Trafilatura's superior
content extraction capabilities.
"""

from __future__ import annotations

import hashlib
import itertools
import logging
import re
from copy import deepcopy
from typing import Annotated
from urllib.parse import urlparse, urlunparse

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData
from protego import Protego
from pydantic import AnyUrl, BaseModel, Field
from trafilatura import extract
from trafilatura.settings import DEFAULT_CONFIG

# Configure logging to stderr (critical for stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fetchv2-mcp-server")

# User agents for different request contexts
DEFAULT_USER_AGENT_AUTONOMOUS = (
    "FetchV2-MCP/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
)
DEFAULT_USER_AGENT_MANUAL = (
    "FetchV2-MCP/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"
)

# URL patterns that serve raw markdown content (no extraction needed)
MARKDOWN_URL_SUFFIXES = (".md", ".markdown", ".mdx")

# Default extraction settings
DEFAULT_MAX_LENGTH = 5000
DEFAULT_TIMEOUT = 30


def get_trafilatura_config():
    """Configure trafilatura settings for optimal extraction."""
    config = deepcopy(DEFAULT_CONFIG)
    config["DEFAULT"]["DOWNLOAD_TIMEOUT"] = "30"
    config["DEFAULT"]["SLEEP_TIME"] = "0"  # We handle rate limiting externally
    config["DEFAULT"]["MIN_FILE_SIZE"] = "10"
    config["DEFAULT"]["EXTRACTION_TIMEOUT"] = "30"
    config["DEFAULT"]["EXTENSIVE_DATE_SEARCH"] = "off"
    config["DEFAULT"]["TARGET_LANGUAGE"] = "en"
    return config


# Initialize trafilatura config once
TRAFILATURA_CONFIG = get_trafilatura_config()


def get_robots_txt_url(url: str) -> str:
    """Get the robots.txt URL for a given website URL."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


def is_markdown_url(url: str) -> bool:
    """Check if URL points to a raw markdown file."""
    parsed = urlparse(url)
    return parsed.path.lower().endswith(MARKDOWN_URL_SUFFIXES)


def sanitize_for_filename(text: str) -> str:
    """Sanitize text for use in filenames."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def generate_url_hash(url: str) -> str:
    """Generate a short hash for URL uniqueness."""
    return hashlib.md5(url.encode()).hexdigest()[:8]  # noqa: S324


async def check_robots_txt(
    url: str,
    user_agent: str,
    client: httpx.AsyncClient,
) -> None:
    """
    Check if the URL can be fetched according to robots.txt.
    Raises McpError if fetching is explicitly not allowed.
    If robots.txt is unavailable or times out, we allow fetching.
    """
    robots_url = get_robots_txt_url(url)

    try:
        response = await client.get(
            robots_url,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
            timeout=5.0,  # Short timeout for robots.txt
        )
    except (httpx.TimeoutException, httpx.ConnectError):
        # If robots.txt times out or connection fails, allow fetching
        logger.debug(f"robots.txt unavailable at {robots_url}, allowing fetch")
        return
    except httpx.HTTPError as e:
        # For other HTTP errors, log and allow
        logger.debug(f"Error fetching robots.txt: {e}, allowing fetch")
        return

    # If robots.txt returns 4xx client error (except 401/403), assume allowed
    if response.status_code in (401, 403):
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=(
                    f"robots.txt at {robots_url} returned {response.status_code}. "
                    "Autonomous fetching may not be allowed. "
                    "Try using the fetch_manual prompt instead."
                ),
            ),
        )
    if 400 <= response.status_code < 500:
        return  # No robots.txt, assume allowed

    # Parse robots.txt
    robot_txt = response.text
    processed = "\n".join(
        line for line in robot_txt.splitlines() if not line.strip().startswith("#")
    )
    robot_parser = Protego.parse(processed)

    if not robot_parser.can_fetch(url, user_agent):
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=(
                    f"robots.txt at {robots_url} disallows fetching this URL.\n"
                    f"User-Agent: {user_agent}\n"
                    f"URL: {url}\n"
                    "The user can try manually fetching using the fetch_manual prompt."
                ),
            ),
        )


async def fetch_and_extract(
    url: str,
    user_agent: str,
    *,
    raw: bool = False,
    include_metadata: bool = True,
    include_tables: bool = True,
    include_links: bool = False,
    include_images: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[str, str]:
    """
    Fetch URL and extract content using Trafilatura.

    Returns:
        Tuple of (content, content_type_info)

    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Timeout fetching {url}"),
            )
        except httpx.HTTPStatusError as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"HTTP {e.response.status_code} fetching {url}",
                ),
            )
        except httpx.HTTPError as e:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"),
            )

        page_content = response.text
        content_type = response.headers.get("content-type", "")

    if not page_content:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Empty response from {url}"),
        )

    # Check if URL serves raw markdown - return directly
    if is_markdown_url(url):
        return page_content, "markdown (raw)"

    # Check if content is HTML
    is_html = "<html" in page_content[:500].lower() or "text/html" in content_type

    if raw or not is_html:
        return page_content, f"raw ({content_type or 'unknown'})"

    # Use Trafilatura for HTML content extraction
    extracted = extract(
        page_content,
        include_comments=False,
        include_tables=include_tables,
        include_links=include_links,
        include_images=include_images,
        output_format="markdown",
        with_metadata=include_metadata,
        config=TRAFILATURA_CONFIG,
    )

    if not extracted:
        # Fallback: return raw content with a note
        return (
            f"<!-- Extraction failed, returning raw HTML -->\n{page_content}",
            "html (extraction failed)",
        )

    return extracted, "markdown (extracted)"


# Initialize FastMCP server
mcp = FastMCP(
    "fetchv2-mcp-server",
    dependencies=["httpx", "trafilatura", "protego", "defusedxml"],
)


class FetchParams(BaseModel):
    """Parameters for the fetch tool."""

    url: Annotated[AnyUrl, Field(description="URL to fetch")]
    max_length: Annotated[
        int,
        Field(
            default=DEFAULT_MAX_LENGTH,
            description="Maximum number of characters to return",
            gt=0,
            lt=1000000,
        ),
    ] = DEFAULT_MAX_LENGTH
    start_index: Annotated[
        int,
        Field(
            default=0,
            description="Start content from this character index (for pagination)",
            ge=0,
        ),
    ] = 0
    raw: Annotated[
        bool,
        Field(
            default=False,
            description="Get raw content without markdown extraction",
        ),
    ] = False
    include_metadata: Annotated[
        bool,
        Field(
            default=True,
            description="Include page metadata (title, author, date) in output",
        ),
    ] = True
    include_tables: Annotated[
        bool,
        Field(default=True, description="Include tables in extracted content"),
    ] = True
    include_links: Annotated[
        bool,
        Field(default=False, description="Include hyperlinks in extracted content"),
    ] = False


class FetchMultipleParams(BaseModel):
    """Parameters for fetching multiple URLs."""

    urls: Annotated[
        list[str],
        Field(description="List of URLs to fetch", min_length=1, max_length=10),
    ]
    max_length_per_url: Annotated[
        int,
        Field(
            default=2000,
            description="Maximum characters per URL",
            gt=0,
            lt=100000,
        ),
    ] = 2000
    raw: Annotated[
        bool,
        Field(default=False, description="Get raw content without extraction"),
    ] = False


@mcp.tool()
async def fetch(
    url: Annotated[
        str, Field(description="The webpage URL to fetch (must be http:// or https://)")
    ],
    max_length: Annotated[
        int,
        Field(
            description=(
                "Maximum characters to return. "
                "Use 1000-2000 for summaries, 5000 (default) for full content."
            ),
            default=DEFAULT_MAX_LENGTH,
        ),
    ] = DEFAULT_MAX_LENGTH,
    start_index: Annotated[
        int,
        Field(
            description=(
                "Character offset for pagination. "
                "Use the value from 'start_index=N' in truncated responses."
            ),
            default=0,
        ),
    ] = 0,
    get_raw_html: Annotated[
        bool,
        Field(
            description=(
                "Skip extraction and return raw HTML. "
                "Use when you need original markup or extraction fails."
            ),
            default=False,
        ),
    ] = False,
    include_metadata: Annotated[
        bool,
        Field(
            description="Include title, author, date at top. Disable to save tokens.",
            default=True,
        ),
    ] = True,
    include_tables: Annotated[
        bool,
        Field(
            description="Preserve tables in markdown. Disable for text-only articles.",
            default=True,
        ),
    ] = True,
    include_links: Annotated[
        bool,
        Field(
            description="Preserve hyperlinks in markdown. Enable to follow references.",
            default=False,
        ),
    ] = False,
    bypass_robots_txt: Annotated[
        bool,
        Field(
            description="Skip robots.txt check. Only for user-initiated requests.",
            default=False,
        ),
    ] = False,
) -> str:
    """
    Fetch a single webpage and extract its main content as clean markdown.

    USE THIS TOOL WHEN:
    - You need to read an article, documentation page, or blog post
    - You want clean, readable text without boilerplate (navbars, ads, footers)
    - The user provides a specific URL to read

    DO NOT USE WHEN:
    - You need to fetch multiple URLs (use fetch_batch instead - fewer round trips)
    - You want to discover what pages exist on a site (use discover_links first)

    PAGINATION: Large pages are automatically truncated. The response will include
    'use start_index=N to continue' - call again with that value to get more content.

    EXAMPLES:
    - fetch(url="https://docs.example.com/guide") → Get documentation page
    - fetch(url="https://example.com/api", max_length=2000) → Shorter response to save context
    - fetch(url="https://example.com/data", include_tables=True) → Preserve tabular data
    """
    if not url:
        raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

    user_agent = DEFAULT_USER_AGENT_AUTONOMOUS

    # Check robots.txt unless ignored
    if not bypass_robots_txt:
        async with httpx.AsyncClient() as client:
            await check_robots_txt(url, user_agent, client)

    # Fetch and extract content
    content, content_type = await fetch_and_extract(
        url,
        user_agent,
        raw=get_raw_html,
        include_metadata=include_metadata,
        include_tables=include_tables,
        include_links=include_links,
    )

    # Handle pagination
    original_length = len(content)

    if start_index >= original_length:
        return (
            f"<error>start_index={start_index} exceeds content length "
            f"({original_length} chars). Use start_index=0 to restart.</error>"
        )

    truncated = content[start_index : start_index + max_length]

    if not truncated:
        return (
            f"<error>No content extracted from {url}. "
            "Try get_raw_html=True or verify the URL has readable content.</error>"
        )

    # Build response
    result_parts = [f"# Content from {url}", f"<!-- Type: {content_type} -->", ""]

    remaining = original_length - (start_index + len(truncated))
    if len(truncated) == max_length and remaining > 0:
        next_index = start_index + len(truncated)
        result_parts.append(truncated)
        result_parts.append("")
        result_parts.append(
            f"<!-- Truncated. {remaining} chars remaining. "
            f"Use start_index={next_index} to continue. -->",
        )
    else:
        result_parts.append(truncated)

    return "\n".join(result_parts)


@mcp.tool()
async def fetch_batch(
    urls: Annotated[
        list[str],
        Field(
            description=(
                "List of webpage URLs to fetch (max 10). "
                "URLs are fetched sequentially and results combined."
            )
        ),
    ],
    max_length_per_url: Annotated[
        int,
        Field(
            description=(
                "Character limit per URL. Use 1000-1500 when fetching many pages. "
                "Default 2000."
            ),
            default=2000,
        ),
    ] = 2000,
    get_raw_html: Annotated[
        bool,
        Field(
            description="Skip content extraction and return raw HTML for all URLs.",
            default=False,
        ),
    ] = False,
) -> str:
    """
    Fetch multiple webpages in a single request and return combined content.

    USE THIS TOOL WHEN:
    - You have 2-10 URLs to read (e.g., from discover_links results)
    - Comparing content across multiple pages
    - Gathering context from several documentation pages at once

    KEY BENEFIT: One tool call instead of multiple fetch() calls = fewer round trips,
    faster results, and reduced overhead in supervised/approval workflows.

    WORKFLOW EXAMPLE:
    1. discover_links(url="https://docs.example.com", filter_pattern="/api/")
    2. fetch_batch(urls=[...returned links...], max_length_per_url=1500)

    NOTES:
    - Each URL's content is separated by '---' dividers
    - Failed URLs show inline errors without stopping other fetches
    - Robots.txt is NOT checked for batch fetches (assumes prior discovery)
    """
    if not urls:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=(
                    "urls list is empty. Provide 1-10 URLs. "
                    "Example: urls=['https://example.com/page1']"
                ),
            )
        )

    if len(urls) > 10:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=(
                    f"Too many URLs ({len(urls)}). Maximum 10 per request. "
                    "Split into multiple fetch_batch calls."
                ),
            ),
        )

    user_agent = DEFAULT_USER_AGENT_AUTONOMOUS
    results = []

    for url in urls:
        try:
            content, content_type = await fetch_and_extract(
                url,
                user_agent,
                raw=get_raw_html,
                include_metadata=False,
            )
            truncated = content[:max_length_per_url]
            if len(content) > max_length_per_url:
                omitted = len(content) - max_length_per_url
                truncated += f"\n<!-- Truncated: {omitted} chars omitted -->"

            results.append(f"## {url}\n<!-- Type: {content_type} -->\n\n{truncated}")
        except McpError as e:
            results.append(f"## {url}\n\n<error>{e.error.message}</error>")
        except Exception as e:
            results.append(f"## {url}\n\n<error>Unexpected error: {e!r}</error>")

    return "\n\n---\n\n".join(results)


@mcp.tool()
async def discover_links(
    url: Annotated[
        str,
        Field(
            description="The webpage URL to scan for links (e.g., a docs index or sitemap)"
        ),
    ],
    filter_pattern: Annotated[
        str,
        Field(
            description=(
                "Regex to filter links. Examples: '/docs/', '\\.pdf$', 'api|guide'. "
                "Leave empty for all links."
            ),
            default="",
        ),
    ] = "",
) -> str:
    """
    Discover all links on a webpage. Use this BEFORE fetch_batch to find relevant URLs.

    USE THIS TOOL WHEN:
    - Exploring a documentation site to find relevant pages
    - Building a list of URLs to fetch in batch
    - Finding all subpages under a section (e.g., all /api/ docs)
    - Checking what content exists before deciding what to read

    RECOMMENDED WORKFLOW:
    1. discover_links(url="https://docs.example.com/", filter_pattern="/guide/")
    2. Review the returned links and select relevant ones
    3. fetch_batch(urls=[selected_urls], max_length_per_url=1500)

    FILTER EXAMPLES:
    - filter_pattern="/docs/"     → Only links containing '/docs/'
    - filter_pattern="getting-started|quickstart" → Links with either term
    - filter_pattern="\\.md$"     → Only markdown file links

    NOTES:
    - Returns up to 100 links (more are noted but omitted to save context)
    - Relative URLs are automatically resolved to absolute URLs
    - JavaScript/mailto/anchor links are excluded
    """
    if not url:
        raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

    user_agent = DEFAULT_USER_AGENT_AUTONOMOUS

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"),
            )

    # Extract links using regex (simple but effective)
    html = response.text
    link_pattern = r'href=["\']([^"\']+)["\']'
    matches = re.findall(link_pattern, html, re.IGNORECASE)

    # Deduplicate and filter
    seen = set()
    links = []
    for link in matches:
        if link not in seen:
            seen.add(link)
            # Apply filter if provided
            if filter_pattern:
                if re.search(filter_pattern, link):
                    links.append(link)
            else:
                links.append(link)

    # Resolve relative URLs
    parsed_base = urlparse(url)
    base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"

    resolved_links = []
    for link in links:
        if link.startswith("//"):
            resolved_links.append(f"{parsed_base.scheme}:{link}")
        elif link.startswith("/"):
            resolved_links.append(f"{base_url}{link}")
        elif link.startswith("http"):
            resolved_links.append(link)
        elif not link.startswith(("#", "javascript:", "mailto:", "tel:")):
            resolved_links.append(f"{base_url}/{link}")

    result = [f"# Links from {url}", f"Found {len(resolved_links)} links", ""]
    result.extend(f"- {link}" for link in resolved_links[:100])

    if len(resolved_links) > 100:
        result.append(f"\n<!-- {len(resolved_links) - 100} more links omitted -->")

    return "\n".join(result)


def parse_llms_txt(txt: str) -> dict:
    """
    Parse llms.txt file contents to extract structure and links.

    Args:
        txt: Raw text content of llms.txt file

    Returns:
        Dictionary with title, summary, and sections containing links
    """

    def _chunked(it, chunk_sz: int):
        it = iter(it)
        return iter(lambda: list(itertools.islice(it, chunk_sz)), [])

    def _parse_links(links: str) -> list[dict[str, str]]:
        link_pat = r"-\s*\[(?P<title>[^\]]+)\]\((?P<url>[^\)]+)\)(?::\s*(?P<desc>.*))?"
        return [
            m.groupdict()
            for line in re.split(r"\n+", links.strip())
            if line.strip() and (m := re.search(link_pat, line))
        ]

    # Split into header and sections
    start, *rest = re.split(r"^##\s*(.*?$)", txt, flags=re.MULTILINE)

    # Parse sections
    sects = {k: _parse_links(v) for k, v in dict(_chunked(rest, 2)).items()}

    # Parse header with optional summary (blockquote)
    pat_with_summary = (
        r"^#\s*(?P<title>.+?$)\n+" r"(?:^>\s*(?P<summary>.+?$)\n+)?" r"(?P<info>.*)"
    )
    match = re.search(pat_with_summary, start.strip(), re.MULTILINE | re.DOTALL)

    if match:
        d = match.groupdict()
        d["summary"] = d.get("summary") or ""
        d["info"] = (d.get("info") or "").strip()
    else:
        # Fallback: just extract title
        title_match = re.search(r"^#\s*(.+?)$", start.strip(), re.MULTILINE)
        d = {
            "title": title_match.group(1) if title_match else "Unknown",
            "summary": "",
            "info": "",
        }

    d["sections"] = sects
    return d


@mcp.tool()
async def fetch_llms_txt(
    url: Annotated[
        str,
        Field(
            description="URL to an llms.txt file (e.g., https://example.com/llms.txt)"
        ),
    ],
    include_content: Annotated[
        bool,
        Field(
            description="If true, also fetch content of all linked pages. Default false.",
            default=False,
        ),
    ] = False,
    max_length_per_url: Annotated[
        int,
        Field(
            description="When include_content=True, max chars per linked page. Default 2000.",
            default=2000,
        ),
    ] = 2000,
) -> str:
    """
    Fetch and parse an llms.txt file to discover LLM-friendly documentation.

    USE THIS TOOL WHEN:
    - A site provides an llms.txt file for AI-friendly content discovery
    - You need to understand what documentation is available
    - You want to fetch structured docs in a single request

    WHAT IS llms.txt:
    A proposal for sites to provide LLM-friendly content at /llms.txt.
    It's a markdown file listing documentation links with descriptions.
    See https://llmstxt.org for the specification.

    WORKFLOW:
    1. fetch_llms_txt(url="https://example.com/llms.txt") → Get structure
    2. Review sections and links
    3. Either use include_content=True or fetch_batch for specific pages

    EXAMPLES:
    - fetch_llms_txt(url="https://fastht.ml/docs/llms.txt")
    - fetch_llms_txt(url="https://example.com/llms.txt", include_content=True)
    """
    if not url:
        raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

    user_agent = DEFAULT_USER_AGENT_AUTONOMOUS

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        # Fetch the llms.txt file
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to fetch llms.txt from {url}: {e!r}",
                ),
            )

        # Parse the llms.txt content
        try:
            parsed = parse_llms_txt(response.text)
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse llms.txt: {e!r}",
                ),
            )

        # Build the response
        result_parts = [
            f"# {parsed.get('title', 'llms.txt')}",
            "",
        ]

        if parsed.get("summary"):
            result_parts.append(f"> {parsed['summary']}")
            result_parts.append("")

        if parsed.get("info"):
            result_parts.append(parsed["info"])
            result_parts.append("")

        # Resolve relative URLs to absolute URLs
        parsed_base = urlparse(url)
        base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"

        def resolve_url(link_url: str) -> str:
            """Resolve relative URLs to absolute URLs."""
            if link_url.startswith(("http://", "https://")):
                return link_url
            elif link_url.startswith("//"):
                return f"{parsed_base.scheme}:{link_url}"
            elif link_url.startswith("/"):
                return f"{base_url}{link_url}"
            else:
                # Relative path - resolve from the llms.txt directory
                base_path = parsed_base.path.rsplit("/", 1)[0]
                return f"{base_url}{base_path}/{link_url}"

        # Collect all URLs for potential content fetching
        all_urls: list[tuple[str, str, str]] = []  # (url, title, section)

        sections = parsed.get("sections", {})
        for section_name, links in sections.items():
            result_parts.append(f"## {section_name}")
            result_parts.append("")
            for link in links:
                title = link.get("title", "")
                link_url = link.get("url", "")
                desc = link.get("desc", "")

                if link_url:
                    # Resolve relative URLs
                    resolved_url = resolve_url(link_url)
                    all_urls.append((resolved_url, title, section_name))
                    desc_str = f": {desc}" if desc else ""
                    result_parts.append(f"- [{title}]({resolved_url}){desc_str}")

            result_parts.append("")

        result_parts.append(f"---\nFound {len(all_urls)} documentation links.")

        # Optionally fetch all content
        if include_content and all_urls:
            result_parts.append("")
            result_parts.append("# Fetched Content")
            result_parts.append("")

            for link_url, title, section in all_urls:
                try:
                    content, content_type = await fetch_and_extract(
                        link_url,
                        user_agent,
                        raw=False,
                        include_metadata=False,
                    )
                    truncated = content[:max_length_per_url]
                    if len(content) > max_length_per_url:
                        omitted = len(content) - max_length_per_url
                        truncated += f"\n<!-- Truncated: {omitted} chars omitted -->"

                    result_parts.append(f"## {title}")
                    result_parts.append(
                        f"<!-- Section: {section} | URL: {link_url} -->"
                    )
                    result_parts.append("")
                    result_parts.append(truncated)
                    result_parts.append("")
                    result_parts.append("---")
                    result_parts.append("")
                except Exception as e:
                    result_parts.append(f"## {title}")
                    result_parts.append(
                        f"<error>Failed to fetch {link_url}: {e!r}</error>"
                    )
                    result_parts.append("")

    return "\n".join(result_parts)


# Prompts for user-initiated fetching (bypasses robots.txt)
@mcp.prompt()
def fetch_manual(url: str) -> str:
    """Fetch a URL manually (user-initiated, bypasses robots.txt check)."""
    return f"Please fetch and summarize the content from: {url}"


@mcp.prompt()
def research_topic(topic: str, urls: str = "") -> str:
    """Research a topic by fetching multiple relevant URLs."""
    if urls:
        return f"Research the topic '{topic}' using these URLs:\n{urls}"
    return f"Research the topic '{topic}' by finding and fetching relevant web pages."


def main():
    """Run the FetchV2 MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
