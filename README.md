# FetchV2 MCP Server

[![PyPI version](https://img.shields.io/pypi/v/fetchv2-mcp-server.svg)](https://pypi.org/project/fetchv2-mcp-server/)
[![CI](https://github.com/praveenc/fetchv2-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/praveenc/fetchv2-mcp-server/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Model Context Protocol (MCP) server for web content fetching and extraction.

This MCP server provides tools to fetch webpages, extract clean content using [Trafilatura](https://trafilatura.readthedocs.io/), and discover links for batch processing.

## Features

- **Fetch Webpages**: Extract clean markdown content from any URL
- **Batch Fetching**: Fetch up to 10 URLs in a single request
- **Link Discovery**: Find and filter links on any webpage
- **Smart Extraction**: Trafilatura removes boilerplate (navbars, ads, footers)
- **Robots.txt Compliance**: Respects robots.txt with graceful timeout handling
- **Pagination Support**: Handle large pages with `start_index` parameter

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python 3.10 or newer using `uv python install 3.10`

## Installation

| Cursor | VS Code |
| ------ | ------- |
| [Install MCP Server](https://cursor.com/install-mcp?name=fetchv2-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmZXRjaHYyLW1jcC1zZXJ2ZXJAbGF0ZXN0Il0sImVudiI6e30sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [Install on VS Code](https://insiders.vscode.dev/redirect/mcp/install?name=FetchV2%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22fetchv2-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Or configure manually in your MCP client:

```json
{
  "mcpServers": {
    "fetchv2": {
      "command": "uvx",
      "args": ["fetchv2-mcp-server@latest"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Config file locations:**

- **Claude Desktop (macOS)**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Desktop (Windows)**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Windsurf**: `~/.codeium/windsurf/mcp_config.json`
- **Kiro**: `.kiro/settings/mcp.json` in your project

### Install from PyPI

```bash
# Using uv
uv add fetchv2-mcp-server

# Using pip
pip install fetchv2-mcp-server
```

## Basic Usage

Example prompts to try:

- "Fetch the documentation from `<URL>`"
- "Find all links on `<docs URL>` that contain 'tutorial'"
- "Read these three pages and summarize the differences: `[url1, url2, url3]`"

## Available Tools

### fetch

Fetches a webpage and extracts its main content as clean markdown.

```python
fetch(url: str, max_length: int = 5000, start_index: int = 0) -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `url` | str | required | The webpage URL to fetch |
| `max_length` | int | 5000 | Maximum characters to return |
| `start_index` | int | 0 | Character offset for pagination |
| `get_raw_html` | bool | false | Skip extraction, return raw HTML |
| `include_metadata` | bool | true | Include title, author, date |
| `include_tables` | bool | true | Preserve tables in markdown |
| `include_links` | bool | false | Preserve hyperlinks |
| `bypass_robots_txt` | bool | false | Skip robots.txt check |

### fetch_batch

Fetches multiple webpages in a single request.

```python
fetch_batch(urls: list[str], max_length_per_url: int = 2000) -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `urls` | list[str] | required | List of URLs (max 10) |
| `max_length_per_url` | int | 2000 | Character limit per URL |
| `get_raw_html` | bool | false | Skip extraction for all URLs |

### discover_links

Discovers all links on a webpage with optional filtering.

```python
discover_links(url: str, filter_pattern: str = "") -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `url` | str | required | The webpage URL to scan |
| `filter_pattern` | str | "" | Regex to filter links (e.g., `/docs/`) |

## Workflow Example

**Step 1:** Discover relevant documentation pages

```python
discover_links(url="https://docs.example.com/", filter_pattern="/guide/")
```

**Step 2:** Batch fetch the pages you need

```python
fetch_batch(urls=["https://docs.example.com/guide/intro", "https://docs.example.com/guide/setup"])
```

## Prompts

- **fetch_manual** - User-initiated fetch that bypasses robots.txt
- **research_topic** - Research a topic by fetching multiple relevant URLs

## Development

```bash
# Clone and install
git clone https://github.com/praveenc/fetchv2-mcp-server.git
cd fetchv2-mcp-server
uv sync --dev
source .venv/bin/activate

# Run tests
uv run pytest

# Run with MCP Inspector
mcp dev src/fetchv2_mcp_server/server.py

# Linting and type checking
uv run ruff check .
uv run pyright
```

## License

MIT - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

For issues and questions, use the [GitHub issue tracker](https://github.com/praveenc/fetchv2-mcp-server/issues).
