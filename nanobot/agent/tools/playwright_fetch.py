"""Playwright-based web fetch tool for nanobot."""

import subprocess
import sys
from typing import Any, ClassVar

from nanobot.agent.tools.base import Tool


class PlaywrightFetchTool(Tool):
    """Fetch a URL using a headless Chromium browser via Playwright."""

    name = "playwright_fetch"
    description = "Fetch a URL using a headless Chromium browser. Use this when web_fetch returns empty or incomplete content (JS-heavy pages, bot detection, etc.)."
    parameters: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "screenshot": {"type": "boolean", "description": "Whether to save a screenshot", "default": False}
        },
        "required": ["url"]
    }

    async def execute(self, url: str, screenshot: bool = False, **kwargs: Any) -> str:
        """Execute the Playwright fetch tool.

        Args:
            url: The URL to fetch
            screenshot: Whether to save a screenshot (default: False)
            **kwargs: Additional arguments (ignored)

        Returns:
            Extracted text content from the page, or error message
        """
        try:
            cmd = [sys.executable, "/Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/playwright_fetch.py", url]
            if screenshot:
                cmd.append("--screenshot")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if not error_msg:
                    error_msg = result.stdout.strip()
                return f"Error: {error_msg}"

            # Extract the content (everything after the "---" separator)
            output = result.stdout
            if "---" in output:
                content = output.split("---", 1)[1].strip()
            else:
                content = output.strip()

            return content
        except subprocess.TimeoutExpired:
            return "Error: Timeout - page took too long to load"
        except Exception as e:
            return f"Error: {e}"
