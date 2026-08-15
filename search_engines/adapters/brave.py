"""Brave adapter. analyze_serp uses the official Brave Search API when BRAVE_API_KEY
is configured. All other capabilities report data unavailable."""

from __future__ import annotations

import os

import httpx

from ..base import SearchEngineAdapter


class BraveAdapter(SearchEngineAdapter):
    engine_id = "brave"
    display_name = "Brave Search"

    def __init__(self, env: dict | None = None):
        self.env = env or os.environ
        self.api_key = self.env.get("BRAVE_API_KEY", "")
        if self.api_key:
            self.status = "configured"
            self.reason = "Brave Search API key configured"
        else:
            self.status = "unconfigured"
            self.reason = "Set BRAVE_API_KEY for SERP analysis"

    def capabilities(self) -> dict:
        ok = self.status == "configured"
        return {
            "get_keyword_data": False,
            "get_ranking_data": False,
            "get_search_visibility": False,
            "get_index_signals": False,
            "analyze_serp": ok,
            "get_search_analytics": False,
        }

    def analyze_serp(self, query: str, **kwargs) -> dict:
        if self.status != "configured":
            raise self._unavailable("analyze_serp")
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": kwargs.get("count", 10)},
            headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [{
            "title": r.get("title"),
            "url": r.get("url"),
            "description": r.get("description"),
            "position": idx + 1,
        } for idx, r in enumerate(data.get("web", {}).get("results", []))]
        return {"query": query, "search_engine": "brave", "results": results, "source": "brave-search-api"}
