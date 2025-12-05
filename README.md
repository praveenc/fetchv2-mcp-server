# FetchV2 MCP Server

A robust Model Context Protocol server for fetching and extracting web content using [Trafilatura](https://trafilatura.readthedocs.io/en/latest/). Optimized for AI agents with clean markdown output.

## Why FetchV2?

**Trafilatura is the real star.** Unlike basic HTML-to-markdown converters, Trafilatura is specifically designed for web content extraction:

- Removes boilerplate (navbars, footers, ads, cookie banners)
- Preserves article structure and tables
- Extracts metadata (title, author, date) automatically
- Handles edge cases like minimal-content SPAs

**Graceful robots.txt handling.** Instead of failing hard when robots.txt is unreachable, FetchV2 treats timeout/unavailable as "allowed" - more practical for real-world use.

## Features

- **Superior Content Extraction**: Uses Trafilatura for high-quality HTML-to-markdown conversion
- **Robots.txt Compliance**: Respects robots.txt by default, gracefully handles timeouts
- **Pagination Support**: Handle large pages with `start_index` parameter
- **Multi-URL Fetching**: Fetch up to 10 URLs in a single request
- **Link Discovery**: Extract and filter links from any webpage
- **Raw Mode**: Get unprocessed content when needed
- **Markdown Detection**: Automatically handles `.md` files without extraction

## Installation

```bash
# Clone the repo
git clone https://github.com/praveenc/fetchv2-mcp-server.git
cd fetchv2-mcp-server

# Using uv (recommended)
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Available Tools

### `fetch`

Fetch a single webpage and extract its main content as clean markdown.

**Use when:** Reading an article, documentation page, or blog post.

Parameters:

- `url` (required): The webpage URL to fetch
- `max_length` (default: 5000): Maximum characters to return (use 1000-2000 for summaries)
- `start_index` (default: 0): Character offset for pagination
- `get_raw_html` (default: false): Skip extraction, return original HTML
- `include_metadata` (default: true): Include title, author, date at top
- `include_tables` (default: true): Preserve tables in markdown format
- `include_links` (default: false): Preserve hyperlinks in output
- `bypass_robots_txt` (default: false): Skip robots.txt check (user-initiated only)

### `fetch_batch`

Fetch multiple webpages in a single request. **Fewer round trips = faster workflows.**

**Use when:** You have 2-10 URLs to read (e.g., from `discover_links` results).

Parameters:

- `urls` (required): List of URLs (max 10)
- `max_length_per_url` (default: 2000): Character limit per URL
- `get_raw_html` (default: false): Skip extraction for all URLs

### `discover_links`

Discover all links on a webpage. **Use before `fetch_batch` to find relevant URLs.**

**Use when:** Exploring a site to find relevant pages before fetching.

Parameters:

- `url` (required): The webpage URL to scan for links
- `filter_pattern` (optional): Regex to filter links (e.g., `/docs/`, `\.pdf$`)

## Real-World Use Cases

### Discovery → Batch Fetch Workflow

First, discover what pages exist:

```python
discover_links(url="https://kiro.dev/docs/", filter_pattern="/docs/")
```

Tool Output:

```bash
# Links from https://kiro.dev/docs/
Found 11 links

- https://kiro.dev/docs/getting-started/installation/
- https://kiro.dev/docs/getting-started/first-project/
- https://kiro.dev/docs/specs/
- https://kiro.dev/docs/hooks/
- https://kiro.dev/docs/chat/
- https://kiro.dev/docs/steering/
- https://kiro.dev/docs/mcp/
...
```

Then fetch multiple pages at once:

```python
fetch_batch(
  urls=["https://kiro.dev/docs/specs/", "https://kiro.dev/docs/hooks/", "https://kiro.dev/docs/steering/"],
  max_length_per_url=1500
)
```

Tool Output:

```markdown
## https://kiro.dev/docs/specs/
<!-- Type: markdown (extracted) -->

Specs or specifications are structured artifacts that formalize the development
process for complex features in your application...

---

## https://kiro.dev/docs/hooks/
<!-- Type: markdown (extracted) -->

Agent hooks are powerful automation tools that streamline your development
workflow by automatically executing predefined agent actions...

---

## https://kiro.dev/docs/steering/
<!-- Type: markdown (extracted) -->

Steering gives Kiro persistent knowledge about your workspace through markdown
files. Instead of explaining your conventions in every chat...
```

### Use Case Examples

**discover_links:**

- Docs crawling - Find all pages before scraping
- Competitive research - Extract blog post links from a site
- API discovery - Find all API endpoint documentation pages

**fetch_batch:**

- Comparison research - Fetch React, Vue, and Svelte docs to compare approaches
- Onboarding context - Grab multiple docs pages to understand a new tool
- Multi-source fact-checking - Get the same topic from different sources

**Key value: fewer round trips.** Instead of 10 separate fetch calls (10 tool invocations, 10 approvals in supervised mode), you get everything in 1-2 calls.

## Configuration

### Kiro / VS Code

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "fetchv2": {
      "command": "uv",
      "args": ["--directory", "/path/to/fetchv2-mcp-server", "run", "python", "-m", "fetchv2_mcp_server"]
    }
  }
}
```

### Claude Desktop

```json
{
  "mcpServers": {
    "fetchv2": {
      "command": "uv",
      "args": ["--directory", "/path/to/fetchv2-mcp-server", "run", "python", "-m", "fetchv2_mcp_server"]
    }
  }
}
```

## Prompts

- **fetch_manual** - User-initiated fetch that bypasses robots.txt
- **research_topic** - Research a topic by fetching multiple relevant URLs

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run with MCP Inspector
mcp dev server.py

# Type checking
uv run pyright

# Linting
uv run ruff check .
```

## Project Structure

```bash
fetchv2_mcp_server/
├── pyproject.toml
├── README.md
└── src/
    └── fetchv2_mcp_server/
        ├── __init__.py
        ├── __main__.py
        └── server.py
```

## License

MIT
