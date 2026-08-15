"""SQLAlchemy models - full platform schema (PostgreSQL-ready, portable).

Every tenant-scoped table carries a workspace_id and/or website_id. Access is
scoped at the application layer (strict tenant isolation) plus row-level
security policies provided in database/schema.sql for Supabase.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


def uuid4() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


# ---------------------------------------------------------------- users/tenancy
class User(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")


class Workspace(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="free")  # free | pro | agency

    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace")
    projects: Mapped[list["Project"]] = relationship(back_populates="workspace")


class WorkspaceMember(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")  # owner | member

    user: Mapped["User"] = relationship(back_populates="memberships")
    workspace: Mapped["Workspace"] = relationship(back_populates="members")


class Project(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    workspace: Mapped["Workspace"] = relationship(back_populates="projects")
    websites: Mapped[list["Website"]] = relationship(back_populates="project")


class Website(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "websites"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    sitemap_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    robots_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_crawl_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project | None"] = relationship(back_populates="websites")


# ---------------------------------------------------------------- crawling
class CrawlJob(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "crawl_jobs"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|completed|failed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    skipped_by_robots: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Page(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "pages"
    __table_args__ = (
        Index("ix_pages_website_url", "website_id", "final_url"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    final_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    h1: Mapped[list | None] = mapped_column(JSON, nullable=True)
    h2: Mapped[list | None] = mapped_column(JSON, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    canonical: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    robots_meta: Mapped[list | None] = mapped_column(JSON, nullable=True)
    internal_links: Mapped[int] = mapped_column(Integer, default=0)
    external_links: Mapped[int] = mapped_column(Integer, default=0)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    has_schema: Mapped[bool] = mapped_column(Boolean, default=False)
    is_indexable: Mapped[bool] = mapped_column(Boolean, default=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlResult(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "crawl_results"

    crawl_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crawl_jobs.id"), index=True)
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pages.id"), nullable=True, index=True)
    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SeoIssue(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "seo_issues"
    __table_args__ = (
        Index("ix_issues_website_severity", "website_id", "severity"),
        Index("ix_issues_status", "status"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    crawl_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crawl_jobs.id"), nullable=True, index=True)
    issue: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # CRITICAL|HIGH|MEDIUM|LOW
    affected_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimension: Mapped[str] = mapped_column(String(50), default="technical")
    ai_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|in_progress|resolved|ignored
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------- keywords
class Keyword(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "keywords"
    __table_args__ = (
        Index("ix_keywords_website_keyword", "website_id", "keyword"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)  # informational|commercial|transactional|navigational|local
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")


class KeywordCluster(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "keyword_clusters"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(500), nullable=True)


# ---------------------------------------------------------------- competitors
class Competitor(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "competitors"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    domain: Mapped[str] = mapped_column(String(300), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)


# ---------------------------------------------------------------- content
class ContentBrief(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "content_briefs"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    keyword_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("keywords.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    outline: Mapped[list | None] = mapped_column(JSON, nullable=True)
    internal_link_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")


class ContentDocument(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "content_documents"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    brief_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("content_briefs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------- linking
class InternalLinkSuggestion(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "internal_link_suggestions"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected|applied


# ---------------------------------------------------------------- indexing
class Sitemap(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "sitemaps"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    url_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class IndexingCheck(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "indexing_checks"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    engine: Mapped[str] = mapped_column(String(30), default="google")
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    robots_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    noindex: Mapped[bool] = mapped_column(Boolean, default=False)
    canonical: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    crawlable: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    signal_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------- search engines
class SearchEngine(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "search_engines"

    engine_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    supported: Mapped[bool] = mapped_column(Boolean, default=True)


class SearchEngineConnection(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "search_engine_connections"
    __table_args__ = (UniqueConstraint("website_id", "engine_id", name="uq_website_engine"),)

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    engine_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unconfigured")
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SearchData(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "search_data"
    __table_args__ = (
        Index("ix_search_data_website_engine_date", "website_id", "engine_id", "date"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    engine_id: Mapped[str] = mapped_column(String(50), nullable=False)
    keyword: Mapped[str | None] = mapped_column(String(300), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    device: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="unavailable")


class RankingData(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "ranking_data"
    __table_args__ = (
        Index("ix_ranking_website_keyword_engine", "website_id", "engine_id", "keyword"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    engine_id: Mapped[str] = mapped_column(String(50), nullable=False)
    keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    device: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="unavailable")


class SearchConsoleData(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "search_console_data"
    __table_args__ = (
        Index("ix_scd_website_date", "website_id", "date"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    query: Mapped[str | None] = mapped_column(String(300), nullable=True)
    page: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)


class AnalyticsData(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "analytics_data"
    __table_args__ = (
        Index("ix_analytics_website_metric_date", "website_id", "metric", "date"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)  # organic_clicks|organic_impressions|ranked_keywords|...
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="unavailable")


# ---------------------------------------------------------------- tasks / off-page
class SeoTask(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "seo_tasks"
    __table_args__ = (
        Index("ix_tasks_website_status", "website_id", "status"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    crawl_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crawl_jobs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="audit")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected|completed
    ai_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BacklinkOpportunity(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "backlink_opportunities"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # guest_post|digital_pr|resource_page|directory|citation|brand_mention|broken_link
    target_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    anchor: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="open")


# ---------------------------------------------------------------- reports / notifications
class Report(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    website_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("websites.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # weekly|monthly|technical|content|keyword|comparison
    format: Mapped[str] = mapped_column(String(10), default="json")  # pdf|csv|json
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- AI
class AiJob(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "ai_jobs"

    website_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("websites.id"), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiUsage(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "ai_usage"
    __table_args__ = (
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------- audit
class AuditLog(UUIDPkMixin, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
