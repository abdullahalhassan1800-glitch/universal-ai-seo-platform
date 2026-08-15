"""Search engine adapter registry."""

from __future__ import annotations

from .adapters.google import GoogleAdapter
from .adapters.bing import BingAdapter
from .adapters.yandex import YandexAdapter
from .adapters.brave import BraveAdapter
from .adapters.duckduckgo import DuckDuckGoAdapter
from .adapters.yahoo import YahooAdapter

ENGINE_IDS = ("google", "bing", "yandex", "brave", "duckduckgo", "yahoo")

ADAPTER_CLASSES = {
    "google": GoogleAdapter,
    "bing": BingAdapter,
    "yandex": YandexAdapter,
    "brave": BraveAdapter,
    "duckduckgo": DuckDuckGoAdapter,
    "yahoo": YahooAdapter,
}


def list_engines() -> list[dict]:
    return [cls().to_dict() for cls in ADAPTER_CLASSES.values()]


def get_adapter(engine_id: str, env: dict | None = None):
    cls = ADAPTER_CLASSES.get(engine_id)
    if cls is None:
        raise KeyError(f"Unknown search engine: {engine_id}")
    return cls(env=env)
