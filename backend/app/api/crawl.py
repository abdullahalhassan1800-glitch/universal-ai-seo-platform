"""Crawl job, page, issue and score routes."""

from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..api.deps import get_website_access
from ..core.db import get_db
from ..models import CrawlJob, Page, SeoIssue, SeoTask, Website
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


@router.get("/websites/{website_id}/report", response_class=HTMLResponse)
def audit_report(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    job = (
        db.query(CrawlJob)
        .filter(CrawlJob.website_id == website.id, CrawlJob.status == "completed")
        .order_by(CrawlJob.finished_at.desc())
        .first()
    )
    issues = (
        db.query(SeoIssue)
        .filter(SeoIssue.website_id == website.id)
        .order_by(SeoIssue.severity)
        .limit(500)
        .all()
    )
    tasks = (
        db.query(SeoTask)
        .filter(SeoTask.website_id == website.id)
        .order_by(SeoTask.priority)
        .limit(200)
        .all()
    )
    pages = (
        db.query(Page)
        .filter(Page.website_id == website.id)
        .order_by(Page.created_at.desc())
        .limit(500)
        .all()
    )

    scores = job.scores if job and job.scores else {}
    dims = scores.get("dimensions", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    severity_colors = {"CRITICAL": "#dc2626", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "LOW": "#65a30d"}

    def esc(s):
        return html.escape(str(s)) if s else ""

    dims_rows = "\n".join(
        f'<tr><td style="padding:6px 12px;text-transform:capitalize">{esc(k.replace("_"," "))}</td>'
        f'<td style="padding:6px 12px;text-align:right;font-weight:600">{esc(v) if v is not None else "—"}</td></tr>'
        for k, v in dims.items()
    )

    issue_rows = "\n".join(
        f'<tr>'
        f'<td style="padding:8px 12px"><span style="display:inline-block;padding:2px 8px;border-radius:4px;color:#fff;background:{severity_colors.get(i.severity,"#6b7280")};font-size:12px;font-weight:600">{esc(i.severity)}</span></td>'
        f'<td style="padding:8px 12px;font-weight:500">{esc(i.issue)}</td>'
        f'<td style="padding:8px 12px;color:#64748b;font-size:13px">{esc(i.affected_url or "site-wide")}</td>'
        f'<td style="padding:8px 12px;font-size:13px">{esc(i.explanation or "")}</td>'
        f'<td style="padding:8px 12px;font-size:13px;color:#2563eb">{esc(i.ai_solution or i.recommendation or "")}</td>'
        f'</tr>'
        for i in issues
    )

    task_rows = "\n".join(
        f'<tr>'
        f'<td style="padding:6px 12px"><span style="color:{severity_colors.get(t.priority,"#6b7280")};font-weight:600">{esc(t.priority)}</span></td>'
        f'<td style="padding:6px 12px">{esc(t.title)}</td>'
        f'<td style="padding:6px 12px;font-size:13px">{esc(t.description or "")}</td>'
        f'<td style="padding:6px 12px;text-align:center">{esc(t.impact) or "—"}</td>'
        f'<td style="padding:6px 12px;text-align:center">{esc(t.difficulty) or "—"}</td>'
        f'<td style="padding:6px 12px;text-align:center">{esc(t.urgency) or "—"}</td>'
        f'<td style="padding:6px 12px;text-align:center">{esc(t.confidence) or "—"}</td>'
        f'</tr>'
        for t in tasks
    )

    page_rows = "\n".join(
        f'<tr>'
        f'<td style="padding:6px 12px;max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{esc(p.url)}</td>'
        f'<td style="padding:6px 12px">{esc(p.status_code)}</td>'
        f'<td style="padding:6px 12px">{esc(p.title or "—")}</td>'
        f'<td style="padding:6px 12px;text-align:right">{esc(p.word_count)}</td>'
        f'</tr>'
        for p in pages
    )

    report_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>SEO Audit Report — {esc(website.name)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:system-ui,-apple-system,sans-serif; color:#1e293b; background:#f8fafc; padding:40px; }}
  .container {{ max-width:960px; margin:0 auto; }}
  h1 {{ font-size:28px; margin-bottom:4px; }}
  .meta {{ color:#64748b; font-size:14px; margin-bottom:32px; }}
  .score-box {{ display:inline-flex; align-items:center; gap:16px; background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px 28px; margin-bottom:24px; }}
  .score-num {{ font-size:52px; font-weight:800; color:#0f172a; }}
  .score-label {{ font-size:14px; color:#64748b; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; margin-bottom:24px; }}
  th {{ text-align:left; padding:10px 12px; background:#f1f5f9; font-size:13px; color:#475569; font-weight:600; }}
  td {{ border-top:1px solid #f1f5f9; }}
  h2 {{ font-size:18px; margin:24px 0 12px; color:#0f172a; }}
  .footer {{ margin-top:40px; text-align:center; color:#94a3b8; font-size:12px; }}
</style></head><body>
<div class="container">
  <h1>SEO Audit Report</h1>
  <div class="meta">{esc(website.name)} &mdash; {esc(website.domain)} &bull; Generated {now}</div>

  <div class="score-box">
    <div><div class="score-num">{esc(scores.get('universal_seo_score', 0))}</div><div class="score-label">Universal SEO Score</div></div>
    <div style="border-left:1px solid #e2e8f0;padding-left:20px">
      <div class="score-label">Pages crawled: {esc(job.pages_crawled if job else 0)}<br>Issues found: {esc(len(issues))}</div>
    </div>
  </div>

  {'<h2>Dimension Scores</h2><table><thead><tr><th>Dimension</th><th style="text-align:right">Score</th></tr></thead><tbody>' + dims_rows + '</tbody></table>' if dims_rows else ''}

  {'<h2>SEO Issues (' + str(len(issues)) + ')</h2><table><thead><tr><th>Severity</th><th>Issue</th><th>URL</th><th>Explanation</th><th>AI Solution / Fix</th></tr></thead><tbody>' + issue_rows + '</tbody></table>' if issue_rows else '<p style="color:#64748b">No issues found.</p>'}

  {'<h2>SEO Tasks (' + str(len(tasks)) + ')</h2><table><thead><tr><th>Priority</th><th>Task</th><th>Description</th><th style="text-align:center">Impact</th><th style="text-align:center">Difficulty</th><th style="text-align:center">Urgency</th><th style="text-align:center">Confidence</th></tr></thead><tbody>' + task_rows + '</tbody></table>' if task_rows else ''}

  {'<h2>Crawled Pages (' + str(len(pages)) + ')</h2><table><thead><tr><th>URL</th><th>Status</th><th>Title</th><th style="text-align:right">Words</th></tr></thead><tbody>' + page_rows + '</tbody></table>' if page_rows else ''}

  <div class="footer">Universal AI SEO Platform &bull; Report generated {now}</div>
</div></body></html>"""

    return HTMLResponse(content=report_html)
