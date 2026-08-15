"""Search-engine-agnostic adapter interface.

Every adapter exposes the same capability surface. When a search engine has no
official API for a capability, the method raises DataUnavailableError and the
API layer returns: "Data unavailable for this search engine." — never fabricated
metrics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class DataUnavailableError(RuntimeError):
    """Raised when real data cannot be retrieved for a search engine capability."""


@dataclass
class KeywordData:
    keyword: str = ""
    search_engine: str = ""
    volume: int | None = None
    cpc: float | None = None
    difficulty: int | None = None
    intent: str | None = None
    country: str | None = None
    language: str | None = None
    date: str | None = None
    source: str = "unavailable"

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "search_engine": self.search_engine,
            "volume": self.volume,
            "cpc": self.cpc,
            "difficulty": self.difficulty,
            "intent": self.intent,
            "country": self.country,
            "language": self.language,
            "date": self.date,
            "source": self.source,
        }


@dataclass
class RankingData:
    keyword: str = ""
    search_engine: str = ""
    country: str | None = None
    language: str | None = None
    device: str | None = None
    position: int | None = None
    url: str | None = None
    date: str | None = None
    source: str = "unavailable"

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "search_engine": self.search_engine,
            "country": self.country,
            "language": self.language,
            "device": self.device,
            "position": self.position,
            "url": self.url,
            "date": self.date,
            "source": self.source,
        }


class SearchEngineAdapter(ABC):
    engine_id: str = ""
    display_name: str = ""
    status: str = "unconfigured"
    reason: str = ""

    def capabilities(self) -> dict:
        """Map of capability name -> bool. False means no official API configured."""
        return {
            "get_keyword_data": False,
            "get_ranking_data": False,
            "get_search_visibility": False,
            "get_index_signals": False,
            "analyze_serp": False,
            "get_search_analytics": False,
        }

    def _unavailable(self, feature: str) -> DataUnavailableError:
        return DataUnavailableError(f"Data unavailable for this search engine ({feature}).")

    # --- capability surface -------------------------------------------------
    def get_keyword_data(self, keyword: str, **kwargs) -> list[KeywordData]:
        raise self._unavailable("get_keyword_data")

    def get_ranking_data(self, keyword: str, **kwargs) -> list[RankingData]:
        raise self._unavailable("get_ranking_data")

    def get_search_visibility(self, **kwargs) -> dict:
        raise self._unavailable("get_search_visibility")

    def get_index_signals(self, url: str | None = None, **kwargs) -> dict:
        raise self._unavailable("get_index_signals")

    def analyze_serp(self, query: str, **kwargs) -> dict:
        raise self._unavailable("analyze_serp")

    def get_search_analytics(self, start_date: str, end_date: str, **kwargs) -> list[dict]:
        raise self._unavailable("get_search_analytics")

    def to_dict(self) -> dict:
        return {
            "engine_id": self.engine_id,
            "display_name": self.display_name,
            "status": self.status,
            "reason": self.reason,
            "capabilities": self.capabilities(),
        }
