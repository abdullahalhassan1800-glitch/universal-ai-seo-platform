"""Google Search Console adapter (official GSC API, OAuth2).

Only returns real GSC data when credentials are configured.
"""

from __future__ import annotations

import os

import httpx

from ..base import DataUnavailableError, KeywordData, RankingData, SearchEngineAdapter

AUTH_URL = "https://oauth2.googleapis.com/token"
GSC_API = "https://www.googleapis.com/webmasters/v3/sites"


class GoogleAdapter(SearchEngineAdapter):
    engine_id = "google"
    display_name = "Google (Search Console)"

    def __init__(self, env: dict | None = None):
        self.env = env or os.environ
        self.client_id = self.env.get("GSC_CLIENT_ID", "")
        self.client_secret = self.env.get("GSC_CLIENT_SECRET", "")
        self.refresh_token = self.env.get("GSC_REFRESH_TOKEN", "")
        self.site = self.env.get("GSC_SITE", "")
        if self.client_id and self.client_secret and self.refresh_token and self.site:
            self.status = "configured"
            self.reason = "GSC credentials configured"
        else:
            self.status = "unconfigured"
            self.reason = "Set GSC_CLIENT_ID, GSC_CLIENT_SECRET, GSC_REFRESH_TOKEN and GSC_SITE"

    def capabilities(self) -> dict:
        ok = self.status == "configured"
        return {
            "get_keyword_data": False,
            "get_ranking_data": True,
            "get_search_visibility": True,
            "get_index_signals": False,
            "analyze_serp": False,
            "get_search_analytics": True,
        } if ok else {
            "get_keyword_data": False,
            "get_ranking_data": False,
            "get_search_visibility": False,
            "get_index_signals": False,
            "analyze_serp": False,
            "get_search_analytics": False,
        }

    def _access_token(self) -> str:
        resp = httpx.post(AUTH_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }, timeout=30.0)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _search_analytics(self, start_date: str, end_date: str, dimensions: list[str], row_limit: int = 25) -> list[dict]:
        if self.status != "configured":
            raise self._unavailable("get_search_analytics")
        token = self._access_token()
        resp = httpx.post(
            f"{GSC_API}/{self.site}/searchAnalytics/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"startDate": start_date, "endDate": end_date,
                  "dimensions": dimensions, "rowLimit": row_limit},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json().get("rows", [])

    def get_search_analytics(self, start_date: str, end_date: str, **kwargs) -> list[dict]:
        if self.status != "configured":
            raise self._unavailable("get_search_analytics")
        rows = self._search_analytics(start_date, end_date, ["query", "page"])
        out = []
        for row in rows:
            keys = row.get("keys", ["", ""])
            out.append({
                "query": keys[0],
                "page": keys[1],
                "clicks": row.get("clicks"),
                "impressions": row.get("impressions"),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": row.get("position"),
                "search_engine": "google",
            })
        return out

    def get_ranking_data(self, keyword: str, **kwargs) -> list[RankingData]:
        if self.status != "configured":
            raise self._unavailable("get_ranking_data")
        start = kwargs.get("start_date", "28daysAgo")
        end = kwargs.get("end_date", "today")
        rows = self._search_analytics(start, end, ["query", "page", "device"], row_limit=25)
        return [RankingData(
            keyword=row["keys"][0], search_engine="google",
            device=row["keys"][2], position=row.get("position"),
            url=row["keys"][1], source="gsc",
        ) for row in rows if row.get("keys")]

    def get_search_visibility(self, **kwargs) -> dict:
        if self.status != "configured":
            raise self._unavailable("get_search_visibility")
        start = kwargs.get("start_date", "28daysAgo")
        end = kwargs.get("end_date", "today")
        rows = self._search_analytics(start, end, [], row_limit=1)
        if not rows:
            return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": None}
        row = rows[0]
        return {
            "clicks": row.get("clicks"),
            "impressions": row.get("impressions"),
            "ctr": round(row.get("ctr", 0) * 100, 2),
            "position": row.get("position"),
        }
