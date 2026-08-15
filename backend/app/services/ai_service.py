"""AI orchestration service: provider access + rule-based fallbacks."""

from __future__ import annotations

import os
import re
import threading

from ai import AiUnavailableError, AIProvider, load_provider_from_env
from ai.prompts import (
    AUDIT_SOLUTION_PROMPT,
    CLUSTER_PROMPT,
    INTENT_PROMPT,
    PRIORITY_PROMPT,
)
from crawler.analyzer import Issue

_lock = threading.Lock()
_cached: AIProvider | None = None
_cached_env: dict = {}


def get_provider(env: dict | None = None) -> AIProvider:
    """Return the configured AI provider (cached per env), or UnavailableProvider."""
    global _cached, _cached_env
    env = env if env is not None else os.environ
    key = (env.get("AI_PROVIDER"), env.get("AI_MODEL"), env.get("NVIDIA_API_KEY"),
           env.get("OPENAI_API_KEY"), env.get("GEMINI_API_KEY"), env.get("OLLAMA_BASE_URL"))
    with _lock:
        if _cached is not None and _cached_env.get("_key") == key:
            return _cached
        provider = load_provider_from_env(env)
        _cached_env = {"_key": key}
        _cached = provider
        return provider


def ai_available(env: dict | None = None) -> bool:
    provider = get_provider(env)
    return not isinstance(provider, type(get_provider(env))) or provider.name != "unavailable"


def _call(operation: str, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except AiUnavailableError as exc:
        raise
    except Exception as exc:  # any provider/network failure degrades gracefully
        raise AiUnavailableError(f"AI provider error during {operation}: {exc}")


def enrich_issues_with_ai(issues: list[Issue]) -> list[Issue]:
    """Attach an AI-written recommended solution to each issue."""
    provider = get_provider()
    if provider.name == "unavailable":
        return issues
    enriched = []
    for issue in issues[:25]:
        try:
            prompt = AUDIT_SOLUTION_PROMPT.format(
                issue=issue.issue,
                explanation=issue.explanation,
                recommendation=issue.recommendation,
                url=issue.affected_url or "site-wide",
                dimension=issue.dimension,
            )
            result = _call("audit-solution", provider.analyze, issue.explanation or issue.issue, prompt)
            solution = result.get("ai_solution") or result.get("solution") or result.get("recommendation")
            issue.ai_solution = solution
        except AiUnavailableError:
            issue.ai_solution = None
        enriched.append(issue)
    return enriched


def classify_keyword_intent(keywords: list[str]) -> dict[str, str]:
    """Search-intent classification. Uses AI when available, rule-based otherwise."""
    provider = get_provider()
    if provider.name != "unavailable":
        try:
            result = _call("intent", provider.classify, keywords,
                           ["informational", "commercial", "transactional", "navigational", "local"])
            if isinstance(result, dict):
                mapping = {}
                for k, v in result.items():
                    if isinstance(v, str):
                        mapping[k] = v.lower() if v.lower() in ("informational", "commercial", "transactional", "navigational", "local") else "informational"
                if mapping:
                    return mapping
        except AiUnavailableError:
            pass
    return {k: _rule_intent(k) for k in keywords}


def _rule_intent(keyword: str) -> str:
    k = keyword.lower().strip()
    local_words = ("near me", "nearby", " in ", " city", "town", "area", "zip", "postcode")
    tx_words = ("buy", "order", "purchase", "price", "cheap", "discount", "deal", "sale", "subscribe", "sign up", "coupon")
    nav_words = ("login", "log in", "sign in", "my account", "dashboard", "homepage", " contact ", "download app")
    cm_words = ("best", "top", "review", "compare", "vs", "alternative", "reviews", "rating")
    if any(w in k for w in local_words):
        return "local"
    if any(w in k for w in tx_words):
        return "transactional"
    if any(w in k for w in nav_words):
        return "navigational"
    if any(w in k for w in cm_words):
        return "commercial"
    return "informational"


def cluster_keywords(keywords: list[str], intents: dict[str, str] | None = None) -> list[dict]:
    """Cluster keywords into topic clusters. AI when available, rule-based otherwise."""
    intents = intents or {}
    provider = get_provider()
    if provider.name != "unavailable" and len(keywords) >= 2:
        try:
            result = _call("cluster", provider._json, CLUSTER_PROMPT.format(keywords=keywords))
            if isinstance(result, list):
                clusters = []
                for item in result:
                    if isinstance(item, dict) and item.get("name"):
                        members = item.get("keywords") or []
                        clusters.append({
                            "name": item["name"],
                            "topic": item.get("topic"),
                            "intent": item.get("intent"),
                            "keywords": members if isinstance(members, list) else [],
                        })
                if clusters:
                    return clusters
        except AiUnavailableError:
            pass
    return _rule_clusters(keywords, intents)


def _rule_clusters(keywords: list[str], intents: dict[str, str]) -> list[dict]:
    def tokens(kw: str) -> set:
        stop = {"for", "the", "and", "how", "to", "of", "in", "best", "what", "is", "a"}
        return {t for t in re.findall(r"[a-z0-9]+", kw.lower()) if t not in stop}

    groups: list[dict] = []
    used: set[int] = set()
    for i, kw in enumerate(keywords):
        if i in used:
            continue
        members = [kw]
        used.add(i)
        ti = tokens(kw)
        for j in range(i + 1, len(keywords)):
            if j in used:
                continue
            tj = tokens(keywords[j])
            if ti and tj and len(ti & tj) >= max(1, min(len(ti), len(tj)) // 2):
                members.append(keywords[j])
                used.add(j)
        if not members:
            continue
        name = min(members, key=len)
        intent = next((intents[m] for m in members if intents.get(m)), None)
        groups.append({"name": name, "topic": name, "intent": intent, "keywords": members})
    return groups


def prioritize_tasks(tasks: list[dict]) -> list[dict]:
    """AI priority engine: assign impact/difficulty/urgency/confidence and order."""
    provider = get_provider()
    if provider.name == "unavailable":
        return _rule_priorities(tasks)
    try:
        context = "\n".join(f"- {t['title']} ({t.get('priority', 'MEDIUM')})" for t in tasks[:30])
        plan = _call("plan", provider.plan, context, system=PRIORITY_PROMPT)
        if isinstance(plan, list) and plan:
            by_title = {t.get("title", "").lower(): t for t in plan if isinstance(t, dict)}
            for task in tasks:
                match = by_title.get(task["title"].lower())
                if match:
                    task["impact"] = match.get("impact")
                    task["difficulty"] = match.get("difficulty")
                    task["urgency"] = match.get("urgency")
                    task["confidence"] = match.get("confidence")
                    task["priority"] = match.get("priority", task.get("priority"))
            return tasks
    except AiUnavailableError:
        pass
    return _rule_priorities(tasks)


def _rule_priorities(tasks: list[dict]) -> list[dict]:
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    for task in tasks:
        task.setdefault("priority", "MEDIUM")
        task.setdefault("impact", None)
        task.setdefault("difficulty", None)
        task.setdefault("urgency", None)
        task.setdefault("confidence", None)
    tasks.sort(key=lambda t: order.get(t["priority"], 4))
    return tasks
