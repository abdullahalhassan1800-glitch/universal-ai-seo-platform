"""Sitemap fetching and parsing."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import httpx

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def parse_sitemap(text: str, base_url: str) -> dict:
    """Parse a sitemap (or sitemap index) body.

    Returns {"urls": [...], "sub_sitemaps": [...], "errors": [...]}.
    """
    urls: list[str] = []
    sub_sitemaps: list[str] = []
    errors: list[str] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return {"urls": [], "sub_sitemaps": [], "errors": [f"XML parse error: {exc}"]}
    if root is None:
        return {"urls": [], "sub_sitemaps": [], "errors": ["Empty document"]}
    tag = root.tag.rsplit("}", 1)[-1]
    for child in root.iter():
        name = child.tag.rsplit("}", 1)[-1]
        text_val = (child.text or "").strip()
        if name == "loc" and text_val:
            target = urljoin(base_url, text_val)
            if tag == "urlset":
                urls.append(target)
            elif tag == "sitemapindex":
                sub_sitemaps.append(target)
    return {"urls": urls, "sub_sitemaps": sub_sitemaps, "errors": errors}


async def discover_sitemaps(client: httpx.AsyncClient, base_url: str, robots: object) -> list[str]:
    """Discover sitemap URLs from robots.txt and common locations."""
    candidates: list[str] = []
    sitemaps = getattr(robots, "sitemaps", []) or []
    candidates.extend(sitemaps)
    candidates.append(urljoin(base_url, "sitemap.xml"))
    candidates.append(urljoin(base_url, "sitemap_index.xml"))
    candidates.append(urljoin(base_url, "sitemap-index.xml"))
    found: list[str] = []
    seen: set[str] = set()
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith(("application/xml", "text/xml")):
                found.append(url)
        except httpx.HTTPError:
            continue
    return found


async def collect_sitemap_urls(client: httpx.AsyncClient, sitemap_urls: list[str], max_urls: int = 1000) -> list[str]:
    """Fetch and flatten sitemap index trees into a URL list."""
    urls: list[str] = []
    queue = list(sitemap_urls)
    while queue and len(urls) < max_urls:
        url = queue.pop(0)
        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                continue
            data = parse_sitemap(resp.text, url)
            urls.extend(data["urls"])
            queue.extend(data["sub_sitemaps"][: max_urls - len(urls)])
        except httpx.HTTPError:
            continue
    return urls[:max_urls]
