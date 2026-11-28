---
name: paginate-long-pages
description: Read a long page in pieces with fetch by following the start_index the server returns, instead of raising max_length. Use when a fetch result ends with a Truncated comment or when you need content beyond the first 5000 characters.
---

# Paginate long pages

## Steps

1. Call `fetch(url=<url>)`.
   `max_length` defaults to 5000 characters and `start_index` defaults to 0.
2. If the result ends with `Truncated. N chars remaining. Use start_index=M to continue`, call `fetch` again.
   Pass the same `url` and set `start_index` to exactly M.
3. Repeat until no `Truncated` comment remains or you have what you need.
   Stop early once the answer is found.

## Rules

- Take `start_index` from the result.
  Do not compute it yourself.
- Do not raise `max_length` to avoid paging.
  Large values fill the context with text you may not need.
- Keep `max_length` and the other options (`include_links`, `include_tables`, `get_raw_html`) the same on every page of one document.
  Changed options change the extracted text, so the offsets no longer line up.
- If the result says `start_index` exceeds the content length, the page is finished or has changed.
  Restart at `start_index=0` only if you need to re-read it.
- Use `max_length` 1000 to 2000 for summaries and 5000 for full reading.
