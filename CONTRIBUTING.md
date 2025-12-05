# Contributing to FetchV2 MCP Server

Thanks for your interest in contributing!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/praveenc/fetchv2-mcp-server.git
cd fetchv2-mcp-server

# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev
```

## Running Tests

```bash
uv run pytest
```

## Code Quality

```bash
# Linting
uv run ruff check .

# Type checking
uv run pyright

# Format (auto-fix)
uv run ruff check --fix .
```

## Testing with MCP Inspector

```bash
uv run mcp dev src/fetchv2_mcp_server/server.py
```

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Make your changes
3. Ensure tests pass and code quality checks are clean
4. Update CHANGELOG.md with your changes
5. Submit a PR with a clear description

## Code Style

- Use type hints for all function parameters and returns
- Write docstrings for public functions
- Follow existing patterns in the codebase
