---
name: discover-and-batch
description: Find the relevant pages on a documentation site with discover_links, then read them together with fetch_batch. Use when you need several pages from one site, such as all guides or API pages, and do not yet know their URLs.
---

# Discover links, then fetch in batch

## Steps

1. Call `discover_links(url=<index page>, filter_pattern=<regex>)`.
   Use a tight regular expression, for example `/guide/` or `/api/v2/`.
   An empty `filter_pattern` returns every link on the page.
2. The result lists at most 100 URLs and notes how many were omitted.
   If it says links were omitted, tighten `filter_pattern` and call again.
3. Pick the pages you need.
   Do not fetch the whole list by default.
4. Call `fetch_batch(urls=[...], max_length_per_url=1500)`.
   A call accepts 1 to 10 URLs.
   More than 10 is rejected, so split the list into groups of 10 or fewer.
5. `fetch_batch` reports a failed URL in its result and continues with the rest.
   Retry failed URLs with `fetch`.

## Notes

- `max_length_per_url` defaults to 2000.
  Use 1000 to 1500 when fetching many pages.
- A page cut at `max_length_per_url` ends with a `Truncated` comment.
  Read the rest with `fetch` and `start_index` (see the `paginate-long-pages` skill).
- `fetch_batch` does not check robots.txt.
  See the `robots-and-safety` skill before fetching pages the user did not name.
