"""Crawl orchestration service (background job execution)."""

from __future__ import annotations

import threading
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from crawler import run_crawl_sync

from ..core.config import settings
from ..core.db import SessionLocal
from ..models import CrawlJob, CrawlResult, Page, SeoIssue, Website


def start_crawl(website: Website, max_pages: int | None = None, delay: float | None = None,
                render: str | None = None) -> CrawlJob:
    job = CrawlJob(website_id=website.id, status="queued")
    db = SessionLocal()
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()
    thread = threading.Thread(target=_run_job, args=(str(job_id), max_pages, delay, render), daemon=True)
    thread.start()
    return job


def _run_job(job_id: str, max_pages: int | None, delay: float | None, render: str | None) -> None:
    db = SessionLocal()
    try:
        job = db.get(CrawlJob, uuid.UUID(job_id))
        if job is None:
            return
        website = db.get(Website, job.website_id)
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        result = run_crawl_sync(
            site_url=website.domain,
            max_pages=max_pages or settings.crawler_max_pages,
            delay=delay if delay is not None else settings.crawler_delay,
            user_agent=settings.crawler_user_agent,
            render=render or settings.crawler_render,
            render_timeout=settings.crawler_render_timeout,
        )

        _persist(db, job, website, result)
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        try:
            job = db.get(CrawlJob, uuid.UUID(job_id))
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.errors = [str(exc), traceback.format_exc(limit=5)]
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _persist(db: Session, job: CrawlJob, website: Website, result) -> None:
    from crawler.analyzer import Issue

    from ..services.ai_service import enrich_issues_with_ai

    result.issues = enrich_issues_with_ai(result.issues)

    job.pages_crawled = len(result.pages)
    job.skipped_by_robots = result.skipped_by_robots
    job.errors = result.errors or None
    job.scores = result.scores

    pages_by_url: dict[str, Page] = {}
    for page in result.pages:
        db_page = Page(
            website_id=website.id,
            url=page.url,
            final_url=page.final_url,
            status_code=page.status_code,
            title=page.title,
            meta_description=page.meta_description,
            h1=page.h1 or None,
            h2=page.h2 or None,
            word_count=page.word_count,
            canonical=page.canonical,
            robots_meta=page.robots_meta or None,
            internal_links=len(page.internal_links),
            external_links=len(page.external_links),
            image_count=len(page.images),
            has_schema=bool(page.structured_data),
            is_indexable="noindex" not in (page.robots_meta or []),
        )
        db.add(db_page)
        db.flush()
        pages_by_url[page.final_url] = db_page
        db.add(CrawlResult(
            crawl_job_id=job.id,
            page_id=db_page.id,
            website_id=website.id,
            url=page.url,
            status_code=page.status_code,
            data={
                "title": page.title,
                "meta_description": page.meta_description,
                "h1": page.h1,
                "h2": page.h2,
                "h3": page.h3,
                "word_count": page.word_count,
                "canonical": page.canonical,
                "robots_meta": page.robots_meta,
                "images": page.images,
                "structured_data": page.structured_data,
                "internal_links": page.internal_links[:200],
                "external_links": page.external_links[:200],
            },
        ))

    for issue in result.issues:
        if not isinstance(issue, Issue):
            continue
        d = issue.to_dict()
        db.add(SeoIssue(
            website_id=website.id,
            crawl_job_id=job.id,
            issue=d["issue"],
            severity=d["severity"],
            affected_url=d["affected_url"],
            explanation=d["explanation"],
            recommendation=d["recommendation"],
            dimension=d["dimension"],
            ai_solution=d.get("ai_solution"),
            priority=d["priority"],
            status="open",
        ))

    website.last_crawl_at = datetime.now(timezone.utc)
