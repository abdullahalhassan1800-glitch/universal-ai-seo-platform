"""AI provider abstraction.

Supports NVIDIA Nemotron (OpenAI-compatible), OpenAI-compatible APIs,
Google Gemini and local Ollama/llama.cpp/vLLM endpoints.

The system works without any AI provider: every method degrades to a clear
"AI unavailable" signal so callers can fall back to rule-based logic.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod

import httpx

PROVIDER_OPTIONS = ("nvidia", "openai", "gemini", "ollama")


class AiUnavailableError(RuntimeError):
    pass


def _extract_json(text: str) -> dict | list:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise AiUnavailableError("Model output was not valid JSON")


class AIProvider(ABC):
    """Interface every provider implements (generate/analyze/classify/embed/rank/plan/tool_call)."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        ...

    def analyze(self, text: str, instructions: str, system: str | None = None) -> dict:
        prompt = f"{instructions}\n\nText:\n{text}\n\nReturn your answer as JSON."
        return self._json(prompt, system=system)

    def classify(self, items: list[str], labels: list[str], system: str | None = None) -> dict:
        prompt = (
            f"Classify each item into exactly one of these labels: {json.dumps(labels)}.\n"
            f"Return a JSON object mapping each item string to a label string.\nItems: {json.dumps(items)}"
        )
        return self._json(prompt, system=system)

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        return None

    def rank(self, items: list[str], criteria: str, system: str | None = None) -> list:
        prompt = (
            f"Rank these items by: {criteria}.\nReturn a JSON array of {json.dumps(items)} "
            "ordered from most to least important."
        )
        result = self._json(prompt, system=system)
        if isinstance(result, list):
            return result
        return items

    def plan(self, context: str, system: str | None = None) -> list:
        prompt = (
            f"Create an actionable SEO action plan from this context.\n"
            f"Return a JSON array of objects: {{\"title\", \"priority\" (CRITICAL/HIGH/MEDIUM/LOW), "
            f"\"impact\" (0-100), \"difficulty\" (0-100), \"urgency\" (0-100), \"confidence\" (0-100), \"description\"}}.\n"
            f"Context:\n{context}"
        )
        result = self._json(prompt, system=system)
        return result if isinstance(result, list) else []

    def tool_call(self, spec: dict, arguments: dict) -> dict:
        prompt = (
            f"You are calling a tool. Tool spec: {json.dumps(spec)}\nArguments: {json.dumps(arguments)}\n"
            "Return a JSON object with a 'result' field."
        )
        return self._json(prompt)

    def _json(self, prompt: str, system: str | None = None) -> dict | list:
        text = self.generate(prompt, system=system)
        return _extract_json(text)


class OpenAICompatProvider(AIProvider):
    """NVIDIA Nemotron, OpenAI and any OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str, small_model: str | None = None, name: str = "openai"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._small_model = small_model or model
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": model or self._model, "messages": messages, "temperature": 0.2},
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    @property
    def name(self) -> str:
        return "gemini"

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system + "\n---\n"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or self._model}:generateContent"
        resp = httpx.post(url, params={"key": self._api_key}, json={"contents": contents}, timeout=120.0)
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if not candidates:
            raise AiUnavailableError("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str, small_model: str | None = None):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._small_model = small_model or model

    @property
    def name(self) -> str:
        return "ollama"

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        payload: dict = {"model": model or self._model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        resp = httpx.post(f"{self._base_url}/api/generate", json=payload, timeout=600.0)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        resp = httpx.post(f"{self._base_url}/api/embed", json={"model": self._model, "input": texts}, timeout=120.0)
        resp.raise_for_status()
        return resp.json().get("embeddings")


class UnavailableProvider(AIProvider):
    @property
    def name(self) -> str:
        return "unavailable"

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        raise AiUnavailableError("No AI provider configured. Set AI_PROVIDER and the provider's API key.")


def load_provider_from_env(env: dict | None = None) -> AIProvider:
    """Build a provider from environment variables. Returns UnavailableProvider when not configured."""
    env = env if env is not None else os.environ
    provider = (env.get("AI_PROVIDER") or "none").strip().lower()
    if provider == "none" or not provider:
        return UnavailableProvider()

    if provider == "nvidia":
        key = env.get("NVIDIA_API_KEY", "")
        base = env.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = env.get("AI_MODEL") or env.get("NVIDIA_MODEL", "")
        if not key or not model:
            return UnavailableProvider()
        return OpenAICompatProvider(key, base, model, env.get("AI_SMALL_MODEL"), name="nvidia")

    if provider == "openai":
        key = env.get("OPENAI_API_KEY", "")
        base = env.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = env.get("AI_MODEL", "")
        if not key or not model:
            return UnavailableProvider()
        return OpenAICompatProvider(key, base, model, env.get("AI_SMALL_MODEL"), name="openai")

    if provider == "gemini":
        key = env.get("GEMINI_API_KEY", "")
        model = env.get("AI_MODEL", "")
        if not key or not model:
            return UnavailableProvider()
        return GeminiProvider(key, model)

    if provider == "ollama":
        base = env.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = env.get("AI_MODEL", "")
        if not model:
            return UnavailableProvider()
        return OllamaProvider(base, model, env.get("AI_SMALL_MODEL"))

    return UnavailableProvider()
