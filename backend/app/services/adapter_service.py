"""Search engine connection + data sync service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from search_engines.base import DataUnavailableError
from search_engines.registry import ADAPTER_CLASSES, ENGINE_IDS, get_adapter

from ..models import (
    AnalyticsData,
    RankingData,
    SearchConsoleData,
    SearchEngine,
    SearchEngineConnection,
    SearchData,
)


def ensure_engines_seeded(db: Session) -> None:
    existing = {r.engine_id for r in db.query(SearchEngine.engine_id).all()}
    for engine_id, name in [("google", "Google"), ("bing", "Bing"), ("yandex", "Yandex"),
                            ("brave", "Brave Search"), ("duckduckgo", "DuckDuckGo"), ("yahoo", "Yahoo")]:
        if engine_id not in existing:
            db.add(SearchEngine(engine_id=engine_id, display_name=name, supported=True))
    db.commit()


def ensure_connections(db: Session, website_id) -> list[SearchEngineConnection]:
    ensure_engines_seeded(db)
    existing = {c.engine_id: c for c in db.query(SearchEngineConnection)
                .filter(SearchEngineConnection.website_id == website_id).all()}
    rows = []
    for engine_id in ENGINE_IDS:
        adapter = get_adapter(engine_id)
        if engine_id in existing:
            row = existing[engine_id]
            row.status = adapter.status
            row.error = adapter.reason if adapter.status != "configured" else None
        else:
            row = SearchEngineConnection(
                website_id=website_id,
                engine_id=engine_id,
                status=adapter.status,
                error=adapter.reason if adapter.status != "configured" else None,
            )
            db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def sync_engine(db: Session, website_id, engine_id: str, start_date: str, end_date: str) -> dict:
    adapter = get_adapter(engine_id)
    connection = (
        db.query(SearchEngineConnection)
        .filter(SearchEngineConnection.website_id == website_id,
                SearchEngineConnection.engine_id == engine_id)
        .first()
    )
    if connection is None:
        connection = SearchEngineConnection(website_id=website_id, engine_id=engine_id, status="unconfigured")
        db.add(connection)
        db.flush()

    try:
        if adapter.status != "configured":
            raise DataUnavailableError(adapter.reason or "Not configured")
        rows = adapter.get_search_analytics(start_date=start_date, end_date=end_date)
        saved = 0
        for row in rows:
            item = SearchData(
                website_id=website_id,
                engine_id=engine_id,
                keyword=row.get("query"),
                date=row.get("date", end_date),
                clicks=row.get("clicks"),
                impressions=row.get("impressions"),
                ctr=row.get("ctr"),
                position=row.get("position"),
                source="api",
            )
            db.add(item)
            scd = SearchConsoleData(
                website_id=website_id,
                date=row.get("date", end_date),
                query=row.get("query"),
                page=row.get("page"),
                clicks=row.get("clicks"),
                impressions=row.get("impressions"),
                ctr=row.get("ctr"),
                position=row.get("position"),
            )
            db.add(scd)
            saved += 1

        visibility = adapter.get_search_visibility(start_date=start_date, end_date=end_date)
        for metric, key in [("organic_clicks", "clicks"), ("organic_impressions", "impressions"),
                            ("avg_position", "position"), ("ctr", "ctr")]:
            if visibility.get(key) is not None:
                db.add(AnalyticsData(
                    website_id=website_id, date=end_date, metric=metric,
                    value=float(visibility[key]), source="api",
                ))
        connection.status = "synced"
        connection.last_sync_at = datetime.now(timezone.utc)
        connection.error = None
        db.commit()
        return {"available": True, "rows": saved, "engine_id": engine_id}
    except DataUnavailableError as exc:
        connection.status = "unavailable"
        connection.error = str(exc)
        db.commit()
        return {"available": False, "rows": 0, "engine_id": engine_id, "message": str(exc)}
    except Exception as exc:
        connection.status = "error"
        connection.error = str(exc)
        db.commit()
        return {"available": False, "rows": 0, "engine_id": engine_id, "message": str(exc)}


def analyze_serp(engine_id: str, query: str) -> dict:
    adapter = get_adapter(engine_id)
    if "analyze_serp" not in adapter.capabilities() or not adapter.capabilities()["analyze_serp"]:
        raise DataUnavailableError("Not supported by this search engine.")
    return adapter.analyze_serp(query)
