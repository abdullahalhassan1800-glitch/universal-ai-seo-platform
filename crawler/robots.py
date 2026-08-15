"""robots.txt parsing and matching (RFC 9309 style rules)."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class RobotsTxt:
    rules: list[tuple[str, str]] = field(default_factory=list)  # (allow/disallow, path)
    crawl_delay: float = 0.0
    sitemaps: list[str] = field(default_factory=list)
    agent: str = "*"

    @classmethod
    def parse(cls, text: str | None, user_agent: str = "*") -> "RobotsTxt":
        robots = cls(agent=user_agent)
        if not text:
            return robots
        current_agents: list[str] = []
        active = False
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                current_agents = [a.strip().lower() for a in value.split(",")]
                active = user_agent.lower() in current_agents or "*" in current_agents
            elif active:
                if key == "disallow" and value:
                    robots.rules.append(("disallow", value))
                elif key == "allow" and value:
                    robots.rules.append(("allow", value))
                elif key == "crawl-delay":
                    try:
                        robots.crawl_delay = max(robots.crawl_delay, float(value))
                    except ValueError:
                        pass
                elif key == "sitemap":
                    robots.sitemaps.append(value)
        return robots

    def is_allowed(self, url: str) -> bool:
        path = urlparse(url).path or "/"
        longest = -1
        allowed = True
        for kind, rule_path in self.rules:
            if rule_path == "*":
                match_len = len(rule_path)
                matches = True
            elif rule_path in ("/", "") :
                match_len = len(rule_path)
                matches = path.startswith(rule_path)
            else:
                if rule_path.endswith("*"):
                    prefix = rule_path.rstrip("*")
                    match_len = len(prefix)
                    matches = path.startswith(prefix)
                else:
                    match_len = len(rule_path)
                    matches = path.startswith(rule_path)
            if matches and match_len >= longest:
                longest = match_len
                allowed = kind == "allow"
        return allowed

    def describe(self) -> dict:
        return {
            "agent": self.agent,
            "rules": [{"type": k, "path": v} for k, v in self.rules],
            "crawl_delay": self.crawl_delay,
            "sitemaps": self.sitemaps,
        }
