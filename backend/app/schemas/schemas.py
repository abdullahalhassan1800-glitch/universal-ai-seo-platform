"""Pydantic request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool


class AuthResponse(BaseModel):
    token: str
    user: UserOut
    workspace: "WorkspaceOut | None" = None


# ---------------------------------------------------------------- tenant
class WorkspaceOut(ORMModel):
    id: uuid.UUID
    name: str
    plan: str
    created_at: datetime


class ProjectOut(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WebsiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domain: str = Field(min_length=3, max_length=300)
    project_id: uuid.UUID | None = None


class WebsiteUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    project_id: uuid.UUID | None = None
    sitemap_url: str | None = None
    robots_url: str | None = None


class WebsiteOut(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID | None
    name: str
    domain: str
    sitemap_url: str | None
    robots_url: str | None
    last_crawl_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------- crawl / audit
class CrawlRequest(BaseModel):
    max_pages: int = Field(default=100, ge=1, le=1000)
    delay: float = Field(default=0.5, ge=0, le=10)
    render: str | None = None


class CrawlJobOut(ORMModel):
    id: uuid.UUID
    website_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    max_pages: int
    pages_crawled: int
    skipped_by_robots: int
    errors: list | None
    scores: dict | None


class ScoreOut(BaseModel):
    universal_seo_score: int | None
    dimensions: dict[str, float | None]
    weights: dict[str, float]
    issue_counts: dict[str, int]
    page_count: int


class IssueOut(ORMModel):
    id: uuid.UUID
    website_id: uuid.UUID
    crawl_job_id: uuid.UUID | None
    issue: str
    severity: str
    affected_url: str | None
    explanation: str | None
    recommendation: str | None
    dimension: str
    ai_solution: str | None
    priority: str
    status: str


class PageOut(ORMModel):
    id: uuid.UUID
    url: str
    final_url: str
    status_code: int
    title: str | None
    meta_description: str | None
    word_count: int
    has_schema: bool
    is_indexable: bool
    crawled_at: datetime


# ---------------------------------------------------------------- keywords
class KeywordIn(BaseModel):
    keywords: list[str] = Field(min_length=1)


class KeywordOut(ORMModel):
    id: uuid.UUID
    website_id: uuid.UUID
    keyword: str
    intent: str | None
    country: str | None
    language: str | None
    volume: int | None
    cpc: float | None
    difficulty: int | None
    source: str


class ClusterOut(ORMModel):
    id: uuid.UUID
    website_id: uuid.UUID
    name: str
    intent: str | None
    keywords: list | None
    topic: str | None


class ClusterRequest(BaseModel):
    keywords: list[str] | None = None


# ---------------------------------------------------------------- tasks
class TaskOut(ORMModel):
    id: uuid.UUID
    website_id: uuid.UUID
    crawl_job_id: uuid.UUID | None
    title: str
    description: str | None
    priority: str
    impact: float | None
    difficulty: float | None
    urgency: float | None
    confidence: float | None
    source: str
    status: str
    ai_solution: str | None


class TaskStatusUpdate(BaseModel):
    status: str  # approved | rejected | completed


# ---------------------------------------------------------------- search engines
class EngineOut(BaseModel):
    engine_id: str
    display_name: str
    status: str
    reason: str
    capabilities: dict[str, bool]


class ConnectionOut(ORMModel):
    id: uuid.UUID
    website_id: uuid.UUID
    engine_id: str
    status: str
    last_sync_at: datetime | None
    error: str | None


class ConnectionCreate(BaseModel):
    engine_id: str
    config: dict[str, Any] | None = None


class SyncRequest(BaseModel):
    engine_id: str
    start_date: str = "28daysAgo"
    end_date: str = "today"


# ---------------------------------------------------------------- dashboard
class DashboardSummary(BaseModel):
    websites: int
    average_seo_score: int | None
    total_pages: int
    issues_by_severity: dict[str, int]
    open_tasks: int
    keywords: int
    connections: int
    indexed_urls: int | None
    ranking_keywords: int
    organic_clicks: int | None
    impressions: int | None
    ctr: float | None
    average_position: float | None
    score_trend: list[dict]
    search_visibility: list[dict]
    recent_tasks: list[TaskOut]


class MessageOut(BaseModel):
    message: str


class SerpResult(BaseModel):
    query: str
    search_engine: str
    results: list[dict]
    source: str


class AnalyticsResult(BaseModel):
    search_engine: str
    available: bool
    data: list[dict] | None
    message: str | None
