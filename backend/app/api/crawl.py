"""Crawl job, page, issue and score routes."""

from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..api.deps import get_website_access, get_current_user, get_workspace
from ..core.db import get_db
from ..core.security import decode_access_token
from ..models import CrawlJob, Page, SeoIssue, SeoTask, User, Website
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
def audit_report(
    request: Request,
    website_id: uuid.UUID,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
):
    user = None
    bearer = request.headers.get("authorization", "")
    if bearer.startswith("Bearer "):
        user_id = decode_access_token(bearer[7:])
        if user_id:
            user = db.get(User, uuid.UUID(user_id))
    if user is None and token:
        user_id = decode_access_token(token)
        if user_id:
            user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    website = db.get(Website, website_id)
    if website is None:
        raise HTTPException(404, "Website not found")
    workspace = get_workspace(user, db)
    if website.workspace_id != workspace.id:
        raise HTTPException(404, "Website not found")

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
    score_val = scores.get("universal_seo_score", 0)
    now = datetime.now(timezone.utc).strftime("%d %B %Y at %H:%M UTC")
    crawled = job.pages_crawled if job else 0

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    issues_sorted = sorted(issues, key=lambda i: sev_order.get(i.severity, 9))
    crit = sum(1 for i in issues if i.severity == "CRITICAL")
    high = sum(1 for i in issues if i.severity == "HIGH")
    med = sum(1 for i in issues if i.severity == "MEDIUM")
    low = sum(1 for i in issues if i.severity == "LOW")

    def esc(s):
        return html.escape(str(s)) if s else ""

    def score_color(v):
        if v is None:
            return "#94a3b8"
        if v >= 80:
            return "#16a34a"
        if v >= 60:
            return "#ca8a04"
        if v >= 40:
            return "#ea580c"
        return "#dc2626"

    def bar_html(label, value, color=None):
        v = value if value is not None else 0
        c = color or score_color(v)
        return f'''<div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-size:13px;color:#475569;text-transform:capitalize">{esc(label.replace("_"," "))}</span>
            <span style="font-size:13px;font-weight:700;color:{c}">{esc(v) if value is not None else "—"}</span>
          </div>
          <div style="background:#e2e8f0;border-radius:6px;height:8px;overflow:hidden">
            <div style="background:{c};height:100%;width:{v}%;border-radius:6px;transition:width .3s"></div>
          </div>
        </div>'''

    sev_colors = {"CRITICAL": "#dc2626", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "LOW": "#65a30d"}
    sev_bg = {"CRITICAL": "#fef2f2", "HIGH": "#fff7ed", "MEDIUM": "#fefce8", "LOW": "#f7fee7"}

    issue_html_parts = []
    for i in issues_sorted:
        sc = sev_colors.get(i.severity, "#6b7280")
        sb = sev_bg.get(i.severity, "#f8fafc")
        solution = i.ai_solution or i.recommendation or ""
        issue_html_parts.append(f'''
        <div style="background:{sb};border-left:4px solid {sc};border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <span style="display:inline-block;padding:2px 10px;border-radius:20px;color:#fff;background:{sc};font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase">{esc(i.severity)}</span>
            <span style="font-size:15px;font-weight:600;color:#0f172a">{esc(i.issue)}</span>
          </div>
          <p style="font-size:13px;color:#475569;margin:4px 0">{esc(i.explanation or "")}</p>
          {f'<p style="font-size:13px;color:#64748b;margin:4px 0">Affected: <code style="background:#e2e8f0;padding:1px 6px;border-radius:4px;font-size:12px">{esc(i.affected_url or "site-wide")}</code></p>' if i.affected_url else ''}
          {f'<div style="margin-top:8px;background:#eff6ff;border-radius:6px;padding:10px 14px;font-size:13px;color:#1d4ed8"><strong>AI Recommendation:</strong> {esc(solution)}</div>' if solution else ''}
        </div>''')
    issues_block = "\n".join(issue_html_parts)

    task_html_parts = []
    for t in tasks:
        tc = sev_colors.get(t.priority, "#6b7280")
        metrics = []
        for label, val in [("Impact", t.impact), ("Difficulty", t.difficulty), ("Urgency", t.urgency), ("Confidence", t.confidence)]:
            if val is not None:
                metrics.append(f'<div style="text-align:center"><div style="font-size:11px;color:#94a3b8;margin-bottom:2px">{label}</div><div style="font-size:18px;font-weight:700;color:{score_color(val)}">{int(val)}</div></div>')
        task_html_parts.append(f'''
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin-bottom:12px;display:flex;align-items:center;gap:20px">
          <div style="min-width:80px;text-align:center">
            <div style="display:inline-block;padding:3px 12px;border-radius:20px;color:#fff;background:{tc};font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase">{esc(t.priority)}</div>
          </div>
          <div style="flex:1">
            <div style="font-size:15px;font-weight:600;color:#0f172a;margin-bottom:2px">{esc(t.title)}</div>
            <div style="font-size:13px;color:#64748b">{esc(t.description or "")}</div>
          </div>
          <div style="display:flex;gap:16px">{"".join(metrics)}</div>
        </div>''')
    tasks_block = "\n".join(task_html_parts)

    page_html_parts = []
    for p in pages:
        pc = "#16a34a" if p.status_code == 200 else "#dc2626"
        pbg = "#f0fdf4" if p.status_code == 200 else "#fef2f2"
        page_html_parts.append(f'''
        <tr>
          <td style="padding:10px 14px;font-size:13px;max-width:360px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#0f172a">{esc(p.url)}</td>
          <td style="padding:10px 14px"><span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;color:{pc};background:{pbg}">{esc(p.status_code)}</span></td>
          <td style="padding:10px 14px;font-size:13px;color:#475569">{esc(p.title or "—")}</td>
          <td style="padding:10px 14px;text-align:right;font-size:13px;color:#475569">{esc(p.word_count)}</td>
        </tr>''')
    pages_block = "\n".join(page_html_parts)

    report_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEO Audit Report — {esc(website.name)}</title>
