# FetchV2 MCP Server

[![PyPI version](https://img.shields.io/pypi/v/fetchv2-mcp-server.svg)](https://pypi.org/project/fetchv2-mcp-server/)
[![CI](https://github.com/praveenc/fetchv2-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/praveenc/fetchv2-mcp-server/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

FetchV2 is a Model Context Protocol (MCP) server that retrieves web pages and returns clean Markdown.
It uses [Trafilatura](https://trafilatura.readthedocs.io/) to remove navigation, advertisements, footers, and other page elements.

## What it does

| Tool | Use |
| ---- | --- |
| `fetch` | Fetch one web page and extract its main content |
| `fetch_batch` | Fetch up to 10 web pages in one request |
| `discover_links` | Find and filter links on a web page |
| `fetch_llms_txt` | Read an [llms.txt](https://llmstxt.org) index and optionally fetch its linked pages |

FetchV2 can return raw HTML, preserve links and tables, and paginate long content.
The `fetch` tool checks `robots.txt` by default.

## Quick start

### Requirements

1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/).
2. Install Python 3.11 or newer:

```bash
uv python install 3.11
```

### Install for Cursor or VS Code

| Cursor | VS Code |
| ------ | ------- |
| [Install MCP Server](https://cursor.com/install-mcp?name=fetchv2-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmZXRjaHYyLW1jcC1zZXJ2ZXJAbGF0ZXN0Il0sImVudiI6e30sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [Install on VS Code](https://insiders.vscode.dev/redirect/mcp/install?name=FetchV2%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22fetchv2-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### Configure another MCP client

Add this server definition to your MCP client configuration:

```json
{
  "mcpServers": {
    "fetchv2": {
      "command": "uvx",
      "args": ["fetchv2-mcp-server@latest"]
    }
  }
}
```

Common configuration file locations:

- Claude Desktop on macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Claude Desktop on Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Windsurf: `~/.codeium/windsurf/mcp_config.json`
- Kiro: `.kiro/settings/mcp.json` in your project

### Install in a Python environment

Use one of these commands if you want to install the package directly:

```bash
uv add fetchv2-mcp-server
```

```bash
pip install fetchv2-mcp-server
```

## Try it

Ask your MCP client to perform a task such as:

- "Fetch the documentation from `<URL>`."
- "Find links on `<docs URL>` that contain `tutorial`."
- "Read these pages and summarize their differences: `[url1, url2, url3]`."

## Typical documentation workflow

First, find the relevant pages:

```python
discover_links(url="https://docs.example.com/", filter_pattern="/guide/")
```

Then fetch the selected pages in one request:

```python
fetch_batch(
    urls=[
        "https://docs.example.com/guide/intro",
        "https://docs.example.com/guide/setup",
    ]
)
```

## Tool reference

### `fetch`

Fetch one web page and extract its main content as Markdown.

```python
fetch(
    url: str,
    max_length: int = 5000,
    start_index: int = 0,
    get_raw_html: bool = False,
    include_metadata: bool = True,
    include_tables: bool = True,
    include_links: bool = False,
    bypass_robots_txt: bool = False,
) -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `url` | `str` | required | Web page URL |
| `max_length` | `int` | `5000` | Maximum number of characters to return |
| `start_index` | `int` | `0` | Character offset for pagination |
| `get_raw_html` | `bool` | `False` | Return raw HTML without extraction |
| `include_metadata` | `bool` | `True` | Include the title, author, and date |
| `include_tables` | `bool` | `True` | Preserve tables in Markdown |
| `include_links` | `bool` | `False` | Preserve links in Markdown |
| `bypass_robots_txt` | `bool` | `False` | Skip the `robots.txt` check for a user-requested fetch |

If the response is truncated, use the returned `start_index` value in the next call.

### `fetch_batch`

Fetch up to 10 web pages and combine the results.

```python
fetch_batch(
    urls: list[str],
    max_length_per_url: int = 2000,
    get_raw_html: bool = False,
) -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `urls` | `list[str]` | required | Web page URLs to fetch |
| `max_length_per_url` | `int` | `2000` | Maximum number of characters to return for each URL |
| `get_raw_html` | `bool` | `False` | Return raw HTML without extraction |

This tool reports a failed URL in its result and continues with the other URLs.
It does not check `robots.txt`.

### `discover_links`

Find links on a web page and optionally filter them with a regular expression.

```python
discover_links(url: str, filter_pattern: str = "") -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `url` | `str` | required | Web page URL to scan |
| `filter_pattern` | `str` | `""` | Regular expression used to filter links |

The tool resolves relative links and returns up to 100 URLs.

### `fetch_llms_txt`

Read an `llms.txt` file and list its documentation links.

```python
fetch_llms_txt(
    url: str,
    include_content: bool = False,
    max_length_per_url: int = 2000,
) -> str
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `url` | `str` | required | URL of an `llms.txt` file |
| `include_content` | `bool` | `False` | Fetch the content of all linked pages |
| `max_length_per_url` | `int` | `2000` | Maximum number of characters to return for each linked page |

By default, this tool fetches only the `llms.txt` index.
Set `include_content=True` to fetch all linked pages.
This option can return a large response.

The tool resolves relative URLs, such as `/docs/guide.md`, against the `llms.txt` URL.

## Prompts

- `fetch_manual` creates a request to fetch and summarize one URL.
- `research_topic` creates a request to research a topic with optional URLs.

## Development

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/praveenc/fetchv2-mcp-server.git
cd fetchv2-mcp-server
uv sync --dev
```

Run the tests:

```bash
uv run pytest
```

Run the server with MCP Inspector:

```bash
uv run mcp dev src/fetchv2_mcp_server/server.py
```

Run lint and type checks:

```bash
uv run ruff check .
uv run pyright
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before you submit a change.

## Support

Use the [GitHub issue tracker](https://github.com/praveenc/fetchv2-mcp-server/issues) to report a problem or request a feature.

## License

This project uses the MIT License.
See [LICENSE](LICENSE) for details.
