#!/usr/bin/env python3
"""Playwright-based web fetcher for nanobot."""

import argparse
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright


def fetch_page(url: str, screenshot: bool = False, extract: bool = True) -> dict:
    """Fetch a web page using Playwright and extract content.
    
    Args:
        url: The URL to fetch
        screenshot: Whether to save a screenshot
        extract: Whether to extract readable text content
        
    Returns:
        dict with keys: title, url, content (optional), screenshot_path (optional), error (optional)
    """
    result = {"title": None, "url": url, "content": None, "screenshot_path": None, "error": None}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to the URL with 30s timeout
            page.goto(url, timeout=30000)
            
            # Get final URL after redirects
            result["url"] = page.url
            
            # Get page title
            result["title"] = page.title()
            
            if extract:
                # Extract readable text content
                result["content"] = page.evaluate("""
                    () => {
                        // Remove script and style elements
                        const clone = document.body.cloneNode(true);
                        const scripts = clone.querySelectorAll('script, style, noscript');
                        scripts.forEach(el => el.remove());
                        
                        // Get text content
                        let text = clone.textContent || '';
                        
                        // Clean up whitespace
                        text = text.replace(/\\s+/g, ' ').trim();
                        
                        return text;
                    }
                """)
            
            if screenshot:
                # Save screenshot to temp file
                with tempfile.NamedTemporaryFile(
                    suffix=".png", 
                    prefix="playwright_screenshot_", 
                    delete=False
                ) as tmp:
                    tmp_path = tmp.name
                
                page.screenshot(path=tmp_path)
                result["screenshot_path"] = tmp_path
            
            browser.close()
            
    except PlaywrightTimeout as e:
        result["error"] = f"Timeout error: {e}"
    except Exception as e:
        result["error"] = f"Navigation error: {e}"
    
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a web page using Playwright")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--screenshot", action="store_true", help="Save screenshot")
    parser.add_argument("--no-extract", action="store_false", dest="extract", help="Skip text extraction")
    args = parser.parse_args()
    
    result = fetch_page(args.url, screenshot=args.screenshot, extract=args.extract)
    
    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    
    # Print title and URL
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    
    # Print separator and content if extracted
    if result["content"] is not None:
        print("---")
        print(result["content"])
    
    # Print screenshot path if taken
    if result["screenshot_path"]:
        print(f"Screenshot: {result['screenshot_path']}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
