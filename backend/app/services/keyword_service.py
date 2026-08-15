"""Keyword and search-intent services."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Keyword, KeywordCluster
from . import ai_service


def add_keywords(db: Session, website_id, keywords: list[str]) -> list[Keyword]:
    existing = {k.keyword for k in db.query(Keyword).filter(Keyword.website_id == website_id)}
    unique = list(dict.fromkeys(k.strip() for k in keywords if k.strip()))
    new = [k for k in unique if k not in existing]
    intents = ai_service.classify_keyword_intent(new)
    created: list[Keyword] = []
    for kw in new:
        row = Keyword(website_id=website_id, keyword=kw, intent=intents.get(kw), source="manual")
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def build_clusters(db: Session, website_id, keywords: list[str] | None = None) -> list[KeywordCluster]:
    if keywords is None:
        keywords = [k.keyword for k in db.query(Keyword).filter(Keyword.website_id == website_id)]
    keywords = list(dict.fromkeys(keywords))
    intents = ai_service.classify_keyword_intent(keywords)
    clusters = ai_service.cluster_keywords(keywords, intents)
    db.query(KeywordCluster).filter(KeywordCluster.website_id == website_id).delete()
    created = []
    for cluster in clusters:
        row = KeywordCluster(
            website_id=website_id,
            name=cluster["name"],
            topic=cluster.get("topic"),
            intent=cluster.get("intent"),
            keywords=cluster.get("keywords") or [],
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created
