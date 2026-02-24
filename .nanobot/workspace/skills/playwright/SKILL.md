# Playwright Web Fetcher

Use this skill to fetch web pages, extract readable content, and take screenshots using a real browser (Playwright + Chromium). 

## When to Use

- When `web_fetch` tool returns empty, blocked, or incomplete content (JavaScript-heavy sites)
- When you need to interact with dynamic content that requires JavaScript execution
- When Brave search is unavailable and you need to fetch search result pages directly
- When you need a screenshot of a page for visual inspection

## When NOT to Use

- For simple static pages — use the built-in `web_fetch` tool first (faster)
- For API endpoints that return JSON — use `web_fetch` directly

## Usage

### Fetch page content
```bash
python3 /Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/playwright_fetch.py <url>
```

### Fetch with screenshot
```bash
python3 /Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/playwright_fetch.py <url> --screenshot
```

### Fetch without text extraction (raw HTML)
```bash
python3 /Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/playwright_fetch.py <url> --no-extract
```

## Output Format

```
Title: <page title>
URL: <final URL after redirects>
---
<extracted text content>
```

If `--screenshot` is used, an additional line is printed:
```
Screenshot: /tmp/playwright_screenshot_XXXX.png
```

## Error Handling

- Timeout (30s default): exits with code 1, prints error to stderr
- Navigation error: exits with code 1, prints error to stderr
- Invalid URL: exits with code 1
