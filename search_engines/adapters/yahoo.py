"""Yahoo adapter.

Yahoo search results are powered by Bing; there is no public Yahoo analytics
API. We never fabricate data.
"""

from __future__ import annotations

import os

from ..base import SearchEngineAdapter


class YahooAdapter(SearchEngineAdapter):
    engine_id = "yahoo"
    display_name = "Yahoo"

    def __init__(self, env: dict | None = None):
        self.env = env or os.environ
        self.status = "unavailable"
        self.reason = "Not supported by this search engine (no official analytics API)."

    def capabilities(self) -> dict:
        return {k: False for k in (
            "get_keyword_data", "get_ranking_data", "get_search_visibility",
            "get_index_signals", "analyze_serp", "get_search_analytics")}
