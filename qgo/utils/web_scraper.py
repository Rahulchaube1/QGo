# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Web scraper for QGo — fetches URLs and converts to clean text/Markdown."""

from __future__ import annotations

import re


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch a web page and return its content as plain text / Markdown.

    Uses BeautifulSoup to strip HTML and extract readable text.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Cleaned text content suitable for LLM context.
        Empty string if fetching fails.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; QGo/0.1; +https://github.com/Rahulchaube1/QGo)"
            )
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        # If it's plain text or markdown, return as-is
        if "text/plain" in content_type or url.endswith((".md", ".txt", ".rst")):
            return response.text

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "noscript", "iframe", "form"]):
            tag.decompose()

        # Try to find main content area
        main = (
            soup.find("main") or
            soup.find("article") or
            soup.find(id=re.compile(r"content|main|body", re.I)) or
            soup.find(class_=re.compile(r"content|main|article|body", re.I)) or
            soup.body or
            soup
        )

        # Extract text with some structure
        lines: list[str] = []
        for element in main.descendants if main else soup.descendants:
            if not hasattr(element, "name"):
                continue
            if element.name in ("h1", "h2", "h3"):
                text = element.get_text(strip=True)
                if text:
                    level = int(element.name[1])
                    lines.append(f"\n{'#' * level} {text}\n")
            elif element.name in ("p", "li", "td", "th"):
                text = element.get_text(strip=True)
                if text and len(text) > 10:
                    lines.append(text)
            elif element.name == "pre":
                code = element.get_text()
                if code.strip():
                    lines.append(f"\n```\n{code.strip()}\n```\n")
            elif element.name == "a":
                href = element.get("href", "")
                text = element.get_text(strip=True)
                if text and href:
                    lines.append(f"[{text}]({href})")

        result = "\n".join(lines)
        # Collapse multiple blank lines
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    except ImportError:
        return _fetch_plain(url, timeout)
    except Exception as exc:
        return f"[Error fetching {url}: {exc}]"


def fetch_page_info(url: str, timeout: int = 15) -> dict:
    """Fetch a web page and return structured info for browser-view display.

    Returns a dict with: url, title, description, status_code, headings, links, content.
    """
    result: dict = {
        "url": url,
        "title": "",
        "description": "",
        "status_code": 0,
        "headings": [],
        "links": [],
        "content": "",
    }
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; QGo/0.1; +https://github.com/Rahulchaube1/QGo)"
            )
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        result["status_code"] = response.status_code

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        if soup.title:
            result["title"] = soup.title.get_text(strip=True)

        # Meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and isinstance(meta, object) and hasattr(meta, "get"):
            result["description"] = meta.get("content", "")  # type: ignore[union-attr]

        # Headings (h1–h3, max 15)
        headings: list[tuple[int, str]] = []
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(strip=True)
            if text:
                headings.append((int(tag.name[1]), text))
        result["headings"] = headings[:15]

        # Links (max 20)
        links: list[tuple[str, str]] = []
        for a in soup.find_all("a", href=True)[:30]:
            text = a.get_text(strip=True)
            href = a["href"]
            if text and href and not href.startswith("#") and len(links) < 20:
                links.append((text[:60], href))
        result["links"] = links

        # Readable content (reuse existing fetch_url)
        result["content"] = fetch_url(url, timeout)

    except Exception as exc:
        result["content"] = f"[Error loading {url}: {exc}]"

    return result



    """Minimal fallback using only urllib (no requests/bs4)."""
    try:
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QGo/0.1"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(1024 * 1024).decode("utf-8", errors="replace")
    except Exception as exc:
        return f"[Error fetching {url}: {exc}]"


def fetch_image_base64(url: str, timeout: int = 15) -> str | None:
    """Fetch an image URL and return it as a base64 data URL.

    For use with vision-capable models.
    """
    try:
        import base64

        import requests

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/png")
        data = base64.b64encode(response.content).decode("ascii")
        return f"data:{content_type};base64,{data}"
    except Exception:
        return None
