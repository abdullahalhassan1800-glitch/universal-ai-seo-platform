"""Crawl job, page, issue and score routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api.deps import get_website_access
from ..core.db import get_db
from ..models import CrawlJob, Page, SeoIssue, Website
from ..schemas import CrawlJobOut, CrawlRequest, IssueOut, PageOut, ScoreOut
from ..services import crawl_service, task_service

router = APIRouter(tags=["crawl"])


@router.post("/websites/{website_id}/crawl", response_model=CrawlJobOut, status_code=202)
def start_crawl(payload: CrawlRequest, website: Website = Depends(get_website_access)):
    job = crawl_service.start_crawl(
        website,
        max_pages=payload.max_pages,
        delay=payload.delay,
        render=payload.render,
    )
    return job


@router.get("/websites/{website_id}/crawl/jobs", response_model=list[CrawlJobOut])
def list_crawl_jobs(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return (
        db.query(CrawlJob)
        .filter(CrawlJob.website_id == website.id)
        .order_by(CrawlJob.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/websites/{website_id}/crawl/jobs/{job_id}", response_model=CrawlJobOut)
def get_crawl_job(job_id: uuid.UUID, website: Website = Depends(get_website_access),
                  db: Session = Depends(get_db)):
    job = db.get(CrawlJob, job_id)
    if job is None or job.website_id != website.id:
        raise HTTPException(404, "Crawl job not found")
    return job


@router.get("/websites/{website_id}/crawl/latest", response_model=CrawlJobOut | None)
def latest_crawl_job(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return (
        db.query(CrawlJob)
        .filter(CrawlJob.website_id == website.id)
        .order_by(CrawlJob.created_at.desc())
        .first()
    )


@router.get("/websites/{website_id}/score", response_model=ScoreOut | None)
def get_score(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    job = (
        db.query(CrawlJob)
        .filter(CrawlJob.website_id == website.id, CrawlJob.status == "completed")
        .order_by(CrawlJob.finished_at.desc())
        .first()
    )
    if job is None or not job.scores:
        return None
    return job.scores


@router.get("/websites/{website_id}/issues", response_model=list[IssueOut])
def list_issues(severity: str | None = None, status: str | None = None,
                website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    query = db.query(SeoIssue).filter(SeoIssue.website_id == website.id)
    if severity:
        query = query.filter(SeoIssue.severity == severity.upper())
    if status:
        query = query.filter(SeoIssue.status == status)
    return query.order_by(SeoIssue.severity).limit(500).all()


@router.get("/websites/{website_id}/pages", response_model=list[PageOut])
def list_pages(limit: int = 100, offset: int = 0,
               website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return (
        db.query(Page)
        .filter(Page.website_id == website.id)
        .order_by(Page.created_at.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )


@router.post("/websites/{website_id}/issues/generate-tasks", status_code=201)
def generate_tasks(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    tasks = task_service.tasks_from_issues(db, website.id)
    return {"created": len(tasks)}
