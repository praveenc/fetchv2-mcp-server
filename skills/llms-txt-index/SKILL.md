---
name: llms-txt-index
description: Read a site's llms.txt documentation index with fetch_llms_txt, then fetch only the chosen links with fetch_batch. Use when a site publishes llms.txt, or when you need an overview of a project's docs before reading specific pages.
---

# Use an llms.txt index

## Steps

1. Call `fetch_llms_txt(url="https://<site>/llms.txt", include_content=False)`.
   `include_content` already defaults to `False`, which fetches only the index.
   The result lists each documentation link with its section and description.
   Relative links such as `/docs/guide.md` are resolved against the `llms.txt` URL.
2. Choose the links that match the question.
3. Call `fetch_batch(urls=[...])` with at most 10 of them per call.
4. Read more of a long page with `fetch` and `start_index`.

## Why not `include_content=True`

- It fetches every linked page in one response, which can be very large.
- `max_length_per_url` (default 2000) cuts each page, so you may still miss the part you need.
- Use it only for a small index, or when the user asks for all pages.
- On clients that can show a confirmation prompt, the server may ask the user first when this would fetch more than 10 pages.
  If the user declines, go back to step 2 and select links yourself.

## Notes

- If the site has no `llms.txt`, use `discover_links` on the docs index page (see the `discover-and-batch` skill).