<style>
  @media print {{ body {{ padding:20px !important; }} .no-print {{ display:none !important; }} }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',system-ui,-apple-system,sans-serif; color:#1e293b; background:#f1f5f9; min-height:100vh; }}
  .header {{ background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 50%,#1e293b 100%); color:#fff; padding:48px 40px; }}
  .header h1 {{ font-size:28px; font-weight:700; margin-bottom:6px; }}
  .header .sub {{ color:#94a3b8; font-size:14px; }}
  .container {{ max-width:900px; margin:-32px auto 40px; padding:0 20px; position:relative; }}
  .card {{ background:#fff; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04); padding:28px 32px; margin-bottom:20px; }}
  .score-hero {{ display:flex; align-items:center; gap:32px; }}
  .score-ring {{ width:120px; height:120px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; background:conic-gradient({score_color(score_val)} {score_val * 3.6}deg, #e2e8f0 0deg); }}
  .score-ring-inner {{ width:90px; height:90px; border-radius:50%; background:#fff; display:flex; align-items:center; justify-content:center; flex-direction:column; }}
  .score-ring-num {{ font-size:32px; font-weight:800; color:#0f172a; line-height:1; }}
  .score-ring-label {{ font-size:10px; color:#94a3b8; font-weight:600; text-transform:uppercase; letter-spacing:.5px; margin-top:2px; }}
  .stat-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; flex:1; }}
  .stat-box {{ background:#f8fafc; border-radius:8px; padding:12px 16px; text-align:center; }}
  .stat-box .num {{ font-size:22px; font-weight:700; }}
  .stat-box .lbl {{ font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:.5px; margin-top:2px; }}
  .section {{ margin-top:24px; }}
  .section-title {{ font-size:16px; font-weight:700; color:#0f172a; margin-bottom:16px; display:flex; align-items:center; gap:8px; }}
  .section-title .icon {{ width:24px; height:24px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:13px; color:#fff; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; padding:10px 14px; font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:.5px; border-bottom:2px solid #e2e8f0; }}
  td {{ border-bottom:1px solid #f1f5f9; }}
  tr:hover td {{ background:#f8fafc; }}
  .footer {{ text-align:center; padding:32px 20px; color:#94a3b8; font-size:12px; }}
</style></head><body>

<div class="header">
  <div style="max-width:900px;margin:0 auto">
    <div style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">SEO Audit Report</div>
    <h1>{esc(website.name)}</h1>
    <div class="sub">{esc(website.domain)} &bull; {esc(now)}</div>
  </div>
</div>

<div class="container">

  <div class="card score-hero">
    <div class="score-ring">
      <div class="score-ring-inner">
        <div class="score-ring-num" style="color:{score_color(score_val)}">{esc(score_val)}</div>
        <div class="score-ring-label">Score</div>
      </div>
    </div>
    <div class="stat-grid">
      <div class="stat-box"><div class="num" style="color:#0f172a">{esc(crawled)}</div><div class="lbl">Pages</div></div>
      <div class="stat-box"><div class="num" style="color:#dc2626">{esc(crit)}</div><div class="lbl">Critical</div></div>
      <div class="stat-box"><div class="num" style="color:#ea580c">{esc(high)}</div><div class="lbl">High</div></div>
      <div class="stat-box"><div class="num" style="color:#ca8a04">{esc(med + low)}</div><div class="lbl">Medium/Low</div></div>
    </div>
  </div>

  {"".join(f'''<div class="card"><div class="section-title"><span class="icon" style="background:#1e293b">&#9632;</span>Dimension Scores</div>{"".join(bar_html(k,v) for k,v in dims.items()) if dims else '<p style="color:#94a3b8;font-size:13px">No dimension scores available.</p>'}</div>''' if dims else "")}

  <div class="card">
    <div class="section-title"><span class="icon" style="background:#dc2626">!</span>SEO Issues ({len(issues)})</div>
    {issues_block if issues_block else '<p style="color:#94a3b8;font-size:13px;padding:12px 0">No issues found. Excellent!</p>'}
  </div>

  {f'''<div class="card">
    <div class="section-title"><span class="icon" style="background:#2563eb">&#9733;</span>Action Plan ({len(tasks)} tasks, AI-prioritized)</div>
    {tasks_block if tasks_block else '<p style="color:#94a3b8;font-size:13px;padding:12px 0">Generate tasks from the audit page.</p>'}
  </div>''' if tasks_block else ""}

  <div class="card">
    <div class="section-title"><span class="icon" style="background:#64748b">&#9776;</span>Crawled Pages ({len(pages)})</div>
    {f'''<table><thead><tr><th>URL</th><th>Status</th><th>Title</th><th style="text-align:right">Words</th></tr></thead><tbody>{pages_block}</tbody></table>''' if pages_block else '<p style="color:#94a3b8;font-size:13px;padding:12px 0">No pages crawled yet.</p>'}
  </div>

</div>

<div class="footer">
  Universal AI SEO Platform &bull; Report generated {esc(now)}
</div>

</body></html>"""

    return HTMLResponse(content=report_html)
