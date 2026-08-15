"""HTML parsing into structured page data with BeautifulSoup."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[\w']+")

DEFAULT_MIN_WORDS = 250


@dataclass
class PageData:
    url: str
    final_url: str
    status_code: int
    redirect_chain: list[str] = field(default_factory=list)
    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    canonical: str | None = None
    robots_meta: list[str] = field(default_factory=list)
    og_title: str | None = None
    og_description: str | None = None
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    structured_data: list[dict] = field(default_factory=list)
    text_content: str = ""
    word_count: int = 0
    html_size_bytes: int = 0
    content_type: str = ""
    error: str | None = None
    is_html: bool = False


def _normalize_url(current: str, link: str) -> str | None:
    link = link.strip()
    if not link or link.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    return urljoin(current, link)


def _is_same_origin(a: str, b: str) -> bool:
    return urlparse(a).netloc == urlparse(b).netloc


def extract_jsonld(soup: BeautifulSoup) -> list[dict]:
    blocks: list[dict] = []
    for script in soup.find_all("script", type=lambda t: t and "application/ld+json" in t):
        raw = script.string or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # may be multiple objects concatenated
            continue
        if isinstance(data, list):
            blocks.extend(data)
        else:
            blocks.append(data)
    return blocks


def parse_html(html: str, url: str, final_url: str = "", status_code: int = 200,
               redirect_chain: list[str] | None = None, content_type: str = "") -> PageData:
    soup = BeautifulSoup(html, "lxml")
    final = final_url or url

    title_tag = soup.title
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_desc = None
    canonical = None
    robots_meta: list[str] = []
    og_title = None
    og_description = None
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or "").strip().lower()
        prop = (meta.get("property") or "").strip().lower()
        content = (meta.get("content") or "").strip()
        charset = (meta.get("charset") or "").lower()
        if name == "description":
            meta_desc = content
        elif name == "robots":
            robots_meta.extend([p.strip() for p in content.split(",") if p.strip()])
        elif name == "googlebot":
            robots_meta.extend([p.strip() for p in content.split(",") if p.strip()])
        elif prop == "og:title":
            og_title = content
        elif prop == "og:description":
            og_description = content
        elif name == "canonical":
            canonical = content

    canonical_tag = soup.find("link", rel=lambda r: r and "canonical" in str(r).lower())
    if canonical_tag and canonical_tag.get("href"):
        canonical = urljoin(final, canonical_tag["href"])

    h1 = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
    h2 = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
    h3 = [h.get_text(strip=True) for h in soup.find_all("h3") if h.get_text(strip=True)]

    internal: list[str] = []
    external: list[str] = []
    for a in soup.find_all("a", href=True):
        href = _normalize_url(final, a["href"])
        if href is None:
            continue
        if _is_same_origin(final, href):
            internal.append(href)
        else:
            external.append(href)

    images: list[dict] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        src = urljoin(final, src)
        alt = (img.get("alt") or "").strip()
        images.append({"src": src, "alt": alt})

    structured_data = extract_jsonld(soup)

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text_content = soup.get_text(separator=" ")
    text_content = re.sub(r"\s+", " ", text_content).strip()
    word_count = len(WORD_RE.findall(text_content))

    return PageData(
        url=url,
        final_url=final,
        status_code=status_code,
        redirect_chain=redirect_chain or [],
        title=title,
        title_length=len(title) if title else 0,
        meta_description=meta_desc,
        meta_description_length=len(meta_desc) if meta_desc else 0,
        h1=h1,
        h2=h2,
        h3=h3,
        canonical=canonical,
        robots_meta=robots_meta,
        og_title=og_title,
        og_description=og_description,
        internal_links=internal,
        external_links=external,
        images=images,
        structured_data=structured_data,
        text_content=text_content,
        word_count=word_count,
        html_size_bytes=len(html.encode("utf-8", errors="ignore")),
        content_type=content_type,
        is_html="html" in content_type,
    )
