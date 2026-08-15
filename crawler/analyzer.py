"""Universal SEO issue detection and dimension scoring.

Engine-agnostic: findings improve discoverability across search engines.
Never invents data a search engine did not provide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from .parser import PageData


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Issue:
    issue: str
    severity: Severity
    affected_url: str | None
    explanation: str
    recommendation: str
    dimension: str
    ai_solution: str | None = None
    priority: str | None = None
    status: str = "open"

    def to_dict(self) -> dict:
        return {
            "issue": self.issue,
            "severity": self.severity.value,
            "affected_url": self.affected_url,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "dimension": self.dimension,
            "ai_solution": self.ai_solution,
            "priority": self.priority or severity_priority(self.severity),
            "status": self.status,
        }


def severity_priority(severity: Severity) -> str:
    return {
        Severity.CRITICAL: "CRITICAL",
        Severity.HIGH: "HIGH",
        Severity.MEDIUM: "MEDIUM",
        Severity.LOW: "LOW",
    }[severity]


def _short_hash(text: str) -> str:
    import hashlib
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:16]


TITLE_MIN, TITLE_MAX = 10, 70
DESC_MAX = 160
THIN_THRESHOLD = 250


class UniversalAnalyzer:
    """Runs all universal SEO checks over a set of crawled pages."""

    def __init__(self, site_url: str):
        self.site_url = site_url.rstrip("/")
        self.site_origin = urlparse(self.site_url).netloc

    def analyze(self, pages: list[PageData], sitemap_urls: list[str] | None = None,
                sitemap_errors: list[str] | None = None) -> list[Issue]:
        issues: list[Issue] = []
        sitemap_urls = sitemap_urls or []
        sitemap_errors = sitemap_errors or []
        ok = [p for p in pages if p.status_code == 200 and p.is_html]
        content_hashes: dict[str, list[str]] = {}
        title_hashes: dict[str, list[str]] = {}
        meta_hashes: dict[str, list[str]] = {}
        page_urls = [p.final_url.rstrip("/") for p in pages]
        url_set = set(page_urls)
        internal_targets: set[str] = set()
        for p in ok:
            internal_targets.update(u.rstrip("/") for u in p.internal_links)
            if p.title:
                title_hashes.setdefault(_short_hash(p.title.lower()), []).append(p.final_url)
            if p.meta_description:
                meta_hashes.setdefault(_short_hash(p.meta_description.lower()), []).append(p.final_url)
            if p.word_count >= THIN_THRESHOLD:
                content_hashes.setdefault(_short_hash(p.text_content[:2000]), []).append(p.final_url)

        for p in pages:
            issues.extend(self._page_issues(p))
            if p.status_code != 200 or not p.is_html:
                continue
            issues.extend(self._title_duplicates(p, title_hashes))
            issues.extend(self._meta_duplicates(p, meta_hashes))
            issues.extend(self._content_duplicates(p, content_hashes))

        issues.extend(self._site_issues(ok, page_urls, url_set, internal_targets, sitemap_urls, sitemap_errors))
        issues.extend(self._orphan_issues(page_urls, internal_targets))
        return issues

    def _page_issues(self, p: PageData) -> list[Issue]:
        issues: list[Issue] = []
        if p.status_code in (404, 410):
            issues.append(Issue("Broken URL", Severity.HIGH, p.url,
                                f"URL returns HTTP {p.status_code}.",
                                "Remove, restore or redirect this URL to a working page.", "technical"))
        elif p.status_code >= 500:
            issues.append(Issue("Server error", Severity.CRITICAL, p.url,
                                f"URL returns HTTP {p.status_code} — search engines may de-index it.",
                                "Fix the server error; review logs and hosting health.", "technical"))
        elif p.status_code in (301, 302, 307, 308):
            chain = p.redirect_chain
            if len(chain) >= 3:
                issues.append(Issue("Redirect chain", Severity.MEDIUM, p.url,
                                    f"URL chains through {len(chain)} redirects.",
                                    "Update internal links to point to the final URL.", "technical"))
            issues.append(Issue("Redirect detected", Severity.LOW, p.url,
                                "URL redirects instead of serving content directly.",
                                "Link directly to the final URL where possible.", "technical"))
        if p.status_code != 200 or not p.is_html:
            return issues

        if not p.title:
            issues.append(Issue("Missing title", Severity.HIGH, p.url,
                                "Page has no <title> element.",
                                "Add a unique, descriptive title (under 70 chars) describing the page's topic.", "on_page"))
        elif p.title_length > TITLE_MAX:
            issues.append(Issue("Title too long", Severity.MEDIUM, p.url,
                                f"Title is {p.title_length} chars (recommended max {TITLE_MAX}).",
                                "Trim the title so search engines display it fully.", "on_page"))
        elif p.title_length < TITLE_MIN:
            issues.append(Issue("Title too short", Severity.LOW, p.url,
                                f"Title is only {p.title_length} chars.",
                                "Expand the title to be more descriptive.", "on_page"))

        if not p.meta_description:
            issues.append(Issue("Missing meta description", Severity.MEDIUM, p.url,
                                "No meta description present.",
                                "Write a compelling 120-160 char description.", "on_page"))
        elif p.meta_description_length > DESC_MAX:
            issues.append(Issue("Meta description too long", Severity.LOW, p.url,
                                f"Meta description is {p.meta_description_length} chars.",
                                "Shorten it to under 160 chars.", "on_page"))

        if not p.h1:
            issues.append(Issue("Missing H1", Severity.HIGH, p.url,
                                "Page has no H1 heading.",
                                "Add one H1 describing the main topic of the page.", "on_page"))
        elif len(p.h1) > 1:
            issues.append(Issue("Multiple H1 tags", Severity.MEDIUM, p.url,
                                f"Page has {len(p.h1)} H1 elements.",
                                "Keep a single H1; demote the rest to H2.", "on_page"))

        if "noindex" in p.robots_meta:
            issues.append(Issue("Noindex page", Severity.MEDIUM, p.url,
                                "Page is set to noindex — it will not appear in search results.",
                                "Confirm this is intentional; if not, remove the noindex directive.", "indexability"))
        if "nofollow" in p.robots_meta:
            issues.append(Issue("Nofollow page", Severity.LOW, p.url,
                                "Page is set to nofollow.",
                                "Confirm this is intentional.", "indexability"))
        if p.canonical and urlparse(p.canonical).path.rstrip("/") != urlparse(p.final_url).path.rstrip("/"):
            issues.append(Issue("Canonical conflict", Severity.HIGH, p.url,
                                f"Canonical points to {p.canonical} which differs from the page URL.",
                                "Point canonical to the page's own URL or the intended canonical page.", "indexability"))
        if p.canonical is None and p.status_code == 200:
            issues.append(Issue("Missing canonical", Severity.LOW, p.url,
                                "No canonical tag declared.",
                                "Add a self-referencing canonical to prevent duplicate-content signals.", "indexability"))

        if p.word_count and p.word_count < THIN_THRESHOLD:
            issues.append(Issue("Thin content", Severity.MEDIUM, p.url,
                                f"Only {p.word_count} words of text on the page.",
                                f"Expand content to at least {THIN_THRESHOLD} words covering the topic in depth.", "content"))

        if p.images:
            missing_alt = [i for i in p.images if not i["alt"]]
            if missing_alt and len(missing_alt) == len(p.images):
                issues.append(Issue("Images missing alt text", Severity.MEDIUM, p.url,
                                    f"All {len(p.images)} images lack alt attributes.",
                                    "Add descriptive alt text to every image.", "on_page"))
            elif missing_alt:
                issues.append(Issue("Some images missing alt text", Severity.LOW, p.url,
                                    f"{len(missing_alt)} of {len(p.images)} images lack alt attributes.",
                                    "Add alt text to the missing images.", "on_page"))

        if not p.internal_links and p.h1:
            issues.append(Issue("Page has no internal links", Severity.MEDIUM, p.url,
                                "This page links to no other pages on the site.",
                                "Add contextual internal links to related pages.", "internal_linking"))

        if not p.structured_data:
            issues.append(Issue("Missing structured data", Severity.LOW, p.url,
                                "No JSON-LD structured data found.",
                                "Add schema.org markup relevant to the page type (e.g. Article, Product, FAQ).", "structured_data"))

        if len(p.h2) == 0 and len(p.h3) == 0:
            issues.append(Issue("No subheadings", Severity.MEDIUM, p.url,
                                "Page has no H2/H3 headings.",
                                "Structure content with descriptive subheadings.", "content"))

        return issues

    def _title_duplicates(self, p: PageData, title_hashes: dict[str, list[str]]) -> list[Issue]:
        if not p.title:
            return []
        group = title_hashes.get(_short_hash(p.title.lower()), [])
        if len(group) > 1 and p.final_url == group[0]:
            others = ", ".join(group[1:4])
            return [Issue("Duplicate title", Severity.MEDIUM, p.final_url,
                          f"Same title used on {len(group)} pages (e.g. {others}).",
                          "Give each page a unique title targeting its specific topic.", "on_page")]
        return []

    def _meta_duplicates(self, p: PageData, meta_hashes: dict[str, list[str]]) -> list[Issue]:
        if not p.meta_description:
            return []
        group = meta_hashes.get(_short_hash(p.meta_description.lower()), [])
        if len(group) > 1 and p.final_url == group[0]:
            return [Issue("Duplicate meta description", Severity.LOW, p.final_url,
                          f"Same meta description on {len(group)} pages.",
                          "Write unique descriptions per page.", "on_page")]
        return []

    def _content_duplicates(self, p: PageData, content_hashes: dict[str, list[str]]) -> list[Issue]:
        if p.word_count < THIN_THRESHOLD:
            return []
        group = content_hashes.get(_short_hash(p.text_content[:2000]), [])
        if len(group) > 1 and p.final_url == group[0]:
            return [Issue("Duplicate content", Severity.HIGH, p.final_url,
                          f"Near-identical content found on {len(group)} pages.",
                          "Merge or differentiate the pages; use canonical/redirect where appropriate.", "content")]
        return []

    def _site_issues(self, ok_pages: list[PageData], page_urls: list[str], url_set: set[str],
                     internal_targets: set[str], sitemap_urls: list[str], sitemap_errors: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        if sitemap_errors:
            issues.append(Issue("Sitemap problem", Severity.HIGH, None,
                                f"Sitemap could not be parsed: {'; '.join(sitemap_errors[:3])}",
                                "Fix the sitemap XML so search engines can discover URLs.", "indexability"))
        elif not sitemap_urls:
            issues.append(Issue("No sitemap found", Severity.MEDIUM, None,
                                "No XML sitemap was discovered at the site.",
                                "Create and submit a sitemap listing your canonical URLs.", "indexability"))
        else:
            missing_in_sitemap = [u for u in url_set if u not in sitemap_urls]
            if len(missing_in_sitemap) > max(3, len(url_set) // 3):
                issues.append(Issue("Sitemap incomplete", Severity.MEDIUM, None,
                                    f"{len(missing_in_sitemap)} of {len(url_set)} crawled URLs are not listed in the sitemap.",
                                    "Ensure the sitemap lists all indexable, canonical URLs.", "indexability"))

        broken_targets = sorted(internal_targets - url_set)
        if broken_targets:
            shown = ", ".join(broken_targets[:5])
            issues.append(Issue("Broken internal links", Severity.HIGH, broken_targets[0],
                                f"{len(broken_targets)} internal link target(s) returned an error or were not reachable (e.g. {shown}).",
                                "Fix or redirect the broken internal targets.", "technical"))
        return issues

    def _orphan_issues(self, page_urls: list[str], internal_targets: set[str]) -> list[Issue]:
        issues: list[Issue] = []
        if not page_urls:
            return issues
        orphans = [u for u in page_urls if u not in internal_targets]
        if len(orphans) > max(2, len(page_urls) // 10):
            issues.append(Issue("Orphan pages", Severity.MEDIUM, orphans[0],
                                f"{len(orphans)} of {len(page_urls)} pages have no internal links pointing to them.",
                                "Add internal links from relevant pages to each orphan.", "internal_linking"))
        elif orphans:
            issues.append(Issue("Orphan pages", Severity.LOW, orphans[0],
                                f"{len(orphans)} page(s) have no internal links pointing to them.",
                                "Add internal links from relevant pages to each orphan.", "internal_linking"))
        return issues
