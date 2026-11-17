# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-11-16

### Changed

- **Behavior change:** all tools now refuse private and local addresses by default. Set `FETCHV2_ALLOW_PRIVATE_NETWORKS=1` to restore the old behavior.
- **Behavior change:** responses over 5 MB are truncated, or refused when `Content-Length` is over 5 MB.

### Security

- Refuse requests to loopback, private, link-local (including cloud metadata), unspecified, multicast, shared, and reserved addresses, for IPv4 and IPv6. The check runs on every redirect hop and on the `robots.txt` request.
- Add the `FETCHV2_ALLOW_PRIVATE_NETWORKS=1` environment variable to allow local and private hosts. The guard is on by default.
- Limit each response body to 5 MB. Refuse a larger `Content-Length` early, and cut a streamed body at the limit with a `Truncated` comment.

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
