# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
