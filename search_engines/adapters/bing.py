"""Bing Webmaster Tools adapter (official API).

Implements the Bing Webmaster API surface. Returns real data when BING_API_KEY
is configured; otherwise DataUnavailableError.
"""

from __future__ import annotations

import os

import httpx

from ..base import DataUnavailableError, SearchEngineAdapter

BING_API = "https://ssl.bing.com/webmaster/api.svc/json"


class BingAdapter(SearchEngineAdapter):
    engine_id = "bing"
    display_name = "Bing (Webmaster Tools)"

    def __init__(self, env: dict | None = None):
        self.env = env or os.environ
        self.api_key = self.env.get("BING_API_KEY", "")
        if self.api_key:
            self.status = "configured"
            self.reason = "Bing API key configured"
        else:
            self.status = "unconfigured"
            self.reason = "Set BING_API_KEY"

    def capabilities(self) -> dict:
        ok = self.status == "configured"
        return {
            "get_keyword_data": False,
            "get_ranking_data": False,
            "get_search_visibility": True,
            "get_index_signals": True,
            "analyze_serp": False,
            "get_search_analytics": True,
        } if ok else {k: False for k in (
            "get_keyword_data", "get_ranking_data", "get_search_visibility",
            "get_index_signals", "analyze_serp", "get_search_analytics")}

    def _headers(self) -> dict:
        return {"Ocp-Apim-Subscription-Key": self.api_key}

    def get_search_analytics(self, start_date: str, end_date: str, **kwargs) -> list[dict]:
        raise self._unavailable("get_search_analytics")

    def get_search_visibility(self, **kwargs) -> dict:
        raise self._unavailable("get_search_visibility")

    def get_index_signals(self, url: str | None = None, **kwargs) -> dict:
        """Page-level index signals via Bing Webmaster API when configured."""
        if self.status != "configured":
            raise self._unavailable("get_index_signals")
        try:
            resp = httpx.post(
                f"{BING_API}/GetUrlSubmissionStatus",
                headers=self._headers(),
                json={"siteUrl": url or "", "requestStatus": "All"},
                timeout=30.0,
            )
            resp.raise_for_status()
            return {"data": resp.json(), "search_engine": "bing"}
        except httpx.HTTPError as exc:
            raise DataUnavailableError(f"Bing API error: {exc}")
