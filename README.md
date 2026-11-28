# FetchV2 MCP Server

<!-- mcp-name: io.github.praveenc/fetchv2-mcp-server -->

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

When `robots.txt` disallows the URL, the result depends on the MCP client:

- If the client supports form elicitation, FetchV2 asks the user once whether to fetch the page anyway.
  If the user accepts, it fetches the page.
  If the user declines or cancels, it returns a normal result that says the page was not fetched.
- If the client does not support elicitation, the tool returns an error.
  The error suggests the `fetch_manual` prompt or `bypass_robots_txt=True` for a user-requested fetch.
- Kiro CLI in headless mode (`kiro-cli chat --no-interactive`) supports elicitation but cancels every prompt.
  The result says the page was not fetched.

The private network guard runs before the `robots.txt` check and never asks the user.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/praveenc/fetchv2-mcp-server/main/docs/diagrams/fetch-confirmation-dark.svg">
  <img src="https://raw.githubusercontent.com/praveenc/fetchv2-mcp-server/main/docs/diagrams/fetch-confirmation-light.svg" width="560" alt="Flowchart: fetch refuses a non-public address without a prompt. If robots.txt allows the URL, or bypass_robots_txt is true, it returns clean Markdown. Otherwise a client that can show a form asks the user. Accept fetches the page, and decline or cancel returns Not fetched. A client without forms gets the robots.txt error.">
</picture>

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

When the index lists more than 10 links and the client supports form elicitation, FetchV2 asks the user before it fetches all of them.
If the user declines or cancels, the tool returns only the index and a note to fetch selected pages with `fetch_batch`.
Clients without elicitation support get all pages, as before.

The tool resolves relative URLs, such as `/docs/guide.md`, against the `llms.txt` URL.

## Security

FetchV2 fetches URLs that a model chooses.
A web page can contain a prompt injection that asks the model to fetch an internal address.
FetchV2 has these limits to reduce that risk.

### Private network guard

FetchV2 refuses a request when the host is, or resolves to, a non-public address:

- Loopback: `127.0.0.0/8`, `::1`, and `localhost` names
- Private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and IPv6 unique local `fc00::/7`
- Link-local: `169.254.0.0/16` (including the cloud metadata address `169.254.169.254`) and `fe80::/10`
- Unspecified, multicast, shared (`100.64.0.0/10`), and reserved ranges
- IPv4-mapped IPv6 addresses, such as `::ffff:127.0.0.1`

The guard checks the first request and every redirect hop.
It also applies to the `robots.txt` request and to the pages that `fetch_llms_txt` loads.

To fetch local or private hosts on purpose, set this environment variable for the server:

```json
{
  "mcpServers": {
    "fetchv2": {
      "command": "uvx",
      "args": ["fetchv2-mcp-server@latest"],
      "env": { "FETCHV2_ALLOW_PRIVATE_NETWORKS": "1" }
    }
  }
}
```

The values `1`, `true`, and `yes` turn the guard off. The guard is on by default.
FetchV2 never asks the user to override this guard. Only the environment variable controls it.

### Response size limit

FetchV2 reads at most 5 MB (5,242,880 bytes) of each response body.
It refuses a response early when `Content-Length` is over the limit.
It also counts bytes while it reads, and it stops at the limit.
A cut body ends with a `<!-- Truncated: response body exceeded ... -->` comment.

### Known limits

- **DNS rebinding.** The guard resolves the host before the request, and then the HTTP client resolves it again to connect.
  A hostile DNS server can return a public address the first time and a private address the second time.
  The guard does not pin the connection to the checked address.
  If this risk matters, run the server where it cannot reach internal services, for example behind an egress firewall.
- **Proxies.** If you set `HTTP_PROXY` or `HTTPS_PROXY`, the proxy connects to the host. The proxy must apply its own rules.
- **Untrusted content.** Fetched page text is untrusted input.
  It can contain instructions written for the model.
  Do not let fetched text approve other tool calls.
  Be careful with `autoApprove` for this server.

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

The flowchart in this README is `docs/diagrams/fetch-confirmation.mmd`, rendered with [Pele](https://pele.run) 1.10.0.
After you edit the `.mmd` file, render it again to `fetch-confirmation-light.svg` and `fetch-confirmation-dark.svg` with the styles in `docs/diagrams/theme.css`, and commit all three files.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before you submit a change.

## Support

Use the [GitHub issue tracker](https://github.com/praveenc/fetchv2-mcp-server/issues) to report a problem or request a feature.

## License

This project uses the MIT License.
See [LICENSE](LICENSE) for details.
