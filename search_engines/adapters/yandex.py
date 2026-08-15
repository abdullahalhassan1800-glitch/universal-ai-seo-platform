"""Yandex Webmaster adapter.

Yandex has a Webmaster API but access requires a Yandex account + token that we
do not fake. Unless a real token is configured we report data unavailable.
"""

from __future__ import annotations

import os

from ..base import SearchEngineAdapter


class YandexAdapter(SearchEngineAdapter):
    engine_id = "yandex"
    display_name = "Yandex"

    def __init__(self, env: dict | None = None):
        self.env = env or os.environ
        token = self.env.get("YANDEX_TOKEN", "")
        if token:
            self.status = "configured"
            self.reason = "Yandex token configured (API integration pending)"
        else:
            self.status = "unconfigured"
            self.reason = "No official Yandex Webmaster API credentials configured"

    def capabilities(self) -> dict:
        return {k: False for k in (
            "get_keyword_data", "get_ranking_data", "get_search_visibility",
            "get_index_signals", "analyze_serp", "get_search_analytics")}
