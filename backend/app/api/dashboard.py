"""Dashboard summary routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..api.deps import get_current_workspace
from ..core.db import get_db
from ..models import (
    AnalyticsData,
    CrawlJob,
    Keyword,
    Page,
    SearchEngineConnection,
    SearchData,
    SeoIssue,
    SeoTask,
    Website,
    Workspace,
)
from ..schemas import DashboardSummary, TaskOut

router = APIRouter(tags=["dashboard"])


def _in(column, website_ids):
    return column.in_(website_ids)


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(workspace: Workspace = Depends(get_current_workspace), db: Session = Depends(get_db)):
    website_ids = [w.id for w in db.query(Website).filter(Website.workspace_id == workspace.id)]
    if not website_ids:
        return DashboardSummary(
            websites=0, average_seo_score=None, total_pages=0, issues_by_severity={},
            open_tasks=0, keywords=0, connections=0, indexed_urls=None, ranking_keywords=0,
            organic_clicks=None, impressions=None, ctr=None, average_position=None,
            score_trend=[], search_visibility=[], recent_tasks=[],
        )

    sites = len(website_ids)

    scores = [
        job.scores.get("universal_seo_score")
        for job in db.query(CrawlJob)
        .filter(_in(CrawlJob.website_id, website_ids), CrawlJob.status == "completed")
        .all()
        if job.scores and job.scores.get("universal_seo_score") is not None
    ]
    average_score = round(sum(scores) / len(scores)) if scores else None

    total_pages = (
        db.query(func.count(Page.id))
        .filter(_in(Page.website_id, website_ids)).scalar() or 0
    )

    issue_rows = (
        db.query(SeoIssue.severity, func.count(SeoIssue.id))
        .filter(_in(SeoIssue.website_id, website_ids))
        .group_by(SeoIssue.severity).all()
    )
    issues_by_severity = {sev: count for sev, count in issue_rows}

    open_tasks = (
        db.query(func.count(SeoTask.id))
        .filter(_in(SeoTask.website_id, website_ids),
                SeoTask.status.in_(["pending", "approved"])).scalar() or 0
    )

    keywords = (
        db.query(func.count(Keyword.id))
        .filter(_in(Keyword.website_id, website_ids)).scalar() or 0
    )

    connections = (
        db.query(func.count(SearchEngineConnection.id))
        .filter(_in(SearchEngineConnection.website_id, website_ids),
                SearchEngineConnection.status == "configured").scalar() or 0
    )

    ranking_keywords = 0
    average_position = None
    ranked = (
        db.query(SearchData.position)
        .filter(_in(SearchData.website_id, website_ids),
                SearchData.keyword.isnot(None), SearchData.position.isnot(None),
                SearchData.position <= 100)
        .all()
    )
    if ranked:
        positions = [r.position for r in ranked]
        ranking_keywords = len(positions)
        average_position = round(sum(positions) / len(positions), 2)

    organic_clicks = impressions = None
    ctr = None
    analytics = {
        m: v for m, v in db.query(AnalyticsData.metric, func.max(AnalyticsData.value))
        .filter(_in(AnalyticsData.website_id, website_ids))
        .group_by(AnalyticsData.metric).all()
    }
    if analytics:
        organic_clicks = int(analytics.get("organic_clicks") or 0)
        impressions = int(analytics.get("organic_impressions") or 0)
        ctr = analytics.get("ctr")

    recent_tasks = (
        db.query(SeoTask)
        .filter(_in(SeoTask.website_id, website_ids))
        .order_by(SeoTask.created_at.desc())
        .limit(10)
        .all()
    )

    return DashboardSummary(
        websites=sites,
        average_seo_score=average_score,
        total_pages=total_pages,
        issues_by_severity=issues_by_severity,
        open_tasks=open_tasks,
        keywords=keywords,
        connections=connections,
        indexed_urls=None,
        ranking_keywords=ranking_keywords,
        organic_clicks=organic_clicks,
        impressions=impressions,
        ctr=ctr,
        average_position=average_position,
        score_trend=_score_trend(db, website_ids),
        search_visibility=_visibility_trend(db, website_ids),
        recent_tasks=[TaskOut.model_validate(t) for t in recent_tasks],
    )


def _score_trend(db: Session, website_ids) -> list[dict]:
    jobs = (
        db.query(CrawlJob)
        .filter(_in(CrawlJob.website_id, website_ids),
                CrawlJob.status == "completed", CrawlJob.scores.isnot(None))
        .order_by(CrawlJob.finished_at)
        .all()
    )
    seen: dict[str, dict] = {}
    for job in jobs:
        score = job.scores.get("universal_seo_score") if job.scores else None
        if score is None:
            continue
        key = job.finished_at.date().isoformat() if job.finished_at else job.created_at.date().isoformat()
        seen[key] = {"date": key, "score": score}
    return [v for k, v in sorted(seen.items())]


def _visibility_trend(db: Session, website_ids) -> list[dict]:
    rows = (
        db.query(AnalyticsData.date, AnalyticsData.metric, AnalyticsData.value)
        .filter(_in(AnalyticsData.website_id, website_ids),
                AnalyticsData.metric.in_(["organic_clicks", "organic_impressions"]))
        .order_by(AnalyticsData.date)
        .all()
    )
    out: dict[str, dict] = {}
    for date, metric, value in rows:
        out.setdefault(date, {"date": date, "clicks": None, "impressions": None})
        out[date][metric.replace("organic_", "")] = value
    return [out[d] for d in sorted(out)]
