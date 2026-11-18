"""Web search and page content extraction tools inspired by OpenJarvis.
Provides keyless live web search and SSRF-protected page content retrieval.
"""
from __future__ import annotations

import ipaddress
import logging
import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

YOUCOM_KEYLESS_SEARCH_URL = "https://api.you.com/v1/agents/search"
YOUCOM_KEYED_SEARCH_URL = "https://api.you.com/v1/search"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# SSRF Blocked IP ranges
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / cloud metadata (AWS/Azure/GCP)
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def check_ssrf(url: str) -> Optional[str]:
    """Verify that a URL does not resolve to private or cloud metadata IPs."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"Blocked: Unsupported URL scheme '{parsed.scheme}'."
        hostname = parsed.hostname
        if not hostname:
            return "Blocked: Missing hostname in URL."

        # Check raw IP
        try:
            ip = ipaddress.ip_address(hostname)
            for net in _BLOCKED_NETWORKS:
                if ip in net:
                    return f"SSRF Blocked: URL points to restricted private/local address {ip}."
        except ValueError:
            pass  # It's a domain name, acceptable for external web calls

        # Disallow cloud metadata endpoints
        if hostname.lower() in ("169.254.169.254", "metadata.google.internal", "instance-data"):
            return "SSRF Blocked: Direct access to cloud instance metadata is forbidden."

        return None
    except Exception as e:
        return f"Invalid URL: {str(e)}"


def web_search(query: str, max_results: int = 5) -> str:
    """Execute live web search across multiple search engines.
    Prefers You.com keyless tier (zero config), with fallbacks to Tavily or DuckDuckGo.
    """
    query = query.strip()
    if not query:
        return "Search query cannot be empty."

    max_results = min(max(1, max_results), 10)

    # 1. Try Tavily if API key is present
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily_key:
        try:
            resp = httpx.post(
                TAVILY_SEARCH_URL,
                json={"api_key": tavily_key, "query": query, "max_results": max_results},
                timeout=12.0
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    formatted = []
                    for item in results:
                        formatted.append(f"### {item.get('title', 'Untitled')}\nURL: {item.get('url')}\n{item.get('content')}")
                    return "\n\n---\n\n".join(formatted)
        except Exception as e:
            logger.warning(f"Tavily search failed, trying You.com: {e}")

    # 2. Try You.com (Keyless or Keyed)
    you_key = os.getenv("YOUDOTCOM_API_KEY", "").strip()
    url = YOUCOM_KEYED_SEARCH_URL if you_key else YOUCOM_KEYLESS_SEARCH_URL
    headers = {"Accept": "application/json", "User-Agent": "JARVIS-Core/3.0"}
    if you_key:
        headers["X-API-Key"] = you_key

    try:
        resp = httpx.get(
            url,
            params={"query": query, "count": max_results},
            headers=headers,
            timeout=12.0
        )
        if resp.status_code == 200:
            data = resp.json()
            web_items = data.get("results", {}).get("web", [])
            news_items = data.get("results", {}).get("news", [])
            items = (web_items + news_items)[:max_results]
            if items:
                formatted = []
                for item in items:
                    title = item.get("title", "Untitled")
                    link = item.get("url", "")
                    snippets = item.get("snippets", [])
                    desc = item.get("description", "")
                    content = "\n".join(snippets) if snippets else desc
                    formatted.append(f"### {title}\nURL: {link}\nSummary: {content}")
                return "\n\n---\n\n".join(formatted)
    except Exception as e:
        logger.warning(f"You.com search failed: {e}")

    # 3. Last resort: DuckDuckGo Search
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query, max_results=max_results))
            if ddg_results:
                formatted = []
                for r in ddg_results:
                    formatted.append(f"### {r.get('title', 'Untitled')}\nURL: {r.get('href')}\nSummary: {r.get('body')}")
                return "\n\n---\n\n".join(formatted)
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")

    return f"No search results found for query: '{query}'."


def fetch_web_page(url: str, max_chars: int = 5000) -> str:
    """Fetch external web page content and return clean, readable markdown text.
    Protects against SSRF and oversized responses.
    """
    url = url.strip()
    ssrf_err = check_ssrf(url)
    if ssrf_err:
        return ssrf_err

    try:
        with httpx.Client(
            follow_redirects=True,
            max_redirects=5,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 JARVIS/3.0"}
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "application/pdf" in content_type:
                return f"[Document points to a PDF ({url}). Use read_pdf tool to inspect it.]"

            html = resp.text
            # Remove scripts, styles, forms, and svgs
            html = re.sub(r"<(script|style|svg|form)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text = re.sub(r"<[^>]+>", " ", html)
            # Collapse whitespace
            text = re.sub(r"\s+", " ", text).strip()

            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[Content truncated at {max_chars} characters. Full URL: {url}]"

            return f"**Source:** {url}\n\n{text}"
    except Exception as e:
        return f"Failed to fetch web page '{url}': {str(e)}"
