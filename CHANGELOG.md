# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-05

### Added

- `fetch_llms_txt` tool - Parse and fetch LLM-friendly documentation from llms.txt files
- Support for the [llms.txt](https://llmstxt.org) specification
- `include_content` parameter to explicitly fetch all linked pages in one request
- Automatic resolution of relative URLs to absolute URLs (handles Raycast-style paths)

### Notes

- By default, only the llms.txt index is fetched — linked .md files are NOT downloaded
- Set `include_content=True` to fetch all linked documentation pages

## [1.0.1] - 2025-12-04

### Changed

- Improved README with one-click install buttons for Cursor and VS Code
- Added Prerequisites section
- Added Basic Usage section with example prompts
- Converted tool parameters to tables for better readability
- Added Windows config location for Claude Desktop

## [1.0.0] - 2025-12-04

### Added

- Initial release
- `fetch` tool - Single URL fetching with Trafilatura extraction
- `fetch_multiple` tool - Batch fetch up to 10 URLs
- `extract_links` tool - Link discovery with regex filtering
- `fetch_manual` prompt - User-initiated fetch bypassing robots.txt
- `research_topic` prompt - Research helper
- Robots.txt compliance with graceful timeout handling
- Pagination support via `start_index` parameter
- Automatic markdown URL detection (.md, .markdown, .mdx)
- Metadata extraction (title, author, date)
