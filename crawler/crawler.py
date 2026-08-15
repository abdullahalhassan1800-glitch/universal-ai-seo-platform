"""Site crawl orchestrator.

Respects robots.txt, crawl-delay and page limits. Uses httpx by default;
optionally renders with Playwright when CRAWLER_RENDER=playwright.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

from .analyzer import UniversalAnalyzer
from .fetcher import fetch
from .parser import PageData, parse_html
from .robots import RobotsTxt
from .scoring import UniversalScorer
from .sitemap import collect_sitemap_urls, discover_sitemaps

DEFAULT_USER_AGENT = "UniversalAI_SEO_Bot/1.0"
DEFAULT_MAX_PAGES = 100
DEFAULT_DELAY = 0.5
MAX_CONCURRENCY = 4


@dataclass
class CrawlResult:
    site_url: str
    robots: RobotsTxt
    sitemap_urls: list[str]
    pages: list[PageData]
    issues: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    skipped_by_robots: int = 0
    errors: list[str] = field(default_factory=list)


async def _render_with_playwright(url: str, timeout: float) -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=DEFAULT_USER_AGENT)
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        html = await page.content()
        await browser.close()
        return html


async def run_crawl(
    site_url: str,
    max_pages: int = DEFAULT_MAX_PAGES,
    delay: float = DEFAULT_DELAY,
    user_agent: str = DEFAULT_USER_AGENT,
    render: str = "httpx",
    render_timeout: float = 15.0,
    follow_sitemap: bool = True,
) -> CrawlResult:
    site_url = site_url.rstrip("/")
    headers = {"User-Agent": user_agent}
    errors: list[str] = []
    pages: list[PageData] = []
    skipped_by_robots = 0

    async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True, max_redirects=5) as client:
        robots_txt = RobotsTxt()
        try:
            resp = await client.get(urljoin(site_url, "/robots.txt"))
            if resp.status_code == 200:
                robots_txt = RobotsTxt.parse(resp.text, user_agent=user_agent)
        except httpx.HTTPError as exc:
            errors.append(f"robots.txt fetch failed: {exc}")

        sitemap_urls: list[str] = []
        sitemap_errors: list[str] = []
        if follow_sitemap:
            try:
                sitemap_urls = await discover_sitemaps(client, site_url, robots_txt)
                sitemap_urls = await collect_sitemap_urls(client, sitemap_urls, max_urls=max_pages * 3)
            except httpx.HTTPError as exc:
                sitemap_errors.append(f"sitemap fetch failed: {exc}")

        queue = [site_url]
        seen: set[str] = set()
        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async def crawl_url(url: str) -> None:
            nonlocal skipped_by_robots
            if not robots_txt.is_allowed(url):
                skipped_by_robots += 1
                return
            try:
                if render == "playwright":
                    try:
                        html = await asyncio.wait_for(_render_with_playwright(url, render_timeout), timeout=render_timeout + 10)
                        page_data = parse_html(html, url, final_url=url, status_code=200, content_type="text/html")
                    except Exception as exc:
                        errors.append(f"render failed {url}: {exc}")
                        return
                else:
                    result = await fetch(client, url)
                    if result.body and ("html" in result.content_type or result.status_code == 200):
                        page_data = parse_html(
                            result.body, result.url, final_url=result.final_url,
                            status_code=result.status_code, redirect_chain=result.redirect_chain,
                            content_type=result.content_type,
                        )
                    else:
                        page_data = PageData(
                            url=result.url, final_url=result.final_url,
                            status_code=result.status_code, error=result.error, content_type=result.content_type,
                        )
            except httpx.HTTPError as exc:
                errors.append(f"fetch failed {url}: {exc}")
                return
            pages.append(page_data)
            if page_data.status_code == 200 and page_data.is_html:
                for link in page_data.internal_links:
                    norm = link.rstrip("/")
                    if urlparse(norm).netloc == urlparse(site_url).netloc and norm not in seen:
                        seen.add(norm)
                        if len(queue) < max_pages * 3:
                            queue.append(norm)

        seen.add(site_url)
        while queue and len(pages) < max_pages:
            batch = []
            while queue and len(batch) < MAX_CONCURRENCY:
                batch.append(queue.pop(0))
            await asyncio.gather(*(crawl_url(u) for u in batch))
            if delay:
                await asyncio.sleep(delay)

        analyzer = UniversalAnalyzer(site_url)
        issues = analyzer.analyze(pages, sitemap_urls=sitemap_urls, sitemap_errors=sitemap_errors)
        scorer = UniversalScorer(pages, issues, site_url)
        scores = scorer.score()

    return CrawlResult(
        site_url=site_url,
        robots=robots_txt,
        sitemap_urls=sitemap_urls,
        pages=pages,
        issues=issues,
        scores=scores,
        skipped_by_robots=skipped_by_robots,
        errors=errors,
    )


def run_crawl_sync(**kwargs) -> CrawlResult:
    return asyncio.run(run_crawl(**kwargs))
