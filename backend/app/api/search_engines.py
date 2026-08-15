"""Search engine connectors: capabilities, connections, sync, SERP analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from search_engines.base import DataUnavailableError
from search_engines.registry import list_engines

from ..api.deps import get_website_access
from ..core.db import get_db
from ..models import SearchEngineConnection, Website
from ..schemas import AnalyticsResult, ConnectionCreate, ConnectionOut, EngineOut, SerpResult, SyncRequest
from ..services import adapter_service

router = APIRouter(tags=["search-engines"])


@router.get("/engines", response_model=list[EngineOut])
def list_available_engines():
    return list_engines()


@router.get("/websites/{website_id}/connections", response_model=list[ConnectionOut])
def list_connections(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return adapter_service.ensure_connections(db, website.id)


@router.post("/websites/{website_id}/connections", response_model=ConnectionOut, status_code=201)
def configure_connection(payload: ConnectionCreate, website: Website = Depends(get_website_access),
                         db: Session = Depends(get_db)):
    row = (
        db.query(SearchEngineConnection)
        .filter(SearchEngineConnection.website_id == website.id,
                SearchEngineConnection.engine_id == payload.engine_id)
        .first()
    )
    if row is None:
        row = SearchEngineConnection(website_id=website.id, engine_id=payload.engine_id, status="unconfigured")
        db.add(row)
    if payload.config is not None:
        row.config = payload.config
    db.commit()
    db.refresh(row)
    return row


@router.post("/websites/{website_id}/connections/sync", response_model=AnalyticsResult)
def sync_connection(payload: SyncRequest, website: Website = Depends(get_website_access),
                    db: Session = Depends(get_db)):
    result = adapter_service.sync_engine(db, website.id, payload.engine_id,
                                         start_date=payload.start_date, end_date=payload.end_date)
    return AnalyticsResult(search_engine=payload.engine_id, available=result["available"],
                           data=result if result["available"] else None, message=result.get("message"))


@router.post("/websites/{website_id}/serp", response_model=SerpResult)
def analyze_serp(query: str, engine_id: str, website: Website = Depends(get_website_access),
                 db: Session = Depends(get_db)):
    if not query.strip():
        raise HTTPException(422, "query is required")
    try:
        result = adapter_service.analyze_serp(engine_id, query)
    except DataUnavailableError as exc:
        raise HTTPException(503, str(exc))
    return SerpResult(query=query, search_engine=engine_id,
                      results=result.get("results", []), source=result.get("source", "api"))
