"""Task generation and AI priority engine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import CrawlJob, SeoIssue, SeoTask
from . import ai_service

PRIORITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

TASK_TEMPLATE = {
    "Missing title": "Add a descriptive, unique title tag to the page.",
    "Duplicate title": "Write unique title tags for each page.",
    "Missing meta description": "Write unique meta descriptions for each page.",
    "Missing H1": "Add a single, topic-focused H1 heading.",
    "Broken internal links": "Fix or redirect internal links that return errors.",
    "Broken URL": "Restore, redirect or remove the broken URL.",
    "Orphan pages": "Add internal links from relevant pages to orphan pages.",
    "Thin content": "Expand thin pages with in-depth, original content.",
    "Duplicate content": "Merge or differentiate near-duplicate pages; use canonicals or redirects.",
    "Missing structured data": "Add relevant schema.org structured data.",
    "Canonical conflict": "Align canonical tags with the intended canonical URL.",
    "Noindex page": "Remove noindex unless the page should be hidden.",
    "No sitemap found": "Create and submit an XML sitemap.",
    "Sitemap problem": "Fix the sitemap XML.",
}


def tasks_from_issues(db: Session, website_id) -> list[SeoTask]:
    issues = (
        db.query(SeoIssue)
        .filter(SeoIssue.website_id == website_id, SeoIssue.status == "open")
        .order_by(SeoIssue.severity)
        .all()
    )
    by_issue: dict[str, list[SeoIssue]] = {}
    for issue in issues:
        by_issue.setdefault(issue.issue, []).append(issue)

    existing = {t.title for t in db.query(SeoTask).filter(SeoTask.website_id == website_id, SeoTask.status.in_(["pending", "approved"]))}
    created = []
    for issue_name, group in by_issue.items():
        if issue_name in existing:
            continue
        priority = _group_priority(group)
        template = TASK_TEMPLATE.get(issue_name, "Resolve this SEO issue.")
        count = len(group)
        description = f"{issue_name}: {count} page(s) affected. {template}" if count > 1 else f"{issue_name}. {template}"
        task = SeoTask(
            website_id=website_id,
            crawl_job_id=group[0].crawl_job_id,
            title=issue_name,
            description=description,
            priority=priority,
            source="audit",
            status="pending",
        )
        db.add(task)
        created.append(task)
    db.commit()
    for task in created:
        db.refresh(task)
    return created


def _group_priority(group: list[SeoIssue]) -> str:
    priorities = [PRIORITY_RANK.get(i.severity, 3) for i in group]
    worst = min(priorities)
    return ["CRITICAL", "HIGH", "MEDIUM", "LOW"][worst]


def apply_ai_priorities(db: Session, website_id) -> list[SeoTask]:
    tasks = db.query(SeoTask).filter(SeoTask.website_id == website_id).all()
    if not tasks:
        return []
    payload = [{"title": t.title, "priority": t.priority, "source": t.source} for t in tasks]
    prioritized = ai_service.prioritize_tasks(payload)
    for task, item in zip(tasks, prioritized):
        task.priority = item.get("priority", task.priority)
        task.impact = item.get("impact", task.impact)
        task.difficulty = item.get("difficulty", task.difficulty)
        task.urgency = item.get("urgency", task.urgency)
        task.confidence = item.get("confidence", task.confidence)
    db.commit()
    ordered = db.query(SeoTask).filter(SeoTask.website_id == website_id).all()
    return ordered
