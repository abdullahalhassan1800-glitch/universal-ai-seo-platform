"""Universal SEO scoring (0-100) from crawled page data.

Scores every dimension a search engine could care about. Dimensions with no
data are reported as None (frontend shows "Data unavailable") and are excluded
from the weighted universal score.
"""

from __future__ import annotations

from collections import Counter

from .analyzer import Severity
from .parser import PageData

WEIGHTS = {
    "technical": 0.15,
    "content": 0.15,
    "on_page": 0.15,
    "internal_linking": 0.15,
    "indexability": 0.15,
    "structured_data": 0.10,
    "performance": 0.10,
    "authority_opportunity": 0.05,
}

SEVERITY_WEIGHT = {
    Severity.CRITICAL: 1.0,
    Severity.HIGH: 0.6,
    Severity.MEDIUM: 0.3,
    Severity.LOW: 0.1,
}


class UniversalScorer:
    def __init__(self, pages: list[PageData], issues: list, site_url: str):
        self.pages = pages
        self.issues = issues
        self.site_url = site_url.rstrip("/")

    def score(self) -> dict:
        dims = {
            "technical": self._technical(),
            "content": self._content(),
            "on_page": self._on_page(),
            "internal_linking": self._internal_linking(),
            "indexability": self._indexability(),
            "structured_data": self._structured_data(),
            "performance": self._performance(),
            "authority_opportunity": None,
        }
        available = {k: v for k, v in dims.items() if v is not None}
        available_w = {k: WEIGHTS[k] for k in available}
        total_w = sum(available_w.values()) or 1.0
        universal = round(sum(available[k] * w for k, w in available_w.items()) / total_w)
        return {
            "universal_seo_score": universal,
            "dimensions": dims,
            "weights": WEIGHTS,
            "issue_counts": self._issue_counts(),
            "page_count": len(self.pages),
        }

    def _issue_counts(self) -> dict:
        counts: dict[str, int] = {}
        for issue in self.issues:
            sev = issue.severity if isinstance(issue.severity, str) else issue.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def _penalty(self, dimension: str) -> float:
        total = sum(SEVERITY_WEIGHT.get(i.severity if isinstance(i.severity, Severity) else Severity(i.severity), 0.3)
                    for i in self.issues if i.dimension == dimension)
        return min(1.0, total / max(1, len(self.pages)))

    def _technical(self) -> int:
        if not self.pages:
            return None  # type: ignore[return-value]
        ok = sum(1 for p in self.pages if p.status_code == 200)
        base = 100 * ok / len(self.pages)
        penalty = self._penalty("technical")
        return max(0, round(base * (1 - 0.7 * penalty)))

    def _content(self) -> int:
        if not self.pages:
            return None  # type: ignore[return-value]
        html = [p for p in self.pages if p.status_code == 200 and p.is_html]
        if not html:
            return 0
        avg_words = sum(p.word_count for p in html) / len(html)
        word_score = min(100, avg_words / 500 * 100)
        penalty = self._penalty("content")
        return max(0, round(word_score * (1 - 0.6 * penalty)))

    def _on_page(self) -> int:
        html = [p for p in self.pages if p.status_code == 200 and p.is_html]
        if not html:
            return 0
        scores = []
        for p in html:
            s = 0
            s += 35 if p.title else 0
            s += 25 if p.meta_description else 0
            s += 25 if p.h1 else 0
            s += 15 if (p.og_title and p.og_description) else 0
            scores.append(s)
        base = sum(scores) / len(scores)
        penalty = self._penalty("on_page")
        return max(0, round(base * (1 - 0.5 * penalty)))

    def _internal_linking(self) -> int:
        html = [p for p in self.pages if p.status_code == 200 and p.is_html]
        if not html:
            return 0
        avg_links = sum(len(p.internal_links) for p in html) / len(html)
        base = min(100, avg_links / 5 * 100)
        penalty = self._penalty("internal_linking")
        return max(0, round(base * (1 - 0.6 * penalty)))

    def _indexability(self) -> int:
        html = [p for p in self.pages if p.status_code == 200 and p.is_html]
        if not html:
            return 0
        not_noindex = sum(1 for p in html if "noindex" not in p.robots_meta)
        base = 100 * not_noindex / len(html)
        penalty = self._penalty("indexability")
        return max(0, round(base * (1 - 0.7 * penalty)))

    def _structured_data(self) -> int:
        html = [p for p in self.pages if p.status_code == 200 and p.is_html]
        if not html:
            return 0
        with_schema = sum(1 for p in html if p.structured_data)
        return round(100 * with_schema / len(html))

    def _performance(self) -> int:
        """Lightweight proxy: pages that are renderable HTML with manageable payload."""
        html = [p for p in self.pages if p.status_code == 200]
        if not html:
            return 0
        avg_size = sum(p.html_size_bytes for p in html) / len(html) / 1024  # KB
        if avg_size <= 100:
            base = 100
        elif avg_size <= 300:
            base = 75
        elif avg_size <= 800:
            base = 50
        else:
            base = 25
        return round(base)
