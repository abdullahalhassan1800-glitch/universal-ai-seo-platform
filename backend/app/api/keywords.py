"""Keyword and topic-cluster routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.deps import get_website_access
from ..core.db import get_db
from ..models import Keyword, KeywordCluster, Website
from ..schemas import ClusterOut, ClusterRequest, KeywordIn, KeywordOut
from ..services import keyword_service

router = APIRouter(tags=["keywords"])


@router.get("/websites/{website_id}/keywords", response_model=list[KeywordOut])
def list_keywords(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return (
        db.query(Keyword)
        .filter(Keyword.website_id == website.id)
        .order_by(Keyword.created_at)
        .all()
    )


@router.post("/websites/{website_id}/keywords", response_model=list[KeywordOut], status_code=201)
def add_keywords(payload: KeywordIn, website: Website = Depends(get_website_access),
                 db: Session = Depends(get_db)):
    return keyword_service.add_keywords(db, website.id, payload.keywords)


@router.delete("/websites/{website_id}/keywords/{keyword_id}", status_code=204)
def delete_keyword(keyword_id: uuid.UUID, website: Website = Depends(get_website_access),
                   db: Session = Depends(get_db)):
    row = db.get(Keyword, keyword_id)
    if row is None or row.website_id != website.id:
        return
    db.delete(row)
    db.commit()


@router.get("/websites/{website_id}/clusters", response_model=list[ClusterOut])
def list_clusters(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return (
        db.query(KeywordCluster)
        .filter(KeywordCluster.website_id == website.id)
        .order_by(KeywordCluster.created_at)
        .all()
    )


@router.post("/websites/{website_id}/clusters", response_model=list[ClusterOut], status_code=201)
def build_clusters(payload: ClusterRequest, website: Website = Depends(get_website_access),
                   db: Session = Depends(get_db)):
    return keyword_service.build_clusters(db, website.id, payload.keywords)
